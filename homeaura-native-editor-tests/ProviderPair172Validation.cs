using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class ProviderPair172Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_OwnerAcceptedAnalogue_D171.homeaura.json");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_ProviderPair_D172.homeaura.json");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == 13, "D172 circuit count");
        Check(project.Collectors.Single(item => item.Id == "K1").Ports == 26, "D172 K1 port count");
        var changed = new HashSet<string>(["F1-D171-C01", "F1-D171-C02"], StringComparer.Ordinal);
        foreach (var sourceCircuit in source.Circuits.Where(item => !changed.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == sourceCircuit.Id);
            Check(Points(current).SequenceEqual(Points(sourceCircuit)), $"{sourceCircuit.Id} must remain unchanged");
        }

        var east = project.Circuits.Single(item => item.Id == "F1-D171-C01");
        var west = project.Circuits.Single(item => item.Id == "F1-D171-C02");
        Check(Points(east).Last() == "9700,9400", "D172 east seam extension");
        Check(east.OrderedPoints.Count == 34 && west.OrderedPoints.Count == 31, "D172 control point counts");
        RequireCentre(east, 17, [
            "11200,10700", "11200,10200", "10700,10200", "10700,10400",
            "11000,10400", "11000,10600", "10500,10600",
        ]);
        RequireCentre(west, 19, [
            "8800,9900", "9300,9900", "9300,10400", "9100,10400",
            "9100,10100", "8900,10100", "8900,10600",
        ]);

        var eastAnalysis = CircuitAnalyzer.Analyze(project, east);
        var westAnalysis = CircuitAnalyzer.Analyze(project, west);
        Check(eastAnalysis.SelfIntersections == 0 && westAnalysis.SelfIntersections == 0, "D172 self topology");
        Check(eastAnalysis.InterCircuitIntersections == 0 && westAnalysis.InterCircuitIntersections == 0, "D172 global contacts");
        Check(eastAnalysis.HeatingBodyInsideAssignedRoom && westAnalysis.HeatingBodyInsideAssignedRoom, "D172 room containment");
        Check(eastAnalysis.HeatingBodyWallIntrusions == 0 && westAnalysis.HeatingBodyWallIntrusions == 0, "D172 body wall hits");
        Check(eastAnalysis.AxisLengthMm == 41_100 && westAnalysis.AxisLengthMm == 32_100, "D172 axis lengths");
        Check(eastAnalysis.BendRadiusViolationCount == 2 && westAnalysis.BendRadiusViolationCount == 2,
            "D172 must expose, not hide, four inherited exterior R80 blockers");

        RequireHorizontalLevels(east, [8800, 8900, 9000]);
        RequireHorizontalLevels(west, [8800, 8900, 9000]);
        RequireVerticalLevels(west, [7700, 7800, 7900]);

        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_provider_pair_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("status").GetString() == "CONTROL_PAIR_OWNER_CENTRE_PASS_REWORK_JOINT_EXTERIOR_R80_WEAVE",
            "D172 bounded status");
        Check(contract.GetProperty("provider_runs").EnumerateArray().Count() == 4, "D172 provider run evidence");
        Check(contract.GetProperty("provider_runs").EnumerateArray().All(item => !item.GetProperty("candidate_accepted").GetBoolean()),
            "D172 must not fabricate provider acceptance");
        var validation = contract.GetProperty("pair_validation");
        Check(validation.GetProperty("inter_circuit_contact_count").GetInt32() == 0, "D172 stored contacts");
        Check(Math.Abs(validation.GetProperty("minimum_pair_centerline_distance_mm").GetDouble() - 200) < 0.001,
            "D172 pair clearance");
        Check(validation.GetProperty("combined_maximum_sample_distance_mm").GetDouble() <= 200.001,
            "D172 pair worst uncovered sample");
        Check(validation.GetProperty("combined_50mm_sample_within_150mm_percent").GetDouble() > 99.9,
            "D172 pair dense coverage");
        Check(validation.GetProperty("rounded_complete_length_spread_mm").GetDouble() < 3000,
            "D172 pair balance hard limit");
        Check(validation.GetProperty("R80_tangent_allocation_violation_count").GetInt32() == 4,
            "D172 stored R80 blockers");
        Check(!contract.GetProperty("installation_ready").GetBoolean(), "D172 installation honesty");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0, "D172 full route honesty");

        var manifestPath = Path.Combine(directory, "artifact_manifest.json");
        using var manifestDocument = JsonDocument.Parse(File.ReadAllText(manifestPath));
        foreach (var item in manifestDocument.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path), $"D172 manifest file {path}");
            Check(new FileInfo(path).Length == item.GetProperty("bytes").GetInt64(), $"D172 manifest bytes {path}");
            Check(Sha(path) == item.GetProperty("sha256").GetString(), $"D172 manifest SHA {path}");
        }
        var package = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172.zip");
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D172 package member count");
        Check(File.Exists(Path.Combine(directory, "HomeAura_Floor1_D172_Clean_View.png")), "D172 clean view");
        Check(File.Exists(Path.Combine(directory, "HomeAura_Floor1_D172_Editor_View.png")), "D172 editor view");
    }

    private static void RequireCentre(ManualCircuit circuit, int startIndex, string[] expected)
    {
        Check(Points(circuit).Skip(startIndex).Take(expected.Length).SequenceEqual(expected), $"{circuit.Id} exact ACCEPTED-B centre");
    }

    private static void RequireHorizontalLevels(ManualCircuit circuit, int[] levels)
    {
        var available = circuit.OrderedPoints.Zip(circuit.OrderedPoints.Skip(1))
            .Where(pair => pair.First.Y == pair.Second.Y)
            .Select(pair => pair.First.Y).ToHashSet();
        Check(levels.All(available.Contains), $"{circuit.Id} top 3x100 levels");
    }

    private static void RequireVerticalLevels(ManualCircuit circuit, int[] levels)
    {
        var available = circuit.OrderedPoints.Zip(circuit.OrderedPoints.Skip(1))
            .Where(pair => pair.First.X == pair.Second.X)
            .Select(pair => pair.First.X).ToHashSet();
        Check(levels.All(available.Contains), $"{circuit.Id} left 3x100 levels");
    }

    private static IEnumerable<string> Points(ManualCircuit circuit) => circuit.OrderedPoints.Select(point => $"{point.X},{point.Y}");

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
