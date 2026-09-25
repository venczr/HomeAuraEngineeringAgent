using System.Text.Json;
using HomeAura.NativeEditor;

internal static class OwnerMarkupCorrection170Validation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var directory = Path.Combine(root, "homeaura-native-editor", "examples", "proposals", "HA_TWO_FLOOR_FLOOR1_USER_MARKUP_CORRECTION_170");
        var project = HomeAuraProject.FromJson(File.ReadAllText(Path.Combine(directory, "HomeAura_Floor1_UserMarkupCorrection_D170.homeaura.json")));
        Check(project.Circuits.Count == 14, "D170 body count");
        Check(project.Collectors.Single(item => item.Id == "K1").Ports == 28, "D170 K1 ports");
        Check(project.Circuits.All(item => item.RoomId is not null && item.HeatingBodyStartIndex == 0 &&
                                                   item.HeatingBodyEndIndex == item.OrderedPoints.Count - 1), "D170 body metadata");
        var analyses = project.Circuits.Select(item => CircuitAnalyzer.Analyze(project, item)).ToArray();
        Check(analyses.All(item => item.HeatingBodyInsideAssignedRoom && item.HeatingBodyWallIntrusions == 0), "D170 wall/room placement");
        Check(analyses.All(item => item.SelfIntersections == 0 && item.InterCircuitIntersections == 0), "D170 body topology/contact");

        using var document = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "floor1_user_markup_correction_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("validation").GetProperty("body_wall_intrusion_count").GetInt32() == 0, "D170 stored wall count");
        Check(!contract.GetProperty("coverage_diagnostic").GetProperty("full_coverage_claimed").GetBoolean(), "D170 coverage honesty");
        var records = contract.GetProperty("body_records").EnumerateArray().ToDictionary(
            item => item.GetProperty("circuit_id").GetString()!, StringComparer.Ordinal);
        foreach (var circuit in project.Circuits)
        {
            var sides = records[circuit.Id].GetProperty("exterior_sides").EnumerateArray().Select(item => item.GetString()!).ToHashSet();
            if (sides.Count == 0) continue;
            var segments = circuit.OrderedPoints.Zip(circuit.OrderedPoints.Skip(1)).ToArray();
            var minX = circuit.OrderedPoints.Min(item => item.X); var maxX = circuit.OrderedPoints.Max(item => item.X);
            var minY = circuit.OrderedPoints.Min(item => item.Y); var maxY = circuit.OrderedPoints.Max(item => item.Y);
            if (sides.Contains("L")) RequireLevels(segments.Where(s => s.First.X == s.Second.X).Select(s => s.First.X), minX, +100, circuit.Id, "L");
            if (sides.Contains("R")) RequireLevels(segments.Where(s => s.First.X == s.Second.X).Select(s => s.First.X), maxX, -100, circuit.Id, "R");
            if (sides.Contains("T")) RequireLevels(segments.Where(s => s.First.Y == s.Second.Y).Select(s => s.First.Y), minY, +100, circuit.Id, "T");
            if (sides.Contains("B")) RequireLevels(segments.Where(s => s.First.Y == s.Second.Y).Select(s => s.First.Y), maxY, -100, circuit.Id, "B");
        }
        var hall = project.Circuits.Single(item => item.RoomId == "F1-R02");
        Check(Contains(hall.OrderedPoints, [(13100, 12400), (13100, 13400), (13300, 13400), (13300, 12600)]), "D170 owner-marked hall snake");
        Check(File.Exists(Path.Combine(directory, "HomeAura_Floor1_D170_Clean_View.png")), "D170 render");
    }

    private static void RequireLevels(IEnumerable<int> source, int first, int delta, string circuit, string side)
    {
        var levels = source.ToHashSet();
        Check(levels.Contains(first) && levels.Contains(first + delta) && levels.Contains(first + 2 * delta), $"{circuit} exterior {side} 3x100");
    }

    private static bool Contains(IReadOnlyList<PointMm> points, IReadOnlyList<(int X, int Y)> expected)
    {
        for (var start = 0; start + expected.Count <= points.Count; start++)
            if (expected.Select((value, index) => points[start + index].X == value.X && points[start + index].Y == value.Y).All(value => value)) return true;
        return false;
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
