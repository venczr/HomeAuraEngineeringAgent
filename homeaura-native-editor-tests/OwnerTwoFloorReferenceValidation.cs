using System.Text.Json;

internal static class OwnerTwoFloorReferenceValidation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "homeaura-native-editor", "examples", "owner-references",
            "OWNER_TWO_FLOOR_REFERENCE_001", "owner_layout_reference.json");
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var reference = document.RootElement;

        Equal("homeaura.owner-layout-reference.v1", reference.GetProperty("schema").GetString(), "schema");
        Equal("SOURCE_VISUAL_REFERENCE_ACCEPTED", reference.GetProperty("status").GetString(), "status");
        var sources = reference.GetProperty("sources");
        Equal(2, sources.GetArrayLength(), "source count");

        var project1 = sources[0];
        Equal(3, project1.GetProperty("page_count").GetInt32(), "project1 pages");
        Equal(2, project1.GetProperty("plan_count").GetInt32(), "project1 plans");
        Equal(2, project1.GetProperty("user_context_floor_count").GetInt32(), "project1 user-context floors");
        Equal("USER_CONTEXT_CONFIRMED_NOT_LABELLED_ON_RASTER",
            project1.GetProperty("floor_mapping_status").GetString(), "project1 floor mapping honesty");
        Equal("NOT_PRINTED_IN_RASTER_INFERRED_METRES",
            project1.GetProperty("unit_status").GetString(), "project1 unit honesty");
        var project1Lengths = project1.GetProperty("labelled_numeric_values_by_plan")
            .EnumerateArray().SelectMany(item => item.EnumerateArray()).Select(item => item.GetInt32()).ToArray();
        SequenceEqual([66, 62, 62, 55, 44, 44, 57, 56, 66, 42, 63], project1Lengths, "project1 labels");

        var vyritsa = sources[1];
        var vyritsaLengths = vyritsa.GetProperty("labelled_lengths_m").EnumerateArray()
            .Select(item => item.GetInt32()).ToArray();
        Equal(14, vyritsaLengths.Length, "Vyritsa loop count");
        Equal(942, vyritsaLengths.Sum(), "Vyritsa total");
        Equal(61, vyritsaLengths.Min(), "Vyritsa minimum");
        Equal(72, vyritsaLengths.Max(), "Vyritsa maximum");
        Equal("NOT_LABELLED_ON_SOURCE_SHEET", vyritsa.GetProperty("floor_mapping_status").GetString(),
            "Vyritsa floor mapping honesty");

        var morphology = reference.GetProperty("body_morphology");
        Equal("SINGLE_CONTINUOUS_COUNTERFLOW_SPIRAL", morphology.GetProperty("default").GetString(),
            "default body morphology");
        Equal("REJECT", morphology.GetProperty("independent_rectangular_subloops_in_one_open_room").GetString(),
            "independent subloop disposition");

        var exterior = reference.GetProperty("exterior_band");
        SequenceEqual([100, 200, 300], exterior.GetProperty("required_axis_offsets_mm").EnumerateArray()
            .Select(item => item.GetInt32()).ToArray(), "exterior offsets");
        Equal(500, exterior.GetProperty("next_field_axis_offset_mm").GetInt32(), "next field axis");
        Equal(200, exterior.GetProperty("field_pitch_mm").GetInt32(), "field pitch");
        Check(!exterior.GetProperty("direct_100mm_u_turn_allowed").GetBoolean(),
            "Reference accidentally allowed a 100 mm two-turn U-link.");

        var coverage = reference.GetProperty("coverage");
        Equal("R80_FILLETED_BODY_ONLY", coverage.GetProperty("physical_axis_geometry").GetString(),
            "coverage axis");
        Equal(200, coverage.GetProperty("hard_maximum_distance_mm").GetInt32(), "coverage maximum");
        Equal(0, coverage.GetProperty("unexplained_sample_over_hard_max_count").GetInt32(),
            "coverage outlier count");

        var routing = reference.GetProperty("routing");
        Equal(80, routing.GetProperty("minimum_bend_radius_mm").GetInt32(), "bend radius");
        Equal(3, routing.GetProperty("maximum_adjacent_transit_axes_at_100mm").GetInt32(),
            "100 mm transit bundle");
        Check(!routing.GetProperty("sleeves_required").GetBoolean(), "Reference reintroduced sleeves.");

        var lengths = reference.GetProperty("length_policy");
        Equal(40, lengths.GetProperty("hard_minimum_complete_length_m").GetInt32(), "hard minimum length");
        Equal(80, lengths.GetProperty("hard_maximum_complete_length_m").GetInt32(), "hard maximum length");
        var completeness = reference.GetProperty("project_completeness");
        Equal(2, completeness.GetProperty("expected_floor_count").GetInt32(), "expected floors");
        Check(!completeness.GetProperty("collector_symbol_without_floor_routes_counts_as_complete").GetBoolean(),
            "Collector-only second floor incorrectly became complete.");

        var rendering = reference.GetProperty("rendering");
        Equal("PHYSICAL_R80_FILLET_WHEN_WHOLE_CIRCUIT_IS_FEASIBLE",
            rendering.GetProperty("clean_horizontal_turn_geometry").GetString(), "clean R80 claim boundary");
        Equal("RAW_CONTROL_POLYLINE_WITH_SHARP_TURNS_REQUIRES_REWORK",
            rendering.GetProperty("infeasible_circuit_fallback").GetString(), "clean fallback honesty");
    }

    private static void SequenceEqual<T>(IReadOnlyList<T> expected, IReadOnlyList<T> actual, string label)
    {
        if (!expected.SequenceEqual(actual))
            throw new InvalidDataException($"{label}: expected [{string.Join(',', expected)}], got [{string.Join(',', actual)}].");
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
