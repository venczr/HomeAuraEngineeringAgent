using System.Text.Json;
using HomeAura.NativeEditor;

internal static class OwnerAcceptedAnalogue171Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var directory = Path.Combine(root, "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171");
        var project = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(directory, "HomeAura_Floor1_OwnerAcceptedAnalogue_D171.homeaura.json")));
        Check(project.Circuits.Count == 13, "D171 must contain thirteen larger bodies");
        Check(project.Collectors.Single(item => item.Id == "K1").Ports == 26, "D171 K1 port count");
        Check(project.Circuits.Count(item => item.RoomId == "F1-R03") == 3, "D171 kitchen/living must use three bodies, not four");
        Check(project.Circuits.All(item => item.RoomId is not null && item.HeatingBodyStartIndex == 0 &&
                                                   item.HeatingBodyEndIndex == item.OrderedPoints.Count - 1), "D171 body ranges");

        var analyses = project.Circuits.Select(item => CircuitAnalyzer.Analyze(project, item)).ToArray();
        Check(analyses.All(item => item.HeatingBodyInsideAssignedRoom && item.HeatingBodyWallIntrusions == 0), "D171 room/wall placement");
        Check(analyses.All(item => item.SelfIntersections == 0 && item.InterCircuitIntersections == 0), "D171 body topology/contact");

        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_owner_accepted_analogue_contract.json")));
        var contract = document.RootElement;
        var owner = contract.GetProperty("sources").GetProperty("owner_ACCEPTED_reference");
        Check(owner.GetProperty("training_label").GetString() == "ACCEPTED", "D171 accepted owner reference");
        Check(owner.GetProperty("manual_circuit_count").GetInt32() == 2, "D171 reference circuit count");
        Check(owner.GetProperty("manual_length_spread_mm").GetInt32() == 4800, "D171 reference balance");
        Check(owner.GetProperty("manual_lengths_mm")[0].GetInt32() == 62100 && owner.GetProperty("manual_lengths_mm")[1].GetInt32() == 57300,
            "D171 reference lengths");
        Check(contract.GetProperty("allocation").GetProperty("kitchen_living_changed_from_4_to_3").GetBoolean(), "D171 4-to-3 correction");
        Check(contract.GetProperty("validation").GetProperty("owner_analogue_signature_pass_count").GetInt32() == 13, "D171 owner grammar count");
        Check(contract.GetProperty("validation").GetProperty("body_wall_intrusion_count").GetInt32() == 0, "D171 stored wall count");
        Check(!contract.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(), "D171 coverage honesty");
        Check(contract.GetProperty("complete_K1_route_count").GetInt32() == 0, "D171 must not overclaim complete K1 routes");

        var records = contract.GetProperty("body_records").EnumerateArray().ToDictionary(
            item => item.GetProperty("circuit_id").GetString()!, StringComparer.Ordinal);
        foreach (var circuit in project.Circuits)
        {
            var record = records[circuit.Id];
            var signature = record.GetProperty("owner_accepted_analogue_signature");
            Check(signature.GetProperty("orthogonal").GetBoolean() && signature.GetProperty("simple").GetBoolean(), $"{circuit.Id} owner topology");
            Check(signature.GetProperty("compact_asymmetric_centre_present").GetBoolean(), $"{circuit.Id} compact centre");
            Check(signature.GetProperty("field_interleave_mm").GetInt32() == 200 &&
                  signature.GetProperty("inward_frame_step_mm").GetInt32() == 400, $"{circuit.Id} owner pitch grammar");
            var sides = record.GetProperty("exterior_sides").EnumerateArray().Select(item => item.GetString()!).ToHashSet();
            if (sides.Count == 0) continue;
            var segments = circuit.OrderedPoints.Zip(circuit.OrderedPoints.Skip(1)).ToArray();
            var minX = circuit.OrderedPoints.Min(item => item.X); var maxX = circuit.OrderedPoints.Max(item => item.X);
            var minY = circuit.OrderedPoints.Min(item => item.Y); var maxY = circuit.OrderedPoints.Max(item => item.Y);
            if (sides.Contains("L")) RequireLevels(segments.Where(s => s.First.X == s.Second.X).Select(s => s.First.X), minX, +100, circuit.Id, "L");
            if (sides.Contains("R")) RequireLevels(segments.Where(s => s.First.X == s.Second.X).Select(s => s.First.X), maxX, -100, circuit.Id, "R");
            if (sides.Contains("T")) RequireLevels(segments.Where(s => s.First.Y == s.Second.Y).Select(s => s.First.Y), minY, +100, circuit.Id, "T");
            if (sides.Contains("B")) RequireLevels(segments.Where(s => s.First.Y == s.Second.Y).Select(s => s.First.Y), maxY, -100, circuit.Id, "B");
        }
        Check(File.Exists(Path.Combine(directory, "HomeAura_Floor1_D171_Clean_View.png")), "D171 clean render");
    }

    private static void RequireLevels(IEnumerable<int> source, int first, int delta, string circuit, string side)
    {
        var levels = source.ToHashSet();
        Check(levels.Contains(first) && levels.Contains(first + delta) && levels.Contains(first + 2 * delta), $"{circuit} exterior {side} 3x100");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
