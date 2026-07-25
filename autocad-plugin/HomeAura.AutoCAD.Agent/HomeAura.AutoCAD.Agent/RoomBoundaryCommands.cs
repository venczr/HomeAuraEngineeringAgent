using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;

namespace HomeAura.AutoCAD.Agent
{
    internal sealed class RoomBoundaryObservation
    {
        public string Handle { get; set; }
        public string ObjectType { get; set; }
        public string Layer { get; set; }
        public string GeometrySource { get; set; }
        public bool IsClosed { get; set; }
        public bool IsSupported { get; set; }
        public double? AreaM2 { get; set; }
        public RoomBoundary Boundary { get; set; }
        public List<string> Messages { get; set; }
    }

    internal sealed class RoomBoundaryDiscoveryResult
    {
        public RoomBoundaryDiscoveryResult()
        {
            ValidBoundaries = new List<RoomBoundary>();
            Observations =
                new List<RoomBoundaryObservation>();
            Messages = new List<string>();
        }

        public List<RoomBoundary> ValidBoundaries
        {
            get;
            private set;
        }

        public List<RoomBoundaryObservation> Observations
        {
            get;
            private set;
        }

        public List<string> Messages
        {
            get;
            private set;
        }
    }

    internal static class RoomBoundaryService
    {
        public static RoomBoundaryDiscoveryResult Discover(
            Database database,
            Transaction transaction)
        {
            RoomBoundaryDiscoveryResult result =
                new RoomBoundaryDiscoveryResult();

            BlockTable blockTable =
                transaction.GetObject(
                    database.BlockTableId,
                    OpenMode.ForRead
                ) as BlockTable;

            if (blockTable == null)
            {
                result.Messages.Add(
                    "Не удалось открыть таблицу блоков."
                );

                return result;
            }

            BlockTableRecord modelSpace =
                transaction.GetObject(
                    blockTable[
                        BlockTableRecord.ModelSpace
                    ],
                    OpenMode.ForRead
                ) as BlockTableRecord;

            if (modelSpace == null)
            {
                result.Messages.Add(
                    "Не удалось открыть пространство модели."
                );

                return result;
            }

            foreach (ObjectId objectId in modelSpace)
            {
                Entity entity =
                    transaction.GetObject(
                        objectId,
                        OpenMode.ForRead,
                        false
                    ) as Entity;

                if (entity == null)
                {
                    continue;
                }

                InspectModelSpaceEntity(
                    database,
                    transaction,
                    entity,
                    result
                );
            }

            InspectMagiCadBlockDefinitions(
                modelSpace,
                transaction,
                result
            );

            return result;
        }

        public static RoomBoundarySelectionResult MatchMarker(
            IList<RoomBoundary> candidates,
            Point3d markerPosition,
            string markerHandle,
            double? magiCadAreaM2)
        {
            RoomBoundarySelectionResult selection =
                RoomGeometryMath
                    .RankContainingBoundaries(
                        candidates,
                        markerPosition.X,
                        markerPosition.Y,
                        magiCadAreaM2
                    );

            foreach (RoomBoundary match
                     in selection.Matches)
            {
                if (match.Diagnostics != null &&
                    !match.Diagnostics
                        .ContainingMarkerHandles
                        .Contains(markerHandle))
                {
                    match.Diagnostics
                        .ContainingMarkerHandles
                        .Add(markerHandle);
                }
            }

            return selection;
        }

        private static void InspectModelSpaceEntity(
            Database database,
            Transaction transaction,
            Entity entity,
            RoomBoundaryDiscoveryResult result)
        {
            Polyline polyline = entity as Polyline;

            if (polyline != null)
            {
                RoomBoundary boundary =
                    CreateBoundary(
                        database,
                        transaction,
                        polyline
                    );

                RoomBoundaryObservation observation =
                    CreateObservation(
                        entity,
                        "AutoCAD.ModelSpace.Polyline",
                        true
                    );

                observation.IsClosed =
                    boundary.IsClosed;

                observation.AreaM2 =
                    boundary.ContourAreaM2;

                observation.Boundary =
                    boundary;

                observation.Messages.AddRange(
                    boundary.Diagnostics.Messages
                );

                result.Observations.Add(observation);

                if (boundary.Diagnostics.IsValid)
                {
                    result.ValidBoundaries.Add(boundary);
                }

                return;
            }

            if (entity is Polyline2d)
            {
                AddUnsupportedObservation(
                    entity,
                    "AutoCAD.ModelSpace.Polyline2d",
                    "Polyline2d обнаружена, но пока " +
                    "не используется как граница.",
                    result
                );

                return;
            }

            Polyline3d polyline3d =
                entity as Polyline3d;

            if (polyline3d != null)
            {
                RoomBoundary boundary =
                    CreatePolyline3dBoundary(
                        database,
                        transaction,
                        polyline3d
                    );

                RoomBoundaryObservation observation =
                    CreateObservation(
                        entity,
                        "AutoCAD.ModelSpace.Polyline3d",
                        boundary.Diagnostics.IsSupported
                    );

                observation.IsClosed =
                    boundary.IsClosed;
                observation.AreaM2 =
                    boundary.ContourAreaM2;
                observation.Boundary = boundary;
                observation.Messages.AddRange(
                    boundary.Diagnostics.Messages
                );

                result.Observations.Add(observation);

                if (boundary.Diagnostics.IsValid)
                {
                    result.ValidBoundaries.Add(
                        boundary
                    );
                }

                return;
            }

            if (entity is Region)
            {
                AddUnsupportedObservation(
                    entity,
                    "AutoCAD.ModelSpace.Region",
                    "Region обнаружен, но пока " +
                    "не используется как граница.",
                    result
                );
            }
        }

        private static void InspectMagiCadBlockDefinitions(
            BlockTableRecord modelSpace,
            Transaction transaction,
            RoomBoundaryDiscoveryResult result)
        {
            HashSet<ObjectId> inspectedRecords =
                new HashSet<ObjectId>();

            foreach (ObjectId referenceId in modelSpace)
            {
                BlockReference blockReference =
                    transaction.GetObject(
                        referenceId,
                        OpenMode.ForRead,
                        false
                    ) as BlockReference;

                if (blockReference == null ||
                    string.IsNullOrWhiteSpace(
                        blockReference.Layer) ||
                    !blockReference.Layer.StartsWith(
                        "MAGI",
                        StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                ObjectId recordId =
                    blockReference.BlockTableRecord;

                if (recordId.IsNull ||
                    inspectedRecords.Contains(recordId))
                {
                    continue;
                }

                inspectedRecords.Add(recordId);

                BlockTableRecord record =
                    transaction.GetObject(
                        recordId,
                        OpenMode.ForRead,
                        false
                    ) as BlockTableRecord;

                if (record == null ||
                    record.IsLayout)
                {
                    continue;
                }

                foreach (ObjectId entityId in record)
                {
                    Entity entity =
                        transaction.GetObject(
                            entityId,
                            OpenMode.ForRead,
                            false
                        ) as Entity;

                    if (!(entity is Polyline) &&
                        !(entity is Polyline2d) &&
                        !(entity is Polyline3d) &&
                        !(entity is Region))
                    {
                        continue;
                    }

                    RoomBoundaryObservation observation =
                        CreateObservation(
                            entity,
                            "AutoCAD.MagiCADBlockDefinition:" +
                            record.Name +
                            "@" +
                            blockReference.Handle,
                            false
                        );

                    observation.Messages.Add(
                        "Геометрия внутри определения " +
                        "блока обнаружена только для " +
                        "диагностики и не используется."
                    );

                    result.Observations.Add(observation);
                }
            }
        }

        private static RoomBoundary CreateBoundary(
            Database database,
            Transaction transaction,
            Polyline polyline)
        {
            string drawingUnits =
                database.Insunits.ToString();

            double metersPerDrawingUnit;

            bool hasKnownUnits =
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        drawingUnits,
                        out metersPerDrawingUnit
                    );

            double vertexTolerance =
                hasKnownUnits
                    ? RoomGeometryMath
                        .DefaultVertexToleranceMeters /
                      metersPerDrawingUnit
                    : 1e-8;

            double arcChordTolerance =
                hasKnownUnits
                    ? RoomGeometryMath
                        .DefaultArcChordToleranceMeters /
                      metersPerDrawingUnit
                    : 1e-3;

            RoomBoundary boundary =
                new RoomBoundary
                {
                    SourceHandle =
                        polyline.Handle.ToString(),

                    SourceObjectType =
                        GetObjectType(polyline),

                    SourceLayer =
                        polyline.Layer,

                    IsClosed =
                        polyline.Closed,

                    OriginalClosedFlag =
                        polyline.Closed,

                    LogicalClosureMethod =
                        polyline.Closed
                            ? "AutoCAD Closed flag"
                            : "Open",

                    DrawingUnits =
                        drawingUnits,

                    MetersPerDrawingUnit =
                        hasKnownUnits
                            ? (double?)
                                metersPerDrawingUnit
                            : null,

                    GeometrySource =
                        "AutoCAD.ModelSpace.Polyline",

                    HasMagiCadData =
                        HasMagiCadData(
                            transaction,
                            polyline
                        )
                };

            boundary.Diagnostics.IsSupported = true;
            boundary.Diagnostics.MinimumVertexCount =
                RoomGeometryMath.MinimumVertexCount;

            boundary.Diagnostics
                .VertexToleranceDrawingUnits =
                    vertexTolerance;

            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits =
                    arcChordTolerance;

            List<RoomBoundaryVertex> rawVertices =
                new List<RoomBoundaryVertex>();

            for (int index = 0;
                 index < polyline.NumberOfVertices;
                 index++)
            {
                Point3d point =
                    polyline.GetPoint3dAt(index);

                double bulge =
                    polyline.GetBulgeAt(index);

                rawVertices.Add(
                    new RoomBoundaryVertex
                    {
                        X = point.X,
                        Y = point.Y,
                        Z = point.Z,
                        Bulge = bulge,
                        SegmentType =
                            Math.Abs(bulge) <= 1e-12
                                ? "Line"
                                : "Arc"
                    }
                );
            }

            boundary.SourceVertices =
                new List<RoomBoundaryVertex>(
                    rawVertices
                );

            double minimumZ =
                rawVertices.Count == 0
                    ? 0
                    : rawVertices.Min(
                        vertex => vertex.Z
                    );

            double maximumZ =
                rawVertices.Count == 0
                    ? 0
                    : rawVertices.Max(
                        vertex => vertex.Z
                    );

            boundary.ZDeviationDrawingUnits =
                maximumZ - minimumZ;

            boundary.ZDeviationM =
                hasKnownUnits
                    ? (double?)(
                        (maximumZ - minimumZ) *
                        metersPerDrawingUnit
                    )
                    : null;

            int duplicateVerticesRemoved;

            List<RoomBoundaryVertex>
                normalizedVertices =
                    RoomGeometryMath
                        .NormalizeVertices(
                            rawVertices,
                            vertexTolerance,
                            boundary.IsClosed,
                            out duplicateVerticesRemoved
                        );

            boundary.Diagnostics
                .DuplicateVerticesRemoved =
                    duplicateVerticesRemoved;

            boundary.OriginalDirection =
                RoomGeometryMath.GetDirection(
                    normalizedVertices
                );

            boundary.Vertices =
                RoomGeometryMath
                    .NormalizeCounterClockwise(
                        normalizedVertices
                    );

            boundary.Direction =
                RoomGeometryMath.GetDirection(
                    boundary.Vertices
                );

            if (duplicateVerticesRemoved > 0)
            {
                boundary.Diagnostics.Messages.Add(
                    "Удалено последовательных " +
                    "дубликатов вершин: " +
                    duplicateVerticesRemoved + "."
                );
            }

            if (!boundary.IsClosed)
            {
                boundary.Diagnostics.Messages.Add(
                    "Polyline не замкнута."
                );
            }

            if (boundary.Vertices.Count <
                RoomGeometryMath.MinimumVertexCount)
            {
                boundary.Diagnostics.Messages.Add(
                    "После нормализации осталось " +
                    boundary.Vertices.Count +
                    " вершин; требуется минимум " +
                    RoomGeometryMath.MinimumVertexCount +
                    "."
                );
            }

            if (string.Equals(
                    boundary.Direction,
                    "Degenerate",
                    StringComparison.Ordinal))
            {
                boundary.Diagnostics.Messages.Add(
                    "Контур имеет нулевую " +
                    "ориентированную площадь."
                );
            }

            Vector3d normal = polyline.Normal;

            boundary.IsPlanar =
                Math.Abs(normal.Z) >= 0.999999;

            if (Math.Abs(normal.Z) < 0.999999)
            {
                boundary.Diagnostics.Messages.Add(
                    "Polyline не параллельна плоскости " +
                    "XY; проверка маркера отключена."
                );
            }

            if (boundary.IsClosed &&
                boundary.Vertices.Count >=
                    RoomGeometryMath.MinimumVertexCount)
            {
                boundary.Diagnostics
                    .IsSelfIntersecting =
                        RoomGeometryMath
                            .HasSelfIntersections(
                                boundary.Vertices,
                                arcChordTolerance,
                                vertexTolerance
                            );

                if (boundary.Diagnostics
                        .IsSelfIntersecting)
                {
                    boundary.Diagnostics.Messages.Add(
                        "Обнаружено самопересечение " +
                        "контура."
                    );
                }
            }

            if (!hasKnownUnits)
            {
                boundary.Diagnostics.Messages.Add(
                    "Единицы чертежа '" +
                    drawingUnits +
                    "' нельзя однозначно перевести " +
                    "в метры."
                );
            }

            if (boundary.IsClosed &&
                boundary.Vertices.Count >=
                    RoomGeometryMath.MinimumVertexCount)
            {
                try
                {
                    double areaDrawingUnits2 =
                        Math.Abs(polyline.Area);

                    double perimeterDrawingUnits =
                        polyline.Length;

                    boundary.ContourAreaDrawingUnits2 =
                        areaDrawingUnits2;

                    boundary.PerimeterDrawingUnits =
                        perimeterDrawingUnits;

                    if (hasKnownUnits)
                    {
                        boundary.ContourAreaM2 =
                            areaDrawingUnits2 *
                            metersPerDrawingUnit *
                            metersPerDrawingUnit;

                        boundary.PerimeterM =
                            perimeterDrawingUnits *
                            metersPerDrawingUnit;
                    }
                }
                catch (System.Exception exception)
                {
                    boundary.Diagnostics.Messages.Add(
                        "AutoCAD не вычислил точную " +
                        "площадь/длину: " +
                        exception.Message
                    );
                }
            }

            boundary.Diagnostics.IsValid =
                boundary.IsClosed &&
                boundary.Vertices.Count >=
                    RoomGeometryMath.MinimumVertexCount &&
                !boundary.Diagnostics
                    .IsSelfIntersecting &&
                !string.Equals(
                    boundary.Direction,
                    "Degenerate",
                    StringComparison.Ordinal) &&
                Math.Abs(normal.Z) >= 0.999999 &&
                hasKnownUnits &&
                boundary.ContourAreaM2.HasValue &&
                boundary.PerimeterM.HasValue;

            return boundary;
        }

        private static RoomBoundary
            CreatePolyline3dBoundary(
                Database database,
                Transaction transaction,
                Polyline3d polyline)
        {
            string drawingUnits =
                database.Insunits.ToString();

            double metersPerDrawingUnit;

            bool hasKnownUnits =
                RoomGeometryMath
                    .TryGetMetersPerDrawingUnit(
                        drawingUnits,
                        out metersPerDrawingUnit
                    );

            List<RoomBoundaryVertex> sourceVertices =
                new List<RoomBoundaryVertex>();

            foreach (ObjectId vertexId in polyline)
            {
                PolylineVertex3d vertex =
                    transaction.GetObject(
                        vertexId,
                        OpenMode.ForRead,
                        false
                    ) as PolylineVertex3d;

                if (vertex == null)
                {
                    continue;
                }

                sourceVertices.Add(
                    new RoomBoundaryVertex
                    {
                        X = vertex.Position.X,
                        Y = vertex.Position.Y,
                        Z = vertex.Position.Z,
                        Bulge = 0,
                        SegmentType = "Line"
                    }
                );
            }

            RoomBoundary boundary =
                RoomGeometryMath
                    .CreatePolyline3dBoundary(
                        polyline.Handle.ToString(),
                        polyline.Layer,
                        sourceVertices,
                        polyline.Closed,
                        polyline.PolyType.ToString(),
                        drawingUnits,
                        hasKnownUnits
                            ? (double?)
                                metersPerDrawingUnit
                            : null,
                        HasMagiCadData(
                            transaction,
                            polyline
                        )
                    );

            boundary.SourceObjectType =
                GetObjectType(polyline);

            return boundary;
        }

        private static bool HasMagiCadData(
            Transaction transaction,
            DBObject databaseObject)
        {
            if (databaseObject.ExtensionDictionary
                    .IsNull)
            {
                return false;
            }

            DBDictionary dictionary =
                transaction.GetObject(
                    databaseObject.ExtensionDictionary,
                    OpenMode.ForRead,
                    false
                ) as DBDictionary;

            return dictionary != null &&
                dictionary.Contains("MagiCAD-R");
        }

        private static void AddUnsupportedObservation(
            Entity entity,
            string geometrySource,
            string message,
            RoomBoundaryDiscoveryResult result)
        {
            RoomBoundaryObservation observation =
                CreateObservation(
                    entity,
                    geometrySource,
                    false
                );

            observation.Messages.Add(message);
            result.Observations.Add(observation);
        }

        private static RoomBoundaryObservation
            CreateObservation(
                Entity entity,
                string geometrySource,
                bool isSupported)
        {
            return new RoomBoundaryObservation
            {
                Handle = entity.Handle.ToString(),
                ObjectType = GetObjectType(entity),
                Layer = entity.Layer,
                GeometrySource = geometrySource,
                IsClosed =
                    entity is Polyline &&
                    ((Polyline)entity).Closed,
                IsSupported = isSupported,
                AreaM2 = null,
                Boundary = null,
                Messages = new List<string>()
            };
        }

        private static string GetObjectType(
            DBObject databaseObject)
        {
            RXClass rxClass =
                databaseObject.GetRXClass();

            if (rxClass != null &&
                !string.IsNullOrWhiteSpace(
                    rxClass.DxfName))
            {
                return rxClass.DxfName;
            }

            return databaseObject.GetType().FullName;
        }
    }

    public sealed partial class Commands
    {
        [CommandMethod(
            "HA_DISCOVER_ROOM_BOUNDARIES",
            CommandFlags.Modal)]
        public void DiscoverRoomBoundaries()
        {
            Document document =
                Application.DocumentManager
                    .MdiActiveDocument;

            if (document == null)
            {
                return;
            }

            Editor editor = document.Editor;
            Database database = document.Database;

            try
            {
                using (Transaction transaction =
                       database.TransactionManager
                           .StartTransaction())
                {
                    RoomBoundaryDiscoveryResult result =
                        RoomBoundaryService.Discover(
                            database,
                            transaction
                        );

                    List<BlockReference> markers =
                        FindRoomMarkers(
                            database,
                            transaction
                        );

                    editor.WriteMessage("\n");
                    editor.WriteMessage(
                        "\n===================================="
                    );
                    editor.WriteMessage(
                        "\n HomeAura — границы помещений"
                    );
                    editor.WriteMessage(
                        "\n===================================="
                    );
                    editor.WriteMessage(
                        "\nОбъектов-кандидатов: " +
                        result.Observations.Count
                    );
                    editor.WriteMessage(
                        "\nПоддерживаемых валидных " +
                        "контуров: " +
                        result.ValidBoundaries.Count
                    );
                    editor.WriteMessage(
                        "\nМаркеров MAGIROOMTAG: " +
                        markers.Count
                    );

                    foreach (
                        RoomBoundaryObservation observation
                        in result.Observations)
                    {
                        editor.WriteMessage(
                            "\n\nHandle: " +
                            observation.Handle
                        );
                        editor.WriteMessage(
                            "\n  Тип: " +
                            observation.ObjectType
                        );
                        editor.WriteMessage(
                            "\n  Слой: " +
                            observation.Layer
                        );
                        editor.WriteMessage(
                            "\n  Источник: " +
                            observation.GeometrySource
                        );
                        editor.WriteMessage(
                            "\n  Замкнут: " +
                            (
                                observation.IsClosed
                                    ? "да"
                                    : "нет"
                            )
                        );
                        editor.WriteMessage(
                            "\n  Поддерживается: " +
                            (
                                observation.IsSupported
                                    ? "да"
                                    : "нет"
                            )
                        );
                        editor.WriteMessage(
                            "\n  Площадь: " +
                            FormatBoundaryArea(
                                observation.AreaM2
                            )
                        );

                        if (observation.Boundary != null)
                        {
                            editor.WriteMessage(
                                "\n  Исходный Closed: " +
                                observation.Boundary
                                    .OriginalClosedFlag
                            );
                            editor.WriteMessage(
                                "\n  Способ замыкания: " +
                                observation.Boundary
                                    .LogicalClosureMethod
                            );
                            editor.WriteMessage(
                                "\n  Планарный: " +
                                observation.Boundary
                                    .IsPlanar
                            );
                            editor.WriteMessage(
                                "\n  Отклонение Z: " +
                                (
                                    observation.Boundary
                                        .ZDeviationDrawingUnits
                                        .HasValue
                                        ? observation.Boundary
                                            .ZDeviationDrawingUnits
                                            .Value
                                            .ToString(
                                                "0.###",
                                                CultureInfo
                                                    .InvariantCulture
                                            )
                                        : "нет данных"
                                )
                            );
                            editor.WriteMessage(
                                "\n  MagiCAD-R: " +
                                observation.Boundary
                                    .HasMagiCadData
                            );
                        }

                        List<string> containedMarkers =
                            new List<string>();

                        if (observation.Boundary != null &&
                            observation.Boundary
                                .Diagnostics.IsValid)
                        {
                            foreach (
                                BlockReference marker
                                in markers)
                            {
                                if (RoomGeometryMath
                                        .ContainsPoint(
                                            observation
                                                .Boundary,
                                            marker.Position.X,
                                            marker.Position.Y
                                        ))
                                {
                                    containedMarkers.Add(
                                        marker.Handle
                                            .ToString()
                                    );
                                }
                            }
                        }

                        editor.WriteMessage(
                            "\n  Маркеры внутри: " +
                            (
                                containedMarkers.Count == 0
                                    ? "нет"
                                    : string.Join(
                                        ", ",
                                        containedMarkers
                                    )
                            )
                        );

                        foreach (string message
                                 in observation.Messages)
                        {
                            editor.WriteMessage(
                                "\n  Диагностика: " +
                                message
                            );
                        }
                    }

                    foreach (string message
                             in result.Messages)
                    {
                        editor.WriteMessage(
                            "\nДиагностика: " +
                            message
                        );
                    }

                    editor.WriteMessage(
                        "\n===================================="
                    );
                    editor.WriteMessage("\n");

                    // No Commit(): the command is deliberately
                    // read-only and lets the transaction abort.
                }
            }
            catch (System.Exception exception)
            {
                editor.WriteMessage(
                    "\nОшибка " +
                    "HA_DISCOVER_ROOM_BOUNDARIES: " +
                    exception.Message
                );
            }
        }

        private static List<BlockReference>
            FindRoomMarkers(
                Database database,
                Transaction transaction)
        {
            List<BlockReference> result =
                new List<BlockReference>();

            BlockTable blockTable =
                transaction.GetObject(
                    database.BlockTableId,
                    OpenMode.ForRead
                ) as BlockTable;

            if (blockTable == null)
            {
                return result;
            }

            BlockTableRecord modelSpace =
                transaction.GetObject(
                    blockTable[
                        BlockTableRecord.ModelSpace
                    ],
                    OpenMode.ForRead
                ) as BlockTableRecord;

            if (modelSpace == null)
            {
                return result;
            }

            foreach (ObjectId objectId in modelSpace)
            {
                BlockReference marker =
                    transaction.GetObject(
                        objectId,
                        OpenMode.ForRead,
                        false
                    ) as BlockReference;

                if (marker != null &&
                    string.Equals(
                        marker.Layer,
                        "MAGIROOMTAG",
                        StringComparison
                            .OrdinalIgnoreCase))
                {
                    result.Add(marker);
                }
            }

            return result;
        }

        private static string FormatBoundaryArea(
            double? areaM2)
        {
            if (!areaM2.HasValue)
            {
                return "нет данных";
            }

            return areaM2.Value.ToString(
                "0.###",
                CultureInfo.InvariantCulture
            ) + " м²";
        }
    }
}
