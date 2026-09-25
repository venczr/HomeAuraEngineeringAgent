using HomeAura.NativeEditor;

internal static class EngineeringDiagnosticsValidation
{
    public static void Run()
    {
        DetailedBendAndWallViolationsAreReported();
        HorizontalR80ArcMustClearWallSolid();
        ExteriorBandUsesInnerWallFaceAndAllRoomCircuits();
    }

    private static void DetailedBendAndWallViolationsAreReported()
    {
        var bendProject = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };
        var bendCircuit = new ManualCircuit
        {
            Id = "BEND",
            Completed = true,
            OrderedPoints = [new(500, 1500), new(1500, 1500), new(1500, 1600), new(2500, 1600)],
        };
        bendProject.Circuits.Add(bendCircuit);
        var bend = CircuitAnalyzer.Analyze(bendProject, bendCircuit);
        Check(bend.BendRadiusViolations.Count == 1, "Expected one detailed R80 violation.");
        var violation = bend.BendRadiusViolations[0];
        Check(violation.SegmentIndex == 1, "R80 violation points at the wrong segment.");
        Check(Math.Abs(violation.AvailableLengthMm - 100) < 0.001 && violation.RequiredTangentLengthMm == 160,
            "R80 available/required tangent lengths are wrong.");

        var wallProject = RoomProject();
        var intrusionCircuit = new ManualCircuit
        {
            Id = "INTRUSION",
            RoomId = "ROOM",
            Completed = true,
            HeatingBodyStartIndex = 0,
            HeatingBodyEndIndex = 1,
            OrderedPoints = [new(1000, 500), new(2000, 500)],
        };
        wallProject.Circuits.Add(intrusionCircuit);
        var intrusion = CircuitAnalyzer.Analyze(wallProject, intrusionCircuit);
        Check(intrusion.HeatingBodyWallIntrusionDetails.Count == 1, "Expected one detailed body/wall intrusion.");
        var detail = intrusion.HeatingBodyWallIntrusionDetails[0];
        Check(detail.WallId == "EXT" && detail.CircuitSegmentIndex == 0 && Math.Abs(detail.IntrusionDepthMm - 100) < 0.001,
            "Body/wall detail has wrong wall, segment, or depth.");
    }

    private static void ExteriorBandUsesInnerWallFaceAndAllRoomCircuits()
    {
        var project = RoomProject();
        project.Windows.Add(new WindowOpening
        {
            Id = "WINDOW",
            WallId = "EXT",
            Start = new(1500, 500),
            End = new(2500, 500),
        });
        project.Circuits.AddRange([
            Lane("L1", 700, 700, 4300),
            Lane("L2", 800, 700, 4300),
            Lane("L3", 900, 700, 4300),
        ]);

        var analysis = CircuitAnalyzer.Analyze(project, project.Circuits[0]);
        Check(analysis.ExteriorWallBandCoverageDetails.Count == 3, "Exterior wall did not produce three lane details.");
        Check(analysis.Exterior3x100Pass, "Three jointly supplied lanes with full window coverage did not pass.");
        Check(analysis.ExteriorWallBandCoverageDetails.Select(item => item.TargetStart.Y).SequenceEqual([700, 800, 900]),
            "Targets were not offset 100/200/300 mm from the 100 mm inner wall face.");
        Check(analysis.ExteriorWallBandCoverageDetails.All(item => Math.Abs(item.RequiredSpanLengthMm - 3800) < 0.001),
            "Usable wall span was not trimmed by the two perpendicular 200 mm walls.");
        Check(analysis.ExteriorWallBandCoverageDetails.All(item => Math.Abs(item.CoveragePercent - 94.736842) < 0.001),
            "Trimmed wall-span coverage percentage is wrong.");
        Check(analysis.ExteriorWallBandCoverageDetails.All(item => Math.Abs(item.WindowCoveragePercent - 100) < 0.001),
            "Window projection coverage is wrong.");
        Check(analysis.ExteriorWallBandCoverageDetails[1].ContributingCircuitIds.SequenceEqual(["L2"]),
            "Aggregate room analysis did not retain the contributing circuit id.");
        Check(analysis.ExteriorWallBandUsefulSpanDetails.Count == 3 && analysis.Exterior3x100UsefulSpanPass,
            "The separately derived R80 useful span did not pass the full nested lane fixture.");
        Check(analysis.ExteriorWallBandUsefulSpanDetails.All(item =>
                Math.Abs(item.CornerEnvelopeMm - 100) < 0.001 &&
                Math.Abs(item.EffectiveRequiredSpanLengthMm - 3600) < 0.001 &&
                Math.Abs(item.CoveragePercent - 100) < 0.001 && item.UsefulSpanPass),
            "Useful spans were not derived from the wall faces and snapped R80 envelope.");
        Check(analysis.ExteriorWallBandCoverageDetails.All(item => Math.Abs(item.CoveragePercent - 94.736842) < 0.001),
            "Adding useful spans altered the legacy raw wall-face audit.");

        project.Circuits[2].OrderedPoints = [new(1000, 900), new(4000, 900)];
        analysis = CircuitAnalyzer.Analyze(project, project.Circuits[0]);
        var failedLane = analysis.ExteriorWallBandCoverageDetails.Single(item => item.LaneIndex == 3);
        Check(!analysis.Exterior3x100Pass && Math.Abs(failedLane.CoveragePercent - 78.947368) < 0.001,
            "A shortened third exterior lane incorrectly passed.");
        var failedUsefulLane = analysis.ExteriorWallBandUsefulSpanDetails.Single(item => item.LaneIndex == 3);
        Check(!analysis.Exterior3x100UsefulSpanPass && !failedUsefulLane.UsefulSpanPass &&
              Math.Abs(failedUsefulLane.CoveragePercent - 83.333333) < 0.001,
            "A shortened third lane bypassed the useful-span gate.");

        var report = CircuitAnalyzer.AnalyzeProject(project);
        Check(report.Circuits.Count == 3 && report.ExteriorWallLaneCount == 3,
            "Machine-readable project report omitted circuits or routing-rule context.");
    }

    private static void HorizontalR80ArcMustClearWallSolid()
    {
        var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 3000 };
        project.Walls.Add(new WallSegment
        {
            Id = "TURN_WALL",
            Start = new(2000, 500),
            End = new(2000, 2500),
            ThicknessMm = 100,
        });
        var circuit = new ManualCircuit
        {
            Id = "TRANSIT_TURN",
            Completed = true,
            SystemRole = "INTERFLOOR_SERVICE_LEG",
            OrderedPoints = [new(3000, 1000, 135), new(1900, 1000, 135), new(1900, 2200, 135)],
        };
        project.Circuits.Add(circuit);

        var failing = CircuitAnalyzer.Analyze(project, circuit);
        Check(failing.TransitWallIntersections == 1,
            "The intended straight perpendicular wall crossing was not retained as transit.");
        Check(failing.BendRadiusFeasible && failing.HorizontalTurnWallClearanceApplicable && failing.HorizontalTurnWallIntrusions == 1 &&
              !failing.HorizontalTurnWallClearancePass && !failing.EngineeringPass,
            "An R80 transit turn only 50 mm beyond the wall face incorrectly passed.");
        var detail = failing.HorizontalTurnWallIntrusionDetails.Single();
        Check(detail.WallId == "TURN_WALL" && detail.TurnPointIndex == 1 && detail.TurnRole == "TRANSIT" &&
              Math.Abs(detail.RadiusMm - 80) < 0.001 && detail.IntrusionDepthMm > 29.9,
            "Horizontal-turn wall diagnostics omitted the physical arc, role, or intrusion depth.");

        circuit.OrderedPoints[1].X = 1800;
        circuit.OrderedPoints[2].X = 1800;
        var passing = CircuitAnalyzer.Analyze(project, circuit);
        Check(passing.TransitWallIntersections == 1 && passing.HorizontalTurnWallIntrusions == 0 &&
              passing.HorizontalTurnWallClearancePass && passing.EngineeringPass,
            "An R80 transit turn 150 mm beyond the wall face did not pass while its straight crossing remained allowed.");
    }

    private static HomeAuraProject RoomProject()
    {
        var project = new HomeAuraProject { CanvasWidthMm = 5000, CanvasHeightMm = 4000 };
        project.Rooms.Add(new RoomZone
        {
            Id = "ROOM",
            Outline = [new(500, 500), new(4500, 500), new(4500, 3500), new(500, 3500)],
        });
        project.Walls.Add(new WallSegment
        {
            Id = "EXT",
            WallType = "EXTERIOR",
            ThicknessMm = 200,
            Start = new(500, 500),
            End = new(4500, 500),
        });
        project.Walls.AddRange([
            new WallSegment
            {
                Id = "LEFT",
                WallType = "INTERIOR",
                ThicknessMm = 200,
                Start = new(500, 500),
                End = new(500, 3500),
            },
            new WallSegment
            {
                Id = "RIGHT",
                WallType = "INTERIOR",
                ThicknessMm = 200,
                Start = new(4500, 500),
                End = new(4500, 3500),
            },
        ]);
        return project;
    }

    private static ManualCircuit Lane(string id, int y, int fromX, int toX) => new()
    {
        Id = id,
        RoomId = "ROOM",
        Completed = true,
        HeatingBodyStartIndex = 0,
        HeatingBodyEndIndex = 1,
        OrderedPoints = [new(fromX, y), new(toX, y)],
    };

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
