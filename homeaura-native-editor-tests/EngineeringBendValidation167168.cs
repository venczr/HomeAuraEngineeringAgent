using System.Text.Json;
using HomeAura.NativeEditor;

internal static class EngineeringBendValidation167168
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var d167 = Path.Combine(proposals, "HA_TWO_FLOOR_COLLECTOR_AND_R80_AUDIT_167");
        var d168 = Path.Combine(proposals, "HA_TWO_FLOOR_R80_PARTIAL_REPAIR_168");
        var d169 = Path.Combine(proposals, "HA_TWO_FLOOR_LAYER_CLEARANCE_EVIDENCE_169");
        var floor167 = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(d167, "HomeAura_Floor1_Collectors_R80_D167.homeaura.json")));
        var attic167 = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(d167, "HomeAura_Attic_R80_D167.homeaura.json")));
        var floor168 = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(d168, "HomeAura_Floor1_R80_Partial_D168.homeaura.json")));
        var attic168 = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(d168, "HomeAura_Attic_R80_Partial_D168.homeaura.json")));

        var k1 = floor167.Collectors.Single(item => item.Id == "K1");
        var k2 = floor167.Collectors.Single(item => item.Id == "K2");
        Check(k1.Ports == 24 && k1.ReferenceWidthMm == 776 && k1.ReferenceDepthMm == 90,
            "D167 K1 reference envelope changed.");
        Check(k2.Ports == 22 && k2.ReferenceWidthMm == 726 && k2.ReferenceDepthMm == 90,
            "D167 K2 reference envelope changed.");
        Check(k1.EquipmentStatus == "DRAFT_UNSELECTED" && k2.EquipmentStatus == "DRAFT_UNSELECTED",
            "D167 reference equipment was falsely marked selected.");

        var k1Bends167 = floor167.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_LOOP")
            .ToDictionary(item => item.Id, item => CircuitAnalyzer.Analyze(floor167, item).BendRadiusViolationCount);
        Check(k1Bends167.Count(item => item.Value == 0) == 11 && k1Bends167["F1-C14"] == 1,
            "D167 K1 R80 audit changed.");
        Check(floor167.Circuits.Where(item => item.SystemRole == "INTERFLOOR_SERVICE_LEG")
                .All(item => CircuitAnalyzer.Analyze(floor167, item).BendRadiusFeasible),
            "D167 K2 service R80 audit changed.");
        Check(attic167.Circuits.Count(item => CircuitAnalyzer.Analyze(attic167, item).BendRadiusFeasible) == 1,
            "D167 attic R80 baseline changed.");

        Check(floor168.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_LOOP")
                .All(item => CircuitAnalyzer.Analyze(floor168, item).EngineeringPass),
            "D168 does not have 12 engineering-pass K1 routes.");
        Check(floor168.Circuits.Where(item => item.SystemRole == "INTERFLOOR_SERVICE_LEG")
                .All(item => CircuitAnalyzer.Analyze(floor168, item).EngineeringPass),
            "D168 does not have 22 engineering-pass K2 service legs.");
        var atticPass = attic168.Circuits.Where(item => CircuitAnalyzer.Analyze(attic168, item).EngineeringPass).Select(item => item.Id).Order().ToArray();
        Check(atticPass.Length == 6, "D168 attic R80 pass count changed.");
        var expectedRework = new[] { "A-C03", "A-C04", "A-C06", "A-C07", "A-C12" };
        Check(expectedRework.Order().SequenceEqual(attic168.Circuits.Where(item => !CircuitAnalyzer.Analyze(attic168, item).EngineeringPass).Select(item => item.Id).Order()),
            "D168 attic R80 rework set changed.");

        using var contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d168, "r80_partial_repair_contract.json")));
        var validation = contract.RootElement.GetProperty("validation");
        Check(validation.GetProperty("floor_same_layer_contact_count").GetInt32() == 0 && validation.GetProperty("attic_contact_count").GetInt32() == 0,
            "D168 contains route contacts.");
        Check(validation.GetProperty("K1_R80_pass_count").GetInt32() == 12 && validation.GetProperty("K2_service_R80_pass_count").GetInt32() == 22,
            "D168 R80 pass counts changed.");
        Check(validation.GetProperty("minimum_design_length_mm").GetInt32() == 51_800 && validation.GetProperty("maximum_design_length_mm").GetInt32() == 79_300,
            "D168 design length range changed.");
        Check(!contract.RootElement.GetProperty("installation_ready").GetBoolean(), "D168 was incorrectly promoted to installation-ready.");

        var floor169 = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(d169, "HomeAura_Floor1_LayerClearance_D169.homeaura.json")));
        Check(floor169.RoutingRules.PipeOuterDiameterMm == 16 && floor169.RoutingRules.MinimumLayerSurfaceClearanceMm == 5,
            "D169 OD/surface-clearance contract changed.");
        Check(floor169.RoutingRules.MinimumLayerAxisSeparationMm == 25,
            "D169 configured axis-separation contract changed.");
        using var clearanceContract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d169, "layer_clearance_evidence_contract.json")));
        var layer = clearanceContract.RootElement.GetProperty("layer_contract");
        Check(layer.GetProperty("same_layer_contact_pair_count").GetInt32() == 0,
            "D169 contains same-layer contacts.");
        Check(layer.GetProperty("cross_layer_intersection_pair_count").GetInt32() == 101,
            "D169 cross-layer evidence count changed.");
        Check(layer.GetProperty("actual_axis_separation_mm").GetInt32() == 27 && layer.GetProperty("actual_surface_clearance_mm").GetInt32() == 11,
            "D169 layer clearance arithmetic changed.");
        Check(layer.GetProperty("all_cross_layer_pairs_explicitly_clear").GetBoolean(),
            "D169 contains an unproven cross-layer exemption.");
        Check(!clearanceContract.RootElement.GetProperty("installation_ready").GetBoolean(),
            "D169 was incorrectly promoted to installation-ready.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
