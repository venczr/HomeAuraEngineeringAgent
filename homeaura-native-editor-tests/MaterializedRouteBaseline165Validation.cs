using System.Text.Json;
using HomeAura.NativeEditor;

internal static class MaterializedRouteBaseline165Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var folder = Path.Combine(root, "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165");
        var floorPath = Path.Combine(folder, "HomeAura_Floor1_MaterializedRoutes_D165.homeaura.json");
        var atticPath = Path.Combine(folder, "HomeAura_Attic_MaterializedAxes_D165.homeaura.json");
        var contractPath = Path.Combine(folder, "materialized_route_baseline_contract.json");
        var floor = HomeAuraProject.FromJson(File.ReadAllText(floorPath));
        var attic = HomeAuraProject.FromJson(File.ReadAllText(atticPath));

        Check(floor.Circuits.Count == 12, "D165 floor must contain 12 complete K1 routes.");
        Check(floor.Circuits.All(item => item.SystemRole == "FLOOR_HEATING_LOOP" && item.RoutingLayer == "HEATING_PLANE"),
            "D165 floor route roles/layers changed.");
        Check(floor.Circuits.All(item => item.ConcealedServiceLengthMm == 0), "D165 floor contains hidden route length.");
        var floorAnalyses = floor.Circuits.Select(item => CircuitAnalyzer.Analyze(floor, item)).ToArray();
        Check(floorAnalyses.All(item => item.Pass), "D165 complete K1 route failed native analysis.");
        Check(floorAnalyses.All(item => item.SelfIntersections == 0 && item.InterCircuitIntersections == 0),
            "D165 floor topology/contact regression.");
        Check(floorAnalyses.Min(item => item.LengthMm) == 47_500 && floorAnalyses.Max(item => item.LengthMm) == 78_200,
            "D165 floor length range changed.");
        var k1 = floor.Collectors.Single(item => item.Id == "K1");
        var k2 = floor.Collectors.Single(item => item.Id == "K2");
        Check(k1.MountingWallId == k2.MountingWallId, "K1 and K2 are no longer on the same boiler-room wall.");
        Check(k2.RotationDegrees == 180 && k2.PipeOutletDirection == "UP", "K2 is no longer inverted with upward outlets.");
        Check(floor.ServiceZones.Single().PipeGeometryMaterialized, "K1 endpoint bank is not materialized.");

        Check(attic.Circuits.Count == 11, "D165 attic must contain 11 handoff-to-handoff floor axes.");
        Check(attic.Circuits.All(item => item.SystemRole == "FLOOR_HEATING_AXIS" && item.RoutingLayer == "HEATING_PLANE"),
            "D165 attic axes were misrepresented as collector-complete loops.");
        Check(attic.Circuits.All(item => item.CollectorId is null && item.ConcealedServiceLengthMm == 0),
            "D165 attic contains a false collector link or hidden length.");
        var atticAnalyses = attic.Circuits.Select(item => CircuitAnalyzer.Analyze(attic, item)).ToArray();
        Check(atticAnalyses.All(item => item.TopologyPass), "D165 attic floor axis failed bounded topology.");
        Check(atticAnalyses.All(item => item.SelfIntersections == 0 && item.InterCircuitIntersections == 0),
            "D165 attic topology/contact regression.");
        Check(atticAnalyses.Min(item => item.AxisLengthMm) == 41_300 && atticAnalyses.Max(item => item.AxisLengthMm) == 66_600,
            "D165 attic axis length range changed.");

        using var contract = JsonDocument.Parse(File.ReadAllText(contractPath));
        var rootElement = contract.RootElement;
        Check(rootElement.GetProperty("floor1").GetProperty("complete_route_count").GetInt32() == 12,
            "D165 contract floor route count changed.");
        Check(rootElement.GetProperty("attic").GetProperty("K2_to_handoff_service_geometry").GetString() == "NOT_YET_MATERIALIZED_NEXT_BLOCK",
            "D165 falsely claims a complete K2 service bridge.");
        Check(!rootElement.GetProperty("installation_ready").GetBoolean(), "D165 was incorrectly promoted to installation-ready.");
        foreach (var file in new[]
                 {
                     "HomeAura_Floor1_D165_Editor_View.png", "HomeAura_Floor1_D165_Clean_View.png",
                     "HomeAura_Attic_D165_Editor_View.png", "HomeAura_Attic_D165_Clean_View.png",
                     "artifact_manifest.json"
                 })
            Check(File.Exists(Path.Combine(folder, file)), $"D165 evidence file missing: {file}");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
