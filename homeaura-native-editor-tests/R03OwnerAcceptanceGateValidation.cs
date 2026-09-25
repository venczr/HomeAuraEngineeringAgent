using System.Text.Json;

internal static class R03OwnerAcceptanceGateValidation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var reports = Path.Combine(root, "reports");
        using var nearDocument = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(reports, "HomeAura_R03_OwnerGate_NearPass_2026-08-20.json")));
        using var snakeDocument = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(reports, "HomeAura_R03_OwnerGate_GlobalSerpentine_2026-08-20.json")));
        using var seamDocument = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(reports, "HomeAura_R03_OwnerGate_C08CentralSeam_2026-08-20.json")));
        using var wallClearDocument = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(reports, "HomeAura_R03_OwnerGate_C08WallClearMultiRange_2026-08-20.json")));

        var near = nearDocument.RootElement;
        Equal("homeaura.r03.owner-acceptance-audit.v1", near.GetProperty("schema").GetString(), "schema");
        Check(near.GetProperty("read_only_audit").GetBoolean() &&
              !near.GetProperty("official_project_modified").GetBoolean(), "R03 audit changed an official project.");
        var room = near.GetProperty("derived_room_geometry");
        Equal(2, room.GetProperty("free_floor_component_count").GetInt32(), "R03 component count");
        Close(31.21, room.GetProperty("main_component_area_m2").GetDouble(), 1e-12, "R03 main component");
        Close(1.95, room.GetProperty("other_component_areas_m2")[0].GetDouble(), 1e-12, "R03 sealed west slot");

        var nearCoverage = near.GetProperty("coverage");
        Close(95.73264129596905,
            nearCoverage.GetProperty("physical_R80_q16_round100_percent_compatibility").GetDouble(), 1e-10,
            "near-pass q16 coverage");
        Close(95.73759537439429,
            nearCoverage.GetProperty("physical_R80_q64_round100_percent_independent").GetDouble(), 1e-10,
            "near-pass independent q64 coverage");
        Close(200, nearCoverage.GetProperty("maximum_sample_distance_mm").GetDouble(), 1e-10,
            "near-pass maximum sample distance");
        Equal(0, nearCoverage.GetProperty("sample_over_200mm_count").GetInt32(), "near-pass outlier count");
        var nearGates = near.GetProperty("gates");
        Check(!nearGates.GetProperty("geometry_R80_and_contacts_pass").GetBoolean(),
            "near-pass endpoint touching W018 incorrectly cleared the OD16 wall gate.");
        Check(nearGates.GetProperty("owner_morphology_all_routes_pass").GetBoolean(), "owner spirals rejected");
        Check(!nearGates.GetProperty("physical_coverage_at_least_96_and_max_200_pass").GetBoolean(),
            "near-pass falsely reached 96%.");
        Check(!nearGates.GetProperty("publishable_pass").GetBoolean(), "near-pass became publishable.");
        var routes = near.GetProperty("route_audit");
        Equal("NESTED_EXTERIOR_PERIMETER_WITH_LOCAL_RESIDUAL_SNAKE",
            routes.GetProperty("C07").GetProperty("morphology").GetProperty("classification").GetString(),
            "C07 owner-hybrid classification");
        Equal("COUNTERFLOW_SPIRAL_WITH_LOCAL_RESIDUAL",
            routes.GetProperty("C08").GetProperty("morphology").GetProperty("classification").GetString(),
            "C08 spiral classification");
        Equal("COUNTERFLOW_SPIRAL_WITH_LOCAL_RESIDUAL",
            routes.GetProperty("C09").GetProperty("morphology").GetProperty("classification").GetString(),
            "C09 spiral classification");
        Close(0, routes.GetProperty("C08").GetProperty("minimum_axis_clearance_to_wall_solid_mm").GetDouble(),
            1e-10, "old C08 wall clearance");
        Check(!routes.GetProperty("C08").GetProperty("OD16_pipe_envelope_clear_of_wall_solid").GetBoolean(),
            "old C08 wall-face endpoint became OD16-safe.");
        var exterior = near.GetProperty("exterior_3x100").GetProperty("rows");
        Equal(6, exterior.GetArrayLength(), "exterior lane count");
        Check(exterior.EnumerateArray().All(item =>
                item.GetProperty("owner_circuit_id").GetString() == "C07" &&
                item.GetProperty("body_only").GetBoolean() &&
                item.GetProperty("useful_span_percent").GetDouble() >= 90 &&
                Math.Abs(item.GetProperty("window_projection_percent").GetDouble() - 100) < 1e-10),
            "C07 no longer owns six useful BODY/window lanes.");

        var snake = snakeDocument.RootElement;
        var snakeGates = snake.GetProperty("gates");
        Check(snakeGates.GetProperty("physical_coverage_at_least_96_and_max_200_pass").GetBoolean(),
            "numeric control candidate should remain a coverage pass.");
        Check(!snakeGates.GetProperty("owner_morphology_all_routes_pass").GetBoolean() &&
              !snakeGates.GetProperty("publishable_pass").GetBoolean(),
            "generic serpentines bypassed the owner gate.");
        var snakeRoutes = snake.GetProperty("route_audit");
        foreach (var id in new[] { "C08", "C09" })
        {
            var morphology = snakeRoutes.GetProperty(id).GetProperty("morphology");
            Equal("GENERIC_FULL_FIELD_SERPENTINE", morphology.GetProperty("classification").GetString(),
                $"{id} serpentine classification");
            Check(morphology.GetProperty("generic_full_field_serpentine_detected").GetBoolean(),
                $"{id} serpentine detector");
        }

        var seam = seamDocument.RootElement;
        var seamCoverage = seam.GetProperty("coverage");
        Close(96.85845188522077,
            seamCoverage.GetProperty("physical_R80_q16_round100_percent_compatibility").GetDouble(), 1e-10,
            "central seam coverage");
        var seamRecord = seam.GetProperty("supplemental_body_seams");
        Equal(1, seamRecord.GetProperty("count").GetInt32(), "seam count");
        Close(1600, seamRecord.GetProperty("total_physical_R80_exact_axis_length_mm").GetDouble(), 1e-10,
            "seam length");
        Check(seamRecord.GetProperty("combined_owner_morphology_intent_pass").GetBoolean(),
            "central void-fill morphology should pass.");
        Check(!seamRecord.GetProperty("single_ordered_body_chain_proven").GetBoolean() &&
              !seamRecord.GetProperty("continuous_collector_to_collector_point3_route_proven").GetBoolean(),
            "a disconnected seam became one installable tube.");
        var seamGates = seam.GetProperty("gates");
        Check(seamGates.GetProperty("physical_coverage_at_least_96_and_max_200_pass").GetBoolean(),
            "central seam no longer closes the coverage deficit.");
        Check(!seamGates.GetProperty("single_ordered_body_chain_pass").GetBoolean() &&
              !seamGates.GetProperty("numeric_hard_gates_pass").GetBoolean() &&
              !seamGates.GetProperty("publishable_pass").GetBoolean(),
            "disconnected seam bypassed continuity.");

        var wallClear = wallClearDocument.RootElement;
        var wallClearCoverage = wallClear.GetProperty("coverage");
        Close(96.68922372440188,
            wallClearCoverage.GetProperty("physical_R80_q16_round100_percent_compatibility").GetDouble(),
            1e-10, "wall-clear multi-range coverage");
        Close(200, wallClearCoverage.GetProperty("maximum_sample_distance_mm").GetDouble(), 1e-10,
            "wall-clear multi-range maximum sample distance");
        Equal(0, wallClearCoverage.GetProperty("sample_over_200mm_count").GetInt32(),
            "wall-clear multi-range outlier count");
        var wallClearRoutes = wallClear.GetProperty("route_audit");
        foreach (var id in new[] { "C07", "C08", "C09" })
        {
            Close(100, wallClearRoutes.GetProperty(id).GetProperty("minimum_axis_clearance_to_wall_solid_mm").GetDouble(),
                1e-8, $"{id} wall clearance");
            Check(wallClearRoutes.GetProperty(id).GetProperty("OD16_pipe_envelope_clear_of_wall_solid").GetBoolean(),
                $"{id} OD16 wall envelope");
        }
        var ranges = wallClear.GetProperty("supplemental_body_seams");
        Equal(2, ranges.GetProperty("count").GetInt32(), "disconnected wall-clear body range count");
        Check(!ranges.GetProperty("OD16_pipe_envelope_wall_contact").GetBoolean() &&
              ranges.GetProperty("combined_owner_morphology_intent_pass").GetBoolean(),
            "wall-clear shelf/seam geometry or morphology changed.");
        var rangeRows = ranges.GetProperty("morphology_records").EnumerateArray().ToArray();
        Close(100, rangeRows[0].GetProperty("minimum_axis_clearance_to_wall_solid_mm").GetDouble(), 1e-8,
            "shelf wall clearance");
        Close(1100, rangeRows[1].GetProperty("minimum_axis_clearance_to_wall_solid_mm").GetDouble(), 1e-8,
            "central seam wall clearance");
        Check(rangeRows.All(item => item.GetProperty("owner_morphology_range_pass").GetBoolean()),
            "a wall-clear body range failed morphology.");
        var aggregate = wallClear.GetProperty("diagnostic_body_range_aggregates").GetProperty("C08");
        Close(52705.94440323288, aggregate.GetProperty("physical_R80_q16_body_sum_mm").GetDouble(), 1e-8,
            "C08 disconnected body sum");
        Check(!aggregate.GetProperty("valid_cut_length").GetBoolean(),
            "disconnected C08 body ranges became a valid cut length.");
        var wallClearGates = wallClear.GetProperty("gates");
        Check(wallClearGates.GetProperty("geometry_R80_and_contacts_pass").GetBoolean() &&
              wallClearGates.GetProperty("physical_coverage_at_least_96_and_max_200_pass").GetBoolean() &&
              wallClearGates.GetProperty("owner_morphology_all_routes_pass").GetBoolean(),
            "wall-clear body evidence changed.");
        Check(!wallClearGates.GetProperty("single_ordered_body_chain_pass").GetBoolean() &&
              !wallClearGates.GetProperty("publishable_pass").GetBoolean(),
            "multi-range C08 bypassed Point3 continuity.");
    }

    private static void Close(double expected, double actual, double tolerance, string label)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Equal<T>(T expected, T? actual, string label)
    {
        if (!EqualityComparer<T?>.Default.Equals(expected, actual))
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
