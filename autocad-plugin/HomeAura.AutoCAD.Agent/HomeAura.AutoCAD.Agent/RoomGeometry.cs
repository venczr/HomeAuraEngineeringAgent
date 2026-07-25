using System;
using System.Collections.Generic;
using System.Runtime.Serialization;

namespace HomeAura.AutoCAD.Agent
{
    [DataContract]
    public sealed class RoomBoundaryVertex
    {
        [DataMember(Order = 1)]
        public double X { get; set; }

        [DataMember(Order = 2)]
        public double Y { get; set; }

        [DataMember(Order = 3)]
        public double Z { get; set; }

        [DataMember(Order = 4)]
        public double Bulge { get; set; }

        [DataMember(Order = 5)]
        public string SegmentType { get; set; }
    }

    [DataContract]
    public sealed class RoomBoundaryDiagnostics
    {
        public RoomBoundaryDiagnostics()
        {
            ContainingMarkerHandles = new List<string>();
            Messages = new List<string>();
        }

        [DataMember(Order = 1)]
        public bool IsSupported { get; set; }

        [DataMember(Order = 2)]
        public bool IsValid { get; set; }

        [DataMember(Order = 3)]
        public int DuplicateVerticesRemoved { get; set; }

        [DataMember(Order = 4)]
        public bool IsSelfIntersecting { get; set; }

        [DataMember(Order = 5)]
        public int MinimumVertexCount { get; set; }

        [DataMember(Order = 6)]
        public double VertexToleranceDrawingUnits { get; set; }

        [DataMember(Order = 7)]
        public double ArcChordToleranceDrawingUnits { get; set; }

        [DataMember(Order = 8)]
        public List<string> ContainingMarkerHandles { get; set; }

        [DataMember(Order = 9)]
        public List<string> Messages { get; set; }
    }

    [DataContract]
    public sealed class RoomBoundary
    {
        public RoomBoundary()
        {
            SourceVertices = new List<RoomBoundaryVertex>();
            Vertices = new List<RoomBoundaryVertex>();
            Diagnostics = new RoomBoundaryDiagnostics();
        }

        [DataMember(Order = 1)]
        public string SourceHandle { get; set; }

        [DataMember(Order = 2)]
        public string SourceObjectType { get; set; }

        [DataMember(Order = 3)]
        public string SourceLayer { get; set; }

        [DataMember(Order = 4)]
        public List<RoomBoundaryVertex> Vertices { get; set; }

        [DataMember(Order = 5)]
        public bool IsClosed { get; set; }

        [DataMember(Order = 6)]
        public double? ContourAreaDrawingUnits2 { get; set; }

        [DataMember(Order = 7)]
        public double? ContourAreaM2 { get; set; }

        [DataMember(Order = 8)]
        public double? PerimeterDrawingUnits { get; set; }

        [DataMember(Order = 9)]
        public double? PerimeterM { get; set; }

        [DataMember(Order = 10)]
        public string OriginalDirection { get; set; }

        [DataMember(Order = 11)]
        public string Direction { get; set; }

        [DataMember(Order = 12)]
        public string DrawingUnits { get; set; }

        [DataMember(Order = 13)]
        public double? MetersPerDrawingUnit { get; set; }

        [DataMember(Order = 14)]
        public string GeometrySource { get; set; }

        [DataMember(Order = 15)]
        public RoomBoundaryDiagnostics Diagnostics { get; set; }

        [DataMember(Order = 16)]
        public List<RoomBoundaryVertex> SourceVertices
        {
            get;
            set;
        }

        [DataMember(Order = 17)]
        public bool OriginalClosedFlag { get; set; }

        [DataMember(Order = 18)]
        public string LogicalClosureMethod { get; set; }

        [DataMember(Order = 19)]
        public double? ZDeviationDrawingUnits
        {
            get;
            set;
        }

        [DataMember(Order = 20)]
        public double? ZDeviationM { get; set; }

        [DataMember(Order = 21)]
        public bool IsPlanar { get; set; }

        [DataMember(Order = 22)]
        public string Polyline3dType { get; set; }

        [DataMember(Order = 23)]
        public bool HasMagiCadData { get; set; }
    }

    [DataContract]
    public sealed class RoomBoundaryCandidate
    {
        [DataMember(Order = 1)]
        public string SourceHandle { get; set; }

        [DataMember(Order = 2)]
        public string SourceObjectType { get; set; }

        [DataMember(Order = 3)]
        public string SourceLayer { get; set; }

        [DataMember(Order = 4)]
        public string GeometrySource { get; set; }

        [DataMember(Order = 5)]
        public bool HasMagiCadData { get; set; }

        [DataMember(Order = 6)]
        public int PriorityTier { get; set; }

        [DataMember(Order = 7)]
        public string PriorityReason { get; set; }

        [DataMember(Order = 8)]
        public double? BoundaryAreaM2 { get; set; }

        [DataMember(Order = 9)]
        public double? AreaDifferenceM2 { get; set; }

        [DataMember(Order = 10)]
        public double? AreaDifferencePercent { get; set; }

        [DataMember(Order = 11)]
        public string AreaMatchStatus { get; set; }

        [DataMember(Order = 12)]
        public string GeometryStatus { get; set; }

        [DataMember(Order = 13)]
        public bool IsSelected { get; set; }
    }

    public sealed class RoomBoundarySelectionResult
    {
        public RoomBoundarySelectionResult()
        {
            Matches = new List<RoomBoundary>();
        }

        public RoomBoundary Selected { get; set; }
        public List<RoomBoundary> Matches { get; set; }
        public bool IsAmbiguous { get; set; }
    }

    public static class RoomGeometryMath
    {
        public const int MinimumVertexCount = 3;
        public const double DefaultArcChordToleranceMeters = 0.001;
        public const double DefaultVertexToleranceMeters = 0.0001;
        public const double Polyline3dPlanarityToleranceMeters = 0.001;
        public const double AreaWarningThresholdPercent = 15.0;
        public const double CandidateTieToleranceM2 = 0.01;

        public static List<RoomBoundaryVertex> NormalizeVertices(
            IList<RoomBoundaryVertex> source,
            double tolerance,
            bool isClosed,
            out int removedCount)
        {
            List<RoomBoundaryVertex> result =
                new List<RoomBoundaryVertex>();

            removedCount = 0;

            if (source == null)
            {
                return result;
            }

            double effectiveTolerance =
                Math.Max(tolerance, 1e-12);

            foreach (RoomBoundaryVertex sourceVertex in source)
            {
                if (sourceVertex == null)
                {
                    removedCount++;
                    continue;
                }

                RoomBoundaryVertex vertex =
                    CloneVertex(sourceVertex);

                vertex.SegmentType =
                    GetSegmentType(vertex.Bulge);

                if (result.Count > 0 &&
                    AreCoincident(
                        result[result.Count - 1],
                        vertex,
                        effectiveTolerance))
                {
                    // The zero-length outgoing segment of the preceding
                    // duplicate disappears. Preserve the outgoing segment
                    // that starts at the later vertex.
                    result[result.Count - 1].Bulge =
                        vertex.Bulge;

                    result[result.Count - 1].SegmentType =
                        vertex.SegmentType;

                    removedCount++;
                    continue;
                }

                result.Add(vertex);
            }

            if (isClosed &&
                result.Count > 1 &&
                AreCoincident(
                    result[0],
                    result[result.Count - 1],
                    effectiveTolerance))
            {
                // A closed AutoCAD Polyline closes logically; the first
                // vertex must not be repeated at the end of the contract.
                result.RemoveAt(result.Count - 1);
                removedCount++;
            }

            return result;
        }

        public static string GetDirection(
            IList<RoomBoundaryVertex> vertices)
        {
            double signedArea =
                CalculateSignedArea(vertices);

            if (Math.Abs(signedArea) <= 1e-12)
            {
                return "Degenerate";
            }

            return signedArea > 0
                ? "CCW"
                : "CW";
        }

        public static List<RoomBoundaryVertex>
            NormalizeCounterClockwise(
                IList<RoomBoundaryVertex> vertices)
        {
            List<RoomBoundaryVertex> result =
                CloneVertices(vertices);

            if (!string.Equals(
                    GetDirection(result),
                    "CW",
                    StringComparison.Ordinal))
            {
                return result;
            }

            List<RoomBoundaryVertex> reversed =
                new List<RoomBoundaryVertex>();

            int count = result.Count;

            for (int index = count - 1;
                 index >= 0;
                 index--)
            {
                int previousIndex =
                    (index - 1 + count) % count;

                RoomBoundaryVertex vertex =
                    CloneVertex(result[index]);

                vertex.Bulge =
                    -result[previousIndex].Bulge;

                vertex.SegmentType =
                    GetSegmentType(vertex.Bulge);

                reversed.Add(vertex);
            }

            return reversed;
        }

        public static double CalculateSignedArea(
            IList<RoomBoundaryVertex> vertices)
        {
            if (vertices == null ||
                vertices.Count < 2)
            {
                return 0;
            }

            double twiceChordArea = 0;
            double arcSegmentArea = 0;

            for (int index = 0;
                 index < vertices.Count;
                 index++)
            {
                RoomBoundaryVertex start =
                    vertices[index];

                RoomBoundaryVertex end =
                    vertices[
                        (index + 1) %
                        vertices.Count
                    ];

                twiceChordArea +=
                    start.X * end.Y -
                    end.X * start.Y;

                if (Math.Abs(start.Bulge) <= 1e-12)
                {
                    continue;
                }

                double chord =
                    Distance2d(start, end);

                if (chord <= 1e-12)
                {
                    continue;
                }

                double theta =
                    4.0 * Math.Atan(start.Bulge);

                double radius =
                    chord *
                    (1.0 + start.Bulge * start.Bulge) /
                    (4.0 * Math.Abs(start.Bulge));

                arcSegmentArea +=
                    0.5 * radius * radius *
                    (theta - Math.Sin(theta));
            }

            return
                0.5 * twiceChordArea +
                arcSegmentArea;
        }

        public static List<RoomBoundaryVertex> Flatten(
            IList<RoomBoundaryVertex> vertices,
            double chordTolerance)
        {
            List<RoomBoundaryVertex> result =
                new List<RoomBoundaryVertex>();

            if (vertices == null ||
                vertices.Count == 0)
            {
                return result;
            }

            double effectiveTolerance =
                Math.Max(chordTolerance, 1e-9);

            result.Add(ClonePoint(vertices[0]));

            for (int index = 0;
                 index < vertices.Count;
                 index++)
            {
                RoomBoundaryVertex start =
                    vertices[index];

                RoomBoundaryVertex end =
                    vertices[
                        (index + 1) %
                        vertices.Count
                    ];

                AppendFlattenedSegment(
                    result,
                    start,
                    end,
                    effectiveTolerance
                );
            }

            return result;
        }

        public static bool HasSelfIntersections(
            IList<RoomBoundaryVertex> vertices,
            double chordTolerance,
            double intersectionTolerance)
        {
            List<RoomBoundaryVertex> flattened =
                Flatten(vertices, chordTolerance);

            if (flattened.Count < 4)
            {
                return false;
            }

            int segmentCount = flattened.Count - 1;

            for (int firstIndex = 0;
                 firstIndex < segmentCount;
                 firstIndex++)
            {
                RoomBoundaryVertex firstStart =
                    flattened[firstIndex];

                RoomBoundaryVertex firstEnd =
                    flattened[firstIndex + 1];

                for (int secondIndex =
                         firstIndex + 1;
                     secondIndex < segmentCount;
                     secondIndex++)
                {
                    if (AreAdjacentSegments(
                            firstIndex,
                            secondIndex,
                            segmentCount))
                    {
                        continue;
                    }

                    RoomBoundaryVertex secondStart =
                        flattened[secondIndex];

                    RoomBoundaryVertex secondEnd =
                        flattened[secondIndex + 1];

                    if (SegmentsIntersect(
                            firstStart,
                            firstEnd,
                            secondStart,
                            secondEnd,
                            intersectionTolerance))
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        public static bool ContainsPoint(
            RoomBoundary boundary,
            double x,
            double y)
        {
            if (boundary == null ||
                boundary.Vertices == null ||
                boundary.Vertices.Count <
                    MinimumVertexCount ||
                !boundary.IsClosed)
            {
                return false;
            }

            double chordTolerance =
                boundary.Diagnostics == null
                    ? 1e-3
                    : Math.Max(
                        boundary.Diagnostics
                            .ArcChordToleranceDrawingUnits,
                        1e-9
                    );

            double pointTolerance =
                boundary.Diagnostics == null
                    ? 1e-8
                    : Math.Max(
                        boundary.Diagnostics
                            .VertexToleranceDrawingUnits,
                        1e-9
                    );

            List<RoomBoundaryVertex> flattened =
                Flatten(
                    boundary.Vertices,
                    chordTolerance
                );

            if (flattened.Count < 4)
            {
                return false;
            }

            bool inside = false;

            for (int index = 0;
                 index < flattened.Count - 1;
                 index++)
            {
                RoomBoundaryVertex start =
                    flattened[index];

                RoomBoundaryVertex end =
                    flattened[index + 1];

                if (PointOnSegment(
                        x,
                        y,
                        start,
                        end,
                        pointTolerance))
                {
                    return true;
                }

                bool crosses =
                    (start.Y > y) !=
                    (end.Y > y);

                if (!crosses)
                {
                    continue;
                }

                double crossingX =
                    start.X +
                    (y - start.Y) *
                    (end.X - start.X) /
                    (end.Y - start.Y);

                if (crossingX >= x)
                {
                    inside = !inside;
                }
            }

            return inside;
        }

        public static RoomBoundary
            SelectSmallestContaining(
                IList<RoomBoundary> candidates,
                double x,
                double y,
                out int containingCount)
        {
            RoomBoundary selected = null;
            double selectedArea =
                double.PositiveInfinity;

            containingCount = 0;

            if (candidates == null)
            {
                return null;
            }

            foreach (RoomBoundary candidate
                     in candidates)
            {
                if (candidate == null ||
                    candidate.Diagnostics == null ||
                    !candidate.Diagnostics.IsValid ||
                    !ContainsPoint(candidate, x, y))
                {
                    continue;
                }

                containingCount++;

                double candidateArea =
                    candidate.ContourAreaM2 ??
                    Math.Abs(
                        CalculateSignedArea(
                            candidate.Vertices
                        )
                    );

                if (candidateArea < selectedArea)
                {
                    selectedArea = candidateArea;
                    selected = candidate;
                }
            }

            return selected;
        }

        public static RoomBoundary
            CreatePolyline3dBoundary(
                string sourceHandle,
                string sourceLayer,
                IList<RoomBoundaryVertex> sourceVertices,
                bool originalClosedFlag,
                string polyline3dType,
                string drawingUnits,
                double? metersPerDrawingUnit,
                bool hasMagiCadData)
        {
            double vertexTolerance =
                metersPerDrawingUnit.HasValue &&
                metersPerDrawingUnit.Value > 0
                    ? DefaultVertexToleranceMeters /
                      metersPerDrawingUnit.Value
                    : 1e-8;

            double planarityTolerance =
                metersPerDrawingUnit.HasValue &&
                metersPerDrawingUnit.Value > 0
                    ? Polyline3dPlanarityToleranceMeters /
                      metersPerDrawingUnit.Value
                    : 1e-6;

            double arcChordTolerance =
                metersPerDrawingUnit.HasValue &&
                metersPerDrawingUnit.Value > 0
                    ? DefaultArcChordToleranceMeters /
                      metersPerDrawingUnit.Value
                    : 1e-3;

            RoomBoundary boundary =
                new RoomBoundary
                {
                    SourceHandle = sourceHandle,
                    SourceObjectType = "POLYLINE",
                    SourceLayer = sourceLayer,
                    SourceVertices =
                        CloneVertices(sourceVertices),
                    OriginalClosedFlag =
                        originalClosedFlag,
                    DrawingUnits = drawingUnits,
                    MetersPerDrawingUnit =
                        metersPerDrawingUnit,
                    GeometrySource =
                        "AutoCAD.ModelSpace.Polyline3d",
                    Polyline3dType = polyline3dType,
                    HasMagiCadData = hasMagiCadData
                };

            boundary.Diagnostics.MinimumVertexCount =
                MinimumVertexCount;
            boundary.Diagnostics
                .VertexToleranceDrawingUnits =
                    vertexTolerance;
            boundary.Diagnostics
                .ArcChordToleranceDrawingUnits =
                    arcChordTolerance;

            bool simplePoly =
                string.Equals(
                    polyline3dType,
                    "SimplePoly",
                    StringComparison.Ordinal
                );

            boundary.Diagnostics.IsSupported =
                simplePoly;

            if (!simplePoly)
            {
                boundary.Diagnostics.Messages.Add(
                    "Polyline3d имеет тип '" +
                    polyline3dType +
                    "'; поддерживается только SimplePoly."
                );
            }

            bool repeatedFirstLast =
                sourceVertices != null &&
                sourceVertices.Count > 1 &&
                AreCoincident(
                    sourceVertices[0],
                    sourceVertices[
                        sourceVertices.Count - 1
                    ],
                    vertexTolerance
                );

            boundary.IsClosed =
                originalClosedFlag ||
                repeatedFirstLast;

            if (originalClosedFlag)
            {
                boundary.LogicalClosureMethod =
                    "AutoCAD Closed flag";
            }
            else if (repeatedFirstLast)
            {
                boundary.LogicalClosureMethod =
                    "Repeated first/last vertex";
            }
            else
            {
                boundary.LogicalClosureMethod =
                    "Open";
            }

            if (!boundary.IsClosed)
            {
                boundary.Diagnostics.Messages.Add(
                    "Polyline3d разомкнута: Closed=False " +
                    "и первая/последняя вершины не совпадают."
                );
            }

            double minimumZ =
                double.PositiveInfinity;
            double maximumZ =
                double.NegativeInfinity;

            if (sourceVertices != null)
            {
                foreach (RoomBoundaryVertex vertex
                         in sourceVertices)
                {
                    if (vertex == null)
                    {
                        continue;
                    }

                    minimumZ =
                        Math.Min(minimumZ, vertex.Z);
                    maximumZ =
                        Math.Max(maximumZ, vertex.Z);
                }
            }

            double zDeviation =
                double.IsInfinity(minimumZ) ||
                double.IsInfinity(maximumZ)
                    ? 0
                    : maximumZ - minimumZ;

            boundary.ZDeviationDrawingUnits =
                zDeviation;

            boundary.ZDeviationM =
                metersPerDrawingUnit.HasValue
                    ? (double?)(
                        zDeviation *
                        metersPerDrawingUnit.Value
                    )
                    : null;

            boundary.IsPlanar =
                zDeviation <= planarityTolerance;

            if (!boundary.IsPlanar)
            {
                boundary.Diagnostics.Messages.Add(
                    "Polyline3d непланарна по Z: " +
                    "отклонение " +
                    zDeviation.ToString(
                        "0.###############",
                        System.Globalization
                            .CultureInfo.InvariantCulture
                    ) +
                    " единиц DWG превышает допуск " +
                    planarityTolerance.ToString(
                        "0.###############",
                        System.Globalization
                            .CultureInfo.InvariantCulture
                    ) +
                    "."
                );
            }

            int duplicateVerticesRemoved;

            List<RoomBoundaryVertex> normalized =
                NormalizeVertices(
                    sourceVertices,
                    vertexTolerance,
                    boundary.IsClosed,
                    out duplicateVerticesRemoved
                );

            boundary.Diagnostics
                .DuplicateVerticesRemoved =
                    duplicateVerticesRemoved;

            if (duplicateVerticesRemoved > 0)
            {
                boundary.Diagnostics.Messages.Add(
                    "Удалено повторных вершин: " +
                    duplicateVerticesRemoved +
                    "."
                );
            }

            boundary.OriginalDirection =
                GetDirection(normalized);

            boundary.Vertices =
                NormalizeCounterClockwise(normalized);

            boundary.Direction =
                GetDirection(boundary.Vertices);

            if (boundary.Vertices.Count <
                MinimumVertexCount)
            {
                boundary.Diagnostics.Messages.Add(
                    "После нормализации осталось " +
                    boundary.Vertices.Count +
                    " вершин; требуется минимум " +
                    MinimumVertexCount +
                    "."
                );
            }

            if (boundary.IsClosed &&
                boundary.Vertices.Count >=
                    MinimumVertexCount)
            {
                boundary.Diagnostics
                    .IsSelfIntersecting =
                        HasSelfIntersections(
                            boundary.Vertices,
                            arcChordTolerance,
                            vertexTolerance
                        );

                if (boundary.Diagnostics
                        .IsSelfIntersecting)
                {
                    boundary.Diagnostics.Messages.Add(
                        "Обнаружено самопересечение " +
                        "Polyline3d."
                    );
                }
            }

            if (!metersPerDrawingUnit.HasValue ||
                metersPerDrawingUnit.Value <= 0)
            {
                boundary.Diagnostics.Messages.Add(
                    "Неизвестен коэффициент перевода " +
                    "единиц DWG в метры."
                );
            }

            if (boundary.IsClosed &&
                boundary.Vertices.Count >=
                    MinimumVertexCount)
            {
                double areaDrawingUnits2 =
                    Math.Abs(
                        CalculateSignedArea(
                            boundary.Vertices
                        )
                    );

                double perimeterDrawingUnits =
                    CalculatePerimeter2d(
                        boundary.Vertices,
                        true
                    );

                boundary.ContourAreaDrawingUnits2 =
                    areaDrawingUnits2;
                boundary.PerimeterDrawingUnits =
                    perimeterDrawingUnits;

                if (metersPerDrawingUnit.HasValue)
                {
                    boundary.ContourAreaM2 =
                        areaDrawingUnits2 *
                        metersPerDrawingUnit.Value *
                        metersPerDrawingUnit.Value;

                    boundary.PerimeterM =
                        perimeterDrawingUnits *
                        metersPerDrawingUnit.Value;
                }
            }

            boundary.Diagnostics.IsValid =
                simplePoly &&
                boundary.IsPlanar &&
                boundary.IsClosed &&
                boundary.Vertices.Count >=
                    MinimumVertexCount &&
                !boundary.Diagnostics
                    .IsSelfIntersecting &&
                !string.Equals(
                    boundary.Direction,
                    "Degenerate",
                    StringComparison.Ordinal
                ) &&
                metersPerDrawingUnit.HasValue &&
                boundary.ContourAreaM2.HasValue &&
                boundary.PerimeterM.HasValue;

            return boundary;
        }

        public static double CalculatePerimeter2d(
            IList<RoomBoundaryVertex> vertices,
            bool isClosed)
        {
            if (vertices == null ||
                vertices.Count < 2)
            {
                return 0;
            }

            double result = 0;

            for (int index = 0;
                 index < vertices.Count - 1;
                 index++)
            {
                result +=
                    Distance2d(
                        vertices[index],
                        vertices[index + 1]
                    );
            }

            if (isClosed)
            {
                result +=
                    Distance2d(
                        vertices[vertices.Count - 1],
                        vertices[0]
                    );
            }

            return result;
        }

        public static RoomBoundarySelectionResult
            RankContainingBoundaries(
                IList<RoomBoundary> candidates,
                double x,
                double y,
                double? magiCadAreaM2)
        {
            RoomBoundarySelectionResult result =
                new RoomBoundarySelectionResult();

            if (candidates == null)
            {
                return result;
            }

            foreach (RoomBoundary boundary
                     in candidates)
            {
                if (boundary != null &&
                    boundary.Diagnostics != null &&
                    boundary.Diagnostics.IsValid &&
                    ContainsPoint(boundary, x, y))
                {
                    result.Matches.Add(boundary);
                }
            }

            result.Matches.Sort(
                delegate(
                    RoomBoundary left,
                    RoomBoundary right)
                {
                    int priorityComparison =
                        GetBoundaryPriorityTier(left)
                            .CompareTo(
                                GetBoundaryPriorityTier(
                                    right
                                )
                            );

                    if (priorityComparison != 0)
                    {
                        return priorityComparison;
                    }

                    double leftDifference =
                        GetAbsoluteAreaDifference(
                            left,
                            magiCadAreaM2
                        );

                    double rightDifference =
                        GetAbsoluteAreaDifference(
                            right,
                            magiCadAreaM2
                        );

                    int differenceComparison =
                        leftDifference.CompareTo(
                            rightDifference
                        );

                    if (differenceComparison != 0)
                    {
                        return differenceComparison;
                    }

                    return string.Compare(
                        left.SourceHandle,
                        right.SourceHandle,
                        StringComparison.OrdinalIgnoreCase
                    );
                }
            );

            if (result.Matches.Count == 0)
            {
                return result;
            }

            if (result.Matches.Count > 1 &&
                AreEquivalentCandidates(
                    result.Matches[0],
                    result.Matches[1],
                    magiCadAreaM2
                ))
            {
                result.IsAmbiguous = true;
                return result;
            }

            result.Selected = result.Matches[0];
            return result;
        }

        public static int GetBoundaryPriorityTier(
            RoomBoundary boundary)
        {
            bool magiCadLayer =
                boundary != null &&
                string.Equals(
                    boundary.SourceLayer,
                    "MAGIROOMBORDERS",
                    StringComparison.OrdinalIgnoreCase
                );

            if (magiCadLayer &&
                boundary.HasMagiCadData)
            {
                return 0;
            }

            if (magiCadLayer)
            {
                return 1;
            }

            return 2;
        }

        public static string GetBoundaryPriorityReason(
            RoomBoundary boundary)
        {
            int tier =
                GetBoundaryPriorityTier(boundary);

            if (tier == 0)
            {
                return
                    "MAGIROOMBORDERS with MagiCAD-R";
            }

            if (tier == 1)
            {
                return
                    "MAGIROOMBORDERS without MagiCAD-R";
            }

            return
                "Other containing boundary";
        }

        public static string GetGeometryStatus(
            RoomBoundary boundary)
        {
            if (boundary == null)
            {
                return "missing";
            }

            return string.Equals(
                boundary.GeometrySource,
                "AutoCAD.ModelSpace.Polyline3d",
                StringComparison.Ordinal)
                ? "provisional"
                : "validated";
        }

        public static string GetAreaMatchStatus(
            double? magiCadAreaM2,
            RoomBoundary boundary)
        {
            double? differencePercent =
                CalculateAreaDifferencePercent(
                    magiCadAreaM2,
                    boundary
                );

            if (!differencePercent.HasValue)
            {
                return "unknown";
            }

            return Math.Abs(
                       differencePercent.Value
                   ) >
                   AreaWarningThresholdPercent
                ? "warning"
                : "ok";
        }

        private static bool AreEquivalentCandidates(
            RoomBoundary first,
            RoomBoundary second,
            double? magiCadAreaM2)
        {
            if (GetBoundaryPriorityTier(first) !=
                GetBoundaryPriorityTier(second))
            {
                return false;
            }

            double firstDifference =
                GetAbsoluteAreaDifference(
                    first,
                    magiCadAreaM2
                );

            double secondDifference =
                GetAbsoluteAreaDifference(
                    second,
                    magiCadAreaM2
                );

            return Math.Abs(
                       firstDifference -
                       secondDifference
                   ) <= CandidateTieToleranceM2;
        }

        private static double GetAbsoluteAreaDifference(
            RoomBoundary boundary,
            double? magiCadAreaM2)
        {
            if (boundary == null ||
                !boundary.ContourAreaM2.HasValue ||
                !magiCadAreaM2.HasValue)
            {
                return double.PositiveInfinity;
            }

            return Math.Abs(
                boundary.ContourAreaM2.Value -
                magiCadAreaM2.Value
            );
        }

        public static bool TryGetMetersPerDrawingUnit(
            string drawingUnits,
            out double metersPerDrawingUnit)
        {
            metersPerDrawingUnit = 0;

            if (string.IsNullOrWhiteSpace(
                    drawingUnits))
            {
                return false;
            }

            switch (drawingUnits.Trim()
                        .ToLowerInvariant())
            {
                case "microns":
                    metersPerDrawingUnit = 0.000001;
                    return true;

                case "millimeters":
                case "millimetres":
                case "mm":
                    metersPerDrawingUnit = 0.001;
                    return true;

                case "centimeters":
                case "centimetres":
                case "cm":
                    metersPerDrawingUnit = 0.01;
                    return true;

                case "decimeters":
                case "decimetres":
                case "dm":
                    metersPerDrawingUnit = 0.1;
                    return true;

                case "meters":
                case "metres":
                case "m":
                    metersPerDrawingUnit = 1.0;
                    return true;

                case "kilometers":
                case "kilometres":
                case "km":
                    metersPerDrawingUnit = 1000.0;
                    return true;

                case "inches":
                case "in":
                    metersPerDrawingUnit = 0.0254;
                    return true;

                case "feet":
                case "foot":
                case "ft":
                    metersPerDrawingUnit = 0.3048;
                    return true;

                case "yards":
                case "yd":
                    metersPerDrawingUnit = 0.9144;
                    return true;

                case "miles":
                case "mi":
                    metersPerDrawingUnit = 1609.344;
                    return true;

                default:
                    return false;
            }
        }

        public static double? CalculateAreaDifferenceM2(
            double? magiCadAreaM2,
            RoomBoundary boundary)
        {
            if (!magiCadAreaM2.HasValue ||
                boundary == null ||
                !boundary.ContourAreaM2.HasValue)
            {
                return null;
            }

            return
                boundary.ContourAreaM2.Value -
                magiCadAreaM2.Value;
        }

        public static double?
            CalculateAreaDifferencePercent(
                double? magiCadAreaM2,
                RoomBoundary boundary)
        {
            double? difference =
                CalculateAreaDifferenceM2(
                    magiCadAreaM2,
                    boundary
                );

            if (!difference.HasValue ||
                !magiCadAreaM2.HasValue ||
                Math.Abs(magiCadAreaM2.Value) <= 1e-12)
            {
                return null;
            }

            return
                difference.Value /
                magiCadAreaM2.Value *
                100.0;
        }

        private static void AppendFlattenedSegment(
            List<RoomBoundaryVertex> target,
            RoomBoundaryVertex start,
            RoomBoundaryVertex end,
            double chordTolerance)
        {
            double chord = Distance2d(start, end);

            if (chord <= 1e-12)
            {
                return;
            }

            if (Math.Abs(start.Bulge) <= 1e-12)
            {
                target.Add(ClonePoint(end));
                return;
            }

            double theta =
                4.0 * Math.Atan(start.Bulge);

            double radius =
                chord *
                (1.0 + start.Bulge * start.Bulge) /
                (4.0 * Math.Abs(start.Bulge));

            double midpointX =
                (start.X + end.X) * 0.5;

            double midpointY =
                (start.Y + end.Y) * 0.5;

            double leftX =
                -(end.Y - start.Y) / chord;

            double leftY =
                (end.X - start.X) / chord;

            double centerOffset =
                chord *
                (1.0 - start.Bulge * start.Bulge) /
                (4.0 * start.Bulge);

            double centerX =
                midpointX + leftX * centerOffset;

            double centerY =
                midpointY + leftY * centerOffset;

            double startAngle =
                Math.Atan2(
                    start.Y - centerY,
                    start.X - centerX
                );

            double ratio =
                1.0 -
                Math.Min(
                    chordTolerance,
                    radius
                ) /
                radius;

            ratio =
                Math.Max(-1.0, Math.Min(1.0, ratio));

            double maximumAngle =
                2.0 * Math.Acos(ratio);

            if (maximumAngle <= 1e-9)
            {
                maximumAngle =
                    Math.Abs(theta);
            }

            int segmentCount =
                Math.Max(
                    1,
                    (int)Math.Ceiling(
                        Math.Abs(theta) /
                        maximumAngle
                    )
                );

            segmentCount =
                Math.Min(segmentCount, 4096);

            for (int segmentIndex = 1;
                 segmentIndex <= segmentCount;
                 segmentIndex++)
            {
                if (segmentIndex == segmentCount)
                {
                    target.Add(ClonePoint(end));
                    continue;
                }

                double fraction =
                    (double)segmentIndex /
                    segmentCount;

                double angle =
                    startAngle +
                    theta * fraction;

                target.Add(
                    new RoomBoundaryVertex
                    {
                        X =
                            centerX +
                            radius * Math.Cos(angle),

                        Y =
                            centerY +
                            radius * Math.Sin(angle),

                        Z =
                            start.Z +
                            (end.Z - start.Z) *
                            fraction,

                        Bulge = 0,
                        SegmentType = "Line"
                    }
                );
            }
        }

        private static bool SegmentsIntersect(
            RoomBoundaryVertex firstStart,
            RoomBoundaryVertex firstEnd,
            RoomBoundaryVertex secondStart,
            RoomBoundaryVertex secondEnd,
            double tolerance)
        {
            double firstOrientation =
                Orientation(
                    firstStart,
                    firstEnd,
                    secondStart
                );

            double secondOrientation =
                Orientation(
                    firstStart,
                    firstEnd,
                    secondEnd
                );

            double thirdOrientation =
                Orientation(
                    secondStart,
                    secondEnd,
                    firstStart
                );

            double fourthOrientation =
                Orientation(
                    secondStart,
                    secondEnd,
                    firstEnd
                );

            double effectiveTolerance =
                Math.Max(tolerance, 1e-12);

            if (((firstOrientation >
                  effectiveTolerance &&
                  secondOrientation <
                  -effectiveTolerance) ||
                 (firstOrientation <
                  -effectiveTolerance &&
                  secondOrientation >
                  effectiveTolerance)) &&
                ((thirdOrientation >
                  effectiveTolerance &&
                  fourthOrientation <
                  -effectiveTolerance) ||
                 (thirdOrientation <
                  -effectiveTolerance &&
                  fourthOrientation >
                  effectiveTolerance)))
            {
                return true;
            }

            return
                Math.Abs(firstOrientation) <=
                    effectiveTolerance &&
                PointOnSegment(
                    secondStart.X,
                    secondStart.Y,
                    firstStart,
                    firstEnd,
                    effectiveTolerance
                ) ||
                Math.Abs(secondOrientation) <=
                    effectiveTolerance &&
                PointOnSegment(
                    secondEnd.X,
                    secondEnd.Y,
                    firstStart,
                    firstEnd,
                    effectiveTolerance
                ) ||
                Math.Abs(thirdOrientation) <=
                    effectiveTolerance &&
                PointOnSegment(
                    firstStart.X,
                    firstStart.Y,
                    secondStart,
                    secondEnd,
                    effectiveTolerance
                ) ||
                Math.Abs(fourthOrientation) <=
                    effectiveTolerance &&
                PointOnSegment(
                    firstEnd.X,
                    firstEnd.Y,
                    secondStart,
                    secondEnd,
                    effectiveTolerance
                );
        }

        private static bool PointOnSegment(
            double x,
            double y,
            RoomBoundaryVertex start,
            RoomBoundaryVertex end,
            double tolerance)
        {
            double cross =
                (end.X - start.X) *
                (y - start.Y) -
                (end.Y - start.Y) *
                (x - start.X);

            double length =
                Distance2d(start, end);

            if (Math.Abs(cross) >
                tolerance *
                Math.Max(1.0, length))
            {
                return false;
            }

            return
                x >= Math.Min(start.X, end.X) -
                    tolerance &&
                x <= Math.Max(start.X, end.X) +
                    tolerance &&
                y >= Math.Min(start.Y, end.Y) -
                    tolerance &&
                y <= Math.Max(start.Y, end.Y) +
                    tolerance;
        }

        private static double Orientation(
            RoomBoundaryVertex first,
            RoomBoundaryVertex second,
            RoomBoundaryVertex third)
        {
            return
                (second.X - first.X) *
                (third.Y - first.Y) -
                (second.Y - first.Y) *
                (third.X - first.X);
        }

        private static bool AreAdjacentSegments(
            int firstIndex,
            int secondIndex,
            int segmentCount)
        {
            return
                secondIndex == firstIndex + 1 ||
                firstIndex == 0 &&
                secondIndex == segmentCount - 1;
        }

        private static bool AreCoincident(
            RoomBoundaryVertex first,
            RoomBoundaryVertex second,
            double tolerance)
        {
            double deltaX = first.X - second.X;
            double deltaY = first.Y - second.Y;
            double deltaZ = first.Z - second.Z;

            return
                deltaX * deltaX +
                deltaY * deltaY +
                deltaZ * deltaZ <=
                tolerance * tolerance;
        }

        private static double Distance2d(
            RoomBoundaryVertex first,
            RoomBoundaryVertex second)
        {
            double deltaX = second.X - first.X;
            double deltaY = second.Y - first.Y;

            return Math.Sqrt(
                deltaX * deltaX +
                deltaY * deltaY
            );
        }

        private static string GetSegmentType(
            double bulge)
        {
            return Math.Abs(bulge) <= 1e-12
                ? "Line"
                : "Arc";
        }

        private static List<RoomBoundaryVertex>
            CloneVertices(
                IList<RoomBoundaryVertex> vertices)
        {
            List<RoomBoundaryVertex> result =
                new List<RoomBoundaryVertex>();

            if (vertices == null)
            {
                return result;
            }

            foreach (RoomBoundaryVertex vertex
                     in vertices)
            {
                result.Add(CloneVertex(vertex));
            }

            return result;
        }

        private static RoomBoundaryVertex CloneVertex(
            RoomBoundaryVertex source)
        {
            return new RoomBoundaryVertex
            {
                X = source.X,
                Y = source.Y,
                Z = source.Z,
                Bulge = source.Bulge,
                SegmentType =
                    string.IsNullOrWhiteSpace(
                        source.SegmentType)
                        ? GetSegmentType(source.Bulge)
                        : source.SegmentType
            };
        }

        private static RoomBoundaryVertex ClonePoint(
            RoomBoundaryVertex source)
        {
            return new RoomBoundaryVertex
            {
                X = source.X,
                Y = source.Y,
                Z = source.Z,
                Bulge = 0,
                SegmentType = "Line"
            };
        }
    }
}
