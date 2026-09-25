using System.Text.Json;
using HomeAura.NativeEditor;

internal static class K2ServiceLayer166Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var folder = Path.Combine(proposals, "HA_TWO_FLOOR_K2_SERVICE_LAYER_166");
        var floor = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(folder, "HomeAura_Floor1_K1_and_K2_Service_D166.homeaura.json")));
        var attic = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(folder, "HomeAura_Attic_PairedAxes_D166.homeaura.json")));
        var sourceFloor = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(proposals, "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165", "HomeAura_Floor1_MaterializedRoutes_D165.homeaura.json")));
        var sourceAttic = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(proposals, "HA_TWO_FLOOR_MATERIALIZED_ROUTE_BASELINE_165", "HomeAura_Attic_MaterializedAxes_D165.homeaura.json")));

        var heating = floor.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_LOOP").ToArray();
        var service = floor.Circuits.Where(item => item.SystemRole == "INTERFLOOR_SERVICE_LEG").ToArray();
        Check(heating.Length == 12 && service.Length == 22, "D166 expected 12 heating loops and 22 K2 service legs.");
        Check(heating.Select(PointSignature).SequenceEqual(sourceFloor.Circuits.Select(PointSignature)),
            "D166 changed a D165 K1 route.");
        Check(attic.Circuits.Select(PointSignature).SequenceEqual(sourceAttic.Circuits.Select(PointSignature)),
            "D166 changed a D165 attic axis.");
        Check(service.All(item => item.RoutingLayer == "LOWER_SERVICE_LAYER" && item.AxisElevationMm == 135),
            "D166 service layer/elevation changed.");
        Check(heating.All(item => item.RoutingLayer == "HEATING_PLANE" && item.AxisElevationMm == 108),
            "D166 heating plane/elevation changed.");
        Check(floor.RoutingRules.MinimumLayerAxisSeparationMm == 25, "D166 minimum layer separation changed.");
        Check(service.All(item => item.ConcealedServiceLengthMm == 0 && item.OutOfPlaneLengthMm == 3000),
            "D166 vertical length is hidden or missing.");
        var serviceAnalyses = service.Select(item => CircuitAnalyzer.Analyze(floor, item)).ToArray();
        Check(serviceAnalyses.All(item => item.TopologyPass && item.SelfIntersections == 0 && item.InterCircuitIntersections == 0),
            "D166 service topology/contact regression.");
        Check(serviceAnalyses.Sum(item => item.DifferentLayerCrossingsIgnored) > 0,
            "D166 lower service layer no longer records vertically-separated plan crossings.");
        var lanes = service.Select(item => item.OrderedPoints[0].Y).Order().ToArray();
        Check(lanes.Distinct().Count() == 22, "D166 K2 connection gates are not unique.");
        for (var index = 0; index + 3 < lanes.Length; index++)
            Check(lanes[index + 3] - lanes[index] >= 400, "D166 contains more than three adjacent 100mm service axes.");
        Check(service.SelectMany(item => new[] { item.SupplyPortIndex, item.ReturnPortIndex }).Where(item => item is not null).Distinct().Count() == 22,
            "D166 K2 port ownership is not unique.");

        using var contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(folder, "k2_service_layer_contract.json")));
        var model = contract.RootElement;
        Check(model.GetProperty("service_layer").GetProperty("inter_service_contact_count").GetInt32() == 0,
            "D166 contract contains service contacts.");
        Check(model.GetProperty("full_loop_count").GetInt32() == 11 && model.GetProperty("all_design_lengths_40_80m").GetBoolean(),
            "D166 full loop reconciliation failed.");
        Check(model.GetProperty("minimum_design_total_mm").GetInt32() == 51_800 && model.GetProperty("maximum_design_total_mm").GetInt32() == 79_300,
            "D166 design length range changed.");
        Check(model.GetProperty("minimum_headroom_to_80m_mm").GetInt32() == 700,
            "D166 maximum-length headroom changed.");
        Check(model.GetProperty("K2").GetProperty("physical_manifold_selected").GetBoolean() == false,
            "D166 falsely claims a selected physical K2 manifold.");
        Check(model.GetProperty("bend_arc_length_reconciliation").GetString() == "NOT_EVALUATED",
            "D166 falsely claims R80 arc reconciliation.");
        Check(!model.GetProperty("installation_ready").GetBoolean(), "D166 was incorrectly promoted to installation-ready.");
        foreach (var file in new[]
                 {
                     "HomeAura_Floor1_D166_Editor_View.png", "HomeAura_Floor1_D166_Clean_View.png",
                     "HomeAura_Attic_D166_Editor_View.png", "HomeAura_Attic_D166_Clean_View.png", "artifact_manifest.json"
                 })
            Check(File.Exists(Path.Combine(folder, file)), $"D166 evidence file missing: {file}");
    }

    private static string PointSignature(ManualCircuit circuit) =>
        $"{circuit.Id}:" + string.Join(";", circuit.OrderedPoints.Select(point => $"{point.X},{point.Y}"));

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
