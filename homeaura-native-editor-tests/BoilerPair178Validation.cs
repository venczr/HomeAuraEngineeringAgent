using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class BoilerPair178Validation
{
    private static readonly string[] ChangedIds = ["F1-D171-C05", "F1-D171-C06"];

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourceDirectory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_WET_PAIR_PHYSICAL_TURN_FIX_177");
        var sourcePath = Path.Combine(sourceDirectory, "HomeAura_Floor1_WetPairPhysicalTurnFix_D177.homeaura.json");
        var sourceContractPath = Path.Combine(sourceDirectory, "floor1_wet_pair_physical_turn_fix_contract.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178");
        var projectPath = Path.Combine(directory, "HomeAura_Floor1_BoilerPair_D178.homeaura.json");
        var packagePath = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178.zip");
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));

        Check(project.Circuits.Count == source.Circuits.Count, "D178 changed circuit count.");
        foreach (var previous in source.Circuits.Where(item => !ChangedIds.Contains(item.Id)))
        {
            var current = project.Circuits.Single(item => item.Id == previous.Id);
            Check(Serialize(current) == Serialize(previous), $"D178 changed preserved circuit {previous.Id}.");
        }

        ValidateCircuit(project, "F1-D171-C05", 40, [(1,3),(6,8),(11,36)], [0,3,5,8,10,36],
            "89CC743047FBE35FCA4946AE55EF8A244314965C7BEFF33D221089D49C572340",
            46_533.441827207615, 39_307.25635973339, 8, 9);
        ValidateCircuit(project, "F1-D171-C06", 36, [(1,3),(6,31)], [0,3,5,31],
            "8BB2C80B3B730F1CDBC1DBC855379439941E86397359C075CCEF131BE1CCDF1C",
            45_433.79285194222, 37_341.592653589796, 10, 11);
        Close(1_099.6489752653945, Math.Abs(
            CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == ChangedIds[0])).RoundedAxisLengthMm -
            CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == ChangedIds[1])).RoundedAxisLengthMm),
            .003, "D178 pair spread");

        ValidateExteriorBodies(project);
        ValidateWallSolids(project);
        ValidatePorts(project);
        ValidateContract(directory, sourcePath, sourceContractPath);
        ValidateDiagnostics(directory);
        ValidatePackage(directory, packagePath);
    }

    private static void ValidateCircuit(
        HomeAuraProject project, string id, int pointCount, IReadOnlyList<(int Start,int End)> ranges,
        IReadOnlyList<int> transitionSegments, string pointDigest, double expectedLength, double expectedBodyLength,
        int supplyPort, int returnPort)
    {
        var circuit = project.Circuits.Single(item => item.Id == id);
        Check(circuit.OrderedPoints.Count == pointCount && circuit.OrderedPoints.All(item => item.Z is not null),
            $"{id} Point3 chain changed.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex,item.EndIndex)).SequenceEqual(ranges),
            $"{id} body ranges changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual(transitionSegments),
            $"{id} S-bend indices changed.");
        Check(HashPoints(circuit) == pointDigest, $"{id} exact ordered-point digest changed.");
        Check(circuit.SystemRole == "FLOOR_HEATING_LOOP" && circuit.ConcealedServiceLengthMm == 0 &&
              circuit.OutOfPlaneLengthMm == 0, $"{id} full-loop semantics changed.");
        Check(circuit.SupplyPortIndex == supplyPort && circuit.ReturnPortIndex == returnPort,
            $"{id} K1 port ownership changed.");
        Check(MinimumPlanSegment(circuit.OrderedPoints) >= 200, $"{id} has a sub-200 mm ordered segment.");

        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.TopologyPass && analysis.EngineeringPass && analysis.VerticalGeometryMaterialized,
            $"{id} topology/engineering/materialization failed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0 &&
              analysis.BendRadiusViolationCount == 0 && analysis.HeatingBodyWallIntrusions == 0 &&
              analysis.HorizontalTurnWallIntrusions == 0, $"{id} has a contact, R80, or wall defect.");
        Check(analysis.MinimumInterCircuitSurfaceClearanceMm is >= 11 - .051,
            $"{id} global surface clearance fell below 11 mm.");
        Check(analysis.HeatingBodyInsideAssignedRoom && analysis.StartAtCollector && analysis.EndAtCollector,
            $"{id} body/terminal-grid boundary failed.");
        Check(analysis.VerticalTransitions.All(item => item.MaterializedPass && item.RadiusMm == 80 &&
              Math.Abs(item.StartTangentLengthMm + item.RequiredArcProjectionMm + item.EndTangentLengthMm -
                       item.PlanProjectionMm) <= .05), $"{id} transition closure failed.");
        Close(expectedLength, analysis.RoundedAxisLengthMm, .003, $"{id} physical rounded length");

        var bodyLength = circuit.HeatingBodyRanges.Sum(range => RoundedRangeLength(circuit, range));
        Close(expectedBodyLength, bodyLength, .003, $"{id} physical body length");
    }

    private static void ValidateExteriorBodies(HomeAuraProject project)
    {
        var expected = new[]
        {
            (Id:"F1-D171-C05", A:(16400,8800), B:(21000,8800), C:(21000,11600)),
            (Id:"F1-D171-C06", A:(16400,8900), B:(20900,8900), C:(20900,11600)),
            (Id:"F1-D171-C05", A:(16400,9000), B:(20800,9000), C:(20800,11600)),
        };
        foreach (var lane in expected)
        {
            var body = BodySegments(project.Circuits.Single(item => item.Id == lane.Id)).ToArray();
            Check(body.Any(item => Segment(item, lane.A, lane.B)) && body.Any(item => Segment(item, lane.B, lane.C)),
                $"D178 exterior BODY lane at y={lane.A.Item2} changed.");
        }
    }

    private static void ValidateWallSolids(HomeAuraProject project)
    {
        var intersections = 0;
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
                Check(!bodyIndices.Contains(index), $"{circuit.Id} BODY segment {index} touches {wall.Id}.");
                var perpendicular = wall.Start.X == wall.End.X ? first.Y == second.Y : first.X == second.X;
                Check(perpendicular, $"{circuit.Id} TRANSIT segment {index} runs longitudinally in {wall.Id}.");
            }
        }
        Check(intersections == 13, $"D178 wall-solid intersection count changed: {intersections}.");
    }

    private static void ValidatePorts(HomeAuraProject project)
    {
        var ports = project.Circuits.Where(item => item.CollectorId == "K1")
            .SelectMany(item => new[] { item.SupplyPortIndex,item.ReturnPortIndex }).Where(item => item is not null)
            .Select(item => item!.Value).Order().ToArray();
        Check(ports.SequenceEqual(Enumerable.Range(0,28)), "D178 does not own each FM14 K1 point exactly once.");
    }

    private static void ValidateContract(string directory, string sourcePath, string sourceContractPath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"floor1_boiler_pair_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("status").GetString() ==
              "F1_R04_TWO_OWNER_BODY_POINT3_ROUTES_PASS_COLLECTOR_TAILS_DEFERRED", "D178 status changed.");
        Check(contract.GetProperty("source_D177_project_sha256").GetString() == Sha(sourcePath) &&
              contract.GetProperty("source_D177_contract_sha256").GetString() == Sha(sourceContractPath),
            "D178 source lineage changed.");
        Close(1_099.6489752653945, contract.GetProperty("pair_rounded_length_spread_mm").GetDouble(), 1e-6,
            "D178 stored pair spread");
        var coverage = contract.GetProperty("boiler_coverage").GetProperty("physical_R80_axis_round100");
        Close(14.030394185534078, coverage.GetProperty("served_area_m2").GetDouble(), 1e-9,
            "D178 physical served area");
        Close(97.43329295509777, coverage.GetProperty("served_percent").GetDouble(), 1e-9,
            "D178 physical coverage");
        Close(174.55844122715786, coverage.GetProperty("maximum_sample_distance_mm").GetDouble(), 1e-9,
            "D178 maximum physical gap");
        Check(coverage.GetProperty("sample_over_200mm_count").GetInt32() == 0 &&
              contract.GetProperty("exterior_3x100").GetProperty("all_three_body_lanes_pass").GetBoolean(),
            "D178 coverage/exterior gate failed.");
        var walls = contract.GetProperty("sharp_wall_solid_transit_audit");
        Check(walls.GetProperty("pass").GetBoolean() && walls.GetProperty("intersection_count").GetInt32() == 13 &&
              walls.GetProperty("body_wall_hit_count").GetInt32() == 0 &&
              walls.GetProperty("longitudinal_or_nonperpendicular_transit_count").GetInt32() == 0,
            "D178 wall audit changed.");
        Check(contract.GetProperty("physical_R80_turn_wall_audit").GetProperty("intrusion_count").GetInt32() == 0,
            "D178 physical R80 turn entered a wall.");
        var tails = contract.GetProperty("collector_tail_evidence");
        Check(tails.GetProperty("classification").GetString() ==
              "DEFERRED_COLLECTOR_TAIL_FABRICATION_GEOMETRY_NOT_MICRO_STUBS" &&
              tails.GetProperty("records").GetArrayLength() == 4,
            "D178 collector-tail boundary changed.");
        Close(493.13410954830533, tails.GetProperty("minimum_gap_mm").GetDouble(), 1e-6,
            "D178 minimum collector tail");
        Close(747.6672053795057, tails.GetProperty("maximum_gap_mm").GetDouble(), 1e-6,
            "D178 maximum collector tail");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              contract.GetProperty("bounded_terminal_grid_route_count").GetInt32() == 8 &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D178 completion boundary changed.");
    }

    private static void ValidateDiagnostics(string directory)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"engineering_diagnostics.json")));
        var records = document.RootElement.GetProperty("circuits").EnumerateArray()
            .Where(item => ChangedIds.Contains(item.GetProperty("circuit_id").GetString())).ToArray();
        Check(records.Length == 2 && records.All(item => item.GetProperty("engineering_pass").GetBoolean() &&
              item.GetProperty("horizontal_turn_wall_intrusions").GetInt32() == 0 &&
              item.GetProperty("self_surface_clearance_violations").GetInt32() == 0 &&
              item.GetProperty("inter_circuit_surface_clearance_violations").GetInt32() == 0),
            "D178 exported diagnostics failed.");
    }

    private static void ValidatePackage(string directory, string packagePath)
    {
        foreach (var name in new[]
        {
            "HomeAura_Floor1_D178_Clean_View.png", "HomeAura_Floor1_D178_Boiler_Clean_Zoom.png",
            "HomeAura_Floor1_D178_Boiler_3D_Debug.png", "engineering_diagnostics.json",
        }) Check(new FileInfo(Path.Combine(directory,name)) is { Exists:true, Length:>0 }, $"D178 file {name} missing.");
        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory,item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D178 manifest mismatch for {path}.");
        }
        using var archive = ZipFile.OpenRead(packagePath);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D178 ZIP member count changed.");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open(); using var memory = new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory,entry.FullName))),
                $"D178 ZIP byte parity failed for {entry.FullName}.");
        }
    }

    private static double RoundedRangeLength(ManualCircuit circuit, HeatingBodyRange range)
    {
        var points = circuit.OrderedPoints.Skip(range.StartIndex).Take(range.EndIndex - range.StartIndex + 1).ToArray();
        var raw = points.Zip(points.Skip(1)).Sum(pair => Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y));
        var directions = points.Zip(points.Skip(1)).Select(pair =>
            (X: Math.Sign(pair.Second.X-pair.First.X), Y: Math.Sign(pair.Second.Y-pair.First.Y))).ToArray();
        var turns = directions.Zip(directions.Skip(1)).Count(pair => pair.First != pair.Second);
        return raw - turns * (160 - Math.PI * 40);
    }

    private static IEnumerable<(PointMm A,PointMm B)> BodySegments(ManualCircuit circuit)
    {
        foreach (var range in circuit.HeatingBodyRanges)
        for (var index=range.StartIndex; index<range.EndIndex; index++)
            yield return (circuit.OrderedPoints[index],circuit.OrderedPoints[index+1]);
    }

    private static bool Segment((PointMm A,PointMm B) segment,(int X,int Y) first,(int X,int Y) second) =>
        segment.A.X == first.X && segment.A.Y == first.Y && segment.B.X == second.X && segment.B.Y == second.Y ||
        segment.B.X == first.X && segment.B.Y == first.Y && segment.A.X == second.X && segment.A.Y == second.Y;

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
    private static string HashPoints(ManualCircuit circuit)
    {
        var value = string.Join("|", circuit.OrderedPoints.Select(point => $"{point.X},{point.Y},{point.Z}"));
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    }
    private static string Serialize(ManualCircuit circuit) => JsonSerializer.Serialize(circuit,HomeAuraProject.JsonOptions);
    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected,double actual,double tolerance,string label)
    { if(Math.Abs(expected-actual)>tolerance) throw new InvalidDataException($"{label}: expected {expected}, got {actual}."); }
    private static void Check(bool condition,string message)
    { if(!condition) throw new InvalidDataException(message); }
}
