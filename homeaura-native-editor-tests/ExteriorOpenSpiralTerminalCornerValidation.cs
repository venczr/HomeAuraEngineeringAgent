using HomeAura.NativeEditor;

internal static class ExteriorOpenSpiralTerminalCornerValidation
{
    public static void Run()
    {
        var source = LoadC12();
        PositiveWindowlessTerminalCorner(source);
        ServiceSideTerminalCornerPasses(source);
        CollinearExteriorDoesNotFormCorner();
        OppositeWallCornerCannotSatisfyServiceSideAdjacency(source);
        MissingExteriorWallEvidenceIsRejected(source);
        SingleExteriorWallIsRejected(source);
        MultipleBodyRangesAreRejected(source);
        TerminalWindowIsRejected(source);
        GlobalTransitContactIsRejected(source);
        ShortCollinearSegmentIsRejected(source);
        AggregateSelfContactIsRejected(source);
        Direct100UTurnIsRejected(source);
        MaterializedTerminalRampCompletesExactlyOneLane();
        OppositeEndGapCannotUseSharedCornerRampException();
        FlatAdjacentTransitCannotCompleteLane();
        OverhangingAdjacentRampCannotCompleteLane();
        WindowedGapCannotBeCompletedByRamp();
        ContactingRampCannotCompleteLane();
    }

    private static void MissingExteriorWallEvidenceIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Walls.Add(new WallSegment
        {
            Id = "C12-MISSING-EXTERIOR-EVIDENCE-NEGATIVE",
            Start = new PointMm(16400, 19900),
            End = new PointMm(16700, 19900),
            WallType = "EXTERIOR",
            ThicknessMm = 400,
        });

        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && open.ExteriorWallCount == 5 && open.Lanes.Count == 12 &&
              open.Reason == "REJECT_OPEN_SPIRAL_INCOMPLETE_EXTERIOR_LANE_SET",
            $"A fully uncovered exterior wall disappeared from the open-spiral gate: {open.Reason}.");
    }

    private static void OppositeWallCornerCannotSatisfyServiceSideAdjacency(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        circuit.OrderedPoints =
        [
            new(16400, 20200, 108), new(16400, 22000, 108), new(12500, 22000, 108),
            new(12500, 20200, 108), new(16200, 20200, 108), new(16200, 21800, 108),
            new(12700, 21800, 108), new(12700, 20400, 108), new(15800, 20400, 108),
            new(15800, 21400, 108), new(13100, 21400, 108), new(13100, 20800, 108),
            new(15300, 20800, 108), new(15300, 21000, 108), new(13400, 21000, 108),
            new(13400, 21200, 108), new(15600, 21200, 108), new(15600, 20600, 108),
            new(12900, 20600, 108), new(12900, 21600, 108), new(16000, 21600, 108),
            new(16000, 20300, 108), new(12600, 20300, 108), new(12600, 21900, 108),
            new(16300, 21900, 108), new(16300, 20300, 108),
        ];
        circuit.HeatingBodyEndIndex = 25;
        project.Walls.Single(item => item.Id == "FLOOR_1-W031").WallType = "INTERIOR";

        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && open.ExactlyOneTerminalWallPass &&
              !open.TerminalWallAdjacentStrictExteriorPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_TERMINAL_WALL_HAS_NO_ADJACENT_STRICT_EXTERIOR",
            $"The opposite W033 corner incorrectly satisfied the W030 END adjacency: {open.Reason}.");
    }

    private static void ServiceSideTerminalCornerPasses(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        ConfigureServiceSideTerminal(circuit);
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && open.Pass && open.TerminalWallId == "FLOOR_1-W030" &&
              open.TerminalSide == "END" && open.TerminalTaperSequencePass &&
              open.AllOtherWallsStrictNestedPass && open.TerminalWallAdjacentStrictExteriorPass,
            $"The service-side C12 counterflow was not recognized: {open.Reason}.");
        var terminal = open.Lanes.Where(item => item.WallId == "FLOOR_1-W030")
            .OrderBy(item => item.LaneIndex).ToArray();
        Check(terminal.Length == 3 && terminal.All(item => item.OpenTerminalLanePass &&
                                                    item.StartTerminalTaperMm < 0.000001),
            "The service-side terminal tapers are not aligned on W030 END.");
        Close(200, terminal[0].EndTerminalTaperMm, "service-side L1 taper");
        Close(300, terminal[1].EndTerminalTaperMm, "service-side L2 taper");
        Close(400, terminal[2].EndTerminalTaperMm, "service-side L3 taper");
        Check(open.Lanes.Where(item => item.WallId is "FLOOR_1-W031" or "FLOOR_1-W032")
                  .All(item => Math.Abs(item.WindowCoveragePercent - 100) < 0.000001),
            "The service-side counterflow no longer covers every required window lane.");
    }

    private static void CollinearExteriorDoesNotFormCorner()
    {
        var horizontal = new WallSegment
        {
            Id = "C12-CORNER-HORIZONTAL",
            Start = new PointMm(0, 0),
            End = new PointMm(1000, 0),
            WallType = "EXTERIOR",
            ThicknessMm = 200,
        };
        var collinear = new WallSegment
        {
            Id = "C12-CORNER-COLLINEAR",
            Start = new PointMm(1000, 0),
            End = new PointMm(2000, 0),
            WallType = "EXTERIOR",
            ThicknessMm = 200,
        };
        var perpendicular = new WallSegment
        {
            Id = "C12-CORNER-PERPENDICULAR",
            Start = new PointMm(1000, 0),
            End = new PointMm(1000, 1000),
            WallType = "EXTERIOR",
            ThicknessMm = 200,
        };
        var method = typeof(CircuitAnalyzer).GetMethod("AxisWallsPerpendicular",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)
            ?? throw new InvalidDataException("AxisWallsPerpendicular diagnostic helper is missing.");
        var collinearPass = (bool)(method.Invoke(null, [horizontal, collinear]) ?? false);
        var rightAnglePass = (bool)(method.Invoke(null, [horizontal, perpendicular]) ?? false);
        Check(!collinearPass && rightAnglePass,
            "The corner predicate did not distinguish a collinear join from a 90-degree exterior corner.");
    }

    private static void GlobalTransitContactIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Circuits.Add(new ManualCircuit
        {
            Id = "C12-GLOBAL-CONTACT-NEGATIVE",
            Name = "C12 global contact negative",
            Completed = true,
            SystemRole = "FLOOR_SERVICE_LEG",
            RoutingLayer = "HEATING_PLANE",
            AxisElevationMm = 108,
            OrderedPoints = [new PointMm(14000, 20000, 108), new PointMm(14000, 20500, 108)],
        });
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && !open.GlobalInterCircuitContactPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_GLOBAL_INTER_CIRCUIT_CONTACT",
            $"A global transit/body contact bypassed the open-spiral gate: {open.Reason}.");
    }

    private static void PositiveWindowlessTerminalCorner(HomeAuraProject project)
    {
        var analysis = AnalyzeC12(project);
        Check(!analysis.Exterior3x100UsefulSpanPass,
            "The legacy constant-envelope useful-span audit must remain visible and false for C12.");
        var open = analysis.ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && open.Pass && analysis.ExteriorOpenSpiralTerminalCornerPass &&
              open.Reason == "PASS_OPEN_SPIRAL_TERMINAL_CORNER_ON_WINDOWLESS_WALL" &&
              open.TerminalWallId == "FLOOR_1-W033" && open.TerminalSide == "START",
            $"C12 open-spiral terminal corner did not pass honestly: {open.Reason}.");
        Check(open.HeatingBodyCircuitCount == 1 && open.HeatingBodyRangeCount == 1 &&
              open.ExteriorWallCount == 4 && open.RequiredLaneCount == 3 &&
              open.ExactlyOneTerminalWallPass && open.AllOtherWallsStrictNestedPass &&
              open.TerminalWallHasNoRequiredWindowPass && open.TerminalWallAdjacentStrictExteriorPass &&
              open.AlignedTerminalSidePass &&
              open.TerminalTaperSequencePass && open.BasicTopologyPass &&
              open.GlobalInterCircuitContactPass && open.AggregateRoomPhysicalGatePass &&
              open.AggregateRoomDirect100UTurnPass && open.AggregateRoomMinimumSegmentLengthPass,
            "C12 aggregate open-spiral evidence changed.");
        Close(200, open.AggregateRoomMinimumSegmentLengthMm, "C12 minimum ordered segment");

        var strict = open.Lanes.Where(item => item.WallId != "FLOOR_1-W033").ToArray();
        Check(strict.Length == 9 && strict.All(item => item.StrictNestedLanePass &&
                                               Math.Abs(item.CoveragePercent - 100) < 0.000001 &&
                                               Math.Abs(item.WindowCoveragePercent - 100) < 0.000001),
            "C12 non-terminal perimeter/window lanes are no longer exact nested spans.");
        var terminal = open.Lanes.Where(item => item.WallId == "FLOOR_1-W033")
            .OrderBy(item => item.LaneIndex).ToArray();
        Check(terminal.Length == 3 && terminal.All(item => item.OpenTerminalLanePass &&
                                                    !item.StrictNestedLanePass &&
                                                    item.EndTerminalTaperMm < 0.000001 &&
                                                    item.WindowRequiredSpanLengthMm < 0.000001),
            "C12 terminal-wall lanes ceased to be one aligned windowless opening.");
        Close(200, terminal[0].StartTerminalTaperMm, "C12 terminal L1 taper");
        Close(300, terminal[1].StartTerminalTaperMm, "C12 terminal L2 taper");
        Close(400, terminal[2].StartTerminalTaperMm, "C12 terminal L3 taper");
        Close(200, terminal[0].OpenTerminalTaperAllowanceMm, "C12 terminal L1 allowance");
        Close(300, terminal[1].OpenTerminalTaperAllowanceMm, "C12 terminal L2 allowance");
        Close(400, terminal[2].OpenTerminalTaperAllowanceMm, "C12 terminal L3 allowance");
    }

    private static void SingleExteriorWallIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        foreach (var wall in project.Walls.Where(item => item.Id is
                     "FLOOR_1-W030" or "FLOOR_1-W031" or "FLOOR_1-W032"))
            wall.WallType = "INTERIOR";
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && open.ExactlyOneTerminalWallPass &&
              !open.TerminalWallAdjacentStrictExteriorPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_TERMINAL_WALL_HAS_NO_ADJACENT_STRICT_EXTERIOR",
            $"A one-wall facade was accepted as a terminal corner: {open.Reason}.");
    }

    private static void MultipleBodyRangesAreRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        circuit.HeatingBodyStartIndex = null;
        circuit.HeatingBodyEndIndex = null;
        circuit.HeatingBodyRanges =
        [
            new HeatingBodyRange { StartIndex = 0, EndIndex = 11 },
            new HeatingBodyRange { StartIndex = 12, EndIndex = 23 },
        ];
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && open.HeatingBodyRangeCount == 2 &&
              open.Reason == "REJECT_OPEN_SPIRAL_REQUIRES_ONE_COHERENT_BODY_RANGE",
            $"Disconnected BODY ranges were accepted as one coherent spiral: {open.Reason}.");
    }

    private static void ShortCollinearSegmentIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        circuit.OrderedPoints.Insert(1, new PointMm(12600, 20200, 108));
        circuit.HeatingBodyEndIndex += 1;
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && !open.AggregateRoomMinimumSegmentLengthPass &&
              Math.Abs(open.AggregateRoomMinimumSegmentLengthMm - 100) < 0.000001 &&
              open.Reason == "REJECT_OPEN_SPIRAL_MINIMUM_SEGMENT_LENGTH",
            $"A 100 mm ordered BODY segment bypassed the open-spiral gate: {open.Reason}.");
    }

    private static void TerminalWindowIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        project.Windows.Add(new WindowOpening
        {
            Id = "C12-TERMINAL-WINDOW-NEGATIVE",
            WallId = "FLOOR_1-W033",
            Start = new PointMm(12200, 20200),
            End = new PointMm(12200, 20400),
        });
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && open.ExactlyOneTerminalWallPass &&
              !open.TerminalWallHasNoRequiredWindowPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_TERMINAL_WALL_HAS_REQUIRED_WINDOW",
            $"A required window was hidden inside the open terminal corner: {open.Reason}.");
    }

    private static void AggregateSelfContactIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        circuit.OrderedPoints.InsertRange(13,
        [
            new PointMm(13600, 21200, 108),
            new PointMm(13600, 20800, 108),
            new PointMm(13000, 20800, 108),
            new PointMm(13000, 21200, 108),
        ]);
        circuit.HeatingBodyEndIndex += 4;
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && !open.AggregateRoomPhysicalGatePass &&
              open.AggregateRoomDirect100UTurnPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_SELF_CONTACT",
            $"A self-contact bypassed the open-spiral physical gate: {open.Reason}.");
    }

    private static void Direct100UTurnIsRejected(HomeAuraProject source)
    {
        var project = Clone(source);
        var circuit = C12(project);
        circuit.OrderedPoints.InsertRange(12,
        [
            new PointMm(15600, 21400, 108),
            new PointMm(15600, 21300, 108),
            new PointMm(13100, 21300, 108),
        ]);
        circuit.HeatingBodyEndIndex += 3;
        var open = AnalyzeC12(project).ExteriorOpenSpiralTerminalCorner;
        Check(open.Applicable && !open.Pass && !open.AggregateRoomDirect100UTurnPass &&
              open.Reason == "REJECT_OPEN_SPIRAL_DIRECT_100MM_U_TURN",
            $"A direct 100 mm U-turn bypassed the open-spiral gate: {open.Reason}.");
    }

    private static void MaterializedTerminalRampCompletesExactlyOneLane()
    {
        var analysis = AnalyzeC12(LoadMaterializedRampCompletion());
        var baseOpen = analysis.ExteriorOpenSpiralTerminalCorner;
        var ramp = analysis.ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(baseOpen.Applicable && !baseOpen.Pass &&
              baseOpen.Reason == "REJECT_OPEN_SPIRAL_NON_TERMINAL_WALL_NOT_STRICT_NESTED",
            $"The BODY-only open evidence unexpectedly changed: {baseOpen.Reason}.");
        Check(ramp.Applicable && ramp.Pass &&
              ramp.Reason == "PASS_MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE" &&
              ramp.BodyRangeStartIndex == 8 && ramp.BodyRangeEndIndex == 31 &&
              ramp.BodyEndpointSide == "END" && ramp.CircuitSegmentIndex == 31 &&
              ramp.TransitionKind == "S_BEND_R80" && ramp.TransitionMaterializedPass &&
              ramp.WallId == "FLOOR_1-W030" && ramp.LaneIndex == 2 &&
              ramp.CompletionCandidateCount == 1 && ramp.AdjacentBodyEndpointPass &&
              ramp.SameHeadingContinuationPass && ramp.ExactGapMatchPass &&
              ramp.WindowlessGapPass && ramp.NoTerminalWallOrOtherLaneContributionPass &&
              ramp.DeficientWallSharesOpenCornerPass && ramp.GapAtSharedOpenCornerPass &&
              ramp.AssignedRoomWallClearPass && ramp.FullCircuitPhysicalGatePass &&
              ramp.NativeCollectorTerminalTolerancePass && ramp.GlobalInterCircuitContactPass &&
              ramp.AugmentedStrictLanePass && ramp.AugmentedAllNonTerminalWallsStrictPass &&
              ramp.AugmentedOpenCornerAdjacencyPass && ramp.OpenTerminalWallId == "FLOOR_1-W033" &&
              ramp.OpenTerminalSide == "START",
            $"The qualified C12 materialized ramp was not accepted: {ramp.Reason}.");
        Close(200, ramp.MissingLengthMm, "materialized ramp missing interval");
        Close(200, ramp.RampProjectedLengthMm, "materialized ramp projection");
        Close(100, ramp.AugmentedCoveragePercent, "materialized ramp augmented coverage");
        Close(100, ramp.AugmentedWindowCoveragePercent, "materialized ramp window coverage");
        Check(ramp.MissingInterval is not null && ramp.RampProjectedInterval is not null &&
              ramp.MissingInterval.Start.X == 12600 && ramp.MissingInterval.End.X == 12800 &&
              ramp.RampProjectedInterval.Start.X == 12600 && ramp.RampProjectedInterval.End.X == 12800,
            "The exact W030-L2 completion interval changed.");
        Check(!analysis.Exterior3x100Pass && !analysis.Exterior3x100UsefulSpanPass && !analysis.DesignPass,
            "The additive ramp evidence must not rewrite raw/useful/DesignPass semantics.");
        // NativeCollectorTerminalTolerancePass is only the bounded 4100 mm terminal-grid tolerance;
        // it deliberately is not Eurocone continuity evidence.
    }

    private static void OppositeEndGapCannotUseSharedCornerRampException()
    {
        var project = LoadMaterializedRampCompletion();
        var circuit = C12(project);
        circuit.OrderedPoints.RemoveRange(31, circuit.OrderedPoints.Count - 31);
        circuit.OrderedPoints.AddRange(
        [
            new PointMm(16300, 20100, 108),
            new PointMm(12600, 20100, 108),
            new PointMm(12600, 20300, 108),
            new PointMm(16100, 20300, 108),
            new PointMm(16300, 20300, 70),
        ]);
        circuit.HeatingBodyRanges = [new HeatingBodyRange { StartIndex = 8, EndIndex = 34 }];
        circuit.VerticalTransitions.RemoveAll(item => item.SegmentIndex >= 31);
        circuit.VerticalTransitions.Add(new VerticalTransition
        {
            SegmentIndex = 34,
            Kind = "S_BEND_R80",
            RadiusMm = 80,
            StartTangentLengthMm = 16.48188564314004,
            EndTangentLengthMm = 79.99999999999969,
            ArcSamplesPerHalf = 12,
        });

        var ramp = AnalyzeC12(project).ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(ramp.Applicable && !ramp.Pass && ramp.CompletionCandidateCount == 1 &&
              ramp.DeficientWallSharesOpenCornerPass && !ramp.GapAtSharedOpenCornerPass &&
              ramp.Reason == "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_NOT_AT_SHARED_OPEN_CORNER",
            $"An opposite-end W030 gap incorrectly borrowed the W033 shared-corner exception: {ramp.Reason}.");
    }

    private static void FlatAdjacentTransitCannotCompleteLane()
    {
        var project = LoadMaterializedRampCompletion();
        var circuit = C12(project);
        circuit.OrderedPoints[32].Z = 108;
        circuit.VerticalTransitions.RemoveAll(item => item.SegmentIndex == 31);
        var ramp = AnalyzeC12(project).ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(ramp.Applicable && !ramp.Pass && ramp.CompletionCandidateCount == 1 &&
              !ramp.TransitionMaterializedPass &&
              ramp.Reason == "REJECT_MATERIALIZED_TERMINAL_RAMP_S_BEND_NOT_MATERIALIZED",
            $"A flat adjacent TRANSIT segment was counted as physical lane completion: {ramp.Reason}.");
    }

    private static void OverhangingAdjacentRampCannotCompleteLane()
    {
        var project = LoadMaterializedRampCompletion();
        var circuit = C12(project);
        circuit.OrderedPoints[32].X = 12500;
        circuit.OrderedPoints[33].X = 12500;
        circuit.VerticalTransitions.Single(item => item.SegmentIndex == 31).EndTangentLengthMm += 100;
        var ramp = AnalyzeC12(project).ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(ramp.Applicable && !ramp.Pass && ramp.CompletionCandidateCount == 0 &&
              ramp.Reason == "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_EXACTLY_ONE_ADJACENT_CANDIDATE",
            $"An overhanging adjacent ramp was accepted as an exact gap match: {ramp.Reason}.");
    }

    private static void WindowedGapCannotBeCompletedByRamp()
    {
        var project = LoadMaterializedRampCompletion();
        project.Windows.Add(new WindowOpening
        {
            Id = "C12-RAMP-WINDOW-NEGATIVE",
            WallId = "FLOOR_1-W030",
            Start = new PointMm(12600, 19900),
            End = new PointMm(12800, 19900),
        });
        var ramp = AnalyzeC12(project).ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(ramp.Applicable && !ramp.Pass && !ramp.WindowlessGapPass &&
              ramp.Reason == "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_OVERLAPS_REQUIRED_WINDOW",
            $"A ramp hid a required window-lane gap: {ramp.Reason}.");
    }

    private static void ContactingRampCannotCompleteLane()
    {
        var project = LoadMaterializedRampCompletion();
        project.Circuits.Add(new ManualCircuit
        {
            Id = "C12-RAMP-CONTACT-NEGATIVE",
            Name = "C12 ramp contact negative",
            Completed = true,
            SystemRole = "FLOOR_SERVICE_LEG",
            RoutingLayer = "HEATING_PLANE",
            AxisElevationMm = 108,
            OrderedPoints = [new PointMm(12800, 20100, 108), new PointMm(12800, 20300, 108)],
        });
        var ramp = AnalyzeC12(project).ExteriorOpenSpiralMaterializedTerminalRamp;
        Check(ramp.Applicable && !ramp.Pass && !ramp.GlobalInterCircuitContactPass &&
              ramp.Reason == "REJECT_MATERIALIZED_TERMINAL_RAMP_GLOBAL_INTER_CIRCUIT_CONTACT",
            $"A contacting ramp bypassed the global physical gate: {ramp.Reason}.");
    }

    private static void ConfigureServiceSideTerminal(ManualCircuit circuit)
    {
        circuit.OrderedPoints =
        [
            new(16400, 20200, 108), new(16400, 22000, 108), new(12500, 22000, 108),
            new(12500, 20200, 108), new(16200, 20200, 108), new(16200, 21800, 108),
            new(12700, 21800, 108), new(12700, 20400, 108), new(15800, 20400, 108),
            new(15800, 21400, 108), new(13100, 21400, 108), new(13100, 20800, 108),
            new(15300, 20800, 108), new(15300, 21000, 108), new(13400, 21000, 108),
            new(13400, 21200, 108), new(15600, 21200, 108), new(15600, 20600, 108),
            new(12900, 20600, 108), new(12900, 21600, 108), new(16000, 21600, 108),
            new(16000, 20300, 108), new(12600, 20300, 108), new(12600, 21900, 108),
            new(16300, 21900, 108), new(16300, 20300, 108),
        ];
        circuit.HeatingBodyEndIndex = 25;
    }

    private static CircuitAnalysis AnalyzeC12(HomeAuraProject project) =>
        CircuitAnalyzer.Analyze(project, C12(project));

    private static ManualCircuit C12(HomeAuraProject project) =>
        project.Circuits.Single(item => item.Id == "F1-D171-C12");

    private static HomeAuraProject LoadC12()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "homeaura-native-editor", "examples", "proposals",
            "HA_TWO_FLOOR_R07_POINT3_ROUTES_184", "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json");
        var project = HomeAuraProject.FromJson(File.ReadAllText(path));
        var circuit = C12(project);
        circuit.OrderedPoints =
        [
            new(12500, 20200, 108), new(16400, 20200, 108), new(16400, 22000, 108),
            new(12500, 22000, 108), new(12500, 20400, 108), new(16200, 20400, 108),
            new(16200, 21800, 108), new(12700, 21800, 108), new(12700, 20800, 108),
            new(15800, 20800, 108), new(15800, 21400, 108), new(13100, 21400, 108),
            new(13100, 21200, 108), new(15600, 21200, 108), new(15600, 21000, 108),
            new(12900, 21000, 108), new(12900, 21600, 108), new(16000, 21600, 108),
            new(16000, 20600, 108), new(12600, 20600, 108), new(12600, 21900, 108),
            new(16300, 21900, 108), new(16300, 20300, 108), new(12600, 20300, 108),
        ];
        circuit.HeatingBodyRanges.Clear();
        circuit.HeatingBodyStartIndex = 0;
        circuit.HeatingBodyEndIndex = 23;
        circuit.VerticalTransitions.Clear();
        circuit.SystemRole = "FLOOR_HEATING_AXIS";
        circuit.AxisElevationMm = 108;
        return project;
    }

    private static HomeAuraProject LoadMaterializedRampCompletion()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "homeaura-native-editor", "examples", "proposals",
            "HA_TWO_FLOOR_R07_POINT3_ROUTES_184", "HomeAura_TwoFloor_R07Point3Routes_D184.homeaura.json");
        var project = HomeAuraProject.FromJson(File.ReadAllText(path));
        var circuit = C12(project);
        circuit.OrderedPoints =
        [
            new(15800, 13000, 135), new(15800, 18700, 135), new(15800, 19000, 70),
            new(15800, 19300, 70), new(13600, 19300, 70), new(13600, 20100, 135),
            new(13600, 20500, 135), new(12500, 20500, 135), new(12500, 20200, 108),
            new(16400, 20200, 108), new(16400, 22000, 108), new(12500, 22000, 108),
            new(12500, 20400, 108), new(16200, 20400, 108), new(16200, 21800, 108),
            new(12700, 21800, 108), new(12700, 20800, 108), new(15800, 20800, 108),
            new(15800, 21400, 108), new(13100, 21400, 108), new(13100, 21200, 108),
            new(15600, 21200, 108), new(15600, 21000, 108), new(12900, 21000, 108),
            new(12900, 21600, 108), new(16000, 21600, 108), new(16000, 20600, 108),
            new(12600, 20600, 108), new(12600, 21900, 108), new(16300, 21900, 108),
            new(16300, 20300, 108), new(12800, 20300, 108), new(12600, 20300, 70),
            new(12600, 20700, 70), new(16000, 20700, 70), new(16000, 19000, 70),
            new(16000, 18700, 135), new(16000, 13000, 135),
        ];
        circuit.HeatingBodyStartIndex = null;
        circuit.HeatingBodyEndIndex = null;
        circuit.HeatingBodyRanges = [new HeatingBodyRange { StartIndex = 8, EndIndex = 31 }];
        circuit.VerticalTransitions =
        [
            new VerticalTransition { SegmentIndex = 1, Kind = "S_BEND_R80", RadiusMm = 80,
                StartTangentLengthMm = 85.62803405208133, EndTangentLengthMm = 85.62803405208133,
                ArcSamplesPerHalf = 12 },
            new VerticalTransition { SegmentIndex = 4, Kind = "S_BEND_R80", RadiusMm = 80,
                StartTangentLengthMm = 335.6280340520813, EndTangentLengthMm = 335.6280340520813,
                ArcSamplesPerHalf = 12 },
            new VerticalTransition { SegmentIndex = 7, Kind = "S_BEND_R80", RadiusMm = 80,
                StartTangentLengthMm = 131.05619751775845, EndTangentLengthMm = 80,
                ArcSamplesPerHalf = 12 },
            new VerticalTransition { SegmentIndex = 31, Kind = "S_BEND_R80", RadiusMm = 80,
                StartTangentLengthMm = 16.48188564314004, EndTangentLengthMm = 79.99999999999969,
                ArcSamplesPerHalf = 12 },
            new VerticalTransition { SegmentIndex = 35, Kind = "S_BEND_R80", RadiusMm = 80,
                StartTangentLengthMm = 85.62803405208133, EndTangentLengthMm = 85.62803405208133,
                ArcSamplesPerHalf = 12 },
        ];
        circuit.ConcealedServiceLengthMm = 0;
        circuit.OutOfPlaneLengthMm = 0;
        circuit.SystemRole = "FLOOR_HEATING_LOOP";
        circuit.RoutingLayer = "HEATING_PLANE";
        circuit.AxisElevationMm = 108;
        return project;
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
