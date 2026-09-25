using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class JointWeave173Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_PROVIDER_PAIR_172");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_ProviderPair_D172.homeaura.json");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_JointWeave_D173.homeaura.json");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == 13, "D173 circuit count");
        Check(project.Collectors.Single(item => item.Id == "K1").Ports == 26, "D173 K1 ports preserved");
        var changed = new HashSet<string>(["F1-D171-C01", "F1-D171-C02"], StringComparer.Ordinal);
        foreach (var sourceCircuit in source.Circuits.Where(item => !changed.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == sourceCircuit.Id);
            Check(Points(current).SequenceEqual(Points(sourceCircuit)), $"D173 preserves {sourceCircuit.Id}");
        }

        var east = project.Circuits.Single(item => item.Id == "F1-D171-C01");
        var west = project.Circuits.Single(item => item.Id == "F1-D171-C02");
        Check(east.OrderedPoints.Count == 29 && west.OrderedPoints.Count == 30, "D173 point counts");
        Check(Manhattan(east.OrderedPoints) == 39_500 && Manhattan(west.OrderedPoints) == 36_100,
            "D173 body lengths");
        Check(MinimumSegment(east.OrderedPoints) == 200 && MinimumSegment(west.OrderedPoints) == 200,
            "D173 removes 100-mm body U-turn segments");
        RequireCentre(east, 12, [
            "10500,10700", "10500,10200", "11000,10200", "11000,10400",
            "10700,10400", "10700,10600", "11200,10600",
        ]);
        RequireCentre(west, 17, [
            "8600,10600", "9100,10600", "9100,10100", "8900,10100",
            "8900,10400", "8700,10400", "8700,9900",
        ]);

        var eastAnalysis = CircuitAnalyzer.Analyze(project, east);
        var westAnalysis = CircuitAnalyzer.Analyze(project, west);
        Check(eastAnalysis.SelfIntersections == 0 && westAnalysis.SelfIntersections == 0, "D173 self topology");
        Check(eastAnalysis.InterCircuitIntersections == 0 && westAnalysis.InterCircuitIntersections == 0,
            "D173 global contacts");
        Check(eastAnalysis.HeatingBodyInsideAssignedRoom && westAnalysis.HeatingBodyInsideAssignedRoom,
            "D173 room containment");
        Check(eastAnalysis.HeatingBodyWallIntrusions == 0 && westAnalysis.HeatingBodyWallIntrusions == 0,
            "D173 body-wall separation");
        Check(eastAnalysis.BendRadiusViolationCount == 0 && westAnalysis.BendRadiusViolationCount == 0,
            "D173 R80 tangent allocation");

        var pairPoints = east.OrderedPoints.Concat(west.OrderedPoints).ToArray();
        var roomSamples = 0;
        var within150 = 0;
        var worst = 0d;
        for (var x = 7600; x <= 12300; x += 50)
        for (var y = 8700; y <= 11600; y += 50)
        {
            roomSamples++;
            var distance = Math.Min(DistanceToPolyline(new PointMm(x, y), east.OrderedPoints),
                DistanceToPolyline(new PointMm(x, y), west.OrderedPoints));
            if (distance <= 150.000001) within150++;
            worst = Math.Max(worst, distance);
        }
        Check(within150 == roomSamples && worst <= 150.000001, "D173 dense joint room sampling");

        using var contractDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_joint_weave_contract.json")));
        var contract = contractDocument.RootElement;
        Check(contract.GetProperty("status").GetString() ==
              "JOINT_BODY_WEAVE_PASS_REWORK_ACTUAL_K1_TRANSITS_AND_BALANCE", "D173 bounded status");
        var supersession = contract.GetProperty("supersession");
        Check(supersession.GetProperty("supersedes_project_sha256").GetString() == Sha(sourcePath),
            "D173 immutable D172 source hash");
        Check(supersession.GetProperty("errata")[0].GetProperty("verified_D172_value_mm").GetDouble() > 2296,
            "D173 D172 spread erratum");
        var validation = contract.GetProperty("joint_validation");
        Check(validation.GetProperty("global_inter_circuit_contact_count").GetInt32() == 0, "D173 stored contacts");
        Check(validation.GetProperty("R80_tangent_allocation_violation_count").GetInt32() == 0, "D173 stored R80");
        Check(validation.GetProperty("minimum_body_segment_mm").GetInt32() == 200, "D173 stored min segment");
        Check(validation.GetProperty("field_pair_centerline_minimum_mm").GetDouble() >= 200,
            "D173 200-mm field separation");
        Check(validation.GetProperty("pair_centerline_minimum_mm").GetDouble() == 100,
            "D173 100-mm pair spacing is explicit");
        Check(validation.GetProperty("pair_100mm_scope").GetString() == "EXTERIOR_3X100_ZONE_ONLY",
            "D173 100-mm scope");
        Check(validation.GetProperty("joint_round_100mm_served_percent").GetDouble() >= 98,
            "D173 joint proximity coverage");
        Check(validation.GetProperty("joint_maximum_sample_distance_mm").GetDouble() <= 150.000001,
            "D173 worst sample");
        Check(validation.GetProperty("raw_full_face_90_percent_pass_count").GetInt32() == 3,
            "D173 does not hide raw exterior span failures");
        Check(validation.GetProperty("declared_turn_envelope_continuous_pass_count").GetInt32() == 6,
            "D173 six continuous exterior passes");
        Check(!contract.GetProperty("balance").GetProperty("accepted_as_balance_certificate").GetBoolean(),
            "D173 balance honesty");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D173 full-route honesty");

        var providerEvidencePath = Path.Combine(directory, contract.GetProperty("provider_run_evidence_file").GetString()!);
        Check(Sha(providerEvidencePath) == contract.GetProperty("provider_run_evidence_sha256").GetString(),
            "D173 provider evidence hash");
        using var providerDocument = JsonDocument.Parse(File.ReadAllText(providerEvidencePath));
        var provider = providerDocument.RootElement;
        Check(provider.GetProperty("runs").GetArrayLength() == 4, "D173 four immutable provider attempts");
        Check(provider.GetProperty("accepted_provider_candidate_count").GetInt32() == 0,
            "D173 provider non-attribution");
        Check(provider.GetProperty("runs").EnumerateArray().All(item =>
            !item.GetProperty("usable_geometry_returned").GetBoolean()), "D173 no fabricated provider result");

        var diagnosticsPath = Path.Combine(directory, "engineering_diagnostics.json");
        using var diagnosticsDocument = JsonDocument.Parse(File.ReadAllText(diagnosticsPath));
        var diagnostics = diagnosticsDocument.RootElement.GetProperty("circuits").EnumerateArray()
            .Where(item => changed.Contains(item.GetProperty("circuit_id").GetString()!)).ToArray();
        Check(diagnostics.Length == 2, "D173 diagnostics pair");
        Check(diagnostics.All(item => item.GetProperty("bend_radius_violation_count").GetInt32() == 0),
            "D173 exported R80 diagnostics");
        Check(diagnostics.All(item => item.GetProperty("heating_body_wall_intrusions").GetInt32() == 0),
            "D173 exported wall diagnostics");

        var readme = File.ReadAllText(Path.Combine(directory, "README.md"));
        Check(readme.Contains("2,297", StringComparison.Ordinal), "D173 README corrects D172 spread");
        foreach (var file in new[]
        {
            "HomeAura_Floor1_D173_Editor_View.png",
            "HomeAura_Floor1_D173_Clean_View.png",
            "HomeAura_Floor1_D173_F1-R08_Clean_Zoom.png",
            "HomeAura_Floor1_D173_F1-R08_Diagnostics_Zoom.png",
        }) Check(File.Exists(Path.Combine(directory, file)), $"D173 image {file}");

        var manifestPath = Path.Combine(directory, "artifact_manifest.json");
        using var manifestDocument = JsonDocument.Parse(File.ReadAllText(manifestPath));
        foreach (var item in manifestDocument.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path), $"D173 manifest file {path}");
            Check(new FileInfo(path).Length == item.GetProperty("bytes").GetInt64(), $"D173 manifest bytes {path}");
            Check(Sha(path) == item.GetProperty("sha256").GetString(), $"D173 manifest SHA {path}");
        }
        var package = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173.zip");
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D173 package member count");
        foreach (var entry in archive.Entries)
        {
            var path = Path.Combine(directory, entry.FullName);
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(path)), $"D173 package parity {entry.FullName}");
        }
    }

    private static void RequireCentre(ManualCircuit circuit, int startIndex, string[] expected) =>
        Check(Points(circuit).Skip(startIndex).Take(expected.Length).SequenceEqual(expected),
            $"{circuit.Id} exact owner centre");

    private static int Manhattan(IReadOnlyList<PointMm> points) => points.Zip(points.Skip(1))
        .Sum(pair => Math.Abs(pair.First.X - pair.Second.X) + Math.Abs(pair.First.Y - pair.Second.Y));

    private static int MinimumSegment(IReadOnlyList<PointMm> points) => points.Zip(points.Skip(1))
        .Min(pair => Math.Abs(pair.First.X - pair.Second.X) + Math.Abs(pair.First.Y - pair.Second.Y));

    private static double DistanceToPolyline(PointMm point, IReadOnlyList<PointMm> points) =>
        points.Zip(points.Skip(1)).Min(pair => DistanceToSegment(point, pair.First, pair.Second));

    private static double DistanceToSegment(PointMm point, PointMm first, PointMm second)
    {
        if (first.X == second.X)
        {
            var y = Math.Clamp(point.Y, Math.Min(first.Y, second.Y), Math.Max(first.Y, second.Y));
            return Math.Sqrt(Math.Pow(point.X - first.X, 2) + Math.Pow(point.Y - y, 2));
        }
        var x = Math.Clamp(point.X, Math.Min(first.X, second.X), Math.Max(first.X, second.X));
        return Math.Sqrt(Math.Pow(point.X - x, 2) + Math.Pow(point.Y - first.Y, 2));
    }

    private static IEnumerable<string> Points(ManualCircuit circuit) =>
        circuit.OrderedPoints.Select(point => $"{point.X},{point.Y}");

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
