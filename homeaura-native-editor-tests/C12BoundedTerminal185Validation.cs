using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class C12BoundedTerminal185Validation
{
    private const string CircuitId = "F1-D171-C12";
    private const string D184Sha = "1A00E6B7539A0A704F1341BCCEB5982BB79B95F9520C4713D8791B573A511852";
    private const string ProjectSha = "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4";
    private const string DiagnosticsSha = "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9";
    private const string PointsSha = "DD22AE876B20A50149C67EAE3FB35653D04C705C0A064A5453542EDC5C745FCB";
    private const string AcceptedScaffoldPackageSha =
        "EB6A27C3773166CEFAA072E5C6E293AB24BFE5FB1A00B89EFDDD662B7E7A5CDA";
    private const double Raw3DLengthMm = 73_877.03857936525;
    private const double RoundedLengthMm = 72_846.94976367301;
    private const double SupplyTailGapMm = 3_957.4620971021313;
    private const double ReturnTailGapMm = 3_960.6194275643297;
    private const double TailLowerBoundMm = 7_918.081524666461;
    private const double ExactTailTotalLowerBoundMm = 80_765.03128833947;
    private const double MinimumShorteningMm = 765.03128833947;

    public static void Run()
    {
        var root = FindRoot();
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var sourcePath = Path.Combine(proposals, "HA_TWO_FLOOR_R07_POINT3_ROUTES_184",
            "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json");
        var official = Path.Combine(proposals, "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185");
        var isOfficial = Directory.Exists(official);
        var directory = isOfficial ? official : Path.Combine(root, "tmp", "D185_scaffold");
        var package = isOfficial
            ? Path.Combine(proposals, "packages", "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185.zip")
            : Path.Combine(root, "tmp", "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185_SCAFFOLD.zip");
        var projectPath = Path.Combine(directory, "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json");
        var diagnosticsPath = Path.Combine(directory, "engineering_diagnostics.json");
        var contractPath = Path.Combine(directory, "floor1_c12_bounded_terminal_contract.json");
        var reportPath = Path.Combine(directory, "floor1_c12_bounded_terminal_report.json");
        var statusPath = Path.Combine(directory, "status.json");

        Equal(D184Sha, Sha(sourcePath), "D184 source");
        Equal(ProjectSha, Sha(projectPath), "D185 exact project");
        Equal(DiagnosticsSha, Sha(diagnosticsPath), "D185 current-Release diagnostics");
        ValidateAppendOnly(sourcePath, projectPath);
        ValidateNoStructuredSleeves(projectPath);

        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        ValidateCircuit(project);
        ValidateProjectBoundary(project);
        ValidateDiagnostics(diagnosticsPath);
        ValidateContract(contractPath, reportPath, statusPath, isOfficial);
        ValidatePackage(directory, package);
        ValidateProgramRegistration(root, isOfficial);
    }

    private static void ValidateAppendOnly(string sourcePath, string projectPath)
    {
        using var source = JsonDocument.Parse(File.ReadAllText(sourcePath));
        using var project = JsonDocument.Parse(File.ReadAllText(projectPath));
        var sourceNames = source.RootElement.EnumerateObject().Select(item => item.Name).Order().ToArray();
        var projectNames = project.RootElement.EnumerateObject().Select(item => item.Name).Order().ToArray();
        Check(sourceNames.SequenceEqual(projectNames), "D185 changed top-level property names.");
        foreach (var property in source.RootElement.EnumerateObject().Where(item => item.Name != "circuits"))
        {
            Check(project.RootElement.TryGetProperty(property.Name, out var current) &&
                  JsonElement.DeepEquals(property.Value, current), $"D185 changed non-circuit payload {property.Name}.");
        }

        var sourceCircuits = source.RootElement.GetProperty("circuits").EnumerateArray()
            .ToDictionary(item => item.GetProperty("id").GetString()!, item => item.Clone());
        var projectCircuits = project.RootElement.GetProperty("circuits").EnumerateArray()
            .ToDictionary(item => item.GetProperty("id").GetString()!, item => item.Clone());
        Check(sourceCircuits.Keys.Order().SequenceEqual(projectCircuits.Keys.Order()),
            "D185 changed the circuit identity set.");
        var changed = sourceCircuits.Keys.Where(id => !JsonElement.DeepEquals(sourceCircuits[id], projectCircuits[id]))
            .Order().ToArray();
        Check(changed.SequenceEqual([CircuitId]), "D185 is not an only-C12 append-only change.");
    }

    private static void ValidateCircuit(HomeAuraProject project)
    {
        var circuit = project.Circuits.Single(item => item.Id == CircuitId);
        Check(circuit.SystemRole == "FLOOR_HEATING_LOOP" && circuit.CollectorId == "K1" &&
              circuit.SupplyPortIndex == 22 && circuit.ReturnPortIndex == 23 && circuit.Completed,
            "D185 C12 role, ports, or bounded completion changed.");
        Check(circuit.ConcealedServiceLengthMm == 0 && circuit.OutOfPlaneLengthMm == 0 &&
              circuit.OrderedPoints.Count == 38 && circuit.OrderedPoints.All(item => item.Z is not null),
            "D185 C12 is not the exact visible Point3 route.");
        Check(circuit.HeatingBodyRanges.Select(item => (item.StartIndex, item.EndIndex)).SequenceEqual([(8, 31)]),
            "D185 C12 BODY range changed.");
        Check(circuit.VerticalTransitions.Select(item => item.SegmentIndex).SequenceEqual([1, 4, 7, 31, 35]) &&
              circuit.VerticalTransitions.All(item => item.Kind == "S_BEND_R80" && item.RadiusMm == 80 &&
                                                      item.ArcSamplesPerHalf >= 12),
            "D185 C12 S-bend records changed.");
        Equal(PointsSha, HashPoints(circuit.OrderedPoints), "D185 C12 ordered points");
        Check(circuit.OrderedPoints[31] is {X: 12800, Y: 20300, Z: 108} &&
              circuit.OrderedPoints[32] is {X: 12600, Y: 20300, Z: 70},
            "D185 materialized terminal ramp endpoints changed.");

        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.Completed && analysis.Pass && analysis.TopologyPass && analysis.EngineeringPass &&
              analysis.GridAligned && analysis.Continuous && analysis.Orthogonal && analysis.LengthInRange &&
              analysis.RoundedLengthInRange && analysis.StartAtCollector && analysis.EndAtCollector &&
              analysis.VerticalGeometryMaterialized && analysis.VerticalTransitionRadiusFeasible &&
              analysis.BendRadiusFeasible, "D185 C12 native physical route gates changed.");
        Check(analysis.SelfIntersections == 0 && analysis.SelfSurfaceClearanceViolations == 0 &&
              analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0 &&
              analysis.HeatingBodyWallIntrusions == 0 && analysis.HorizontalTurnWallIntrusions == 0 &&
              analysis.BendRadiusViolationCount == 0 && analysis.UnmaterializedElevationChangeCount == 0,
            "D185 C12 native zero-defect gates changed.");
        Check(!analysis.Exterior3x100Pass && !analysis.Exterior3x100UsefulSpanPass &&
              !analysis.ExteriorOpenSpiralTerminalCornerPass &&
              analysis.ExteriorOpenSpiralMaterializedTerminalRampApplicable &&
              analysis.ExteriorOpenSpiralMaterializedTerminalRampPass,
            "D185 legacy/sibling exterior gate boundary changed.");
        Close(Raw3DLengthMm, analysis.AxisLengthMm, .000001, "D185 raw 3D length");
        Close(RoundedLengthMm, analysis.RoundedAxisLengthMm, .000001, "D185 rounded R80 length");

        var sibling = analysis.ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(sibling is
            {
                RoomId: "F1-R01", Applicable: true, Pass: true,
                Reason: "PASS_MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE",
                BodyRangeStartIndex: 8, BodyRangeEndIndex: 31, BodyEndpointSide: "END",
                CircuitSegmentIndex: 31, TransitionKind: "S_BEND_R80", TransitionMaterializedPass: true,
                WallId: "FLOOR_1-W030", LaneIndex: 2, MissingLengthMm: 200,
                RampProjectedLengthMm: 200, AdjacentBodyEndpointPass: true,
                SameHeadingContinuationPass: true, ExactGapMatchPass: true, WindowlessGapPass: true,
                NoTerminalWallOrOtherLaneContributionPass: true, DeficientWallSharesOpenCornerPass: true,
                GapAtSharedOpenCornerPass: true, AssignedRoomWallClearPass: true,
                FullCircuitPhysicalGatePass: true, NativeCollectorTerminalTolerancePass: true,
                GlobalInterCircuitContactPass: true, CompletionCandidateCount: 1,
                AugmentedCoveragePercent: 100, AugmentedWindowCoveragePercent: 100,
                AugmentedStrictLanePass: true, AugmentedAllNonTerminalWallsStrictPass: true,
                AugmentedOpenCornerAdjacencyPass: true, OpenTerminalWallId: "FLOOR_1-W033",
                OpenTerminalSide: "START"
            }, "D185 native materialized-terminal-ramp payload changed.");
        Check(sibling.MissingInterval is {Start: {X: 12600, Y: 20300}, End: {X: 12800, Y: 20300}} &&
              sibling.RampProjectedInterval is {Start: {X: 12600, Y: 20300}, End: {X: 12800, Y: 20300}},
            "D185 sibling gap/ramp intervals changed.");
    }

    private static void ValidateProjectBoundary(HomeAuraProject project)
    {
        var k1Ports = project.Circuits.Where(item => item.CollectorId == "K1")
            .SelectMany(item => new int?[] {item.SupplyPortIndex, item.ReturnPortIndex})
            .Where(item => item is not null).Select(item => item!.Value).Order().ToArray();
        Check(k1Ports.SequenceEqual(Enumerable.Range(0, 28)), "D185 K1 does not own ports 0..27 exactly once.");
        Equal(14, project.Circuits.Count(item => item.SystemRole == "FLOOR_HEATING_LOOP"), "D185 loop count");
        Equal(0, project.Circuits.Count(item => item.SystemRole == "FLOOR_HEATING_AXIS"), "D185 AXIS count");
        Check(project.Circuits.Where(item => item.SystemRole == "FLOOR_HEATING_LOOP")
            .Select(item => CircuitAnalyzer.Analyze(project, item))
            .All(item => item.Pass && item.TopologyPass && item.EngineeringPass),
            "D185 bounded Point3 loop set no longer passes natively.");
    }

    private static void ValidateDiagnostics(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        var circuit = root.GetProperty("circuits").EnumerateArray()
            .Single(item => item.GetProperty("circuit_id").GetString() == CircuitId);
        Check(circuit.GetProperty("exterior_open_spiral_materialized_terminal_ramp_applicable").GetBoolean() &&
              circuit.GetProperty("exterior_open_spiral_materialized_terminal_ramp_pass").GetBoolean(),
            "D185 diagnostics lost the final native sibling gate.");
        using var expected = JsonDocument.Parse(ExpectedSiblingJson);
        Check(JsonElement.DeepEquals(expected.RootElement,
            circuit.GetProperty("exterior_open_spiral_materialized_terminal_ramp")),
            "D185 diagnostics sibling payload is not exact.");
        Check(!circuit.GetProperty("exterior3x100_pass").GetBoolean() &&
              !circuit.GetProperty("exterior3x100_useful_span_pass").GetBoolean() &&
              !circuit.GetProperty("exterior_open_spiral_terminal_corner_pass").GetBoolean() &&
              circuit.GetProperty("completed").GetBoolean() && circuit.GetProperty("start_at_collector").GetBoolean() &&
              circuit.GetProperty("end_at_collector").GetBoolean(),
            "D185 diagnostics changed legacy-false or bounded-completion truth.");
        Check(!root.GetProperty("design_pass").GetBoolean() &&
              !root.GetProperty("installation_completeness_pass").GetBoolean() &&
              root.GetProperty("axis_only_circuit_count").GetInt32() == 0 &&
              root.GetProperty("total_concealed_service_length_mm").GetDouble() == 0,
            "D185 project completeness truth changed.");
        var k1 = root.GetProperty("collector_served_floor_details").EnumerateArray()
            .Single(item => item.GetProperty("collector_id").GetString() == "K1");
        var k2 = root.GetProperty("collector_served_floor_details").EnumerateArray()
            .Single(item => item.GetProperty("collector_id").GetString() == "K2");
        Check(k1.GetProperty("loop_circuit_count").GetInt32() == 14 &&
              k1.GetProperty("axis_circuit_count").GetInt32() == 0 &&
              k2.GetProperty("heating_body_count").GetInt32() == 0 &&
              k2.GetProperty("loop_circuit_count").GetInt32() == 0 &&
              k2.GetProperty("axis_circuit_count").GetInt32() == 0,
            "D185 K1/K2 bounded served-floor counts changed.");
    }

    private static void ValidateContract(string contractPath, string reportPath, string statusPath, bool isOfficial)
    {
        using var contractDocument = JsonDocument.Parse(File.ReadAllText(contractPath));
        using var reportDocument = JsonDocument.Parse(File.ReadAllText(reportPath));
        using var statusDocument = JsonDocument.Parse(File.ReadAllText(statusPath));
        var contract = contractDocument.RootElement;
        var report = reportDocument.RootElement;
        var status = statusDocument.RootElement;
        Equal("HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185", contract.GetProperty("artifact_id").GetString(),
            "D185 artifact id");
        Check(!contract.GetProperty("publishable").GetBoolean() &&
              !contract.GetProperty("publishable_as_installation_project").GetBoolean() &&
              !contract.GetProperty("installation_truth").GetProperty("installation_ready").GetBoolean(),
            "D185 incorrectly claims installation readiness.");
        if (!isOfficial)
        {
            Equal("SCAFFOLD_HARD_GUARD_ACTIVE_NOT_OFFICIAL", contract.GetProperty("publication_state").GetString(),
                "D185 scaffold publication state");
            var guard = contract.GetProperty("publication_guard");
            Check(guard.GetProperty("active").GetBoolean() &&
                  !guard.GetProperty("official_publication_allowed").GetBoolean() &&
                  !guard.GetProperty("Program_registration_allowed").GetBoolean() &&
                  !guard.GetProperty("official_freeze_allowed").GetBoolean() &&
                  guard.GetProperty("native_final_materialized_terminal_ramp_gate").GetString() == "PASS" &&
                  guard.GetProperty("independent_GO_required").GetInt32() == 2 &&
                  guard.GetProperty("independent_GO_received").GetInt32() == 0,
                "D185 scaffold publication guard changed.");
        }
        else
        {
            Equal("OFFICIAL_BOUNDED_TERMINAL_D185", contract.GetProperty("publication_state").GetString(),
                "D185 official publication state");
            Equal("OFFICIAL_BOUNDED_TERMINAL_D185", contract.GetProperty("status").GetString(),
                "D185 official status");
            var guard = contract.GetProperty("publication_guard");
            Check(!guard.GetProperty("active").GetBoolean() &&
                  guard.GetProperty("official_publication_allowed").GetBoolean() &&
                  guard.GetProperty("Program_registration_allowed").GetBoolean() &&
                  guard.GetProperty("official_freeze_allowed").GetBoolean() &&
                  guard.GetProperty("native_final_materialized_terminal_ramp_gate").GetString() == "PASS" &&
                  guard.GetProperty("independent_GO_required").GetInt32() == 2 &&
                  guard.GetProperty("independent_GO_received").GetInt32() == 2 &&
                  guard.GetProperty("explicit_root_GO_received").GetBoolean() &&
                  guard.GetProperty("bounded_terminal_publication_gate").GetString() == "PASS" &&
                  !guard.GetProperty("installation_publication_allowed").GetBoolean() &&
                  !guard.GetProperty("exact_Eurocone_continuity_claim_allowed").GetBoolean(),
                "D185 official bounded-terminal guard/evidence boundary changed.");
            var audit = contract.GetProperty("independent_audit_evidence");
            Check(audit.GetProperty("accepted_scaffold_package_sha256").GetString() == AcceptedScaffoldPackageSha &&
                  audit.GetProperty("required_formal_GO_count").GetInt32() == 2 &&
                  audit.GetProperty("received_formal_GO_count").GetInt32() == 2 &&
                  audit.GetProperty("formal_GO_records").GetArrayLength() == 2 &&
                  audit.GetProperty("formal_GO_records").EnumerateArray().All(item =>
                      item.GetProperty("package_sha256").GetString() == AcceptedScaffoldPackageSha &&
                      item.GetProperty("verdict").GetString() == "GO_BOUNDED_TERMINAL_SCAFFOLD_V2") &&
                  audit.GetProperty("explicit_root_GO_received").GetBoolean() &&
                  audit.GetProperty("publication_scope").GetString() == "OFFICIAL_BOUNDED_TERMINAL_ONLY",
                "D185 official independent/root GO evidence changed.");
        }

        var sibling = contract.GetProperty("additive_sibling_materialized_terminal_ramp");
        using var expectedSibling = JsonDocument.Parse(ExpectedSiblingJson);
        foreach (var property in expectedSibling.RootElement.EnumerateObject())
            Check(sibling.TryGetProperty(property.Name, out var actual) && JsonElement.DeepEquals(property.Value, actual),
                $"D185 contract sibling field changed: {property.Name}.");
        Check(sibling.GetProperty("source").GetString() == "CURRENT_RELEASE_NATIVE_DIAGNOSTICS" &&
              sibling.GetProperty("segment_role").GetString() == "TRANSIT" &&
              !sibling.GetProperty("BODY_role_extended").GetBoolean() &&
              !sibling.GetProperty("arbitrary_TRANSIT_counted_as_BODY").GetBoolean(),
            "D185 contract widened the narrow sibling claim.");

        var tails = contract.GetProperty("collector_terminal_grid");
        Close(SupplyTailGapMm, tails.GetProperty("supply_terminal_to_Eurocone_straight_gap_mm").GetDouble(),
            1e-9, "D185 supply tail gap");
        Close(ReturnTailGapMm, tails.GetProperty("return_terminal_to_Eurocone_straight_gap_mm").GetDouble(),
            1e-9, "D185 return tail gap");
        Close(TailLowerBoundMm, tails.GetProperty("hard_sum_Euclidean_tail_gaps_lower_bound_mm").GetDouble(),
            1e-9, "D185 tail lower bound");
        Close(ExactTailTotalLowerBoundMm,
            tails.GetProperty("rounded_route_plus_exact_tail_lower_bound_mm").GetDouble(),
            1e-9, "D185 exact-tail total lower bound");
        Close(MinimumShorteningMm, tails.GetProperty("exceeds_80m_by_mm").GetDouble(),
            1e-9, "D185 80 m excess");
        Check(tails.GetProperty("minimum_route_shortening_required_mm_to_0_001").GetDouble() == 765.032 &&
              tails.GetProperty("exact_Eurocone_tails_cannot_be_appended_within_80m").GetBoolean() &&
              !tails.GetProperty("physical_Eurocone_tails_materialized").GetBoolean() &&
              tails.GetProperty("tails_deferred").GetBoolean() &&
              tails.GetProperty("collectorContinuous").GetInt32() == 0 &&
              tails.GetProperty("completeK1").GetInt32() == 0,
            "D185 tail/continuity claim boundary changed.");
        Close(TailLowerBoundMm, SupplyTailGapMm + ReturnTailGapMm, 1e-9, "D185 arithmetic tail sum");
        Close(ExactTailTotalLowerBoundMm, RoundedLengthMm + TailLowerBoundMm, 1e-9,
            "D185 arithmetic total lower bound");
        Close(MinimumShorteningMm, ExactTailTotalLowerBoundMm - 80_000, 1e-9,
            "D185 arithmetic shortening lower bound");

        var completion = contract.GetProperty("native_completion_claim_boundary");
        Check(completion.GetProperty("native_completed").GetBoolean() &&
              completion.GetProperty("native_start_at_collector").GetBoolean() &&
              completion.GetProperty("native_end_at_collector").GetBoolean() &&
              completion.GetProperty("K1_connection_tolerance_mm").GetInt32() == 4100 &&
              completion.GetProperty("native_collector_terminal_tolerance_pass").GetBoolean() &&
              completion.GetProperty("does_not_mean_exact_Eurocone_continuity").GetBoolean() &&
              completion.GetProperty("collectorContinuous").GetInt32() == 0 &&
              completion.GetProperty("completeK1").GetInt32() == 0,
            "D185 native completed:true claim boundary changed.");
        Check(JsonElement.DeepEquals(tails, report.GetProperty("collector_terminal_grid")) &&
              JsonElement.DeepEquals(completion, report.GetProperty("native_completion_claim_boundary")) &&
              status.GetProperty("native_completed_does_not_mean_exact_Eurocone_continuity").GetBoolean() &&
              !status.GetProperty("physical_Eurocone_tails_materialized").GetBoolean() &&
              status.GetProperty("minimum_route_shortening_required_mm_to_0_001").GetDouble() == 765.032,
            "D185 contract/report/status claim boundary diverged.");

        var morphology = contract.GetProperty("BODY_morphology");
        Check(morphology.GetProperty("classification").GetString() ==
                  "ONE_COHERENT_REFLECTED_TWO_ARM_COUNTERFLOW" &&
              morphology.GetProperty("intended_open_terminal_wall").GetString() == "FLOOR_1-W033" &&
              morphology.GetProperty("physical_axis_simple").GetBoolean() &&
              morphology.GetProperty("pipe16_inside_clear_domain").GetBoolean(),
            "D185 BODY morphology identity changed.");
        Close(98.74853523263984, morphology.GetProperty("physical_R80_q128_served_percent").GetDouble(),
            1e-12, "D185 BODY q128 coverage");
        Close(174.55844122715774, morphology.GetProperty("maximum_sample_distance_mm").GetDouble(),
            1e-9, "D185 BODY maximum sample distance");
        Equal(0, morphology.GetProperty("sample_over_200mm_count").GetInt32(), "D185 BODY samples over 200 mm");

        var walls = contract.GetProperty("wall_crossing_audit");
        Check(walls.GetProperty("pass").GetBoolean() && walls.GetProperty("intersection_count").GetInt32() == 4 &&
              walls.GetProperty("body_wall_hit_count").GetInt32() == 0 &&
              walls.GetProperty("nonperpendicular_transit_count").GetInt32() == 0 &&
              walls.GetProperty("overlength_transit_count").GetInt32() == 0 &&
              walls.GetProperty("records").GetArrayLength() == 4 &&
              walls.GetProperty("records").EnumerateArray().All(item =>
                  item.GetProperty("role").GetString() == "TRANSIT" &&
                  item.GetProperty("perpendicular").GetBoolean() &&
                  item.GetProperty("within_wall_thickness").GetBoolean()),
            "D185 wall-crossing audit changed.");
        var bank = contract.GetProperty("global_same_layer_bank_audit");
        Check(bank.GetProperty("pass").GetBoolean() &&
              bank.GetProperty("maximum_axes_in_inclusive_300mm_window").GetInt32() == 3,
            "D185 global same-layer bank audit changed.");

        var installation = contract.GetProperty("installation_truth");
        var bounded = contract.GetProperty("bounded_project_counts");
        Check(installation.GetProperty("structured_sleeve_geometry_count").GetInt32() == 0 &&
              !installation.GetProperty("sleeves_added").GetBoolean() &&
              !installation.GetProperty("installation_completeness_pass").GetBoolean() &&
              !installation.GetProperty("installation_ready").GetBoolean() &&
              !installation.GetProperty("design_pass").GetBoolean() &&
              installation.GetProperty("K2_ATTIC_materialized_routes").GetInt32() == 0 &&
              bounded.GetProperty("FLOOR_1_loop_route_count").GetInt32() == 14 &&
              bounded.GetProperty("axis_only_circuit_count").GetInt32() == 0 &&
              bounded.GetProperty("total_concealed_service_length_mm").GetDouble() == 0 &&
              bounded.GetProperty("total_out_of_plane_length_mm").GetDouble() == 0 &&
              bounded.GetProperty("K2_ATTIC_heating_body_count").GetInt32() == 0 &&
              bounded.GetProperty("K2_ATTIC_loop_route_count").GetInt32() == 0 &&
              bounded.GetProperty("K2_ATTIC_axis_route_count").GetInt32() == 0 &&
              !status.GetProperty("sleeves_added").GetBoolean() &&
              !status.GetProperty("installation_ready").GetBoolean() &&
              status.GetProperty("K2_ATTIC_materialized_routes").GetInt32() == 0,
            "D185 sleeve/install/K2 bounded truth changed.");
        Check(JsonElement.DeepEquals(morphology, report.GetProperty("BODY_morphology")) &&
              JsonElement.DeepEquals(walls, report.GetProperty("wall_crossing_audit")) &&
              JsonElement.DeepEquals(bank, report.GetProperty("global_same_layer_bank_audit")) &&
              JsonElement.DeepEquals(installation, report.GetProperty("installation_truth")) &&
              JsonElement.DeepEquals(bounded, report.GetProperty("bounded_project_counts")),
            "D185 contract/report morphology, wall, bank, or bounded truth diverged.");
    }

    private static void ValidateNoStructuredSleeves(string projectPath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(projectPath));
        Check(StructuredSleeveKeys(document.RootElement).Count == 0,
            "D185 project contains structured sleeve geometry.");
    }

    private static void ValidatePackage(string directory, string package)
    {
        foreach (var name in new[]
                 {
                     "HomeAura_Floor1_D185_Clean_View.png",
                     "HomeAura_Floor1_D185_R01_C12_Clean_Zoom.png",
                     "HomeAura_Floor1_D185_R01_C12_3D_Diagnostic.png",
                     "engineering_diagnostics.json", "floor1_c12_bounded_terminal_contract.json",
                     "floor1_c12_bounded_terminal_report.json", "status.json", "render_provenance.json",
                     "README.md", "artifact_manifest.json"
                 })
            Check(new FileInfo(Path.Combine(directory, name)) is {Exists: true, Length: > 0}, $"D185 missing {name}.");
        foreach (var name in new[]
                 {
                     "HomeAura_Floor1_D185_Clean_View.png",
                     "HomeAura_Floor1_D185_R01_C12_Clean_Zoom.png",
                     "HomeAura_Floor1_D185_R01_C12_3D_Diagnostic.png"
                 })
        {
            var bytes = File.ReadAllBytes(Path.Combine(directory, name));
            Check(bytes.Length > 24 && bytes.AsSpan(0, 8).SequenceEqual(new byte[] {137, 80, 78, 71, 13, 10, 26, 10}),
                $"D185 render is not PNG: {name}.");
        }

        using var renderDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "render_provenance.json")));
        var renderRoot = renderDocument.RootElement;
        var full = renderRoot.GetProperty("full_floor_clean");
        Check(full.GetProperty("included_level_ids").EnumerateArray().Select(item => item.GetString())
                  .SequenceEqual(["FLOOR_1"]) &&
              full.GetProperty("excluded_level_ids").EnumerateArray().Select(item => item.GetString())
                  .SequenceEqual(["ATTIC"]) &&
              !full.GetProperty("ATTIC_overlay_rendered").GetBoolean(),
            "D185 full-floor render provenance changed.");
        foreach (var key in new[] {"R01_C12_clean", "R01_C12_3D_diagnostic"})
        {
            var room = renderRoot.GetProperty(key);
            Check(room.GetProperty("room_id").GetString() == "F1-R01" &&
                  room.GetProperty("source_scope").GetString() == "ROOM_CROP_WITH_PROJECT_CONTEXT" &&
                  room.GetProperty("render_scope").GetString() == "ROOM_CROP_WITH_PROJECT_CONTEXT" &&
                  room.GetProperty("focus_circuit_ids").EnumerateArray().Select(item => item.GetString())
                      .SequenceEqual([CircuitId]) &&
                  room.GetProperty("context_circuits_rendered").GetBoolean() &&
                  !room.GetProperty("exclusive_circuit_filter_applied").GetBoolean() &&
                  !room.TryGetProperty("circuit_ids", out _),
                $"D185 room render provenance falsely claims exclusive C12 scope: {key}.");
        }

        using var manifestDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        var manifest = manifestDocument.RootElement;
        Equal(ProjectSha, manifest.GetProperty("project_sha256").GetString(), "D185 manifest project hash");
        Equal(DiagnosticsSha, manifest.GetProperty("engineering_diagnostics_sha256").GetString(),
            "D185 manifest diagnostics hash");
        if (manifest.TryGetProperty("accepted_scaffold_package_sha256", out var accepted))
            Equal(AcceptedScaffoldPackageSha, accepted.GetString(), "D185 manifest accepted scaffold hash");
        var listed = new HashSet<string>(StringComparer.Ordinal);
        foreach (var item in manifest.GetProperty("files").EnumerateArray())
        {
            var name = item.GetProperty("name").GetString()!;
            var file = Path.Combine(directory, name);
            Check(listed.Add(name) && File.Exists(file) && new FileInfo(file).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(file) == item.GetProperty("sha256").GetString(), $"D185 manifest mismatch: {file}");
        }
        var localPayloads = Directory.GetFiles(directory).Select(path => Path.GetFileName(path)!)
            .Where(name => name != "artifact_manifest.json")
            .ToHashSet(StringComparer.Ordinal);
        Check(listed.SetEquals(localPayloads), "D185 manifest payload set is not exact.");

        using var archive = ZipFile.OpenRead(package);
        var expectedNames = Directory.GetFiles(directory).Select(path => Path.GetFileName(path)!)
            .ToHashSet(StringComparer.Ordinal);
        Check(archive.Entries.Select(item => item.FullName).ToHashSet(StringComparer.Ordinal).SetEquals(expectedNames),
            "D185 ZIP member set is not exact.");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D185 ZIP byte parity failed: {entry.FullName}");
            Check(entry.LastWriteTime.Year == 1980 && entry.LastWriteTime.Month == 1 && entry.LastWriteTime.Day == 1,
                $"D185 ZIP timestamp is not deterministic: {entry.FullName}");
        }
    }

    private static void ValidateProgramRegistration(string root, bool isOfficial)
    {
        var program = File.ReadAllText(Path.Combine(root, "homeaura-native-editor-tests", "Program.cs"));
        var registered = program.Contains("C12BoundedTerminal185Validation.Run", StringComparison.Ordinal);
        Check(registered == isOfficial,
            isOfficial ? "D185 hermetic validation is not registered in Program."
                       : "D185 hermetic validation was registered before official publication.");
    }

    private static List<string> StructuredSleeveKeys(JsonElement value, string prefix = "")
    {
        var result = new List<string>();
        if (value.ValueKind == JsonValueKind.Object)
        {
            foreach (var property in value.EnumerateObject())
            {
                var path = $"{prefix}/{property.Name}";
                if (property.Name.Contains("sleeve", StringComparison.OrdinalIgnoreCase) ||
                    property.Name.Contains("гильз", StringComparison.OrdinalIgnoreCase))
                    result.Add(path);
                result.AddRange(StructuredSleeveKeys(property.Value, path));
            }
        }
        else if (value.ValueKind == JsonValueKind.Array)
        {
            var index = 0;
            foreach (var item in value.EnumerateArray()) result.AddRange(StructuredSleeveKeys(item, $"{prefix}/{index++}"));
        }
        return result;
    }

    private static string FindRoot()
    {
        foreach (var seed in new[] {Directory.GetCurrentDirectory(), AppContext.BaseDirectory})
        {
            for (var current = new DirectoryInfo(Path.GetFullPath(seed)); current is not null; current = current.Parent)
                if (Directory.Exists(Path.Combine(current.FullName, "homeaura-native-editor")) &&
                    Directory.Exists(Path.Combine(current.FullName, "homeaura-native-editor-tests")))
                    return current.FullName;
        }
        throw new DirectoryNotFoundException("HomeAura repository root was not found.");
    }

    private static string HashPoints(IEnumerable<PointMm> points)
    {
        var value = string.Join("|", points.Select(point => $"{point.X},{point.Y},{point.Z}"));
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
    }

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Close(double expected, double actual, double tolerance, string label)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }
    private static void Equal<T>(T expected, T actual, string label)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }
    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }

    private const string ExpectedSiblingJson = """
    {
      "room_id": "F1-R01",
      "applicable": true,
      "pass": true,
      "reason": "PASS_MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE",
      "body_range_start_index": 8,
      "body_range_end_index": 31,
      "body_endpoint_side": "END",
      "circuit_segment_index": 31,
      "transition_kind": "S_BEND_R80",
      "transition_materialized_pass": true,
      "wall_id": "FLOOR_1-W030",
      "lane_index": 2,
      "missing_interval": {"start": {"x_mm": 12600, "y_mm": 20300}, "end": {"x_mm": 12800, "y_mm": 20300}},
      "ramp_projected_interval": {"start": {"x_mm": 12600, "y_mm": 20300}, "end": {"x_mm": 12800, "y_mm": 20300}},
      "missing_length_mm": 200,
      "ramp_projected_length_mm": 200,
      "adjacent_body_endpoint_pass": true,
      "same_heading_continuation_pass": true,
      "exact_gap_match_pass": true,
      "windowless_gap_pass": true,
      "no_terminal_wall_or_other_lane_contribution_pass": true,
      "deficient_wall_shares_open_corner_pass": true,
      "gap_at_shared_open_corner_pass": true,
      "assigned_room_wall_clear_pass": true,
      "full_circuit_physical_gate_pass": true,
      "native_collector_terminal_tolerance_pass": true,
      "global_inter_circuit_contact_pass": true,
      "completion_candidate_count": 1,
      "augmented_coverage_percent": 100,
      "augmented_window_coverage_percent": 100,
      "augmented_strict_lane_pass": true,
      "augmented_all_non_terminal_walls_strict_pass": true,
      "augmented_open_corner_adjacency_pass": true,
      "open_terminal_wall_id": "FLOOR_1-W033",
      "open_terminal_side": "START"
    }
    """;
}
