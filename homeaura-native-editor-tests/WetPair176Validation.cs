using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class WetPair176Validation
{
    private static readonly string[] ChangedIds = ["F1-D171-C10", "F1-D171-C11"];

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourcePath = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_PHYSICAL_FOUR_LOOP_175",
            "HomeAura_Floor1_PhysicalFourLoop_D175.homeaura.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_WetPair_D176.homeaura.json");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == source.Circuits.Count, "D176 changed the circuit count.");
        foreach (var sourceCircuit in source.Circuits.Where(item => !ChangedIds.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == sourceCircuit.Id);
            Check(Serialize(current) == Serialize(sourceCircuit), $"D176 changed preserved record {sourceCircuit.Id}.");
        }

        ValidateCircuit(project, "F1-D171-C10", 62,
            [(5,7),(12,24),(28,31),(36,53)], [4,7,11,24,27,31,35,54,55,57],
            77_463.08716343122, 18, 19,
            ["15900,11600,70", "10600,19200,108", "8500,18800,108",
             "10400,18600,108", "12200,17500,108", "16200,11600,70"],
            [0,5,12,28,36,61], 0);
        ValidateCircuit(project, "F1-D171-C11", 64,
            [(5,26),(31,33),(34,35),(38,55),(58,59)], [4,26,30,35,37,55,57,59],
            77_199.17694409931, 20, 21,
            ["16000,11600,135", "7900,15900,108", "7800,15900,108",
             "11000,19100,108", "12000,18600,108", "11000,19200,108", "16900,11600,135"],
            [0,5,31,34,38,58,63], 2);

        ValidateExteriorBodies(project);
        ValidateWallSolids(project);
        ValidatePortsAndCollectorTailBoundary(project);
        ValidateContractAndDiagnostics(directory, sourcePath);
        ValidateFilesAndPackage(directory,
            Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_WET_PAIR_176.zip"));
    }

    private static void ValidateCircuit(
        HomeAuraProject project, string id, int pointCount, IReadOnlyList<(int Start,int End)> ranges,
        IReadOnlyList<int> transitionSegments, double expectedLength, int supplyPort, int returnPort,
        IReadOnlyList<string> expectedPoints, IReadOnlyList<int> pointIndices,
        int expectedHorizontalTurnWallIntrusions)
    {
        var circuit = project.Circuits.Single(item => item.Id == id);
        Check(circuit.OrderedPoints.Count == pointCount && circuit.OrderedPoints.All(item => item.Z is not null),
            $"{id} Point3 chain changed.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex,item.EndIndex)).SequenceEqual(ranges),
            $"{id} heating-body ranges changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual(transitionSegments),
            $"{id} transition indices changed.");
        Check(circuit.SupplyPortIndex == supplyPort && circuit.ReturnPortIndex == returnPort,
            $"{id} FM14 port assignment changed.");
        Check(MinimumPlanSegment(circuit.OrderedPoints) >= 200, $"{id} contains a sub-200 mm ordered segment.");
        for (var index = 0; index < pointIndices.Count; index++)
            Check(Point(circuit, pointIndices[index]) == expectedPoints[index], $"{id} exact point {pointIndices[index]} changed.");

        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.TopologyPass && analysis.VerticalGeometryMaterialized,
            $"{id} topology/materialization gate failed.");
        Check(analysis.HorizontalTurnWallIntrusions == expectedHorizontalTurnWallIntrusions &&
              analysis.HorizontalTurnWallClearancePass == (expectedHorizontalTurnWallIntrusions == 0) &&
              analysis.EngineeringPass == (expectedHorizontalTurnWallIntrusions == 0),
            $"{id} historical physical R80 wall-turn classification changed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.SelfSurfaceClearanceViolationDetails.Count == 0 && analysis.InterCircuitIntersections == 0 &&
              analysis.InterCircuitSurfaceClearanceViolations == 0,
            $"{id} has an unintended 3D contact.");
        Check(analysis.MinimumInterCircuitSurfaceClearanceMm is >= 11 - 0.051,
            $"{id} global physical surface clearance fell below 11 mm.");
        Check(analysis.BendRadiusViolationCount == 0 && analysis.VerticalTransitions.All(item =>
                  item.MaterializedPass && item.RadiusMm == 80 &&
                  Math.Abs(item.StartTangentLengthMm + item.RequiredArcProjectionMm + item.EndTangentLengthMm - item.PlanProjectionMm) <= 0.05),
            $"{id} R80/transition closure failed.");
        Check(analysis.HeatingBodyWallIntrusions == 0 && analysis.HeatingBodyInsideAssignedRoom,
            $"{id} heating body entered a wall or left the assigned room.");
        Check(analysis.StartAtCollector && analysis.EndAtCollector, $"{id} bounded terminal-grid test failed.");
        Close(expectedLength, analysis.RoundedAxisLengthMm, 0.003, $"{id} physical rounded length");
    }

    private static void ValidateExteriorBodies(HomeAuraProject project)
    {
        var bodies = project.Circuits.Where(item => ChangedIds.Contains(item.Id))
            .SelectMany(BodySegments).ToArray();
        var south = new[]
        {
            (Y:19200, West:(7700,10600), East:(11000,12200)),
            (Y:19100, West:(7800,10600), East:(11000,12200)),
            (Y:19000, West:(7900,10600), East:(11000,12200)),
        };
        foreach (var lane in south)
        {
            Close(lane.West.Item2-lane.West.Item1, HorizontalCoverage(bodies,lane.Y,lane.West), .001, $"south west lane {lane.Y}");
            Close(lane.East.Item2-lane.East.Item1, HorizontalCoverage(bodies,lane.Y,lane.East), .001, $"south east lane {lane.Y}");
            Close(1500, HorizontalCoverage(bodies,lane.Y,(8200,9700)), .001, $"WIN-03 lane {lane.Y}");
        }
        var west = new[] { (X:7700, Span:(15900,19200)), (X:7800, Span:(15900,19100)), (X:7900, Span:(15900,19000)) };
        foreach (var lane in west)
            Close(lane.Span.Item2-lane.Span.Item1, VerticalCoverage(bodies,lane.X,lane.Span), .001, $"west lane {lane.X}");
    }

    private static void ValidateWallSolids(HomeAuraProject project)
    {
        var intersections = 0;
        foreach (var circuit in project.Circuits.Where(item => ChangedIds.Contains(item.Id)))
        {
            var bodyIndices = circuit.HeatingBodyRanges
                .SelectMany(range => Enumerable.Range(range.StartIndex, range.EndIndex-range.StartIndex)).ToHashSet();
            for (var index = 0; index + 1 < circuit.OrderedPoints.Count; index++)
            foreach (var wall in project.Walls)
            {
                var first = circuit.OrderedPoints[index]; var second = circuit.OrderedPoints[index+1];
                if (!TouchesWallSolid(first,second,wall)) continue;
                intersections++;
                Check(!bodyIndices.Contains(index), $"{circuit.Id} BODY segment {index} touches {wall.Id}.");
                var segmentHorizontal = first.Y == second.Y; var segmentVertical = first.X == second.X;
                var wallHorizontal = wall.Start.Y == wall.End.Y; var wallVertical = wall.Start.X == wall.End.X;
                Check(wallHorizontal && segmentVertical || wallVertical && segmentHorizontal,
                    $"{circuit.Id} TRANSIT segment {index} runs longitudinally in {wall.Id}.");
            }
        }
        Check(intersections == 41, $"D176 changed wall-solid intersection count: {intersections}.");
    }

    private static void ValidatePortsAndCollectorTailBoundary(HomeAuraProject project)
    {
        var ports = project.Circuits.Where(item => item.CollectorId == "K1")
            .SelectMany(item => new[] { item.SupplyPortIndex,item.ReturnPortIndex }).Where(item => item is not null)
            .Select(item => item!.Value).Order().ToArray();
        Check(ports.SequenceEqual(Enumerable.Range(0,28)), "D176 no longer allocates each FM14 connection exactly once.");
        var collector = project.Collectors.Single(item => item.Id == "K1");
        foreach (var circuit in project.Circuits.Where(item => ChangedIds.Contains(item.Id)))
        {
            foreach (var (point,port) in new[]
            {
                (circuit.OrderedPoints[0],circuit.SupplyPortIndex!.Value),
                (circuit.OrderedPoints[^1],circuit.ReturnPortIndex!.Value),
            })
            {
                var connection = collector.ResolveConnectionPoints().Single(item => item.ConnectionIndex == port);
                var target = collector.ConnectionPointWorldPosition(connection,collector.MountingWallAngleDegrees(project));
                var resolved = CircuitAnalyzer.ResolvePoint3(circuit,point);
                var gap = CircuitAnalyzer.Distance3(resolved,target);
                Check(gap > 2_400, $"{circuit.Id} unexpectedly claims a fabricated Eurocone tail ({gap} mm).");
            }
        }
    }

    private static void ValidateContractAndDiagnostics(string directory, string sourcePath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"floor1_wet_pair_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("source_D175_project_sha256").GetString() == Sha(sourcePath) &&
              contract.GetProperty("status").GetString() == "SIX_POINT3_FLOOR_ROUTES_PASS_COLLECTOR_TERMINALS_REWORK",
            "D176 lineage/status changed.");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              contract.GetProperty("bounded_terminal_grid_route_count").GetInt32() == 6 &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D176 completion boundary changed.");
        Close(263.9102193318831, contract.GetProperty("pair_rounded_length_spread_mm").GetDouble(), .000001, "D176 spread");
        var coverage = contract.GetProperty("wet_coverage").GetProperty("physical_R80_axis_round100");
        Close(93.89318869906187, coverage.GetProperty("served_percent").GetDouble(), .000001, "D176 R80 coverage");
        Close(252.88285560290876, coverage.GetProperty("maximum_sample_distance_mm").GetDouble(), .000001, "D176 maximum gap");
        Check(contract.GetProperty("exterior_3x100").GetProperty("all_partition_aware_gates_pass").GetBoolean() &&
              contract.GetProperty("exterior_3x100").GetProperty("window_projection")
                  .GetProperty("covered_by_all_three_south_lanes").GetBoolean(), "D176 exterior/window evidence failed.");
        var wall = contract.GetProperty("wall_solid_transit_audit");
        Check(wall.GetProperty("pass").GetBoolean() && wall.GetProperty("intersection_count").GetInt32() == 41 &&
              wall.GetProperty("body_wall_hit_count").GetInt32() == 0 &&
              wall.GetProperty("longitudinal_or_nonperpendicular_transit_count").GetInt32() == 0,
            "D176 stored wall-solid audit changed.");

        using var diagnostics = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"engineering_diagnostics.json")));
        var records = diagnostics.RootElement.GetProperty("circuits").EnumerateArray()
            .Where(item => ChangedIds.Contains(item.GetProperty("circuit_id").GetString())).ToArray();
        Check(records.Length == 2 && records.All(item => item.GetProperty("topology_pass").GetBoolean() &&
              item.GetProperty("self_intersections").GetInt32() == 0 &&
              item.GetProperty("inter_circuit_surface_clearance_violations").GetInt32() == 0),
            "D176 historical exported diagnostics changed.");
    }

    private static void ValidateFilesAndPackage(string directory, string package)
    {
        foreach (var name in new[]
        {
            "HomeAura_Floor1_D176_Editor_View.png", "HomeAura_Floor1_D176_Clean_View.png",
            "HomeAura_Floor1_D176_WetPair_Zoom.png", "HomeAura_Floor1_D176_WetPair_Clean_Zoom.png",
            "HomeAura_Floor1_D176_WetPair_3D_Debug.png", "engineering_diagnostics.json",
        }) Check(new FileInfo(Path.Combine(directory,name)) is { Exists:true, Length:>0 }, $"D176 file {name} missing.");

        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory,item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D176 manifest mismatch for {path}.");
        }
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D176 ZIP member count changed.");
        foreach (var entry in archive.Entries)
        {
            using var stream=entry.Open(); using var memory=new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory,entry.FullName))),
                $"D176 ZIP byte parity failed for {entry.FullName}.");
        }
    }

    private static IEnumerable<(PointMm A,PointMm B)> BodySegments(ManualCircuit circuit)
    {
        foreach (var range in circuit.HeatingBodyRanges)
        for (var index=range.StartIndex; index<range.EndIndex; index++)
            yield return (circuit.OrderedPoints[index],circuit.OrderedPoints[index+1]);
    }

    private static double HorizontalCoverage(IEnumerable<(PointMm A,PointMm B)> segments, int y, (int From,int To) required) =>
        Merge(segments.Where(item => item.A.Y == y && item.B.Y == y)
            .Select(item => (Math.Max(required.From,Math.Min(item.A.X,item.B.X)),Math.Min(required.To,Math.Max(item.A.X,item.B.X)))))
            .Sum(item => item.To-item.From);
    private static double VerticalCoverage(IEnumerable<(PointMm A,PointMm B)> segments, int x, (int From,int To) required) =>
        Merge(segments.Where(item => item.A.X == x && item.B.X == x)
            .Select(item => (Math.Max(required.From,Math.Min(item.A.Y,item.B.Y)),Math.Min(required.To,Math.Max(item.A.Y,item.B.Y)))))
            .Sum(item => item.To-item.From);
    private static IEnumerable<(int From,int To)> Merge(IEnumerable<(int From,int To)> source)
    {
        var ordered=source.Where(item => item.To>item.From).OrderBy(item=>item.From).ThenBy(item=>item.To).ToArray();
        if (ordered.Length==0) return [];
        var result=new List<(int From,int To)>{ordered[0]};
        foreach(var interval in ordered.Skip(1))
        {
            var current=result[^1];
            if(interval.From>current.To) result.Add(interval);
            else result[^1]=(current.From,Math.Max(current.To,interval.To));
        }
        return result;
    }

    private static bool TouchesWallSolid(PointMm first,PointMm second,WallSegment wall)
    {
        var half=wall.ThicknessMm/2;
        var wallMinX=Math.Min(wall.Start.X,wall.End.X)-(wall.Start.X==wall.End.X?half:0);
        var wallMaxX=Math.Max(wall.Start.X,wall.End.X)+(wall.Start.X==wall.End.X?half:0);
        var wallMinY=Math.Min(wall.Start.Y,wall.End.Y)-(wall.Start.Y==wall.End.Y?half:0);
        var wallMaxY=Math.Max(wall.Start.Y,wall.End.Y)+(wall.Start.Y==wall.End.Y?half:0);
        return Math.Max(Math.Min(first.X,second.X),wallMinX)<=Math.Min(Math.Max(first.X,second.X),wallMaxX) &&
               Math.Max(Math.Min(first.Y,second.Y),wallMinY)<=Math.Min(Math.Max(first.Y,second.Y),wallMaxY);
    }

    private static double MinimumPlanSegment(IReadOnlyList<PointMm> points) => points.Zip(points.Skip(1))
        .Min(pair => Math.Sqrt(Math.Pow(pair.First.X-pair.Second.X,2)+Math.Pow(pair.First.Y-pair.Second.Y,2)));
    private static string Point(ManualCircuit circuit,int index) =>
        $"{circuit.OrderedPoints[index].X},{circuit.OrderedPoints[index].Y},{circuit.OrderedPoints[index].Z}";
    private static string Serialize(ManualCircuit circuit) => JsonSerializer.Serialize(circuit,HomeAuraProject.JsonOptions);
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected,double actual,double tolerance,string label)
    { if(Math.Abs(expected-actual)>tolerance) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Check(bool condition,string message)
    { if(!condition) throw new InvalidDataException(message); }
}
