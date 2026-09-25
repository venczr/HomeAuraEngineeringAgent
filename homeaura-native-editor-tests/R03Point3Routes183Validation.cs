using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class R03Point3Routes183Validation
{
    private static readonly string[] ChangedIds = ["F1-D171-C07", "F1-D171-C08", "F1-D171-C09"];
    private const string D181Sha = "253E0DD8DBD59227BBE0147DBFECB201EDAAD56F19E4B3B0511B22254B8C55F2";
    private const string D182Sha = "BC4F7A3FAB3969E83516F9E82772A3F7727BAF9870F93ECB094D3691361E08D8";
    private const string ProjectSha = "E5096220BE3D2F7C93BC5F8B399A374C95556A9D4A29797445EDDC27835CDE4B";
    private const string DiagnosticsSha = "FAFC12707CCB88CDB515EAE999088677E8E6F479C3DDF9151A6F22DAF5F2982E";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourcePath = Path.Combine(proposals, "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
            "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json");
        var d182Path = Path.Combine(proposals, "HA_TWO_FLOOR_R03_OWNER_BODY_FIXTURE_182",
            "r03_owner_body_fixture_contract.json");
        var official = Path.Combine(proposals, "HA_TWO_FLOOR_R03_POINT3_ROUTES_183");
        var isOfficial = Directory.Exists(official);
        var directory = isOfficial ? official : Path.Combine(root, "tmp", "D183_scaffold");
        var package = isOfficial
            ? Path.Combine(proposals, "packages", "HA_TWO_FLOOR_R03_POINT3_ROUTES_183.zip")
            : Path.Combine(root, "tmp", "HA_TWO_FLOOR_R03_POINT3_ROUTES_183_SCAFFOLD.zip");
        var projectPath = Path.Combine(directory, "HomeAura_TwoFloor_R03Point3Routes_D183.homeaura.json");
        var contractPath = Path.Combine(directory, "floor1_r03_point3_routes_contract.json");
        Equal(D181Sha, Sha(sourcePath), "D181 source");
        Equal(D182Sha, Sha(d182Path), "D182 source");
        Equal(ProjectSha, Sha(projectPath), "D183 exact project");
        Equal(DiagnosticsSha, Sha(Path.Combine(directory, "engineering_diagnostics.json")), "D183 diagnostics");

        using var sourceDocument = JsonDocument.Parse(File.ReadAllText(sourcePath));
        using var projectDocument = JsonDocument.Parse(File.ReadAllText(projectPath));
        foreach (var property in sourceDocument.RootElement.EnumerateObject())
        {
            Check(projectDocument.RootElement.TryGetProperty(property.Name, out var current), $"D183 lost {property.Name}.");
            if (property.Name != "circuits")
                Check(JsonElement.DeepEquals(property.Value, current), $"D183 changed D181 {property.Name}.");
        }
        var source = HomeAuraProject.FromJson(File.ReadAllText(sourcePath));
        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        foreach (var previous in source.Circuits.Where(item => !ChangedIds.Contains(item.Id)))
            Check(Serialize(previous) == Serialize(project.Circuits.Single(item => item.Id == previous.Id)),
                $"D183 changed preserved circuit {previous.Id}.");

        ValidateCircuit(project, "F1-D171-C07", 36, [(2,29)], [1,29,34],
            "D0D5AAB6091226983D7E0FD5D656E5A34674E4AF5AA15DFBA086A8CA4E044706",
            72_335.29922991096, 71_236.5378265059, 12, 13);
        ValidateCircuit(project, "F1-D171-C08", 50, [(2,6),(13,38),(45,46)], [1,6,7,10,12,41,44,46],
            "D6F2E45D41039E5CBE409663245F0D90DE4C0272FEA93368EB0BC806927F122C",
            72_057.71822073533, 70_615.59387876619, 14, 15);
        ValidateCircuit(project, "F1-D171-C09", 34, [(3,28)], [2,28],
            "F98C5AA81C2DE6ADAAA63B38801F8E690E39FF3D75D6FD4474EEFF318C80F3AD",
            72_918.12470016345, 71_819.36329675838, 16, 17);
        var analyses = ChangedIds.ToDictionary(id => id,
            id => CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == id)));
        Close(860.4064794281148, analyses.Values.Max(item => item.AxisLengthMm) - analyses.Values.Min(item => item.AxisLengthMm),
            .000001, "raw 3D spread");
        Close(1_203.7694179921964, analyses.Values.Max(item => item.RoundedAxisLengthMm) - analyses.Values.Min(item => item.RoundedAxisLengthMm),
            .000001, "physical R80 rounded spread");
        ValidateWallSolids(project);
        ValidatePorts(project);
        ValidateContract(contractPath, isOfficial);
        ValidatePackage(directory, package);
    }

    private static void ValidateCircuit(HomeAuraProject project, string id, int pointCount,
        IReadOnlyList<(int Start,int End)> ranges, IReadOnlyList<int> transitions, string digest,
        double rawLength, double roundedLength, int supplyPort, int returnPort)
    {
        var circuit = project.Circuits.Single(item => item.Id == id);
        Check(circuit.OrderedPoints.Count == pointCount && circuit.OrderedPoints.All(item => item.Z is not null),
            $"{id} is not the exact Point3 chain.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex,item.EndIndex)).SequenceEqual(ranges),
            $"{id} BODY ranges changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual(transitions),
            $"{id} S-bend indices changed.");
        Equal(digest, HashPoints(circuit), $"{id} ordered points");
        Check(circuit.SystemRole == "FLOOR_HEATING_LOOP" && circuit.ConcealedServiceLengthMm == 0 &&
              circuit.OutOfPlaneLengthMm == 0, $"{id} route semantics changed.");
        Check(circuit.SupplyPortIndex == supplyPort && circuit.ReturnPortIndex == returnPort,
            $"{id} ports changed.");
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.Pass && analysis.TopologyPass && analysis.EngineeringPass && analysis.GridAligned &&
              analysis.HeatingBodyInsideAssignedRoom && analysis.HeatingBodyPlacementPass &&
              analysis.VerticalGeometryMaterialized && analysis.VerticalTransitionRadiusFeasible,
            $"{id} C# positive gate failed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0 &&
              analysis.HeatingBodyWallIntrusions == 0 && analysis.HorizontalTurnWallIntrusions == 0 &&
              analysis.BendRadiusViolationCount == 0 && analysis.UnmaterializedElevationChangeCount == 0,
            $"{id} C# zero-defect gate failed.");
        Check(analysis.MinimumInterCircuitSurfaceClearanceMm >= 10.949, $"{id} surface clearance fell below 11 mm.");
        Close(rawLength, analysis.AxisLengthMm, .000001, $"{id} raw 3D length");
        Close(roundedLength, analysis.RoundedAxisLengthMm, .000001, $"{id} physical rounded length");
    }

    private static void ValidateWallSolids(HomeAuraProject project)
    {
        var intersections = 0;
        var terminalEndpointTouches = 0;
        foreach (var circuit in project.Circuits.Where(item => ChangedIds.Contains(item.Id)))
        {
            var bodyIndices = circuit.HeatingBodyRanges
                .SelectMany(range => Enumerable.Range(range.StartIndex, range.EndIndex-range.StartIndex)).ToHashSet();
            for (var index=0; index+1<circuit.OrderedPoints.Count; index++)
            foreach (var wall in project.Walls)
            {
                var first=circuit.OrderedPoints[index]; var second=circuit.OrderedPoints[index+1];
                if (!TouchesWallSolid(first,second,wall)) continue;
                intersections++;
                if (index==0 || index==circuit.OrderedPoints.Count-2) terminalEndpointTouches++;
                Check(!bodyIndices.Contains(index), $"{circuit.Id} BODY {index} touches {wall.Id}.");
                var perpendicular=wall.Start.X==wall.End.X ? first.Y==second.Y : first.X==second.X;
                Check(perpendicular, $"{circuit.Id} TRANSIT {index} is longitudinal in {wall.Id}.");
            }
        }
        Equal(25, intersections, "wall intersections including endpoint touches");
        Equal(10, terminalEndpointTouches, "terminal endpoint wall touches");
    }

    private static void ValidatePorts(HomeAuraProject project)
    {
        var ports=project.Circuits.Where(item=>item.CollectorId=="K1")
            .SelectMany(item=>new[]{item.SupplyPortIndex,item.ReturnPortIndex}).Where(item=>item is not null)
            .Select(item=>item!.Value).Order().ToArray();
        Check(ports.SequenceEqual(Enumerable.Range(0,28)), "D183 K1 does not own ports 0..27 exactly once.");
    }

    private static void ValidateContract(string path, bool isOfficial)
    {
        using var document=JsonDocument.Parse(File.ReadAllText(path)); var contract=document.RootElement;
        Equal("R03_C07_C09_POINT3_HARD_GATES_PASS_COLLECTOR_TAILS_DEFERRED",
            contract.GetProperty("status").GetString(), "D183 status");
        Equal(isOfficial ? "OFFICIAL_APPEND_ONLY_D183" : "PREPUBLICATION_SCAFFOLD_AWAITING_ROOT_GO",
            contract.GetProperty("publication_state").GetString(), "D183 publication state");
        Check(!contract.GetProperty("publishable").GetBoolean() &&
              !contract.GetProperty("publishable_as_installation_project").GetBoolean() &&
              contract.GetProperty("terminal_grid_route_only").GetBoolean() &&
              !contract.GetProperty("physical_eurocone_tails_materialized").GetBoolean(),
            "D183 exceeded its terminal-grid publication boundary.");
        var lengths=contract.GetProperty("route_lengths");
        Close(860.4064794281148, lengths.GetProperty("raw_3d_axis_spread_mm").GetDouble(), .000001, "stored raw spread");
        Close(1_203.7694179921964, lengths.GetProperty("physical_R80_rounded_axis_spread_mm").GetDouble(), .000001, "stored rounded spread");
        var coverage=contract.GetProperty("custom_D182_BODY_coverage").GetProperty("physical_R80_axis_round100");
        Close(96.68922372440188, coverage.GetProperty("served_percent").GetDouble(), 1e-12, "D183 coverage");
        Close(200, coverage.GetProperty("maximum_sample_distance_mm").GetDouble(), 1e-12, "D183 max gap");
        Equal(0, coverage.GetProperty("sample_over_200mm_count").GetInt32(), "D183 samples over 200");
        var exterior=contract.GetProperty("exterior_3x100_and_windows");
        foreach(var field in new[]{"WIN_04_percent_by_lane","WIN_05_percent_by_lane"})
            Check(exterior.GetProperty(field).EnumerateArray().All(item=>item.GetDouble()==100), $"{field} changed.");
        var walls=contract.GetProperty("sharp_wall_solid_transit_audit");
        Check(walls.GetProperty("pass").GetBoolean() && walls.GetProperty("intersection_count").GetInt32()==25 &&
              walls.GetProperty("endpoint_touch_records_included").GetBoolean() &&
              walls.GetProperty("endpoint_touch_record_count").GetInt32()==10 &&
              walls.GetProperty("body_wall_hit_count").GetInt32()==0 &&
              walls.GetProperty("longitudinal_or_nonperpendicular_transit_count").GetInt32()==0,
            "D183 stored wall audit changed.");
        var tails=contract.GetProperty("collector_tail_evidence");
        Check(tails.GetProperty("classification").GetString()=="DEFERRED_COLLECTOR_TAIL_FABRICATION_GEOMETRY_NOT_MICRO_STUBS" &&
              tails.GetProperty("records").GetArrayLength()==6 &&
              tails.GetProperty("records").EnumerateArray().All(item=>!item.GetProperty("fabrication_tail_materialized").GetBoolean()),
            "D183 invented a terminal-to-Eurocone XYZ tail.");
        Check(contract.GetProperty("bounded_terminal_grid_route_count").GetInt32()==11 &&
              contract.GetProperty("complete_K1_route_count").GetInt32()==0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32()==0 &&
              !contract.GetProperty("sleeves_added").GetBoolean() &&
              !contract.GetProperty("installation_ready").GetBoolean(), "D183 completion boundary changed.");
    }

    private static void ValidatePackage(string directory,string package)
    {
        foreach(var name in new[]{"HomeAura_Floor1_D183_Clean_View.png","HomeAura_Floor1_D183_R03_Clean_Zoom.png",
                    "HomeAura_Floor1_D183_R03_3D_Diagnostic.png","engineering_diagnostics.json"})
            Check(new FileInfo(Path.Combine(directory,name)) is {Exists:true,Length:>0}, $"D183 missing {name}.");
        using var manifest=JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,"artifact_manifest.json")));
        foreach(var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var file=Path.Combine(directory,item.GetProperty("name").GetString()!);
            Check(File.Exists(file) && new FileInfo(file).Length==item.GetProperty("bytes").GetInt64() &&
                  Sha(file)==item.GetProperty("sha256").GetString(), $"D183 manifest mismatch: {file}");
        }
        using var archive=ZipFile.OpenRead(package);
        Equal(Directory.GetFiles(directory).Length,archive.Entries.Count,"D183 ZIP member count");
        foreach(var entry in archive.Entries)
        {
            using var stream=entry.Open(); using var memory=new MemoryStream(); stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory,entry.FullName))),
                $"D183 ZIP byte parity failed: {entry.FullName}");
        }
    }

    private static bool TouchesWallSolid(PointMm first,PointMm second,WallSegment wall)
    {
        var half=wall.ThicknessMm/2;
        var minX=Math.Min(wall.Start.X,wall.End.X)-(wall.Start.X==wall.End.X?half:0);
        var maxX=Math.Max(wall.Start.X,wall.End.X)+(wall.Start.X==wall.End.X?half:0);
        var minY=Math.Min(wall.Start.Y,wall.End.Y)-(wall.Start.Y==wall.End.Y?half:0);
        var maxY=Math.Max(wall.Start.Y,wall.End.Y)+(wall.Start.Y==wall.End.Y?half:0);
        return Math.Max(Math.Min(first.X,second.X),minX)<=Math.Min(Math.Max(first.X,second.X),maxX) &&
               Math.Max(Math.Min(first.Y,second.Y),minY)<=Math.Min(Math.Max(first.Y,second.Y),maxY);
    }
    private static string HashPoints(ManualCircuit circuit)
    {
        var value=string.Join("|",circuit.OrderedPoints.Select(point=>$"{point.X},{point.Y},{point.Z}"));
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    }
    private static string Serialize(ManualCircuit circuit)=>JsonSerializer.Serialize(circuit,HomeAuraProject.JsonOptions);
    private static string Sha(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected,double actual,double tolerance,string label)
    {if(Math.Abs(expected-actual)>tolerance)throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");}
    private static void Equal<T>(T expected,T actual,string label)
    {if(!EqualityComparer<T>.Default.Equals(expected,actual))throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");}
    private static void Check(bool condition,string message){if(!condition)throw new InvalidDataException(message);}
}
