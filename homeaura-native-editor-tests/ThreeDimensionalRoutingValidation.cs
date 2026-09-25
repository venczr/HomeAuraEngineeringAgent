using HomeAura.NativeEditor;

internal static class ThreeDimensionalRoutingValidation
{
    public static void Run()
    {
        LegacyPointsRemainBackwardCompatible();
        ExactThirtyEightMillimetreSBendIsMaterialized();
        ZeroPlanVerticalSpliceCannotMasqueradeAsR80();
        EndpointTangentsParticipateInR80Allocation();
        ContactsAndSurfaceClearanceUseActualZ();
        SelfSurfaceClearancePublishesSegmentDetails();
        CurvedRampClearanceIsConservativeNearThreshold();
        RadiusBelowProjectR80IsReported();
        OwnerStyleRotationPreservesTheWhole3DContract();
    }

    private static void LegacyPointsRemainBackwardCompatible()
    {
        const string legacy = """
        {
          "schema_version": "1.0",
          "kind": "homeaura-manual-routing-example",
          "units": "mm",
          "grid_spacing_mm": 100,
          "canvas_width_mm": 4000,
          "canvas_height_mm": 4000,
          "circuits": [{
            "id": "LEGACY",
            "name": "Legacy",
            "ordered_points": [{"x_mm": 500, "y_mm": 500}, {"x_mm": 1500, "y_mm": 500}],
            "completed": true
          }]
        }
        """;
        var restored = HomeAuraProject.FromJson(legacy);
        Check(restored.Circuits[0].OrderedPoints.All(point => point.Z is null), "Legacy XY point acquired an invented Z value.");
        Check(!restored.ToJson().Contains("\"z_mm\"", StringComparison.Ordinal), "Null Z was written into a legacy point.");
        var analysis = CircuitAnalyzer.Analyze(restored, restored.Circuits[0]);
        Check(analysis.AxisLengthMm == 1000 && analysis.PlanAxisLengthMm == 1000 && analysis.VerticalGeometryMaterialized,
            "Legacy flat route metrics changed.");
    }

    private static void ExactThirtyEightMillimetreSBendIsMaterialized()
    {
        var project = Blank();
        var radius = 80d;
        var deltaZ = 38d;
        var theta = Math.Acos(1 - deltaZ / (2 * radius));
        var arcProjection = 2 * radius * Math.Sin(theta);
        var tangent = (200 - arcProjection) / 2;
        var circuit = new ManualCircuit
        {
            Id = "S38",
            Completed = true,
            AxisElevationMm = 108,
            OrderedPoints = [new(500, 1000, 70), new(700, 1000, 108)],
            VerticalTransitions = [new VerticalTransition
            {
                SegmentIndex = 0,
                RadiusMm = radius,
                StartTangentLengthMm = tangent,
                EndTangentLengthMm = tangent,
                ArcSamplesPerHalf = 12,
            }],
        };
        project.Circuits.Add(circuit);
        project.ValidateContract();
        var restored = HomeAuraProject.FromJson(project.ToJson());
        var analysis = CircuitAnalyzer.Analyze(restored, restored.Circuits[0]);
        var transition = analysis.VerticalTransitions.Single();
        var expectedLength = 2 * tangent + 2 * radius * theta;

        Close(40.3149091747088, transition.TurnAngleDegrees, 0.00001, "S-bend angle");
        Close(103.51811435686, transition.RequiredArcProjectionMm, 0.00001, "S-bend arc projection");
        Close(expectedLength, transition.AxisLengthMm, 0.000001, "S-bend analytic length");
        Close(expectedLength, analysis.AxisLengthMm, 0.000001, "Circuit did not use analytic S-bend length");
        Check(transition.MaterializedPass && analysis.VerticalGeometryMaterialized && analysis.BendRadiusFeasible,
            "Exact R80 S-bend did not pass materialization.");
        Check(transition.SampledAxisPoints.Count == 27, "Stored sample density did not produce deterministic two-arc samples.");
        Close(70, transition.SampledAxisPoints[0].Z, 0.000001, "S-bend start Z");
        Close(108, transition.SampledAxisPoints[^1].Z, 0.000001, "S-bend end Z");
    }

    private static void ZeroPlanVerticalSpliceCannotMasqueradeAsR80()
    {
        var project = Blank();
        var circuit = new ManualCircuit
        {
            Id = "ZERO_PLAN",
            Completed = true,
            OrderedPoints = [new(1000, 1000, 70), new(1000, 1000, 108)],
        };
        project.Circuits.Add(circuit);
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.Continuous, "A real 3D segment was treated as a duplicate XY point.");
        Check(analysis.UnmaterializedElevationChangeCount == 1 && !analysis.VerticalGeometryMaterialized && !analysis.TopologyPass,
            "Zero-plan vertical splice incorrectly passed as materialized R80 geometry.");

        circuit.VerticalTransitions.Add(new VerticalTransition { SegmentIndex = 0, RadiusMm = 80 });
        Throws<InvalidDataException>(() => project.ValidateContract());
    }

    private static void EndpointTangentsParticipateInR80Allocation()
    {
        var project = Blank();
        var theta = Math.Acos(1 - 38d / 160d);
        var projection = 160 * Math.Sin(theta);
        var tangent = (300 - projection) / 2;
        var circuit = new ManualCircuit
        {
            Id = "TANGENTS",
            Completed = true,
            OrderedPoints = [
                new(500, 500, 70),
                new(500, 1000, 70),
                new(800, 1000, 108),
                new(800, 1500, 108),
            ],
            VerticalTransitions = [new VerticalTransition
            {
                SegmentIndex = 1,
                RadiusMm = 80,
                StartTangentLengthMm = tangent,
                EndTangentLengthMm = tangent,
            }],
        };
        project.Circuits.Add(circuit);
        project.ValidateContract();
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.BendCount == 2 && analysis.BendRadiusViolationCount == 0 && analysis.BendRadiusFeasible,
            "R80 endpoint turns did not use the explicit S-bend tangents.");

        circuit.VerticalTransitions[0].StartTangentLengthMm = 40;
        circuit.VerticalTransitions[0].EndTangentLengthMm = 300 - projection - 40;
        project.ValidateContract();
        analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.BendRadiusViolationCount == 1 && analysis.BendRadiusViolations[0].SegmentIndex == 1,
            "Short lower tangent was hidden by transferable length at the other end.");
    }

    private static void ContactsAndSurfaceClearanceUseActualZ()
    {
        var project = Blank();
        var upper = new ManualCircuit
        {
            Id = "UPPER", Completed = true, AxisElevationMm = 108,
            OrderedPoints = [new(500, 2000), new(3500, 2000)],
        };
        var lower = new ManualCircuit
        {
            Id = "LOWER", Completed = true, AxisElevationMm = 70,
            OrderedPoints = [new(2000, 500), new(2000, 3500)],
        };
        project.Circuits.AddRange([upper, lower]);
        var analysis = CircuitAnalyzer.Analyze(project, upper);
        Check(analysis.InterCircuitIntersections == 0 && analysis.InterCircuitSurfaceClearanceViolations == 0,
            "38 mm axis separation was reported as a 3D contact.");
        Check(analysis.DifferentLayerCrossingsIgnored == 1 && analysis.StackCrossings.Count == 1,
            "Clear plan crossing was not published as a stack.");
        Close(38, analysis.StackCrossings[0].AxisClearanceMm, 0.000001, "stack axis clearance");
        Close(22, analysis.StackCrossings[0].SurfaceClearanceMm, 0.000001, "stack surface clearance");
        var report = CircuitAnalyzer.AnalyzeProject(project);
        Check(report.PipeOuterDiameterMm == 16 && report.MinimumLayerAxisSeparationMm == 25 &&
              report.MinimumLayerSurfaceClearanceMm == 5,
            "Project diagnostics omitted the 3D surface-clearance contract.");

        lower.AxisElevationMm = 90;
        analysis = CircuitAnalyzer.Analyze(project, upper);
        Check(analysis.InterCircuitIntersections == 1 && analysis.InterCircuitSurfaceClearanceViolations == 1 &&
              analysis.StackCrossings.Count == 0 && !analysis.TopologyPass,
            "18 mm axis separation incorrectly passed the 25 mm/5 mm clearance contract.");
        Close(2, analysis.InterCircuitSurfaceClearanceViolationDetails[0].SurfaceClearanceMm, 0.000001,
            "violating surface clearance");
    }

    private static void SelfSurfaceClearancePublishesSegmentDetails()
    {
        var project = Blank();
        var circuit = new ManualCircuit
        {
            Id = "SELF_CLEARANCE",
            Completed = true,
            OrderedPoints = [new(500, 500), new(1500, 500), new(1500, 520), new(500, 520)],
        };
        project.Circuits.Add(circuit);

        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.SelfSurfaceClearanceViolations == 1 && analysis.SelfSurfaceClearanceViolationDetails.Count == 1,
            "Self-clearance count and detail collection disagree.");
        var detail = analysis.SelfSurfaceClearanceViolationDetails.Single();
        Check(detail.FirstCircuitSegmentIndex == 0 && detail.SecondCircuitSegmentIndex == 2,
            "Self-clearance detail points at the wrong circuit segments.");
        Close(20, detail.AxisClearanceMm, 0.000001, "self axis clearance");
        Close(4, detail.SurfaceClearanceMm, 0.000001, "self surface clearance");
        Close(25, detail.RequiredAxisClearanceMm, 0.000001, "required self axis clearance");
        Close(5, detail.RequiredSurfaceClearanceMm, 0.000001, "required self surface clearance");
        Close(0, detail.ClearanceErrorBoundMm, 0.000001, "self clearance error bound");

        var json = System.Text.Json.JsonSerializer.Serialize(
            CircuitAnalyzer.AnalyzeProject(project),
            new System.Text.Json.JsonSerializerOptions { PropertyNamingPolicy = System.Text.Json.JsonNamingPolicy.SnakeCaseLower });
        using var document = System.Text.Json.JsonDocument.Parse(json);
        var circuitJson = document.RootElement.GetProperty("circuits")[0];
        Check(circuitJson.GetProperty("self_surface_clearance_violations").GetInt32() == 1 &&
              circuitJson.GetProperty("self_surface_clearance_violation_details").GetArrayLength() == 1 &&
              circuitJson.GetProperty("inter_circuit_surface_clearance_violation_details").GetArrayLength() == 0,
            "Snake-case diagnostics changed an existing field or omitted the additive self-clearance details.");
    }

    private static void RadiusBelowProjectR80IsReported()
    {
        var project = Blank();
        const double radius = 60;
        var theta = Math.Acos(1 - 38d / (2 * radius));
        var projection = 2 * radius * Math.Sin(theta);
        var circuit = new ManualCircuit
        {
            Id = "R60",
            Completed = true,
            OrderedPoints = [new(500, 1000, 70), new(700, 1000, 108)],
            VerticalTransitions = [new VerticalTransition
            {
                SegmentIndex = 0,
                RadiusMm = radius,
                StartTangentLengthMm = (200 - projection) / 2,
                EndTangentLengthMm = (200 - projection) / 2,
            }],
        };
        project.Circuits.Add(circuit);
        project.ValidateContract();
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        Check(analysis.VerticalTransitions[0].GeometryPass && !analysis.VerticalTransitions[0].RadiusPass &&
              !analysis.VerticalTransitionRadiusFeasible && !analysis.BendRadiusFeasible && !analysis.EngineeringPass,
            "Materialized R60 transition incorrectly passed a project minimum of R80.");
    }

    private static void CurvedRampClearanceIsConservativeNearThreshold()
    {
        var project = Blank();
        const double radius = 80;
        var fullAngle = Math.Acos(1 - 38d / (2 * radius));
        var arcProjection = 2 * radius * Math.Sin(fullAngle);
        var targetRiseAtX600 = 5.2d;
        var targetAngle = Math.Acos(1 - targetRiseAtX600 / radius);
        var startTangent = 100 - radius * Math.Sin(targetAngle);
        var endTangent = 200 - arcProjection - startTangent;
        var ramp = new ManualCircuit
        {
            Id = "CURVED_RAMP",
            Completed = true,
            OrderedPoints = [new(500, 2000, 70), new(700, 2000, 108)],
            VerticalTransitions = [new VerticalTransition
            {
                SegmentIndex = 0,
                RadiusMm = radius,
                StartTangentLengthMm = startTangent,
                EndTangentLengthMm = endTangent,
                ArcSamplesPerHalf = 2,
            }],
        };
        var crossing = new ManualCircuit
        {
            Id = "NEAR_LIMIT",
            Completed = true,
            AxisElevationMm = 100,
            OrderedPoints = [new(600, 1500), new(600, 2500)],
        };
        project.Circuits.AddRange([ramp, crossing]);
        project.ValidateContract();
        var analysis = CircuitAnalyzer.Analyze(project, ramp);
        var transition = analysis.VerticalTransitions.Single();
        Check(transition.EffectiveArcSamplesPerHalf > transition.RequestedArcSamplesPerHalf &&
              transition.MaximumChordErrorMm <= 0.050001,
            "Clearance analysis trusted the coarse user rendering tessellation.");
        Check(analysis.InterCircuitIntersections == 1 && analysis.InterCircuitSurfaceClearanceViolations == 1,
            "A true 24.8 mm curved-ramp crossing falsely passed the 25 mm axis-clearance threshold.");
    }

    private static void OwnerStyleRotationPreservesTheWhole3DContract()
    {
        var source = Blank();
        source.Training.Label = "ACCEPTED";
        source.Levels.Add(new FloorLevel
        {
            Id = "F1",
            Outline = [new(0, 0), new(4000, 0), new(4000, 4000), new(0, 4000)],
            Origin = new(0, 0),
            LabelPosition = new(500, 3500),
        });
        source.FloorBuildUps.Add(new FloorBuildUp { FloorId = "F1", InstalledInsulationMm = 100, RemainingHeightMm = 70 });
        source.RoutingRules = new RoutingRules
        {
            PipeOuterDiameterMm = 18,
            MinimumBendRadiusMm = 90,
            ExteriorWallSpacingMm = 100,
            FieldSpacingMm = 200,
            MaximumParallelTransitPipesAt100Mm = 3,
            MinimumLayerAxisSeparationMm = 25,
            MinimumLayerSurfaceClearanceMm = 7,
            TransitLaneGeometryVerified = true,
            ExteriorEdgeZoneApplied = true,
        };
        source.Collectors.Add(new Collector { Id = "K", Position = new(500, 500), FloorId = "F1" });
        source.ServiceZones.Add(new ServiceZone
        {
            Id = "SZ", FloorId = "F1", CollectorId = "K",
            Outline = [new(400, 400), new(800, 400), new(800, 800), new(400, 800)],
            PipeCapacity = 4, RequiredPipeCount = 2, RequiredPlanWidthMm = 400,
        });
        const double radius = 100;
        var theta = Math.Acos(1 - 38d / (2 * radius));
        var projection = 2 * radius * Math.Sin(theta);
        source.Circuits.Add(new ManualCircuit
        {
            Id = "C", Completed = true, CollectorId = "K", ServiceZoneId = "SZ",
            RoutingLayer = "LOWER_SERVICE_LAYER", SystemRole = "FLOOR_SERVICE_LEG",
            OrderedPoints = [new(500, 500, 70), new(700, 500, 108)],
            VerticalTransitions = [new VerticalTransition
            {
                SegmentIndex = 0, RadiusMm = radius,
                StartTangentLengthMm = (200 - projection) / 2,
                EndTangentLengthMm = (200 - projection) / 2,
            }],
        });
        source.ValidateContract();

        var rotated = OwnerStyleProposalGenerator.RotateAcceptedExampleCounterClockwise(source);
        Check(rotated.RoutingRules.PipeOuterDiameterMm == 18 && rotated.RoutingRules.MinimumBendRadiusMm == 90 &&
              rotated.RoutingRules.MinimumLayerSurfaceClearanceMm == 7 && rotated.FloorBuildUps.Single().RemainingHeightMm == 70,
            "Owner-style rotation reset the 3D engineering contract.");
        var rotatedCircuit = rotated.Circuits.Single();
        Check(rotated.ServiceZones.Single().CollectorId == rotated.Collectors.Single().Id &&
              rotatedCircuit.ServiceZoneId == rotated.ServiceZones.Single().Id &&
              rotatedCircuit.VerticalTransitions.Single().RadiusMm == radius && rotatedCircuit.OrderedPoints[0].Z == 70,
            "Owner-style rotation broke service-zone or Point3 references.");
    }

    private static HomeAuraProject Blank() => new() { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };

    private static void Close(double expected, double actual, double tolerance, string label)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new InvalidOperationException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static void Throws<T>(Action action) where T : Exception
    {
        try { action(); }
        catch (T) { return; }
        throw new InvalidOperationException($"Expected {typeof(T).Name}.");
    }
}
