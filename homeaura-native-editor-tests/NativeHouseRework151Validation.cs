using System.Text.Json;
using HomeAura.NativeEditor;

public static class NativeHouseRework151Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var folder = Path.Combine(root, "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_151");
        var floor1 = Load(Path.Combine(folder, "HomeAura_Floor1_Rework_D151.homeaura.json"));
        var attic = Load(Path.Combine(folder, "HomeAura_Attic_Rework_D151.homeaura.json"));

        Equal(1, floor1.Levels.Count); Equal("FLOOR_1", floor1.Levels[0].Id);
        Equal(8, floor1.Rooms.Count); Equal(11, floor1.Circuits.Count); Equal(1, floor1.Collectors.Count);
        Equal(1, attic.Levels.Count); Equal("ATTIC", attic.Levels[0].Id);
        Equal(9, attic.Rooms.Count); Equal(11, attic.Circuits.Count); Equal(1, attic.Collectors.Count);
        Equal(1, attic.ServiceZones.Count); Equal(70, attic.ServiceZones[0].ClearHeightMm);
        Equal(22, attic.ServiceZones[0].PipeCapacity); Equal("K2", attic.ServiceZones[0].CollectorId);
        True(attic.Circuits.All(item => item.ServiceZoneId == "K2-SERVICE-70"), "Attic circuit is missing its service-zone assignment.");

        ValidateRoutes(floor1);
        ValidateRoutes(attic);
        True(floor1.Exclusions.Any(item => item.Id == "F1-X-STAIR-3"), "Floor-1 tread exclusion is missing.");
        True(attic.Exclusions.Any(item => item.Id == "A-X-STAIR"), "Attic stair opening is missing.");

        var summary = JsonDocument.Parse(File.ReadAllText(Path.Combine(folder, "validation_summary.json"))).RootElement;
        Equal(16, summary.GetProperty("design_input").GetProperty("pipe_od_mm").GetInt32());
        Equal(80, summary.GetProperty("design_input").GetProperty("minimum_bend_radius_mm").GetInt32());
        Equal(70, summary.GetProperty("design_input").GetProperty("available_above_insulation_mm").GetInt32());
        var audit = JsonDocument.Parse(File.ReadAllText(Path.Combine(folder, "independent_geometry_audit.json"))).RootElement;
        Equal("PASS_NATIVE_EDITABLE_AXIS_GEOMETRY_REWORK_DRAFT_POLYGON_COVERAGE", audit.GetProperty("result").GetString());
        foreach (var floor in new[] { audit.GetProperty("floor1"), audit.GetProperty("attic") })
        {
            True(floor.GetProperty("all_lengths_40_80m").GetBoolean(), "Audit reports an out-of-range circuit.");
            Equal(0, floor.GetProperty("self_invalid_route_ids").GetArrayLength());
            Equal(0, floor.GetProperty("inter_route_contact_pairs").GetArrayLength());
            Equal(0, floor.GetProperty("exclusion_hit_route_ids").GetArrayLength());
        }
        var successor = Path.Combine(root, "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_NATIVE_EDITOR_REWORK_152");
        True(File.Exists(Path.Combine(successor, "HomeAura_Floor1_Rework_D152.homeaura.json")), "Missing D152 floor-1 project.");
        True(File.Exists(Path.Combine(successor, "HomeAura_Attic_Rework_D152.homeaura.json")), "Missing D152 attic project.");
        True(File.Exists(Path.Combine(successor, "HomeAura_Floor1_D152_Editor_View.png")), "Missing D152 floor-1 editor view.");
        True(File.Exists(Path.Combine(successor, "HomeAura_Attic_D152_Editor_View.png")), "Missing D152 attic editor view.");
    }

    private static HomeAuraProject Load(string path)
    {
        True(File.Exists(path), $"Missing D151 project: {path}");
        return HomeAuraProject.FromJson(File.ReadAllText(path));
    }

    private static void ValidateRoutes(HomeAuraProject project)
    {
        project.ValidateContract();
        var used = project.Circuits.SelectMany(item => new[] { item.SupplyPortIndex, item.ReturnPortIndex }).ToArray();
        Equal(project.Circuits.Count * 2, used.Distinct().Count());
        foreach (var circuit in project.Circuits)
        {
            var analysis = CircuitAnalyzer.Analyze(project, circuit);
            True(analysis.GridAligned && analysis.Continuous, $"{circuit.Id}: invalid ordered axis.");
            True(analysis.LengthInRange, $"{circuit.Id}: length outside 40–80 m: {analysis.LengthMm}.");
            Equal(0, analysis.SelfIntersections);
            Equal(0, analysis.InterCircuitIntersections);
            True(analysis.StartAtCollector && analysis.EndAtCollector, $"{circuit.Id}: not connected to collector/service zone.");
        }
    }

    private static void True(bool value, string message) { if (!value) throw new Exception(message); }
    private static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new Exception($"Expected {expected}, got {actual}.");
    }
}
