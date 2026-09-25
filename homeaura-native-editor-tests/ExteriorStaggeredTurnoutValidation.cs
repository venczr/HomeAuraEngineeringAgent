using HomeAura.NativeEditor;

internal static class ExteriorStaggeredTurnoutValidation
{
    public static void Run()
    {
        var source = LoadR07();
        PositiveR07AlternatingTurnout(source);
        ExtensionBeyondOneEnvelopeIsRejected(source);
        ExtensionInsideWindowIsRejected(source);
        AggregateRoomContactIsRejected(source);
        Direct100UTurnIsRejected(source);
    }

    private static void PositiveR07AlternatingTurnout(HomeAuraProject project)
    {
        var analysis = AnalyzeOwner(project);
        Check(!analysis.Exterior3x100Pass && analysis.Exterior3x100UsefulSpanPass,
            "R07 must retain the failing raw audit while its bounded staggered useful span passes.");
        var rows = analysis.ExteriorWallBandUsefulSpanDetails
            .Where(item => item.WallId == "FLOOR_1-W008").OrderBy(item => item.LaneIndex).ToArray();
        Check(rows.Length == 3, "R07 W008 did not expose three exterior lanes.");
        Close(100, rows[0].CoveragePercent, "R07 L1 coverage");
        Close(95.83333333333333, rows[1].CoveragePercent, "R07 L2 coverage");
        Close(91.66666666666667, rows[2].CoveragePercent, "R07 L3 coverage");
        Check(rows.All(item => Math.Abs(item.WindowCoveragePercent - 100) < 0.000001),
            "R07 window projection changed.");
        Check(rows[0].UsefulSpanMode == "STRICT_NESTED_CORNER_TAPER" &&
              rows[1].UsefulSpanMode == "STRICT_NESTED_CORNER_TAPER",
            "R07 L1/L2 ceased to be strict nested lanes.");

        var staggered = rows[2];
        Check(!staggered.NestedCornerTaperPass && staggered.StaggeredTurnoutEvaluated &&
              staggered.StaggeredTurnoutPass && staggered.UsefulSpanPass &&
              staggered.UsefulSpanMode == "STAGGERED_ALTERNATING_TURNOUT" &&
              staggered.StaggeredTurnoutReason == "PASS_STAGGERED_ALTERNATING_TURNOUT_OUTSIDE_REQUIRED_WINDOW",
            "R07 L3 did not use the explicit staggered-turnout path.");
        Close(0, staggered.PreviousLaneStartExtensionMm, "R07 L3 start extension");
        Close(100, staggered.PreviousLaneEndExtensionMm, "R07 L3 end extension");
        Check(staggered.SingleEndpointExtensionPass && staggered.ExtensionWithinCornerEnvelopePass &&
              staggered.AlternatingEndpointPass && staggered.OppositeTaperWithinAllowancePass &&
              staggered.ExtensionOutsideRequiredWindowPass,
            "R07 L3 bounded endpoint evidence changed.");
        Check(staggered.AggregateRoomR80Pass == true && staggered.AggregateRoomSelfContactPass == true &&
              staggered.AggregateRoomInterCircuitContactPass == true && staggered.AggregateRoomBodyWallPass == true &&
              staggered.AggregateRoomHorizontalTurnWallPass == true &&
              staggered.AggregateRoomDirect100UTurnPass == true && staggered.AggregateRoomPhysicalGatePass == true,
            "R07 aggregate room physical gate did not pass cleanly.");
        Close(200, staggered.AggregateRoomMinimumSegmentLengthMm ?? -1, "R07 aggregate minimum segment");
    }

    private static void ExtensionBeyondOneEnvelopeIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Circuits.Single(item => item.Id == "F1-D171-C04").OrderedPoints[0].Y = 14800;
        var lane = AnalyzeOwner(project).ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Close(200, lane.PreviousLaneEndExtensionMm, "R07 excessive extension");
        Check(lane.StaggeredTurnoutEvaluated && lane.SingleEndpointExtensionPass &&
              !lane.ExtensionWithinCornerEnvelopePass && !lane.StaggeredTurnoutPass && !lane.UsefulSpanPass &&
              lane.StaggeredTurnoutReason == "REJECT_STAGGERED_EXTENSION_EXCEEDS_CORNER_ENVELOPE",
            "A 200 mm staggered endpoint bypassed the one-envelope limit.");
    }

    private static void ExtensionInsideWindowIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        var window = project.Windows.Single(item => item.Id == "F1-WIN-02");
        window.Start.Y = 14900;
        window.End.Y = 15000;
        var lane = AnalyzeOwner(project).ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Close(100, lane.WindowCoveragePercent, "R07 moved-window L3 coverage");
        Check(lane.ExtensionWithinCornerEnvelopePass && !lane.ExtensionOutsideRequiredWindowPass &&
              !lane.StaggeredTurnoutPass && !lane.UsefulSpanPass &&
              lane.StaggeredTurnoutReason == "REJECT_STAGGERED_EXTENSION_OVERLAPS_REQUIRED_WINDOW",
            "A staggered endpoint inside the required window projection incorrectly passed.");
    }

    private static void AggregateRoomContactIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Circuits.Add(new ManualCircuit
        {
            Id = "R07-CONTACT-NEGATIVE",
            Name = "R07 contact-negative control",
            RoomId = "F1-R07",
            Completed = true,
            SystemRole = "FLOOR_HEATING_AXIS",
            AxisElevationMm = 108,
            HeatingBodyStartIndex = 0,
            HeatingBodyEndIndex = 1,
            OrderedPoints = [new(8000, 13300, 108), new(10000, 13300, 108)],
        });
        var lane = AnalyzeOwner(project).ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Check(lane.AggregateRoomR80Pass == true && lane.AggregateRoomSelfContactPass == true &&
              lane.AggregateRoomInterCircuitContactPass == false && lane.AggregateRoomPhysicalGatePass == false &&
              !lane.StaggeredTurnoutPass && !lane.UsefulSpanPass &&
              lane.StaggeredTurnoutReason == "REJECT_STAGGERED_AGGREGATE_ROOM_INTER_CIRCUIT_CONTACT",
            $"An aggregate R07 room contact bypassed the staggered-turnout physical gate: " +
            $"R80={lane.AggregateRoomR80Pass}, self={lane.AggregateRoomSelfContactPass}, " +
            $"inter={lane.AggregateRoomInterCircuitContactPass}, physical={lane.AggregateRoomPhysicalGatePass}, " +
            $"stagger={lane.StaggeredTurnoutPass}, useful={lane.UsefulSpanPass}, reason={lane.StaggeredTurnoutReason}.");
    }

    private static void Direct100UTurnIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Circuits.Add(new ManualCircuit
        {
            Id = "R07-DIRECT-U100-NEGATIVE",
            Name = "R07 direct-100-U negative control",
            RoomId = "F1-R07",
            Completed = true,
            SystemRole = "FLOOR_HEATING_AXIS",
            AxisElevationMm = 108,
            HeatingBodyStartIndex = 0,
            HeatingBodyEndIndex = 3,
            OrderedPoints =
            [
                new(10300, 12700, 108),
                new(10500, 12700, 108),
                new(10500, 12800, 108),
                new(10300, 12800, 108),
            ],
        });
        var lane = AnalyzeOwner(project).ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Check(lane.AggregateRoomDirect100UTurnPass == false && lane.AggregateRoomPhysicalGatePass == false &&
              !lane.StaggeredTurnoutPass && !lane.UsefulSpanPass &&
              lane.StaggeredTurnoutReason == "REJECT_STAGGERED_DIRECT_100MM_U_TURN",
            $"A direct 100 mm U-turn bypassed the explicit staggered-turnout prohibition: " +
            $"direct={lane.AggregateRoomDirect100UTurnPass}, R80={lane.AggregateRoomR80Pass}, " +
            $"physical={lane.AggregateRoomPhysicalGatePass}, reason={lane.StaggeredTurnoutReason}.");
    }

    private static CircuitAnalysis AnalyzeOwner(HomeAuraProject project) =>
        CircuitAnalyzer.Analyze(project, project.Circuits.Single(item => item.Id == "F1-D171-C03"));

    private static HomeAuraProject LoadR07()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "tmp", "reports", "R07_Strict_Distributed_BODY_candidate.homeaura.json");
        return HomeAuraProject.FromJson(File.ReadAllText(path));
    }

    private static HomeAuraProject Clone(HomeAuraProject project) => HomeAuraProject.FromJson(project.ToJson());

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
