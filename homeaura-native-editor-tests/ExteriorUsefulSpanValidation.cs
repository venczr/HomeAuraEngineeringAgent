using HomeAura.NativeEditor;

internal static class ExteriorUsefulSpanValidation
{
    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "homeaura-native-editor", "examples", "proposals",
            "HA_TWO_FLOOR_R03_POINT3_ROUTES_183", "HomeAura_TwoFloor_R03Point3Routes_D183.homeaura.json");
        var project = HomeAuraProject.FromJson(File.ReadAllText(path));
        var circuit = project.Circuits.Single(item => item.Id == "F1-D171-C07");
        var analysis = CircuitAnalyzer.Analyze(project, circuit);

        Check(analysis.ExteriorWallBandCoverageDetails.Count == 6 && !analysis.Exterior3x100Pass,
            "D183 legacy raw wall-face audit must remain present and failing separately.");
        Check(analysis.ExteriorWallBandUsefulSpanDetails.Count == 6 &&
              analysis.Exterior3x100UsefulSpanApplicable && analysis.Exterior3x100UsefulSpanPass,
            "D183 nested-corner useful-span gate did not pass all six BODY lanes.");
        Check(analysis.ExteriorWallBandUsefulSpanDetails.All(item =>
                item.Derivation == "WALL_INNER_FACE_PARTITIONS_AND_SNAPPED_R80_ENVELOPE" &&
                Math.Abs(item.CornerEnvelopeMm - 100) < 0.001 &&
                item.ContiguousCoveragePass && item.NestedWithPreviousLanePass &&
                item.NestedCornerTaperPass && !item.StaggeredTurnoutEvaluated &&
                !item.StaggeredTurnoutPass &&
                item.StaggeredTurnoutReason == "NOT_REQUIRED_STRICT_NESTED_CORNER_TAPER" &&
                item.UsefulSpanMode == "STRICT_NESTED_CORNER_TAPER" && item.UsefulSpanPass &&
                Math.Abs(item.WindowCoveragePercent - 100) < 0.001 &&
                item.ContributingCircuitIds.SequenceEqual(["F1-D171-C07"])),
            "D183 useful-span provenance, nested topology, BODY ownership, or window projection changed.");

        ValidateWall(analysis, "FLOOR_1-W027", 7000,
            [7000, 6700, 6400], [100, 95.71428571428571, 91.42857142857143],
            territoryFrom: 12100, territoryTo: 19300, effectiveFrom: 12200, effectiveTo: 19200);
        ValidateWall(analysis, "FLOOR_1-W028", 4100,
            [4100, 3900, 3700], [100, 95.1219512195122, 90.2439024390244],
            territoryFrom: 16800, territoryTo: 21100, effectiveFrom: 16900, effectiveTo: 21000);

        var rawW027 = analysis.ExteriorWallBandCoverageDetails
            .Where(item => item.WallId == "FLOOR_1-W027").OrderBy(item => item.LaneIndex).ToArray();
        var rawW028 = analysis.ExteriorWallBandCoverageDetails
            .Where(item => item.WallId == "FLOOR_1-W028").OrderBy(item => item.LaneIndex).ToArray();
        Check(rawW027.All(item => Math.Abs(item.RequiredSpanLengthMm - 7200) < 0.001) &&
              rawW027[0].CoveragePass && rawW027[1].CoveragePass && !rawW027[2].CoveragePass,
            "D183 W027 raw 7.2 m audit was weakened or replaced.");
        Check(rawW028.All(item => Math.Abs(item.RequiredSpanLengthMm - 4800) < 0.001 && !item.CoveragePass),
            "D183 W028 raw 4.8 m audit was weakened or replaced.");
    }

    private static void ValidateWall(
        CircuitAnalysis analysis,
        string wallId,
        double requiredLength,
        IReadOnlyList<double> coveredLengths,
        IReadOnlyList<double> coveragePercents,
        int territoryFrom,
        int territoryTo,
        int effectiveFrom,
        int effectiveTo)
    {
        var rows = analysis.ExteriorWallBandUsefulSpanDetails
            .Where(item => item.WallId == wallId).OrderBy(item => item.LaneIndex).ToArray();
        Check(rows.Length == 3, $"{wallId} useful-span lane count changed.");
        for (var index = 0; index < rows.Length; index++)
        {
            var row = rows[index];
            Close(requiredLength, row.EffectiveRequiredSpanLengthMm, $"{wallId} L{index + 1} required span");
            Close(coveredLengths[index], row.CoveredSpanLengthMm, $"{wallId} L{index + 1} covered span");
            Close(coveragePercents[index], row.CoveragePercent, $"{wallId} L{index + 1} useful percent");
            var territory = row.SelectedTerritoryIntervals.Single();
            var effective = row.EffectiveRequiredIntervals.Single();
            if (wallId == "FLOOR_1-W027")
            {
                Check(territory.Start.Y == territoryFrom && territory.End.Y == territoryTo &&
                      effective.Start.Y == effectiveFrom && effective.End.Y == effectiveTo,
                    $"{wallId} L{index + 1} vertical territory/effective endpoints changed.");
            }
            else
            {
                Check(territory.Start.X == territoryFrom && territory.End.X == territoryTo &&
                      effective.Start.X == effectiveFrom && effective.End.X == effectiveTo,
                    $"{wallId} L{index + 1} partition-derived territory/effective endpoints changed.");
            }
        }
    }

    private static void Close(double expected, double actual, string label)
    {
        if (Math.Abs(expected - actual) > 0.000001)
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
