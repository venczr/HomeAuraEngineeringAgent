using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class LowerServicePair174Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_JOINT_WEAVE_173");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_JointWeave_D173.homeaura.json");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_LowerServicePair_D174.homeaura.json");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == 17, "D174 13 upper axes plus four lower service legs");
        var changed = new HashSet<string> { "F1-D171-C01", "F1-D171-C02" };
        foreach (var sourceCircuit in source.Circuits.Where(item => !changed.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == sourceCircuit.Id);
            Check(Points(current).SequenceEqual(Points(sourceCircuit)), $"D174 preserves {sourceCircuit.Id}");
        }

        var c01 = project.Circuits.Single(item => item.Id == "F1-D171-C01");
        var c02 = project.Circuits.Single(item => item.Id == "F1-D171-C02");
        Check(c01.SystemRole == "FLOOR_HEATING_AXIS" && c02.SystemRole == "FLOOR_HEATING_AXIS",
            "D174 upper candidates are not falsely complete loops");
        Check(c01.HeatingBodyRanges.Count == 2 &&
              c01.HeatingBodyRanges[0].StartIndex == 0 && c01.HeatingBodyRanges[0].EndIndex == 2 &&
              c01.HeatingBodyRanges[1].StartIndex == 5 && c01.HeatingBodyRanges[1].EndIndex == 32,
            "D174 C01 multi-range classification");
        Check(c02.HeatingBodyRanges.Count == 3 &&
              c02.HeatingBodyRanges[0].StartIndex == 0 && c02.HeatingBodyRanges[0].EndIndex == 2 &&
              c02.HeatingBodyRanges[1].StartIndex == 7 && c02.HeatingBodyRanges[1].EndIndex == 9 &&
              c02.HeatingBodyRanges[2].StartIndex == 13 && c02.HeatingBodyRanges[2].EndIndex == 35,
            "D174 C02 multi-range classification");
        Check(c01.SupplyPortIndex is null && c01.ReturnPortIndex is null &&
              c02.SupplyPortIndex is null && c02.ReturnPortIndex is null,
            "D174 moves K1 ownership to lower service legs");
        foreach (var upper in new[] { c01, c02 })
        {
            var analysis = CircuitAnalyzer.Analyze(project, upper);
            Check(analysis.SelfIntersections == 0 && analysis.InterCircuitIntersections == 0,
                $"D174 {upper.Id} upper topology");
            Check(analysis.BendRadiusViolationCount == 0, $"D174 {upper.Id} R80");
            Check(analysis.HeatingBodyInsideAssignedRoom && analysis.HeatingBodyWallIntrusions == 0,
                $"D174 {upper.Id} body room/wall classification");
            Check(analysis.TransitWallIntersections > 0, $"D174 {upper.Id} explicit transit wall crossings");
        }

        var fragmentIds = new[]
        {
            "F1-D174-C02-SUPPLY", "F1-D174-C02-RETURN",
            "F1-D174-C01-SUPPLY", "F1-D174-C01-RETURN",
        };
        var fragments = fragmentIds.Select(id => project.Circuits.Single(item => item.Id == id)).ToArray();
        Check(fragments.All(item => item.SystemRole == "FLOOR_SERVICE_LEG" &&
                                    item.RoutingLayer == "LOWER_SERVICE_LAYER" && item.AxisElevationMm == 70),
            "D174 lower service role and elevation");
        Check(fragments.Select(item => item.SupplyPortIndex ?? item.ReturnPortIndex).Order()
              .SequenceEqual(new int?[] { 0, 1, 2, 3 }), "D174 four unique K1 ports");
        var lengths = fragments.ToDictionary(item => item.Id, item => Manhattan(item.OrderedPoints));
        Check(lengths["F1-D174-C02-SUPPLY"] == 3_800 && lengths["F1-D174-C02-RETURN"] == 7_900 &&
              lengths["F1-D174-C01-SUPPLY"] == 8_100 && lengths["F1-D174-C01-RETURN"] == 3_800,
            "D174 exact lower service lengths");
        foreach (var fragment in fragments)
        {
            var analysis = CircuitAnalyzer.Analyze(project, fragment);
            Check(analysis.SelfIntersections == 0 && analysis.InterCircuitIntersections == 0,
                $"D174 {fragment.Id} lower topology");
            Check(analysis.BendRadiusViolationCount == 0, $"D174 {fragment.Id} lower R80");
            Check(analysis.DifferentLayerCrossingsIgnored > 0, $"D174 {fragment.Id} records separated crossings");
            Check(analysis.WallIntersections == 3, $"D174 {fragment.Id} crosses three vertical wall axes");
        }
        Check(MinimumPolylineDistance(fragments) >= 200, "D174 lower service spacing");

        using var contractDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_lower_service_pair_contract.json")));
        var contract = contractDocument.RootElement;
        Check(contract.GetProperty("status").GetString() ==
              "BALANCED_MULTI_RANGE_PAIR_GEOMETRY_PASS_REWORK_3D_RAMPS_AND_WHOLE_FLOOR_R80", "D174 bounded status");
        Check(contract.GetProperty("source_D173_project_sha256").GetString() == Sha(sourcePath), "D174 source hash");
        Check(contract.GetProperty("unchanged_circuit_point_arrays_preserved").GetBoolean(), "D174 preservation claim");
        var validation = contract.GetProperty("fragment_validation");
        Check(validation.GetProperty("upper_pair_contact_count").GetInt32() == 0 &&
              validation.GetProperty("lower_service_contact_count").GetInt32() == 0 &&
              validation.GetProperty("minimum_lower_service_centerline_mm").GetDouble() == 200 &&
              validation.GetProperty("R80_tangent_allocation_violation_count").GetInt32() == 0,
            "D174 stored topology/R80");
        var coverage = contract.GetProperty("coverage_diagnostic");
        Check(Math.Abs(coverage.GetProperty("sharp_axis_round100_served_percent").GetDouble() - 98.225540746947) < 1e-9,
            "D174 sharp coverage recompute");
        Check(Math.Abs(coverage.GetProperty("R80_filleted_axis_round100_served_percent").GetDouble() - 96.81735098647324) < 1e-9,
            "D174 physical R80 coverage recompute");
        Check(coverage.GetProperty("R80_filleted_axis_50mm_sample_max_distance_mm").GetDouble() < 175 &&
              coverage.GetProperty("R80_filleted_all_samples_within200").GetBoolean(),
            "D174 R80 no-large-void evidence");
        var exterior = contract.GetProperty("exterior_3x100");
        Check(exterior.GetProperty("raw_full_face_90_percent_pass_count").GetInt32() == 4 &&
              exterior.GetProperty("R80_corner_envelope_90_percent_pass_count").GetInt32() == 6 &&
              exterior.GetProperty("window_projection_covered_by_all_left_passes").GetBoolean(),
            "D174 honest 3x100 exterior evidence");
        var routes = contract.GetProperty("logical_route_candidates");
        Check(Math.Abs(routes.GetProperty("F1-D171-C02").GetProperty("nominal_3D_rounded_length_mm").GetDouble() - 54_945.91118430775) < 1e-6,
            "D174 C02 nominal length");
        Check(Math.Abs(routes.GetProperty("F1-D171-C01").GetProperty("nominal_3D_rounded_length_mm").GetDouble() - 53_980.24747816499) < 1e-6,
            "D174 C01 nominal length");
        Check(contract.GetProperty("nominal_3D_rounded_length_spread_mm").GetDouble() < 1_000 &&
              contract.GetProperty("pair_balance_candidate_pass").GetBoolean(), "D174 balanced pair candidate");
        Check(contract.GetProperty("whole_floor_R80_violation_count_in_unchanged_routes").GetInt32() == 16 &&
              contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D174 remaining-work honesty");

        using var diagnosticsDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "engineering_diagnostics.json")));
        var exported = diagnosticsDocument.RootElement.GetProperty("circuits").EnumerateArray().
            Where(item => fragmentIds.Contains(item.GetProperty("circuit_id").GetString())).ToArray();
        Check(exported.Length == 4 && exported.All(item => item.GetProperty("bend_radius_violation_count").GetInt32() == 0),
            "D174 exported lower diagnostics");
        foreach (var name in new[]
        {
            "HomeAura_Floor1_D174_Editor_View.png", "HomeAura_Floor1_D174_Clean_View.png",
            "HomeAura_Floor1_D174_F1-R08_Zoom.png", "HomeAura_Floor1_D174_F1-R08_Diagnostics.png",
        }) Check(File.Exists(Path.Combine(directory, name)), $"D174 image {name}");
        VerifyPackage(directory, Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174.zip"));
    }

    private static void VerifyPackage(string directory, string package)
    {
        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D174 manifest {path}");
        }
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D174 ZIP member count");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open(); using var memory = new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D174 ZIP parity {entry.FullName}");
        }
    }

    private static double MinimumPolylineDistance(IReadOnlyList<ManualCircuit> circuits)
    {
        var minimum = double.PositiveInfinity;
        for (var i = 0; i < circuits.Count; i++)
        for (var j = i + 1; j < circuits.Count; j++)
        foreach (var first in Segments(circuits[i].OrderedPoints))
        foreach (var second in Segments(circuits[j].OrderedPoints))
            minimum = Math.Min(minimum, SegmentDistance(first, second));
        return minimum;
    }
    private static IEnumerable<(PointMm A, PointMm B)> Segments(IReadOnlyList<PointMm> points)
    { for (var i = 0; i + 1 < points.Count; i++) yield return (points[i], points[i + 1]); }
    private static double SegmentDistance((PointMm A, PointMm B) first, (PointMm A, PointMm B) second) =>
        new[] { DistanceToSegment(first.A,second.A,second.B),DistanceToSegment(first.B,second.A,second.B),
                DistanceToSegment(second.A,first.A,first.B),DistanceToSegment(second.B,first.A,first.B) }.Min();
    private static double DistanceToSegment(PointMm point, PointMm first, PointMm second)
    {
        var dx=second.X-first.X; var dy=second.Y-first.Y; var denominator=(double)dx*dx+(double)dy*dy;
        var t=denominator==0?0:Math.Clamp(((point.X-first.X)*dx+(point.Y-first.Y)*dy)/denominator,0,1);
        var x=first.X+t*dx; var y=first.Y+t*dy;
        return Math.Sqrt(Math.Pow(point.X-x,2)+Math.Pow(point.Y-y,2));
    }
    private static int Manhattan(IReadOnlyList<PointMm> points) => points.Zip(points.Skip(1)).
        Sum(pair => Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y));
    private static IEnumerable<string> Points(ManualCircuit circuit) => circuit.OrderedPoints.Select(point => $"{point.X},{point.Y}");
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Check(bool condition, string message)
    { if (!condition) throw new InvalidDataException(message); }
}
