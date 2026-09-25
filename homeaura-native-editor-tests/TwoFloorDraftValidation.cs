using System.Security.Cryptography;
using System.Text.Json;

internal static class TwoFloorDraftValidation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor",
            "examples", "proposals", "HA_TWO_FLOOR_ROUTE_DRAFT_009"));
        using var validationDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "validation.json")));
        var validation = validationDocument.RootElement;
        Require(validation.GetProperty("status").GetString() == "REWORK_TRANSIT_ROUTING", "draft status must remain REWORK");
        Require(validation.GetProperty("published_floor_1_body_contact_count").GetInt32() == 0, "floor-1 bodies contact");
        Require(validation.GetProperty("published_attic_body_contact_count").GetInt32() == 0, "attic bodies contact");
        Require(validation.GetProperty("published_hard_exclusion_hit_count").GetInt32() == 0, "published exclusion hit");
        Require(validation.GetProperty("rejected_full_route_attempt_floor_1_contact_count").GetInt32() > 0, "rejected F1 transits not recorded");
        Require(validation.GetProperty("rejected_full_route_attempt_attic_contact_count").GetInt32() > 0, "rejected attic transits not recorded");
        Require(validation.GetProperty("riser_vertical_length").GetString() == "NOT_EVALUATED", "riser length claim");
        Require(validation.GetProperty("attic_complete_40_80m").GetString() == "NOT_EVALUATED", "attic length claim");
        Require(validation.GetProperty("hydraulics").GetString() == "NOT_CALCULATED", "hydraulics claim");
        Require(!validation.GetProperty("normative_compliance_claimed").GetBoolean(), "normative claim");

        using var geometryDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "canonical_geometry_draft.json")));
        var routes = geometryDocument.RootElement.GetProperty("routes").EnumerateArray().ToArray();
        Require(routes.Length == 27, "route body count");
        Require(routes.Count(route => route.GetProperty("floor_id").GetString() == "FLOOR_1") == 14, "F1 body count");
        Require(routes.Count(route => route.GetProperty("floor_id").GetString() == "ATTIC") == 13, "attic body count");
        foreach (var route in routes)
        {
            var topology = route.GetProperty("body_topology_validation");
            Require(topology.GetProperty("result").GetString() == "PASS", $"{route.GetProperty("route_id").GetString()} topology");
            Require(topology.GetProperty("endpoint_count").GetInt32() == 2, "endpoint count");
            Require(topology.GetProperty("branch_count").GetInt32() == 0, "branch count");
            Require(topology.GetProperty("nonadjacent_contact_count").GetInt32() == 0, "self-contact count");
            Require(route.GetProperty("route_validation").ValueKind == JsonValueKind.Null, "full route validation must be unresolved");
            Require(route.GetProperty("total_length_mm").ValueKind == JsonValueKind.Null, "total length must be unresolved");
            Require(route.GetProperty("collector_transit_status").GetString() == "NOT_ROUTED_REWORK", "transit status");
            var points = route.GetProperty("ordered_points_grid").EnumerateArray()
                .Select(point => (X: point[0].GetInt32(), Y: point[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points) == 0, "independently calculated body self-contact");
        }
        var floorRoutes = routes.Where(route => route.GetProperty("floor_id").GetString() == "FLOOR_1").ToArray();
        var atticRoutes = routes.Where(route => route.GetProperty("floor_id").GetString() == "ATTIC").ToArray();
        Require(CountInterRouteContacts(floorRoutes) == 0, "independently calculated F1 contact");
        Require(CountInterRouteContacts(atticRoutes) == 0, "independently calculated attic contact");

        var vectorRoot = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor",
            "examples", "proposals", "HA_TWO_FLOOR_VECTOR_CONTRACT_011"));
        using var vectorDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(vectorRoot, "vector_source_contract.json")));
        var vector = vectorDocument.RootElement;
        Require(vector.GetProperty("source_documents").GetArrayLength() == 2, "vector PDF source count");
        Require(vector.GetProperty("gate_contract").GetProperty("r1_unique_gate_nodes_grid").GetArrayLength() == 26, "R1 gate count");
        Require(vector.GetProperty("gate_contract").GetProperty("floor_1_unique_entry_gates_grid").GetArrayLength() == 28, "F1 gate count");
        Require(!vector.GetProperty("gate_contract").GetProperty("shared_pipe_trunk").GetBoolean(), "shared pipe trunk");
        var exclusions = vector.GetProperty("vector_traced_geometry");
        Require(exclusions.GetProperty("floor_1_first_three_treads").GetProperty("conservative_blocked_box_grid")[0].GetInt32() == 113, "correct tread trace");
        Require(exclusions.GetProperty("attic_structural_stair_void").GetProperty("conservative_blocked_box_grid")[0].GetInt32() == 99, "correct attic void trace");

        ValidateLocalGroup012(vectorRoot);
    }

    private static void ValidateLocalGroup012(string vectorRoot)
    {
        var root = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor",
            "examples", "proposals", "HA_TWO_FLOOR_LOCAL_GROUP_012"));
        using var geometryDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "canonical_geometry.json")));
        using var validationDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "validation.json")));
        var geometry = geometryDocument.RootElement;
        var validation = validationDocument.RootElement;
        Require(geometry.GetProperty("status").GetString() == "THREE_LOCAL_K1_FULL_ROUTES_PASS", "D012 bounded status");
        Require(!geometry.GetProperty("whole_house_completion").GetBoolean(), "D012 must not claim whole-house completion");
        Require(validation.GetProperty("route_count").GetInt32() == 3, "D012 route count");
        Require(validation.GetProperty("unique_port_id_count").GetInt32() == 6, "D012 unique port IDs");
        Require(validation.GetProperty("unique_port_coordinate_count").GetInt32() == 6, "D012 unique port coordinates");
        Require(validation.GetProperty("all_ports_inside_k1_bbox").GetBoolean(), "D012 K1 port containment");
        Require(validation.GetProperty("self_contact_count").GetInt32() == 0, "D012 stored self contact");
        Require(validation.GetProperty("inter_route_contact_count").GetInt32() == 0, "D012 stored inter contact");
        Require(validation.GetProperty("first_three_tread_exclusion_hit_count").GetInt32() == 0, "D012 tread exclusion");
        Require(validation.GetProperty("all_complete_lengths_40_80m").GetBoolean(), "D012 length status");

        var routes = geometry.GetProperty("routes").EnumerateArray().ToArray();
        Require(routes.Length == 3, "D012 geometry route count");
        var portIds = new HashSet<string>();
        var portCoordinates = new HashSet<string>();
        foreach (var route in routes)
        {
            Require(route.GetProperty("completed").GetBoolean(), "D012 completed route");
            Require(route.GetProperty("collector_id").GetString() == "K1", "D012 collector ownership");
            Require(route.GetProperty("supply_collector_id").GetString() == "K1", "D012 supply collector");
            Require(route.GetProperty("return_collector_id").GetString() == "K1", "D012 return collector");
            Require(portIds.Add(route.GetProperty("supply_port_id").GetString()!), "duplicate supply port ID");
            Require(portIds.Add(route.GetProperty("return_port_id").GetString()!), "duplicate return port ID");
            var supply = route.GetProperty("supply_port_grid");
            var returned = route.GetProperty("return_port_grid");
            Require(portCoordinates.Add($"{supply[0]}:{supply[1]}"), "duplicate supply port coordinate");
            Require(portCoordinates.Add($"{returned[0]}:{returned[1]}"), "duplicate return port coordinate");
            var points = route.GetProperty("ordered_points_grid").EnumerateArray()
                .Select(point => (X: point[0].GetInt32(), Y: point[1].GetInt32())).ToArray();
            Require(points[0] == (supply[0].GetInt32(), supply[1].GetInt32()), "supply endpoint mismatch");
            Require(points[^1] == (returned[0].GetInt32(), returned[1].GetInt32()), "return endpoint mismatch");
            Require(CountSelfContacts(points) == 0, "D012 independently calculated self-contact");
            var measured = points.Zip(points.Skip(1)).Sum(pair => (Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured == route.GetProperty("calculated_length_mm").GetInt32(), "D012 measured length mismatch");
            Require(measured >= 40000 && measured <= 80000, "D012 measured length range");
            Require(measured == route.GetProperty("supply_transit_length_mm").GetInt32()
                + route.GetProperty("heating_body_length_mm").GetInt32()
                + route.GetProperty("return_transit_length_mm").GetInt32(), "D012 component length mismatch");
        }
        Require(CountInterRouteContacts(routes) == 0, "D012 independently calculated inter-route contact");
        Require(portIds.Count == 6, "D012 independently counted port IDs");
        Require(portCoordinates.Count == 6, "D012 independently counted port coordinates");

        ValidateCoverageBodies014();
        ValidateCounterflowFullRoutes015();
        ValidateFloor1WestGroup018();
        ValidateFloor1Unified019();
        ValidateFloor1TenRoutes023();
        ValidateFloor1Repartitioned024();
        ValidateFloor1RepartitionLineage025();
        ValidateFloor1ElevenRoutes026();
        ValidateFloor1TwelveRoutes027();
        ValidateFloor1TwelveRoutesSpacing028();
        ValidateFloor1NorthHall029();
        ValidateFloor1NorthHallEvidence031();
        ValidateFloor1HallVectorCoverage032();
        ValidateFloor1HallLPolygonCoverage033();
        ValidateFloor1NorthTransitBank034();
        ValidateFloor1ExteriorThreePass035();
        ValidateFloor1ExteriorFirstGrid036();
        ValidateFloor1WallClearance037();
        ValidateFloor1FieldLadder038();
        ValidateFloor1C06NorthStair039();
        ValidateFloor1C06Evidence040();
        ValidateAtticBodyBaseline041();
        ValidateAtticRightCounterflow042();
        ValidateAtticRectangularCounterflows043();
        ValidateAtticCounterflowEvidence044();
        ValidateAtticHallVectorContract045();
        ValidateAtticHallVectorContract046();
        ValidateAtticHallExactVectorContract047();
        ValidateAtticHallCounterflows048();
        ValidateAtticRightR1Fragments049();
        ValidateAtticHallRefined050();
        ValidateAtticR1Contract051();
        ValidateAtticR1ContractRepaired052();
        ValidateAtticR1CorridorAudit053();
        ValidateAtticR1SplitInterface054();
        ValidateAtticR1SouthCandidates055();
        ValidateAtticFloorCandidateNodes056();
        ValidateAtticFloorCandidateEvidence057();
        ValidateAtticPlanSpaceDiagnostic058();
        ValidateAtticPlanSpaceDomainAudit059();
        ValidateAtticPlanSpaceEvidence060();
        ValidateAtticPlanSpaceDomainRepaired061();
        ValidateAtticAdjacentFloorDomains062();
        ValidateAtticAdjacentFloorEvidence063();
        ValidateAtticPlanSpaceProximity064();
        ValidateAtticRiserPacking065();
        ValidateAtticWallTransitAudit066();
        ValidateAtticPartitionOpening067();
        ValidateAtticPartitionLaneCapacity068();
        ValidateAtticRiserPackingScope069();
        ValidateAtticWallStrips070();
        ValidateAtticPartitionOpeningEvidence071();
        ValidateAtticPhysicalInputGate072();
        ValidateAtticPartitionAmbiguity073();
        ValidateOwnerPhysicalInputs074();
        ValidateOwnerBendRadius075();
        ValidateOwnerBendRadiusEvidence076();
        ValidatePhysicalR1Location077();
        ValidateWallRegisteredR1Location078();
        ValidateInternalStairWardrobeR1Strategy079();
        ValidateInternalRiser3D080();
        ValidateAtticWardrobeManifold081();
        ValidateAtticManifoldServiceZone082();
        ValidateAtticPrimaryHydraulicEnvelope083();
        ValidateAtticHydraulicEvidence084();
        ValidateAtticC01ManifoldCorridor085();
        ValidateAtticRoutingBudgets086();
        ValidateAtticRoutingBudgetEvidence087();
        ValidateAtticK2PortLattice088();
        ValidateAtticK2StationAssignment089();
        ValidateInternalRiserK2StageGate090();
        ValidateAtticK2ProductSelection091();
        ValidateAtticK2ProductEvidence092();
        ValidateAtticK2SelectedPorts093();
        ValidateAtticK2SelectedPortBudgets094();
        ValidateAtticK2MountingDatum095();
        ValidateAtticPrimaryPipeSelection096();
        ValidateAtticPrimaryBendFittings097();
        ValidateTwoPrimaryInternalPenetration098();
        ValidateInternalRiserK2StageGate099();
        ValidateOwnerFloorBuildUp100();
        ValidatePrimaryWallServiceBox101();
        ValidateFloorBuildUpStageGate102();
        ValidateFloorLayerStack103();
        ValidatePrimaryInsulationChannel104();
        ValidatePrimaryChannel3D105();
        ValidatePrimaryChannel3DEvidence106();
        ValidatePrimaryChannelNoFastener107();
        ValidatePrimaryChannelThermal108();
        ValidateFloorPrimaryIntegration109();
        ValidateVerticalDatum110();
        ValidateVerticalDatumEvidence111();
        ValidateFloorPrimaryInstallationSheet112();
        ValidateFloorPrimaryResearch113();
        ValidateFloorPrimaryChannelRevision114();
        ValidateFloorPrimaryRevisionSheet115();
        ValidateFloorStackOptions116();
        ValidateFloorPrimaryLoadBridgeGate117();
        ValidateFloorPrimaryStackBridgeSheet119();
        ValidateFloorPrimaryLevellingConcept120();
        ValidateFloorPrimaryPreliminarySheet122();
        ValidateFloorPrimarySupportStripAudit123();
        ValidateFloorPrimaryVectorDomain124();
        ValidateFloorPrimaryAacCrossings125();
        ValidateFloorPrimaryCoordination126();
        ValidateFloorPrimaryVectorMetadataRepair127();
        ValidateFloorPrimaryCoordinationCleanEvidence130();
        ValidatePrimaryOpeningsOwnerReport131();
        ValidatePrimaryOpeningsPullGate132();
        ValidatePrimaryOpeningsPullGateEvidence133();
        ValidatePrimaryOpeningsAcceptanceCriteria134();
        ValidatePrimaryBendMethodEvidence135();
        ValidatePrimaryAcceptanceBendClarification136();
        ValidatePrimaryReleaseStateBinding137();
    }

    private static void ValidatePrimaryReleaseStateBinding137()
    {
        var proposals=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals"));
        var root=Path.Combine(proposals,"HA_TWO_FLOOR_PRIMARY_RELEASE_STATE_BINDING_137");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_release_state_binding.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="SELF_CONTAINED_RELEASE_STATE_BINDING_PASS_PHYSICAL_RELEASE_REMAINS_FALSE","D137 bounded status");
        var sourceD136=model.GetProperty("source_records").EnumerateArray().Single(s=>s.GetProperty("source_key").GetString()=="D136");
        var sourceD136Path=Path.Combine(proposals,"HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136","primary_acceptance_bend_clarification.json");
        var sourceD136Sha=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(sourceD136Path)));
        Require(sourceD136.GetProperty("file_sha256").GetString()==sourceD136Sha,"D137 D136 source file SHA");
        Require(model.GetProperty("D136_final_read_only_audits").GetArrayLength()==2&&model.GetProperty("D136_final_read_only_audits").EnumerateArray().All(a=>a.GetProperty("status").GetString()=="COMPLETED"&&a.GetProperty("exit_code").GetInt32()==0&&!a.GetProperty("timed_out").GetBoolean()),"D137 completed Claude and Kimi audits");
        var gates=model.GetProperty("authoritative_pull_release_gates").EnumerateArray().ToArray();
        var gateIds=new[]{"G01_AS_BUILT_OPENING_RECORDS","G02_STRUCTURAL_AND_WALL_DISPOSITION","G03_SLEEVE_EDGE_CLOSEOUT_SYSTEM","G04_CONTINUOUS_PIPE_AND_ACCESSIBLE_FITTINGS","G05_LABEL_CAP_AND_PULL_METHOD"};
        Require(gates.Length==5&&gates.Select(g=>g.GetProperty("gate_id").GetString()).SequenceEqual(gateIds),"D137 authoritative gate IDs");
        Require(gates.All(g=>g.GetProperty("inputs_required").EnumerateArray().All(i=>i.GetString()!.StartsWith("readiness_inputs."))&&!g.GetProperty("evaluated").GetBoolean()&&g.GetProperty("passes").ValueKind==JsonValueKind.Null),"D137 self-contained unresolved gates");
        var readiness=model.GetProperty("readiness_inputs");
        Require(readiness.GetProperty("openings").GetArrayLength()==3&&readiness.GetProperty("openings").EnumerateArray().All(o=>o.GetProperty("per_primary_records").GetArrayLength()==2&&o.GetProperty("per_primary_records").EnumerateArray().All(p=>!p.GetProperty("closeout_system_selected").GetBoolean()&&p.GetProperty("closeout_system_id").ValueKind==JsonValueKind.Null)),"D137 six unresolved closeout records");
        Require(readiness.GetProperty("p01").GetProperty("pitch_offset_axis").ValueKind==JsonValueKind.Null&&readiness.GetProperty("required_cover_above_envelope_mm").ValueKind==JsonValueKind.Null&&readiness.GetProperty("required_annulus_per_primary_mm").ValueKind==JsonValueKind.Null,"D137 unresolved geometry inputs");
        var bend=readiness.GetProperty("bend");
        Require(bend.GetProperty("bend_method").ValueKind==JsonValueKind.Null&&bend.GetProperty("bend_radius_definition").ValueKind==JsonValueKind.Null&&!bend.GetProperty("tool_and_segment_procured_and_field_verified").GetBoolean()&&!bend.GetProperty("factory_insulation_bend_method_verified").GetBoolean(),"D137 unresolved bend inputs");
        Require(!readiness.GetProperty("pressure_test_parameters_selected").GetBoolean(),"D137 pressure test unresolved");
        var state=model.GetProperty("state_machine");
        Require(state.GetProperty("current_state").GetString()=="S_PREPARATION"&&state.GetProperty("D134_state_machine_gate_ids_superseded").GetBoolean(),"D137 current state");
        Require(state.GetProperty("transitions")[0].GetProperty("required_gate_ids").EnumerateArray().Select(i=>i.GetString()).SequenceEqual(gateIds),"D137 release transition gate IDs");
        Require(model.GetProperty("stop_conditions").EnumerateArray().Any(i=>i.GetString()=="REMAINING_DEPTH_MINUS_ENVELOPE_BELOW_REQUIRED_COVER")&&model.GetProperty("stop_conditions").EnumerateArray().Any(i=>i.GetString()=="CLOSEOUT_SYSTEM_NOT_SELECTED"),"D137 stop conditions");
        Require(!model.GetProperty("all_pull_release_gates_pass").GetBoolean()&&!model.GetProperty("pipe_bending_authorized").GetBoolean()&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("penetration_closeout_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D137 release remains false");
        Require(model.GetProperty("new_route_coordinate_count").GetInt32()==0&&model.GetProperty("approved_bend_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0,"D137 no geometry");
        using var manifestDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"artifact_manifest.json")));
        foreach(var item in manifestDocument.RootElement.GetProperty("files").EnumerateArray())
        {
            var path=Path.Combine(root,item.GetProperty("name").GetString()!);
            Require(new FileInfo(path).Length==item.GetProperty("bytes").GetInt64(),"D137 manifest file size");
            Require(Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)))==item.GetProperty("sha256").GetString(),"D137 manifest file SHA");
        }
    }

    private static void ValidatePrimaryAcceptanceBendClarification136()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_ACCEPTANCE_BEND_CLARIFICATION_136"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_acceptance_bend_clarification.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="EVIDENCE_SCOPE_AND_HASH_SEMANTICS_CLARIFIED_PHYSICAL_RELEASE_REMAINS_FALSE","D136 bounded status");
        Require(model.GetProperty("independent_final_read_only_audits").GetArrayLength()==2&&model.GetProperty("independent_final_read_only_audits").EnumerateArray().All(a=>a.GetProperty("status").GetString()=="COMPLETED"),"D136 completed Claude and Kimi audits");
        var hashes=model.GetProperty("hash_semantics_clarification");
        Require(hashes.GetProperty("D135_source_records_sha256_semantics").GetString()=="SOURCE_FILE_BYTES_SHA256"&&hashes.GetProperty("D134_acceptance_criteria_digest_semantics").GetString()=="CANONICAL_JSON_BEFORE_DIGEST_FIELD_INSERTION","D136 hash domains");
        Require(hashes.GetProperty("D135_recorded_D134_source_file_sha256").GetString()==hashes.GetProperty("independently_recomputed_D134_file_sha256").GetString()&&!hashes.GetProperty("hash_domain_mismatch_exists").GetBoolean()&&hashes.GetProperty("values_are_expected_to_differ").GetBoolean(),"D136 source hash clarification");
        var lineage=model.GetProperty("gate_lineage_and_supersession");
        Require(lineage.GetProperty("D132_is_gate_definition_source").GetBoolean()&&lineage.GetProperty("D133_contains_gate_count_but_not_gate_definitions").GetBoolean()&&lineage.GetProperty("superseded_gate_map").GetArrayLength()==5,"D136 gate provenance");
        var gates=model.GetProperty("authoritative_pull_release_gates").EnumerateArray().ToArray();
        Require(gates.Length==5&&gates.All(g=>!g.GetProperty("evaluated").GetBoolean()&&g.GetProperty("passes").ValueKind==JsonValueKind.Null)&&!model.GetProperty("all_pull_release_gates_pass").GetBoolean(),"D136 gates remain unreleased");
        var g03=gates.Single(g=>g.GetProperty("gate_id").GetString()=="G03_SLEEVE_EDGE_CLOSEOUT_SYSTEM");
        var g04=gates.Single(g=>g.GetProperty("gate_id").GetString()=="G04_CONTINUOUS_PIPE_AND_ACCESSIBLE_FITTINGS");
        Require(g03.GetProperty("inputs_required").EnumerateArray().Any(i=>i.GetString()!.Contains("closeout_system_selected")),"D136 closeout requirement");
        Require(g04.GetProperty("inputs_required").EnumerateArray().Any(i=>i.GetString()!.Contains("bend_radius_definition"))&&g04.GetProperty("inputs_required").EnumerateArray().Any(i=>i.GetString()!.Contains("required_cover_above_envelope_mm")),"D136 radius and cover requirements");
        Require(model.GetProperty("stop_conditions_added").GetArrayLength()==3,"D136 added stop conditions");
        var release=model.GetProperty("release_semantics_clarification");
        Require(release.GetProperty("D134_pass_scope").GetString()=="ACCEPTANCE_CRITERIA_DEFINITION_ONLY"&&release.GetProperty("D135_pass_scope").GetString()=="OFFICIAL_R80_TOOL_METHOD_EVIDENCE_ONLY"&&release.GetProperty("physical_release_status").GetString()=="NOT_RELEASED","D136 pass scope");
        Require(!release.GetProperty("pipe_bending_authorized").GetBoolean()&&!release.GetProperty("pipe_pull_authorized").GetBoolean()&&!release.GetProperty("penetration_closeout_authorized").GetBoolean()&&!release.GetProperty("construction_authorized").GetBoolean(),"D136 physical release remains false");
        var floors=model.GetProperty("per_floor_owner_statement_depth_screening").EnumerateArray().ToArray();
        Require(floors.Length==2&&floors.All(f=>Math.Abs(f.GetProperty("remaining_minus_coordination_envelope_mm").GetDouble())<1e-9&&Math.Abs(f.GetProperty("remaining_minus_comparison_insulated_od_mm").GetDouble()-8)<1e-9&&!f.GetProperty("adequacy_claimed").GetBoolean()),"D136 per-floor depth scope");
        var p01=model.GetProperty("P01_orientation_screening_preserved");
        Require(Math.Abs(p01.GetProperty("margin_along_120mm_side_mm").GetDouble()+50)<1e-9&&Math.Abs(p01.GetProperty("margin_along_200mm_side_mm").GetDouble()-30)<1e-9&&!p01.GetProperty("as_built_orientation_and_clear_size_verified").GetBoolean(),"D136 P01 screening preserved");
        Require(model.GetProperty("new_route_coordinate_count").GetInt32()==0&&model.GetProperty("approved_bend_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0,"D136 no geometry or approval");
    }

    private static void ValidatePrimaryBendMethodEvidence135()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_BEND_METHOD_EVIDENCE_135"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_bend_method_evidence.json")));
        var model=document.RootElement;
        var radii=model.GetProperty("official_minimum_bending_radii_mm");
        Require(radii.GetProperty("without_tool_by_hand").GetInt32()==160&&radii.GetProperty("internal_bending_spring").GetInt32()==96&&radii.GetProperty("uponor_bending_tool").GetInt32()==80&&radii.GetProperty("external_bending_spring").ValueKind==JsonValueKind.Null,"D135 official 32x3 radii");
        Require(model.GetProperty("owner_directed_radius_mm").GetInt32()==80&&model.GetProperty("owner_directed_radius_matches_official_tool_table").GetBoolean()&&model.GetProperty("r80_is_not_released_for_hand_bending").GetBoolean()&&model.GetProperty("r80_is_not_released_for_hot_bending").GetBoolean(),"D135 bounded R80 method");
        Require(model.GetProperty("selected_tool_part_number_candidate").GetString()=="1071925"&&model.GetProperty("selected_segment_part_number_candidate").GetString()=="1120411"&&!model.GetProperty("tool_and_segment_procured_and_field_verified").GetBoolean(),"D135 official tool candidates not procurement claim");
        Require(!model.GetProperty("factory_insulation_can_remain_installed_during_tool_bending_verified").GetBoolean()&&!model.GetProperty("D134_gate_G04_can_pass").GetBoolean(),"D135 insulation and gate remain unresolved");
        Require(model.GetProperty("field_acceptance_inputs").EnumerateArray().All(i=>i.GetProperty("value").ValueKind==JsonValueKind.Null&&!i.GetProperty("verified").GetBoolean()),"D135 field inputs empty");
        Require(model.GetProperty("new_route_coordinate_count").GetInt32()==0&&model.GetProperty("approved_bend_geometry_count").GetInt32()==0&&!model.GetProperty("pipe_bending_authorized").GetBoolean()&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D135 honest release scope");
    }

    private static void ValidatePrimaryOpeningsAcceptanceCriteria134()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_OPENINGS_ACCEPTANCE_CRITERIA_134"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_openings_acceptance_criteria.json")));
        var model=document.RootElement;
        Require(model.GetProperty("independent_read_only_reviews").GetArrayLength()==2,"D134 Claude and Kimi reviews");
        var owner=model.GetProperty("owner_stated_inputs");
        Require(owner.GetProperty("vertical_rise_mm").GetInt32()==3000&&owner.GetProperty("coordination_minimum_bend_radius_mm").GetInt32()==80&&owner.GetProperty("bend_radius_definition").ValueKind==JsonValueKind.Null,"D134 owner inputs remain bounded");
        var floors=owner.GetProperty("floor_buildups").EnumerateArray().ToArray();
        Require(floors.Length==2&&floors[0].GetProperty("total_from_owner_statement_mm").GetInt32()==170&&floors[1].GetProperty("total_from_owner_statement_mm").GetInt32()==120&&owner.GetProperty("buildup_total_difference_mm").GetInt32()==50,"D134 floor buildup arithmetic");
        var derived=model.GetProperty("derived_envelope_screening");
        Require(Math.Abs(derived.GetProperty("pair_outer_to_outer_envelope_mm").GetDouble()-170)<1e-9&&Math.Abs(derived.GetProperty("pair_outer_to_outer_comparison_mm").GetDouble()-162)<1e-9&&!derived.GetProperty("adequacy_claimed").GetBoolean(),"D134 envelope screening");
        var p01=model.GetProperty("p01_orientation_screening");
        Require(Math.Abs(p01.GetProperty("pair_envelope_if_offset_along_120mm_margin_mm").GetDouble()+50)<1e-9&&Math.Abs(p01.GetProperty("pair_envelope_if_offset_along_200mm_margin_mm").GetDouble()-30)<1e-9&&!p01.GetProperty("orientation_resolved").GetBoolean(),"D134 P01 orientation screen");
        var openings=model.GetProperty("openings").EnumerateArray().ToArray();
        Require(openings.Length==3&&openings.All(o=>o.GetProperty("per_primary_records").GetArrayLength()==2&&o.GetProperty("face_records").GetArrayLength()==2&&!o.GetProperty("independently_verified").GetBoolean()),"D134 per-primary and per-face records");
        var gates=model.GetProperty("pull_release_gates").EnumerateArray().ToArray();
        Require(gates.Length==5&&gates.All(g=>!g.GetProperty("evaluated").GetBoolean()&&g.GetProperty("passes").ValueKind==JsonValueKind.Null)&&model.GetProperty("evaluated_gate_count").GetInt32()==0&&!model.GetProperty("all_pull_release_gates_pass").GetBoolean(),"D134 gates remain unreleased");
        Require(model.GetProperty("state_machine").GetProperty("current_state").GetString()=="S_PREPARATION"&&model.GetProperty("new_route_coordinate_count").GetInt32()==0,"D134 preparation-only state");
        Require(!model.GetProperty("pressure_test_parameters_selected").GetBoolean()&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("penetration_closeout_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D134 honest authorization scope");
    }

    private static void ValidatePrimaryOpeningsPullGateEvidence133()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_EVIDENCE_133"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_openings_asbuilt_pull_gate_evidence.json")));
        var model=document.RootElement;
        Require(!model.GetProperty("source_geometry_or_requirements_changed").GetBoolean()&&model.GetProperty("visual_repairs").GetArrayLength()==3,"D133 evidence-only repair");
        Require(model.GetProperty("page_count").GetInt32()==2&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE"&&model.GetProperty("opening_count").GetInt32()==3&&model.GetProperty("owner_reported_drilled_count").GetInt32()==3,"D133 field sheet contract");
        Require(model.GetProperty("independently_verified_opening_count").GetInt32()==0&&model.GetProperty("pull_release_gate_count").GetInt32()==5&&!model.GetProperty("all_pull_release_gates_pass").GetBoolean()&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("penetration_closeout_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D133 honest release scope");
        var pdf=Path.Combine(root,"HomeAura_primary_openings_asbuilt_and_pull_gate_D133.pdf");
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>50000,"D133 PDF");
    }

    private static void ValidatePrimaryOpeningsPullGate132()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_OPENINGS_ASBUILT_PULL_GATE_132"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_openings_asbuilt_pull_gate.json")));
        var model=document.RootElement;var review=model.GetProperty("independent_cloud_review");var basis=model.GetProperty("primary_design_basis");
        Require(model.GetProperty("opening_count").GetInt32()==3&&model.GetProperty("owner_reported_drilled_count").GetInt32()==3&&model.GetProperty("independently_verified_opening_count").GetInt32()==0,"D132 opening status");
        Require(review.GetProperty("agent").GetString()=="claude"&&review.GetProperty("status").GetString()=="COMPLETED"&&review.GetProperty("material_findings_incorporated").GetArrayLength()==7&&!review.GetProperty("obsolete_D123_unknown_floor_scope_incorporated").GetBoolean(),"D132 independent review provenance");
        Require(basis.GetProperty("count").GetInt32()==2&&basis.GetProperty("factory_insulated_comparison_od_mm").GetInt32()==62&&basis.GetProperty("continuous_no_hidden_joints").GetBoolean()&&basis.GetProperty("supply_return_axis_pitch_mm").GetInt32()==100,"D132 primary design basis");
        Require(model.GetProperty("pull_release_gates").GetArrayLength()==5&&!model.GetProperty("all_pull_release_gates_pass").GetBoolean()&&model.GetProperty("installation_sequence_count").GetInt32()==8&&model.GetProperty("stop_work_trigger_count").GetInt32()==8,"D132 gates and sequence");
        Require(!model.GetProperty("pressure_test_parameters_selected").GetBoolean()&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("penetration_closeout_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D132 honest release scope");
    }

    private static void ValidatePrimaryOpeningsOwnerReport131()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_OPENINGS_OWNER_REPORT_131"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_openings_owner_report.json")));
        var model=document.RootElement;var openings=model.GetProperty("openings").EnumerateArray().ToArray();
        Require(model.GetProperty("owner_statement_verbatim").GetString()=="отверстия сделаны"&&model.GetProperty("owner_report_is_not_instrumental_verification").GetBoolean()&&openings.Length==3,"D131 owner report scope");
        Require(openings.All(o=>o.GetProperty("owner_reported_drilled").GetBoolean()&&!o.GetProperty("independently_verified").GetBoolean()&&o.GetProperty("photo_evidence_paths").GetArrayLength()==0),"D131 three unverified drilled openings");
        Require(openings[0].GetProperty("as_built_clear_width_mm").ValueKind==JsonValueKind.Null&&openings[1].GetProperty("as_built_clear_height_mm").ValueKind==JsonValueKind.Null&&openings[2].GetProperty("as_built_building_bbox_mm").ValueKind==JsonValueKind.Null,"D131 unknown as-built values");
        Require(model.GetProperty("released_claims").GetArrayLength()==1&&model.GetProperty("not_released_claims").GetArrayLength()==7&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&!model.GetProperty("pipe_pull_authorized").GetBoolean()&&!model.GetProperty("construction_closeout_authorized").GetBoolean(),"D131 honest release scope");
    }

    private static void ValidateFloorPrimaryCoordinationCleanEvidence130()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_CLEAN_EVIDENCE_130"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_coordination_clean_evidence.json")));
        var model=document.RootElement;
        Require(model.GetProperty("page_count").GetInt32()==2&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE"&&model.GetProperty("historical_overflow_fully_masked").GetBoolean(),"D130 page and visual repair contract");
        Require(Math.Abs(model.GetProperty("authoritative_floor_axis_length_mm").GetDouble()-3930.7657623286996)<1e-6&&Math.Abs(model.GetProperty("authoritative_aac_wall_axis_length_mm").GetDouble()-639.2342376713004)<1e-6&&model.GetProperty("unknown_axis_length_mm").GetDouble()==0,"D130 route partition");
        Require(model.GetProperty("aac_wall_opening_count").GetInt32()==2&&model.GetProperty("separate_slab_penetration_node_count").GetInt32()==1,"D130 physical node separation");
        Require(model.GetProperty("approved_wall_opening_count").GetInt32()==0&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&model.GetProperty("selected_floor_stack_option_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D130 honest release scope");
        var pdf=Path.Combine(root,"HomeAura_floor_primary_coordination_D130.pdf");
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>50000,"D130 PDF");
    }

    private static void ValidateFloorPrimaryVectorMetadataRepair127()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_METADATA_REPAIR_127"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_vector_domain_metadata_repair.json")));
        var model=document.RootElement;var totals=model.GetProperty("authoritative_totals");
        Require(!model.GetProperty("geometry_changed").GetBoolean()&&model.GetProperty("source_route_axis_building_mm").GetArrayLength()==3,"D127 geometry preservation");
        Require(Math.Abs(totals.GetProperty("vector_draft_floor_axis_length_mm").GetDouble()-3930.7657623286996)<1e-6&&Math.Abs(totals.GetProperty("aac_wall_axis_length_mm").GetDouble()-639.2342376713004)<1e-6&&Math.Abs(totals.GetProperty("vector_draft_floor_axis_length_mm").GetDouble()+totals.GetProperty("aac_wall_axis_length_mm").GetDouble()-totals.GetProperty("axis_length_reconciliation_mm").GetDouble())<1e-6,"D127 corrected metadata");
        Require(model.GetProperty("corrected_result").GetString()!.Contains("3930_766MM")&&model.GetProperty("corrected_result").GetString()!.Contains("639_234MM")&&!model.GetProperty("construction_authorized").GetBoolean(),"D127 repair status");
    }

    private static void ValidateFloorPrimaryCoordination126()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_COORDINATION_SHEET_126"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_coordination_sheet.json")));
        var model=document.RootElement;
        Require(model.GetProperty("page_count").GetInt32()==2&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE"&&model.GetProperty("route_axis_length_mm").GetDouble()==4570,"D126 sheet contract");
        Require(Math.Abs(model.GetProperty("vector_draft_floor_axis_length_mm").GetDouble()+model.GetProperty("aac_wall_axis_length_mm").GetDouble()-4570)<1e-6&&model.GetProperty("aac_wall_crossing_count").GetInt32()==2,"D126 route partition");
        Require(model.GetProperty("separate_slab_penetration_coordination_size_mm")[0].GetDouble()==120&&model.GetProperty("separate_slab_penetration_coordination_size_mm")[1].GetDouble()==200,"D126 slab node");
        Require(model.GetProperty("approved_aac_wall_opening_count").GetInt32()==0&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&model.GetProperty("selected_floor_stack_option_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D126 release scope");
    }

    private static void ValidateFloorPrimaryAacCrossings125()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_AAC_CROSSINGS_125"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_aac_crossings.json")));
        var model=document.RootElement;var crossings=model.GetProperty("crossings").EnumerateArray().ToArray();var detail=model.GetProperty("common_detail_requirements");
        Require(crossings.Length==2&&crossings.All(c=>c.GetProperty("wall_material").GetString()=="AAC_GAS_CONCRETE"&&c.GetProperty("orientation").GetString()!.StartsWith("TRANSVERSE")&&!c.GetProperty("opening_or_sleeve_size_selected").GetBoolean()),"D125 separate AAC crossings");
        Require(model.GetProperty("primary_pipe").GetProperty("comparison_insulated_od_mm").GetInt32()==62&&model.GetProperty("primary_pipe").GetProperty("hidden_press_fitting_count").GetInt32()==0,"D125 primary pipe scope");
        Require(detail.GetProperty("one_protective_sleeve_or_tested_common_system_per_primary").GetBoolean()&&!detail.GetProperty("pipe_or_factory_jacket_may_touch_raw_AAC_edge").GetBoolean()&&!detail.GetProperty("pipe_may_be_bent_over_wall_edge").GetBoolean()&&detail.GetProperty("wall_chase_is_not_used").GetBoolean(),"D125 wall method");
        Require(model.GetProperty("separate_slab_penetration_node").GetProperty("not_same_as_W01_or_W02").GetBoolean()&&model.GetProperty("approved_wall_opening_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D125 release scope");
    }

    private static void ValidateFloorPrimaryVectorDomain124()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_VECTOR_DOMAIN_REPAIR_124"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_vector_domain_repair.json")));
        var model=document.RootElement;var totals=model.GetProperty("audit_totals");
        Require(model.GetProperty("source_faces").EnumerateObject().Count()==4&&model.GetProperty("horizontal_axis_partition").GetArrayLength()==5&&model.GetProperty("vertical_axis_partition").GetArrayLength()==1,"D124 vector partitions");
        Require(Math.Abs(totals.GetProperty("vector_draft_floor_axis_length_mm").GetDouble()-3930.7657623286996)<1e-6&&Math.Abs(totals.GetProperty("aac_wall_axis_length_mm").GetDouble()-639.2342376713004)<1e-6&&totals.GetProperty("unknown_axis_length_mm").GetDouble()==0&&Math.Abs(totals.GetProperty("vector_draft_floor_axis_length_mm").GetDouble()+totals.GetProperty("aac_wall_axis_length_mm").GetDouble()-totals.GetProperty("axis_length_reconciliation_mm").GetDouble())<1e-6,"D124 exact route balance");
        Require(totals.GetProperty("floor_axis_support_strip_geometry_pass").GetBoolean()&&!totals.GetProperty("whole_route_construction_pass").GetBoolean()&&!model.GetProperty("west_room_draft_floor_evidence").GetProperty("floor_strength_or_insulation_grade_proven").GetBoolean(),"D124 support scope");
    }

    private static void ValidateFloorPrimarySupportStripAudit123()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_SUPPORT_STRIP_AUDIT_123"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"support_strip_audit.json")));
        var model=document.RootElement;var totals=model.GetProperty("audit_totals");
        Require(model.GetProperty("source_records").GetArrayLength()==3&&model.GetProperty("route_axis_length_mm").GetDouble()==4570&&model.GetProperty("pipe_route_width_mm").GetInt32()==200&&model.GetProperty("required_support_width_next_to_route_mm").GetInt32()==200,"D123 source and geometry");
        Require(model.GetProperty("horizontal_axis_partition").GetArrayLength()==5&&model.GetProperty("vertical_axis_partition").GetArrayLength()==1,"D123 route partition");
        Require(Math.Abs(totals.GetProperty("known_vector_draft_floor_axis_length_mm").GetDouble()-3257.9)<1e-6&&totals.GetProperty("wall_band_axis_length_mm").GetDouble()==318&&Math.Abs(totals.GetProperty("unknown_or_unresolved_floor_axis_length_mm").GetDouble()-994.1)<1e-6&&totals.GetProperty("axis_length_reconciliation_mm").GetDouble()==4570&&!totals.GetProperty("whole_route_support_strip_pass").GetBoolean(),"D123 reconciled support scope");
        Require(!model.GetProperty("important_limits").GetProperty("door_thresholds_and_wall_openings_resolved").GetBoolean()&&!model.GetProperty("important_limits").GetProperty("support_strip_strength_or_insulation_grade_proven").GetBoolean()&&model.GetProperty("next_safe_inputs").GetArrayLength()==5,"D123 honest limits");
        Require(model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"support_strip_audit_evidence.png")),"D123 release scope");
    }

    private static void ValidateFloorPrimaryPreliminarySheet122()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_PRELIMINARY_SHEET_122"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"preliminary_sheet.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_records").GetArrayLength()==2&&model.GetProperty("supersedes_D119_mandatory_load_bridge_as_primary_method").GetBoolean()&&model.GetProperty("page_count").GetInt32()==1&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE","D122 document contract");
        Require(model.GetProperty("selected_concept_family").GetString()!.Contains("LEVELLING_LAYER")&&model.GetProperty("load_bridge_status").GetString()=="FALLBACK_NOT_SELECTED"&&model.GetProperty("floor_stack_option_count").GetInt32()==2&&model.GetProperty("selected_floor_stack_option_count").GetInt32()==0,"D122 selected method and stack scope");
        Require(model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D122 release scope");
        var pdf=Path.Combine(root,model.GetProperty("pdf_file").GetString()!);
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>50000,"D122 PDF");
    }

    private static void ValidateFloorPrimaryLevellingConcept120()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_LEVELLING_CONCEPT_120"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_levelling_concept.json")));
        var model=document.RootElement;var geometry=model.GetProperty("fixed_geometry");var detail=model.GetProperty("preferred_detail_requirements");var fasteners=model.GetProperty("fastener_schedule_screen");
        Require(model.GetProperty("source_records").GetArrayLength()==2&&model.GetProperty("official_source").GetProperty("requirements_used").GetArrayLength()==10&&model.GetProperty("supersession").GetProperty("D114_D115_D117_D119_mandatory_load_bridge_wording").GetString()!.Contains("SUPERSEDED"),"D120 source and supersession");
        Require(model.GetProperty("selected_concept_family").GetString()!.Contains("LEVELLING_LAYER")&&geometry.GetProperty("route_width_mm").GetInt32()==200&&geometry.GetProperty("manufacturer_max_route_width_mm").GetInt32()==300&&geometry.GetProperty("route_width_within_manufacturer_limit").GetBoolean()&&geometry.GetProperty("required_support_strip_next_to_route_each_applicable_side_mm").GetInt32()==200&&!geometry.GetProperty("support_strip_continuity_on_plan_verified").GetBoolean(),"D120 route limits");
        Require(geometry.GetProperty("actual_comparison_od_mm").GetInt32()==62&&geometry.GetProperty("clear_gap_between_actual_insulated_pipes_mm").GetInt32()==38&&geometry.GetProperty("actual_side_margin_each_side_mm").GetInt32()==19,"D120 pipe cross section");
        Require(detail.GetProperty("pipe_fixing_base").GetString()=="RAW_STRUCTURAL_CONCRETE_SLAB"&&detail.GetProperty("recommended_max_fixing_spacing_straight_mm").GetInt32()==800&&detail.GetProperty("maximum_fastener_distance_before_and_after_each_bend_mm").GetInt32()==300&&detail.GetProperty("pipe_thermal_movement_must_remain_free").GetBoolean()&&!detail.GetProperty("factory_insulation_may_be_crushed_or_point_loaded").GetBoolean()&&!detail.GetProperty("screed_or_floor_load_may_bear_directly_on_pipe").GetBoolean(),"D120 support contract");
        Require(fasteners.GetProperty("minimum_interval_count_if_only_length_division").GetInt32()==6&&fasteners.GetProperty("minimum_point_count_if_endpoints_are_both_fixed").GetInt32()==7&&fasteners.GetProperty("exact_count_and_positions").ValueKind==JsonValueKind.Null,"D120 preliminary fastener count");
        Require(model.GetProperty("fallback_detail").GetProperty("selected").GetBoolean()==false&&model.GetProperty("approved_levelling_product_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"floor_primary_levelling_concept_evidence.png")),"D120 release scope");
    }

    private static void ValidateFloorPrimaryStackBridgeSheet119()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_STACK_BRIDGE_SHEET_119"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"stack_bridge_sheet.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_records").GetArrayLength()==2&&model.GetProperty("page_count").GetInt32()==1&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE","D119 document contract");
        Require(model.GetProperty("floor_stack_option_count").GetInt32()==2&&model.GetProperty("selected_floor_stack_option_count").GetInt32()==0&&model.GetProperty("actual_pipe_headroom_to_insulation_top_mm").GetInt32()==34&&model.GetProperty("maximum_bridge_thickness_with_30mm_actual_infill_mm").GetInt32()==4,"D119 dimensional content");
        Require(model.GetProperty("selected_load_bridge_detail_count").GetInt32()==0&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D119 release scope");
        var pdf=Path.Combine(root,model.GetProperty("pdf_file").GetString()!);
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>50000,"D119 PDF");
    }

    private static void ValidateFloorPrimaryLoadBridgeGate117()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_LOAD_BRIDGE_GATE_117"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"load_bridge_stage_gate.json")));
        var model=document.RootElement;var geometry=model.GetProperty("fixed_geometry");var budget=model.GetProperty("vertical_budget");var load=model.GetProperty("load_path_contract");
        Require(model.GetProperty("source_records").GetArrayLength()==3&&model.GetProperty("supersession").GetProperty("D114_nominal_30mm_thermal_infill_plus_unspecified_bridge").GetString()!.Contains("SUPERSEDED"),"D117 source and supersession");
        Require(geometry.GetProperty("installed_floor1_insulation_depth_mm").GetInt32()==100&&geometry.GetProperty("primary_clear_pipe_channel_width_mm").GetInt32()==200&&geometry.GetProperty("factory_insulated_pipe_actual_comparison_od_mm").GetInt32()==62&&geometry.GetProperty("nominal_pipe_axis_z_from_slab_mm").GetInt32()==35,"D117 fixed geometry");
        Require(geometry.GetProperty("actual_pipe_bottom_z_mm").GetDouble()==4&&geometry.GetProperty("actual_pipe_top_z_mm").GetDouble()==66&&geometry.GetProperty("insulation_top_z_from_slab_mm").GetInt32()==100,"D117 actual section");
        Require(budget.GetProperty("actual_headroom_pipe_top_to_insulation_top_mm").GetDouble()==34&&budget.GetProperty("maximum_support_build_under_actual_pipe_retaining_30mm_infill_mm").GetDouble()==8&&budget.GetProperty("maximum_bridge_thickness_if_axis35_and_30mm_actual_infill_are_both_preserved_mm").GetDouble()==4&&!budget.GetProperty("thirty_mm_infill_and_nonzero_bridge_both_fit_above_70mm_envelope").GetBoolean(),"D117 dimensional conflict");
        Require(load.GetProperty("clear_span_mm").GetInt32()==200&&load.GetProperty("overall_bridge_width_mm").ValueKind==JsonValueKind.Null&&load.GetProperty("bearing_width_each_side_mm").ValueKind==JsonValueKind.Null&&load.GetProperty("bearings_must_be_outside_clear_pipe_channel").GetBoolean()&&!load.GetProperty("screed_or_finish_may_span_unsupported_200mm_channel").GetBoolean()&&!load.GetProperty("thermal_infill_is_load_bearing").GetBoolean(),"D117 load path contract");
        Require(model.GetProperty("candidate_system_families").GetArrayLength()==3&&model.GetProperty("rejected_unengineered_details").GetArrayLength()==6&&model.GetProperty("required_engineering_checks").GetArrayLength()==10,"D117 alternatives and checks");
        Require(model.GetProperty("approved_load_bridge_detail_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"load_bridge_stage_gate_evidence.png")),"D117 release scope");
    }

    private static void ValidateFloorStackOptions116()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_STACK_OPTIONS_116"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_stack_options.json")));
        var model=document.RootElement;var options=model.GetProperty("floor_stack_options").EnumerateArray().ToArray();
        Require(model.GetProperty("source_records").GetArrayLength()==3&&model.GetProperty("supersession").GetProperty("D103_combined_WET_FLOW_OR_CALCIUM_SULPHATE_35MM_wording").GetString()!.Contains("SUPERSEDED"),"D116 source and supersession");
        Require(model.GetProperty("owner_height_contract").GetProperty("available_above_installed_insulation_mm").GetInt32()==70&&model.GetProperty("owner_height_contract").GetProperty("loop_pipe_outer_diameter_mm").GetInt32()==16,"D116 owner height contract");
        Require(options.Length==2&&options[0].GetProperty("cover_above_pipe_mm").GetInt32()==35&&options[0].GetProperty("screed_total_from_insulation_top_mm").GetInt32()==51&&options[0].GetProperty("finish_adhesive_underlay_allowance_mm").GetInt32()==19&&!options[0].GetProperty("selected").GetBoolean(),"D116 calcium sulphate branch");
        Require(options[1].GetProperty("cover_above_pipe_mm").GetInt32()==45&&options[1].GetProperty("screed_total_from_insulation_top_mm").GetInt32()==61&&options[1].GetProperty("finish_adhesive_underlay_allowance_mm").GetInt32()==9&&!options[1].GetProperty("selected").GetBoolean(),"D116 cement branch");
        Require(model.GetProperty("selected_option_id").ValueKind==JsonValueKind.Null&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"floor_stack_options_evidence.png")),"D116 release scope");
    }

    private static void ValidateFloorPrimaryRevisionSheet115()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_REVISION_SHEET_115"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"revision_sheet.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_artifact_id").GetString()=="HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114"&&model.GetProperty("page_count").GetInt32()==1&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE","D115 document contract");
        Require(model.GetProperty("D112_page_2_load_detail_superseded").GetBoolean()&&model.GetProperty("load_bearing_bridge_required").GetBoolean()&&model.GetProperty("primary_support_base").GetString()=="STRUCTURAL_SLAB"&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D115 correction scope");
        var pdf=Path.Combine(root,model.GetProperty("pdf_file").GetString()!);
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>100000,"D115 PDF");
    }

    private static void ValidateFloorPrimaryChannelRevision114()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_CHANNEL_REVISION_114"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_channel_revision.json")));
        var model=document.RootElement;var channel=model.GetProperty("horizontal_floor_channel");var load=model.GetProperty("required_load_path");var support=model.GetProperty("primary_support_contract");var penetration=model.GetProperty("slab_penetration");var bend=model.GetProperty("bend_and_joint_policy");
        Require(model.GetProperty("source_records").GetArrayLength()==4&&model.GetProperty("supersession").GetProperty("D109_route_axis_and_noncontact_geometry_preserved").GetBoolean()&&model.GetProperty("supersession").GetProperty("D109_thirty_mm_insulation_as_possible_load_closure_rejected").GetBoolean(),"D114 source and supersession");
        Require(channel.GetProperty("channel_width_mm").GetInt32()==200&&channel.GetProperty("installed_insulation_depth_mm").GetInt32()==100&&channel.GetProperty("service_zone_from_slab_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{0,70})&&channel.GetProperty("actual_comparison_insulated_pipe_od_mm").GetInt32()==62&&!channel.GetProperty("thermal_infill_is_load_bearing_member").GetBoolean(),"D114 channel geometry");
        Require(channel.GetProperty("actual_pipe_surface_z_range_at_coordination_axis_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{4,66})&&channel.GetProperty("actual_thermal_infill_nominal_above_pipe_mm").GetInt32()==34&&channel.GetProperty("hidden_fitting_count").GetInt32()==0,"D114 actual pipe section");
        Require(load.GetProperty("selected_concept").GetString()!.Contains("LOAD_BRIDGE")&&!load.GetProperty("screed_and_finish_load_may_bear_on_pipe_or_thermal_infill").GetBoolean()&&load.GetProperty("bridge_material").ValueKind==JsonValueKind.Null&&!load.GetProperty("structural_calculation_complete").GetBoolean()&&!load.GetProperty("construction_release").GetBoolean(),"D114 load path scope");
        Require(support.GetProperty("support_base").GetString()=="STRUCTURAL_SLAB"&&!support.GetProperty("support_may_attach_to_insulation").GetBoolean()&&support.GetProperty("support_type").ValueKind==JsonValueKind.Null&&!support.GetProperty("physical_fit_with_selected_support_system_proven").GetBoolean(),"D114 support scope");
        Require(penetration.GetProperty("coordination_bbox_size_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{120,200})&&!penetration.GetProperty("coordination_bbox_is_final_core_or_sleeve_size").GetBoolean()&&!penetration.GetProperty("pipe_bending_over_concrete_or_wall_edge_allowed").GetBoolean()&&penetration.GetProperty("approved_opening_count").GetInt32()==0,"D114 penetration scope");
        Require(bend.GetProperty("loop_pipe_16x2_supported_bend_radius_design_basis_mm").GetInt32()==80&&bend.GetProperty("loop_pipe_16x2_free_hand_radius_mm").GetInt32()==128&&bend.GetProperty("primary_pipe_32x3_radius_without_tool_mm").GetInt32()==160&&bend.GetProperty("primary_pipe_32x3_radius_with_Uponor_tool_mm").GetInt32()==80&&!bend.GetProperty("primary_hot_bending_allowed").GetBoolean()&&bend.GetProperty("hidden_joint_count").GetInt32()==0,"D114 bending policy");
        Require(model.GetProperty("site_release_sequence").GetArrayLength()==9&&model.GetProperty("complete_primary_route_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"floor_primary_channel_revision_evidence.png")),"D114 release scope and evidence");
    }

    private static void ValidateFloorPrimaryResearch113()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_RESEARCH_113"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_research.json")));
        var model=document.RootElement;var channels=model.GetProperty("external_model_channels");
        Require(model.GetProperty("source_records").GetArrayLength()==3&&model.GetProperty("official_source_findings").GetArrayLength()==4&&model.GetProperty("engineering_corrections").GetArrayLength()==6,"D113 research contract");
        Require(channels.GetProperty("claude").GetProperty("status").GetString()=="BLOCKED"&&channels.GetProperty("claude").GetProperty("timed_out").GetBoolean()&&!channels.GetProperty("claude").GetProperty("usable_engineering_response").GetBoolean(),"D113 Claude terminal status");
        Require(channels.GetProperty("kimi_api").GetProperty("status").GetString()=="NOT_SENT_PROVIDER_BINDING_UNAVAILABLE"&&!channels.GetProperty("kimi_api").GetProperty("canonical_ledger_row_created").GetBoolean()&&channels.GetProperty("kimi_api").GetProperty("charged_tokens").GetInt32()==0&&!channels.GetProperty("model_only_claim_used_for_design").GetBoolean(),"D113 Kimi safe stop");
        Require(!model.GetProperty("construction_authorized").GetBoolean()&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&File.Exists(Path.Combine(root,"report.md")),"D113 claim scope");
    }

    private static void ValidateFloorPrimaryInstallationSheet112()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_INSTALLATION_SHEET_112"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"installation_sheet.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_records").GetArrayLength()==4&&model.GetProperty("page_count").GetInt32()==4&&model.GetProperty("page_size").GetString()=="A3_LANDSCAPE","D112 document contract");
        Require(model.GetProperty("selected_method").GetString()=="HIDDEN_PRIMARY_PAIR_IN_EXISTING_FLOOR1_INSULATION"&&!model.GetProperty("external_wall_used").GetBoolean()&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&model.GetProperty("construction_issue_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D112 claim scope");
        var pdf=Path.Combine(root,model.GetProperty("pdf_file").GetString()!);
        Require(File.Exists(pdf)&&new FileInfo(pdf).Length>100000,"D112 PDF");
    }

    private static void ValidateVerticalDatumEvidence111()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_VERTICAL_DATUM_EVIDENCE_111"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"vertical_datum_evidence.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_geometry_and_numbers_preserved").GetBoolean()&&model.GetProperty("D110_overlapping_lower_labels_disposition").GetString()!.Contains("SUPERSEDED"),"D111 evidence repair");
        Require(model.GetProperty("working_interpretation").GetProperty("structural_slab_top_separation_mm").GetInt32()==3050&&model.GetProperty("primary_vertical_coordination").GetProperty("axis_to_K2_cabinet_bottom_vertical_coordinate_difference_mm").GetInt32()==3405,"D111 preserved values");
        Require(model.GetProperty("complete_primary_route_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"vertical_datum_evidence_corrected.png")),"D111 scope");
    }

    private static void ValidateVerticalDatum110()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_VERTICAL_DATUM_RECONCILIATION_110"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"vertical_datum_reconciliation.json")));
        var model=document.RootElement;var working=model.GetProperty("working_interpretation");var primary=model.GetProperty("primary_vertical_coordination");var unresolved=model.GetProperty("unresolved");
        Require(model.GetProperty("owner_height_statement_mm").GetInt32()==3000&&working.GetProperty("floor_1_finished_floor_global_z_mm").GetInt32()==170&&working.GetProperty("attic_finished_floor_global_z_mm").GetInt32()==3170&&working.GetProperty("structural_slab_top_separation_mm").GetInt32()==3050,"D110 datum chain");
        Require(primary.GetProperty("floor_1_hidden_primary_axis_global_z_mm").GetInt32()==35&&primary.GetProperty("attic_K2_cabinet_bottom_global_z_mm").GetInt32()==3440&&primary.GetProperty("attic_K2_cabinet_top_global_z_mm").GetInt32()==4170&&primary.GetProperty("axis_to_K2_cabinet_bottom_vertical_coordinate_difference_mm").GetInt32()==3405,"D110 primary Z");
        Require(unresolved.GetProperty("floor_or_slab_thickness_mm").ValueKind==JsonValueKind.Null&&unresolved.GetProperty("exact_pipe_cut_length_mm").ValueKind==JsonValueKind.Null&&!unresolved.GetProperty("site_laser_datum_confirmed").GetBoolean()&&model.GetProperty("complete_primary_route_count").GetInt32()==0&&!model.GetProperty("construction_authorized").GetBoolean(),"D110 unresolved scope");
    }

    private static void ValidateFloorPrimaryIntegration109()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_PRIMARY_INTEGRATION_109"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_primary_integration.json")));
        var model=document.RootElement;var floor=model.GetProperty("selected_floor_layer_design_basis_both_floors");var channel=model.GetProperty("selected_floor_1_primary_route_method");
        Require(model.GetProperty("source_records").GetArrayLength()==8&&model.GetProperty("owner_inputs_locked").GetProperty("floor_1_installed_insulation_mm").GetInt32()==100&&model.GetProperty("owner_inputs_locked").GetProperty("attic_installed_insulation_mm").GetInt32()==50,"D109 sources and owner layers");
        Require(floor.GetProperty("design_screed_cover_above_pipe_mm").GetInt32()==35&&floor.GetProperty("total_screed_from_insulation_top_mm").GetInt32()==51&&floor.GetProperty("finish_adhesive_underlay_allowance_mm").GetInt32()==19&&floor.GetProperty("height_reconciliation_mm").GetInt32()==70&&floor.GetProperty("fits").GetBoolean(),"D109 floor layer stack");
        Require(channel.GetProperty("axis_length_mm").GetInt32()==4570&&channel.GetProperty("strip_width_mm").GetInt32()==200&&channel.GetProperty("lower_service_zone_z_from_structural_slab_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{0,70})&&channel.GetProperty("restored_insulation_above_service_zone_mm").GetInt32()==30,"D109 channel section");
        Require(channel.GetProperty("warm_floor_loop_bottom_z_from_structural_slab_mm").GetInt32()==100&&channel.GetProperty("warm_floor_loop_top_z_from_structural_slab_mm").GetInt32()==116&&channel.GetProperty("minimum_primary_envelope_to_loop_surface_clearance_mm").GetInt32()==30&&channel.GetProperty("plan_crossing_route_count").GetInt32()==9&&channel.GetProperty("geometric_3d_contact_count").GetInt32()==0&&channel.GetProperty("hidden_press_fitting_count").GetInt32()==0,"D109 3D reconciliation");
        Require(channel.GetProperty("D104_depth_cut_wording_disposition").GetString()!.Contains("SUPERSEDED"),"D109 D104 clarification");
        var fastening=model.GetProperty("floor_1_no_fastener_control");
        Require(fastening.GetProperty("marked_zone_width_mm").GetDouble()==200&&fastening.GetProperty("affected_floor_loop_route_count").GetInt32()==9&&fastening.GetProperty("exact_loop_pipe_length_inside_marked_zone_mm").GetDouble()==6570&&!fastening.GetProperty("tacker_clip_staple_screw_anchor_allowed").GetBoolean()&&fastening.GetProperty("non_penetrating_support_or_load_spreading_bridge_required").GetBoolean(),"D109 no-fastener control");
        var thermal=model.GetProperty("thermal_screen");Require(thermal.GetProperty("pair_heat_loss_range_w")[0].GetDouble()>34&&thermal.GetProperty("pair_heat_loss_range_w")[1].GetDouble()<61&&!thermal.GetProperty("local_finished_floor_surface_temperature_calculated").GetBoolean(),"D109 thermal scope");
        var opening=model.GetProperty("internal_vertical_transition");Require(!opening.GetProperty("external_wall_used").GetBoolean()&&opening.GetProperty("same_plan_coordinates_both_floors").GetBoolean()&&opening.GetProperty("opening_bbox_building_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{9190,7300,9310,7500})&&opening.GetProperty("approved_slab_opening_count").GetInt32()==0,"D109 vertical transition");
        Require(model.GetProperty("installation_sequence").GetArrayLength()==9&&model.GetProperty("release_items").GetArrayLength()==6&&model.GetProperty("complete_primary_route_count").GetInt32()==0&&!model.GetProperty("procurement_authorized").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D109 release scope");
        Require(File.Exists(Path.Combine(root,"floor_primary_integration_evidence.png"))&&File.Exists(Path.Combine(root,"installation_release_checklist.md")),"D109 evidence");
    }

    private static void ValidatePrimaryChannelThermal108()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_CHANNEL_THERMAL_108"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_channel_thermal.json")));
        var model=document.RootElement;var pipe=model.GetProperty("pipe_insulation_screen");var scenarios=model.GetProperty("temperature_scenarios").EnumerateArray().ToArray();
        Require(Math.Abs(model.GetProperty("primary_route_axis_length_m").GetDouble()-4.57)<1e-9&&Math.Abs(model.GetProperty("D107_exact_loop_length_over_no_fastener_zone_mm").GetDouble()-6570)<1e-9,"D108 lengths");
        Require(pipe.GetProperty("pipe_od_mm").GetDouble()==32&&pipe.GetProperty("insulated_od_mm").GetDouble()==62&&pipe.GetProperty("insulation_thickness_mm").GetDouble()==15&&Math.Abs(pipe.GetProperty("insulation_lambda_w_mk").GetDouble()-.04)<1e-12&&!pipe.GetProperty("surrounding_30mm_floor_insulation_credited").GetBoolean(),"D108 insulation screen");
        Require(scenarios.Length==3,"D108 scenarios");
        var resistance=pipe.GetProperty("total_screening_resistance_k_m_w").GetDouble();
        foreach(var item in scenarios)
        {
            var q=(item.GetProperty("supply_temperature_c").GetDouble()-20)/resistance+(item.GetProperty("return_temperature_c").GetDouble()-20)/resistance;
            Require(Math.Abs(q-item.GetProperty("pair_heat_loss_w_m_route").GetDouble())<1e-9,"D108 heat loss per metre");
            Require(Math.Abs(q*4.57-item.GetProperty("pair_heat_loss_over_4_57m_w").GetDouble())<1e-9,"D108 total heat loss");
        }
        var range=model.GetProperty("screening_result").GetProperty("pair_heat_loss_range_w");
        Require(range[0].GetDouble()>34&&range[0].GetDouble()<36&&range[1].GetDouble()>60&&range[1].GetDouble()<61&&!model.GetProperty("screening_result").GetProperty("local_floor_surface_temperature_calculated").GetBoolean(),"D108 result range");
        Require(!model.GetProperty("final_primary_temperatures_selected").GetBoolean()&&!model.GetProperty("exact_insulation_product_selected").GetBoolean()&&!model.GetProperty("linear_thermal_bridge_calculated").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D108 scope");
        Require(File.Exists(Path.Combine(root,"primary_channel_thermal_evidence.png")),"D108 image");
    }

    private static void ValidatePrimaryChannelNoFastener107()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_CHANNEL_NO_FASTENER_107"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_channel_no_fastener.json")));
        var model=document.RootElement;var affected=model.GetProperty("affected_routes").EnumerateArray().ToArray();
        Require(model.GetProperty("no_fastener_zone_half_width_mm").GetDouble()==100&&model.GetProperty("no_fastener_zone_total_width_mm").GetDouble()==200&&Math.Abs(model.GetProperty("no_fastener_zone_area_m2").GetDouble()-.914)<1e-9,"D107 marked zone");
        Require(model.GetProperty("affected_route_count").GetInt32()==9&&affected.Length==9&&Math.Abs(model.GetProperty("total_loop_pipe_length_inside_marked_zone_mm").GetDouble()-6570)<1e-9,"D107 affected pipe");
        var routeIds=affected.Select(x=>x.GetProperty("route_id").GetString()).ToArray();
        Require(routeIds.SequenceEqual(new[]{"F1-C01","F1-C02","F1-C03","F1-C04","F1-C11","F1-C12","F1-C14","F1-C05","F1-C06"}),"D107 route IDs");
        Require(affected.All(x=>x.GetProperty("3d_pipe_contact_count").GetInt32()==0)&&model.GetProperty("all_plan_crossings_3d_contact_free").GetBoolean()&&model.GetProperty("minimum_3d_surface_clearance_mm").GetDouble()==30,"D107 clearance");
        Require(!model.GetProperty("floor_loop_ordered_points_modified").GetBoolean()&&!model.GetProperty("primary_pipe_geometry_published").GetBoolean()&&!model.GetProperty("fixing_product_selected").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D107 scope");
        Require(File.Exists(Path.Combine(root,"primary_channel_no_fastener_overlay.png")),"D107 image");
    }

    private static void ValidatePrimaryChannel3DEvidence106()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_EVIDENCE_106"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_channel_3d_corrected.json")));
        var model=document.RootElement;var calc=model.GetProperty("independent_recalculation");
        Require(model.GetProperty("D105_geometry_preserved").GetBoolean()&&model.GetProperty("D105_false_textual_22mm_disposition").GetString()!.Contains("SUPERSEDED"),"D106 disposition");
        Require(calc.GetProperty("primary_envelope_top_z_mm").GetDouble()==70&&calc.GetProperty("loop_pipe_bottom_z_mm").GetDouble()==100&&calc.GetProperty("minimum_surface_clearance_mm").GetDouble()==30&&calc.GetProperty("geometric_3d_contact_count").GetInt32()==0,"D106 clearance");
        Require(model.GetProperty("plan_crossing_route_count").GetInt32()==9&&!model.GetProperty("thermal_structural_or_fastener_approval").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D106 scope");
        Require(File.Exists(Path.Combine(root,"primary_channel_3d_corrected_evidence.png")),"D106 image");
    }

    private static void ValidatePrimaryChannel3D105()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_CHANNEL_3D_105"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_channel_3d.json")));
        var model=document.RootElement;var z=model.GetProperty("layer_z_contract_mm");var crossing=model.GetProperty("crossing_separation");
        Require(z.GetProperty("primary_envelope_top").GetDouble()==70&&z.GetProperty("installed_insulation_top").GetDouble()==100&&z.GetProperty("loop_pipe_bottom").GetDouble()==100&&z.GetProperty("loop_pipe_top").GetDouble()==116&&z.GetProperty("screed_top").GetDouble()==151&&z.GetProperty("finished_floor_top").GetDouble()==170,"D105 Z contract");
        Require(crossing.GetProperty("minimum_primary_envelope_to_loop_pipe_surface_clearance_mm").GetDouble()==30&&crossing.GetProperty("geometric_3d_contact_count").GetInt32()==0&&crossing.GetProperty("plan_crossing_route_count").GetInt32()==9&&crossing.GetProperty("plan_crossing_is_not_pipe_contact_due_to_z_separation").GetBoolean(),"D105 crossing separation");
        Require(model.GetProperty("fastener_and_channel_policy").GetProperty("hidden_primary_press_fitting_count").GetInt32()==0&&model.GetProperty("fastener_and_channel_policy").GetProperty("no_loop_tacker_clip_or_floor_anchor_may_enter_channel_footprint").GetBoolean(),"D105 fastener policy");
        Require(!model.GetProperty("thermal_scope").GetProperty("linear_heat_loss_and_floor_surface_temperature_over_channel_calculated").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D105 scope");
    }

    private static void ValidatePrimaryInsulationChannel104()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_INSULATION_CHANNEL_104"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_insulation_channel.json")));
        var model=document.RootElement;var section=model.GetProperty("channel_cross_section");var installation=model.GetProperty("installation_policy");
        Require(section.GetProperty("width_mm").GetDouble()==200&&section.GetProperty("depth_cut_into_installed_insulation_mm").GetDouble()==70&&section.GetProperty("installed_insulation_total_mm").GetDouble()==100&&section.GetProperty("restored_or_continuous_insulation_above_channel_mm").GetDouble()==30,"D104 channel section");
        Require(section.GetProperty("primary_envelope_od_mm").GetDouble()==70&&section.GetProperty("axis_pitch_mm").GetInt32()==100&&section.GetProperty("clear_gap_between_envelopes_mm").GetInt32()==30&&section.GetProperty("side_margin_each_envelope_mm").GetInt32()==15&&section.GetProperty("straight_section_geometric_fit").GetBoolean(),"D104 packing");
        Require(installation.GetProperty("continuous_factory_insulated_primary_lengths_in_hidden_channel").GetBoolean()&&installation.GetProperty("hidden_press_fitting_count").GetInt32()==0&&installation.GetProperty("all_press_fittings_in_accessible_K1_and_riser_boxes").GetBoolean()&&installation.GetProperty("warm_floor_70mm_stack_above_installed_insulation_preserved").GetBoolean(),"D104 installation policy");
        Require(model.GetProperty("thermal_and_structural_checks").GetProperty("floor_1_heating_route_contacts_from_D079").GetInt32()==9&&!model.GetProperty("channel_construction_authorized").GetBoolean()&&model.GetProperty("complete_primary_pipe_geometry_count").GetInt32()==0,"D104 scope");
        Require(File.Exists(Path.Combine(root,"primary_insulation_channel_evidence.png")),"D104 image");
    }

    private static void ValidateFloorLayerStack103()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_LAYER_STACK_103"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_layer_stack.json")));
        var model=document.RootElement;var layer=model.GetProperty("selected_layer_design_basis");
        Require(model.GetProperty("available_height_above_installed_insulation_mm").GetDouble()==70&&model.GetProperty("loop_pipe").GetProperty("outer_diameter_mm").GetDouble()==16,"D103 base dimensions");
        Require(layer.GetProperty("design_screed_cover_above_pipe_mm").GetDouble()==35&&layer.GetProperty("total_screed_from_insulation_top_mm").GetDouble()==51&&layer.GetProperty("remaining_finish_adhesive_underlay_allowance_mm").GetDouble()==19&&layer.GetProperty("height_reconciliation_mm").GetDouble()==70&&layer.GetProperty("fits_available_70mm").GetBoolean(),"D103 layer reconciliation");
        Require(model.GetProperty("standard_sand_cement_comparison").GetProperty("official_uponor_uk_domestic_total_screed_depth_over_insulation_mm").GetDouble()==65&&model.GetProperty("standard_sand_cement_comparison").GetProperty("remaining_finish_allowance_mm").GetDouble()==5&&!model.GetProperty("standard_sand_cement_comparison").GetProperty("selected_as_default").GetBoolean(),"D103 standard comparison");
        Require(!model.GetProperty("screed_product_selected").GetBoolean()&&!model.GetProperty("final_floor_finish_selected").GetBoolean()&&!model.GetProperty("design_surface_load_confirmed").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean(),"D103 scope");
        Require(File.Exists(Path.Combine(root,"floor_layer_stack_evidence.png")),"D103 image");
    }

    private static void ValidateFloorBuildUpStageGate102()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR_BUILDUP_STAGE_GATE_102"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"floor_build_up_stage_gate.json")));
        var model=document.RootElement;var accepted=model.GetProperty("accepted_owner_build_up");var datum=model.GetProperty("K2_updated_vertical_datum");
        Require(accepted.GetProperty("floor_1_installed_insulation_mm").GetInt32()==100&&accepted.GetProperty("floor_1_remaining_to_finished_floor_mm").GetInt32()==70&&accepted.GetProperty("floor_1_total_slab_to_finished_floor_mm").GetInt32()==170,"D102 floor1 build-up");
        Require(accepted.GetProperty("attic_installed_insulation_mm").GetInt32()==50&&accepted.GetProperty("attic_remaining_to_finished_floor_mm").GetInt32()==70&&accepted.GetProperty("attic_total_slab_to_finished_floor_mm").GetInt32()==120,"D102 attic build-up");
        Require(datum.GetProperty("cabinet_bottom_above_structural_slab_mm").GetInt32()==390&&datum.GetProperty("cabinet_top_above_structural_slab_mm").GetInt32()==1120,"D102 K2 datum");
        Require(model.GetProperty("three_metre_height_working_interpretation").GetProperty("implied_structural_slab_top_separation_mm").GetInt32()==3050&&!model.GetProperty("three_metre_height_working_interpretation").GetProperty("final_vertical_route_length_released").GetBoolean(),"D102 height datum");
        Require(model.GetProperty("site_or_layer_inputs_still_required").GetArrayLength()==4&&!model.GetProperty("floor_layer_construction_approved").GetBoolean()&&!model.GetProperty("primary_service_box_construction_approved").GetBoolean()&&model.GetProperty("complete_primary_route_count").GetInt32()==0,"D102 claim scope");
    }

    private static void ValidatePrimaryWallServiceBox101()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PRIMARY_WALL_SERVICE_BOX_101"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"primary_wall_service_box.json")));
        var model=document.RootElement;var section=model.GetProperty("service_box_section_reservation");
        Require(!model.GetProperty("external_wall_used").GetBoolean()&&!model.GetProperty("buried_in_remaining_70mm_floor_build_up").GetBoolean()&&!model.GetProperty("wall_chase_in_AAC").GetBoolean(),"D101 route policy");
        Require(section.GetProperty("clear_internal_height_mm").GetDouble()==200&&section.GetProperty("clear_internal_depth_mm").GetDouble()==120&&section.GetProperty("primary_axes_height_above_finished_floor_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{50d,150d}),"D101 box section");
        Require(section.GetProperty("provisional_pipe_envelope_od_mm").GetDouble()==70&&section.GetProperty("clear_gap_between_envelopes_mm").GetDouble()==30&&section.GetProperty("minimum_vertical_edge_margin_mm").GetDouble()==15&&section.GetProperty("symmetric_depth_margin_if_centered_mm").GetDouble()==25&&section.GetProperty("geometric_straight_section_packing_pass").GetBoolean(),"D101 packing");
        var access=model.GetProperty("bend_and_tool_access");Require(access.GetProperty("removable_inspection_cover_required").GetBoolean()&&!access.GetProperty("joints_buried_in_screed").GetBoolean()&&!access.GetProperty("press_jaw_service_access_validated").GetBoolean(),"D101 access");
        Require(!model.GetProperty("full_plan_polyline_published").GetBoolean()&&!model.GetProperty("construction_authorized").GetBoolean()&&File.Exists(Path.Combine(root,"primary_wall_service_box_evidence.png")),"D101 claim scope");
    }

    private static void ValidateOwnerFloorBuildUp100()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_OWNER_FLOOR_BUILDUP_100"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"owner_floor_build_up.json")));
        var model=document.RootElement;var layers=model.GetProperty("owner_reported_layers");var f1=layers.GetProperty("floor_1");var attic=layers.GetProperty("attic_floor_2");
        Require(f1.GetProperty("installed_insulation_mm").GetDouble()==100&&f1.GetProperty("remaining_height_above_insulation_to_planned_finished_floor_mm").GetDouble()==70&&f1.GetProperty("provisional_structural_slab_to_finished_floor_build_up_mm").GetDouble()==170,"D100 floor1 layers");
        Require(attic.GetProperty("installed_insulation_mm").GetDouble()==50&&attic.GetProperty("remaining_height_above_insulation_to_planned_finished_floor_mm").GetDouble()==70&&attic.GetProperty("provisional_structural_slab_to_finished_floor_build_up_mm").GetDouble()==120,"D100 attic layers");
        var loop=model.GetProperty("loop_16mm_layer_screen");Require(loop.GetProperty("height_left_after_bare_pipe_mm").GetDouble()==54&&loop.GetProperty("geometrically_fits_in_remaining_height").GetBoolean()&&!loop.GetProperty("required_cover_screed_finish_and_strength_verified").GetBoolean(),"D100 loop screen");
        var primary=model.GetProperty("primary_32mm_floor_concealment_screen");Require(primary.GetProperty("official_comparison_outer_diameter_mm").GetDouble()==62&&primary.GetProperty("height_left_with_62mm_factory_insulated_comparison_mm").GetDouble()==8&&primary.GetProperty("height_left_with_D098_70mm_reservation_envelope_mm").GetDouble()==0&&!primary.GetProperty("concealed_primary_route_inside_remaining_70mm_accepted").GetBoolean(),"D100 primary screen");
        var datum=model.GetProperty("attic_K2_mounting_datum_update");Require(datum.GetProperty("cabinet_bottom_above_structural_slab_mm").GetDouble()==390&&datum.GetProperty("cabinet_top_above_structural_slab_mm").GetDouble()==1120,"D100 K2 datum");
        Require(model.GetProperty("height_datum_reconciliation").GetProperty("accepted_vertical_design_length_mm").ValueKind==JsonValueKind.Null&&!model.GetProperty("construction_layer_detail_approved").GetBoolean()&&File.Exists(Path.Combine(root,"owner_floor_build_up_evidence.png")),"D100 claim scope");
    }

    private static void ValidateInternalRiserK2StageGate099()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_099"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"internal_riser_k2_stage_gate.json")));
        var model=document.RootElement;var owner=model.GetProperty("owner_inputs_locked");var accepted=model.GetProperty("accepted_design_baseline");
        Require(owner.GetProperty("floor_to_floor_height_mm").GetInt32()==3000&&owner.GetProperty("wall_material").GetString()=="AAC_GAS_CONCRETE"&&owner.GetProperty("loop_pipe_outer_diameter_mm").GetInt32()==16&&owner.GetProperty("loop_design_centerline_bend_radius_mm").GetInt32()==80&&!owner.GetProperty("heated_radius_reduction_credited").GetBoolean()&&!owner.GetProperty("external_wall_transition_used").GetBoolean(),"D099 owner inputs");
        Require(accepted.GetProperty("attic_circuit_count").GetInt32()==12&&accepted.GetProperty("attic_loop_port_count").GetInt32()==24&&accepted.GetProperty("primary_clear_id_mm").GetDouble()==26&&accepted.GetProperty("primary_turn_fitting_quantity_screen").GetInt32()==4,"D099 architecture");
        Require(accepted.GetProperty("penetration_clear_size_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{120d,200d})&&accepted.GetProperty("vertical_primary_axes").GetArrayLength()==2&&accepted.GetProperty("same_penetration_coordinates_both_floors").GetBoolean(),"D099 penetration");
        Require(model.GetProperty("source_records").GetArrayLength()==7&&model.GetProperty("external_or_owner_input_gate").GetProperty("human_action_required").GetBoolean()&&model.GetProperty("external_or_owner_input_gate").GetProperty("items").GetArrayLength()==4,"D099 handoff");
        Require(model.GetProperty("complete_attic_route_count").GetInt32()==0&&model.GetProperty("approved_slab_opening_count").GetInt32()==0&&model.GetProperty("construction_issue_count").GetInt32()==0,"D099 construction claims");
        Require(File.Exists(Path.Combine(root,"internal_riser_k2_stage_gate_evidence.png"))&&File.Exists(Path.Combine(root,"site_release_checklist.md")),"D099 evidence files");
    }

    private static void ValidateTwoPrimaryInternalPenetration098()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_TWO_PRIMARY_INTERNAL_PENETRATION_098"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"two_primary_internal_penetration.json")));
        var model=document.RootElement;var opening=model.GetProperty("selected_building_plan_opening_candidate");var envelope=model.GetProperty("provisional_insulated_pipe_envelope");
        Require(opening.GetProperty("building_bbox_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{9190d,7300d,9310d,7500d}),"D098 opening bbox");
        Require(opening.GetProperty("clear_size_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{120d,200d})&&opening.GetProperty("same_physical_plan_coordinates_on_both_floors").GetBoolean()&&opening.GetProperty("inside_D079_maximum_reservation").GetBoolean()&&opening.GetProperty("inside_attic_K2_service_zone").GetBoolean()&&opening.GetProperty("does_not_cut_registered_common_wall_core").GetBoolean(),"D098 containment");
        var axes=model.GetProperty("vertical_primary_axes").EnumerateArray().Select(a=>a.GetProperty("building_plan_xy_mm").EnumerateArray().Select(x=>x.GetDouble()).ToArray()).ToArray();
        Require(axes.Length==2&&axes[0].SequenceEqual(new[]{9250d,7350d})&&axes[1].SequenceEqual(new[]{9250d,7450d}),"D098 axes");
        Require(Math.Abs(envelope.GetProperty("outer_envelope_diameter_mm").GetDouble()-70)<1e-6&&Math.Abs(envelope.GetProperty("axis_pitch_mm").GetDouble()-100)<1e-6&&Math.Abs(envelope.GetProperty("clear_gap_between_envelopes_mm").GetDouble()-30)<1e-6&&Math.Abs(envelope.GetProperty("minimum_envelope_to_opening_y_edge_mm").GetDouble()-15)<1e-6&&envelope.GetProperty("geometric_packing_pass").GetBoolean()&&!envelope.GetProperty("final_insulation_product_selected").GetBoolean(),"D098 envelope");
        Require(!model.GetProperty("slab_opening_cut_authorized").GetBoolean()&&model.GetProperty("slab_rebar_beam_scan_required").GetBoolean()&&model.GetProperty("structural_engineer_or_responsible_designer_release_required").GetBoolean()&&model.GetProperty("complete_primary_route_geometry_count").GetInt32()==0,"D098 claim scope");
        Require(File.Exists(Path.Combine(root,"two_primary_internal_penetration_evidence.png")),"D098 image");
    }

    private static void ValidateAtticPrimaryBendFittings097()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PRIMARY_BEND_FITTINGS_097"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_primary_bend_fittings.json")));
        var model=document.RootElement;var fitting=model.GetProperty("selected_direction_change_fitting");var policy=model.GetProperty("bend_policy");
        Require(model.GetProperty("selected_primary_pipe_part_number").GetString()=="1059583"&&fitting.GetProperty("part_number").GetString()=="1070526"&&fitting.GetProperty("nominal_size").GetString()=="32-32","D097 product binding");
        Require(fitting.GetProperty("official_leg_length_l_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{51d,51d})&&fitting.GetProperty("official_z_mm").EnumerateArray().Select(x=>x.GetDouble()).SequenceEqual(new[]{23d,23d}),"D097 dimensions");
        Require(model.GetProperty("design_quantity_screen").GetProperty("total_32x32_elbows").GetInt32()==4&&policy.GetProperty("owner_R80_scope").GetString()=="LOOP_PIPE_16MM_ONLY"&&policy.GetProperty("primary_direction_changes_use_selected_press_elbow").GetBoolean()&&policy.GetProperty("primary_hot_air_or_open_flame_bending_prohibited").GetBoolean()&&!policy.GetProperty("primary_field_bend_radius_credited").GetBoolean(),"D097 bend policy");
        Require(model.GetProperty("complete_primary_route_geometry_count").GetInt32()==0&&model.GetProperty("approved_installed_fitting_count").GetInt32()==0&&!model.GetProperty("procurement_authorized").GetBoolean(),"D097 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_primary_bend_fittings_evidence.png")),"D097 image");
    }

    private static void ValidateAtticPrimaryPipeSelection096()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PRIMARY_PIPE_SELECTION_096"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_primary_pipe_selection.json")));
        var model=document.RootElement;var pipe=model.GetProperty("selected_design_basis_primary_pipe");
        Require(pipe.GetProperty("part_number").GetString()=="1059583"&&Math.Abs(pipe.GetProperty("outer_diameter_mm").GetDouble()-32)<1e-6&&Math.Abs(pipe.GetProperty("wall_thickness_mm").GetDouble()-3)<1e-6&&Math.Abs(pipe.GetProperty("calculated_clear_inside_diameter_mm").GetDouble()-26)<1e-6,"D096 pipe selection");
        var records=model.GetProperty("screening_records").EnumerateArray().ToArray();Require(records.Length==4,"D096 scenarios");
        foreach(var item in records)
        {
            Require(item.GetProperty("flow_m3_h").GetDouble()>0&&item.GetProperty("velocity_m_s").GetDouble()>0&&item.GetProperty("straight_pipe_pressure_gradient_pa_m").GetDouble()>0,"D096 positive hydraulics");
            Require(Math.Abs(item.GetProperty("one_way_8m_straight_pressure_drop_pa").GetDouble()*2-item.GetProperty("supply_return_16m_straight_pressure_drop_pa").GetDouble())<1e-6,"D096 straight pair reconciliation");
        }
        var baseline=model.GetProperty("base_screening_result");var worst=model.GetProperty("worst_screening_result");
        Require(baseline.GetProperty("velocity_m_s").GetDouble()>0.58&&baseline.GetProperty("velocity_m_s").GetDouble()<0.59&&baseline.GetProperty("velocity_below_D083_0_7m_s_screening_value").GetBoolean(),"D096 base velocity");
        Require(worst.GetProperty("velocity_m_s").GetDouble()>1.09&&!worst.GetProperty("velocity_below_D083_0_7m_s_screening_value").GetBoolean(),"D096 worst velocity");
        Require(model.GetProperty("all_screening_flows_below_selected_manifold_documented_max").GetBoolean()&&!model.GetProperty("insulation_product_selected").GetBoolean()&&!model.GetProperty("heat_loss_calculation_available").GetBoolean()&&!model.GetProperty("pump_head_selected").GetBoolean()&&model.GetProperty("complete_primary_route_geometry_count").GetInt32()==0&&!model.GetProperty("procurement_authorized").GetBoolean(),"D096 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_primary_pipe_selection_evidence.png")),"D096 image");
    }

    private static void ValidateAtticK2MountingDatum095()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_MOUNTING_DATUM_095"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_mounting_datum.json")));
        var model=document.RootElement;var datum=model.GetProperty("project_mounting_datum");
        Require(Math.Abs(datum.GetProperty("cabinet_top_aff_mm").GetDouble()-1000)<1e-6&&Math.Abs(datum.GetProperty("cabinet_bottom_aff_mm").GetDouble()-270)<1e-6&&!datum.GetProperty("site_finished_floor_level_verified").GetBoolean()&&datum.GetProperty("site_marking_required_before_drilling").GetBoolean(),"D095 datum");
        var bend=model.GetProperty("bend_envelope_screen");
        Require(Math.Abs(bend.GetProperty("outer_pipe_envelope_radius_mm").GetDouble()-88)<1e-6&&Math.Abs(bend.GetProperty("supply_frontward_turn_envelope_margin_mm").GetDouble()-17)<1e-6&&Math.Abs(bend.GetProperty("return_frontward_turn_envelope_margin_mm").GetDouble()+3)<1e-6&&!bend.GetProperty("all_frontward_turns_fit_inside_closed_cabinet_depth").GetBoolean()&&bend.GetProperty("vertical_envelope_screen_pass").GetBoolean(),"D095 bend envelope");
        Require(model.GetProperty("absolute_manifold_header_z_mm").ValueKind==JsonValueKind.Null&&model.GetProperty("absolute_loop_port_z_mm").ValueKind==JsonValueKind.Null&&model.GetProperty("published_3d_fanout_pipe_count").GetInt32()==0&&model.GetProperty("complete_route_count").GetInt32()==0&&!model.GetProperty("wall_drilling_authorized").GetBoolean(),"D095 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_k2_mounting_datum_evidence.png")),"D095 image");
    }

    private static void ValidateAtticK2SelectedPortBudgets094()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORT_BUDGETS_094"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_selected_port_budgets.json")));
        var model=document.RootElement;var budgets=model.GetProperty("circuit_budgets").EnumerateArray().ToArray();
        Require(budgets.Length==12&&model.GetProperty("physical_plan_port_count").GetInt32()==24&&model.GetProperty("unique_station_count").GetInt32()==12,"D094 counts");
        var stations=new HashSet<int>();var ports=new HashSet<string>();double links=0;
        foreach(var item in budgets)
        {
            Require(stations.Add(item.GetProperty("selected_product_station_index").GetInt32()),"D094 duplicate station");
            Require(ports.Add(item.GetProperty("selected_supply_port_id").GetString()!)&&ports.Add(item.GetProperty("selected_return_port_id").GetString()!),"D094 duplicate port");
            var supply=item.GetProperty("optimistic_supply_link_lower_bound_mm").GetDouble();var inter=item.GetProperty("optimistic_inter_body_link_lower_bound_mm").GetDouble();var returning=item.GetProperty("optimistic_return_link_lower_bound_mm").GetDouble();var total=item.GetProperty("optimistic_total_lower_bound_mm").GetDouble();
            Require(Math.Abs(item.GetProperty("body_length_mm").GetInt32()+supply+inter+returning-total)<1e-6,"D094 component reconciliation");
            Require(Math.Abs(78000-total-item.GetProperty("budget_to_78m_target_mm").GetDouble())<1e-6,"D094 target budget");
            Require(total>=40000&&total<=80000&&item.GetProperty("within_40_80m_at_lower_bound").GetBoolean(),"D094 lower-bound range");
            Require(!item.GetProperty("complete_route_geometry_published").GetBoolean(),"D094 complete route claim");
            links+=supply+inter+returning;
        }
        Require(stations.SetEquals(Enumerable.Range(1,12))&&ports.Count==24,"D094 station and port uniqueness");
        Require(Math.Abs(links-model.GetProperty("total_paired_link_lower_bound_mm").GetDouble())<1e-6,"D094 link objective");
        var changed=model.GetProperty("station_assignments_changed_from_D089").EnumerateArray().Select(item=>item.GetString()).ToHashSet();
        Require(changed.SetEquals(new[]{"A-C12","A-C13","A-C10_C11_SERIAL"}),"D094 changed assignments");
        var tight=model.GetProperty("tightest_budget_to_78m_target");
        Require(tight.GetProperty("circuit_id").GetString()=="A-C07"&&tight.GetProperty("budget_mm").GetDouble()>3900&&tight.GetProperty("budget_mm").GetDouble()<4000,"D094 tightest circuit");
        Require(model.GetProperty("all_optimistic_totals_within_40_80m").GetBoolean()&&!model.GetProperty("installation_authority").GetBoolean()&&model.GetProperty("fanout_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_route_count").GetInt32()==0,"D094 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_k2_selected_port_budgets_evidence.png")),"D094 image");
    }

    private static void ValidateAtticK2SelectedPorts093()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_SELECTED_PORTS_093"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_selected_ports.json")));
        var model=document.RootElement;var ports=model.GetProperty("physical_plan_ports").EnumerateArray().ToArray();
        Require(model.GetProperty("selected_manifold_part_number").GetString()=="1140843"&&model.GetProperty("selected_cabinet_part_number").GetString()=="1136219","D093 products");
        Require(ports.Length==24&&model.GetProperty("port_count").GetInt32()==24&&model.GetProperty("unique_plan_coordinate_count").GetInt32()==24&&model.GetProperty("unique_port_id_count").GetInt32()==24&&model.GetProperty("unique_route_leg_ownership_count").GetInt32()==24,"D093 counts");
        var coordinates=new HashSet<string>();var ids=new HashSet<string>();var legs=new HashSet<string>();var stationYs=new SortedSet<double>();
        foreach(var port in ports)
        {
            var xy=port.GetProperty("building_plan_xy_mm");
            Require(coordinates.Add($"{xy[0]}:{xy[1]}")&&ids.Add(port.GetProperty("physical_port_id").GetString()!)&&legs.Add($"{port.GetProperty("route_id").GetString()}:{port.GetProperty("leg").GetString()}"),"D093 uniqueness");
            stationYs.Add(xy[1].GetDouble());Require(port.GetProperty("mounting_height_z_mm").ValueKind==JsonValueKind.Null,"D093 Z claim");
        }
        Require(coordinates.Count==24&&ids.Count==24&&legs.Count==24&&stationYs.Count==12,"D093 independent counts");
        var ys=stationYs.ToArray();Require(ys.Zip(ys.Skip(1)).All(pair=>Math.Abs(pair.Second-pair.First-50)<1e-6),"D093 50mm station pitch");
        var dimensions=model.GetProperty("manufacturer_drawing_source").GetProperty("drawing_dimensions_mm");
        Require(Math.Abs(dimensions.GetProperty("overall_length_l").GetDouble()-714)<1e-6&&Math.Abs(dimensions.GetProperty("header_pitch_specification").GetDouble()-215)<1e-6&&Math.Abs(dimensions.GetProperty("drawing_measurement_b1").GetDouble()-217)<1e-6,"D093 dimension semantics");
        var clearance=model.GetProperty("cabinet_plan_clearance_screening");
        Require(Math.Abs(clearance.GetProperty("minimum_plan_clearance_mm").GetDouble()-85)<1e-6&&clearance.GetProperty("minimum_plan_clearance_at_least_r80").GetBoolean()&&Math.Abs(clearance.GetProperty("minimum_plan_margin_over_r80_mm").GetDouble()-5)<1e-6,"D093 plan R80 screen");
        Require(model.GetProperty("plan_port_coordinates_bound_to_selected_product").GetBoolean()&&!model.GetProperty("mounting_height_bound").GetBoolean()&&model.GetProperty("fanout_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_route_count").GetInt32()==0&&!model.GetProperty("procurement_authorized").GetBoolean(),"D093 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_k2_selected_ports_evidence.png")),"D093 image");
    }

    private static void ValidateAtticK2ProductEvidence092()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_PRODUCT_EVIDENCE_092"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_product_selection_corrected.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("derived_from_artifact_id").GetString()=="HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091","D092 source");
        Require(model.GetProperty("D091_margin_field_disposition").GetProperty("D091_field_rejected").GetBoolean(),"D092 D091 margin disposition");
        Require(model.GetProperty("fit_validation").GetProperty("manifold_length_margin_inside_cabinet_l1_mm").GetInt32()==275&&model.GetProperty("fit_validation").GetProperty("cabinet_outer_length_minus_manifold_length_mm").GetInt32()==336,"D092 margins");
        Require(model.GetProperty("official_cabinet_compatibility_evidence").GetProperty("minimum_official_cabinet_internal_width_class_mm").GetInt32()==850&&model.GetProperty("official_cabinet_compatibility_evidence").GetProperty("selected_cabinet_compatibility_pass").GetBoolean(),"D092 official compatibility");
        Require(validation.GetProperty("selected_manifold_part_number").GetString()=="1140843"&&validation.GetProperty("selected_cabinet_part_number").GetString()=="1136219","D092 products");
        Require(validation.GetProperty("official_compatibility_pass").GetBoolean()&&validation.GetProperty("D091_false_margin_field_rejected").GetBoolean()&&!validation.GetProperty("physical_port_coordinates_bound").GetBoolean()&&!validation.GetProperty("purchase_authorized").GetBoolean(),"D092 claim scope");
        Require(File.Exists(Path.Combine(root,"attic_k2_product_evidence.png")),"D092 image");
    }

    private static void ValidateAtticK2ProductSelection091()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_PRODUCT_SELECTION_091"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_product_selection.json")));
        var model=document.RootElement;var manifold=model.GetProperty("selected_design_basis_manifold");var cabinet=model.GetProperty("selected_design_basis_cabinet");var fit=model.GetProperty("fit_validation");
        Require(manifold.GetProperty("part_number").GetString()=="1140843"&&manifold.GetProperty("circuit_count").GetInt32()==12&&manifold.GetProperty("product_measurement_LENGTH_L_mm").GetInt32()==714&&manifold.GetProperty("loop_pitch_mm").GetInt32()==50&&manifold.GetProperty("header_pitch_mm").GetInt32()==215,"D091 manifold");
        Require(cabinet.GetProperty("part_number").GetString()=="1136219"&&cabinet.GetProperty("mounting_type").GetString()=="ON_WALL"&&cabinet.GetProperty("cabinet_length_mm").GetInt32()==1050&&cabinet.GetProperty("cabinet_depth_mm").GetInt32()==135&&!cabinet.GetProperty("wall_recess_required").GetBoolean(),"D091 cabinet");
        Require(fit.GetProperty("service_zone_contains_cabinet_plan_bbox").GetBoolean()&&fit.GetProperty("cabinet_length_margin_inside_service_zone_mm").GetInt32()==250&&fit.GetProperty("cabinet_depth_margin_inside_service_zone_mm").GetInt32()==165&&fit.GetProperty("C01_clearance_exceeds_twice_R80").GetBoolean(),"D091 plan fit");
        Require(model.GetProperty("superseded_parametric_geometry").GetProperty("D088_header_pitch_mm").GetInt32()==225&&model.GetProperty("superseded_parametric_geometry").GetProperty("selected_product_header_pitch_mm").GetInt32()==215&&model.GetProperty("superseded_parametric_geometry").GetProperty("D088_3d_header_z_coordinates_rejected_for_selected_product").GetBoolean(),"D091 D088 disposition");
        Require(model.GetProperty("physical_manifold_selected_as_design_basis").GetBoolean()&&model.GetProperty("physical_cabinet_selected_as_design_basis").GetBoolean()&&!model.GetProperty("purchase_authorized").GetBoolean()&&model.GetProperty("physical_port_coordinate_count").GetInt32()==0,"D091 selection scope");
        Require(File.Exists(Path.Combine(root,"attic_k2_product_selection_evidence.png")),"D091 image");
    }

    private static void ValidateInternalRiserK2StageGate090()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_INTERNAL_RISER_K2_STAGE_GATE_090"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"internal_riser_k2_stage_gate.json")));
        var model=document.RootElement;var owner=model.GetProperty("owner_inputs_locked");
        Require(owner.GetProperty("vertical_floor_to_floor_height_mm").GetInt32()==3000&&owner.GetProperty("wall_material").GetString()=="AAC_GAS_CONCRETE"&&owner.GetProperty("loop_pipe_outer_diameter_mm").GetInt32()==16&&owner.GetProperty("minimum_bend_radius_mm").GetInt32()==80,"D090 owner inputs");
        Require(owner.GetProperty("external_wall_transition_rejected").GetBoolean()&&owner.GetProperty("preferred_path").GetString()!.Contains("BOILER_ROOM"),"D090 internal strategy");
        var baseline=model.GetProperty("accepted_parametric_baseline");
        Require(baseline.GetProperty("attic_circuit_count").GetInt32()==12&&baseline.GetProperty("primary_main_count").GetInt32()==2&&baseline.GetProperty("K2_candidate_3d_port_count").GetInt32()==24,"D090 architecture");
        Require(baseline.GetProperty("C01_reworked_body_length_mm").GetInt32()==45800&&baseline.GetProperty("C01_axis_to_service_zone_clearance_mm").GetDouble()>229,"D090 C01 baseline");
        Require(!baseline.GetProperty("station_assignment_is_physical_authority").GetBoolean(),"D090 station authority");
        var hydraulic=model.GetProperty("hydraulic_screening_baseline");
        Require(hydraulic.GetProperty("screening_only").GetBoolean()&&Math.Abs(hydraulic.GetProperty("base_power_kw").GetDouble()-9.09)<1e-6,"D090 hydraulic scope");
        Require(model.GetProperty("safe_frozen_claims").GetArrayLength()==11&&model.GetProperty("external_or_owner_action_gate").GetProperty("items").GetArrayLength()==4,"D090 stage lists");
        Require(model.GetProperty("complete_route_count").GetInt32()==0&&!model.GetProperty("physical_product_selected").GetBoolean()&&!model.GetProperty("production_opening_authorized").GetBoolean(),"D090 production boundaries");
        Require(File.Exists(Path.Combine(root,"report.md")),"D090 report");
    }

    private static void ValidateAtticK2StationAssignment089()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_STATION_ASSIGNMENT_089"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_station_assignment.json")));
        var model=document.RootElement;var assignments=model.GetProperty("assignments").EnumerateArray().ToArray();
        Require(assignments.Length==12&&model.GetProperty("circuit_count").GetInt32()==12&&model.GetProperty("candidate_station_count").GetInt32()==12,"D089 counts");
        var circuits=new HashSet<string>();var stations=new HashSet<int>();double linkSum=0;
        foreach(var assignment in assignments)
        {
            Require(circuits.Add(assignment.GetProperty("circuit_id").GetString()!),"D089 duplicate circuit");
            Require(stations.Add(assignment.GetProperty("candidate_station_index").GetInt32()),"D089 duplicate station");
            var body=assignment.GetProperty("body_length_mm").GetInt32();var links=assignment.GetProperty("paired_manhattan_link_lower_bound_mm").GetDouble();var total=assignment.GetProperty("optimistic_total_lower_bound_mm").GetDouble();
            Require(Math.Abs(body+links-total)<1e-6,"D089 component reconciliation");
            Require(Math.Abs(78000-total-assignment.GetProperty("budget_to_78m_target_mm").GetDouble())<1e-6,"D089 budget reconciliation");
            Require(total>=40000&&total<=80000&&assignment.GetProperty("within_40_80m_at_lower_bound").GetBoolean(),"D089 lower range");
            Require(!assignment.GetProperty("fanout_geometry_published").GetBoolean(),"D089 fanout claim");
            linkSum+=links;
        }
        Require(circuits.Count==12&&stations.Count==12&&stations.SetEquals(Enumerable.Range(1,12)),"D089 independent uniqueness");
        Require(Math.Abs(linkSum-model.GetProperty("total_paired_link_lower_bound_mm").GetDouble())<1e-6,"D089 total link objective");
        var tight=model.GetProperty("tightest_budget_to_78m_target");
        Require(tight.GetProperty("circuit_id").GetString()=="A-C07"&&tight.GetProperty("budget_mm").GetDouble()>3700&&tight.GetProperty("budget_mm").GetDouble()<3800,"D089 tightest circuit");
        Require(model.GetProperty("unique_assigned_station_count").GetInt32()==12&&!model.GetProperty("physical_K2_product_selected").GetBoolean()&&model.GetProperty("current_assigned_physical_port_count").GetInt32()==0&&!model.GetProperty("candidate_assignment_is_installation_authority").GetBoolean(),"D089 claim boundaries");
        Require(File.Exists(Path.Combine(root,"attic_k2_station_assignment_evidence.png")),"D089 image");
    }

    private static void ValidateAtticK2PortLattice088()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_K2_PORT_LATTICE_088"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_k2_port_lattice.json")));
        var model=document.RootElement;var ports=model.GetProperty("candidate_ports").EnumerateArray().ToArray();
        Require(model.GetProperty("port_station_count").GetInt32()==12&&ports.Length==24&&model.GetProperty("candidate_3d_port_count").GetInt32()==24,"D088 counts");
        Require(model.GetProperty("unique_3d_coordinate_count").GetInt32()==24&&model.GetProperty("unique_plan_coordinate_count").GetInt32()==12&&model.GetProperty("paired_supply_return_share_plan_xy_by_design").GetBoolean(),"D088 coordinate semantics");
        var xyz=new HashSet<string>();var plan=new HashSet<string>();var stationYs=new SortedSet<double>();
        foreach(var port in ports)
        {
            var p3=port.GetProperty("building_xyz_mm");var p2=port.GetProperty("plan_xy_mm");
            Require(xyz.Add($"{p3[0]}:{p3[1]}:{p3[2]}"),"D088 duplicate XYZ");
            plan.Add($"{p2[0]}:{p2[1]}");stationYs.Add(p2[1].GetDouble());
            Require(port.GetProperty("route_id").ValueKind==JsonValueKind.Null&&!port.GetProperty("assigned").GetBoolean(),"D088 assignment honesty");
        }
        Require(xyz.Count==24&&plan.Count==12&&stationYs.Count==12,"D088 independently counted coordinates");
        var ys=stationYs.ToArray();Require(ys.Zip(ys.Skip(1)).All(pair=>Math.Abs(pair.Second-pair.First-50)<1e-6),"D088 50mm pitch");
        var bbox=model.GetProperty("service_zone_bbox_building_mm").EnumerateArray().Select(item=>item.GetDouble()).ToArray();
        Require(ys[0]>=bbox[1]&&ys[^1]<=bbox[3]&&Math.Abs(model.GetProperty("loop_station_span_mm").GetDouble()-550)<1e-6,"D088 service fit");
        Require(Math.Abs(model.GetProperty("service_length_margin_each_end_mm").GetDouble()-375)<1e-6&&model.GetProperty("available_depth_exceeds_owner_bend_radius").GetBoolean(),"D088 margins");
        Require(model.GetProperty("assigned_port_count").GetInt32()==0&&!model.GetProperty("route_assignment_published").GetBoolean()&&!model.GetProperty("fanout_pipe_geometry_published").GetBoolean()&&!model.GetProperty("physical_product_selected").GetBoolean(),"D088 claim boundaries");
        Require(File.Exists(Path.Combine(root,"attic_k2_port_lattice_evidence.png")),"D088 image");
    }

    private static void ValidateAtticRoutingBudgetEvidence087()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_EVIDENCE_087"));
        var copy=File.ReadAllBytes(Path.Combine(root,"attic_routing_budgets_d086.json"));
        var source=Path.GetFullPath(Path.Combine(root,"..","HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086","attic_routing_budgets.json"));
        Require(copy.SequenceEqual(File.ReadAllBytes(source)),"D087 source byte identity");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_validation.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_json_byte_identical").GetBoolean()&&model.GetProperty("circuit_row_count").GetInt32()==12,"D087 content");
        Require(model.GetProperty("canvas_width_px").GetInt32()==1650&&model.GetProperty("canvas_height_px").GetInt32()==1460,"D087 canvas");
        Require(model.GetProperty("explanation_separated_from_table").GetBoolean()&&model.GetProperty("all_rows_and_explanations_inside_canvas").GetBoolean(),"D087 layout");
        Require(File.Exists(Path.Combine(root,"attic_routing_budgets_evidence.png")),"D087 image");
    }

    private static void ValidateAtticRoutingBudgets086()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_ROUTING_BUDGETS_086"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_routing_budgets.json")));
        var model=document.RootElement;var circuits=model.GetProperty("circuit_budgets").EnumerateArray().ToArray();
        Require(circuits.Length==12&&model.GetProperty("architecture").GetProperty("attic_circuit_count").GetInt32()==12&&model.GetProperty("architecture").GetProperty("attic_loop_leg_count").GetInt32()==24,"D086 topology count");
        foreach(var circuit in circuits)
        {
            var lower=circuit.GetProperty("optimistic_total_lower_bound_mm").GetDouble();
            Require(lower==circuit.GetProperty("body_length_mm").GetInt32()+circuit.GetProperty("optimistic_supply_link_lower_bound_mm").GetDouble()+circuit.GetProperty("optimistic_return_link_lower_bound_mm").GetDouble()+(circuit.TryGetProperty("optimistic_inter_body_link_lower_bound_mm",out var link)?link.GetDouble():0),"D086 component reconciliation");
            Require(Math.Abs(circuit.GetProperty("detour_budget_to_80m_mm").GetDouble()-(80000-lower))<1e-6,"D086 80m budget");
            Require(Math.Abs(circuit.GetProperty("detour_budget_to_78m_target_mm").GetDouble()-(78000-lower))<1e-6,"D086 78m budget");
            Require(lower>=40000&&lower<=80000&&circuit.GetProperty("within_40_80m_at_lower_bound").GetBoolean(),"D086 lower-bound range");
            Require(!circuit.GetProperty("complete_route_geometry_published").GetBoolean(),"D086 complete-route claim");
        }
        var tight=model.GetProperty("tightest_detour_budget_to_78m_target");
        Require(tight.GetProperty("circuit_id").GetString()=="A-C07"&&tight.GetProperty("budget_mm").GetDouble()>4100&&tight.GetProperty("budget_mm").GetDouble()<4200,"D086 tightest circuit");
        Require(model.GetProperty("all_optimistic_lower_bounds_within_40_80m").GetBoolean()&&model.GetProperty("complete_route_count").GetInt32()==0&&!model.GetProperty("K2_port_geometry_published").GetBoolean(),"D086 claim boundaries");
        Require(File.Exists(Path.Combine(root,"attic_routing_budgets_evidence.png")),"D086 image");
    }

    private static void ValidateAtticC01ManifoldCorridor085()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_C01_MANIFOLD_CORRIDOR_085"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"..","HA_TWO_FLOOR_ATTIC_HALL_REFINED_050","attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var source=sourceDocument.RootElement;var validation=validationDocument.RootElement;
        var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        var sourceRoutes=source.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        Require(routes.Length==13&&model.GetProperty("changed_body_route_ids").EnumerateArray().Single().GetString()=="A-C01","D085 route scope");
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D085 orthogonal nonzero body");
            Require(CountSelfContacts(points)==0,"D085 body self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D085 body length");
            if(id!="A-C01") Require(route.GetProperty("body_points_grid").GetRawText()==sourceRoutes[id].GetProperty("body_points_grid").GetRawText(),"D085 non-C01 body preservation");
        }
        Require(CountInterBodyContacts(routes)==0,"D085 inter-body contacts");
        var c01=routes.Single(route=>route.GetProperty("route_id").GetString()=="A-C01");
        Require(c01.GetProperty("body_envelope_grid").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{49,61,92,81}),"D085 C01 envelope");
        Require(c01.GetProperty("body_length_mm").GetInt32()==45800&&c01.GetProperty("regularity_validation").GetProperty("result").GetString()=="PASS","D085 C01 regularity and length");
        Require(c01.GetProperty("regularity_validation").GetProperty("centre_turn_perpendicular_join_length_mm").GetInt32()==200&&c01.GetProperty("regularity_validation").GetProperty("minimum_segment_length_mm").GetInt32()>=200,"D085 C01 center turn");
        Require(validation.GetProperty("service_zone_contact_count").GetInt32()==0&&validation.GetProperty("minimum_axis_to_service_zone_clearance_mm").GetDouble()>229,"D085 service corridor");
        Require(validation.GetProperty("wardrobe_draft_containment").GetBoolean()&&validation.GetProperty("minimum_centerline_to_draft_boundary_mm").GetDouble()>108,"D085 draft containment");
        Require(validation.GetProperty("optimistic_complete_lower_bound_within_40_80m").GetBoolean()&&validation.GetProperty("optimistic_complete_lower_bound_mm").GetDouble()>47000,"D085 lower bound");
        Require(validation.GetProperty("coverage_ratio_after").GetDouble()>validation.GetProperty("coverage_ratio_before").GetDouble(),"D085 coverage proxy improvement");
        Require(!model.GetProperty("K2_port_geometry_published").GetBoolean()&&model.GetProperty("complete_attic_route_count").GetInt32()==0&&!model.GetProperty("whole_attic_coverage_claimed").GetBoolean(),"D085 claim boundaries");
        Require(File.Exists(Path.Combine(root,"attic_c01_manifold_corridor_overlay.png"))&&File.Exists(Path.Combine(root,"attic_c01_manifold_corridor_pipes_only.png")),"D085 images");
    }

    private static void ValidateAtticHydraulicEvidence084()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HYDRAULIC_EVIDENCE_084"));
        var copied=File.ReadAllBytes(Path.Combine(root,"attic_primary_hydraulic_envelope_d083.json"));
        var source=Path.GetFullPath(Path.Combine(root,"..","HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083","attic_primary_hydraulic_envelope.json"));
        Require(copied.SequenceEqual(File.ReadAllBytes(source)),"D084 source byte identity");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_validation.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_json_byte_identical").GetBoolean()&&model.GetProperty("scenario_row_count").GetInt32()==9&&model.GetProperty("candidate_id_bar_count").GetInt32()==6,"D084 content");
        Require(model.GetProperty("canvas_width_px").GetInt32()==1700&&model.GetProperty("canvas_height_px").GetInt32()==1420&&model.GetProperty("all_table_rows_and_bars_inside_canvas").GetBoolean(),"D084 bounds");
        Require(File.Exists(Path.Combine(root,"attic_primary_hydraulic_evidence.png")),"D084 image");
    }

    private static void ValidateAtticPrimaryHydraulicEnvelope083()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PRIMARY_HYDRAULIC_ENVELOPE_083"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_primary_hydraulic_envelope.json")));
        var model=document.RootElement;
        Require(Math.Abs(model.GetProperty("named_attic_area_m2").GetDouble()-151.5)<1e-6&&model.GetProperty("specific_load_scenarios_w_m2").GetArrayLength()==3&&model.GetProperty("delta_t_scenarios_k").GetArrayLength()==3,"D083 inputs");
        var scenarios=model.GetProperty("hydraulic_scenarios").EnumerateArray().ToArray();
        Require(scenarios.Length==9,"D083 scenarios");
        var baseCase=model.GetProperty("base_screening_scenario");
        Require(Math.Abs(baseCase.GetProperty("power_kw").GetDouble()-9.09)<1e-6&&Math.Abs(baseCase.GetProperty("primary_flow_m3_h").GetDouble()-1.116570446)<1e-6,"D083 base flow");
        var ids=model.GetProperty("base_screening_primary_clear_id_range_mm").EnumerateArray().Select(x=>x.GetDouble()).ToArray();
        Require(ids[0]>23&&ids[0]<25&&ids[1]>28&&ids[1]<29,"D083 base IDs");
        Require(!model.GetProperty("screening_velocity_values_are_normative_limits").GetBoolean()&&!model.GetProperty("design_heat_loss_available").GetBoolean()&&!model.GetProperty("design_delta_t_selected").GetBoolean(),"D083 screening honesty");
        Require(model.GetProperty("loop_flow_records").GetArrayLength()==12&&model.GetProperty("all_loop_screening_flows_within_documented_uponor_0_5_l_min_flowmeter_range").GetBoolean(),"D083 loop flows");
        Require(!model.GetProperty("primary_pipe_outer_diameter_selected").GetBoolean()&&!model.GetProperty("pressure_drop_calculated").GetBoolean()&&!model.GetProperty("pump_head_calculated").GetBoolean(),"D083 selection honesty");
        Require(File.Exists(Path.Combine(root,"attic_primary_hydraulic_envelope.png")),"D083 image");
    }

    private static void ValidateAtticManifoldServiceZone082()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_MANIFOLD_SERVICE_ZONE_082"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_manifold_service_zone.json")));
        var model=document.RootElement;
        Require(model.GetProperty("supersedes_reservation_artifact_id").GetString()=="HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081","D082 source");
        Require(model.GetProperty("service_zone_bbox_building_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{9070,6500,9370,7800}),"D082 bbox");
        Require(model.GetProperty("service_zone_clear_length_mm").GetInt32()==1300&&model.GetProperty("service_zone_clear_depth_mm").GetInt32()==300,"D082 size");
        Require(model.GetProperty("wardrobe_vector_draft_floor_contains_service_zone").GetBoolean()&&model.GetProperty("existing_body_contact_count").GetInt32()==0&&model.GetProperty("minimum_existing_body_centerline_clearance_mm").GetDouble()>29,"D082 containment");
        Require(model.GetProperty("maximum_opening_inside_service_zone").GetBoolean()&&model.GetProperty("source_D081_reservation_inside_revised_service_zone").GetBoolean(),"D082 supersets");
        var evidence=model.GetProperty("product_class_evidence");
        Require(evidence.GetProperty("rehau_documented_port_count").GetInt32()==12&&evidence.GetProperty("rehau_12_port_total_dimension_mm").GetInt32()==862&&evidence.GetProperty("uponor_loop_pitch_mm").GetInt32()==50,"D082 official dimensions");
        Require(model.GetProperty("service_length_margin_over_documented_total_mm").GetInt32()==438,"D082 margin");
        Require(!model.GetProperty("physical_product_selected").GetBoolean()&&!model.GetProperty("cabinet_selected").GetBoolean()&&!model.GetProperty("loop_ports_and_primary_connections_published").GetBoolean(),"D082 selection honesty");
        Require(File.Exists(Path.Combine(root,"attic_manifold_service_zone_evidence.png")),"D082 image");
    }

    private static void ValidateAtticWardrobeManifold081()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_WARDROBE_MANIFOLD_081"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_wardrobe_manifold.json")));
        var model=document.RootElement;
        Require(model.GetProperty("supersedes_direct_26_pipe_topology_artifact_id").GetString()=="HA_TWO_FLOOR_INTERNAL_RISER_3D_080","D081 supersedes direct topology");
        Require(model.GetProperty("superseded_topology_disposition").GetString()!.Contains("EXCEED_80M"),"D081 length reason");
        var architecture=model.GetProperty("selected_architecture");
        Require(architecture.GetProperty("primary_vertical_pipe_count").GetInt32()==2&&architecture.GetProperty("attic_loop_leg_count").GetInt32()==24&&architecture.GetProperty("attic_circuit_count").GetInt32()==12&&architecture.GetProperty("second_manifold_required").GetBoolean(),"D081 architecture");
        var station=model.GetProperty("attic_manifold_reservation");
        Require(station.GetProperty("building_bbox_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{9070,7200,9370,7800}),"D081 K2 bbox");
        Require(station.GetProperty("wardrobe_draft_floor_contains_reservation").GetBoolean()&&station.GetProperty("existing_body_contact_count").GetInt32()==0&&station.GetProperty("minimum_existing_body_clearance_mm").GetDouble()>=29,"D081 K2 location");
        Require(!station.GetProperty("physical_product_selected").GetBoolean()&&station.GetProperty("cabinet_service_clearance_not_evaluated").GetBoolean(),"D081 K2 honesty");
        var circuits=model.GetProperty("attic_circuit_topology").EnumerateArray().ToArray();
        Require(circuits.Length==12&&model.GetProperty("all_optimistic_lower_bounds_40_80m").GetBoolean(),"D081 circuit lower bounds");
        Require(circuits.Count(item=>item.GetProperty("source_body_ids").GetArrayLength()==2)==1&&circuits.Single(item=>item.GetProperty("source_body_ids").GetArrayLength()==2).GetProperty("circuit_id").GetString()=="A-C10_C11_SERIAL","D081 short body merge");
        var range=model.GetProperty("optimistic_lower_bound_range_mm").EnumerateArray().Select(x=>x.GetDouble()).ToArray();
        Require(range[0]>=40000&&range[1]<76000,"D081 range");
        Require(!model.GetProperty("maximum_reserved_opening_is_final_cut_size").GetBoolean()&&model.GetProperty("final_sleeve_or_opening_size").GetString()!.StartsWith("NOT_SELECTED"),"D081 opening honesty");
        Require(model.GetProperty("primary_supply_return_pipe_material_and_size").GetString()!.StartsWith("NOT_SELECTED")&&model.GetProperty("primary_flow_rate").GetString()=="NOT_CALCULATED","D081 hydraulics honesty");
        Require(model.GetProperty("complete_attic_route_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0,"D081 geometry scope");
        Require(File.Exists(Path.Combine(root,"attic_wardrobe_manifold_evidence.png")),"D081 image");
    }

    private static void ValidateInternalRiser3D080()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_INTERNAL_RISER_3D_080"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"internal_riser_3d.json")));
        var model=document.RootElement;
        Require(model.GetProperty("source_strategy_artifact_id").GetString()=="HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079","D080 source strategy");
        Require(model.GetProperty("pipe_count").GetInt32()==26&&model.GetProperty("circuit_candidate_count").GetInt32()==13,"D080 counts");
        Require(model.GetProperty("pipe_od_mm").GetInt32()==16&&model.GetProperty("floor_to_floor_mm").GetInt32()==3000&&model.GetProperty("design_centerline_bend_radius_mm").GetInt32()==80&&!model.GetProperty("heated_radius_reduction_credited").GetBoolean(),"D080 physical inputs");
        Require(model.GetProperty("opening_clear_size_mm").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{160,400})&&model.GetProperty("vertical_axis_grid_shape").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{3,9}),"D080 opening/grid");
        var axes=model.GetProperty("pipe_axes").EnumerateArray().ToArray();
        Require(axes.Length==26&&model.GetProperty("vertical_axis_unique_count").GetInt32()==26,"D080 unique axes");
        var ids=axes.Select(axis=>axis.GetProperty("pipe_id").GetString()).ToArray();
        Require(ids.Distinct().Count()==26,"D080 unique pipe ids");
        foreach(var axis in axes)
        {
            Require(axis.GetProperty("bend_count").GetInt32()==2&&axis.GetProperty("bend_radius_mm").GetInt32()==80,"D080 R80 bends");
            Require(axis.GetProperty("ordered_axis_points_xyz_mm").GetArrayLength()>30&&!axis.GetProperty("complete_circuit").GetBoolean(),"D080 axis geometry scope");
            Require(axis.GetProperty("fixed_transit_length_mm").GetDouble()>7100&&axis.GetProperty("fixed_transit_length_mm").GetDouble()<7120,"D080 fixed length");
        }
        Require(Math.Abs(model.GetProperty("sampled_minimum_center_distance_mm").GetDouble()-40)<0.001&&Math.Abs(model.GetProperty("provisional_minimum_envelope_clear_gap_mm").GetDouble()-12)<0.001,"D080 spacing");
        Require(model.GetProperty("sampled_3d_pair_count").GetInt32()==325&&model.GetProperty("axis_self_contact_count").GetInt32()==0&&model.GetProperty("axis_pair_contact_count").GetInt32()==0,"D080 contacts");
        Require(model.GetProperty("all_vertical_axes_inside_opening_with_provisional_envelope").GetBoolean()&&model.GetProperty("lower_and_upper_R80_are_materialized").GetBoolean(),"D080 local geometry");
        var floorBank=model.GetProperty("floor_service_bank");
        Require(floorBank.GetProperty("required_clear_service_box_width_mm").GetInt32()==400&&floorBank.GetProperty("required_clear_service_box_height_mm").GetInt32()==160&&!floorBank.GetProperty("physical_box_selected_or_measured").GetBoolean()&&!floorBank.GetProperty("inside_floor_screed_claimed").GetBoolean(),"D080 service box honesty");
        Require(!model.GetProperty("floor_1_plan_projection_is_contact_free").GetBoolean()&&model.GetProperty("floor_1_local_reroute_required").GetBoolean(),"D080 floor rework");
        Require(!model.GetProperty("attic_distribution_links_published").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0&&!model.GetProperty("physical_K1_manifold_selected").GetBoolean(),"D080 incomplete scope");
        Require(File.Exists(Path.Combine(root,"internal_riser_3d_evidence.png")),"D080 image");
    }

    private static void ValidateInternalStairWardrobeR1Strategy079()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_INTERNAL_STAIR_WARDROBE_R1_079"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"internal_stair_wardrobe_r1_strategy.json")));
        var model=document.RootElement;
        Require(model.GetProperty("supersedes_artifact_id").GetString()=="HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078","D079 supersedes D078");
        Require(model.GetProperty("superseded_artifact_disposition").GetString()=="REJECTED_BY_OWNER_EXTERNAL_WALL_RISER_NOT_DESIRED","D079 owner disposition");
        var wall=model.GetProperty("shared_stair_wardrobe_partition");
        Require(wall.GetProperty("wall_solids_overlap_on_both_floor_plans").GetBoolean()&&wall.GetProperty("registered_common_wall_core_width_mm").GetDouble()>220&&wall.GetProperty("registered_common_wall_core_width_mm").GetDouble()<221,"D079 common internal wall");
        var penetration=model.GetProperty("selected_penetration");
        Require(penetration.GetProperty("building_bbox_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{9150,7200,9310,7600}),"D079 building bbox");
        Require(penetration.GetProperty("clear_size_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{160,400}),"D079 opening size");
        Require(penetration.GetProperty("same_physical_plan_bbox_on_both_floors").GetBoolean()&&penetration.GetProperty("does_not_cut_registered_common_wall_core").GetBoolean(),"D079 registered opening");
        Require(penetration.GetProperty("attic_wardrobe_draft_floor_contains_opening").GetBoolean()&&!penetration.GetProperty("attic_conservative_stair_void_contact").GetBoolean()&&penetration.GetProperty("attic_conservative_stair_void_clearance_mm").GetDouble()>230,"D079 wardrobe/void");
        Require(Math.Abs(penetration.GetProperty("floor_1_room_finish_face_clearance_mm").GetDouble()-7.566494)<0.001&&Math.Abs(penetration.GetProperty("attic_wardrobe_finish_face_clearance_mm").GetDouble()-66.833333)<0.001,"D079 wall-side clearances");
        Require(model.GetProperty("floor_1_penetration_route_contact_count").GetInt32()==1&&model.GetProperty("floor_1_penetration_route_contacts")[0].GetProperty("route_id").GetString()=="F1-C01","D079 F1 local rework");
        Require(model.GetProperty("attic_body_contact_count").GetInt32()==0&&model.GetProperty("diagnostic_attic_fragment_contact_count").GetInt32()==0,"D079 attic opening contacts");
        var corridor=model.GetProperty("floor_1_service_corridor_reservation");
        Require(!corridor.GetProperty("first_three_treads_contact").GetBoolean()&&!corridor.GetProperty("pipe_centerlines_published").GetBoolean()&&corridor.GetProperty("existing_route_contact_count").GetInt32()>0,"D079 corridor reservation");
        var fanout=model.GetProperty("attic_wardrobe_fanout_reservation");
        Require(fanout.GetProperty("wardrobe_draft_floor_contains_reservation").GetBoolean()&&fanout.GetProperty("requires_local_body_rework").GetBoolean()&&!fanout.GetProperty("second_collector_claimed").GetBoolean(),"D079 wardrobe fanout");
        Require(model.GetProperty("floor_to_floor_height_mm").GetInt32()==3000&&model.GetProperty("pipe_od_mm").GetInt32()==16&&model.GetProperty("design_centerline_bend_radius_mm").GetInt32()==80&&!model.GetProperty("heated_radius_reduction_credited").GetBoolean(),"D079 owner physical inputs");
        Require(model.GetProperty("candidate_vertical_pipe_count").GetInt32()==26&&model.GetProperty("straight_penetration_packing_scenario_fits").GetBoolean(),"D079 straight packing");
        Require(!model.GetProperty("physical_route_geometry_published").GetBoolean()&&model.GetProperty("current_assigned_r1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0,"D079 route honesty");
        Require(File.Exists(Path.Combine(root,"internal_stair_wardrobe_r1_two_floor.png")),"D079 image");
    }

    private static void ValidateWallRegisteredR1Location078()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_WALL_REGISTERED_R1_LOCATION_078"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"wall_registered_r1_location.json")));
        var model=document.RootElement;
        Require(model.GetProperty("supersedes_artifact_id").GetString()=="HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077","D078 supersedes D077");
        Require(model.GetProperty("superseded_artifact_disposition").GetString()=="REJECTED_UNREGISTERED_PDF_PAGE_COORDINATES_NOT_A_COMMON_BUILDING_DATUM","D078 D077 disposition");
        var registration=model.GetProperty("pdf_page_registration");
        var shiftPt=registration.GetProperty("attic_to_floor_1_translation_pt").EnumerateArray().Select(item=>item.GetDouble()).ToArray();
        Require(Math.Abs(shiftPt[0]+10.2)<0.0001&&Math.Abs(shiftPt[1]+8.64)<0.0001,"D078 sheet registration");
        Require(Math.Abs(registration.GetProperty("registration_residual_mm").GetDouble())<0.001,"D078 registration residual");
        var wall=model.GetProperty("common_wall_alignment");
        Require(wall.GetProperty("same_wall_line_on_both_floors").GetBoolean()&&Math.Abs(wall.GetProperty("registered_finish_face_delta_mm").GetDouble())<0.01,"D078 common wall alignment");
        Require(model.GetProperty("clear_penetration_bbox_building_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{18050,7800,18210,8200}),"D078 building bbox");
        Require(model.GetProperty("clear_penetration_size_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{160,400}),"D078 size");
        Require(model.GetProperty("same_physical_plan_bbox_on_both_floors").GetBoolean()&&Math.Abs(model.GetProperty("clear_penetration_east_edge_to_common_finish_face_mm").GetDouble()-27.200775)<0.001,"D078 common-wall offset");
        Require(model.GetProperty("floor_1_boiler_interior_contains_penetration").GetBoolean()&&model.GetProperty("attic_known_right_north_floor_contains_penetration").GetBoolean(),"D078 two-floor containment");
        Require(model.GetProperty("floor_1_route_contact_count").GetInt32()==1&&model.GetProperty("floor_1_route_contacts")[0].GetProperty("route_id").GetString()=="F1-C08","D078 F1 local rework");
        Require(model.GetProperty("attic_body_contact_count").GetInt32()==0&&model.GetProperty("diagnostic_attic_fragment_contact_count").GetInt32()==0,"D078 attic contacts");
        Require(model.GetProperty("candidate_vertical_pipe_count").GetInt32()==26&&model.GetProperty("all_candidate_envelopes_fit_clear_penetration").GetBoolean(),"D078 packing");
        Require(!model.GetProperty("physical_route_geometry_published").GetBoolean()&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0,"D078 route honesty");
        Require(File.Exists(Path.Combine(root,"wall_registered_r1_two_floor.png")),"D078 image");
    }

    private static void ValidatePhysicalR1Location077()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_PHYSICAL_R1_LOCATION_077"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"physical_r1_location.json")));
        var model=document.RootElement;
        Require(model.GetProperty("selected_r1_plan_location").GetBoolean()&&model.GetProperty("selected_clear_penetration_dimensions").GetBoolean(),"D077 selected");
        Require(model.GetProperty("clear_penetration_bbox_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{13120,7800,13280,8200}),"D077 bbox");
        Require(model.GetProperty("clear_penetration_size_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{160,400})&&model.GetProperty("orientation").GetString()=="LONG_SIDE_PARALLEL_TO_WALL_Y_AXIS","D077 size/orientation");
        Require(model.GetProperty("floor_1_boiler_interior_contains_penetration").GetBoolean()&&!model.GetProperty("attic_source_stair_void_contact").GetBoolean()&&!model.GetProperty("attic_conservative_void_contact").GetBoolean(),"D077 containment/void");
        Require(Math.Abs(model.GetProperty("attic_source_stair_void_clearance_mm").GetDouble()-126)<0.001&&Math.Abs(model.GetProperty("attic_conservative_void_clearance_mm").GetDouble()-20)<0.001,"D077 void clearance");
        Require(model.GetProperty("attic_body_contact_count").GetInt32()==0&&Math.Abs(model.GetProperty("attic_minimum_body_clearance_mm").GetDouble()-220)<0.001&&model.GetProperty("diagnostic_attic_fragment_contact_count").GetInt32()==0,"D077 attic clearance");
        Require(model.GetProperty("floor_1_route_contact_count").GetInt32()==1&&model.GetProperty("floor_1_route_contacts")[0].GetProperty("route_id").GetString()=="F1-C11"&&Math.Abs(model.GetProperty("floor_1_route_contacts")[0].GetProperty("intersection_length_mm").GetDouble()-400)<0.001,"D077 F1 conflict");
        Require(model.GetProperty("candidate_vertical_pipe_count").GetInt32()==26&&model.GetProperty("all_candidate_envelopes_fit_clear_penetration").GetBoolean(),"D077 packing");
        Require(model.GetProperty("structural_cutting_approval").GetString()=="REQUIRED_BEFORE_CONSTRUCTION"&&!model.GetProperty("physical_route_geometry_published").GetBoolean(),"D077 construction scope");
        Require(model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_attic_circuit_count").GetInt32()==0,"D077 route honesty");
        Require(File.Exists(Path.Combine(root,"physical_r1_location_two_floor.png")),"D077 image");
    }

    private static void ValidateOwnerBendRadiusEvidence076()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_OWNER_BEND_RADIUS_EVIDENCE_076"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"owner_bend_radius_evidence.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="ALL_THIRTEEN_ATTIC_BODIES_PASS_LOCAL_R80_TANGENT_FIT_ONLY_A_C08_DIAGNOSTIC_JOIN_REWORK","D076 status");
        Require(model.GetProperty("attic_body_pass_count").GetInt32()==13&&model.GetProperty("diagnostic_fragment_pass_count").GetInt32()==6&&model.GetProperty("diagnostic_fragment_rework_count").GetInt32()==1,"D076 counts");
        Require(model.GetProperty("diagnostic_fragment_rework_route_ids").EnumerateArray().Select(item=>item.GetString() ?? "").SequenceEqual(new[]{"A-C08"}),"D076 route");
        var failure=model.GetProperty("A_C08_failing_segment");
        Require(failure.GetProperty("straight_length_mm").GetInt32()==100&&failure.GetProperty("required_tangent_allowance_mm").GetInt32()==160,"D076 failing segment");
        Require(model.GetProperty("A_C09_100mm_segment_status").GetString()=="PASS_ONE_ADJACENT_BEND_REQUIRES_80MM"&&model.GetProperty("A_C10_100mm_segment_status").GetString()=="PASS_ONE_ADJACENT_BEND_REQUIRES_80MM","D076 one-bend segments");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_complete_circuit_count").GetInt32()==0,"D076 geometry honesty");
        Require(File.Exists(Path.Combine(root,"owner_bend_radius_evidence.png")),"D076 image");
    }

    private static void ValidateOwnerBendRadius075()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_OWNER_BEND_RADIUS_AUDIT_075"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"owner_bend_radius_audit.json")));
        var model=document.RootElement;var bodies=model.GetProperty("attic_body_audits").EnumerateArray().ToArray();var fragments=model.GetProperty("diagnostic_fragment_audits").EnumerateArray().ToArray();
        Require(model.GetProperty("pipe_outer_diameter_mm").GetInt32()==16&&model.GetProperty("design_centerline_bend_radius_mm").GetInt32()==80&&!model.GetProperty("heated_radius_reduction_credited").GetBoolean(),"D075 radius contract");
        Require(model.GetProperty("two_bend_segment_minimum_length_mm").GetInt32()==160,"D075 tangent minimum");
        Require(bodies.Length==13&&model.GetProperty("attic_body_pass_count").GetInt32()==13&&model.GetProperty("attic_body_rework_count").GetInt32()==0&&bodies.All(item=>item.GetProperty("failing_segment_count").GetInt32()==0),"D075 body fit");
        Require(fragments.Length==7&&model.GetProperty("diagnostic_fragment_pass_count").GetInt32()==6&&model.GetProperty("diagnostic_fragment_rework_count").GetInt32()==1,"D075 fragment counts");
        Require(model.GetProperty("diagnostic_fragment_rework_route_ids").EnumerateArray().Select(item=>item.GetString() ?? "").SequenceEqual(new[]{"A-C08"}),"D075 fragment IDs");
        Require(fragments.Where(item=>item.GetProperty("failing_segment_count").GetInt32()>0).All(item=>item.GetProperty("failing_segments")[0].GetProperty("straight_length_mm").GetInt32()==100&&item.GetProperty("failing_segments")[0].GetProperty("required_tangent_allowance_mm").GetInt32()==160),"D075 failing segments");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_complete_circuit_count").GetInt32()==0,"D075 geometry honesty");
        Require(File.Exists(Path.Combine(root,"owner_bend_radius_audit.png")),"D075 image");
    }

    private static void ValidateOwnerPhysicalInputs074()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_OWNER_PHYSICAL_INPUTS_074"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"owner_physical_inputs.json")));
        var model=document.RootElement;var owner=model.GetProperty("owner_inputs");var bounds=model.GetProperty("seven_diagnostic_fragment_length_lower_bounds").EnumerateArray().ToArray();
        Require(owner.GetProperty("floor_to_floor_height_mm").GetInt32()==3000&&owner.GetProperty("wall_material").GetString()=="AUTOCLAVED_AERATED_CONCRETE_GASOBETON","D074 height/wall");
        Require(owner.GetProperty("pipe_outer_diameter_mm").GetInt32()==16&&owner.GetProperty("design_minimum_bend_radius_mm").GetInt32()==80&&owner.GetProperty("bend_radius_reference").GetString()=="PIPE_CENTERLINE","D074 pipe/bend");
        Require(owner.GetProperty("heated_bending_radius_reduction_allowed_by_owner").GetBoolean()&&!owner.GetProperty("heated_bending_radius_reduction_credited_in_design").GetBoolean(),"D074 conservative bend");
        Require(model.GetProperty("vertical_length_contract").GetProperty("vertical_supply_and_return_per_circuit_mm").GetInt32()==6000&&model.GetProperty("vertical_length_contract").GetProperty("aggregate_vertical_pipe_length_for_26_candidate_legs_mm").GetInt32()==78000,"D074 vertical lengths");
        Require(bounds.Length==7&&bounds.All(item=>item.GetProperty("known_length_lower_bound_mm").GetInt32()==item.GetProperty("planar_diagnostic_fragment_length_mm").GetInt32()+6000),"D074 lower bounds");
        Require(model.GetProperty("known_lower_bound_40_80_count").GetInt32()==5&&model.GetProperty("known_lower_bound_below_40000_route_ids").EnumerateArray().Select(item=>item.GetString()).SequenceEqual(new[]{"A-C11","A-C10"}),"D074 range state");
        Require(model.GetProperty("bend_contract").GetProperty("minimum_radius_to_od_ratio").GetDouble()==5&&(model.GetProperty("bend_contract").GetProperty("exact_arc_length_reconciliation").GetString() ?? "").StartsWith("NOT_EVALUATED"),"D074 bend scope");
        Require(model.GetProperty("physical_R1_penetration_location").GetString()=="NOT_SELECTED"&&model.GetProperty("physical_R1_penetration_clear_bbox_mm").ValueKind==JsonValueKind.Null,"D074 remaining penetration input");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("new_gate_count").GetInt32()==0&&model.GetProperty("complete_attic_circuit_count").GetInt32()==0,"D074 geometry honesty");
        Require(File.Exists(Path.Combine(root,"owner_physical_inputs_and_length_bounds.png")),"D074 image");
    }

    private static void ValidateAtticPartitionAmbiguity073()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PARTITION_AMBIGUITY_073"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_partition_ambiguity.json")));
        var model=document.RootElement;var axes=model.GetProperty("abstract_capacity_axes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="MATCHED_SPLIT_PATH_INTERVAL_CANDIDATE_CONFLICTING_CONTINUOUS_PATHS_PRESENT_REWORK_PHYSICAL_CONFIRMATION","D073 status");
        Require(model.GetProperty("split_path_records").GetArrayLength()==4&&model.GetProperty("conflicting_continuous_path_records").EnumerateArray().Select(item=>item.GetProperty("pdf_path_id").GetInt32()).SequenceEqual(new[]{579,283}),"D073 source paths");
        Require(model.GetProperty("continuous_paths_cover_complete_interval").GetBoolean()&&!model.GetProperty("physical_opening_confirmed").GetBoolean(),"D073 opening ambiguity");
        Require(axes.Length==4&&model.GetProperty("D050_total_body_contact_count").GetInt32()==0&&model.GetProperty("D011_total_void_contact_count").GetInt32()==0,"D073 body/void contacts");
        Require(model.GetProperty("D058_total_fragment_point_contact_count").GetInt32()==8&&!model.GetProperty("all_capacity_axes_contact_free_against_existing_D058_fragments").GetBoolean(),"D073 fragment contacts");
        Require(axes.All(axis=>axis.GetProperty("D058_fragment_contact_count").GetInt32()==2&&!axis.GetProperty("global_contact_free_routing_candidate").GetBoolean()&&axis.GetProperty("capacity_axis_only").GetBoolean()),"D073 per-axis scope");
        Require(model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D073 route honesty");
        Require(File.Exists(Path.Combine(root,"attic_partition_ambiguity_overlay.png")),"D073 image");
    }

    private static void ValidateAtticPhysicalInputGate072()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PHYSICAL_INPUT_GATE_072"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_physical_input_gate.json")));
        var model=document.RootElement;var state=model.GetProperty("verified_current_state");
        Require(model.GetProperty("status").GetString()=="SAFE_LOCAL_PREPARATION_COMPLETE_BLOCKED_PHYSICAL_R1_SURVEY_STRUCTURE_PRODUCT_AND_HYDRAULICS","D072 status");
        Require(state.GetProperty("floor_1_complete_planar_route_count").GetInt32()==12&&state.GetProperty("attic_regular_body_candidate_count").GetInt32()==13&&state.GetProperty("attic_complete_circuit_count").GetInt32()==0,"D072 geometry state");
        Require(state.GetProperty("current_assigned_physical_R1_gate_count").GetInt32()==0&&state.GetProperty("approved_attic_pipe_geometry_count").GetInt32()==0,"D072 physical state");
        Require(state.GetProperty("opening_candidate_width_mm").GetDouble()>901&&state.GetProperty("unowned_crossing_axis_count").GetInt32()==4,"D072 opening state");
        Require(state.GetProperty("packing_scenario_pipe_count").GetInt32()==26&&state.GetProperty("selected_physical_chase_count").GetInt32()==0,"D072 packing state");
        Require(model.GetProperty("required_input_count").GetInt32()==6&&model.GetProperty("required_external_inputs").GetArrayLength()==6,"D072 input count");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("new_gate_count").GetInt32()==0,"D072 no geometry");
        Require(File.Exists(Path.Combine(root,"attic_physical_input_gate.png")),"D072 image");
    }

    private static void ValidateAtticPartitionOpeningEvidence071()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_EVIDENCE_071"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_partition_opening_evidence.json")));
        var model=document.RootElement;var axes=model.GetProperty("four_unowned_200mm_crossing_axes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="SOURCE_MATCHED_901_7MM_GAP_AND_FOUR_UNOWNED_200MM_CROSSING_AXES_PASS_REWORK_PHYSICAL_INTERFACE","D071 status");
        Require(Math.Abs(model.GetProperty("opening_clear_width_mm").GetDouble()-901.6999138726)<0.001,"D071 width");
        Require(axes.Length==4&&axes.Select(axis=>axis.GetProperty("ordered_points_grid")[0][1].GetInt32()).SequenceEqual(new[]{138,140,142,144}),"D071 axes");
        Require(axes.All(axis=>{var points=axis.GetProperty("ordered_points_grid");return points[0][0].GetInt32()==129&&points[points.GetArrayLength()-1][0].GetInt32()==133;}),"D071 floor-to-floor extent");
        Require(axes.All(axis=>!axis.GetProperty("is_pipe_geometry").GetBoolean()&&!axis.GetProperty("is_R1_gate").GetBoolean()&&axis.GetProperty("body_contact_count").GetInt32()==0&&axis.GetProperty("void_contact_count").GetInt32()==0),"D071 diagnostic only/contact free");
        Require(model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D071 route honesty");
        Require(File.Exists(Path.Combine(root,"attic_partition_opening_evidence_overlay.png")),"D071 overlay");
    }

    private static void ValidateAtticWallStrips070()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_WALL_STRIPS_070"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_sourced_wall_strip_audit.json")));
        var model=document.RootElement;var longRuns=model.GetProperty("longitudinal_rework_legs").EnumerateArray().ToArray();
        Require(model.GetProperty("sourced_strip_count").GetInt32()==3&&model.GetProperty("right_face_path_ids").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{425,910,283}),"D070 strip provenance");
        Require(model.GetProperty("hall_face_provenance").GetProperty("pdf_path_id").GetInt32()==579,"D070 hall face provenance");
        Require(!model.GetProperty("audit_clip_is_source_wall_extent").GetBoolean()&&!model.GetProperty("door_and_threshold_openings_subtracted").GetBoolean(),"D070 scope honesty");
        Require(model.GetProperty("screening_threshold_source").GetString()=="PROJECT_DIAGNOSTIC_INFERENCE_NOT_NORMATIVE_OR_OWNER_RULE","D070 threshold scope");
        Require(longRuns.Length==3&&longRuns.Count(item=>item.GetProperty("route_id").GetString()=="A-C12")==2&&longRuns.Count(item=>item.GetProperty("route_id").GetString()=="A-C13")==1,"D070 longitudinal legs");
        var a13Return=model.GetProperty("A_C13_return_classification");
        Require(a13Return.GetProperty("leg").GetString()=="RETURN"&&a13Return.GetProperty("result").GetString()=="PERPENDICULAR_CROSSING_CANDIDATE_OPENING_AND_STRUCTURE_NOT_RESOLVED","D070 A13 return scope");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0,"D070 geometry honesty");
        Require(File.Exists(Path.Combine(root,"attic_sourced_wall_strips_overlay.png")),"D070 overlay");
    }

    private static void ValidateAtticRiserPackingScope069()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RISER_PACKING_SCOPE_069"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_riser_packing_scenario.json")));
        var model=document.RootElement;var positions=model.GetProperty("scenario_pipe_positions").EnumerateArray().ToArray();
        Require(model.GetProperty("scenario_only").GetBoolean()&&model.GetProperty("assumed_body_candidate_count").GetInt32()==13&&model.GetProperty("assumed_distinct_vertical_pipe_count").GetInt32()==26,"D069 scenario counts");
        Require(model.GetProperty("complete_circuit_count").GetInt32()==0&&model.GetProperty("approved_vertical_pipe_count").GetInt32()==0&&model.GetProperty("selected_chase_count").GetInt32()==0,"D069 physical counts");
        Require(positions.Length==26&&positions.Select(item=>item.GetProperty("center_mm").GetRawText()).Distinct().Count()==26,"D069 unique positions");
        Require(model.GetProperty("assumed_chase_clear_bbox_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{0,0,400,160}),"D069 assumed bbox");
        Require(Math.Abs(model.GetProperty("minimum_center_distance_mm").GetDouble()-40)<0.000001&&Math.Abs(model.GetProperty("minimum_provisional_envelope_clear_gap_mm").GetDouble()-12)<0.000001&&Math.Abs(model.GetProperty("minimum_provisional_envelope_to_assumed_boundary_mm").GetDouble()-26)<0.000001,"D069 spacing");
        Require(model.GetProperty("physical_chase_location").GetString()=="NOT_SELECTED"&&model.GetProperty("physical_chase_clear_dimensions").GetString()=="NOT_MEASURED"&&!model.GetProperty("approved_installation_detail").GetBoolean(),"D069 physical honesty");
        Require(File.Exists(Path.Combine(root,"attic_riser_packing_scenario.png")),"D069 image");
    }

    private static void ValidateAtticPartitionLaneCapacity068()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PARTITION_LANE_CAPACITY_068"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_partition_lane_capacity.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="MATCHED_OPENING_HAS_FOUR_200MM_CENTERLINE_LANES_REWORK_APPROACH_ROUTING_THRESHOLD_AND_PHYSICAL_R1","D068 status");
        Require(model.GetProperty("candidate_100mm_lane_count").GetInt32()==7&&model.GetProperty("required_independent_lane_count").GetInt32()==4,"D068 lane counts");
        Require(model.GetProperty("four_lane_200mm_selection_y_grid").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{138,140,142,144}),"D068 selected lanes");
        Require(model.GetProperty("selected_lane_spacing_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{200,200,200}),"D068 spacing");
        Require(model.GetProperty("selected_lane_minimum_edge_clearance_mm").GetDouble()>140,"D068 edge clearance");
        Require(!model.GetProperty("selected_crossing_x_grid_is_route_geometry").GetBoolean()&&model.GetProperty("selected_lane_ownership").ValueKind==JsonValueKind.Null,"D068 no route ownership");
        Require(model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D068 route honesty");
        foreach(var field in new[]{"approach_corridor_contacts","threshold_floor_ownership","door_leaf_swing_clearance","wall_sleeve_and_firestop","physical_R1_interface_status"}) Require(model.GetProperty(field).GetString()=="NOT_EVALUATED",$"D068 {field}");
        Require(File.Exists(Path.Combine(root,"attic_partition_lane_capacity.png")),"D068 visual evidence");
    }

    private static void ValidateAtticPartitionOpening067()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PARTITION_OPENING_067"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_partition_opening.json")));
        var model=document.RootElement;var opening=model.GetProperty("matched_opening");
        Require(model.GetProperty("status").GetString()=="ONE_MATCHED_PARTITION_FACE_GAP_PASS_REWORK_UPPER_OPENINGS_THRESHOLD_AND_REROUTING","D067 status");
        Require(model.GetProperty("confirmed_matched_opening_count").GetInt32()==1&&opening.GetProperty("source_paths").EnumerateObject().Count()==4,"D067 opening/provenance");
        Require(Math.Abs(opening.GetProperty("opening_clear_width_along_wall_mm").GetDouble()-901.6999138726)<0.001&&Math.Abs(opening.GetProperty("wall_thickness_between_selected_faces_mm").GetDouble()-220.1333333333)<0.001,"D067 opening dimensions");
        Require(opening.GetProperty("status").GetString()=="MATCHED_OPPOSING_VECTOR_FACE_GAP_PASS_THRESHOLD_OWNERSHIP_NOT_EVALUATED"&&opening.GetProperty("threshold_floor_ownership").GetString()=="NOT_EVALUATED","D067 semantic scope");
        Require(opening.GetProperty("pipe_crossing_candidate_status").GetString()=="GEOMETRIC_OPENING_CANDIDATE_OWNER_WALL_CROSSING_PERMISSION_EXISTS_NOT_YET_ROUTED"&&!opening.GetProperty("longitudinal_pipe_run_allowed").GetBoolean(),"D067 crossing scope");
        Require(model.GetProperty("upper_face_gap_status").GetString()=="NOT_MATCHED_ACROSS_OPPOSING_FACES_INTERNAL_PARTITIONS_CHANGE","D067 upper gap honesty");
        Require(model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("physical_R1_interface_status").GetString()=="NOT_EVALUATED","D067 geometry/interface honesty");
        Require(File.Exists(Path.Combine(root,"attic_partition_opening_overlay.png")),"D067 overlay missing");
    }

    private static void ValidateAtticWallTransitAudit066()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_WALL_TRANSIT_AUDIT_066"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        Require(File.ReadAllBytes(Path.Combine(root,"source_D058_geometry.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(sourceRoot,"attic_plan_space_diagnostic.json"))),"D066 D058 geometry changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_wall_transit_audit.json")));
        var model=document.RootElement;var longRuns=model.GetProperty("longitudinal_rework_legs").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="D058_GEOMETRY_PRESERVED_REWORK_LONGITUDINAL_DRAFT_WALL_RUNS_A12_A13","D066 status");
        Require(model.GetProperty("result").GetString()=="FAIL_D058_WALL_TRANSIT_CLASSIFICATION_REWORK_A12_A13_TRANSITS","D066 result");
        Require(model.GetProperty("owner_wall_crossing_permission").GetBoolean()&&model.GetProperty("owner_permission_does_not_authorize_longitudinal_wall_run").GetBoolean(),"D066 owner scope");
        Require(model.GetProperty("wall_band_status").GetString()=="VECTOR_FACE_PAIR_DRAFT_NOT_SURVEYED_OPENINGS_UNRESOLVED"&&!model.GetProperty("door_openings_subtracted").GetBoolean(),"D066 wall scope");
        Require(longRuns.Length==3&&longRuns.All(item=>new[]{"A-C12","A-C13"}.Contains(item.GetProperty("route_id").GetString()!)),"D066 long runs");
        Require(longRuns.Count(item=>item.GetProperty("route_id").GetString()=="A-C12")==2&&longRuns.Count(item=>item.GetProperty("route_id").GetString()=="A-C13")==1,"D066 affected legs");
        Require(model.GetProperty("total_longitudinal_draft_wall_band_length_mm").GetDouble()>14000,"D066 wall length");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0,"D066 geometry/gate honesty");
        Require(File.Exists(Path.Combine(root,"attic_wall_transit_audit_overlay.png")),"D066 overlay missing");
    }

    private static void ValidateAtticRiserPacking065()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RISER_PACKING_065"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_riser_packing.json")));
        var model=document.RootElement;var pipes=model.GetProperty("pipe_positions").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWENTY_SIX_VERTICAL_PIPE_CROSS_SECTION_FITS_ASSUMED_CHASE_REWORK_PRODUCT_BENDS_LOCATION_AND_INTERFACE","D065 status");
        Require(model.GetProperty("attic_circuit_count").GetInt32()==13&&model.GetProperty("distinct_vertical_pipe_count").GetInt32()==26&&!model.GetProperty("shared_pipe_trunk").GetBoolean(),"D065 pipe counts");
        Require(pipes.Length==26&&pipes.Select(item=>item.GetProperty("pipe_id").GetString()).Distinct().Count()==26&&pipes.Select(item=>item.GetProperty("center_mm").GetRawText()).Distinct().Count()==26,"D065 unique pipes");
        Require(model.GetProperty("row_counts").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{9,9,8}),"D065 rows");
        Require(model.GetProperty("chase_clear_internal_bbox_mm").EnumerateArray().Select(item=>item.GetInt32()).SequenceEqual(new[]{0,0,400,160}),"D065 chase bbox");
        Require(model.GetProperty("cross_section_overlap_count").GetInt32()==0&&model.GetProperty("cross_section_containment_pass").GetBoolean(),"D065 packing");
        Require(Math.Abs(model.GetProperty("minimum_center_distance_mm").GetDouble()-40)<0.000001&&Math.Abs(model.GetProperty("minimum_provisional_insulated_envelope_clear_gap_mm").GetDouble()-12)<0.000001&&Math.Abs(model.GetProperty("minimum_provisional_insulated_envelope_to_chase_wall_mm").GetDouble()-26)<0.000001,"D065 spacing");
        Require(!model.GetProperty("assumptions_are_product_selection").GetBoolean()&&!model.GetProperty("approved_installation_detail").GetBoolean(),"D065 assumption honesty");
        foreach(var field in new[]{"bend_radius_and_fanout","firestopping","hydraulics","commercial_manifold_banks","r1_plan_location","floor_penetration_location","physical_r1_interface_status"}) Require((model.GetProperty(field).GetString() ?? "").StartsWith("NOT_"),$"D065 {field}");
        Require(model.GetProperty("vertical_riser_length_mm").ValueKind==JsonValueKind.Null,"D065 vertical length");
        Require(File.Exists(Path.Combine(root,"attic_riser_packing_cross_section.png")),"D065 cross section missing");
    }

    private static void ValidateAtticPlanSpaceProximity064()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_PROXIMITY_064"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        Require(File.ReadAllBytes(Path.Combine(root,"source_D058_geometry.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(sourceRoot,"attic_plan_space_diagnostic.json"))),"D064 D058 geometry changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_plan_space_proximity.json")));
        var model=document.RootElement;var totals=model.GetProperty("totals");
        Require(model.GetProperty("status").GetString()=="D058_GEOMETRY_PRESERVED_ALL_DIAGNOSTIC_TRANSITS_WITHIN_200MM_OF_KNOWN_FLOOR_REWORK_WALL_THRESHOLD_SEMANTICS","D064 status");
        Require(model.GetProperty("classification_records").GetArrayLength()==7&&model.GetProperty("all_diagnostic_transit_within_200mm_of_known_floor_union").GetBoolean(),"D064 records/result");
        var total=totals.GetProperty("total_length_mm").GetDouble();
        var partition=totals.GetProperty("inside_known_floor_union_mm").GetDouble()+totals.GetProperty("outside_union_within_100mm_proximity_mm").GetDouble()+totals.GetProperty("outside_union_between_100_and_200mm_proximity_mm").GetDouble()+totals.GetProperty("beyond_200mm_from_known_floor_union_mm").GetDouble();
        Require(Math.Abs(total-52700)<0.000001&&Math.Abs(total-partition)<0.000001&&Math.Abs(totals.GetProperty("beyond_200mm_from_known_floor_union_mm").GetDouble())<0.000001,"D064 partition");
        Require(model.GetProperty("wall_transit_classification_status").GetString()=="NOT_EVALUATED_PROXIMITY_IS_NOT_WALL_SOLID_PROOF"&&model.GetProperty("threshold_ownership_status").GetString()=="NOT_EVALUATED"&&model.GetProperty("exterior_boundary_side_status").GetString()=="NOT_EVALUATED","D064 semantic honesty");
        Require(!model.GetProperty("geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D064 geometry/gate honesty");
    }

    private static void ValidateAtticAdjacentFloorEvidence063()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_EVIDENCE_063"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062"));
        Require(File.ReadAllBytes(Path.Combine(root,"attic_adjacent_floor_domains_d062.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(sourceRoot,"attic_adjacent_floor_domains.json"))),"D063 D062 bytes changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_validation.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="D062_CONTRACT_PRESERVED_CYRILLIC_VISUAL_EVIDENCE_REPAIRED","D063 status");
        Require(model.GetProperty("unicode_font").GetString()=="Segoe UI"&&model.GetProperty("adjacent_domain_count").GetInt32()==7,"D063 visual contract");
        Require(!model.GetProperty("source_geometry_modified").GetBoolean()&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0,"D063 honesty");
        Require(File.Exists(Path.Combine(root,"attic_adjacent_floor_domains_clean_overlay.png")),"D063 overlay missing");
    }

    private static void ValidateAtticAdjacentFloorDomains062()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_ADJACENT_FLOOR_DOMAINS_062"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_adjacent_floor_domains.json")));
        var model=document.RootElement;var domains=model.GetProperty("adjacent_floor_domains").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="SEVEN_ADJACENT_RECTANGULAR_FLOOR_DOMAINS_VECTOR_DRAFT_PASS_REWORK_THRESHOLDS_WALLS_AND_WHOLE_ATTIC_UNION","D062 status");
        Require(domains.Length==7&&domains.All(item=>item.GetProperty("source_path_records").GetArrayLength()==4),"D062 domains/path provenance");
        Require(domains.All(item=>item.GetProperty("status").GetString()=="VECTOR_FINISH_FACE_RECTANGLE_DRAFT_NOT_SURVEYED"&&!item.GetProperty("door_thresholds_included").GetBoolean()&&!item.GetProperty("wall_solids_included").GetBoolean()),"D062 domain scope");
        Require(!model.GetProperty("known_floor_union_is_complete_whole_attic").GetBoolean()&&model.GetProperty("door_threshold_ownership").GetString()=="NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS"&&model.GetProperty("wall_transit_solids").GetString()=="NOT_SERIALIZED_YET","D062 scope honesty");
        Require(model.GetProperty("body_known_floor_records").GetArrayLength()==13&&model.GetProperty("all_thirteen_bodies_covered_by_known_floor_union").GetBoolean(),"D062 body containment");
        var transits=model.GetProperty("diagnostic_transit_domain_records").EnumerateArray().ToArray();
        Require(transits.Length==7&&transits.All(item=>item.GetProperty("legs").GetArrayLength()==2),"D062 transit records");
        var total=transits.Sum(item=>item.GetProperty("legs").EnumerateArray().Sum(leg=>leg.GetProperty("length_mm").GetDouble()));
        var known=transits.Sum(item=>item.GetProperty("legs").EnumerateArray().Sum(leg=>leg.GetProperty("known_floor_union_length_mm").GetDouble()));
        var unknown=transits.Sum(item=>item.GetProperty("legs").EnumerateArray().Sum(leg=>leg.GetProperty("unknown_wall_threshold_or_untraced_floor_length_mm").GetDouble()));
        Require(Math.Abs(total-model.GetProperty("diagnostic_transit_total_length_mm").GetDouble())<0.000001&&Math.Abs(known-model.GetProperty("diagnostic_transit_known_floor_union_length_mm").GetDouble())<0.000001&&Math.Abs(unknown-model.GetProperty("diagnostic_transit_unknown_wall_threshold_or_untraced_floor_length_mm").GetDouble())<0.000001,"D062 transit sums");
        Require(known>0&&unknown>0&&Math.Abs(total-known-unknown)<0.000001,"D062 transit source partition");
        Require(model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("physical_R1_interface_status").GetString()=="NOT_EVALUATED","D062 pipe/interface honesty");
        Require(File.Exists(Path.Combine(root,"attic_adjacent_floor_domains_overlay.png")),"D062 overlay missing");
    }

    private static void ValidateAtticPlanSpaceDomainRepaired061()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_REPAIRED_061"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        Require(File.ReadAllBytes(Path.Combine(root,"source_D058_geometry.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(sourceRoot,"attic_plan_space_diagnostic.json"))),"D061 D058 geometry changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_plan_space_domain_repair.json")));
        var model=document.RootElement;var endpoints=model.GetProperty("candidate_endpoint_table").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="D058_GEOMETRY_PRESERVED_D059_ENDPOINT_CLASSIFICATION_REPAIRED_REWORK_FULL_ATTIC_DOMAINS_AND_R1_INTERFACE","D061 status");
        Require(model.GetProperty("source_D059_disposition").GetString()=="SUPERSEDED_ENDPOINT_CLASSIFICATION_BUG_RETURN_USED_FIRST_POINT","D061 D059 disposition");
        Require(endpoints.Length==14&&endpoints.Count(item=>item.GetProperty("covered_by_local_D047").GetBoolean())==1,"D061 endpoint counts");
        var covered=endpoints.Single(item=>item.GetProperty("covered_by_local_D047").GetBoolean());
        Require(covered.GetProperty("route_id").GetString()=="A-C13"&&covered.GetProperty("leg").GetString()=="RETURN"&&covered.GetProperty("point_grid")[0].GetInt32()==129&&covered.GetProperty("point_grid")[1].GetInt32()==93,"D061 corrected endpoint");
        Require(model.GetProperty("covered_by_local_D047_endpoint_count").GetInt32()==1&&model.GetProperty("unknown_adjacent_domain_endpoint_count").GetInt32()==13,"D061 stored endpoint classification");
        Require(model.GetProperty("current_D050_body_source").GetProperty("artifact_id").GetString()=="HA_TWO_FLOOR_ATTIC_HALL_REFINED_050","D061 current D050 source");
        Require(model.GetProperty("old_D009_lineage_from_inherited_D050_fields").GetProperty("classification").GetString()=="MISPAIRED_INHERITED_LINEAGE_NOT_CURRENT_D050_SOURCE","D061 old lineage scope");
        Require(!model.GetProperty("fragment_geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0,"D061 geometry/gate honesty");
        Require(model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0&&model.GetProperty("physical_R1_interface_status").GetString()=="NOT_EVALUATED","D061 physical honesty");
    }

    private static void ValidateAtticPlanSpaceEvidence060()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_EVIDENCE_060"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        var copied=File.ReadAllBytes(Path.Combine(root,"source_D058_geometry.json"));
        var source=File.ReadAllBytes(Path.Combine(sourceRoot,"attic_plan_space_diagnostic.json"));
        Require(copied.SequenceEqual(source),"D060 D058 geometry changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_contract.json")));
        var model=document.RootElement;var rows=model.GetProperty("diagnostic_endpoint_table").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="D058_GEOMETRY_PASS_MACHINE_AND_VISUAL_GATE_SEMANTICS_REPAIRED_REWORK_SOURCE_DOMAINS_AND_INTERFACE","D060 status");
        Require(model.GetProperty("historical_D050_planned_R1_mapping_status").GetString()=="SUPERSEDED_NOT_CURRENT_PHYSICAL_INTERFACE","D060 history scope");
        Require(model.GetProperty("current_assigned_R1_gate_count").GetInt32()==0&&model.GetProperty("current_assigned_R1_gate_mapping").GetArrayLength()==0,"D060 current gates");
        Require(rows.Length==7&&rows.All(item=>!item.GetProperty("supply_return_are_current_R1_gates").GetBoolean()),"D060 endpoint table");
        Require(rows.SelectMany(item=>new[]{item.GetProperty("supply_endpoint_grid").GetRawText(),item.GetProperty("return_endpoint_grid").GetRawText()}).Distinct().Count()==14,"D060 unique endpoints");
        Require(model.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0&&model.GetProperty("physical_R1_interface_status").GetString()=="NOT_EVALUATED","D060 physical honesty");
        Require(model.GetProperty("full_attic_floor_union_status").GetString()=="MISSING"&&model.GetProperty("unknown_adjacent_domain_transit_length_mm").GetDouble()>0,"D060 domain honesty");
        Require(File.Exists(Path.Combine(root,"attic_plan_space_evidence_overlay.png"))&&File.Exists(Path.Combine(root,"attic_plan_space_evidence_pipes_only.png")),"D060 visual evidence");
    }

    private static void ValidateAtticPlanSpaceDomainAudit059()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DOMAIN_AUDIT_059"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        var copied=File.ReadAllBytes(Path.Combine(root,"source_D058_geometry.json"));
        var source=File.ReadAllBytes(Path.Combine(sourceRoot,"attic_plan_space_diagnostic.json"));
        Require(copied.SequenceEqual(source),"D059 D058 geometry changed");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_plan_space_domain_audit.json")));
        var model=document.RootElement;var records=model.GetProperty("fragment_domain_records").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="D058_PLANAR_TOPOLOGY_PRESERVED_REWORK_ADJACENT_FLOOR_SOURCE_DOMAINS","D059 status");
        Require(model.GetProperty("result").GetString()=="PASS_SOURCE_SCOPE_CLASSIFICATION_REWORK_ADJACENT_ROOM_POLYGONS_AND_PHYSICAL_R1_INTERFACE","D059 result");
        Require(model.GetProperty("D047_not_claimed_as_whole_attic_floor_union").GetBoolean()&&model.GetProperty("source_D047_scope").GetString()=="LOCAL_CENTRAL_HALL_DRAFT_ONLY","D059 D047 scope");
        Require(!model.GetProperty("fragment_geometry_modified").GetBoolean()&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0,"D059 geometry honesty");
        Require(records.Length==7&&records.All(item=>item.GetProperty("legs").GetArrayLength()==2),"D059 records");
        Require(records.All(item=>item.GetProperty("source_containment_result").GetString()=="PARTIAL_D047_ONLY_REWORK_FULL_ATTIC_FLOOR_UNION"),"D059 partial scope");
        var total=records.Sum(item=>item.GetProperty("transit_length_mm").GetDouble());
        var known=records.Sum(item=>item.GetProperty("known_D047_transit_length_mm").GetDouble());
        var unknown=records.Sum(item=>item.GetProperty("unknown_adjacent_domain_transit_length_mm").GetDouble());
        Require(Math.Abs(total-model.GetProperty("total_transit_length_mm").GetDouble())<0.000001&&Math.Abs(known-model.GetProperty("known_D047_transit_length_mm").GetDouble())<0.000001&&Math.Abs(unknown-model.GetProperty("unknown_adjacent_domain_transit_length_mm").GetDouble())<0.000001,"D059 length sums");
        Require(total>0&&known>0&&unknown>0&&Math.Abs(total-known-unknown)<0.000001,"D059 source partition");
        Require(model.GetProperty("full_attic_floor_union_status").GetString()=="MISSING"&&model.GetProperty("physical_r1_interface_status").GetString()=="NOT_EVALUATED","D059 unresolved sources");
        Require(File.Exists(Path.Combine(root,"attic_plan_space_domain_audit_overlay.png"))&&File.Exists(Path.Combine(root,"attic_plan_space_domain_audit_pipes_only.png")),"D059 visual evidence");
    }

    private static void ValidateAtticPlanSpaceDiagnostic058()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_PLANSPACE_DIAGNOSTIC_058"));
        var bodyRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_plan_space_diagnostic.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var bodyDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(bodyRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var body=bodyDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="SEVEN_PLANAR_FRAGMENT_TOPOLOGY_PASS_REWORK_SOURCE_DOMAINS_AND_PHYSICAL_R1_INTERFACE","D058 status");
        Require(model.GetProperty("result").GetString()=="PASS_PLANAR_NONCONTACT_DIAGNOSTIC_REWORK_PHYSICAL_INTERFACE_FLOOR_DOMAINS_AND_FULL_ROUTING","D058 result");
        Require(!model.GetProperty("diagnostic_geometry_is_approved_pipe").GetBoolean()&&!model.GetProperty("physical_r1_interface_confirmed").GetBoolean()&&!model.GetProperty("slab_penetration_confirmed").GetBoolean(),"D058 physical honesty");
        Require(!model.GetProperty("full_attic_floor_union_available").GetBoolean()&&!model.GetProperty("candidate_adjacent_floor_containment_evaluated").GetBoolean(),"D058 domain honesty");
        var fragments=model.GetProperty("diagnostic_planar_fragments").EnumerateArray().ToArray();
        Require(fragments.Length==7&&validation.GetProperty("diagnostic_fragment_count").GetInt32()==7,"D058 fragment count");
        var endpoints=new HashSet<string>();
        var sourceBodies=body.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        foreach(var route in model.GetProperty("body_routes").EnumerateArray())
            Require(route.GetProperty("body_points_grid").GetRawText()==sourceBodies[route.GetProperty("route_id").GetString()!].GetProperty("body_points_grid").GetRawText(),"D058 body geometry changed");
        foreach(var fragment in fragments)
        {
            Require(!fragment.GetProperty("candidate_endpoints_are_r1_gates").GetBoolean()&&fragment.GetProperty("physical_interface_status").GetString()=="NOT_EVALUATED","D058 endpoint classification");
            Require(fragment.GetProperty("adjacent_floor_domain_containment").GetString()=="NOT_EVALUATED_FULL_ATTIC_FLOOR_UNION_MISSING","D058 containment classification");
            var supply=fragment.GetProperty("candidate_supply_endpoint_grid");var returned=fragment.GetProperty("candidate_return_endpoint_grid");
            Require(endpoints.Add($"{supply[0]}:{supply[1]}")&&endpoints.Add($"{returned[0]}:{returned[1]}"),"D058 duplicate candidate endpoint");
            var points=fragment.GetProperty("ordered_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D058 endpoints");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D058 orthogonal nonzero");
            Require(CountSelfContacts(points)==0,"D058 self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D058 void hit");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==fragment.GetProperty("planar_fragment_length_mm").GetInt32(),"D058 measured length");
            Require(measured==fragment.GetProperty("supply_transit_length_mm").GetInt32()+fragment.GetProperty("heating_body_length_mm").GetInt32()+fragment.GetProperty("return_transit_length_mm").GetInt32(),"D058 component length");
            Require(fragment.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null,"D058 complete length claim");
        }
        Require(endpoints.Count==14,"D058 endpoint count");
        Require(CountInterRouteContacts(fragments)==0,"D058 global candidate contact");
        Require(validation.GetProperty("inter_fragment_contact_count").GetInt32()==0&&validation.GetProperty("foreign_body_contact_count").GetInt32()==0&&validation.GetProperty("structural_void_hit_count").GetInt32()==0,"D058 stored contacts");
        Require(validation.GetProperty("approved_pipe_geometry_count").GetInt32()==0&&validation.GetProperty("complete_circuit_count").GetInt32()==0,"D058 approval honesty");
        Require(File.Exists(Path.Combine(root,"attic_plan_space_diagnostic_overlay.png"))&&File.Exists(Path.Combine(root,"attic_plan_space_diagnostic_pipes_only.png")),"D058 visual evidence");
    }

    private static void ValidateAtticFloorCandidateEvidence057()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_EVIDENCE_057"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056"));
        var copied=File.ReadAllBytes(Path.Combine(root,"attic_floor_candidate_nodes_d056.json"));
        var source=File.ReadAllBytes(Path.Combine(sourceRoot,"attic_floor_candidate_nodes.json"));
        Require(copied.SequenceEqual(source),"D057 D056 bytes changed");
        using var evidenceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_validation.json")));
        var evidence=evidenceDocument.RootElement;
        Require(evidence.GetProperty("status").GetString()=="D056_DATA_PASS_VISUAL_LEGACY_R1_LAYER_REMOVED","D057 status");
        Require(evidence.GetProperty("candidate_node_count").GetInt32()==28&&evidence.GetProperty("assigned_gate_count").GetInt32()==0&&evidence.GetProperty("published_pipe_geometry_count").GetInt32()==0,"D057 counts");
        Require(!evidence.GetProperty("legacy_vertical_r1_bank_rendered").GetBoolean()&&!evidence.GetProperty("candidate_nodes_rendered_as_gates").GetBoolean()&&!evidence.GetProperty("candidate_nodes_rendered_as_pipe").GetBoolean(),"D057 visual classification");
        Require(!evidence.GetProperty("source_geometry_modified").GetBoolean(),"D057 source geometry modification");
        Require(File.Exists(Path.Combine(root,"attic_floor_candidate_nodes_clean_overlay.png"))&&File.Exists(Path.Combine(root,"attic_floor_candidate_nodes_clean_pipes_only.png")),"D057 clean visual evidence");
    }

    private static void ValidateAtticFloorCandidateNodes056()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_FLOOR_CANDIDATE_NODES_056"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_floor_candidate_nodes.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="FLOOR_CONFIRMED_CANDIDATE_NODE_SET_PASS_NO_INTERFACE_OWNERSHIP","D056 status");
        Require(model.GetProperty("result").GetString()=="PASS_VECTOR_DRAFT_CONTAINMENT_REWORK_GATE_ASSIGNMENT_AND_FULL_ROUTING","D056 result");
        Require(model.GetProperty("source_D054_disposition").GetString()=="REWORK_SOURCE_CONTAINED_CANDIDATE_MAPPING_NOT_PROVEN_INTERFACE","D056 D054 disposition");
        var nodes=model.GetProperty("candidate_nodes").EnumerateArray().ToArray();
        Require(nodes.Length==28&&nodes.Select(item=>item.GetProperty("point_grid")[0].GetInt32()).SequenceEqual(Enumerable.Range(101,28))&&nodes.All(item=>item.GetProperty("point_grid")[1].GetInt32()==93),"D056 node ordering");
        Require(nodes.All(item=>item.GetProperty("inside_or_on_vector_draft_floor").GetBoolean()&&!item.GetProperty("conservative_void_contact").GetBoolean()),"D056 containment");
        Require(nodes.All(item=>Math.Abs(item.GetProperty("centerline_distance_to_vector_draft_floor_boundary_mm").GetDouble()-100.0)<0.0000011&&Math.Abs(item.GetProperty("centerline_distance_to_conservative_void_mm").GetDouble()-100.0)<0.0000011),"D056 distances");
        Require(nodes.All(item=>item.GetProperty("route_id").ValueKind==JsonValueKind.Null&&item.GetProperty("leg").ValueKind==JsonValueKind.Null&&!item.GetProperty("assigned_as_gate").GetBoolean()&&!item.GetProperty("published_as_pipe_geometry").GetBoolean()),"D056 no ownership");
        Require(model.GetProperty("candidate_node_count").GetInt32()==28&&model.GetProperty("future_leg_count").GetInt32()==26,"D056 counts");
        Require(model.GetProperty("assigned_gate_count").GetInt32()==0&&model.GetProperty("route_connection_count").GetInt32()==0&&model.GetProperty("published_pipe_geometry_count").GetInt32()==0&&model.GetProperty("full_route_count").GetInt32()==0,"D056 no route materialization");
        foreach(var field in new[]{"r1_interface_status","riser_chase_status","slab_penetration_status","collector_interface_status","wall_crossing_status","threshold_ownership","physical_3d_packing","hydraulics"}) Require(model.GetProperty(field).GetString()=="NOT_EVALUATED",$"D056 {field}");
        Require(validation.GetProperty("void_contact_count").GetInt32()==0&&validation.GetProperty("assigned_gate_count").GetInt32()==0&&validation.GetProperty("published_pipe_geometry_count").GetInt32()==0,"D056 validation");
        Require(File.Exists(Path.Combine(root,"attic_floor_candidate_nodes_overlay.png"))&&File.Exists(Path.Combine(root,"attic_floor_candidate_nodes_pipes_only.png")),"D056 visual evidence");
    }

    private static void ValidateAtticR1SouthCandidates055()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_SOUTH_CANDIDATES_055"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_r1_south_candidates.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="SOUTH_PLANAR_FLOOR_CANDIDATES_PASS_R1_PHYSICAL_CONNECTION_BLOCKED_SOURCE_CONTRACT","D055 status");
        Require(model.GetProperty("source_D054_disposition").GetString()=="HISTORICAL_OVERASSERTIVE_GATE_OWNERSHIP_AND_R1_FACE_NOT_ACCEPTED","D055 D054 disposition");
        var south=model.GetProperty("south_landing_candidate_interface");
        Require(south.GetProperty("r1_physical_connection_status").GetString()=="UNCONFIRMED_NO_SOURCE_EVIDENCE_OF_RISER_TO_SOUTH_LANDING_FANOUT","D055 physical connection status");
        Require(south.GetProperty("gate_ownership_status").GetString()=="UNASSIGNED_SOLVER_MUST_SELECT_22_OF_28","D055 ownership status");
        var candidates=south.GetProperty("candidates").EnumerateArray().ToArray();
        Require(candidates.Length==28,"D055 candidate count");
        Require(candidates.All(item=>item.GetProperty("point_grid")[1].GetInt32()==93),"D055 candidate row");
        Require(candidates.Select(item=>item.GetProperty("point_grid")[0].GetInt32()).SequenceEqual(Enumerable.Range(101,28)),"D055 candidate x order");
        Require(candidates.All(item=>item.GetProperty("inside_or_on_routing_draft_floor").GetBoolean()),"D055 candidate containment");
        Require(candidates.All(item=>item.GetProperty("gate_owner_route_id").ValueKind==JsonValueKind.Null&&item.GetProperty("gate_owner_leg").ValueKind==JsonValueKind.Null&&!item.GetProperty("pipe_geometry_materialized").GetBoolean()),"D055 no ownership/pipe");
        Require(model.GetProperty("new_gate_ownership_count").GetInt32()==0&&model.GetProperty("new_pipe_geometry_count").GetInt32()==0&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D055 no materialization");
        Require(!model.GetProperty("physical_riser_chase_selected").GetBoolean()&&model.GetProperty("physical_3d_fanout_capacity").GetString()=="NOT_EVALUATED","D055 physical honesty");
        Require(validation.GetProperty("candidate_count").GetInt32()==28&&validation.GetProperty("required_candidate_count").GetInt32()==22&&validation.GetProperty("spare_count").GetInt32()==6,"D055 candidate arithmetic");
        Require(File.Exists(Path.Combine(root,"attic_r1_south_candidates_overlay.png"))&&File.Exists(Path.Combine(root,"attic_r1_south_candidates_pipes_only.png")),"D055 visual evidence");
    }

    private static void ValidateAtticR1SplitInterface054()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_SPLIT_INTERFACE_054"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_r1_split_interface.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="SOURCE_CONTAINED_SPLIT_INTERFACE_PASS_REWORK_HALL_BODIES_3D_PACKING_AND_GLOBAL_TRANSITS","D054 status");
        Require(model.GetProperty("historical_vertical_26_gate_bank_status").GetString()=="SUPERSEDED_REWORK_BY_D053_CUT_CAPACITY_FAILURE","D054 supersession");
        var mapping=model.GetProperty("current_split_gate_mapping").EnumerateArray().ToArray();
        var points=mapping.Select(item=>(X:item.GetProperty("gate_point_grid")[0].GetInt32(),Y:item.GetProperty("gate_point_grid")[1].GetInt32())).ToArray();
        Require(mapping.Length==26&&points.Distinct().Count()==26,"D054 distinct gates");
        Require(mapping.Count(item=>item.GetProperty("face").GetString()=="EAST_OF_VOID")==4&&mapping.Count(item=>item.GetProperty("face").GetString()=="SOUTH_OF_VOID")==22,"D054 face counts");
        var south=mapping.Where(item=>item.GetProperty("face").GetString()=="SOUTH_OF_VOID").ToArray();
        Require(south.All(item=>item.GetProperty("gate_point_grid")[1].GetInt32()==93&&item.GetProperty("gate_point_grid")[0].GetInt32()>=101&&item.GetProperty("gate_point_grid")[0].GetInt32()<=122),"D054 south bank coordinates");
        Require(south.All(item=>item.GetProperty("inside_or_on_routing_draft_allowed_floor").GetBoolean()),"D054 south bank containment");
        Require(model.GetProperty("south_transit_ribbon_lane_count").GetInt32()==22&&model.GetProperty("south_transit_ribbon_spacing_mm").GetInt32()==100,"D054 ribbon geometry");
        Require(model.GetProperty("south_ribbon_inside_vector_draft_floor").GetBoolean()&&model.GetProperty("south_ribbon_void_hit_count").GetInt32()==0,"D054 ribbon containment");
        Require(model.GetProperty("hall_body_route_ids_requiring_repartition").EnumerateArray().Select(x=>x.GetString()).SequenceEqual(new[]{"A-C05","A-C06"}),"D054 affected hall bodies");
        Require(!model.GetProperty("new_pipe_geometry_published").GetBoolean()&&model.GetProperty("full_route_count").GetInt32()==0,"D054 route honesty");
        Require(!model.GetProperty("physical_riser_chase_selected").GetBoolean()&&model.GetProperty("physical_3d_fanout_capacity").GetString()=="NOT_EVALUATED","D054 physical honesty");
        Require(validation.GetProperty("new_pipe_geometry_count").GetInt32()==0&&validation.GetProperty("south_gate_containment_pass").GetBoolean(),"D054 validation");
        Require(File.Exists(Path.Combine(root,"attic_r1_split_interface_overlay.png"))&&File.Exists(Path.Combine(root,"attic_r1_split_interface_pipes_only.png")),"D054 visual evidence");
    }

    private static void ValidateAtticR1CorridorAudit053()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_CORRIDOR_AUDIT_053"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_r1_corridor_audit.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_r1_contract.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var source=sourceDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="TWO_LOCAL_FRAGMENTS_PASS_REWORK_GLOBAL_R1_CORRIDOR","D053 status");
        Require(model.GetProperty("source_geometry_preserved").GetBoolean()&&model.GetProperty("source_fragment_count").GetInt32()==source.GetProperty("attic_plane_route_fragments").GetArrayLength(),"D053 source preservation");
        Require(model.GetProperty("source_26_gate_mapping_global_status").GetString()=="REWORK_NOT_EXTENDABLE_WITH_CURRENT_FRAGMENTS","D053 global mapping status");
        Require(model.GetProperty("isolated_gate_count").GetInt32()==3&&model.GetProperty("baseline_corridor_capacity_nodes_per_transverse_cut").GetInt32()==2,"D053 blocker counts");
        Require(model.GetProperty("upper_four_circuit_required_distinct_leg_count").GetInt32()==8&&model.GetProperty("remaining_unbuilt_leg_count").GetInt32()==22,"D053 capacity demand");
        Require(model.GetProperty("complete_circuit_count").GetInt32()==0&&!model.GetProperty("full_attic_route_claimed").GetBoolean(),"D053 route honesty");
        Require(validation.GetProperty("new_pipe_geometry_count").GetInt32()==0&&validation.GetProperty("global_mapping_extendability").GetString()=="FAIL_CURRENT_D052_FRAGMENT_LAYOUT","D053 validation result");

        var bodyNodes=new HashSet<(int X,int Y)>();
        foreach(var route in source.GetProperty("body_routes").EnumerateArray())
        {
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            foreach(var point in ExpandUnitPoints(points)) bodyNodes.Add(point);
        }
        var fragmentNodes=new HashSet<(int X,int Y)>();
        foreach(var route in source.GetProperty("attic_plane_route_fragments").EnumerateArray())
        {
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            foreach(var point in ExpandUnitPoints(points)) fragmentNodes.Add(point);
        }
        var gateNodes=source.GetProperty("planned_R1_gate_mapping").EnumerateArray().Select(item=>(X:item.GetProperty("gate_point_grid")[0].GetInt32(),Y:item.GetProperty("gate_point_grid")[1].GetInt32())).ToHashSet();
        bool InVoid((int X,int Y) point)=>point.X>=99&&point.X<=131&&point.Y>=57&&point.Y<=92;
        foreach(var y in new[]{61,62,63})
        {
            var gate=(X:132,Y:y);var free=0;
            foreach(var delta in new[]{(X:1,Y:0),(X:-1,Y:0),(X:0,Y:1),(X:0,Y:-1)})
            {
                var next=(X:gate.X+delta.X,Y:gate.Y+delta.Y);
                if(!InVoid(next)&&!bodyNodes.Contains(next)&&!fragmentNodes.Contains(next)&&(!gateNodes.Contains(next)||next==gate)) free++;
            }
            Require(free==0,$"D053 gate {y} should be isolated");
        }
        Require(File.Exists(Path.Combine(root,"attic_r1_corridor_blocker_debug.png"))&&File.Exists(Path.Combine(root,"attic_r1_corridor_blocker_overlay.png")),"D053 visual evidence");
    }

    private static void ValidateAtticR1ContractRepaired052()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_CONTRACT_REPAIRED_052"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051"));
        var bodyRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_r1_contract.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_r1_contract.json")));
        using var bodyDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(bodyRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var source=sourceDocument.RootElement;var body=bodyDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="AUTHORITATIVE_R1_MAPPING_AND_TWO_FRAGMENTS_PASS_PROVENANCE_REPAIRED_REWORK_REMAINING_ROUTES","D052 status");
        Require(validation.GetProperty("current_mapping_preserved").GetBoolean()&&model.GetProperty("planned_R1_gate_mapping").GetRawText()==source.GetProperty("planned_R1_gate_mapping").GetRawText(),"D052 current mapping changed");
        Require(validation.GetProperty("fragments_preserved").GetBoolean()&&model.GetProperty("attic_plane_route_fragments").GetRawText()==source.GetProperty("attic_plane_route_fragments").GetRawText(),"D052 fragments changed");
        var currentBodies=model.GetProperty("body_routes").EnumerateArray().Select(route=>route.GetProperty("body_points_grid").GetRawText()).ToArray();
        var sourceBodies=source.GetProperty("body_routes").EnumerateArray().Select(route=>route.GetProperty("body_points_grid").GetRawText()).ToArray();
        Require(validation.GetProperty("body_points_preserved").GetBoolean()&&currentBodies.SequenceEqual(sourceBodies),"D052 body points changed");
        Require(validation.GetProperty("historical_mapping_exact_D050").GetBoolean()&&model.GetProperty("source_planned_R1_gate_mapping").GetRawText()==body.GetProperty("planned_R1_gate_mapping").GetRawText(),"D052 historical mapping false");
        var historical=model.GetProperty("source_planned_R1_gate_mapping").EnumerateArray().ToArray();var current=model.GetProperty("planned_R1_gate_mapping").EnumerateArray().ToArray();
        int[] Pair(JsonElement[] mapping,string id)=>mapping.Where(item=>item.GetProperty("route_id").GetString()==id).Select(item=>item.GetProperty("gate_point_grid")[1].GetInt32()).Order().ToArray();
        Require(Pair(historical,"A-C08").SequenceEqual(new[]{57,58})&&Pair(historical,"A-C09").SequenceEqual(new[]{59,60}),"D052 historical pairs");
        Require(Pair(current,"A-C09").SequenceEqual(new[]{57,58})&&Pair(current,"A-C08").SequenceEqual(new[]{59,60}),"D052 current pairs");
        var numeric=model.GetProperty("boundary_clearance_numeric_contract");
        Require(Math.Abs(numeric.GetProperty("comparison_tolerance_mm").GetDouble()-0.000001)<1e-12&&numeric.GetProperty("comparison_pass").GetBoolean()&&numeric.GetProperty("margin_status").GetString()=="ZERO_DESIGN_MARGIN_VECTOR_DRAFT_NOT_SURVEYED","D052 clearance numeric contract");
        Require(model.GetProperty("complete_circuit_count").GetInt32()==0&&!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean(),"D052 full-route honesty");
        Require(File.Exists(Path.Combine(root,"attic_r1_contract_repaired_overlay.png"))&&File.Exists(Path.Combine(root,"attic_r1_contract_repaired_pipes_only.png")),"D052 visual evidence");
    }

    private static void ValidateAtticR1Contract051()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_R1_CONTRACT_051"));
        var bodyRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_r1_contract.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var bodyDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(bodyRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("status").GetString()=="AUTHORITATIVE_R1_MAPPING_AND_TWO_ATTIC_FRAGMENTS_PASS_REWORK_REMAINING_TRANSITS_AND_COMPLETE_ROUTES","D051 status");
        var bodyRoutes=model.GetProperty("body_routes").EnumerateArray().ToArray();var sourceBodyRoutes=bodyDocument.RootElement.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        Require(bodyRoutes.All(route=>route.GetProperty("body_points_grid").GetRawText()==sourceBodyRoutes[route.GetProperty("route_id").GetString()!].GetProperty("body_points_grid").GetRawText()),"D051 D050 body geometry changed");
        Require(!model.GetProperty("planned_R1_gate_mapping_preserved").GetBoolean()&&model.GetProperty("source_planned_R1_gate_mapping_status").GetString()=="HISTORICAL_SUPERSEDED_FOR_A-C08_A-C09_ONLY","D051 source mapping disposition");
        var mapping=model.GetProperty("planned_R1_gate_mapping").EnumerateArray().ToArray();
        Require(mapping.Length==26&&validation.GetProperty("current_R1_unique_gate_count").GetInt32()==26&&validation.GetProperty("current_R1_gate_set_exact_x132_y57_through_y82").GetBoolean(),"D051 gate count/set");
        var points=mapping.Select(item=>(X:item.GetProperty("gate_point_grid")[0].GetInt32(),Y:item.GetProperty("gate_point_grid")[1].GetInt32())).ToHashSet();
        Require(points.SetEquals(Enumerable.Range(57,26).Select(y=>(X:132,Y:y))),"D051 exact gate set");
        Require(model.GetProperty("planned_R1_gate_order")[0].GetString()=="A-C09"&&model.GetProperty("planned_R1_gate_order")[1].GetString()=="A-C08","D051 far-first order");
        var a09=mapping.Where(item=>item.GetProperty("route_id").GetString()=="A-C09").Select(item=>item.GetProperty("gate_point_grid")[1].GetInt32()).Order().ToArray();
        var a08=mapping.Where(item=>item.GetProperty("route_id").GetString()=="A-C08").Select(item=>item.GetProperty("gate_point_grid")[1].GetInt32()).Order().ToArray();
        Require(a09.SequenceEqual(new[]{57,58})&&a08.SequenceEqual(new[]{59,60}),"D051 current pair ownership");
        Require(model.GetProperty("counterflow_certification_count").GetInt32()==13&&model.GetProperty("counterflow_certifications").EnumerateObject().Count()==13,"D051 certification map");
        Require(model.GetProperty("body_length_range_mm")[0].GetInt32()==14600&&model.GetProperty("body_length_range_mm")[1].GetInt32()==51400,"D051 length range");
        Require(model.GetProperty("body_count_at_least_40000mm").GetInt32()==8&&model.GetProperty("body_count_below_40000mm").GetInt32()==5,"D051 body counts");
        var fragments=model.GetProperty("attic_plane_route_fragments").EnumerateArray().ToArray();
        Require(fragments.Length==2,"D051 fragment count");
        foreach(var fragment in fragments)
        {
            var id=fragment.GetProperty("route_id").GetString()!;
            var currentPair=mapping.Where(item=>item.GetProperty("route_id").GetString()==id).ToDictionary(item=>item.GetProperty("leg").GetString()!);
            Require(fragment.GetProperty("supply_gate_grid").GetRawText()==currentPair["SUPPLY"].GetProperty("gate_point_grid").GetRawText()&&fragment.GetProperty("return_gate_grid").GetRawText()==currentPair["RETURN"].GetProperty("gate_point_grid").GetRawText(),"D051 fragment/mapping mismatch");
            var pointsGrid=fragment.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(pointsGrid)==0,"D051 fragment self contact");
        }
        var adapted=fragments.Select(fragment=>JsonDocument.Parse(JsonSerializer.Serialize(new {ordered_points_grid=fragment.GetProperty("ordered_points_grid")})).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0&&!model.GetProperty("shared_pipe_trunk").GetBoolean(),"D051 fragment intercontact/trunk");
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0&&model.GetProperty("vertical_riser_length_mm").ValueKind==JsonValueKind.Null,"D051 full-route honesty");
        Require(File.Exists(Path.Combine(root,"attic_r1_contract_overlay.png"))&&File.Exists(Path.Combine(root,"attic_r1_contract_pipes_only.png")),"D051 visual evidence");
    }

    private static void ValidateAtticHallRefined050()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_REFINED_050"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        var sourceRoutes=sourceDocument.RootElement.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        var changed=new HashSet<string>(new[]{"A-C05","A-C06"});
        Require(model.GetProperty("status").GetString()=="THIRTEEN_ATTIC_REGULAR_BODIES_AND_DRAFT_CLEARANCE_PASS_REWORK_COVERAGE_AND_FULL_ROUTES","D050 status");
        Require(routes.Length==13&&validation.GetProperty("regular_counterflow_pass_count").GetInt32()==13,"D050 regular count");
        Require(model.GetProperty("preserved_body_route_count").GetInt32()==11&&!model.GetProperty("source_ordered_body_geometry_preserved").GetBoolean(),"D050 lineage scope");
        Require(model.GetProperty("body_length_range_mm")[0].GetInt32()==14600&&model.GetProperty("body_length_range_mm")[1].GetInt32()==51400,"D050 body range");
        Require(model.GetProperty("body_count_at_least_40000mm").GetInt32()==8&&model.GetProperty("body_count_below_40000mm").GetInt32()==5,"D050 body counts");
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D050 self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D050 void hit");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D050 body length");
            var certificate=route.GetProperty("regularity_validation");
            Require(certificate.GetProperty("result").GetString()=="PASS"&&certificate.GetProperty("canonical_points_match_frame_grammar").GetBoolean(),"D050 grammar");
            Require(certificate.GetProperty("centre_turn_perpendicular_join_length_mm").GetInt32()==200&&certificate.GetProperty("centre_turn_join_is_perpendicular").GetBoolean()&&certificate.GetProperty("centre_turn_parallel_terminal_legs").GetBoolean(),"D050 centre turn");
            Require(certificate.GetProperty("unexpected_short_segment_count").GetInt32()==0&&certificate.GetProperty("body_notch_count").GetInt32()==0&&certificate.GetProperty("staircase_pattern_count").GetInt32()==0,"D050 defects");
            if(changed.Contains(id)) Require(route.GetProperty("body_length_mm").GetInt32()==(id=="A-C05"?50200:51400),"D050 transposed length");
            else Require(route.GetProperty("body_points_grid").GetRawText()==sourceRoutes[id].GetProperty("body_points_grid").GetRawText(),"D050 preserved body changed");
        }
        var adapted=routes.Select(route=>JsonDocument.Parse(JsonSerializer.Serialize(new {ordered_points_grid=route.GetProperty("body_points_grid")})).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0&&validation.GetProperty("inter_body_contact_count").GetInt32()==0,"D050 inter contact");
        var clearance=model.GetProperty("draft_boundary_clearance_validation");
        Require(clearance.GetProperty("all_at_least_100mm").GetBoolean()&&Math.Abs(clearance.GetProperty("minimum_clearance_mm").GetDouble()-100)<0.000001,"D050 draft clearance");
        Require(clearance.GetProperty("pipe_surface_clearance").GetString()=="NOT_EVALUATED_PIPE_OD_NOT_SUPPLIED","D050 surface-clearance honesty");
        var coverage=model.GetProperty("hall_coverage_diagnostic");
        Require(Math.Abs(coverage.GetProperty("served_area_m2").GetDouble()-29.720261)<0.000001&&Math.Abs(coverage.GetProperty("unresolved_area_m2").GetDouble()-6.154013)<0.000001,"D050 coverage arithmetic");
        Require(!coverage.GetProperty("full_coverage_claimed").GetBoolean()&&!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean(),"D050 honesty");
        Require(File.Exists(Path.Combine(root,"attic_hall_refined_overlay.png"))&&File.Exists(Path.Combine(root,"attic_hall_refined_pipes_only.png")),"D050 visual evidence");
    }

    private static void ValidateAtticRightR1Fragments049()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RIGHT_R1_FRAGMENTS_049"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_right_r1_fragments.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var fragments=model.GetProperty("attic_plane_route_fragments").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWO_ATTIC_R1_TO_BODY_TO_R1_FRAGMENTS_PASS_REWORK_REMAINING_TRANSITS_AND_COMPLETE_ROUTES","D049 status");
        Require(fragments.Length==2&&validation.GetProperty("distinct_gate_count").GetInt32()==4&&validation.GetProperty("distinct_transit_count").GetInt32()==4,"D049 scope");
        Require(model.GetProperty("source_body_geometry_preserved").GetBoolean()&&model.GetProperty("body_routes").GetRawText()==sourceDocument.RootElement.GetProperty("body_routes").GetRawText(),"D049 source body preservation");
        var gates=new HashSet<string>();
        foreach(var fragment in fragments)
        {
            var id=fragment.GetProperty("route_id").GetString()!;
            Require(id is "A-C08" or "A-C09","D049 route identity");
            var supply=fragment.GetProperty("supply_gate_grid");var returned=fragment.GetProperty("return_gate_grid");
            Require(gates.Add($"{supply[0]}:{supply[1]}")&&gates.Add($"{returned[0]}:{returned[1]}"),"D049 duplicate gate");
            var points=fragment.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D049 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D049 orthogonal nonzero fragment");
            Require(CountSelfContacts(points)==0,"D049 self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D049 structural void hit");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==fragment.GetProperty("planar_fragment_length_mm").GetInt32(),"D049 measured fragment length");
            Require(measured==fragment.GetProperty("supply_transit_length_mm").GetInt32()+fragment.GetProperty("heating_body_length_mm").GetInt32()+fragment.GetProperty("return_transit_length_mm").GetInt32(),"D049 component reconciliation");
            Require(measured==(id=="A-C09"?49300:41700),"D049 expected fragment length");
            Require(fragment.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null&&fragment.GetProperty("complete_40_80m_validation").GetString()=="NOT_EVALUATED_VERTICAL_AND_K1_LEGS_MISSING","D049 complete length honesty");
        }
        var adapted=fragments.Select(fragment=>JsonDocument.Parse(JsonSerializer.Serialize(new {ordered_points_grid=fragment.GetProperty("ordered_points_grid")})).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0&&validation.GetProperty("inter_fragment_contact_count").GetInt32()==0,"D049 inter-fragment contact");
        Require(!model.GetProperty("shared_pipe_trunk").GetBoolean()&&!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D049 full-route honesty");
        Require(File.Exists(Path.Combine(root,"attic_right_r1_fragments_overlay.png"))&&File.Exists(Path.Combine(root,"attic_right_r1_fragments_pipes_only.png"))&&File.Exists(Path.Combine(root,"attic_right_r1_fragments_debug.png")),"D049 visual evidence");
    }

    private static void ValidateAtticHallCounterflows048()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_COUNTERFLOWS_048"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_COUNTERFLOW_EVIDENCE_044"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        var sourceRoutes=sourceDocument.RootElement.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        var rebuilt=new HashSet<string>(new[]{"A-C05","A-C06","A-C07"});
        Require(model.GetProperty("status").GetString()=="THIRTEEN_ATTIC_REGULAR_BODY_GEOMETRIES_PASS_REWORK_COVERAGE_AND_FULL_ROUTES","D048 bounded status");
        Require(routes.Length==13&&validation.GetProperty("regular_counterflow_pass_count").GetInt32()==13,"D048 regular body count");
        Require(validation.GetProperty("all_centre_turn_joins_200mm").GetBoolean()&&validation.GetProperty("all_centre_turn_terminal_legs_parallel").GetBoolean(),"D048 centre-turn derivation");
        Require(validation.GetProperty("all_rebuilt_hall_body_points_inside_D047_draft").GetBoolean(),"D048 hall containment");
        Require(validation.GetProperty("planned_R1_gate_count").GetInt32()==26&&validation.GetProperty("planned_R1_unique_gate_count").GetInt32()==26,"D048 R1 gates");
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D048 orthogonal nonzero body");
            Require(CountSelfContacts(points)==0,"D048 body self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D048 structural void hit");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D048 body length");
            var certificate=route.GetProperty("regularity_validation");
            Require(certificate.GetProperty("result").GetString()=="PASS"&&certificate.GetProperty("canonical_points_match_frame_grammar").GetBoolean(),"D048 grammar certificate");
            Require(certificate.GetProperty("centre_turn_perpendicular_join_length_mm").GetInt32()==200&&certificate.GetProperty("centre_turn_join_is_perpendicular").GetBoolean()&&certificate.GetProperty("centre_turn_parallel_terminal_legs").GetBoolean(),"D048 centre hairpin geometry");
            Require(certificate.GetProperty("unexpected_short_segment_count").GetInt32()==0&&certificate.GetProperty("body_notch_count").GetInt32()==0&&certificate.GetProperty("staircase_pattern_count").GetInt32()==0,"D048 regularity defect");
            Require(route.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null&&route.GetProperty("complete_40_80m_validation").GetString()=="NOT_EVALUATED","D048 complete length honesty");
            if(rebuilt.Contains(id)) Require(route.GetProperty("body_length_mm").GetInt32()==(id=="A-C05"?48400:id=="A-C06"?49400:47200),"D048 rebuilt hall length");
            else Require(route.GetProperty("body_points_grid").GetRawText()==sourceRoutes[id].GetProperty("body_points_grid").GetRawText(),"D048 preserved body changed");
        }
        var adapted=routes.Select(route=>JsonDocument.Parse(JsonSerializer.Serialize(new {ordered_points_grid=route.GetProperty("body_points_grid")})).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0&&validation.GetProperty("inter_body_contact_count").GetInt32()==0,"D048 inter-body contacts");
        var coverage=model.GetProperty("hall_coverage_diagnostic");
        Require(!coverage.GetProperty("full_coverage_claimed").GetBoolean()&&coverage.GetProperty("result").GetString()=="REWORK_COVERAGE_AND_THRESHOLD_OWNERSHIP","D048 coverage honesty");
        Require(Math.Abs(coverage.GetProperty("allowed_area_m2").GetDouble()-35.874274)<0.000001&&Math.Abs(coverage.GetProperty("served_area_m2").GetDouble()-28.960261)<0.000001,"D048 coverage arithmetic");
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D048 full-route honesty");
        Require(File.Exists(Path.Combine(root,"attic_hall_counterflows_overlay.png"))&&File.Exists(Path.Combine(root,"attic_hall_counterflows_pipes_only.png"))&&File.Exists(Path.Combine(root,"attic_hall_three_bodies_debug.png")),"D048 visual evidence");
    }

    private static void ValidateAtticHallExactVectorContract047()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_EXACT_VECTOR_CONTRACT_047"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_hall_exact_vector_contract.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var hall=model.GetProperty("hall_source_contract");
        Require(model.GetProperty("status").GetString()=="VECTOR_HALL_SOURCE_AND_FINISH_FACE_DRAFT_PASS_REWORK_THRESHOLDS_AND_COVERAGE","D047 status");
        Require(model.GetProperty("source_pdf_sha256").GetString()=="B66D169ED5B1FDEFF12B817FC887226376740A34592C777EE3FE5AA40967075D","D047 PDF digest");
        Require(validation.GetProperty("source_path_count").GetInt32()==10&&validation.GetProperty("source_path_585_present").GetBoolean(),"D047 vector path evidence");
        Require(validation.GetProperty("maximum_selected_face_delta_pt").GetDouble()<0.001,"D047 selected finish faces");
        Require(Math.Abs(hall.GetProperty("wall_axis_gross_area_m2").GetDouble()-39.856551)<0.000001,"D047 wall-axis area");
        Require(Math.Abs(hall.GetProperty("finish_face_gross_area_m2").GetDouble()-39.531480)<0.000001,"D047 finish area");
        Require(Math.Abs(hall.GetProperty("structural_void_area_inside_finish_polygon_m2").GetDouble()-3.657206)<0.000001,"D047 void area");
        Require(Math.Abs(hall.GetProperty("routing_draft_allowed_floor_area_m2").GetDouble()-35.874274)<0.000001,"D047 allowed area");
        Require(hall.GetProperty("routing_draft_geometry_valid").GetBoolean()&&hall.GetProperty("routing_draft_connected_component_count").GetInt32()==1,"D047 allowed geometry");
        Require(hall.GetProperty("door_threshold_ownership").GetString()=="NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS"&&hall.GetProperty("survey_status").GetString()=="VECTOR_TRACED_DRAFT_NOT_SURVEYED","D047 uncertainty honesty");
        Require(!hall.GetProperty("pipe_clearance_erosion_applied").GetBoolean()&&!model.GetProperty("coverage_claimed").GetBoolean()&&!model.GetProperty("full_routes_claimed").GetBoolean(),"D047 no clearance/coverage/route claim");
        Require(validation.GetProperty("new_body_count").GetInt32()==0&&validation.GetProperty("full_route_count").GetInt32()==0,"D047 route-free source contract");
        Require(File.Exists(Path.Combine(root,"attic_hall_exact_vector_overlay.png")),"D047 overlay missing");
    }

    private static void ValidateAtticHallVectorContract046()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_046"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_hall_vector_contract.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var hall=model.GetProperty("hall_candidate");
        Require(model.GetProperty("status").GetString()=="CORRECTED_VECTOR_HALL_WITH_FULL_VOID_SUBTRACTION_READY_FOR_VISUAL_REVIEW","D046 status");
        Require(model.GetProperty("rejected_D045_finding").GetProperty("D045_status").GetString()=="REJECTED_FALSE_AREA_RECONCILIATION","D046 D045 rejection");
        Require(validation.GetProperty("D045_rejected").GetBoolean()&&hall.GetProperty("full_structural_void_subtracted").GetBoolean(),"D046 void subtraction");
        Require(Math.Abs(hall.GetProperty("gross_shell_area_m2").GetDouble()-50.960392)<0.000001,"D046 gross shell area");
        Require(Math.Abs(hall.GetProperty("structural_void_area_inside_shell_m2").GetDouble()-11.179140)<0.000001,"D046 void area");
        Require(Math.Abs(hall.GetProperty("allowed_floor_area_m2").GetDouble()-39.781252)<0.000001,"D046 allowed area");
        Require(Math.Abs(hall.GetProperty("allowed_area_delta_percent").GetDouble())<1,"D046 area reconciliation");
        Require(hall.GetProperty("allowed_geometry_valid").GetBoolean()&&hall.GetProperty("hole_count").GetInt32()==0,"D046 geometry");
        Require(hall.GetProperty("threshold_semantics").GetString()=="NOT_RESOLVED_FLATTENED_VECTOR_PDF"&&hall.GetProperty("survey_status").GetString()=="VECTOR_CANDIDATE_NOT_SURVEYED","D046 uncertainty honesty");
        Require(model.GetProperty("routing_decision").GetProperty("complete_circuit_count_selected").ValueKind==JsonValueKind.Null&&!model.GetProperty("coverage_claimed").GetBoolean()&&!model.GetProperty("full_routes_claimed").GetBoolean(),"D046 no route/coverage claim");
        Require(validation.GetProperty("new_route_count").GetInt32()==0&&File.Exists(Path.Combine(root,"attic_hall_vector_overlay.png")),"D046 evidence");
    }

    private static void ValidateAtticHallVectorContract045()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_HALL_VECTOR_CONTRACT_045"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_hall_vector_contract.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var hall=model.GetProperty("hall_candidate");
        Require(model.GetProperty("status").GetString()=="VECTOR_HALL_CANDIDATE_READY_FOR_VISUAL_REVIEW_REWORK_THRESHOLDS_AND_COVERAGE","D045 status");
        Require(model.GetProperty("source_pdf_sha256").GetString()=="B66D169ED5B1FDEFF12B817FC887226376740A34592C777EE3FE5AA40967075D","D045 PDF digest");
        Require(hall.GetProperty("polygon_valid").GetBoolean()&&hall.GetProperty("polygon_vertex_count").GetInt32()==8,"D045 polygon");
        Require(Math.Abs(hall.GetProperty("candidate_area_m2").GetDouble()-39.900153)<0.000001,"D045 candidate area");
        Require(Math.Abs(hall.GetProperty("printed_area_m2").GetDouble()-39.9)<0.000001&&Math.Abs(hall.GetProperty("area_delta_percent").GetDouble())<1,"D045 area reconciliation");
        Require(hall.GetProperty("structural_void_is_separate_hard_exclusion").GetBoolean(),"D045 structural void");
        Require(hall.GetProperty("threshold_semantics").GetString()=="NOT_RESOLVED_FLATTENED_VECTOR_PDF"&&hall.GetProperty("survey_status").GetString()=="VECTOR_CANDIDATE_NOT_SURVEYED","D045 uncertainty honesty");
        var routing=model.GetProperty("routing_decision");
        Require(routing.GetProperty("old_hall_body_ids").GetArrayLength()==3&&routing.GetProperty("independent_rectangular_replacement_rejected").GetBoolean(),"D045 hall disposition");
        Require(routing.GetProperty("complete_circuit_count_selected").ValueKind==JsonValueKind.Null&&!routing.GetProperty("new_body_generation_started").GetBoolean(),"D045 no route claim");
        Require(!model.GetProperty("coverage_claimed").GetBoolean()&&!model.GetProperty("full_routes_claimed").GetBoolean(),"D045 coverage/route honesty");
        Require(validation.GetProperty("new_route_count").GetInt32()==0&&File.Exists(Path.Combine(root,"attic_hall_vector_overlay.png")),"D045 evidence");
    }

    private static void ValidateAtticCounterflowEvidence044()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_COUNTERFLOW_EVIDENCE_044"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RECTANGULAR_COUNTERFLOWS_043"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var source=sourceDocument.RootElement;
        var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();var sourceRoutes=source.GetProperty("body_routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TEN_ATTIC_COUNTERFLOW_BODY_GEOMETRIES_CERTIFIED_REWORK_HALL_AND_FULL_ROUTES","D044 status");
        Require(routes.Select(route=>route.GetProperty("body_points_grid").GetRawText()).SequenceEqual(sourceRoutes.Select(route=>route.GetProperty("body_points_grid").GetRawText())),"D044 body geometry changed");
        Require(validation.GetProperty("counterflow_certification_count").GetInt32()==10&&validation.GetProperty("counterflow_all_exact_grammar_match").GetBoolean(),"D044 grammar match");
        Require(validation.GetProperty("counterflow_all_centre_turns_two_segments").GetBoolean(),"D044 centre turn count");
        Require(validation.GetProperty("counterflow_unexpected_short_segment_count").GetInt32()==0&&validation.GetProperty("counterflow_body_notch_count").GetInt32()==0&&validation.GetProperty("counterflow_staircase_pattern_count").GetInt32()==0,"D044 regularity defects");
        Require(validation.GetProperty("rendered_noncanonical_pipe_like_bbox_segment_count").GetInt32()==0,"D044 renderer added bbox pipe");
        foreach(var route in routes.Where(route=>route.GetProperty("owner_style_validation").GetProperty("result").GetString()=="PASS"))
        {
            var certificate=route.GetProperty("regularity_validation");
            Require(certificate.GetProperty("validation_method").GetString()=="EXACT_CANONICAL_MATCH_TO_DETERMINISTIC_OPEN_RECTANGULAR_FRAME_GRAMMAR","D044 validation method");
            Require(certificate.GetProperty("canonical_points_match_frame_grammar").GetBoolean()&&certificate.GetProperty("open_frame_entry_exit_gaps_are_intentional").GetBoolean(),"D044 open frame grammar");
            Require(certificate.GetProperty("renderer_must_not_close_open_frame_gaps").GetBoolean(),"D044 renderer gap rule");
            Require(certificate.GetProperty("centre_turn_segment_count").GetInt32()==2&&certificate.GetProperty("minimum_segment_length_mm").GetInt32()>=200,"D044 centre/min segment");
        }
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D044 full-route claim");
        Require(File.Exists(Path.Combine(root,"attic_counterflow_overlay.png"))&&File.Exists(Path.Combine(root,"attic_counterflow_pipes_only.png")),"D044 PNG evidence");
    }

    private static void ValidateAtticRectangularCounterflows043()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RECTANGULAR_COUNTERFLOWS_043"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        var sourceRoutes=sourceDocument.RootElement.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        Require(model.GetProperty("status").GetString()=="TEN_ATTIC_RECTANGULAR_COUNTERFLOW_BODIES_PASS_REWORK_HALL_AND_FULL_ROUTES","D043 status");
        Require(routes.Length==13&&validation.GetProperty("regular_counterflow_pass_count").GetInt32()==10&&validation.GetProperty("owner_style_rework_count").GetInt32()==3,"D043 scope");
        var expectedRegular=new HashSet<string>(new[]{"A-C01","A-C02","A-C03","A-C04","A-C08","A-C09","A-C10","A-C11","A-C12","A-C13"});
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D043 self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D043 structural void contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D043 body length");
            if(expectedRegular.Contains(id))
            {
                Require(route.GetProperty("body_topology").GetString()=="REGULAR_RECTANGULAR_COUNTERFLOW","D043 counterflow type");
                var regularity=route.GetProperty("regularity_validation");
                Require(regularity.GetProperty("result").GetString()=="PASS","D043 regularity");
                Require(regularity.GetProperty("inward_frame_inset_mm").GetInt32()==400&&regularity.GetProperty("outward_interleave_offset_mm").GetInt32()==200,"D043 frame spacing");
                Require(regularity.GetProperty("centre_turn_segment_count").GetInt32()<=3&&regularity.GetProperty("unexpected_short_segment_count").GetInt32()==0,"D043 centre/short segment");
                Require(regularity.GetProperty("body_notch_count").GetInt32()==0&&regularity.GetProperty("staircase_pattern_count").GetInt32()==0&&regularity.GetProperty("meander_endcap_count").GetInt32()==0,"D043 body defects");
            }
            else Require(route.GetProperty("body_points_grid").GetRawText()==sourceRoutes[id].GetProperty("body_points_grid").GetRawText(),"D043 hall body changed");
            Require(route.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null,"D043 total length claim");
        }
        var adapted=routes.Select(route=>JsonDocument.Parse(JsonSerializer.Serialize(new { ordered_points_grid=route.GetProperty("body_points_grid") })).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0,"D043 inter-body contacts");
        Require(validation.GetProperty("planned_R1_gate_count").GetInt32()==26&&validation.GetProperty("planned_R1_unique_gate_count").GetInt32()==26,"D043 R1 gates");
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D043 full-route claim");
        Require(File.Exists(Path.Combine(root,"attic_rectangular_counterflows_overlay.png"))&&File.Exists(Path.Combine(root,"attic_rectangular_counterflows_pipes_only.png")),"D043 PNG evidence");
    }

    private static void ValidateAtticRightCounterflow042()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_RIGHT_COUNTERFLOW_042"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"attic_body_baseline.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;
        var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        var sourceRoutes=sourceDocument.RootElement.GetProperty("body_routes").EnumerateArray().ToDictionary(route=>route.GetProperty("route_id").GetString()!);
        Require(model.GetProperty("status").GetString()=="TWO_RIGHT_ATTIC_COUNTERFLOW_BODIES_PASS_REWORK_REMAINING_BODIES_AND_FULL_ROUTES","D042 status");
        Require(routes.Length==13&&validation.GetProperty("changed_route_ids").GetArrayLength()==2&&validation.GetProperty("preserved_route_count").GetInt32()==11,"D042 scope");
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D042 self contact");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D042 structural void contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D042 body length");
            Require(route.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null&&route.GetProperty("complete_40_80m_validation").GetString()=="NOT_EVALUATED","D042 full-route honesty");
            if(id is "A-C08" or "A-C09")
            {
                Require(route.GetProperty("body_topology").GetString()=="REGULAR_RECTANGULAR_COUNTERFLOW","D042 counterflow type");
                var regularity=route.GetProperty("regularity_validation");
                Require(regularity.GetProperty("result").GetString()=="PASS","D042 regularity");
                Require(regularity.GetProperty("inward_frame_inset_mm").GetInt32()==400&&regularity.GetProperty("outward_interleave_offset_mm").GetInt32()==200,"D042 frame spacing");
                Require(regularity.GetProperty("centre_turn_segment_count").GetInt32()<=3&&regularity.GetProperty("unexpected_short_segment_count").GetInt32()==0,"D042 centre/short segment");
                Require(regularity.GetProperty("body_notch_count").GetInt32()==0&&regularity.GetProperty("staircase_pattern_count").GetInt32()==0&&regularity.GetProperty("meander_endcap_count").GetInt32()==0,"D042 body defects");
            }
            else Require(route.GetProperty("body_points_grid").GetRawText()==sourceRoutes[id].GetProperty("body_points_grid").GetRawText(),"D042 unrelated body changed");
        }
        var adapted=routes.Select(route=>JsonDocument.Parse(JsonSerializer.Serialize(new { ordered_points_grid=route.GetProperty("body_points_grid") })).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0,"D042 inter-body contacts");
        Require(validation.GetProperty("planned_R1_gate_count").GetInt32()==26&&validation.GetProperty("planned_R1_unique_gate_count").GetInt32()==26,"D042 R1 gates");
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D042 full-route claim");
        Require(File.Exists(Path.Combine(root,"attic_right_counterflow_overlay.png"))&&File.Exists(Path.Combine(root,"attic_right_counterflow_pipes_only.png")),"D042 PNG evidence");
    }

    private static void ValidateAtticBodyBaseline041()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_ATTIC_BODY_BASELINE_041"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"attic_body_baseline.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("body_routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="THIRTEEN_ATTIC_BODY_CANDIDATES_PASS_REWORK_FULL_TRANSITS_AND_OWNER_STYLE","D041 status");
        Require(routes.Length==13&&validation.GetProperty("body_route_count").GetInt32()==13,"D041 body count");
        foreach(var route in routes)
        {
            var points=route.GetProperty("body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D041 body self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("body_length_mm").GetInt32(),"D041 body length");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(99,57,131,92)),"D041 structural void contact");
            Require(route.GetProperty("complete_circuit_total_length_mm").ValueKind==JsonValueKind.Null&&route.GetProperty("complete_40_80m_validation").GetString()=="NOT_EVALUATED","D041 full-route honesty");
        }
        var adapted=routes.Select(route=>JsonDocument.Parse(JsonSerializer.Serialize(new { ordered_points_grid=route.GetProperty("body_points_grid") })).RootElement.Clone()).ToArray();
        Require(CountInterRouteContacts(adapted)==0,"D041 inter-body contacts");
        Require(validation.GetProperty("body_count_below_40000mm").GetInt32()==7,"D041 below40 body count");
        Require(validation.GetProperty("planned_R1_gate_count").GetInt32()==26&&validation.GetProperty("planned_R1_unique_gate_count").GetInt32()==26,"D041 R1 gates");
        Require(!model.GetProperty("full_collector_to_collector_routes_claimed").GetBoolean()&&model.GetProperty("complete_circuit_count").GetInt32()==0,"D041 full-route claim");
        Require(File.Exists(Path.Combine(root,"attic_body_baseline_overlay.png"))&&File.Exists(Path.Combine(root,"attic_body_baseline_pipes_only.png")),"D041 PNG evidence");
    }

    private static void ValidateFloor1C06Evidence040()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_C06_EVIDENCE_040"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"canonical_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var source=sourceDocument.RootElement;
        var routes=model.GetProperty("routes").EnumerateArray().ToArray();var sourceRoutes=source.GetProperty("routes").EnumerateArray().ToArray();
        Require(routes.Length==12&&routes.Select(r=>r.GetProperty("ordered_points_grid").GetRawText()).SequenceEqual(sourceRoutes.Select(r=>r.GetProperty("ordered_points_grid").GetRawText())),"D040 route geometry preserved");
        Require(validation.GetProperty("result").GetString()=="PASS_D039_GEOMETRY_AND_CORRECTED_C06_EVIDENCE","D040 result");
        Require(Math.Abs(validation.GetProperty("C06_bypass_to_tread_box_centerline_mm").GetDouble()-632.455532)<0.000001,"D040 bypass clearance");
        Require(validation.GetProperty("C06_whole_route_to_tread_box_centerline_mm").GetInt32()==200,"D040 whole C06 clearance");
        Require(validation.GetProperty("C06_outward_frames_grid").GetArrayLength()==2,"D040 outward frame count");
        Require(validation.GetProperty("C06_outward_frames_grid")[1].EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{113,84,119,90}),"D040 second outward frame");
        Require(validation.GetProperty("C06_entry_transition_mm").GetInt32()==200&&!validation.GetProperty("full_coverage_claimed").GetBoolean(),"D040 transition/coverage honesty");
        Require(File.Exists(Path.Combine(root,"floor_1_c06_geometry_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_c06_geometry_pipes_only.png")),"D040 evidence files");
    }

    private static void ValidateFloor1C06NorthStair039()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_C06_NORTH_STAIR_039"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"canonical_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var sourceRoutes=sourceDocument.RootElement.GetProperty("routes").EnumerateArray().ToDictionary(r=>r.GetProperty("route_id").GetString()!);
        var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_C06_NORTH_STAIR_LOBE_PASS_REWORK_POLYGON_COVERAGE","D039 status");
        var ports=new HashSet<string>();
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D039 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D039 length");
            if(id!="F1-C06") Require(route.GetProperty("ordered_points_grid").GetRawText()==sourceRoutes[id].GetProperty("ordered_points_grid").GetRawText(),"D039 non-C06 route preservation");
            ports.Add($"{points[0].X}:{points[0].Y}");ports.Add($"{points[^1].X}:{points[^1].Y}");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D039 tread contact");
        }
        Require(ports.Count==24&&CountInterRouteContacts(routes)==0,"D039 ports/global contacts");
        var c06=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C06");
        Require(c06.GetProperty("total_length_mm").GetInt32()==74400,"D039 C06 length");
        var c06Evidence=validation.GetProperty("C06");
        Require(c06Evidence.GetProperty("C06_north_stair_bbox_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{107,78,125,96}),"D039 lobe bbox");
        Require(c06Evidence.GetProperty("C06_north_stair_entry_transition_mm").GetInt32()==200,"D039 lobe transition");
        var northLobe=c06.GetProperty("lobe_territories").EnumerateArray().Single(lobe=>lobe.GetProperty("lobe_id").GetString()=="C06-NORTH-STAIR");
        Require(northLobe.GetProperty("regularity").GetProperty("unexpected_short_segment_count").GetInt32()==0,"D039 no short segment");
        Require(northLobe.GetProperty("regularity").GetProperty("result").GetString()=="PASS_COMPUTED_FROM_FINAL_LOBE","D039 lobe regularity");
        var gateOrder=validation.GetProperty("west_gate_order");
        Require(!gateOrder.GetProperty("whole_field_spacing_claimed").GetBoolean()&&gateOrder.GetProperty("scope").GetString()=="WEST_K1_GATE_AND_TRANSIT_CENTERLINE_ORDER_ONLY","D039 gate-order scope");
        Require(validation.GetProperty("collector_unused_reserved_gate_count").GetInt32()==2,"D039 unused gate cleanup");
        var coverage=validation.GetProperty("coverage");
        Require(Math.Abs(coverage.GetProperty("served_ratio_percent").GetDouble()-92.0441)<0.0001,"D039 coverage ratio");
        Require(Math.Abs(coverage.GetProperty("unresolved_area_m2").GetDouble()-2.327663)<0.000001&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D039 coverage honesty");
        Require(File.Exists(Path.Combine(root,"floor_1_c06_north_stair_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_c06_north_stair_pipes_only.png")),"D039 PNG evidence");
    }

    private static void ValidateFloor1FieldLadder038()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_FIELD_LADDER_038"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"canonical_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var sourceRoutes=sourceDocument.RootElement.GetProperty("routes").EnumerateArray().ToDictionary(r=>r.GetProperty("route_id").GetString()!);
        var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_CONTINUOUS_FIELD_LADDER_PASS_REWORK_POLYGON_COVERAGE","D038 status");
        var expected=new Dictionary<string,((int X,int Y) S,(int X,int Y) R,int Length)>{{"F1-C05",((129,70),(129,72),51600)},{"F1-C06",((129,74),(129,76),72600)},{"F1-C14",((129,80),(129,78),78200)}};
        var ports=new HashSet<string>();
        foreach(var route in routes)
        {
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D038 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D038 length");
            var id=route.GetProperty("route_id").GetString()!;
            if(expected.TryGetValue(id,out var item))
            {
                Require(points[0]==item.S&&points[^1]==item.R&&measured==item.Length,"D038 reassigned endpoints");
                var sourceBody=sourceRoutes[id].GetProperty("heating_body_points_grid").GetRawText();
                Require(route.GetProperty("heating_body_points_grid").GetRawText()==sourceBody,"D038 heating body preserved");
            }
            ports.Add($"{points[0].X}:{points[0].Y}");ports.Add($"{points[^1].X}:{points[^1].Y}");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D038 tread contact");
        }
        Require(ports.Count==24,"D038 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D038 global contacts");
        var spacing=validation.GetProperty("spacing_validation");
        Require(spacing.GetProperty("ordered_y_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{56,57,58,60,62,64,66,68,70,72,74,76,78,80}),"D038 field ladder");
        Require(spacing.GetProperty("adjacent_delta_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{1,1,2,2,2,2,2,2,2,2,2,2,2}),"D038 field deltas");
        Require(spacing.GetProperty("result").GetString()=="PASS","D038 spacing result");
        var coverage=validation.GetProperty("coverage");
        Require(Math.Abs(coverage.GetProperty("served_ratio_percent").GetDouble()-90.8136)<0.0001,"D038 coverage ratio");
        Require(Math.Abs(coverage.GetProperty("unresolved_area_m2").GetDouble()-2.687663)<0.000001&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D038 coverage honesty");
        Require(File.Exists(Path.Combine(root,"floor_1_field_ladder_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_field_ladder_pipes_only.png")),"D038 PNG evidence");
    }

    private static void ValidateFloor1WallClearance037()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_WALL_CLEARANCE_037"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"canonical_geometry.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var source=sourceDocument.RootElement;
        var routes=model.GetProperty("routes").EnumerateArray().ToArray();var sourceRoutes=source.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="GEOMETRY_AND_NORTH_BANK_SPACING_PASS_REWORK_HALL_COVERAGE","D037 status");
        Require(routes.Length==12&&sourceRoutes.Length==12,"D037 route count");
        for(var index=0;index<routes.Length;index++)
        {
            var route=routes[index];var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            var sourcePoints=sourceRoutes[index].GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points.SequenceEqual(sourcePoints),"D037 D035 geometry preservation");
            Require(CountSelfContacts(points)==0,"D037 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D037 length");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D037 tread contact");
        }
        Require(CountInterRouteContacts(routes)==0,"D037 global contacts");
        Require(validation.GetProperty("route_geometry_preserved").GetBoolean(),"D037 stored geometry preservation");
        Require(validation.GetProperty("port_coordinate_count").GetInt32()==24,"D037 unique ports");
        var wall=validation.GetProperty("wall_clearance");
        Require(wall.GetProperty("source_path_id").GetInt32()==18,"D037 wall path provenance");
        Require(Math.Abs(wall.GetProperty("wall_finish_face_pdf_y_pt").GetDouble()-153.24)<0.000001,"D037 finish face");
        Require(wall.GetProperty("required_centerline_clearance_mm").GetInt32()==100,"D037 required clearance");
        Require(wall.GetProperty("first_valid_grid_node_mm").GetInt32()==5600,"D037 first valid node");
        Require(Math.Abs(wall.GetProperty("actual_centerline_clearance_mm").GetDouble()-194.033333)<0.00001,"D037 actual clearance");
        Require(wall.GetProperty("rejected_y55_clearance_mm").GetDouble()<100&&wall.GetProperty("rejected_y55_result").GetString()=="FAIL_BELOW_100MM","D037 negative y55 proof");
        var spacing=validation.GetProperty("spacing_validation");
        Require(spacing.GetProperty("ordered_y_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{56,57,58,60,62,64,66,68}),"D037 spacing lines");
        Require(spacing.GetProperty("adjacent_delta_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{1,1,2,2,2,2,2}),"D037 spacing deltas");
        var hall=validation.GetProperty("hall_coverage");
        Require(Math.Abs(hall.GetProperty("hall_served_ratio_percent").GetDouble()-89.0321)<0.0001&&!hall.GetProperty("full_coverage_claimed").GetBoolean(),"D037 hall coverage honesty");
        var landing=validation.GetProperty("north_entry_landing");
        Require(!landing.GetProperty("is_separate_room_claimed").GetBoolean(),"D037 landing room claim");
        Require(Math.Abs(landing.GetProperty("finish_face_domain_served_ratio_percent").GetDouble()-90.859)<0.0001,"D037 landing full-domain coverage");
        Require(Math.Abs(landing.GetProperty("routable_domain_served_ratio_percent").GetDouble()-100)<0.0001,"D037 landing routable coverage");
        Require(File.Exists(Path.Combine(root,"floor_1_wall_clearance_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_wall_clearance_pipes_only.png")),"D037 PNG evidence");
    }

    private static void ValidateFloor1ExteriorFirstGrid036()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_EXTERIOR_FIRST_GRID_036"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_FIRST_GRID_EXTERIOR_THREE_PASS_PASS_REWORK_ROOM_POLYGONS","D036 status");
        var expected=new Dictionary<string,((int X,int Y) S,(int X,int Y) R,int Length)>{{"F1-C01",((129,56),(129,55),73500)},{"F1-C02",((129,59),(129,57),70400)},{"F1-C03",((129,63),(129,61),65800)},{"F1-C04",((129,67),(129,65),68600)}};
        foreach(var route in routes)
        {
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D036 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D036 measured length");
            var id=route.GetProperty("route_id").GetString()!;
            if(expected.TryGetValue(id,out var item)) Require(points[0]==item.S&&points[^1]==item.R&&measured==item.Length,"D036 reassigned route");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D036 tread contact");
        }
        Require(CountInterRouteContacts(routes)==0,"D036 global contacts");
        var spacing=validation.GetProperty("spacing_validation");
        Require(spacing.GetProperty("ordered_y_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{55,56,57,59,61,63,65,67}),"D036 ordered spacing lines");
        Require(spacing.GetProperty("adjacent_delta_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{1,1,2,2,2,2,2}),"D036 spacing deltas");
        Require(Math.Abs(spacing.GetProperty("centerline_wall_clearance_mm").GetDouble()-106.666667)<0.00001,"D036 wall clearance");
        Require(spacing.GetProperty("exterior_three_pass_count").GetInt32()==3&&spacing.GetProperty("result").GetString()=="PASS","D036 spacing result");
        var coverage=model.GetProperty("hall_coverage_diagnostic");
        Require(Math.Abs(coverage.GetProperty("served_ratio_percent").GetDouble()-89.1354)<0.0001&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D036 coverage/honesty");
        Require(coverage.GetProperty("room_semantics").GetString()=="REWORK_SEPARATE_ROOM_3_03_FROM_HALL_30_7","D036 room semantics");
        Require(File.Exists(Path.Combine(root,"floor_1_north_transit_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_north_transit_pipes_only.png")),"D036 visual evidence");
    }

    private static void ValidateFloor1ExteriorThreePass035()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_EXTERIOR_THREE_PASS_035"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_EXTERIOR_THREE_PASS_PASS_REWORK_EXACT_COVERAGE","D035 status");
        var expected=new Dictionary<string,((int X,int Y) S,(int X,int Y) R,int Length)>{{"F1-C01",((129,57),(129,56),73300)},{"F1-C02",((129,60),(129,58),70200)},{"F1-C03",((129,64),(129,62),65600)},{"F1-C04",((129,68),(129,66),68400)}};
        foreach(var route in routes)
        {
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D035 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D035 measured length");
            var id=route.GetProperty("route_id").GetString()!;
            if(expected.TryGetValue(id,out var item)) Require(points[0]==item.S&&points[^1]==item.R&&measured==item.Length,"D035 reassigned route");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D035 tread contact");
        }
        Require(CountInterRouteContacts(routes)==0,"D035 global contacts");
        var spacing=validation.GetProperty("spacing_validation");
        Require(spacing.GetProperty("ordered_y_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{56,57,58,60,62,64,66,68}),"D035 ordered spacing lines");
        Require(spacing.GetProperty("adjacent_delta_grid").EnumerateArray().Select(x=>x.GetInt32()).SequenceEqual(new[]{1,1,2,2,2,2,2}),"D035 exhaustive spacing deltas");
        Require(spacing.GetProperty("exterior_three_pass_count").GetInt32()==3&&spacing.GetProperty("result").GetString()=="PASS","D035 three-pass status");
        var coverage=model.GetProperty("hall_coverage_diagnostic");
        Require(Math.Abs(coverage.GetProperty("served_ratio_percent").GetDouble()-89.0321)<0.0001&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D035 coverage evidence/honesty");
        Require(coverage.GetProperty("C07_decision").GetString()=="DO_NOT_ADD","D035 C07");
        Require(File.Exists(Path.Combine(root,"floor_1_north_transit_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_north_transit_pipes_only.png")),"D035 visual evidence");
    }

    private static void ValidateFloor1NorthTransitBank034()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_NORTH_TRANSIT_BANK_034"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_PASS_NORTH_TRANSIT_REBALANCED_REWORK_EXACT_COVERAGE","D034 status");
        Require(routes.Length==12&&validation.GetProperty("global_inter_route_contact_count").GetInt32()==0,"D034 route/contact count");
        Require(validation.GetProperty("first_three_tread_hit_count").GetInt32()==0&&validation.GetProperty("all_lengths_40_80m").GetBoolean(),"D034 exclusion/length status");
        var expected=new Dictionary<string,((int X,int Y) S,(int X,int Y) R,int Length)>{{"F1-C01",((129,57),(129,56),73300)},{"F1-C02",((129,59),(129,58),70300)},{"F1-C03",((129,61),(129,60),66100)},{"F1-C04",((129,63),(129,62),69300)}};
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D034 duplicate port ID");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D034 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D034 endpoint ownership");
            Require(CountSelfContacts(points)==0,"D034 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D034 measured length");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D034 component reconciliation");
            var id=route.GetProperty("route_id").GetString()!;
            if(expected.TryGetValue(id,out var item)) Require(points[0]==item.S&&points[^1]==item.R&&measured==item.Length,"D034 reassigned route");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D034 tread contact");
        }
        Require(ids.Count==24&&coords.Count==24&&CountInterRouteContacts(routes)==0,"D034 global topology");
        var collector=model.GetProperty("collector_contract");
        Require(collector.GetProperty("north_transit_bank_reassignment").GetProperty("distinct_gate_count").GetInt32()==8,"D034 gate count");
        Require(!collector.GetProperty("north_transit_bank_reassignment").GetProperty("shared_segments").GetBoolean()&&!collector.GetProperty("north_transit_bank_reassignment").GetProperty("lane_swaps").GetBoolean(),"D034 bank integrity");
        var coverage=model.GetProperty("hall_coverage_diagnostic");
        Require(coverage.GetProperty("served_area_gain_m2").GetDouble()>0.63&&coverage.GetProperty("C07_decision").GetString()=="DO_NOT_ADD","D034 coverage gain/C07");
        Require(!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D034 coverage honesty");
        Require(File.Exists(Path.Combine(root,"floor_1_north_transit_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_north_transit_pipes_only.png")),"D034 visual evidence");
    }

    private static void ValidateFloor1HallLPolygonCoverage033()
    {
        var proposalRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals"));
        var sourceRoot=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029");
        var root=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_HALL_L_POLYGON_COVERAGE_033");
        Require(File.ReadAllBytes(Path.Combine(sourceRoot,"canonical_geometry.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(root,"canonical_geometry_d029.json"))),"D033 must preserve D029 canonical bytes");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"hall_l_polygon_coverage.json")));
        var coverage=document.RootElement;
        Require(!coverage.GetProperty("route_geometry_modified").GetBoolean()&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D033 geometry/coverage honesty");
        Require(Math.Abs(coverage.GetProperty("hall_gross_area_m2").GetDouble()-30.443075)<0.00001,"D033 L polygon gross area");
        Require(Math.Abs(coverage.GetProperty("allowed_area_m2").GetDouble()-29.256967)<0.00001,"D033 allowed area");
        Require(Math.Abs(coverage.GetProperty("served_area_m2").GetDouble()-24.145777)<0.00001,"D033 served area");
        Require(Math.Abs(coverage.GetProperty("unresolved_area_m2").GetDouble()-5.111189)<0.00001,"D033 unresolved area");
        Require(coverage.GetProperty("distance_model").GetString()=="TRUE_ROUND_EUCLIDEAN_BUFFER_100MM","D033 distance model");
        Require(coverage.GetProperty("material_unresolved_component_count").GetInt32()==9,"D033 material components");
        Require(coverage.GetProperty("micro_corner_component_count").GetInt32()==39,"D033 micro components");
        Require(coverage.GetProperty("threshold_ownership").GetString()=="NOT_EVALUATED_FLATTENED_PDF_AMBIGUOUS","D033 threshold honesty");
        Require(coverage.GetProperty("C07_decision").GetString()!.StartsWith("DO_NOT_ADD"),"D033 C07 decision");
        Require(File.Exists(Path.Combine(root,"floor_1_hall_l_polygon_coverage.png")),"D033 visual evidence");
    }

    private static void ValidateFloor1HallVectorCoverage032()
    {
        var proposalRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals"));
        var sourceRoot=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029");
        var root=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_HALL_VECTOR_COVERAGE_032");
        Require(File.ReadAllBytes(Path.Combine(sourceRoot,"canonical_geometry.json")).SequenceEqual(File.ReadAllBytes(Path.Combine(root,"canonical_geometry_d029.json"))),"D032 must preserve D029 canonical bytes");
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"hall_vector_coverage.json")));
        var coverage=document.RootElement;
        Require(!coverage.GetProperty("route_geometry_modified").GetBoolean()&&!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D032 geometry/coverage honesty");
        Require(Math.Abs(coverage.GetProperty("draft_allowed_area_m2").GetDouble()-31.711739)<0.00001,"D032 draft area");
        Require(Math.Abs(coverage.GetProperty("served_area_m2").GetDouble()-26.548873)<0.00001,"D032 served area");
        Require(Math.Abs(coverage.GetProperty("unresolved_area_m2").GetDouble()-5.162866)<0.00001,"D032 unresolved area");
        Require(coverage.GetProperty("largest_unresolved_components").GetArrayLength()==10,"D032 unresolved components");
        Require(!coverage.GetProperty("exterior_wall_100mm_band_evaluated").GetBoolean(),"D032 exterior-band honesty");
        Require(coverage.GetProperty("C07_decision").GetString()=="DO_NOT_ADD_FROM_DRAFT_RECTANGLE_ALONE","D032 C07 gate");
        Require(File.Exists(Path.Combine(root,"floor_1_hall_vector_coverage.png")),"D032 visual evidence");
    }

    private static void ValidateFloor1NorthHallEvidence031()
    {
        var proposalRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals"));
        var sourceRoot=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029");
        var root=Path.Combine(proposalRoot,"HA_TWO_FLOOR_FLOOR1_NORTH_HALL_EVIDENCE_031");
        var sourceBytes=File.ReadAllBytes(Path.Combine(sourceRoot,"canonical_geometry.json"));
        var copiedBytes=File.ReadAllBytes(Path.Combine(root,"canonical_geometry_d029.json"));
        Require(sourceBytes.SequenceEqual(copiedBytes),"D031 must preserve D029 canonical bytes");
        using var sourceDocument=JsonDocument.Parse(sourceBytes);
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"evidence_validation.json")));
        var model=sourceDocument.RootElement;var validation=validationDocument.RootElement;
        Require(model.GetProperty("artifact_id").GetString()=="HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029","D031 source identity");
        Require(validation.GetProperty("source_geometry_copied_byte_identical").GetBoolean()&&!validation.GetProperty("route_geometry_modified").GetBoolean(),"D031 source preservation status");
        Require(validation.GetProperty("route_count").GetInt32()==12,"D031 route count");
        Require(validation.GetProperty("C06_total_length_mm").GetInt32()==72500,"D031 C06 label value");
        var clearance=validation.GetProperty("clearance_evidence");
        Require(Math.Abs(clearance.GetProperty("whole_c06_mm").GetDouble()-200.0)<0.001,"D031 whole C06 clearance");
        Require(Math.Abs(clearance.GetProperty("bypass_mm").GetDouble()-538.5164807134504)<0.001,"D031 bypass clearance");
        Require(clearance.GetProperty("vertical_x105_mm").GetDouble()==800.0,"D031 vertical clearance");
        Require(clearance.GetProperty("pipe_surface_clearance").GetString()=="NOT_EVALUATED_PIPE_OD_NOT_SUPPLIED","D031 surface-clearance honesty");
        Require(validation.GetProperty("coverage_status").GetString()=="REWORK_EXACT_POLYGON_UNION_AND_EXTERIOR_BAND","D031 coverage honesty");
        foreach(var name in new[]{"floor_1_north_hall_overlay.png","floor_1_north_hall_pipes_only.png","floor_1_c06_three_lobe_debug.png"})
            Require(File.Exists(Path.Combine(root,name))&&new FileInfo(Path.Combine(root,name)).Length>10000,$"D031 missing {name}");
    }

    private static void ValidateFloor1NorthHall029()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_NORTH_HALL_029"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_NORTH_HALL_BODY_PASS_REWORK_POLYGON_COVERAGE","D029 status");
        Require(routes.Length==12&&!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D029 route count/coverage honesty");
        var c06=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C06");
        Require(c06.GetProperty("topology").GetString()=="COMPOSITE_THREE_LOBE_COUNTERFLOW"&&c06.GetProperty("lobe_count").GetInt32()==3,"D029 C06 topology");
        Require(c06.GetProperty("total_length_mm").GetInt32()==72500,"D029 C06 length");
        Require(c06.GetProperty("supply_transit_length_mm").GetInt32()==9900&&c06.GetProperty("heating_body_length_mm").GetInt32()==57800&&c06.GetProperty("return_transit_length_mm").GetInt32()==4800,"D029 C06 parts");
        var semantic=c06.GetProperty("semantic_route_parts").EnumerateArray().ToArray();
        Require(semantic.Length==5,"D029 semantic part count");
        Require(semantic.Select(part=>part.GetProperty("role").GetString()).SequenceEqual(new[]{"SOUTH_COUNTERFLOW_LOBE","TERRITORY_TRANSITION","NORTH_COUNTERFLOW_LOBE","STAIR_EXCLUSION_BYPASS_TRANSITION","NORTH_STAIR_COUNTERFLOW_LOBE"}),"D029 semantic order");
        Require(semantic.Sum(part=>part.GetProperty("length_mm").GetInt32())==c06.GetProperty("heating_body_length_mm").GetInt32(),"D029 semantic reconciliation");
        Require(c06.GetProperty("lobe_territories").GetArrayLength()==3,"D029 lobe metadata");
        foreach(var lobe in c06.GetProperty("lobe_territories").EnumerateArray()) Require(lobe.GetProperty("regularity").GetProperty("result").GetString()!.StartsWith("PASS"),"D029 lobe regularity");
        var bypass=semantic.Single(part=>part.GetProperty("role").GetString()=="STAIR_EXCLUSION_BYPASS_TRANSITION");
        Require(bypass.GetProperty("minimum_centerline_to_tread_box_mm").GetInt32()==800,"D029 bypass clearance metadata");
        var allIds=new HashSet<string>();var allCoords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(allIds.Add(route.GetProperty("supply_port_id").GetString()!)&&allIds.Add(route.GetProperty("return_port_id").GetString()!),"D029 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(allCoords.Add($"{supply[0]}:{supply[1]}")&&allCoords.Add($"{returned[0]}:{returned[1]}"),"D029 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D029 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D029 measured length");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D029 component reconciliation");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D029 tread exclusion contact");
        }
        Require(allIds.Count==24&&allCoords.Count==24&&CountInterRouteContacts(routes)==0,"D029 global topology");
        Require(File.Exists(Path.Combine(root,"floor_1_north_hall_overlay.png"))&&File.Exists(Path.Combine(root,"floor_1_north_hall_pipes_only.png")),"D029 visual evidence");
    }

    private static void ValidateFloor1TwelveRoutesSpacing028()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_SPACING_028"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_AND_C06_SPACING_PASS_REWORK_POLYGON_COVERAGE","D028 status");
        Require(routes.Length==12,"D028 route count");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("territory_assignment_complete").GetBoolean(),"D028 assignment honesty");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D028 coverage honesty");
        var c06=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C06");
        Require(c06.GetProperty("total_length_mm").GetInt32()==55500,"D028 C06 length");
        Require(c06.GetProperty("supply_transit_length_mm").GetInt32()==9900&&c06.GetProperty("heating_body_length_mm").GetInt32()==38300&&c06.GetProperty("return_transit_length_mm").GetInt32()==7300,"D028 C06 parts");
        var semantic=c06.GetProperty("semantic_route_parts").EnumerateArray().ToArray();
        Require(semantic.Length==3&&semantic.Select(part=>part.GetProperty("role").GetString()).SequenceEqual(new[]{"SOUTH_COUNTERFLOW_LOBE","TERRITORY_TRANSITION","NORTH_COUNTERFLOW_LOBE"}),"D028 semantic part order");
        Require(semantic.Sum(part=>part.GetProperty("length_mm").GetInt32())==c06.GetProperty("heating_body_length_mm").GetInt32(),"D028 semantic part reconciliation");
        var transition=semantic[1].GetProperty("points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
        Require(transition.SequenceEqual(new[]{(108,142),(104,142),(104,126),(107,126)}),"D028 transition points");
        Require(c06.GetProperty("regularity_validation").GetProperty("minimum_transition_to_south_lobe_parallel_spacing_mm").GetInt32()==200,"D028 transition spacing");
        Require(c06.GetProperty("regularity_validation").GetProperty("semantic_boundary_points_preserved").GetBoolean(),"D028 semantic boundaries");
        var body=c06.GetProperty("heating_body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
        Require(ContainsConsecutive(body,transition),"D028 transition not embedded");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D028 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D028 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D028 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D028 measured length");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D028 component reconciliation");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D028 tread exclusion contact");
        }
        Require(ids.Count==24&&coords.Count==24&&CountInterRouteContacts(routes)==0,"D028 global topology");
    }

    private static void ValidateFloor1TwelveRoutes027()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_TWELVE_ROUTES_027"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TWELVE_ROUTE_GEOMETRY_PASS_REWORK_POLYGON_COVERAGE","D027 bounded status");
        Require(routes.Length==12,"D027 route count");
        Require(model.GetProperty("remaining_route_ids").GetArrayLength()==0,"D027 assigned route count");
        Require(model.GetProperty("retired_route_candidates")[0].GetProperty("route_id").GetString()=="F1-C07","D027 C07 retirement");
        var coverage=model.GetProperty("coverage_diagnostic");
        Require(coverage.GetProperty("territory_assignment_complete").GetBoolean(),"D027 territory assignment");
        Require(!coverage.GetProperty("full_coverage_claimed").GetBoolean(),"D027 coverage honesty");
        Require(!coverage.GetProperty("exact_room_polygon_union_evaluated").GetBoolean(),"D027 polygon claim");
        Require(!coverage.GetProperty("exterior_wall_100mm_band_evaluated").GetBoolean(),"D027 exterior band claim");
        Require(coverage.GetProperty("nominal_served_area_mm2").GetInt64()==routes.Sum(route=>route.GetProperty("heating_body_length_mm").GetInt64())*200,"D027 nominal coverage arithmetic");
        var collector=model.GetProperty("collector_contract");var envelope=collector.GetProperty("station_envelope_bbox_grid");
        Require(collector.GetProperty("logical_assembly_count").GetInt32()==1,"D027 logical K1 count");
        Require(collector.GetProperty("circuit_count").GetInt32()==12&&collector.GetProperty("physical_pipe_connection_count").GetInt32()==24,"D027 K1 connection count");
        Require(collector.GetProperty("connection_to_gate_mapping").GetArrayLength()==24,"D027 gate mapping count");
        Require(!collector.GetProperty("physical_commercial_manifold_selected").GetBoolean(),"D027 physical manifold claim");
        Require(collector.GetProperty("commercial_capacity").GetString()=="NOT_EVALUATED","D027 capacity claim");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(route.GetProperty("collector_id").GetString()=="K1"&&route.GetProperty("completed").GetBoolean(),"D027 route ownership/completion");
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D027 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D027 duplicate port coordinate");
            foreach(var port in new[]{supply,returned}) Require(port[0].GetInt32()>=envelope[0].GetInt32()&&port[0].GetInt32()<=envelope[2].GetInt32()&&port[1].GetInt32()>=envelope[1].GetInt32()&&port[1].GetInt32()<=envelope[3].GetInt32(),"D027 port outside K1 envelope");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            var body=route.GetProperty("heating_body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D027 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D027 orthogonal nonzero segments");
            Require(CountSelfContacts(points)==0,"D027 self contact");
            Require(ContainsConsecutive(ExpandUnitPoints(points),ExpandUnitPoints(body)),"D027 body not preserved in canonical route");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D027 measured length");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D027 component reconciliation");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D027 tread exclusion contact");
        }
        Require(ids.Count==24&&coords.Count==24,"D027 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D027 global contacts");
        var c05=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C05");
        Require(c05.GetProperty("topology").GetString()=="REGULAR_RECTANGULAR_COUNTERFLOW"&&c05.GetProperty("total_length_mm").GetInt32()==51300,"D027 C05 result");
        Require(c05.GetProperty("regularity_validation").GetProperty("result").GetString()=="PASS"&&c05.GetProperty("regularity_validation").GetProperty("staircase_pattern_count").GetInt32()==0,"D027 C05 regularity");
        var c06=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C06");
        Require(c06.GetProperty("topology").GetString()=="COMPOSITE_TWO_LOBE_COUNTERFLOW"&&c06.GetProperty("total_length_mm").GetInt32()==56100,"D027 C06 result");
        Require(c06.GetProperty("lobe_count").GetInt32()==2&&c06.GetProperty("lobe_territories").GetArrayLength()==2,"D027 C06 lobe count");
        Require(c06.GetProperty("regularity_validation").GetProperty("result").GetString()=="PASS_BOUNDED_TWO_LOBE"&&!c06.GetProperty("regularity_validation").GetProperty("transition_is_length_padding").GetBoolean(),"D027 C06 regularity");
        foreach(var lobe in c06.GetProperty("lobe_territories").EnumerateArray()) Require(lobe.GetProperty("regularity").GetProperty("result").GetString()=="PASS","D027 C06 lobe regularity");
        var c14=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C14");
        Require(c14.GetProperty("total_length_mm").GetInt32()==77900&&c14.GetProperty("tread_bypass_classification").GetString()=="RETURN_TRANSIT_AROUND_CONFIRMED_EXCLUSION","D027 C14 result");
        Require(c14.GetProperty("regularity_validation").GetProperty("centre_turn_points_are_consecutive_body_points").GetBoolean(),"D027 C14 centre metadata");
        Require(File.Exists(Path.Combine(root,"floor_1_twelve_routes_overlay.png")),"D027 overlay missing");
        Require(File.Exists(Path.Combine(root,"floor_1_twelve_routes_pipes_only.png")),"D027 pipes-only missing");
        Require(File.Exists(Path.Combine(root,"floor_1_hall_regularity_debug.png")),"D027 debug image missing");
    }

    private static void ValidateFloor1ElevenRoutes026()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_ELEVEN_ROUTES_026"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="ELEVEN_ROUTES_GEOMETRY_PASS_REWORK_EAST_HALL_COVERAGE","D026 bounded status");
        Require(routes.Length==11,"D026 route count");
        Require(model.GetProperty("remaining_route_ids").GetArrayLength()==2,"D026 remaining routes");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D026 coverage honesty");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D026 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D026 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D026 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D026 orthogonal nonzero segments");
            Require(CountSelfContacts(points)==0,"D026 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D026 measured length");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D026 tread exclusion contact");
        }
        Require(ids.Count==22&&coords.Count==22,"D026 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D026 global contacts");
        var c05=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C05");
        Require(c05.GetProperty("total_length_mm").GetInt32()==40100&&c05.GetProperty("territory_id").GetString()=="STAIR_AND_HALL_WEST","D026 C05 result");
        var c14=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C14");
        Require(c14.GetProperty("total_length_mm").GetInt32()==77200&&c14.GetProperty("return_port_grid")[1].GetInt32()==73,"D026 C14 result");
        var contract=model.GetProperty("collector_contract");
        Require(contract.GetProperty("circuit_count").GetInt32()==11&&contract.GetProperty("physical_pipe_connection_count").GetInt32()==22,"D026 K1 counts");
        Require(contract.GetProperty("reserved_future_hall_gate_pairs_grid").GetArrayLength()==2,"D026 future hall gates");
    }

    private static void ValidateFloor1RepartitionLineage025()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_REPARTITION_CERTIFIED_025"));
        var sourceRoot=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var sourceDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(sourceRoot,"canonical_geometry.json")));
        var model=document.RootElement;var source=sourceDocument.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();var sourceRoutes=source.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="D024_GEOMETRY_AND_BODY_LINEAGE_PASS_REWORK_HALL_COVERAGE","D025 status");
        Require(routes.Length==sourceRoutes.Length,"D025 route count");
        for(var i=0;i<routes.Length;i++) Require(routes[i].GetProperty("ordered_points_grid").GetRawText()==sourceRoutes[i].GetProperty("ordered_points_grid").GetRawText(),"D025 changed ordered geometry");
        Require(model.GetProperty("body_digest_coordinate_space").GetString()=="ORDERED_POINTS_MM","D025 digest coordinate space");
        var lineage=model.GetProperty("body_lineage").EnumerateArray().ToArray();
        Require(lineage.Length==10,"D025 lineage count");
        var changed=lineage.Where(item=>item.GetProperty("changed").GetBoolean()).Select(item=>item.GetProperty("route_id").GetString()).OrderBy(id=>id).ToArray();
        Require(changed.SequenceEqual(new[]{"F1-C03","F1-C04"}),"D025 changed body lineage");
        foreach(var item in lineage)
        {
            var route=routes.Single(candidate=>candidate.GetProperty("route_id").GetString()==item.GetProperty("route_id").GetString());
            Require(route.GetProperty("heating_body_digest").GetString()==item.GetProperty("current_body_digest_mm").GetString(),"D025 current body digest link");
            Require(item.GetProperty("changed").GetBoolean()==(item.GetProperty("source_body_digest_mm").GetString()!=item.GetProperty("current_body_digest_mm").GetString()),"D025 changed flag semantics");
        }
    }

    private static void ValidateFloor1Repartitioned024()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_REPARTITIONED_024"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TEN_ROUTES_REPARTITIONED_PASS_REWORK_HALL_COVERAGE","D024 bounded status");
        Require(routes.Length==10,"D024 route count");
        Require(model.GetProperty("small_wc_shower_strategy").GetString()=="ABSORBED_INTO_C03_C04_CONNECTED_WET_ROOM_TERRITORY","D024 small WC strategy");
        Require(model.GetProperty("remaining_route_ids").GetArrayLength()==3,"D024 remaining route count");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D024 coverage honesty");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D024 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D024 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D024 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D024 orthogonal nonzero segments");
            Require(CountSelfContacts(points)==0,"D024 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D024 measured length");
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,(113,98,127,108)),"D024 tread exclusion contact");
        }
        Require(ids.Count==20&&coords.Count==20,"D024 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D024 global contacts");
        var c03=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C03");
        var c04=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C04");
        Require(c03.GetProperty("territory_bbox_grid")[2].GetInt32()==94&&c04.GetProperty("territory_bbox_grid")[2].GetInt32()==94,"D024 wet territory extension");
        Require(c03.GetProperty("small_wc_shower_absorbed").GetBoolean()&&c04.GetProperty("small_wc_shower_absorbed").GetBoolean(),"D024 small WC absorption metadata");
        var c14=routes.Single(route=>route.GetProperty("route_id").GetString()=="F1-C14");
        Require(c14.GetProperty("supply_port_grid")[1].GetInt32()==81&&c14.GetProperty("return_port_grid")[1].GetInt32()==80,"D024 C14 gate relocation");
        Require(model.GetProperty("collector_contract").GetProperty("reserved_future_hall_gate_pairs_grid").GetArrayLength()==3,"D024 hall gates");
    }

    private static void ValidateFloor1TenRoutes023()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_TEN_ROUTES_REPAIRED_023"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        using var validationDocument=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"validation.json")));
        var model=document.RootElement;var validation=validationDocument.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="TEN_FLOOR1_ROUTES_GEOMETRY_PASS_REWORK_REMAINING_COVERAGE","D023 bounded status");
        Require(routes.Length==10,"D023 route count");
        Require(validation.GetProperty("global_inter_route_contact_count").GetInt32()==0,"D023 stored global contacts");
        Require(validation.GetProperty("first_three_tread_exclusion_hit_count").GetInt32()==0,"D023 stored tread contacts");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D023 coverage honesty");
        var collector=model.GetProperty("collector_contract");var envelope=collector.GetProperty("station_envelope_bbox_grid");
        Require(collector.GetProperty("logical_assembly_count").GetInt32()==1,"D023 logical collector count");
        Require(collector.GetProperty("west_wall_face_gate_bbox_grid")[3].GetInt32()==75,"D023 west gate bbox");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            var id=route.GetProperty("route_id").GetString()!;var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D023 duplicate port ID");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D023 duplicate port coordinate");
            foreach(var port in new[]{supply,returned}) Require(port[0].GetInt32()>=envelope[0].GetInt32()&&port[0].GetInt32()<=envelope[2].GetInt32()&&port[1].GetInt32()>=envelope[1].GetInt32()&&port[1].GetInt32()<=envelope[3].GetInt32(),"D023 port outside K1 envelope");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D023 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D023 orthogonal nonzero segments");
            Require(CountSelfContacts(points)==0,"D023 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32()&&measured>=40000&&measured<=80000,"D023 measured length");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D023 component length");
            if(id=="F1-C14")
            {
                Require(points[0]==(129,75)&&points[1]==(128,75),"D023 C14 must exit west face orthogonally");
                var body=route.GetProperty("heating_body_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
                Require(Enumerable.Range(0,body.Length-2).Any(i=>body[i]==(97,177)&&body[i+1]==(127,177)&&body[i+2]==(127,179)),"D023 actual C14 centre turn");
                Require(route.GetProperty("regularity_validation").GetProperty("centre_turn_points_are_consecutive_body_points").GetBoolean(),"D023 centre metadata");
            }
        }
        Require(ids.Count==20&&coords.Count==20,"D023 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D023 independently calculated global contact");
        var tread=(X0:113,Y0:98,X1:127,Y1:108);
        foreach(var route in routes)
        {
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            foreach(var pair in points.Zip(points.Skip(1))) Require(!SegmentHitsBox(pair.First,pair.Second,tread),"D023 tread exclusion contact");
        }
        Require(File.Exists(Path.Combine(root,"floor_1_ten_routes_overlay.png")),"D023 overlay missing");
        Require(File.Exists(Path.Combine(root,"floor_1_ten_routes_pipes_only.png")),"D023 pipes-only missing");
    }

    private static void ValidateFloor1Unified019()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_FLOOR1_UNIFIED_019"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="NINE_FLOOR1_FULL_ROUTES_ONE_K1_PASS_REWORK_REMAINING_FLOOR1_COVERAGE","D019 status");
        Require(routes.Length==9,"D019 route count");
        Require(model.GetProperty("collector_contract").GetProperty("logical_assembly_count").GetInt32()==1,"D019 collector count");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D019 coverage honesty");
        Require(!model.GetProperty("whole_floor_completion").GetBoolean(),"D019 whole-floor honesty");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(route.GetProperty("collector_id").GetString()=="K1","D019 collector ownership");
            Require(route.GetProperty("completed").GetBoolean(),"D019 completed route");
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!)&&ids.Add(route.GetProperty("return_port_id").GetString()!),"D019 duplicate port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D019 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32())&&points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D019 endpoint ownership");
            Require(points.Zip(points.Skip(1)).All(pair=>pair.First!=pair.Second&&(pair.First.X==pair.Second.X||pair.First.Y==pair.Second.Y)),"D019 orthogonal nonzero segments");
            Require(CountSelfContacts(points)==0,"D019 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32(),"D019 measured length");
            Require(measured>=40000&&measured<=80000,"D019 length range");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D019 component length");
        }
        Require(ids.Count==18&&coords.Count==18,"D019 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D019 global inter-route contact");
        var collector=model.GetProperty("collector_contract");
        Require(collector.GetProperty("west_wall_face_gates_grid").GetArrayLength()==8,"D019 west gates");
        Require(collector.GetProperty("south_wall_penetration_gates_grid").GetArrayLength()==9,"D019 south gates");
        Require(!collector.GetProperty("shared_pipe_trunk").GetBoolean(),"D019 shared trunk claim");
    }

    private static void ValidateFloor1WestGroup018()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_WEST_GROUP_018"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="FOUR_WEST_GROUP_FULL_ROUTES_PASS_REWORK_WHOLE_FLOOR_INTEGRATION","D018 status");
        Require(routes.Length==4,"D018 route count");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D018 coverage honesty");
        Require(!model.GetProperty("whole_floor_completion").GetBoolean(),"D018 whole-floor honesty");
        var portIds=new HashSet<string>();var portCoordinates=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(route.GetProperty("collector_id").GetString()=="K1","D018 collector ownership");
            Require(route.GetProperty("completed").GetBoolean(),"D018 completed route");
            Require(route.GetProperty("topology").GetString()=="REGULAR_RECTANGULAR_COUNTERFLOW","D018 body topology");
            Require(route.GetProperty("regularity_validation").GetProperty("result").GetString()=="PASS","D018 regularity");
            Require(portIds.Add(route.GetProperty("supply_port_id").GetString()!),"D018 duplicate supply port ID");
            Require(portIds.Add(route.GetProperty("return_port_id").GetString()!),"D018 duplicate return port ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(portCoordinates.Add($"{supply[0]}:{supply[1]}")&&portCoordinates.Add($"{returned[0]}:{returned[1]}"),"D018 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32()),"D018 supply endpoint");
            Require(points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D018 return endpoint");
            Require(CountSelfContacts(points)==0,"D018 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32(),"D018 measured length");
            Require(measured>=40000&&measured<=80000,"D018 length range");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D018 length components");
        }
        Require(portIds.Count==8&&portCoordinates.Count==8,"D018 unique ports");
        Require(CountInterRouteContacts(routes)==0,"D018 inter-route contact");
    }

    private static void ValidateCounterflowFullRoutes015()
    {
        var root=Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,"..","..","..","..","homeaura-native-editor","examples","proposals","HA_TWO_FLOOR_COUNTERFLOW_FULL_ROUTES_015"));
        using var document=JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_geometry.json")));
        var model=document.RootElement;var routes=model.GetProperty("routes").EnumerateArray().ToArray();
        Require(model.GetProperty("status").GetString()=="FIVE_COUNTERFLOW_FULL_ROUTES_PASS_REWORK_COVERAGE","D015 status");
        Require(routes.Length==5,"D015 route count");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D015 coverage honesty");
        var ids=new HashSet<string>();var coords=new HashSet<string>();
        foreach(var route in routes)
        {
            Require(route.GetProperty("completed").GetBoolean(),"D015 completed");
            Require(route.GetProperty("collector_id").GetString()=="K1","D015 collector");
            Require(ids.Add(route.GetProperty("supply_port_id").GetString()!),"D015 duplicate supply ID");
            Require(ids.Add(route.GetProperty("return_port_id").GetString()!),"D015 duplicate return ID");
            var supply=route.GetProperty("supply_port_grid");var returned=route.GetProperty("return_port_grid");
            Require(coords.Add($"{supply[0]}:{supply[1]}")&&coords.Add($"{returned[0]}:{returned[1]}"),"D015 duplicate port coordinate");
            var points=route.GetProperty("ordered_points_grid").EnumerateArray().Select(p=>(X:p[0].GetInt32(),Y:p[1].GetInt32())).ToArray();
            Require(points[0]==(supply[0].GetInt32(),supply[1].GetInt32()),"D015 supply endpoint");Require(points[^1]==(returned[0].GetInt32(),returned[1].GetInt32()),"D015 return endpoint");
            Require(CountSelfContacts(points)==0,"D015 self contact");
            var measured=points.Zip(points.Skip(1)).Sum(pair=>(Math.Abs(pair.First.X-pair.Second.X)+Math.Abs(pair.First.Y-pair.Second.Y))*100);
            Require(measured==route.GetProperty("total_length_mm").GetInt32(),"D015 measured length");Require(measured>=40000&&measured<=80000,"D015 length range");
            Require(measured==route.GetProperty("supply_transit_length_mm").GetInt32()+route.GetProperty("heating_body_length_mm").GetInt32()+route.GetProperty("return_transit_length_mm").GetInt32(),"D015 length components");
        }
        Require(ids.Count==10&&coords.Count==10,"D015 unique ports");Require(CountInterRouteContacts(routes)==0,"D015 inter contact");
    }

    private static void ValidateCoverageBodies014()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_COUNTERFLOW_COVERAGE_014"));
        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(root,"canonical_counterflow_bodies.json")));
        var model=document.RootElement;
        Require(model.GetProperty("status").GetString()=="COUNTERFLOW_BODIES_PASS_REWORK_K1_TRANSITS","D014 status");
        Require(!model.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(),"D014 false coverage claim");
        Require(model.GetProperty("collector_transits").GetString()=="NOT_ROUTED_REWORK","D014 transit honesty");
        var bodies=model.GetProperty("bodies").EnumerateArray().ToArray();
        Require(bodies.Length==5,"D014 body count");
        foreach(var body in bodies)
        {
            Require(body.GetProperty("topology").GetString()=="REGULAR_RECTANGULAR_COUNTERFLOW","D014 topology type");
            Require(body.GetProperty("body_topology_validation").GetProperty("result").GetString()=="PASS","D014 body topology");
            Require(body.GetProperty("regularity_validation").GetProperty("result").GetString()=="PASS","D014 regularity");
            Require(body.GetProperty("total_circuit_length_mm").ValueKind==JsonValueKind.Null,"D014 total length claim");
            var points=body.GetProperty("ordered_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            Require(CountSelfContacts(points)==0,"D014 independently calculated self contact");
        }
        Require(CountInterRouteContacts(bodies)==0,"D014 independently calculated inter body contact");
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }

    private static int CountSelfContacts((int X, int Y)[] points)
    {
        var count = 0;
        for (var i = 0; i < points.Length - 1; i++)
        for (var j = i + 2; j < points.Length - 1; j++)
            if (Relation(points[i], points[i + 1], points[j], points[j + 1]) != 0) count++;
        return count;
    }

    private static bool ContainsConsecutive((int X,int Y)[] haystack,(int X,int Y)[] needle)
    {
        if(needle.Length==0||needle.Length>haystack.Length) return false;
        return Enumerable.Range(0,haystack.Length-needle.Length+1).Any(index=>haystack.Skip(index).Take(needle.Length).SequenceEqual(needle));
    }

    private static (int X,int Y)[] ExpandUnitPoints((int X,int Y)[] points)
    {
        var expanded=new List<(int X,int Y)>{points[0]};
        foreach(var pair in points.Zip(points.Skip(1)))
        {
            var dx=Math.Sign(pair.Second.X-pair.First.X);var dy=Math.Sign(pair.Second.Y-pair.First.Y);
            var cursor=pair.First;
            while(cursor!=pair.Second){cursor=(cursor.X+dx,cursor.Y+dy);expanded.Add(cursor);}
        }
        return expanded.ToArray();
    }

    private static int CountInterRouteContacts(JsonElement[] routes)
    {
        var count = 0;
        for (var i = 0; i < routes.Length; i++)
        {
            var first = routes[i].GetProperty("ordered_points_grid").EnumerateArray().Select(p => (X: p[0].GetInt32(), Y: p[1].GetInt32())).ToArray();
            for (var j = i + 1; j < routes.Length; j++)
            {
                var second = routes[j].GetProperty("ordered_points_grid").EnumerateArray().Select(p => (X: p[0].GetInt32(), Y: p[1].GetInt32())).ToArray();
                for (var a = 0; a < first.Length - 1; a++)
                for (var b = 0; b < second.Length - 1; b++)
                    if (Relation(first[a], first[a + 1], second[b], second[b + 1]) != 0) count++;
            }
        }
        return count;
    }

    private static int CountInterBodyContacts(JsonElement[] routes)
    {
        var count=0;
        for(var i=0;i<routes.Length;i++)
        {
            var first=routes[i].GetProperty("body_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
            for(var j=i+1;j<routes.Length;j++)
            {
                var second=routes[j].GetProperty("body_points_grid").EnumerateArray().Select(point=>(X:point[0].GetInt32(),Y:point[1].GetInt32())).ToArray();
                for(var a=0;a<first.Length-1;a++)
                for(var b=0;b<second.Length-1;b++)
                    if(Relation(first[a],first[a+1],second[b],second[b+1])!=0) count++;
            }
        }
        return count;
    }

    private static bool SegmentHitsBox((int X,int Y) a,(int X,int Y) b,(int X0,int Y0,int X1,int Y1) box)
    {
        if(a.X==b.X) return a.X>=box.X0&&a.X<=box.X1&&Math.Max(Math.Min(a.Y,b.Y),box.Y0)<=Math.Min(Math.Max(a.Y,b.Y),box.Y1);
        return a.Y>=box.Y0&&a.Y<=box.Y1&&Math.Max(Math.Min(a.X,b.X),box.X0)<=Math.Min(Math.Max(a.X,b.X),box.X1);
    }

    private static int Relation((int X, int Y) a, (int X, int Y) b, (int X, int Y) c, (int X, int Y) d)
    {
        static long Cross((int X, int Y) p, (int X, int Y) q, (int X, int Y) r) => (long)(q.X-p.X)*(r.Y-p.Y)-(long)(q.Y-p.Y)*(r.X-p.X);
        var v = new[] { Cross(a,b,c), Cross(a,b,d), Cross(c,d,a), Cross(c,d,b) };
        if (v.All(x => x == 0))
        {
            var ox = Math.Min(Math.Max(a.X,b.X), Math.Max(c.X,d.X)) - Math.Max(Math.Min(a.X,b.X), Math.Min(c.X,d.X));
            var oy = Math.Min(Math.Max(a.Y,b.Y), Math.Max(c.Y,d.Y)) - Math.Max(Math.Min(a.Y,b.Y), Math.Min(c.Y,d.Y));
            return Math.Max(ox, oy) > 0 || (ox == 0 && oy == 0) ? 1 : 0;
        }
        var hit = (v[0] == 0 || v[1] == 0 || (v[0] < 0) != (v[1] < 0)) && (v[2] == 0 || v[3] == 0 || (v[2] < 0) != (v[3] < 0));
        return hit ? 1 : 0;
    }
}
