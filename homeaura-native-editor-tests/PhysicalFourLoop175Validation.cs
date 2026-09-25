using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class PhysicalFourLoop175Validation
{
    private static readonly string[] ChangedIds =
    [
        "F1-D171-C01", "F1-D171-C02", "F1-D171-C13", "F1-D175-C14",
    ];

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_LOWER_SERVICE_PAIR_174");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_LowerServicePair_D174.homeaura.json");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_PhysicalFourLoop_D175.homeaura.json");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == 14, "D175 must contain C01-C14 and no detached service fragments.");
        var removed = new HashSet<string>
        {
            "F1-D174-C02-SUPPLY", "F1-D174-C02-RETURN",
            "F1-D174-C01-SUPPLY", "F1-D174-C01-RETURN",
        };
        Check(project.Circuits.All(item => !removed.Contains(item.Id)), "D175 retained a detached D174 service leg.");

        var changedExisting = new HashSet<string> { "F1-D171-C01", "F1-D171-C02", "F1-D171-C13" };
        foreach (var sourceCircuit in source.Circuits.Where(item => !changedExisting.Contains(item.Id) && !removed.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == sourceCircuit.Id);
            Check(Serialize(current) == Serialize(sourceCircuit), $"D175 changed preserved record {sourceCircuit.Id}.");
        }

        ValidateCollectors(source, project);
        ValidateCircuit(project, "F1-D171-C01", 35, new[] { (1,3), (6,33) },
            new[] { 0,3,5,33 }, 53_906.16058463464, 0, 1);
        ValidateCircuit(project, "F1-D171-C02", 42, new[] { (3,5), (10,12), (16,38) },
            new[] { 0,2,5,9,12,15,38 }, 55_465.396936873585, 2, 3);
        ValidateCircuit(project, "F1-D171-C13", 59, new[] { (3,56) },
            new[] { 2,56 }, 75_063.9648319174, 24, 25);
        ValidateCircuit(project, "F1-D175-C14", 56, new[] { (1,54) },
            new[] { 0,3,4,54 }, 72_412.04441754727, 26, 27);

        ValidateExactTransitions(project);
        ValidateExactPoint3Chains(project);
        ValidateHallBodySeparation(project);
        ValidatePortAllocation(project);
        ValidateContractAndDiagnostics(directory, sourcePath);
        ValidateFilesAndPackage(directory, Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175.zip"));
    }

    private static void ValidateCollectors(HomeAuraProject source, HomeAuraProject project)
    {
        var sourceK2 = source.Collectors.Single(item => item.Id == "K2");
        var k1 = project.Collectors.Single(item => item.Id == "K1");
        var k2 = project.Collectors.Single(item => item.Id == "K2");
        foreach (var collector in new[] { k1, k2 })
        {
            Check(collector.Ports == 28 && collector.LoopCount == 14 && collector.ConnectionPointCount == 28,
                $"{collector.Id} is not a physical FM14.");
            Check(collector.Manufacturer == "Uponor" && collector.PartNumber == "1140845" &&
                  collector.ReferenceLengthMm == 814 && collector.LoopConnectionPitchMm == 50 && collector.HeaderPitchMm == 225,
                $"{collector.Id} official reference fields changed.");
            Check(collector.MountingWallId == "FLOOR_1-W025" && collector.ConnectionPoints?.Count == 28,
                $"{collector.Id} wall or explicit connection lattice changed.");
            var points = collector.ConnectionPoints!.OrderBy(item => item.ConnectionIndex).ToArray();
            for (var loop = 0; loop < 14; loop++)
            {
                var supply = points[loop * 2]; var returned = points[loop * 2 + 1];
                Check(supply.LoopIndex == loop && returned.LoopIndex == loop &&
                      supply.Header == "SUPPLY" && returned.Header == "RETURN" &&
                      Math.Abs(supply.LocalPositionMm.X - (-325 + 50 * loop)) < 0.001 &&
                      Math.Abs(returned.LocalPositionMm.X - supply.LocalPositionMm.X) < 0.001 &&
                      Math.Abs(supply.LocalPositionMm.Y + 112.5) < 0.001 && Math.Abs(returned.LocalPositionMm.Y - 112.5) < 0.001,
                    $"{collector.Id} loop {loop} port pairing changed.");
            }
        }
        Check(k1.RotationDegrees == 0 && k2.RotationDegrees == 180, "D175 collector orientation changed.");
        Check(k2.Position.X == sourceK2.Position.X && k2.Position.Y == sourceK2.Position.Y &&
              k2.ServedFloorId == sourceK2.ServedFloorId && k2.PipeOutletDirection == sourceK2.PipeOutletDirection,
            "D175 changed the preserved K2 placement/role contract.");
    }

    private static void ValidateCircuit(
        HomeAuraProject project, string id, int pointCount, IReadOnlyList<(int Start, int End)> ranges,
        IReadOnlyList<int> transitionSegments, double expectedRoundedLength, int supplyPort, int returnPort)
    {
        var circuit = project.Circuits.Single(item => item.Id == id);
        Check(circuit.SystemRole == "FLOOR_HEATING_LOOP" && circuit.Completed && circuit.CollectorId == "K1",
            $"{id} is not a complete K1 Point3 loop.");
        Check(circuit.SupplyPortIndex == supplyPort && circuit.ReturnPortIndex == returnPort,
            $"{id} port allocation changed.");
        Check(circuit.OrderedPoints.Count == pointCount && circuit.OrderedPoints.All(point => point.Z is not null),
            $"{id} Point3 chain changed.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex,item.EndIndex)).SequenceEqual(ranges),
            $"{id} body ranges changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual(transitionSegments),
            $"{id} transition indices changed.");
        Check(MinimumPlanSegment(circuit.OrderedPoints) >= 200, $"{id} has an ordered plan segment below 200 mm.");

        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.TopologyPass && analysis.EngineeringPass && analysis.VerticalGeometryMaterialized,
            $"{id} physical route no longer passes topology/engineering.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0,
            $"{id} has an unintended 3D contact.");
        Check(analysis.MinimumInterCircuitSurfaceClearanceMm is null or >= 5 - 0.051,
            $"{id} layer surface clearance fell below 5 mm.");
        Check(analysis.BendRadiusViolationCount == 0 && analysis.HeatingBodyWallIntrusions == 0 &&
              analysis.HeatingBodyInsideAssignedRoom, $"{id} R80/body-wall gate failed.");
        Check(analysis.StartAtCollector && analysis.EndAtCollector, $"{id} collector terminal contract failed.");
        Close(expectedRoundedLength, analysis.RoundedAxisLengthMm, 0.003, $"{id} physical rounded length");
    }

    private static void ValidateExactTransitions(HomeAuraProject project)
    {
        var expected = new Dictionary<string, (int Segment, int Rise, double Start, double End)[]>
        {
            ["F1-D171-C01"] = [(0,38,7900,96.481886),(3,38,0,496.481886),(5,38,100,396.481886),(33,38,0,3696.481886)],
            ["F1-D171-C02"] = [(0,65,71.256068,0),(2,27,100,11.056198),(5,38,0,496.481886),(9,38,100,196.481886),
                                    (12,27,0,611.056198),(15,27,100,211.056198),(38,38,0,96.481886)],
            ["F1-D171-C13"] = [(2,38,96.481886,0),(56,38,0,996.481886)],
            ["F1-D175-C14"] = [(0,38,896.481886,0),(3,27,80,31.056198),(4,27,31.056198,80),(54,38,0,1696.481886)],
        };
        foreach (var (id, records) in expected)
        {
            var circuit = project.Circuits.Single(item => item.Id == id);
            var analysis = CircuitAnalyzer.Analyze(project, circuit);
            Check(analysis.VerticalTransitions.Count == records.Length, $"{id} transition count changed.");
            for (var index = 0; index < records.Length; index++)
            {
                var actual = analysis.VerticalTransitions[index]; var record = records[index];
                Check(actual.CircuitSegmentIndex == record.Segment && Math.Abs(actual.VerticalDeltaMm - record.Rise) < 0.001 &&
                      actual.MaterializedPass && actual.RadiusMm == 80,
                    $"{id} transition {index} materialization changed.");
                Close(record.Start, actual.StartTangentLengthMm, 0.000001, $"{id} transition {index} start tangent");
                Close(record.End, actual.EndTangentLengthMm, 0.000001, $"{id} transition {index} end tangent");
            }
        }
    }

    private static void ValidateExactPoint3Chains(HomeAuraProject project)
    {
        var c13 = project.Circuits.Single(item => item.Id == "F1-D171-C13");
        Check(Point(c13,0) == "16000,12200,70" && Point(c13,1) == "16000,16900,70" &&
              Point(c13,2) == "15500,16900,70" && Point(c13,3) == "15300,16900,108" &&
              Point(c13,56) == "15300,17600,108" && Point(c13,57) == "16400,17600,70" && Point(c13,58) == "16400,13100,70",
            "D175 C13 exact supply/body/return endpoints changed.");
        var c14 = project.Circuits.Single(item => item.Id == "F1-D175-C14");
        Check(Point(c14,0) == "16400,8900,70" && Point(c14,1) == "15400,8900,108" &&
              Point(c14,2) == "12900,8900,108" && Point(c14,3) == "12900,12000,108" &&
              Point(c14,4) == "12900,12200,135" && Point(c14,5) == "12900,12400,108" &&
              Point(c14,54) == "14100,12900,108" && Point(c14,55) == "15900,12900,70",
            "D175 C14 exact band/overpass/return endpoints changed.");
    }

    private static void ValidateHallBodySeparation(HomeAuraProject project)
    {
        var c13 = project.Circuits.Single(item => item.Id == "F1-D171-C13");
        var c14 = project.Circuits.Single(item => item.Id == "F1-D175-C14");
        var first = BodySegments(c13).ToArray(); var second = BodySegments(c14).ToArray();
        var minimum = first.SelectMany(a => second.Select(b => SegmentDistance(a,b))).Min();
        Close(200, minimum, 0.000001, "C13/C14 minimum body spacing");
    }

    private static void ValidatePortAllocation(HomeAuraProject project)
    {
        var ports = project.Circuits.Where(item => item.CollectorId == "K1")
            .SelectMany(item => new[] { item.SupplyPortIndex, item.ReturnPortIndex }).Where(item => item is not null)
            .Select(item => item!.Value).Order().ToArray();
        Check(ports.SequenceEqual(Enumerable.Range(0, 28)), "D175 K1 does not use each FM14 connection exactly once.");
        Check(project.Circuits.Count(item => ChangedIds.Contains(item.Id) &&
              CircuitAnalyzer.Analyze(project,item).TopologyPass && CircuitAnalyzer.Analyze(project,item).StartAtCollector &&
              CircuitAnalyzer.Analyze(project,item).EndAtCollector) == 4, "D175 bounded terminal-grid route count changed.");
    }

    private static void ValidateContractAndDiagnostics(string directory, string sourcePath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_physical_four_loop_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("status").GetString() == "FOUR_POINT3_FLOOR_ROUTES_PASS_COLLECTOR_TERMINALS_REWORK" &&
              contract.GetProperty("source_D174_project_sha256").GetString() == Sha(sourcePath), "D175 lineage/status changed.");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              contract.GetProperty("bounded_terminal_grid_route_count").GetInt32() == 4 &&
              contract.GetProperty("materialized_floor_plane_route_count").GetInt32() == 4 &&
              !contract.GetProperty("installation_ready").GetBoolean() &&
              contract.GetProperty("whole_floor_R80_violation_count_in_unchanged_routes").GetInt32() == 16,
            "D175 bounded completion honesty changed.");
        var lengths = contract.GetProperty("route_metrics");
        Close(53_906.16058463464, lengths.GetProperty("F1-D171-C01").GetProperty("rounded_physical_axis_length_mm").GetDouble(), .000001, "stored C01 length");
        Close(55_465.396936873585, lengths.GetProperty("F1-D171-C02").GetProperty("rounded_physical_axis_length_mm").GetDouble(), .000001, "stored C02 length");
        Close(75_063.9648319174, lengths.GetProperty("F1-D171-C13").GetProperty("rounded_physical_axis_length_mm").GetDouble(), .000001, "stored C13 length");
        Close(72_412.04441754727, lengths.GetProperty("F1-D175-C14").GetProperty("rounded_physical_axis_length_mm").GetDouble(), .000001, "stored C14 length");
        Close(2_651.9204143701354, contract.GetProperty("hall_pair_rounded_length_spread_mm").GetDouble(), .000001, "hall spread");
        var coverage = contract.GetProperty("hall_coverage");
        Close(27.418652, coverage.GetProperty("domain_area_m2").GetDouble(), .0000001, "hall routable domain");
        Close(95.06497455572112, coverage.GetProperty("sharp_axis_round100").GetProperty("served_percent").GetDouble(), .0000001, "sharp q16 coverage");
        Close(93.34835536973114, coverage.GetProperty("physical_R80_axis_round100").GetProperty("served_percent").GetDouble(), .0000001, "R80 q16 coverage");
        Check(coverage.GetProperty("physical_R80_axis_round100").GetProperty("q16_buffer_resolution").GetInt32() == 16 &&
              !coverage.GetProperty("proxy_is_heat_loss_or_hydraulic_certificate").GetBoolean(), "D175 coverage claim boundary changed.");
        var exterior = contract.GetProperty("exterior_W016_3x100");
        Check(exterior.GetProperty("raw_full_span_pass_by_lane").EnumerateArray().Select(item => item.GetBoolean()).SequenceEqual(new[] { true,false,false }) &&
              exterior.GetProperty("R80_nested_envelope_pass_by_lane").EnumerateArray().All(item => item.GetBoolean()) &&
              exterior.GetProperty("raw_and_corner_envelope_are_not_conflated").GetBoolean(), "D175 W016 honest 3x100 evidence changed.");

        using var diagnostics = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "engineering_diagnostics.json")));
        var records = diagnostics.RootElement.GetProperty("circuits").EnumerateArray()
            .Where(item => ChangedIds.Contains(item.GetProperty("circuit_id").GetString())).ToArray();
        Check(records.Length == 4 && records.All(item => item.GetProperty("topology_pass").GetBoolean() &&
              item.GetProperty("engineering_pass").GetBoolean() && item.GetProperty("vertical_geometry_materialized").GetBoolean()),
            "D175 exported changed-route diagnostics regressed.");
    }

    private static void ValidateFilesAndPackage(string directory, string package)
    {
        foreach (var name in new[]
        {
            "HomeAura_Floor1_D175_Editor_View.png", "HomeAura_Floor1_D175_Clean_View.png",
            "HomeAura_Floor1_D175_F1-R02_Zoom.png", "HomeAura_Floor1_D175_F1-R02_Clean_Zoom.png",
            "HomeAura_Floor1_D175_F1-R04_Collectors_Zoom.png", "HomeAura_Floor1_D175_3D_Layer_Debug.png",
            "collector_manufacturer_contract.json", "engineering_diagnostics.json",
        }) Check(new FileInfo(Path.Combine(directory,name)) is { Exists: true, Length: > 0 }, $"D175 file {name} missing.");

        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory,item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D175 manifest mismatch for {path}.");
        }
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D175 ZIP member count changed.");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open(); using var memory = new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory,entry.FullName))),
                $"D175 ZIP byte parity failed for {entry.FullName}.");
        }
    }

    private static IEnumerable<(PointMm A, PointMm B)> BodySegments(ManualCircuit circuit)
    {
        foreach (var range in circuit.HeatingBodyRanges)
        for (var index = range.StartIndex; index < range.EndIndex; index++)
            yield return (circuit.OrderedPoints[index], circuit.OrderedPoints[index + 1]);
    }

    private static double SegmentDistance((PointMm A,PointMm B) first, (PointMm A,PointMm B) second) =>
        new[] { PointSegment(first.A,second), PointSegment(first.B,second), PointSegment(second.A,first), PointSegment(second.B,first) }.Min();

    private static double PointSegment(PointMm point, (PointMm A,PointMm B) segment)
    {
        var dx=segment.B.X-segment.A.X; var dy=segment.B.Y-segment.A.Y; var denominator=(double)dx*dx+(double)dy*dy;
        var t=denominator==0?0:Math.Clamp(((point.X-segment.A.X)*dx+(point.Y-segment.A.Y)*dy)/denominator,0,1);
        return Math.Sqrt(Math.Pow(point.X-(segment.A.X+t*dx),2)+Math.Pow(point.Y-(segment.A.Y+t*dy),2));
    }

    private static double MinimumPlanSegment(IReadOnlyList<PointMm> points) => points.Zip(points.Skip(1))
        .Min(pair => Math.Sqrt(Math.Pow(pair.First.X-pair.Second.X,2)+Math.Pow(pair.First.Y-pair.Second.Y,2)));
    private static string Point(ManualCircuit circuit, int index) =>
        $"{circuit.OrderedPoints[index].X},{circuit.OrderedPoints[index].Y},{circuit.OrderedPoints[index].Z}";
    private static string Serialize(ManualCircuit circuit) => JsonSerializer.Serialize(circuit,HomeAuraProject.JsonOptions);
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected,double actual,double tolerance,string label)
    { if (Math.Abs(expected-actual)>tolerance) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Check(bool condition,string message)
    { if (!condition) throw new InvalidDataException(message); }
}
