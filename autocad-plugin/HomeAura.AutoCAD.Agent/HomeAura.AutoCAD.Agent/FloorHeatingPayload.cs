using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Web.Script.Serialization;

namespace HomeAura.AutoCAD.Agent
{
    internal sealed class FloorHeatingPayloadException : Exception
    {
        public FloorHeatingPayloadException(string message)
            : base(message)
        {
        }
    }

    internal sealed class FloorHeatingPointData
    {
        public int X { get; set; }
        public int Y { get; set; }
    }

    internal sealed class FloorHeatingPolygonData
    {
        public List<FloorHeatingPointData> Points { get; set; }
    }

    internal sealed class FloorHeatingWallData
    {
        public string Reference { get; set; }
        public FloorHeatingPointData Start { get; set; }
        public FloorHeatingPointData End { get; set; }
    }

    internal sealed class FloorHeatingCircuitData
    {
        public string CircuitId { get; set; }
        public string NodeId { get; set; }
        public List<FloorHeatingPointData> Points { get; set; }
        public List<FloorHeatingPointData> Supply { get; set; }
        public List<FloorHeatingPointData> Return { get; set; }
        public List<FloorHeatingPointData> Laying { get; set; }
        public int LayingLength { get; set; }
        public int SupplyLength { get; set; }
        public int ReturnLength { get; set; }
        public int TotalLength { get; set; }
        public int Spacing { get; set; }
        public string MaximumStatus { get; set; }
        public string ZoneRole { get; set; }
        public string Topology { get; set; }
        public int NominalSpacing { get; set; }
        public int PerimeterLayingLength { get; set; }
        public int FieldLayingLength { get; set; }
        public List<string> ExteriorWallReferences { get; set; }
    }

    internal sealed class FloorHeatingPayloadData
    {
        public string ProjectId { get; set; }
        public string RoomId { get; set; }
        public string ResultDigest { get; set; }
        public string ProjectionDigest { get; set; }
        public string GraphId { get; set; }
        public string SystemId { get; set; }
        public FloorHeatingPointData CollectorPoint { get; set; }
        public int CollectorPortCount { get; set; }
        public int TotalPipeLength { get; set; }
        public int MaximumCircuitLength { get; set; }
        public string ProcurementReserveStatus { get; set; }
        public string CommercialSelection { get; set; }
        public List<FloorHeatingCircuitData> Circuits { get; set; }
        public string Generation { get; set; }
        public int FieldSpacing { get; set; }
        public int PerimeterSpacing { get; set; }
        public int PerimeterBandDepth { get; set; }
        public int TurnRadius { get; set; }
        public int InstallationGridSpacing { get; set; }
        public string PreferredTopology { get; set; }
        public FloorHeatingPolygonData RoomBoundary { get; set; }
        public List<FloorHeatingPolygonData> ExclusionZones { get; set; }
        public FloorHeatingPolygonData PerimeterBandPolygon { get; set; }
        public string PerimeterBandDigest { get; set; }
        public List<FloorHeatingWallData> ExteriorWallSegments { get; set; }
    }

    internal static class FloorHeatingPayloadReader
    {
        private const int MaxPayloadBytes = 2 * 1024 * 1024;

        private static readonly HashSet<string> RootKeys =
            new HashSet<string>(StringComparer.Ordinal)
            {
                "schema_version", "preview_id", "project_id",
                "room_id", "status", "system_graph",
                "specification", "diagnostics", "source_result_digest",
                "projection_digest"
            };

        public static FloorHeatingPayloadData Load(
            string path,
            string trustedRoot)
        {
            string fullPath = ValidateContainedPath(path, trustedRoot);
            FileInfo file = new FileInfo(fullPath);

            if (!file.Exists)
            {
                throw new FloorHeatingPayloadException(
                    "Payload file does not exist."
                );
            }

            if (file.Length > MaxPayloadBytes)
            {
                throw new FloorHeatingPayloadException(
                    "Payload file exceeds the bounded size."
                );
            }

            string json = File.ReadAllText(
                fullPath,
                new System.Text.UTF8Encoding(false, true)
            );

            JavaScriptSerializer serializer =
                new JavaScriptSerializer
                {
                    MaxJsonLength = MaxPayloadBytes,
                    RecursionLimit = 64
                };

            object parsed;
            try
            {
                parsed = serializer.DeserializeObject(json);
            }
            catch (Exception exception)
            {
                throw new FloorHeatingPayloadException(
                    "Payload is not valid strict JSON: " +
                    exception.GetType().Name
                );
            }

            IDictionary<string, object> root =
                RequireDictionary(parsed, "root");
            RequireExactKeys(root, RootKeys, "root");

            RequireString(root, "schema_version", "1.0");
            RequireString(root, "status", "ok");

            IDictionary<string, object> graph =
                RequireDictionary(root["system_graph"], "system_graph");
            IDictionary<string, object> specification =
                RequireDictionary(root["specification"], "specification");

            string projectId = RequireText(root, "project_id");
            string roomId = RequireText(root, "room_id");
            string resultDigest = RequireDigest(
                root,
                "source_result_digest"
            );
            string projectionDigest = RequireDigest(
                root,
                "projection_digest"
            );

            string graphId = RequireText(graph, "graph_id");
            string systemId = RequireText(graph, "system_id");
            if (!string.Equals(
                    RequireText(graph, "project_id"),
                    projectId,
                    StringComparison.Ordinal) ||
                !string.Equals(
                    RequireText(graph, "room_id"),
                    roomId,
                    StringComparison.Ordinal) ||
                !string.Equals(
                    RequireString(graph, "status", "ok"),
                    "ok",
                    StringComparison.Ordinal))
            {
                throw new FloorHeatingPayloadException(
                    "Graph identity or status does not match the preview."
                );
            }

            IList<object> nodes = RequireList(graph, "nodes");
            IDictionary<string, object> collectorAttributes = null;
            IDictionary<string, object> systemAttributes = null;
            List<FloorHeatingCircuitData> circuits =
                new List<FloorHeatingCircuitData>();
            foreach (object nodeValue in nodes)
            {
                IDictionary<string, object> node =
                    RequireDictionary(nodeValue, "graph node");
                string kind = RequireText(node, "kind");
                IDictionary<string, object> attributes =
                    RequireDictionary(node["attributes"], "node attributes");

                if (kind == "floor_heating_system")
                {
                    systemAttributes = attributes;
                    continue;
                }

                if (kind == "collector")
                {
                    collectorAttributes = attributes;
                    continue;
                }

                if (kind != "circuit")
                {
                    continue;
                }

                FloorHeatingCircuitData circuit =
                    ReadCircuit(node, attributes, resultDigest);
                circuits.Add(circuit);
            }

            if (collectorAttributes == null)
            {
                throw new FloorHeatingPayloadException(
                    "Collector node is missing."
                );
            }

            if (systemAttributes == null)
            {
                throw new FloorHeatingPayloadException(
                    "Floor-heating system node is missing."
                );
            }

            FloorHeatingPointData collectorPoint =
                ReadPoint(collectorAttributes, "collector_point_mm");
            int collectorPorts = RequireInt(
                collectorAttributes,
                "required_port_count"
            );

            IDictionary<string, object> pipeRequirement =
                RequireDictionary(
                    RequireDictionary(
                        specification,
                        "specification"
                    )["pipe_requirement"],
                    "pipe_requirement"
                );
            IDictionary<string, object> collectorRequirement =
                RequireDictionary(
                    specification["collector_requirement"],
                    "collector_requirement"
                );
            int totalPipeLength = RequireInt(
                pipeRequirement,
                "calculated_total_pipe_length_mm"
            );
            int declaredPorts = RequireInt(
                collectorRequirement,
                "required_port_count"
            );
            string reserve = RequireText(
                pipeRequirement,
                "procurement_reserve_status"
            ).ToUpperInvariant();
            if (reserve != "NOT_APPLIED" ||
                !string.Equals(
                    RequireText(
                        collectorRequirement,
                        "catalog_selection"
                    ),
                    "unresolved",
                    StringComparison.OrdinalIgnoreCase
                ) ||
                collectorPorts != declaredPorts ||
                collectorPorts != circuits.Count)
            {
                throw new FloorHeatingPayloadException(
                    "Specification and graph collector quantities disagree."
                );
            }

            if (totalPipeLength != circuits.Sum(item => item.TotalLength))
            {
                throw new FloorHeatingPayloadException(
                    "Specification total pipe length disagrees with circuits."
                );
            }

            return new FloorHeatingPayloadData
            {
                ProjectId = projectId,
                RoomId = roomId,
                ResultDigest = resultDigest,
                ProjectionDigest = projectionDigest,
                GraphId = graphId,
                SystemId = systemId,
                CollectorPoint = collectorPoint,
                CollectorPortCount = collectorPorts,
                TotalPipeLength = totalPipeLength,
                MaximumCircuitLength = RequireOptionalInt(systemAttributes, "maximum_circuit_length_mm"),
                ProcurementReserveStatus = reserve,
                CommercialSelection = "UNRESOLVED",
                Circuits = circuits
                    .OrderBy(item => item.CircuitId, StringComparer.Ordinal)
                    .ToList(),
                Generation = RequireOptionalText(systemAttributes, "preferred_topology") != null
                    ? "block55/" + resultDigest
                    : "block54/" + resultDigest,
                FieldSpacing = RequireOptionalInt(systemAttributes, "field_spacing_mm"),
                PerimeterSpacing = RequireOptionalInt(systemAttributes, "perimeter_spacing_mm"),
                PerimeterBandDepth = RequireOptionalInt(systemAttributes, "perimeter_band_depth_mm"),
                TurnRadius = RequireOptionalInt(systemAttributes, "turn_radius_mm"),
                InstallationGridSpacing = RequireOptionalInt(systemAttributes, "installation_grid_spacing_mm"),
                PreferredTopology = RequireOptionalText(systemAttributes, "preferred_topology"),
                RoomBoundary = ReadOptionalPolygon(systemAttributes, "room_boundary"),
                PerimeterBandPolygon = ReadOptionalPolygon(systemAttributes, "perimeter_band_polygon"),
                PerimeterBandDigest = RequireOptionalDigest(systemAttributes, "perimeter_band_digest"),
                ExclusionZones = ReadOptionalPolygons(systemAttributes, "exclusion_zones"),
                ExteriorWallSegments = ReadOptionalWalls(systemAttributes, "exterior_wall_segments")
            };
        }

        private static FloorHeatingCircuitData ReadCircuit(
            IDictionary<string, object> node,
            IDictionary<string, object> attributes,
            string resultDigest)
        {
            string circuitId = RequireText(node, "circuit_id");
            List<FloorHeatingPointData> points =
                ReadPoints(attributes, "points_mm");
            List<FloorHeatingPointData> supply =
                ReadPoints(attributes, "supply_transit_mm");
            List<FloorHeatingPointData> returnPath =
                ReadPoints(attributes, "return_transit_mm");

            if (points.Count < 2 || supply.Count < 2 || returnPath.Count < 2)
            {
                throw new FloorHeatingPayloadException(
                    "Circuit geometry is too short."
                );
            }

            int layingStart = supply.Count - 1;
            int layingEnd = points.Count - returnPath.Count;
            if (layingStart < 0 || layingEnd < layingStart ||
                layingEnd >= points.Count ||
                !SamePoint(points[layingStart], supply[supply.Count - 1]) ||
                !SamePoint(points[layingEnd], returnPath[0]))
            {
                throw new FloorHeatingPayloadException(
                    "Circuit transit and laying geometry do not join."
                );
            }

            List<FloorHeatingPointData> laying = points
                .Skip(layingStart)
                .Take(layingEnd - layingStart + 1)
                .ToList();
            int supplyLength = Length(supply);
            int returnLength = Length(returnPath);
            int layingLength = Length(laying);
            int totalLength = RequireInt(attributes, "total_length_mm");
            if (supplyLength != RequireInt(attributes, "supply_length_mm") ||
                returnLength != RequireInt(attributes, "return_length_mm") ||
                layingLength != RequireInt(attributes, "laying_length_mm") ||
                totalLength != layingLength + supplyLength + returnLength ||
                totalLength <= 0)
            {
                throw new FloorHeatingPayloadException(
                    "Circuit lengths are not exact integer-mm quantities."
                );
            }

            return new FloorHeatingCircuitData
            {
                CircuitId = circuitId,
                NodeId = RequireText(node, "node_id"),
                Points = points,
                Supply = supply,
                Return = returnPath,
                Laying = laying,
                LayingLength = layingLength,
                SupplyLength = supplyLength,
                ReturnLength = returnLength,
                TotalLength = totalLength,
                Spacing = RequireInt(attributes, "spacing_mm"),
                MaximumStatus = RequireText(
                    attributes,
                    "maximum_length_status"
                ),
                ZoneRole = RequireOptionalText(attributes, "zone_role"),
                Topology = RequireOptionalText(attributes, "topology"),
                NominalSpacing = RequireOptionalInt(attributes, "nominal_spacing_mm"),
                PerimeterLayingLength = RequireOptionalInt(
                    attributes,
                    "perimeter_laying_length_mm"
                ),
                FieldLayingLength = RequireOptionalInt(
                    attributes,
                    "field_laying_length_mm"
                ),
                ExteriorWallReferences = ReadOptionalStrings(
                    attributes,
                    "exterior_wall_references"
                )
            };
        }

        private static string RequireOptionalText(
            IDictionary<string, object> dictionary,
            string key)
        {
            object value;
            if (!dictionary.TryGetValue(key, out value) || value == null)
            {
                return null;
            }

            if (!(value is string) || string.IsNullOrWhiteSpace((string)value))
            {
                throw new FloorHeatingPayloadException(
                    "Optional text field is invalid: " + key
                );
            }

            return (string)value;
        }

        private static int RequireOptionalInt(
            IDictionary<string, object> dictionary,
            string key)
        {
            object value;
            if (!dictionary.TryGetValue(key, out value) || value == null)
            {
                return 0;
            }

            return RequireInt(dictionary, key);
        }

        private static string RequireOptionalDigest(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key) || dictionary[key] == null)
            {
                return null;
            }

            return RequireDigest(dictionary, key);
        }

        private static List<string> ReadOptionalStrings(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key) || dictionary[key] == null)
            {
                return new List<string>();
            }

            return RequireList(dictionary, key)
                .Select(value =>
                {
                    if (!(value is string) || string.IsNullOrWhiteSpace((string)value))
                    {
                        throw new FloorHeatingPayloadException(
                            "Optional string array contains an invalid value: " + key
                        );
                    }

                    return (string)value;
                })
                .ToList();
        }

        private static FloorHeatingPolygonData ReadOptionalPolygon(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key) || dictionary[key] == null)
            {
                return null;
            }

            IDictionary<string, object> polygon =
                RequireDictionary(dictionary[key], key);
            return new FloorHeatingPolygonData
            {
                Points = ReadPoints(polygon, "points")
            };
        }

        private static List<FloorHeatingPolygonData> ReadOptionalPolygons(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key) || dictionary[key] == null)
            {
                return new List<FloorHeatingPolygonData>();
            }

            return RequireList(dictionary, key)
                .Select(value =>
                {
                    IDictionary<string, object> polygon =
                        RequireDictionary(value, key);
                    return new FloorHeatingPolygonData
                    {
                        Points = ReadPoints(polygon, "points")
                    };
                })
                .ToList();
        }

        private static List<FloorHeatingWallData> ReadOptionalWalls(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key) || dictionary[key] == null)
            {
                return new List<FloorHeatingWallData>();
            }

            return RequireList(dictionary, key)
                .Select(value =>
                {
                    IDictionary<string, object> wall =
                        RequireDictionary(value, key);
                    return new FloorHeatingWallData
                    {
                        Reference = RequireText(wall, "reference"),
                        Start = ReadPoint(wall, "start"),
                        End = ReadPoint(wall, "end")
                    };
                })
                .ToList();
        }

        private static string ValidateContainedPath(
            string path,
            string trustedRoot)
        {
            if (string.IsNullOrWhiteSpace(path) ||
                string.IsNullOrWhiteSpace(trustedRoot) ||
                !Path.IsPathRooted(path) ||
                !Path.IsPathRooted(trustedRoot))
            {
                throw new FloorHeatingPayloadException(
                    "Payload and trusted root must be absolute paths."
                );
            }

            string root = Path.GetFullPath(trustedRoot)
                .TrimEnd(Path.DirectorySeparatorChar) +
                Path.DirectorySeparatorChar;
            string full = Path.GetFullPath(path);
            if (!full.StartsWith(root, StringComparison.OrdinalIgnoreCase))
            {
                throw new FloorHeatingPayloadException(
                    "Payload path escapes the disposable runtime root."
                );
            }

            return full;
        }

        private static int Length(List<FloorHeatingPointData> points)
        {
            long total = 0;
            for (int index = 1; index < points.Count; index++)
            {
                total += Math.Abs(
                    (long)points[index].X - points[index - 1].X
                );
                total += Math.Abs(
                    (long)points[index].Y - points[index - 1].Y
                );
            }

            if (total > int.MaxValue)
            {
                throw new FloorHeatingPayloadException(
                    "Circuit geometry length overflows integer millimetres."
                );
            }

            return (int)total;
        }

        private static bool SamePoint(
            FloorHeatingPointData left,
            FloorHeatingPointData right)
        {
            return left.X == right.X && left.Y == right.Y;
        }

        private static List<FloorHeatingPointData> ReadPoints(
            IDictionary<string, object> dictionary,
            string key)
        {
            return RequireList(dictionary, key)
                .Select(value => ReadPoint(value, key))
                .ToList();
        }

        private static FloorHeatingPointData ReadPoint(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key))
            {
                throw new FloorHeatingPayloadException(
                    "Point field is missing: " + key
                );
            }

            return ReadPoint(dictionary[key], key);
        }

        private static FloorHeatingPointData ReadPoint(
            object value,
            string field)
        {
            IDictionary<string, object> dictionary =
                RequireDictionary(value, field);
            return new FloorHeatingPointData
            {
                X = RequireInt(dictionary, "x_mm"),
                Y = RequireInt(dictionary, "y_mm")
            };
        }

        private static int RequireInt(
            IDictionary<string, object> dictionary,
            string key)
        {
            if (!dictionary.ContainsKey(key))
            {
                throw new FloorHeatingPayloadException(
                    "Integer field is missing: " + key
                );
            }

            object value = dictionary[key];
            if (value is bool)
            {
                throw new FloorHeatingPayloadException(
                    "Boolean is not an integer: " + key
                );
            }

            try
            {
                decimal number = Convert.ToDecimal(
                    value,
                    CultureInfo.InvariantCulture
                );
                if (decimal.Truncate(number) != number ||
                    number < int.MinValue || number > int.MaxValue)
                {
                    throw new Exception();
                }

                return (int)number;
            }
            catch
            {
                throw new FloorHeatingPayloadException(
                    "Field is not a bounded integer: " + key
                );
            }
        }

        private static string RequireText(
            IDictionary<string, object> dictionary,
            string key)
        {
            object value;
            if (!dictionary.TryGetValue(key, out value) ||
                !(value is string) ||
                string.IsNullOrWhiteSpace((string)value))
            {
                throw new FloorHeatingPayloadException(
                    "Text field is missing or blank: " + key
                );
            }

            return (string)value;
        }

        private static string RequireString(
            IDictionary<string, object> dictionary,
            string key,
            string expected)
        {
            string value = RequireText(dictionary, key);
            if (!string.Equals(value, expected, StringComparison.Ordinal))
            {
                throw new FloorHeatingPayloadException(
                    "Field has an unexpected value: " + key
                );
            }

            return value;
        }

        private static string RequireDigest(
            IDictionary<string, object> dictionary,
            string key)
        {
            string value = RequireText(dictionary, key).ToLowerInvariant();
            if (value.Length != 64 ||
                value.Any(character =>
                    (character < '0' || character > '9') &&
                    (character < 'a' || character > 'f')))
            {
                throw new FloorHeatingPayloadException(
                    "Field is not a SHA-256 digest: " + key
                );
            }

            return value;
        }

        private static IDictionary<string, object> RequireDictionary(
            object value,
            string field)
        {
            IDictionary<string, object> result =
                value as IDictionary<string, object>;
            if (result == null)
            {
                throw new FloorHeatingPayloadException(
                    "Object field is missing: " + field
                );
            }

            return result;
        }

        private static IList<object> RequireList(
            IDictionary<string, object> dictionary,
            string key)
        {
            object value;
            if (!dictionary.TryGetValue(key, out value))
            {
                throw new FloorHeatingPayloadException(
                    "Array field is missing: " + key
                );
            }

            object[] array = value as object[];
            if (array != null)
            {
                return array;
            }

            IList list = value as IList;
            if (list == null)
            {
                throw new FloorHeatingPayloadException(
                    "Array field is invalid: " + key
                );
            }

            List<object> copy = new List<object>();
            foreach (object item in list)
            {
                copy.Add(item);
            }

            return copy;
        }

        private static void RequireExactKeys(
            IDictionary<string, object> dictionary,
            HashSet<string> allowed,
            string field)
        {
            if (dictionary.Keys.Any(key => !allowed.Contains(key)))
            {
                throw new FloorHeatingPayloadException(
                    "Unknown field in strict payload: " + field
                );
            }
        }
    }
}
