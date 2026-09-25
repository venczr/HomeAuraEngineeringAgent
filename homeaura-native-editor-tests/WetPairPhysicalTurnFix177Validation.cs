using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class WetPairPhysicalTurnFix177Validation
{
    private const string ChangedId = "F1-D171-C11";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_WetPair_D176.homeaura.json");
        var sourceContractPath = Path.Combine(sourceDirectory, "floor1_wet_pair_contract.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_WetPairPhysicalTurnFix_D177.homeaura.json");
        var packagePath = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177.zip");

        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        Check(project.Circuits.Count == source.Circuits.Count, "D177 changed circuit count.");
        foreach (var previous in source.Circuits.Where(item => item.Id != ChangedId))
        {
            var current = project.Circuits.Single(item => item.Id == previous.Id);
            Check(Serialize(current) == Serialize(previous), $"D177 changed preserved circuit {previous.Id}.");
        }

        var oldCircuit = source.Circuits.Single(item => item.Id == ChangedId);
        var circuit = project.Circuits.Single(item => item.Id == ChangedId);
        Check(circuit.OrderedPoints.Count == oldCircuit.OrderedPoints.Count, "D177 changed C11 point count.");
        for (var index = 0; index < circuit.OrderedPoints.Count; index++)
        {
            var oldPoint = oldCircuit.OrderedPoints[index];
            var point = circuit.OrderedPoints[index];
            if (index is 56 or 57)
                Check(oldPoint.X == 10700 && point.X == 10600 && point.Y == oldPoint.Y && point.Z == oldPoint.Z,
                    $"D177 exact C11 point shift failed at {index}.");
            else
                Check(Point(point) == Point(oldPoint), $"D177 changed unexpected C11 point {index}.");
        }
        Check(Point(circuit.OrderedPoints[56]) == "10600,19000,135" &&
              Point(circuit.OrderedPoints[57]) == "10600,19200,135", "D177 corrected vertices changed.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex, item.EndIndex))
              .SequenceEqual(oldCircuit.HeatingBodyRanges.Select(item => (item.StartIndex, item.EndIndex))),
            "D177 changed heating body ranges.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex)
              .SequenceEqual(new[] { 4, 26, 30, 35, 37, 55, 57, 59 }), "D177 transition indices changed.");
        var transition55 = circuit.VerticalTransitions.Single(item => item.SegmentIndex == 55);
        var transition57 = circuit.VerticalTransitions.Single(item => item.SegmentIndex == 57);
        Close(115.52809875887922, transition55.StartTangentLengthMm, 1e-9, "D177 transition 55 start tangent");
        Close(195.52809875887922, transition55.EndTangentLengthMm, 1e-9, "D177 transition 55 end tangent");
        Close(195.52809875887922, transition57.StartTangentLengthMm, 1e-9, "D177 transition 57 start tangent");
        Close(115.52809875887922, transition57.EndTangentLengthMm, 1e-9, "D177 transition 57 end tangent");

        var sourceAnalysis = CircuitAnalyzer.Analyze(source, oldCircuit);
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(sourceAnalysis.HorizontalTurnWallIntrusions == 2 && !sourceAnalysis.HorizontalTurnWallClearancePass &&
              !sourceAnalysis.EngineeringPass, "D176 historical wall-turn defect is no longer reproduced.");
        Check(analysis.HorizontalTurnWallIntrusions == 0 && analysis.HorizontalTurnWallClearancePass &&
              analysis.EngineeringPass && analysis.TopologyPass, "D177 physical R80 wall-turn fix failed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0 &&
              analysis.BendRadiusViolationCount == 0 && analysis.HeatingBodyWallIntrusions == 0,
            "D177 introduced a topology, clearance, R80, or body-wall defect.");
        Close(77_399.1769440993, analysis.RoundedAxisLengthMm, .003, "D177 C11 rounded length");
        var c10 = CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == "F1-D171-C10"));
        Close(77_463.08716343118, c10.RoundedAxisLengthMm, .003, "D177 C10 rounded length");
        Close(63.91021933188313, Math.Abs(c10.RoundedAxisLengthMm - analysis.RoundedAxisLengthMm), .003,
            "D177 pair spread");

        ValidateContract(directory, sourcePath, sourceContractPath);
        ValidateDiagnostics(directory);
        ValidatePackage(directory, packagePath);
    }

    private static void ValidateContract(string directory, string sourcePath, string sourceContractPath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,
            "floor1_wet_pair_physical_turn_fix_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("status").GetString() ==
              "D176_PHYSICAL_TURN_SUPERSEDED_PASS_COLLECTOR_TAILS_DEFERRED", "D177 status changed.");
        Check(contract.GetProperty("source_D176_project_sha256").GetString() == Sha(sourcePath) &&
              contract.GetProperty("source_D176_contract_sha256").GetString() == Sha(sourceContractPath),
            "D177 source lineage changed.");
        Check(contract.GetProperty("physical_R80_turn_wall_audit").GetProperty("intrusion_count").GetInt32() == 0 &&
              contract.GetProperty("physical_R80_turn_wall_audit").GetProperty("pass").GetBoolean(),
            "D177 stored physical wall-turn audit failed.");
        Close(20, contract.GetProperty("physical_R80_turn_wall_audit")
            .GetProperty("minimum_axis_clearance_to_any_wall_solid_mm").GetDouble(), 1e-6,
            "D177 minimum axis-to-wall clearance");
        Close(63.91021933188313, contract.GetProperty("pair_rounded_length_spread_mm").GetDouble(), 1e-6,
            "D177 stored pair spread");
        var tails = contract.GetProperty("collector_tail_evidence");
        Check(tails.GetProperty("classification").GetString() ==
              "DEFERRED_COLLECTOR_TAIL_FABRICATION_GEOMETRY_NOT_MICRO_STUBS" &&
              tails.GetProperty("records").GetArrayLength() == 4, "D177 collector-tail classification changed.");
        Close(2446.0542205764777, tails.GetProperty("minimum_gap_mm").GetDouble(), 1e-6,
            "D177 minimum collector tail");
        Close(2508.785811901845, tails.GetProperty("maximum_gap_mm").GetDouble(), 1e-6,
            "D177 maximum collector tail");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              contract.GetProperty("bounded_terminal_grid_route_count").GetInt32() == 6 &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D177 completion boundary changed.");
    }

    private static void ValidateDiagnostics(string directory)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "engineering_diagnostics.json")));
        var records = document.RootElement.GetProperty("circuits").EnumerateArray()
            .Where(item => item.GetProperty("circuit_id").GetString() is "F1-D171-C10" or ChangedId).ToArray();
        Check(records.Length == 2 && records.All(item => item.GetProperty("engineering_pass").GetBoolean() &&
              item.GetProperty("horizontal_turn_wall_intrusions").GetInt32() == 0 &&
              item.GetProperty("self_surface_clearance_violations").GetInt32() == 0 &&
              item.GetProperty("inter_circuit_surface_clearance_violations").GetInt32() == 0),
            "D177 exported diagnostics failed.");
    }

    private static void ValidatePackage(string directory, string packagePath)
    {
        foreach (var name in new[]
        {
            "HomeAura_Floor1_D177_Clean_View.png", "HomeAura_Floor1_D177_WetPair_Clean_Zoom.png",
            "HomeAura_Floor1_D177_WetPair_3D_Debug.png", "engineering_diagnostics.json",
        })
            Check(new FileInfo(Path.Combine(directory, name)) is { Exists: true, Length: > 0 }, $"D177 file {name} missing.");

        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D177 manifest mismatch for {path}.");
        }
        using var archive = ZipFile.OpenRead(packagePath);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D177 ZIP member count changed.");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D177 ZIP byte parity failed for {entry.FullName}.");
        }
    }

    private static string Point(PointMm point) => $"{point.X},{point.Y},{point.Z}";
    private static string Serialize(ManualCircuit circuit) => JsonSerializer.Serialize(circuit, HomeAuraProject.JsonOptions);
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected, double actual, double tolerance, string label)
    { if (Math.Abs(expected - actual) > tolerance) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Check(bool condition, string message)
    { if (!condition) throw new InvalidDataException(message); }
}
