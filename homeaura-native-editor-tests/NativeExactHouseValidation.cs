using System.Text.Json;
using HomeAura.NativeEditor;

public static class NativeExactHouseValidation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");

        var d153Floor1 = Load(Path.Combine(
            proposals,
            "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153",
            "HomeAura_Floor1_ExactHouse_D153.homeaura.json"));
        var d153Attic = Load(Path.Combine(
            proposals,
            "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153",
            "HomeAura_Attic_ExactHouse_D153.homeaura.json"));

        True(d153Floor1.Rooms.SelectMany(item => item.Outline).Any(point => point.X % 100 != 0 || point.Y % 100 != 0),
            "D153 floor-1 architecture was rounded back to the pipe grid.");
        True(d153Attic.Rooms.SelectMany(item => item.Outline).Any(point => point.X % 100 != 0 || point.Y % 100 != 0),
            "D153 attic architecture was rounded back to the pipe grid.");
        True(d153Floor1.Circuits.SelectMany(item => item.OrderedPoints).All(IsGridPoint), "D153 floor-1 pipe axis left the 100 mm grid.");
        True(d153Attic.Circuits.SelectMany(item => item.OrderedPoints).All(IsGridPoint), "D153 attic pipe axis left the 100 mm grid.");

        var d154Folder = Path.Combine(proposals, "HA_TWO_FLOOR_NATIVE_EDITOR_COUNTERFLOW_LAYOUT_154");
        var d154Floor1 = Load(Path.Combine(d154Folder, "HomeAura_Floor1_Counterflow_D154.homeaura.json"));
        var d154Attic = Load(Path.Combine(d154Folder, "HomeAura_Attic_CounterflowBodies_D154.homeaura.json"));
        Equal(12, d154Floor1.Circuits.Count);
        True(d154Floor1.Circuits.All(item => CircuitAnalyzer.Analyze(d154Floor1, item).Pass),
            "D154 floor-1 contains an incomplete, intersecting, disconnected, or out-of-range route.");
        Equal(13, d154Attic.Circuits.Count);
        True(d154Attic.Circuits.All(item => !item.Completed), "D154 attic bodies were incorrectly published as full K2 routes.");
        True(d154Attic.Circuits.All(item => CircuitAnalyzer.Analyze(d154Attic, item).SelfIntersections == 0),
            "D154 attic contains a self-intersecting counterflow body.");
        True(d154Attic.Circuits.All(item => CircuitAnalyzer.Analyze(d154Attic, item).InterCircuitIntersections == 0),
            "D154 attic bodies touch or intersect one another.");

        var d154Audit = JsonDocument.Parse(File.ReadAllText(Path.Combine(d154Folder, "independent_geometry_audit.json"))).RootElement;
        Near(88.06969272699759,
            d154Audit.GetProperty("attic").GetProperty("coverage").GetProperty("served_proximity_percent").GetDouble(),
            0.000001,
            "D154 attic proximity changed.");
        True(!d154Audit.GetProperty("attic").GetProperty("coverage").GetProperty("full_coverage_claimed").GetBoolean(),
            "D154 attic must not claim full coverage.");

        var d155Folder = Path.Combine(proposals, "HA_TWO_FLOOR_ATTIC_SERVICE_LENGTH_CANDIDATES_155");
        var d155 = Load(Path.Combine(d155Folder, "HomeAura_Attic_ServiceLengthCandidates_D155.homeaura.json"));
        Equal(12, d155.Circuits.Count);
        Equal(24, d155.Collectors.Single(item => item.Id == "K2").Ports);
        Equal(1, d155.ServiceZones.Count);
        True(d155.Circuits.All(item => item.Completed && item.ConcealedServiceLengthMm > 0 && item.ServiceZoneId is not null),
            "D155 is missing a completed body or its concealed service-length assignment.");

        var analyses = d155.Circuits.Select(item => CircuitAnalyzer.Analyze(d155, item)).ToArray();
        True(analyses.All(item => item.Pass), "D155 contains an incomplete, intersecting, disconnected, or out-of-range route candidate.");
        Equal(57_000d, analyses.Min(item => item.LengthMm));
        Equal(79_200d, analyses.Max(item => item.LengthMm));
        True(analyses.All(item => item.LengthMm == item.AxisLengthMm + item.ConcealedServiceLengthMm),
            "D155 total length does not reconcile body and concealed service portions.");

        var contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d155Folder, "service_length_contract.json"))).RootElement;
        Equal(2, contract.GetProperty("service_cross_section").GetProperty("baseline_layer_count").GetInt32());
        True(!contract.GetProperty("service_cross_section").GetProperty("three_layers_claimed").GetBoolean(),
            "D155 must not claim three layers in 70 mm.");
        True(!contract.GetProperty("service_cross_section").GetProperty("vertical_90_degree_bend_inside_70mm_allowed").GetBoolean(),
            "D155 must not claim that an R80 vertical bend fits inside 70 mm.");
        Equal(96, contract.GetProperty("service_cross_section").GetProperty("minimum_shallow_s_offset_run_mm_for_30mm_layer_change").GetInt32());
        True(!contract.GetProperty("individual_service_pipe_axes_materialized").GetBoolean(),
            "D155 must not promote the service skeleton to individual pipe axes.");

        var d156Folder = Path.Combine(proposals, "HA_TWO_FLOOR_INTERFLOOR_RISER_ALIGNMENT_156");
        var d156Floor1 = Load(Path.Combine(d156Folder, "HomeAura_Floor1_R1_Aligned_D156.homeaura.json"));
        var d156Attic = Load(Path.Combine(d156Folder, "HomeAura_Attic_R1_Aligned_D156.homeaura.json"));
        SequenceEqual(RouteKeys(d154Floor1), RouteKeys(d156Floor1));
        SequenceEqual(RouteKeys(d155), RouteKeys(d156Attic));
        Equal(d154Floor1.ServiceZones.Count + 2, d156Floor1.ServiceZones.Count);
        Equal(d155.ServiceZones.Count + 2, d156Attic.ServiceZones.Count);

        var r1 = JsonDocument.Parse(File.ReadAllText(Path.Combine(d156Folder, "r1_alignment_contract.json"))).RootElement;
        SequenceEqual(new[] { 12_700, 11_000 }, r1.GetProperty("r1_axis_mm").EnumerateArray().Select(item => item.GetInt32()));
        True(r1.GetProperty("placement").GetProperty("covered_by_floor1_hall").GetBoolean(), "R1 is outside the floor-1 hall.");
        True(r1.GetProperty("placement").GetProperty("covered_by_attic_wardrobe").GetBoolean(), "R1 is outside the attic wardrobe.");
        Equal(200d, r1.GetProperty("placement").GetProperty("distance_to_attic_stair_opening_mm").GetDouble());
        Equal(4_600, r1.GetProperty("route").GetProperty("floor1_plan_length_mm").GetInt32());
        Equal(3_000, r1.GetProperty("route").GetProperty("vertical_rise_mm").GetInt32());
        Equal(1_000, r1.GetProperty("route").GetProperty("attic_plan_length_mm").GetInt32());
        Equal(8_600, r1.GetProperty("route").GetProperty("one_way_K1_to_K2_axis_length_mm").GetInt32());
        True(!r1.GetProperty("bend_contract").GetProperty("horizontal_to_vertical_90_degree_bend_inside_70mm_floor_layer_allowed").GetBoolean(),
            "D156 must keep the R80 vertical turn out of the 70 mm floor layer.");
        True(!r1.GetProperty("feed_contract").GetProperty("installation_ready").GetBoolean(),
            "D156 must not be installation-ready before the opening size and feed hydraulics are known.");

        var d158Folder = Path.Combine(proposals, "HA_TWO_FLOOR_K2_CLEARANCE_COVERAGE_CORRECTION_158");
        var d158Floor1 = Load(Path.Combine(d158Folder, "HomeAura_Floor1_R1_K2_Clearance_D158.homeaura.json"));
        var d158Attic = Load(Path.Combine(d158Folder, "HomeAura_Attic_K2_Clearance_D158.homeaura.json"));
        SequenceEqual(RouteKeys(d156Floor1), RouteKeys(d158Floor1));
        Equal(12, d158Attic.Circuits.Count);
        True(d158Attic.Circuits.All(item => CircuitAnalyzer.Analyze(d158Attic, item).Pass),
            "D158 contains an invalid complete attic circuit candidate.");
        Equal(1, d158Attic.Circuits.Count(item => item.Id == "A-C01" && item.ConcealedServiceLengthMm == 4_000));
        var k2 = d158Attic.Collectors.Single(item => item.Id == "K2").Position;
        var wardrobeCircuit = d158Attic.Circuits.Single(item => item.Id == "A-C01");
        Equal(400d, MinimumDistance(k2, wardrobeCircuit.OrderedPoints));
        True(d158Attic.ServiceZones.Any(item => item.Id == "K2-CABINET-CLEARANCE-D157"),
            "D158 is missing the K2 no-heating cabinet zone.");

        var d158Contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d158Folder, "k2_clearance_and_service_contract.json"))).RootElement;
        Equal(100d, d158Contract.GetProperty("A_C01_body_distance_to_cabinet_mm").GetDouble());
        Equal(0, d158Contract.GetProperty("A_C01_cabinet_intersection_count").GetInt32());
        Near(85.20187403955791,
            d158Contract.GetProperty("coverage").GetProperty("served_proximity_percent").GetDouble(),
            0.000001,
            "D158 corrected attic proximity changed.");
        True(d158Contract.GetProperty("D157_coverage_rejected").GetProperty("served_proximity_percent").GetDouble() < 50,
            "D158 no longer records the rejected D157 coordinate-frame result.");
        True(!d158Contract.GetProperty("installation_ready").GetBoolean(),
            "D158 must not be installation-ready before individual K2 service axes and a physical manifold are selected.");

        var d159Folder = Path.Combine(proposals, "HA_TWO_FLOOR_DENSE_CENTRE_COUNTERFLOW_159");
        var d159Floor1 = Load(Path.Combine(d159Folder, "HomeAura_Floor1_DenseCounterflow_D159.homeaura.json"));
        var d159Attic = Load(Path.Combine(d159Folder, "HomeAura_Attic_DenseCounterflow_D159.homeaura.json"));
        SequenceEqual(RouteKeys(d158Floor1), RouteKeys(d159Floor1));
        Equal(12, d159Attic.Circuits.Count);
        True(d159Attic.Circuits.All(item => CircuitAnalyzer.Analyze(d159Attic, item).Pass),
            "D159 contains an invalid complete attic circuit candidate.");
        True(d159Attic.Circuits.All(item => MinimumSegmentLength(item.OrderedPoints) >= 200),
            "D159 introduced a sub-200 mm axis segment.");
        Equal(58_600d, CircuitAnalyzer.Analyze(d159Attic, d159Attic.Circuits.Single(item => item.Id == "A-C01")).LengthMm);
        Equal(78_000d, CircuitAnalyzer.Analyze(d159Attic, d159Attic.Circuits.Single(item => item.Id == "A-C04")).LengthMm);
        Equal(77_600d, CircuitAnalyzer.Analyze(d159Attic, d159Attic.Circuits.Single(item => item.Id == "A-C07")).LengthMm);
        Equal(400d, MinimumDistance(k2, d159Attic.Circuits.Single(item => item.Id == "A-C01").OrderedPoints));

        var d159Contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d159Folder, "dense_counterflow_contract.json"))).RootElement;
        SequenceEqual(new[] { "A-C01", "A-C04", "A-C07" },
            d159Contract.GetProperty("changed_route_ids").EnumerateArray().Select(item => item.GetString()!));
        Near(87.08964114086942,
            d159Contract.GetProperty("coverage").GetProperty("served_proximity_percent").GetDouble(),
            0.000001,
            "D159 corrected attic proximity changed.");
        True(d159Contract.GetProperty("coverage_gain_m2").GetDouble() > 2.7,
            "D159 dense centres no longer improve served proximity by the proven amount.");
        True(!d159Contract.GetProperty("installation_ready").GetBoolean(),
            "D159 must not be installation-ready before individual service axes are materialized.");

        var d162Folder = Path.Combine(proposals, "HA_TWO_FLOOR_FINAL_DENSE_DUAL_RISE_162");
        var d162Floor1 = Load(Path.Combine(d162Folder, "HomeAura_Floor1_Final_D162.homeaura.json"));
        var d162Attic = Load(Path.Combine(d162Folder, "HomeAura_Attic_Final_D162.homeaura.json"));
        Equal(2, d162Floor1.Collectors.Count);
        var d162K1 = d162Floor1.Collectors.Single(item => item.Id == "K1");
        var d162K2 = d162Floor1.Collectors.Single(item => item.Id == "K2");
        Equal("FLOOR_1-W025", d162K1.MountingWallId);
        Equal(d162K1.MountingWallId, d162K2.MountingWallId);
        Equal("DOWN", d162K1.PipeOutletDirection);
        Equal("UP", d162K2.PipeOutletDirection);
        Equal(180, d162K2.RotationDegrees);
        Equal(30, d162K2.Ports);
        True(d162Floor1.Collectors.All(item => item.FloorId == "FLOOR_1"), "Both D162 collectors must be in the boiler-room floor.");
        True(d162Floor1.Circuits.All(item => CircuitAnalyzer.Analyze(d162Floor1, item).Pass), "D162 damaged a floor-1 route.");
        Equal(8, d162Floor1.Windows.Count);
        Equal(8, d162Attic.Windows.Count);
        SequenceEqual(new[] { 100, 200, 400 }, d162Floor1.Walls.Concat(d162Attic.Walls).Select(item => item.ThicknessMm).Distinct().Order());
        Equal(16, d162Floor1.RoutingRules.PipeOuterDiameterMm);
        Equal(80, d162Floor1.RoutingRules.MinimumBendRadiusMm);
        Equal(100, d162Floor1.RoutingRules.ExteriorWallSpacingMm);
        Equal(200, d162Floor1.RoutingRules.FieldSpacingMm);
        Equal(3, d162Floor1.RoutingRules.MaximumParallelTransitPipesAt100Mm);
        Equal(100, d162Floor1.FloorBuildUps.Single().InstalledInsulationMm);
        Equal(70, d162Floor1.FloorBuildUps.Single().RemainingHeightMm);
        Equal(50, d162Attic.FloorBuildUps.Single().InstalledInsulationMm);
        Equal(70, d162Attic.FloorBuildUps.Single().RemainingHeightMm);
        Equal(15, d162Attic.Circuits.Count);
        True(d162Attic.Collectors.Single().ExternalToPlan && !d162Attic.Collectors.Single().VisibleOnPlan,
            "D162 must not draw a fake attic K2 after moving it to the boiler room.");
        var d162Analyses = d162Attic.Circuits.Select(item => CircuitAnalyzer.Analyze(d162Attic, item)).ToArray();
        True(d162Analyses.All(item => item.Pass), "D162 contains an invalid complete attic circuit candidate.");
        Equal(56_200d, d162Analyses.Min(item => item.LengthMm));
        Equal(76_200d, d162Analyses.Max(item => item.LengthMm));

        var d162Contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d162Folder, "final_dense_dual_rise_contract.json"))).RootElement;
        Equal(7, d162Contract.GetProperty("rise_strategy").GetProperty("under_stair_wall_to_wardrobe_route_count").GetInt32());
        Equal(8, d162Contract.GetProperty("rise_strategy").GetProperty("direct_boiler_slab_to_right_half_route_count").GetInt32());
        Equal(3_000, d162Contract.GetProperty("rise_strategy").GetProperty("floor_to_floor_height_mm").GetInt32());
        Equal(80, d162Contract.GetProperty("rise_strategy").GetProperty("minimum_bend_radius_mm").GetInt32());
        True(!d162Contract.GetProperty("rise_strategy").GetProperty("vertical_turn_inside_70mm_floor_layer").GetBoolean(),
            "D162 must keep R80 vertical bends outside the 70 mm floor reserve.");
        Near(88.97280430709564,
            d162Contract.GetProperty("coverage").GetProperty("served_proximity_percent").GetDouble(),
            0.000001,
            "D162 attic body-only proximity changed.");
        True(d162Contract.GetProperty("coverage_gain_vs_D160_m2").GetDouble() > 3.2,
            "D162 no longer closes the proven left-south coverage gap.");
        True(!d162Contract.GetProperty("installation_ready").GetBoolean(),
            "D162 must not claim installation release before hydraulic balancing.");

        var d163Folder = Path.Combine(proposals, "HA_TWO_FLOOR_AUDITED_DENSE_DUAL_RISE_163");
        var d163Floor1 = Load(Path.Combine(d163Folder, "HomeAura_Floor1_Audited_D163.homeaura.json"));
        var d163Attic = Load(Path.Combine(d163Folder, "HomeAura_Attic_Audited_D163.homeaura.json"));
        Equal(32, d163Floor1.Collectors.Single(item => item.Id == "K2").Ports);
        Equal("FLOOR_1-W025", d163Floor1.Collectors.Single(item => item.Id == "K2").MountingWallId);
        Equal("UP", d163Floor1.Collectors.Single(item => item.Id == "K2").PipeOutletDirection);
        Equal(180, d163Floor1.Collectors.Single(item => item.Id == "K2").RotationDegrees);
        Equal(16, d163Attic.Circuits.Count);
        True(d163Attic.Collectors.Single().ExternalToPlan && !d163Attic.Collectors.Single().VisibleOnPlan,
            "D163 must not draw a second physical K2 on the attic plan.");
        True(!d163Floor1.RoutingRules.TransitLaneGeometryVerified && !d163Attic.RoutingRules.TransitLaneGeometryVerified,
            "D163 must not certify schematic corridor centrelines as separated pipe lanes.");
        True(!d163Floor1.RoutingRules.ExteriorEdgeZoneApplied && !d163Attic.RoutingRules.ExteriorEdgeZoneApplied,
            "D163 must not claim the exterior 100 mm edge-zone pattern before it is materialized.");
        var stairReserve = d163Attic.ServiceZones.Single(item => item.Id == "K2-STAIR-WALL-BRANCH-D163");
        var directReserve = d163Attic.ServiceZones.Single(item => item.Id == "K2-DIRECT-SLAB-BRANCH-D163");
        True(!stairReserve.PipeGeometryMaterialized && !directReserve.PipeGeometryMaterialized,
            "D163 reservation zones were misrepresented as actual pipe geometry.");
        Equal(14, stairReserve.RequiredPipeCount);
        Equal(18, directReserve.RequiredPipeCount);
        Equal(1_800, stairReserve.RequiredPlanWidthMm);
        Equal(2_300, directReserve.RequiredPlanWidthMm);
        True(d163Attic.Circuits.Take(7).All(item => item.ServiceZoneId == stairReserve.Id),
            "D163 K2 under-stair branch is not contiguous on the collector port bank.");
        True(d163Attic.Circuits.Skip(7).All(item => item.ServiceZoneId == directReserve.Id),
            "D163 K2 direct branch is not contiguous on the collector port bank.");
        Equal(35.9, d163Attic.Rooms.Single(item => item.Id == "A-R09").AreaM2);
        var d163Analyses = d163Attic.Circuits.Select(item => CircuitAnalyzer.Analyze(d163Attic, item)).ToArray();
        True(d163Analyses.All(item => item.Pass), "D163 contains an invalid dense attic body candidate.");
        Equal(45_400d, d163Analyses.Min(item => item.LengthMm));
        Equal(76_200d, d163Analyses.Max(item => item.LengthMm));
        True(d163Attic.Circuits.Any(item => item.Id == "A-C08-N") && d163Attic.Circuits.Any(item => item.Id == "A-C08-S"),
            "D163 lost the two dense east-child-room spirals.");

        var d163Contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d163Folder, "audited_dense_dual_rise_contract.json"))).RootElement;
        Equal(7, d163Contract.GetProperty("rise_strategy").GetProperty("under_stair_wall_to_wardrobe_route_count").GetInt32());
        Equal(9, d163Contract.GetProperty("rise_strategy").GetProperty("direct_boiler_slab_to_right_half_route_count").GetInt32());
        True(d163Contract.GetProperty("rise_strategy").GetProperty("plan_axes_are_schematic_reservations_not_pipe_centerlines").GetBoolean(),
            "D163 must explicitly classify unseparated service axes as reservation geometry.");
        True(!d163Contract.GetProperty("rise_strategy").GetProperty("transit_lane_separation_verified").GetBoolean(),
            "D163 must not publish a false transit-lane separation pass.");
        Near(90.5529151101986,
            d163Contract.GetProperty("coverage").GetProperty("served_proximity_percent").GetDouble(),
            0.000001,
            "D163 audited attic body-only proximity changed.");
        True(d163Contract.GetProperty("coverage_gain_vs_D162_m2").GetDouble() > 2.3,
            "D163 no longer closes the independently identified centre gaps.");
        True(!d163Contract.GetProperty("installation_ready").GetBoolean(),
            "D163 must remain non-installation-ready until transit lanes and hydraulics are complete.");

        var d164Folder = Path.Combine(proposals, "HA_TWO_FLOOR_ITERATIVE_GOLDEN_MEAN_164");
        var d164Floor1 = Load(Path.Combine(d164Folder, "HomeAura_Floor1_GoldenMean_D164.homeaura.json"));
        var d164Attic = Load(Path.Combine(d164Folder, "HomeAura_Attic_GoldenMean_D164.homeaura.json"));
        Equal(15, d164Floor1.Circuits.Count);
        Equal(15, d164Attic.Circuits.Count);
        Equal(30, d164Floor1.Collectors.Single(item => item.Id == "K1").Ports);
        Equal(30, d164Floor1.Collectors.Single(item => item.Id == "K2").Ports);
        Equal(180, d164Floor1.Collectors.Single(item => item.Id == "K2").RotationDegrees);
        Equal("UP", d164Floor1.Collectors.Single(item => item.Id == "K2").PipeOutletDirection);
        True(d164Attic.Collectors.Single().ExternalToPlan && !d164Attic.Collectors.Single().VisibleOnPlan,
            "D164 must keep the physical K2 in the boiler room only.");
        True(d164Floor1.RoutingRules.ExteriorEdgeZoneApplied && d164Attic.RoutingRules.ExteriorEdgeZoneApplied,
            "D164 lost the explicitly materialized three-pass window edge bands.");
        True(!d164Floor1.RoutingRules.TransitLaneGeometryVerified && !d164Attic.RoutingRules.TransitLaneGeometryVerified,
            "D164 must not upgrade hidden service reservations into verified pipe axes.");
        Equal(3, d164Floor1.RoutingRules.MaximumParallelTransitPipesAt100Mm);
        Equal(100, d164Floor1.RoutingRules.ExteriorWallSpacingMm);
        Equal(200, d164Floor1.RoutingRules.FieldSpacingMm);
        var k1Reserve164 = d164Floor1.ServiceZones.Single(item => item.Id == "K1-HIDDEN-TRANSIT-RESERVATION-D164");
        Equal(30, k1Reserve164.RequiredPipeCount);
        True(!k1Reserve164.PipeGeometryMaterialized,
            "D164 K1 service reservation was misrepresented as installed pipe geometry.");
        var stairReserve164 = d164Attic.ServiceZones.Single(item => item.Id == "K2-STAIR-WALL-BRANCH-D164");
        var directReserve164 = d164Attic.ServiceZones.Single(item => item.Id == "K2-DIRECT-SLAB-BRANCH-D164");
        Equal(12, stairReserve164.RequiredPipeCount);
        Equal(18, directReserve164.RequiredPipeCount);
        True(!stairReserve164.PipeGeometryMaterialized && !directReserve164.PipeGeometryMaterialized,
            "D164 K2 service reservations were misrepresented as installed pipe geometry.");
        var d164FloorAnalyses = d164Floor1.Circuits.Select(item => CircuitAnalyzer.Analyze(d164Floor1, item)).ToArray();
        var d164AtticAnalyses = d164Attic.Circuits.Select(item => CircuitAnalyzer.Analyze(d164Attic, item)).ToArray();
        True(d164FloorAnalyses.All(item => item.GridAligned && item.Continuous && item.LengthInRange && item.SelfIntersections == 0 && item.InterCircuitIntersections == 0),
            "D164 floor-one body geometry contains a topology, length, or contact defect.");
        True(d164AtticAnalyses.All(item => item.GridAligned && item.Continuous && item.LengthInRange && item.SelfIntersections == 0 && item.InterCircuitIntersections == 0),
            "D164 attic body geometry contains a topology, length, or contact defect.");

        var d164Contract = JsonDocument.Parse(File.ReadAllText(Path.Combine(d164Folder, "iterative_golden_mean_contract.json"))).RootElement;
        Equal(15, d164Contract.GetProperty("collector_allocation").GetProperty("K1_floor1_circuit_count").GetInt32());
        Equal(15, d164Contract.GetProperty("collector_allocation").GetProperty("K2_attic_circuit_count").GetInt32());
        Equal(3, d164Contract.GetProperty("room_allocation").GetProperty("attic").GetProperty("large_bedroom").GetInt32());
        Equal(1, d164Contract.GetProperty("room_allocation").GetProperty("floor1").GetProperty("hall").GetInt32());
        True(!d164Contract.GetProperty("owner_rules").GetProperty("penetration_sleeves_required").GetBoolean(),
            "D164 reintroduced sleeves despite the owner's explicit prohibition.");
        Equal(8, d164Contract.GetProperty("floor1_window_edge_audit").GetProperty("pass_count").GetInt32());
        Equal(8, d164Contract.GetProperty("attic_window_edge_audit").GetProperty("pass_count").GetInt32());
        True(d164Contract.GetProperty("all_design_lengths_40_80m").GetBoolean(),
            "D164 has a design length outside the 40-80 m band.");
        True(d164Contract.GetProperty("minimum_design_length_mm").GetInt32() >= 40_000,
            "D164 minimum design length fell below 40 m.");
        True(d164Contract.GetProperty("maximum_design_length_mm").GetInt32() <= 80_000,
            "D164 maximum design length exceeded 80 m.");
        Equal(0, d164Contract.GetProperty("body_contact_count").GetInt32());
        True(d164Contract.GetProperty("floor1_coverage").GetProperty("served_percent").GetDouble() > 81.0,
            "D164 floor-one body-only coverage regressed.");
        True(d164Contract.GetProperty("attic_coverage").GetProperty("served_percent").GetDouble() > 87.0,
            "D164 attic body-only coverage regressed.");
        True(!d164Contract.GetProperty("installation_ready").GetBoolean(),
            "D164 must remain non-installation-ready until individual service axes and hydraulics exist.");
    }

    private static IEnumerable<string> RouteKeys(HomeAuraProject project) => project.Circuits.Select(circuit =>
        $"{circuit.Id}|{circuit.ConcealedServiceLengthMm}|{string.Join(';', circuit.OrderedPoints.Select(point => $"{point.X},{point.Y}"))}");

    private static double MinimumDistance(PointMm point, IReadOnlyList<PointMm> route)
    {
        var minimum = double.PositiveInfinity;
        for (var index = 1; index < route.Count; index++)
        {
            var first = route[index - 1];
            var second = route[index];
            var dx = second.X - first.X;
            var dy = second.Y - first.Y;
            var denominator = (double)dx * dx + (double)dy * dy;
            var t = denominator == 0
                ? 0
                : Math.Clamp(((point.X - first.X) * dx + (point.Y - first.Y) * dy) / denominator, 0, 1);
            var x = first.X + t * dx;
            var y = first.Y + t * dy;
            minimum = Math.Min(minimum, Math.Sqrt(Math.Pow(point.X - x, 2) + Math.Pow(point.Y - y, 2)));
        }
        return minimum;
    }

    private static double MinimumSegmentLength(IReadOnlyList<PointMm> route)
    {
        var minimum = double.PositiveInfinity;
        for (var index = 1; index < route.Count; index++)
            minimum = Math.Min(minimum, CircuitAnalyzer.Distance(route[index - 1], route[index]));
        return minimum;
    }

    private static bool IsGridPoint(PointMm point) => point.X % 100 == 0 && point.Y % 100 == 0;

    private static HomeAuraProject Load(string path)
    {
        True(File.Exists(path), $"Missing exact-house artifact: {path}");
        return HomeAuraProject.FromJson(File.ReadAllText(path));
    }

    private static void True(bool value, string message)
    {
        if (!value) throw new Exception(message);
    }

    private static void Equal<T>(T expected, T actual)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new Exception($"Expected {expected}, got {actual}.");
    }

    private static void Near(double expected, double actual, double tolerance, string message)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new Exception($"{message} Expected {expected}, got {actual}.");
    }

    private static void SequenceEqual<T>(IEnumerable<T> expected, IEnumerable<T> actual)
    {
        if (!expected.SequenceEqual(actual)) throw new Exception("Sequences differ.");
    }
}
