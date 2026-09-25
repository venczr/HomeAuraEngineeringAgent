using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class R07Point3Routes184Validation
{
    private static readonly string[] ChangedIds = ["F1-D171-C03", "F1-D171-C04"];
    private const string D183Sha = "E5096220BE3D2F7C93BC5F8B399A374C95556A9D4A29797445EDDC27835CDE4B";
    private const string StrictBodySha = "0D320A979A240D470E6C19ABE6D5475E315E74FC362B68EFDF17FD2F3899A676";
    private const string IndependentAuditSha = "FF15844F195E0C67DE743A2F9FF5696AEFE40661E1CDA4C4CBE2C574ABE6758A";
    private const string SecondIndependentAuditSha = "E6B938B383DD18918696D9AE43078C5667A1A394DB325176897362DC26A36E38";
    private const string ProjectSha = "1A00E6B7539A0A704F1341BCCEB5982BB79B95F9520C4713D8791B573A511852";
    private const string DiagnosticsSha = "8C99ABC19A9A0021EFA80C50CA4078E0E4D6E316CB9D126874BDCAFED7F18312";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourcePath = Path.Combine(proposals, "HA_TWO_FLOOR_R03_POINT3_ROUTES_183",
            "HomeAura_TwoFloor_R03Point3Routes_D183.homeaura.json");
        var strictBodyPath = Path.Combine(root, "tmp", "reports", "R07_Strict_Distributed_BODY_candidate.homeaura.json");
        var independentAuditPath = Path.Combine(root, "tmp", "r07_point3", "frozen_candidate_acceptance.json");
        var secondIndependentAuditPath = Path.Combine(root, "tmp", "r07_service_audit", "second_independent_audit.json");
        var official = Path.Combine(proposals, "HA_TWO_FLOOR_R07_POINT3_ROUTES_184");
        var isOfficial = Directory.Exists(official);
        var directory = isOfficial ? official : Path.Combine(root, "tmp", "D184_scaffold");
        var package = isOfficial
            ? Path.Combine(proposals, "packages", "HA_TWO_FLOOR_R07_POINT3_ROUTES_184.zip")
            : Path.Combine(root, "tmp", "HA_TWO_FLOOR_R07_POINT3_ROUTES_184_SCAFFOLD.zip");
        var projectPath = Path.Combine(directory, "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json");
        var contractPath = Path.Combine(directory, "floor1_r07_point3_routes_contract.json");
        Equal(D183Sha, Sha(sourcePath), "D183 source");
        Equal(StrictBodySha, Sha(strictBodyPath), "strict R07 BODY source");
        Equal(IndependentAuditSha, Sha(independentAuditPath), "independent audit");
        Equal(SecondIndependentAuditSha, Sha(secondIndependentAuditPath), "second independent audit");
        Equal(ProjectSha, Sha(projectPath), "D184 exact project");
        Equal(DiagnosticsSha, Sha(Path.Combine(directory, "engineering_diagnostics.json")), "D184 diagnostics");

        using var sourceDocument = JsonDocument.Parse(File.ReadAllText(sourcePath));
        using var projectDocument = JsonDocument.Parse(File.ReadAllText(projectPath));
        foreach (var property in sourceDocument.RootElement.EnumerateObject())
        {
            Check(projectDocument.RootElement.TryGetProperty(property.Name, out var current), $"D184 lost {property.Name}.");
            if (property.Name != "circuits")
                Check(JsonElement.DeepEquals(property.Value, current), $"D184 changed D183 {property.Name}.");
        }
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var strictBody = HomeAuraProject.FromJson(File.ReadAllText(strictBodyPath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        foreach (var previous in source.Circuits.Where(item => !ChangedIds.Contains(item.Id)))
            Check(Serialize(previous) == Serialize(project.Circuits.Single(item => item.Id == previous.Id)),
                $"D184 changed preserved circuit {previous.Id}.");

        ValidateCircuit(project, strictBody, "F1-D171-C03", 35, (4, 30), [3, 30],
            "3A00AE33E21D260293C9C450AEA1A6E898A4CA76844A90471DB9600C09EFCD58",
            49_710.734410204226, 48_611.97300679916, 4, 5);
        ValidateCircuit(project, strictBody, "F1-D171-C04", 37, (4, 32), [3, 32],
            "EA40E10B9D500AFB618477828567D27583ED796B6FDF19AB31C235A5E65777C7",
            51_710.734410204226, 50_543.30041908634, 6, 7);
        var analyses = ChangedIds.ToDictionary(id => id,
            id => CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == id)));
        Close(2_000, analyses.Values.Max(item => item.AxisLengthMm) - analyses.Values.Min(item => item.AxisLengthMm),
            .000001, "raw 3D spread");
        Close(1_931.3274122871808,
            analyses.Values.Max(item => item.RoundedAxisLengthMm) - analyses.Values.Min(item => item.RoundedAxisLengthMm),
            .000001, "physical R80 rounded spread");
        ValidateWallSolids(project);
        ValidatePorts(project);
        ValidateCompleteness(project);
        ValidateContract(contractPath, isOfficial);
        ValidatePackage(directory, package);
    }

    private static void ValidateCircuit(HomeAuraProject project, HomeAuraProject strictBody, string id, int pointCount,
        (int Start, int End) range, IReadOnlyList<int> transitions, string digest,
        double rawLength, double roundedLength, int supplyPort, int returnPort)
    {
        var circuit = project.Circuits.Single(item => item.Id == id);
        Check(circuit.OrderedPoints.Count == pointCount && circuit.OrderedPoints.All(item => item.Z is not null),
            $"{id} is not the exact Point3 chain.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex, item.EndIndex)).SequenceEqual([range]),
            $"{id} BODY range changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual(transitions),
            $"{id} S-bend indices changed.");
        Equal(digest, HashPoints(circuit.OrderedPoints), $"{id} ordered points");
        var expectedBody = strictBody.Circuits.Single(item => item.Id == id).OrderedPoints;
        var actualBody = circuit.OrderedPoints.Skip(range.Start).Take(range.End - range.Start + 1).ToArray();
        Check(HashPoints(expectedBody) == HashPoints(actualBody) && actualBody.All(item => item.Z == 108),
            $"{id} no longer forwards the strict BODY exactly.");
        Check(circuit.SystemRole == "FLOOR_HEATING_LOOP" && circuit.ConcealedServiceLengthMm == 0 &&
              circuit.OutOfPlaneLengthMm == 0, $"{id} route semantics changed.");
        Check(circuit.SupplyPortIndex == supplyPort && circuit.ReturnPortIndex == returnPort, $"{id} ports changed.");
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.Pass && analysis.TopologyPass && analysis.EngineeringPass && analysis.GridAligned &&
              analysis.HeatingBodyInsideAssignedRoom && analysis.HeatingBodyPlacementPass &&
              analysis.VerticalGeometryMaterialized && analysis.VerticalTransitionRadiusFeasible &&
              analysis.Exterior3x100UsefulSpanApplicable && analysis.Exterior3x100UsefulSpanPass,
            $"{id} C# positive gate failed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0 &&
              analysis.HeatingBodyWallIntrusions == 0 && analysis.HorizontalTurnWallIntrusions == 0 &&
              analysis.BendRadiusViolationCount == 0 && analysis.UnmaterializedElevationChangeCount == 0,
            $"{id} C# zero-defect gate failed.");
        Check(analysis.MinimumInterCircuitSurfaceClearanceMm >= 10.965, $"{id} surface clearance fell below 10.965 mm.");
        var lane3 = analysis.ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Check(lane3.UsefulSpanPass && lane3.StaggeredTurnoutPass &&
              lane3.UsefulSpanMode == "STAGGERED_ALTERNATING_TURNOUT" &&
              lane3.PreviousLaneEndExtensionMm == 100 && lane3.WindowCoveragePercent == 100 &&
              lane3.AggregateRoomMinimumSegmentLengthMm == 200,
            $"{id} staggered useful-span gate changed.");
        Close(rawLength, analysis.AxisLengthMm, .000001, $"{id} raw 3D length");
        Close(roundedLength, analysis.RoundedAxisLengthMm, .000001, $"{id} physical rounded length");
    }

    private static void ValidateWallSolids(HomeAuraProject project)
    {
        var intersections = 0;
        var endpointTouches = 0;
        foreach (var circuit in project.Circuits.Where(item => ChangedIds.Contains(item.Id)))
        {
            var bodyIndices = circuit.HeatingBodyRanges
                .SelectMany(range => Enumerable.Range(range.StartIndex, range.EndIndex - range.StartIndex)).ToHashSet();
            for (var index = 0; index + 1 < circuit.OrderedPoints.Count; index++)
            foreach (var wall in project.Walls)
            {
                var first = circuit.OrderedPoints[index]; var second = circuit.OrderedPoints[index + 1];
                if (!TouchesWallSolid(first, second, wall)) continue;
                intersections++;
                if (index == 0 || index == circuit.OrderedPoints.Count - 2) endpointTouches++;
                Check(!bodyIndices.Contains(index), $"{circuit.Id} BODY {index} touches {wall.Id}.");
                var perpendicular = wall.Start.X == wall.End.X ? first.Y == second.Y : first.X == second.X;
                Check(perpendicular, $"{circuit.Id} TRANSIT {index} is longitudinal in {wall.Id}.");
            }
        }
        Equal(12, intersections, "wall intersections");
        Equal(4, endpointTouches, "terminal endpoint wall touches");
    }

    private static void ValidatePorts(HomeAuraProject project)
    {
        var ports = project.Circuits.Where(item => item.CollectorId == "K1")
            .SelectMany(item => new[] {item.SupplyPortIndex, item.ReturnPortIndex}).Where(item => item is not null)
            .Select(item => item!.Value).Order().ToArray();
        Check(ports.SequenceEqual(Enumerable.Range(0, 28)), "D184 K1 does not own ports 0..27 exactly once.");
    }

    private static void ValidateCompleteness(HomeAuraProject project)
    {
        var point3 = project.Circuits.Count(item => item.SystemRole == "FLOOR_HEATING_LOOP" &&
            item.ConcealedServiceLengthMm == 0 && item.OutOfPlaneLengthMm == 0 &&
            item.OrderedPoints.Count > 0 && item.OrderedPoints.All(point => point.Z is not null));
        Equal(13, point3, "bounded terminal-grid Point3 routes");
        var axes = project.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_AXIS").Select(item => item.Id).ToArray();
        Check(axes.SequenceEqual(["F1-D171-C12"]), "D184 remaining AXIS boundary changed.");
        var loops = project.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_LOOP")
            .Select(item => CircuitAnalyzer.Analyze(project, item)).ToArray();
        Check(loops.Length == 13 && loops.All(item => item.Pass && item.TopologyPass && item.EngineeringPass),
            "D184 materialized LOOP set no longer passes globally.");
    }

    private static void ValidateContract(string path, bool isOfficial)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path)); var contract = document.RootElement;
        Equal("R07_C03_C04_POINT3_HARD_GATES_PASS_COLLECTOR_TAILS_DEFERRED",
            contract.GetProperty("status").GetString(), "D184 status");
        Equal(isOfficial ? "OFFICIAL_APPEND_ONLY_D184" : "PREPUBLICATION_SCAFFOLD_AWAITING_ROOT_GO",
            contract.GetProperty("publication_state").GetString(), "D184 publication state");
        Check(!contract.GetProperty("publishable").GetBoolean() &&
              !contract.GetProperty("publishable_as_installation_project").GetBoolean() &&
              contract.GetProperty("terminal_grid_route_only").GetBoolean() &&
              !contract.GetProperty("physical_eurocone_tails_materialized").GetBoolean(),
            "D184 exceeded its terminal-grid publication boundary.");
        var lengths = contract.GetProperty("route_lengths");
        Close(2_000, lengths.GetProperty("raw_3d_axis_spread_mm").GetDouble(), .000001, "stored raw spread");
        Close(1_931.3274122871808, lengths.GetProperty("physical_R80_rounded_axis_spread_mm").GetDouble(),
            .000001, "stored rounded spread");
        var coverage = contract.GetProperty("custom_R07_BODY_coverage").GetProperty("physical_R80_axis_round100_q16");
        Close(96.26167789144965, coverage.GetProperty("served_percent").GetDouble(), 1e-12, "D184 coverage");
        Close(200, coverage.GetProperty("maximum_sample_distance_mm").GetDouble(), 1e-12, "D184 max gap");
        Equal(0, coverage.GetProperty("sample_over_200mm_count").GetInt32(), "D184 samples over 200");
        var exterior = contract.GetProperty("exterior_3x100_useful_span");
        Check(exterior.GetProperty("window_id").GetString() == "F1-WIN-02" &&
              exterior.GetProperty("window_coverage_percent").EnumerateArray().All(item => item.GetDouble() == 100) &&
              exterior.GetProperty("all_useful_span_pass").GetBoolean() &&
              exterior.GetProperty("staggered_lane_3").GetProperty("staggered_turnout_pass").GetBoolean(),
            "D184 useful exterior 3x100 gate changed.");
        var walls = contract.GetProperty("sharp_wall_solid_transit_audit");
        Check(walls.GetProperty("pass").GetBoolean() && walls.GetProperty("intersection_count").GetInt32() == 12 &&
              walls.GetProperty("body_wall_hit_count").GetInt32() == 0 &&
              walls.GetProperty("longitudinal_or_nonperpendicular_transit_count").GetInt32() == 0,
            "D184 stored wall audit changed.");
        var bundle = contract.GetProperty("global_same_layer_transit_bundle_audit");
        Check(bundle.GetProperty("all_groups_at_most_three_pipes").GetBoolean() &&
              bundle.GetProperty("maximum_pipe_axes_in_any_group_window").GetInt32() == 3,
            "D184 transit bundle gate changed.");
        var tails = contract.GetProperty("collector_tail_evidence");
        Check(tails.GetProperty("records").GetArrayLength() == 4 &&
              tails.GetProperty("records").EnumerateArray().All(item => !item.GetProperty("fabrication_tail_materialized").GetBoolean()),
            "D184 invented a terminal-to-Eurocone XYZ tail.");
        Check(contract.GetProperty("bounded_terminal_grid_route_count").GetInt32() == 13 &&
              contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              !contract.GetProperty("sleeves_added").GetBoolean() &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D184 completion boundary changed.");
        Equal("GO", contract.GetProperty("independent_audit").GetProperty("status").GetString(), "independent GO");
        Equal("GO", contract.GetProperty("independent_audit").GetProperty("second_status").GetString(), "second independent GO");
    }

    private static void ValidatePackage(string directory, string package)
    {
        foreach (var name in new[] {"HomeAura_Floor1_D184_Clean_View.png", "HomeAura_Floor1_D184_R07_Clean_Zoom.png",
                     "HomeAura_Floor1_D184_R07_3D_Diagnostic.png", "engineering_diagnostics.json"})
            Check(new FileInfo(Path.Combine(directory, name)) is {Exists: true, Length: > 0}, $"D184 missing {name}.");
        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var file = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(file) && new FileInfo(file).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(file) == item.GetProperty("sha256").GetString(), $"D184 manifest mismatch: {file}");
        }
        using var archive = ZipFile.OpenRead(package);
        Equal(Directory.GetFiles(directory).Length, archive.Entries.Count, "D184 ZIP member count");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open(); using var memory = new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D184 ZIP byte parity failed: {entry.FullName}");
        }
    }

    private static bool TouchesWallSolid(PointMm first, PointMm second, WallSegment wall)
    {
        var half = wall.ThicknessMm / 2;
        var minX = Math.Min(wall.Start.X, wall.End.X) - (wall.Start.X == wall.End.X ? half : 0);
        var maxX = Math.Max(wall.Start.X, wall.End.X) + (wall.Start.X == wall.End.X ? half : 0);
        var minY = Math.Min(wall.Start.Y, wall.End.Y) - (wall.Start.Y == wall.End.Y ? half : 0);
        var maxY = Math.Max(wall.Start.Y, wall.End.Y) + (wall.Start.Y == wall.End.Y ? half : 0);
        return Math.Max(Math.Min(first.X, second.X), minX) <= Math.Min(Math.Max(first.X, second.X), maxX) &&
               Math.Max(Math.Min(first.Y, second.Y), minY) <= Math.Min(Math.Max(first.Y, second.Y), maxY);
    }

    private static string HashPoints(IEnumerable<PointMm> points)
    {
        var value = string.Join("|", points.Select(point => $"{point.X},{point.Y},{point.Z}"));
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    }
    private static string Serialize(ManualCircuit circuit) => JsonSerializer.Serialize(circuit, HomeAuraProject.JsonOptions);
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected, double actual, double tolerance, string label)
    { if (Math.Abs(expected - actual) > tolerance) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Equal<T>(T expected, T actual, string label)
    { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Check(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
}
