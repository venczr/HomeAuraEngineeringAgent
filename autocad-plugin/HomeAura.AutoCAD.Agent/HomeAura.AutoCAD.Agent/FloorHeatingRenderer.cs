using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;

namespace HomeAura.AutoCAD.Agent
{
    internal sealed class FloorHeatingRenderResult
    {
        public int CircuitGeometryCount { get; set; }
        public int GridEntityCount { get; set; }
        public int PerimeterBandEntityCount { get; set; }
        public int CollectorCount { get; set; }
        public int AnnotationCount { get; set; }
        public int ScheduleEntityCount { get; set; }
        public int RemovedEntityCount { get; set; }
        public bool NoOp { get; set; }
    }

    internal static class FloorHeatingRenderer
    {
        private const string MetadataKey = "HOMEAURA_FH";
        private const string MetadataSchema = "HomeAura.FloorHeating";
        private const string MetadataVersion = "1";

        private static readonly string[] LayerNames =
        {
            "HA_FH_LAYING",
            "HA_FH_INSTALL_GRID",
            "HA_FH_PERIMETER_BAND",
            "HA_FH_PERIMETER_LAYING",
            "HA_FH_FIELD_LAYING",
            "HA_FH_SUPPLY",
            "HA_FH_RETURN",
            "HA_FH_COLLECTOR",
            "HA_FH_ANNOTATIONS",
            "HA_FH_SCHEDULE",
            "HA_FH_EXCLUSION",
            "HA_FH_DIMENSIONS",
            "HA_FH_FLOW"
        };

        public static FloorHeatingRenderResult Apply(
            Database database,
            FloorHeatingPayloadData payload)
        {
            if (database == null)
            {
                throw new ArgumentNullException("database");
            }

            if (payload == null)
            {
                throw new ArgumentNullException("payload");
            }

            using (Transaction transaction =
                   database.TransactionManager.StartTransaction())
            {
                BlockTable blockTable =
                    (BlockTable)transaction.GetObject(
                        database.BlockTableId,
                        OpenMode.ForRead
                    );
                BlockTableRecord modelSpace =
                    (BlockTableRecord)transaction.GetObject(
                        blockTable[BlockTableRecord.ModelSpace],
                        OpenMode.ForWrite
                    );

                List<Entity> owned = FindOwned(
                    transaction,
                    modelSpace,
                    payload
                );

                if (owned.Count > 0 &&
                    owned.All(entity =>
                        ReadMetadata(transaction, entity)
                            .ContainsKey("result_digest") &&
                        string.Equals(
                            ReadMetadata(transaction, entity)["result_digest"],
                            payload.ResultDigest,
                            StringComparison.Ordinal)))
                {
                    transaction.Commit();
                    return new FloorHeatingRenderResult
                    {
                        NoOp = true
                    };
                }

                int removed = 0;
                foreach (Entity entity in owned)
                {
                    entity.UpgradeOpen();
                    entity.Erase();
                    removed++;
                }

                Dictionary<string, ObjectId> layers = EnsureLayers(
                    transaction,
                    database
                );

                FloorHeatingRenderResult result =
                    new FloorHeatingRenderResult
                    {
                        RemovedEntityCount = removed
                    };

                bool dualZone = !string.IsNullOrWhiteSpace(
                    payload.PreferredTopology
                );
                if (dualZone)
                {
                    result.GridEntityCount = AddInstallationGrid(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_INSTALL_GRID"],
                        payload
                    );
                    result.PerimeterBandEntityCount = AddPerimeterBand(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_PERIMETER_BAND"],
                        payload
                    );
                    result.AnnotationCount += AddExclusionZones(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_EXCLUSION"],
                        payload
                    );
                    result.AnnotationCount += AddRoomDimensions(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_DIMENSIONS"],
                        payload
                    );
                }

                foreach (FloorHeatingCircuitData circuit in payload.Circuits)
                {
                    string circuitBase = circuit.NodeId;
                    string layingLayer = dualZone
                        ? (circuit.ZoneRole == "PERIMETER_ZONE"
                            ? "HA_FH_PERIMETER_LAYING"
                            : "HA_FH_FIELD_LAYING")
                        : "HA_FH_LAYING";
                    AddPolyline(
                        database,
                        transaction,
                        modelSpace,
                        circuit.Laying,
                        layers[layingLayer],
                        Metadata(
                            payload,
                            "laying",
                            circuitBase + "|laying",
                            circuit
                        )
                    );
                    AddPolyline(
                        database,
                        transaction,
                        modelSpace,
                        circuit.Supply,
                        layers["HA_FH_SUPPLY"],
                        Metadata(
                            payload,
                            "supply",
                            circuitBase + "|supply",
                            circuit
                        )
                    );
                    if (dualZone)
                    {
                        result.AnnotationCount += AddFlowArrows(
                            database,
                            transaction,
                            modelSpace,
                            layers["HA_FH_FLOW"],
                            circuit,
                            payload
                        );
                    }
                    AddPolyline(
                        database,
                        transaction,
                        modelSpace,
                        circuit.Return,
                        layers["HA_FH_RETURN"],
                        Metadata(
                            payload,
                            "return",
                            circuitBase + "|return",
                            circuit
                        )
                    );
                    result.CircuitGeometryCount += 3;

                    FloorHeatingPointData labelPoint = circuit.Laying[0];
                    if (dualZone && payload.RoomBoundary != null &&
                        payload.RoomBoundary.Points != null)
                    {
                        int minX = payload.RoomBoundary.Points.Min(point => point.X);
                        int maxY = payload.RoomBoundary.Points.Max(point => point.Y);
                        labelPoint = circuit.ZoneRole == "OCCUPIED_FIELD"
                            ? new FloorHeatingPointData { X = minX + 220, Y = maxY + 120 }
                            : new FloorHeatingPointData { X = minX + 220, Y = 60 };
                    }
                    AddText(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_ANNOTATIONS"],
                        new Point3d(labelPoint.X, labelPoint.Y, 0),
                        CircuitLabel(payload, circuit),
                        Metadata(
                            payload,
                            "annotation",
                            circuitBase + "|label",
                            circuit
                        )
                    );
                    result.AnnotationCount++;
                    if (dualZone && circuit.Topology == "COUNTERFLOW_SPIRAL")
                    {
                        FloorHeatingPointData marker = circuit.Laying[circuit.Laying.Count - 1];
                        AddText(
                            database,
                            transaction,
                            modelSpace,
                            layers["HA_FH_ANNOTATIONS"],
                            new Point3d(marker.X + 160, marker.Y - 180, 0),
                            "CF SPIRAL | TRACE TO CENTRE TURN",
                            Metadata(payload, "spiral_annotation", circuitBase + "|spiral-marker", circuit)
                        );
                        result.AnnotationCount++;
                    }
                }

                AddCollector(
                    database,
                    transaction,
                    modelSpace,
                    layers["HA_FH_COLLECTOR"],
                    payload,
                    Metadata(payload, "collector", payload.SystemId + "|collector")
                );
                result.CollectorCount = 1;

                result.ScheduleEntityCount = dualZone
                    ? AddDualSchedule(
                        database,
                        transaction,
                        modelSpace,
                        layers["HA_FH_SCHEDULE"],
                        payload
                    )
                    : AddSchedule(
                    database,
                    transaction,
                    modelSpace,
                    layers["HA_FH_SCHEDULE"],
                    payload
                );

                transaction.Commit();
                return result;
            }
        }

        private static Dictionary<string, ObjectId> EnsureLayers(
            Transaction transaction,
            Database database)
        {
            Dictionary<string, ObjectId> result =
                new Dictionary<string, ObjectId>(StringComparer.Ordinal);
            LayerTable table =
                (LayerTable)transaction.GetObject(
                    database.LayerTableId,
                    OpenMode.ForRead
                );

            foreach (string name in LayerNames)
            {
                ObjectId id;
                if (table.Has(name))
                {
                    id = table[name];
                }
                else
                {
                    table.UpgradeOpen();
                    LayerTableRecord record = new LayerTableRecord
                    {
                        Name = name,
                        Color = Autodesk.AutoCAD.Colors.Color
                            .FromColorIndex(
                                Autodesk.AutoCAD.Colors.ColorMethod.ByAci,
                                LayerColor(name)
                            )
                    };
                    id = table.Add(record);
                    transaction.AddNewlyCreatedDBObject(record, true);
                }

                result.Add(name, id);
            }

            return result;
        }

        private static short LayerColor(string name)
        {
            if (name == "HA_FH_INSTALL_GRID") return 8;
            if (name == "HA_FH_PERIMETER_BAND") return 9;
            if (name == "HA_FH_PERIMETER_LAYING") return 3;
            if (name == "HA_FH_FIELD_LAYING") return 4;
            if (name.EndsWith("LAYING", StringComparison.Ordinal)) return 3;
            if (name.EndsWith("SUPPLY", StringComparison.Ordinal)) return 1;
            if (name.EndsWith("RETURN", StringComparison.Ordinal)) return 5;
            if (name.EndsWith("COLLECTOR", StringComparison.Ordinal)) return 2;
            if (name.EndsWith("ANNOTATIONS", StringComparison.Ordinal)) return 7;
            if (name.EndsWith("EXCLUSION", StringComparison.Ordinal)) return 1;
            if (name.EndsWith("DIMENSIONS", StringComparison.Ordinal)) return 6;
            if (name.EndsWith("FLOW", StringComparison.Ordinal)) return 2;
            return 6;
        }

        private static int AddPerimeterBand(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            if (payload.PerimeterBandPolygon == null ||
                payload.PerimeterBandPolygon.Points == null ||
                payload.PerimeterBandPolygon.Points.Count < 3)
            {
                throw new FloorHeatingPayloadException(
                    "Dual-zone payload must contain a perimeter band polygon."
                );
            }

            AddPolyline(
                database,
                transaction,
                modelSpace,
                payload.PerimeterBandPolygon.Points,
                layerId,
                Metadata(payload, "perimeter_band", "system|perimeter_band")
            );
            return 1;
        }

        private static int AddInstallationGrid(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            if (payload.RoomBoundary == null ||
                payload.RoomBoundary.Points == null ||
                payload.RoomBoundary.Points.Count < 4 ||
                payload.InstallationGridSpacing <= 0)
            {
                throw new FloorHeatingPayloadException(
                    "Dual-zone payload must contain a bounded installation grid."
                );
            }

            int minX = payload.RoomBoundary.Points.Min(point => point.X);
            int maxX = payload.RoomBoundary.Points.Max(point => point.X);
            int minY = payload.RoomBoundary.Points.Min(point => point.Y);
            int maxY = payload.RoomBoundary.Points.Max(point => point.Y);
            int spacing = payload.InstallationGridSpacing;
            int count = 0;

            for (int y = minY; y <= maxY; y += spacing)
            {
                foreach (int[] segment in GridHorizontalSegments(
                    minX,
                    maxX,
                    y,
                    payload.ExclusionZones))
                {
                    AddLine(
                        database,
                        transaction,
                        modelSpace,
                        layerId,
                        new Point3d(segment[0], y, 0),
                        new Point3d(segment[1], y, 0),
                        Metadata(
                            payload,
                            "installation_reference_grid",
                            "grid|h|" + y + "|" + segment[0]
                        )
                    );
                    count++;
                }
            }

            for (int x = minX; x <= maxX; x += spacing)
            {
                foreach (int[] segment in GridVerticalSegments(
                    minY,
                    maxY,
                    x,
                    payload.ExclusionZones))
                {
                    AddLine(
                        database,
                        transaction,
                        modelSpace,
                        layerId,
                        new Point3d(x, segment[0], 0),
                        new Point3d(x, segment[1], 0),
                        Metadata(
                            payload,
                            "installation_reference_grid",
                            "grid|v|" + x + "|" + segment[0]
                        )
                    );
                    count++;
                }
            }

            return count;
        }

        private static int AddExclusionZones(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            int count = 0;
            foreach (FloorHeatingPolygonData exclusion in payload.ExclusionZones ??
                new List<FloorHeatingPolygonData>())
            {
                AddPolyline(
                    database,
                    transaction,
                    modelSpace,
                    exclusion.Points,
                    layerId,
                    Metadata(payload, "exclusion_no_lay", "exclusion|" + count)
                );
                int minX = exclusion.Points.Min(point => point.X);
                int maxX = exclusion.Points.Max(point => point.X);
                int minY = exclusion.Points.Min(point => point.Y);
                int maxY = exclusion.Points.Max(point => point.Y);
                AddText(
                    database,
                    transaction,
                    modelSpace,
                    layerId,
                    new Point3d(minX, maxY + 140, 0),
                    "NO-LAY " + (maxX - minX).ToString(CultureInfo.InvariantCulture) +
                        "x" + (maxY - minY).ToString(CultureInfo.InvariantCulture) + " mm",
                    Metadata(payload, "exclusion_label", "exclusion|label|" + count)
                );
                count += 2;
            }
            return count;
        }

        private static int AddRoomDimensions(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            if (payload.RoomBoundary == null || payload.RoomBoundary.Points == null)
            {
                return 0;
            }
            int minX = payload.RoomBoundary.Points.Min(point => point.X);
            int maxX = payload.RoomBoundary.Points.Max(point => point.X);
            int minY = payload.RoomBoundary.Points.Min(point => point.Y);
            int maxY = payload.RoomBoundary.Points.Max(point => point.Y);
            AddText(database, transaction, modelSpace, layerId,
                new Point3d(minX, maxY + 260, 0),
                "ROOM " + (maxX - minX).ToString(CultureInfo.InvariantCulture) +
                    "x" + (maxY - minY).ToString(CultureInfo.InvariantCulture) + " mm",
                Metadata(payload, "room_dimension", "dimensions|room"));
            AddText(database, transaction, modelSpace, layerId,
                new Point3d(minX, minY - 220, 0),
                "SOUTH EXTERIOR | PERIMETER BAND " +
                    payload.PerimeterBandDepth.ToString(CultureInfo.InvariantCulture) + " mm",
                Metadata(payload, "wall_dimension", "dimensions|south"));
            return 2;
        }

        private static List<int[]> GridHorizontalSegments(
            int minimum,
            int maximum,
            int coordinate,
            List<FloorHeatingPolygonData> exclusions)
        {
            List<int[]> result = new List<int[]> { new[] { minimum, maximum } };
            foreach (FloorHeatingPolygonData exclusion in exclusions ??
                new List<FloorHeatingPolygonData>())
            {
                int low = exclusion.Points.Min(point => point.X);
                int high = exclusion.Points.Max(point => point.X);
                int bottom = exclusion.Points.Min(point => point.Y);
                int top = exclusion.Points.Max(point => point.Y);
                if (coordinate < bottom || coordinate > top) continue;
                result = SubtractSegments(result, low, high);
            }
            return result;
        }

        private static List<int[]> GridVerticalSegments(
            int minimum,
            int maximum,
            int coordinate,
            List<FloorHeatingPolygonData> exclusions)
        {
            List<int[]> result = new List<int[]> { new[] { minimum, maximum } };
            foreach (FloorHeatingPolygonData exclusion in exclusions ??
                new List<FloorHeatingPolygonData>())
            {
                int low = exclusion.Points.Min(point => point.Y);
                int high = exclusion.Points.Max(point => point.Y);
                int left = exclusion.Points.Min(point => point.X);
                int right = exclusion.Points.Max(point => point.X);
                if (coordinate < left || coordinate > right) continue;
                result = SubtractSegments(result, low, high);
            }
            return result;
        }

        private static List<int[]> SubtractSegments(
            List<int[]> segments,
            int cutLow,
            int cutHigh)
        {
            List<int[]> result = new List<int[]>();
            foreach (int[] segment in segments)
            {
                if (cutHigh <= segment[0] || cutLow >= segment[1])
                {
                    result.Add(segment);
                    continue;
                }
                if (segment[0] < cutLow)
                {
                    result.Add(new[] { segment[0], cutLow });
                }
                if (cutHigh < segment[1])
                {
                    result.Add(new[] { cutHigh, segment[1] });
                }
            }
            return result.Where(segment => segment[1] > segment[0]).ToList();
        }

        private static void AddPolyline(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            List<FloorHeatingPointData> points,
            ObjectId layerId,
            Dictionary<string, string> metadata)
        {
            if (points.Count < 2)
            {
                throw new FloorHeatingPayloadException(
                    "Cannot render a polyline with fewer than two points."
                );
            }

            Polyline polyline = new Polyline();
            polyline.SetDatabaseDefaults(database);
            polyline.LayerId = layerId;
            for (int index = 0; index < points.Count; index++)
            {
                polyline.AddVertexAt(
                    index,
                    new Point2d(points[index].X, points[index].Y),
                    0,
                    0,
                    0
                );
            }

            string turnRadiusText;
            int turnRadius;
            if (metadata.TryGetValue("turn_radius_mm", out turnRadiusText) &&
                int.TryParse(turnRadiusText, NumberStyles.Integer, CultureInfo.InvariantCulture, out turnRadius) &&
                turnRadius > 0)
            {
                for (int index = 1; index < points.Count - 1; index++)
                {
                    double cross =
                        (points[index].X - points[index - 1].X) *
                            (points[index + 1].Y - points[index].Y) -
                        (points[index].Y - points[index - 1].Y) *
                            (points[index + 1].X - points[index].X);
                    if (Math.Abs(cross) > 0.01)
                    {
                        double incoming = Math.Sqrt(
                            Math.Pow(points[index].X - points[index - 1].X, 2) +
                            Math.Pow(points[index].Y - points[index - 1].Y, 2));
                        double outgoing = Math.Sqrt(
                            Math.Pow(points[index + 1].X - points[index].X, 2) +
                            Math.Pow(points[index + 1].Y - points[index].Y, 2));
                        double bulgeMagnitude = Math.Min(
                            0.06,
                            turnRadius / (8.0 * Math.Max(1.0, Math.Min(incoming, outgoing)))
                        );
                        polyline.SetBulgeAt(
                            index,
                            Math.Sign(cross) * bulgeMagnitude
                        );
                    }
                }
            }

            AppendEntity(
                transaction,
                modelSpace,
                polyline,
                metadata
            );
        }

        private static void AddCollector(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload,
            Dictionary<string, string> metadata)
        {
            Point3d center = new Point3d(
                payload.CollectorPoint.X,
                payload.CollectorPoint.Y,
                0
            );
            Circle circle = new Circle(center, Vector3d.ZAxis, 180);
            circle.SetDatabaseDefaults(database);
            circle.LayerId = layerId;
            AppendEntity(transaction, modelSpace, circle, metadata);
            AddLine(database, transaction, modelSpace, layerId,
                new Point3d(center.X - 320, center.Y - 260, 0),
                new Point3d(center.X + 320, center.Y - 260, 0),
                Metadata(payload, "collector_manifold", payload.SystemId + "|manifold"));
            AddLine(database, transaction, modelSpace, layerId,
                new Point3d(center.X - 320, center.Y + 260, 0),
                new Point3d(center.X + 320, center.Y + 260, 0),
                Metadata(payload, "collector_manifold", payload.SystemId + "|manifold|return"));
            for (int index = 0; index < payload.Circuits.Count; index++)
            {
                double y = center.Y - 160 + index * 320;
                AddLine(database, transaction, modelSpace, layerId,
                new Point3d(center.X + 320, y, 0),
                new Point3d(center.X + 560, y, 0),
                Metadata(payload, "collector_port", payload.SystemId + "|port|" + (index + 1)));
            AddText(database, transaction, modelSpace, layerId,
                    new Point3d(center.X + 640, y - 45, 0),
                    "P" + (index + 1).ToString(CultureInfo.InvariantCulture) + " " +
                        ShortCircuitId(payload.Circuits[index].CircuitId),
                    Metadata(payload, "collector_port_label", payload.SystemId + "|port-label|" + (index + 1)));
            }
            AddText(database, transaction, modelSpace, layerId,
                new Point3d(center.X - 520, center.Y - 520, 0),
                "COLLECTOR | " + payload.CollectorPortCount.ToString(CultureInfo.InvariantCulture) + " PORTS",
                Metadata(payload, "collector_label", payload.SystemId + "|label"));
        }

        private static int AddFlowArrows(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingCircuitData circuit,
            FloorHeatingPayloadData payload)
        {
            int count = 0;
            count += AddArrowForPath(database, transaction, modelSpace, layerId,
                circuit.Laying, payload, circuit.NodeId + "|laying-arrow");
            count += AddArrowForPath(database, transaction, modelSpace, layerId,
                circuit.Supply, payload, circuit.NodeId + "|supply-arrow");
            count += AddArrowForPath(database, transaction, modelSpace, layerId,
                circuit.Return, payload, circuit.NodeId + "|return-arrow");
            return count;
        }

        private static int AddArrowForPath(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            List<FloorHeatingPointData> path,
            FloorHeatingPayloadData payload,
            string entityBase)
        {
            if (path == null || path.Count < 2) return 0;
            FloorHeatingPointData first = path[0];
            FloorHeatingPointData second = path[1];
            double dx = second.X - first.X;
            double dy = second.Y - first.Y;
            double length = Math.Sqrt(dx * dx + dy * dy);
            if (length < 1) return 0;
            double ux = dx / length;
            double uy = dy / length;
            double px = -uy;
            double py = ux;
            double mx = first.X + dx * 0.55;
            double my = first.Y + dy * 0.55;
            Point3d tip = new Point3d(mx + ux * 90, my + uy * 90, 0);
            Point3d left = new Point3d(mx - ux * 70 + px * 70, my - uy * 70 + py * 70, 0);
            Point3d right = new Point3d(mx - ux * 70 - px * 70, my - uy * 70 - py * 70, 0);
            AddLine(database, transaction, modelSpace, layerId, left, tip,
                Metadata(payload, "flow_arrow", entityBase + "|left"));
            AddLine(database, transaction, modelSpace, layerId, right, tip,
                Metadata(payload, "flow_arrow", entityBase + "|right"));
            return 2;
        }

        private static void AddText(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            Point3d position,
            string text,
            Dictionary<string, string> metadata)
        {
            DBText entity = new DBText
            {
                Position = position,
                Height = 120,
                TextString = text
            };
            entity.SetDatabaseDefaults(database);
            entity.LayerId = layerId;
            AppendEntity(transaction, modelSpace, entity, metadata);
        }

        private static int AddSchedule(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            int maximumX = payload.Circuits
                .SelectMany(item => item.Points)
                .Max(item => item.X);
            int maximumY = payload.Circuits
                .SelectMany(item => item.Points)
                .Max(item => item.Y);
            double left = maximumX + 1000;
            double top = maximumY;
            double rowHeight = 300;
            double[] widths =
            {
                850, 1500, 2400, 1300, 1300, 1300,
                1300, 1200, 1700
            };
            string[] headings =
            {
                "#", "Room", "Circuit", "Laying", "Supply",
                "Return", "Total", "Spacing", "Max"
            };
            List<string[]> rows = new List<string[]> { headings };
            for (int index = 0; index < payload.Circuits.Count; index++)
            {
                FloorHeatingCircuitData circuit = payload.Circuits[index];
                rows.Add(
                    new[]
                    {
                        (index + 1).ToString(CultureInfo.InvariantCulture),
                        payload.RoomId,
                        ShortCircuitId(circuit.CircuitId),
                        circuit.LayingLength.ToString(CultureInfo.InvariantCulture),
                        circuit.SupplyLength.ToString(CultureInfo.InvariantCulture),
                        circuit.ReturnLength.ToString(CultureInfo.InvariantCulture),
                        circuit.TotalLength.ToString(CultureInfo.InvariantCulture),
                        circuit.Spacing.ToString(CultureInfo.InvariantCulture),
                        circuit.MaximumStatus
                    }
                );
            }

            rows.Add(
                new[]
                {
                    "", "", "PIPE TOTAL",
                    "", "", "",
                    payload.TotalPipeLength.ToString(CultureInfo.InvariantCulture),
                    "", payload.ProcurementReserveStatus
                }
            );
            rows.Add(
                new[]
                {
                    "", "", "COLLECTOR PORTS",
                    payload.CollectorPortCount.ToString(CultureInfo.InvariantCulture),
                    "", "", "", "", payload.CommercialSelection
                }
            );

            int count = 0;
            double totalWidth = widths.Sum();
            for (int row = 0; row <= rows.Count; row++)
            {
                double y = top - row * rowHeight;
                AddLine(
                    database,
                    transaction,
                    modelSpace,
                    layerId,
                    new Point3d(left, y, 0),
                    new Point3d(left + totalWidth, y, 0),
                    Metadata(payload, "schedule_line", "schedule|h|" + row)
                );
                count++;
            }

            double x = left;
            for (int column = 0; column <= widths.Length; column++)
            {
                AddLine(
                    database,
                    transaction,
                    modelSpace,
                    layerId,
                    new Point3d(x, top, 0),
                    new Point3d(x, top - rows.Count * rowHeight, 0),
                    Metadata(payload, "schedule_line", "schedule|v|" + column)
                );
                count++;
                if (column < widths.Length) x += widths[column];
            }

            for (int row = 0; row < rows.Count; row++)
            {
                x = left;
                for (int column = 0; column < widths.Length; column++)
                {
                    AddText(
                        database,
                        transaction,
                        modelSpace,
                        layerId,
                        new Point3d(x + 40, top - row * rowHeight - 180, 0),
                        rows[row][column],
                        Metadata(
                            payload,
                            "schedule_text",
                            "schedule|text|" + row + "|" + column
                        )
                    );
                    count++;
                    x += widths[column];
                }
            }

            AddText(
                database,
                transaction,
                modelSpace,
                layerId,
                new Point3d(left, top + 300, 0),
                "FLOOR HEATING | " + payload.ProjectId + " | " + payload.RoomId,
                Metadata(payload, "schedule_text", "schedule|title")
            );
            count++;
            return count;
        }

        private static int AddDualSchedule(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            FloorHeatingPayloadData payload)
        {
            int maximumX = payload.Circuits
                .SelectMany(item => item.Points)
                .Max(item => item.X);
            int maximumY = payload.Circuits
                .SelectMany(item => item.Points)
                .Max(item => item.Y);
            double left = maximumX + 1000;
            double top = maximumY;
            double rowHeight = 300;
            double[] widths =
            {
                500, 1200, 1500, 1400, 600, 850, 850,
                750, 750, 850, 850, 1500
            };
            string[] headings =
            {
                "#", "Circuit", "Role", "Topology", "S",
                "P-Lay", "Field", "Sup", "Ret", "Total", "Diff",
                "Max"
            };
            List<string[]> rows = new List<string[]> { headings };
            for (int index = 0; index < payload.Circuits.Count; index++)
            {
                FloorHeatingCircuitData circuit = payload.Circuits[index];
                rows.Add(
                    new[]
                    {
                        (index + 1).ToString(CultureInfo.InvariantCulture),
                        ShortCircuitId(circuit.CircuitId),
                        DisplayRole(circuit.ZoneRole),
                        DisplayTopology(circuit.Topology),
                        circuit.NominalSpacing.ToString(CultureInfo.InvariantCulture),
                        circuit.PerimeterLayingLength.ToString(CultureInfo.InvariantCulture),
                        circuit.FieldLayingLength.ToString(CultureInfo.InvariantCulture),
                        circuit.SupplyLength.ToString(CultureInfo.InvariantCulture),
                        circuit.ReturnLength.ToString(CultureInfo.InvariantCulture),
                        circuit.TotalLength.ToString(CultureInfo.InvariantCulture),
                        OtherCircuitDifference(payload, index).ToString(CultureInfo.InvariantCulture),
                        circuit.MaximumStatus
                    }
                );
            }

            rows.Add(new[]
            {
                "", "PIPE TOTAL", "", "", "", "", "", "", "",
                payload.TotalPipeLength.ToString(CultureInfo.InvariantCulture), "", ""
            });
            rows.Add(new[]
            {
                "", "PORTS", payload.CollectorPortCount.ToString(CultureInfo.InvariantCulture),
                "", "", "", "", "", "", "", "", "2 PORTS"
            });
            rows.Add(new[]
            {
                "", "BAND mm", payload.PerimeterBandDepth.ToString(CultureInfo.InvariantCulture),
                "GRID mm", payload.InstallationGridSpacing.ToString(CultureInfo.InvariantCulture),
                "WALL", "SOUTH", "", "", "", "", ""
            });
            rows.Add(new[]
            {
                "", "LIMITS", "MIN mm", "40000", "MAX mm",
                payload.MaximumCircuitLength.ToString(CultureInfo.InvariantCulture),
                "", "", "", "", "", ""
            });
            rows.Add(new[]
            {
                "", "STATUS", "HEAT LOSS", "NOT CALC", "", "", "", "", "", "", "", ""
            });
            rows.Add(new[]
            {
                "", "STATUS", "HYDRAULIC", "NOT CALC", "", "", "", "", "", "", "", ""
            });
            rows.Add(new[]
            {
                "", "STATUS", "PROCURE", "UNRESOLVED", "", "", "", "", "", "", "", ""
            });

            int count = 0;
            double totalWidth = widths.Sum();
            for (int row = 0; row <= rows.Count; row++)
            {
                double y = top - row * rowHeight;
                AddLine(
                    database,
                    transaction,
                    modelSpace,
                    layerId,
                    new Point3d(left, y, 0),
                    new Point3d(left + totalWidth, y, 0),
                    Metadata(payload, "schedule_line", "dual-schedule|h|" + row)
                );
                count++;
            }

            double x = left;
            for (int column = 0; column <= widths.Length; column++)
            {
                AddLine(
                    database,
                    transaction,
                    modelSpace,
                    layerId,
                    new Point3d(x, top, 0),
                    new Point3d(x, top - rows.Count * rowHeight, 0),
                    Metadata(payload, "schedule_line", "dual-schedule|v|" + column)
                );
                count++;
                if (column < widths.Length) x += widths[column];
            }

            for (int row = 0; row < rows.Count; row++)
            {
                x = left;
                for (int column = 0; column < widths.Length; column++)
                {
                    AddText(
                        database,
                        transaction,
                        modelSpace,
                        layerId,
                        new Point3d(x + 35, top - row * rowHeight - 180, 0),
                        rows[row][column],
                        Metadata(
                            payload,
                            "schedule_text",
                            "dual-schedule|text|" + row + "|" + column
                        )
                    );
                    count++;
                    x += widths[column];
                }
            }

            AddText(
                database,
                transaction,
                modelSpace,
                layerId,
                new Point3d(left, top + 300, 0),
                "UFH | UNITS mm | GRID 100 | PERIM 100 | FIELD 200 | " +
                    payload.ProjectId + " | " + payload.RoomId,
                Metadata(payload, "schedule_text", "dual-schedule|title")
            );
            count++;
            return count;
        }

        private static int OtherCircuitDifference(
            FloorHeatingPayloadData payload,
            int circuitIndex)
        {
            if (payload.Circuits.Count != 2) return 0;
            return Math.Abs(
                payload.Circuits[circuitIndex].TotalLength -
                payload.Circuits[1 - circuitIndex].TotalLength
            );
        }

        private static void AddLine(
            Database database,
            Transaction transaction,
            BlockTableRecord modelSpace,
            ObjectId layerId,
            Point3d start,
            Point3d end,
            Dictionary<string, string> metadata)
        {
            Line line = new Line(start, end);
            line.SetDatabaseDefaults(database);
            line.LayerId = layerId;
            AppendEntity(transaction, modelSpace, line, metadata);
        }

        private static ObjectId AppendEntity(
            Transaction transaction,
            BlockTableRecord modelSpace,
            Entity entity,
            Dictionary<string, string> metadata)
        {
            ObjectId id = modelSpace.AppendEntity(entity);
            transaction.AddNewlyCreatedDBObject(entity, true);
            WriteMetadata(transaction, entity, metadata);
            return id;
        }

        private static Dictionary<string, string> Metadata(
            FloorHeatingPayloadData payload,
            string role,
            string entityId)
        {
            return Metadata(payload, role, entityId, null);
        }

        private static Dictionary<string, string> Metadata(
            FloorHeatingPayloadData payload,
            string role,
            string entityId,
            FloorHeatingCircuitData circuit)
        {
            Dictionary<string, string> result =
                new Dictionary<string, string>(StringComparer.Ordinal)
            {
                { "schema", MetadataSchema },
                { "metadata_schema_version", MetadataVersion },
                { "role", role },
                { "project_id", payload.ProjectId },
                { "room_id", payload.RoomId },
                { "result_digest", payload.ResultDigest },
                { "source_digest", payload.ProjectionDigest },
                { "graph_id", payload.GraphId },
                { "generation", payload.Generation },
                { "entity_id", entityId }
            };
            if (circuit != null &&
                !string.IsNullOrWhiteSpace(payload.PreferredTopology))
            {
                result["zone_role"] = circuit.ZoneRole ?? "";
                result["topology"] = circuit.Topology ?? "";
                result["nominal_spacing_mm"] = circuit.NominalSpacing
                    .ToString(CultureInfo.InvariantCulture);
                result["perimeter_band_depth_mm"] = payload.PerimeterBandDepth
                    .ToString(CultureInfo.InvariantCulture);
                result["installation_grid_spacing_mm"] = payload.InstallationGridSpacing
                    .ToString(CultureInfo.InvariantCulture);
                result["turn_radius_mm"] = payload.TurnRadius
                    .ToString(CultureInfo.InvariantCulture);
            }
            return result;
        }

        private static void WriteMetadata(
            Transaction transaction,
            Entity entity,
            Dictionary<string, string> metadata)
        {
            entity.UpgradeOpen();
            entity.CreateExtensionDictionary();
            DBDictionary dictionary =
                (DBDictionary)transaction.GetObject(
                    entity.ExtensionDictionary,
                    OpenMode.ForWrite
                );
            if (dictionary.Contains(MetadataKey))
            {
                ObjectId oldId = dictionary.GetAt(MetadataKey);
                DBObject old = transaction.GetObject(oldId, OpenMode.ForWrite);
                old.Erase();
            }

            Xrecord record = new Xrecord
            {
                Data = new ResultBuffer(
                    metadata.Select(item =>
                        new TypedValue(
                            (int)DxfCode.Text,
                            item.Key + "=" + item.Value
                        )
                    ).ToArray()
                )
            };
            dictionary.SetAt(MetadataKey, record);
            transaction.AddNewlyCreatedDBObject(record, true);
        }

        private static List<Entity> FindOwned(
            Transaction transaction,
            BlockTableRecord modelSpace,
            FloorHeatingPayloadData payload)
        {
            List<Entity> result = new List<Entity>();
            foreach (ObjectId objectId in modelSpace)
            {
                Entity entity = transaction.GetObject(
                    objectId,
                    OpenMode.ForRead,
                    false
                ) as Entity;
                if (entity == null) continue;

                Dictionary<string, string> metadata =
                    ReadMetadata(transaction, entity);
                string value;
                if (!metadata.TryGetValue("schema", out value) ||
                    !string.Equals(value, MetadataSchema, StringComparison.Ordinal) ||
                    !metadata.TryGetValue("project_id", out value) ||
                    !string.Equals(value, payload.ProjectId, StringComparison.Ordinal) ||
                    !metadata.TryGetValue("room_id", out value) ||
                    !string.Equals(value, payload.RoomId, StringComparison.Ordinal))
                {
                    continue;
                }

                result.Add(entity);
            }

            return result;
        }

        private static Dictionary<string, string> ReadMetadata(
            Transaction transaction,
            Entity entity)
        {
            Dictionary<string, string> result =
                new Dictionary<string, string>(StringComparer.Ordinal);
            if (entity.ExtensionDictionary.IsNull) return result;

            DBDictionary dictionary = transaction.GetObject(
                entity.ExtensionDictionary,
                OpenMode.ForRead,
                false
            ) as DBDictionary;
            if (dictionary == null || !dictionary.Contains(MetadataKey))
            {
                return result;
            }

            Xrecord record = transaction.GetObject(
                dictionary.GetAt(MetadataKey),
                OpenMode.ForRead,
                false
            ) as Xrecord;
            if (record == null || record.Data == null) return result;

            foreach (TypedValue value in record.Data)
            {
                string text = value.Value as string;
                if (string.IsNullOrEmpty(text)) continue;
                int separator = text.IndexOf('=');
                if (separator <= 0) continue;
                result[text.Substring(0, separator)] =
                    text.Substring(separator + 1);
            }

            return result;
        }

        private static string CircuitLabel(
            FloorHeatingPayloadData payload,
            FloorHeatingCircuitData circuit)
        {
            if (!string.IsNullOrWhiteSpace(payload.PreferredTopology))
            {
                return "UFH " + ShortCircuitId(circuit.CircuitId) +
                    " | " + DisplayRole(circuit.ZoneRole) + " | " +
                    DisplayTopology(circuit.Topology) +
                    " | S" + circuit.NominalSpacing.ToString(CultureInfo.InvariantCulture) +
                    " | T" + circuit.TotalLength.ToString(CultureInfo.InvariantCulture);
            }
            return "FH " + circuit.CircuitId +
                " | S" + circuit.Spacing.ToString(CultureInfo.InvariantCulture) +
                " | L" + circuit.LayingLength.ToString(CultureInfo.InvariantCulture) +
                " | Sup" + circuit.SupplyLength.ToString(CultureInfo.InvariantCulture) +
                " | Ret" + circuit.ReturnLength.ToString(CultureInfo.InvariantCulture) +
                " | T" + circuit.TotalLength.ToString(CultureInfo.InvariantCulture) +
      " | " + circuit.MaximumStatus;
        }

        private static string DisplayRole(string role)
        {
            return role == "PERIMETER_ZONE"
                ? "PERIMETER"
                : role == "OCCUPIED_FIELD" ? "FIELD" : (role ?? "-");
        }

        private static string DisplayTopology(string topology)
        {
            return topology == "COUNTERFLOW_SPIRAL"
                ? "CF_SPIRAL"
                : (topology ?? "-");
        }

        private static string WallLabel(FloorHeatingWallData wall)
        {
            if (wall == null || string.IsNullOrWhiteSpace(wall.Reference)) return "-";
            int separator = wall.Reference.LastIndexOf('-');
            return separator >= 0 && separator < wall.Reference.Length - 1
                ? wall.Reference.Substring(separator + 1).ToUpperInvariant()
                : wall.Reference;
        }

        private static string ShortCircuitId(string circuitId)
        {
            int separator = circuitId.LastIndexOf('/');
            return separator >= 0 && separator < circuitId.Length - 1
                ? circuitId.Substring(separator + 1)
                : circuitId;
        }
    }
}
