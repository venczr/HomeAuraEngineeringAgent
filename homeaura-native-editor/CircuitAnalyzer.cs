using System.Text.Json.Serialization;

namespace HomeAura.NativeEditor;

public sealed class BendRadiusViolationDetail
{
    public int SegmentIndex { get; init; }
    public required PointMm Start { get; init; }
    public required PointMm End { get; init; }
    public bool TurnAtStart { get; init; }
    public bool TurnAtEnd { get; init; }
    public double AvailableLengthMm { get; init; }
    public int RequiredTangentLengthMm { get; init; }
    public double RequiredTangentLengthExactMm { get; init; }
    public double ShortfallMm => Math.Max(0, RequiredTangentLengthExactMm - AvailableLengthMm);
}

public sealed class HeatingBodyWallIntrusionDetail
{
    public int HeatingBodySegmentIndex { get; init; }
    public int CircuitSegmentIndex { get; init; }
    public required string WallId { get; init; }
    public required PointMm SegmentStart { get; init; }
    public required PointMm SegmentEnd { get; init; }
    public double CenterlineClearanceMm { get; init; }
    public double RequiredCenterlineClearanceMm { get; init; }
    public double IntrusionDepthMm => Math.Max(0, RequiredCenterlineClearanceMm - CenterlineClearanceMm);
}

public sealed class HorizontalTurnWallIntrusionDetail
{
    public int TurnPointIndex { get; init; }
    public int IncomingCircuitSegmentIndex => TurnPointIndex - 1;
    public int OutgoingCircuitSegmentIndex => TurnPointIndex;
    public required string TurnRole { get; init; }
    public required string WallId { get; init; }
    public required Point3Mm TurnVertex { get; init; }
    public required Point3Mm ArcStart { get; init; }
    public required Point3Mm ArcEnd { get; init; }
    public required Point3Mm ArcCenter { get; init; }
    public double RadiusMm { get; init; }
    public double CenterlineClearanceMm { get; init; }
    public double RequiredCenterlineClearanceMm { get; init; }
    public double ClearanceErrorBoundMm { get; init; }
    public double IntrusionDepthMm => Math.Max(0, RequiredCenterlineClearanceMm - CenterlineClearanceMm);
}

public sealed class VerticalTransitionAnalysisDetail
{
    public int CircuitSegmentIndex { get; init; }
    public required string Kind { get; init; }
    public required Point3Mm Start { get; init; }
    public required Point3Mm End { get; init; }
    public double VerticalDeltaMm { get; init; }
    public double PlanProjectionMm { get; init; }
    public double RadiusMm { get; init; }
    public double TurnAngleRadians { get; init; }
    public double TurnAngleDegrees => TurnAngleRadians * 180d / Math.PI;
    public double RequiredArcProjectionMm { get; init; }
    public double StartTangentLengthMm { get; init; }
    public double EndTangentLengthMm { get; init; }
    public double ArcLengthMm { get; init; }
    public double AxisLengthMm { get; init; }
    public int RequestedArcSamplesPerHalf { get; init; }
    public int EffectiveArcSamplesPerHalf { get; init; }
    public double MaximumChordErrorMm { get; init; }
    public bool GeometryPass { get; init; }
    public bool RadiusPass { get; init; }
    public bool MaterializedPass => GeometryPass && RadiusPass;
    public required IReadOnlyList<Point3Mm> SampledAxisPoints { get; init; }
}

public sealed class SurfaceClearanceViolationDetail
{
    public int CircuitSegmentIndex { get; init; }
    public required string OtherCircuitId { get; init; }
    public int OtherCircuitSegmentIndex { get; init; }
    public double AxisClearanceMm { get; init; }
    public double SurfaceClearanceMm { get; init; }
    public double RequiredAxisClearanceMm { get; init; }
    public double RequiredSurfaceClearanceMm { get; init; }
    public double ClearanceErrorBoundMm { get; init; }
}

public sealed class SelfSurfaceClearanceViolationDetail
{
    public int FirstCircuitSegmentIndex { get; init; }
    public int SecondCircuitSegmentIndex { get; init; }
    public double AxisClearanceMm { get; init; }
    public double SurfaceClearanceMm { get; init; }
    public double RequiredAxisClearanceMm { get; init; }
    public double RequiredSurfaceClearanceMm { get; init; }
    public double ClearanceErrorBoundMm { get; init; }
}

public sealed class StackCrossingDetail
{
    public int CircuitSegmentIndex { get; init; }
    public required string OtherCircuitId { get; init; }
    public int OtherCircuitSegmentIndex { get; init; }
    public required PointMm Position { get; init; }
    public double LowerAxisElevationMm { get; init; }
    public double UpperAxisElevationMm { get; init; }
    public double AxisClearanceMm { get; init; }
    public double SurfaceClearanceMm { get; init; }
    public double ClearanceErrorBoundMm { get; init; }
}

public sealed class ExteriorBandCoveredInterval
{
    public required PointMm Start { get; init; }
    public required PointMm End { get; init; }
}

public sealed class ExteriorWallBandCoverageDetail
{
    public required string RoomId { get; init; }
    public required string WallId { get; init; }
    public int LaneIndex { get; init; }
    public int OffsetFromInteriorFaceMm { get; init; }
    public required PointMm TargetStart { get; init; }
    public required PointMm TargetEnd { get; init; }
    public double RequiredSpanLengthMm { get; init; }
    public double CoveredSpanLengthMm { get; init; }
    public double CoveragePercent { get; init; }
    public double WindowRequiredSpanLengthMm { get; init; }
    public double WindowCoveredSpanLengthMm { get; init; }
    public double WindowCoveragePercent { get; init; }
    public required IReadOnlyList<string> ContributingCircuitIds { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> CoveredIntervals { get; init; }
    public bool CoveragePass => CoveragePercent + 0.000001 >= 90 &&
                                (WindowRequiredSpanLengthMm <= 0.001 || WindowCoveragePercent + 0.000001 >= 100);
}

public sealed class ExteriorWallBandUsefulSpanDetail
{
    public required string RoomId { get; init; }
    public required string WallId { get; init; }
    public int LaneIndex { get; init; }
    public int OffsetFromInteriorFaceMm { get; init; }
    public required string Derivation { get; init; }
    public double CornerEnvelopeMm { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> SelectedTerritoryIntervals { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> EffectiveRequiredIntervals { get; init; }
    public double EffectiveRequiredSpanLengthMm { get; init; }
    public double CoveredSpanLengthMm { get; init; }
    public double CoveragePercent { get; init; }
    public double WindowRequiredSpanLengthMm { get; init; }
    public double WindowCoveredSpanLengthMm { get; init; }
    public double WindowCoveragePercent { get; init; }
    public required IReadOnlyList<string> ContributingCircuitIds { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> CoveredIntervals { get; init; }
    public double MaximumStartTaperMm { get; init; }
    public double MaximumEndTaperMm { get; init; }
    public double NestedCornerTaperAllowanceMm { get; init; }
    public bool ContiguousCoveragePass { get; init; }
    public bool NestedWithPreviousLanePass { get; init; }
    public bool NestedCornerTaperPass { get; init; }
    public bool StaggeredTurnoutEvaluated { get; init; }
    public double PreviousLaneStartExtensionMm { get; init; }
    public double PreviousLaneEndExtensionMm { get; init; }
    public bool SingleEndpointExtensionPass { get; init; }
    public bool ExtensionWithinCornerEnvelopePass { get; init; }
    public bool AlternatingEndpointPass { get; init; }
    public bool OppositeTaperWithinAllowancePass { get; init; }
    public bool ExtensionOutsideRequiredWindowPass { get; init; }
    public bool? AggregateRoomR80Pass { get; init; }
    public bool? AggregateRoomSelfContactPass { get; init; }
    public bool? AggregateRoomInterCircuitContactPass { get; init; }
    public bool? AggregateRoomBodyWallPass { get; init; }
    public bool? AggregateRoomHorizontalTurnWallPass { get; init; }
    public bool? AggregateRoomDirect100UTurnPass { get; init; }
    public double? AggregateRoomMinimumSegmentLengthMm { get; init; }
    public bool? AggregateRoomPhysicalGatePass { get; init; }
    public bool StaggeredTurnoutPass { get; init; }
    public required string StaggeredTurnoutReason { get; init; }
    public required string UsefulSpanMode { get; init; }
    public double RawRequiredSpanLengthMm { get; init; }
    public double RawCoveragePercent { get; init; }
    public bool RawCoveragePass { get; init; }
    public bool UsefulSpanPass => EffectiveRequiredSpanLengthMm > 0.001 &&
                                  (NestedCornerTaperPass || StaggeredTurnoutPass) &&
                                  CoveragePercent + 0.000001 >= 90 &&
                                  (WindowRequiredSpanLengthMm <= 0.001 || WindowCoveragePercent + 0.000001 >= 100);
}

public sealed class ExteriorOpenSpiralLaneDetail
{
    public required string WallId { get; init; }
    public int LaneIndex { get; init; }
    public double LaneSpecificCornerEnvelopeMm { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> EffectiveRequiredIntervals { get; init; }
    public required IReadOnlyList<ExteriorBandCoveredInterval> CoveredIntervals { get; init; }
    public double EffectiveRequiredSpanLengthMm { get; init; }
    public double CoveredSpanLengthMm { get; init; }
    public double CoveragePercent { get; init; }
    public double WindowRequiredSpanLengthMm { get; init; }
    public double WindowCoveredSpanLengthMm { get; init; }
    public double WindowCoveragePercent { get; init; }
    public bool ContiguousCoveragePass { get; init; }
    public double StartTerminalTaperMm { get; init; }
    public double EndTerminalTaperMm { get; init; }
    public double OpenTerminalTaperAllowanceMm { get; init; }
    public bool StrictNestedLanePass { get; init; }
    public bool OpenTerminalLanePass { get; init; }
}

public sealed class ExteriorOpenSpiralTerminalCornerDetail
{
    public required string RoomId { get; init; }
    public bool Applicable { get; init; }
    public bool Pass { get; init; }
    public required string Reason { get; init; }
    public string? TerminalWallId { get; init; }
    public string? TerminalSide { get; init; }
    public int HeatingBodyCircuitCount { get; init; }
    public int HeatingBodyRangeCount { get; init; }
    public int ExteriorWallCount { get; init; }
    public int RequiredLaneCount { get; init; }
    public bool ExactlyOneTerminalWallPass { get; init; }
    public bool AllOtherWallsStrictNestedPass { get; init; }
    public bool TerminalWallHasNoRequiredWindowPass { get; init; }
    public bool TerminalWallAdjacentStrictExteriorPass { get; init; }
    public bool AlignedTerminalSidePass { get; init; }
    public bool TerminalTaperSequencePass { get; init; }
    public bool BasicTopologyPass { get; init; }
    public bool GlobalInterCircuitContactPass { get; init; }
    public bool AggregateRoomPhysicalGatePass { get; init; }
    public bool AggregateRoomDirect100UTurnPass { get; init; }
    public bool AggregateRoomMinimumSegmentLengthPass { get; init; }
    public double AggregateRoomMinimumSegmentLengthMm { get; init; }
    public required IReadOnlyList<ExteriorOpenSpiralLaneDetail> Lanes { get; init; }
}

public sealed class ExteriorOpenSpiralMaterializedTerminalRampDetail
{
    public required string RoomId { get; init; }
    public bool Applicable { get; init; }
    public bool Pass { get; init; }
    public required string Reason { get; init; }
    public int BodyRangeStartIndex { get; init; }
    public int BodyRangeEndIndex { get; init; }
    public string? BodyEndpointSide { get; init; }
    public int? CircuitSegmentIndex { get; init; }
    public string? TransitionKind { get; init; }
    public bool TransitionMaterializedPass { get; init; }
    public string? WallId { get; init; }
    public int? LaneIndex { get; init; }
    public ExteriorBandCoveredInterval? MissingInterval { get; init; }
    public ExteriorBandCoveredInterval? RampProjectedInterval { get; init; }
    public double MissingLengthMm { get; init; }
    public double RampProjectedLengthMm { get; init; }
    public bool AdjacentBodyEndpointPass { get; init; }
    public bool SameHeadingContinuationPass { get; init; }
    public bool ExactGapMatchPass { get; init; }
    public bool WindowlessGapPass { get; init; }
    public bool NoTerminalWallOrOtherLaneContributionPass { get; init; }
    public bool DeficientWallSharesOpenCornerPass { get; init; }
    public bool GapAtSharedOpenCornerPass { get; init; }
    public bool AssignedRoomWallClearPass { get; init; }
    public bool FullCircuitPhysicalGatePass { get; init; }
    public bool NativeCollectorTerminalTolerancePass { get; init; }
    public bool GlobalInterCircuitContactPass { get; init; }
    public int CompletionCandidateCount { get; init; }
    public double AugmentedCoveragePercent { get; init; }
    public double AugmentedWindowCoveragePercent { get; init; }
    public bool AugmentedStrictLanePass { get; init; }
    public bool AugmentedAllNonTerminalWallsStrictPass { get; init; }
    public bool AugmentedOpenCornerAdjacencyPass { get; init; }
    public string? OpenTerminalWallId { get; init; }
    public string? OpenTerminalSide { get; init; }
}

public sealed class CollectorServedFloorDetail
{
    public required string CollectorId { get; init; }
    public string? ServedFloorId { get; init; }
    public bool Applicable { get; init; }
    public bool ServedFloorExists { get; init; }
    public int RoomCount { get; init; }
    public int HeatingBodyCount { get; init; }
    public int LoopCircuitCount { get; init; }
    public int AxisCircuitCount { get; init; }
}

public sealed class FloorPhysicalInputReadinessDetail
{
    public required string FloorId { get; init; }
    public bool ServedByCollector { get; init; }
    public bool RequiredByCrossFloorSystem { get; init; }
    public int RoomCount { get; init; }
    public int ExplicitWallCount { get; init; }
    public int ExplicitWindowCount { get; init; }
    public int ExplicitDoorCount { get; init; }
    public int FloorBuildUpCount { get; init; }
    public bool SharedDatumPass { get; init; }
    public bool RegistryDeclarationPass { get; init; }
    public bool WallGeometryPass { get; init; }
    public bool WindowRegistryPass { get; init; }
    public bool DoorAndThresholdRegistryPass { get; init; }
    public bool FloorBuildUpAndPipeAxisPass { get; init; }
    public bool Pass { get; init; }
}

public sealed class InterfloorOpeningReadinessDetail
{
    public required string FromFloorId { get; init; }
    public required string ToFloorId { get; init; }
    public bool RegistryDeclarationPass { get; init; }
    public int OpeningCount { get; init; }
    public int IndependentlyVerifiedOpeningCount { get; init; }
    public bool PairedFaceGeometryPass { get; init; }
    public bool StructuralDispositionPass { get; init; }
    public bool RoutingInputPass { get; init; }
}

public sealed class CrossFloorCollectorReadinessDetail
{
    public required string CollectorId { get; init; }
    public string? InstalledFloorId { get; init; }
    public string? ServedFloorId { get; init; }
    public bool FloorReferencesPass { get; init; }
    public bool VerifiedOpeningInputPass { get; init; }
    public bool MaterializedRouteOpeningBindingPass { get; init; }
}

public sealed class PhysicalInputReadinessDetail
{
    public bool Applicable { get; init; }
    public bool ArchitectureFloorScopePass { get; init; }
    public required IReadOnlyList<string> UnscopedWallIds { get; init; }
    public required IReadOnlyList<string> UnscopedWindowIds { get; init; }
    public required IReadOnlyList<FloorPhysicalInputReadinessDetail> FloorDetails { get; init; }
    public required IReadOnlyList<InterfloorOpeningReadinessDetail> InterfloorOpeningDetails { get; init; }
    public required IReadOnlyList<CrossFloorCollectorReadinessDetail> CrossFloorCollectorDetails { get; init; }
    public bool VerifiedArchitectureInputPass { get; init; }
    public bool VerifiedInterfloorOpeningInputPass { get; init; }
    public bool RoutingInputReadinessPass { get; init; }
    public bool StructuralDispositionPass { get; init; }
    public bool RouteOpeningBindingPass { get; init; }
    public bool InstallationInputReadinessPass { get; init; }
    public required IReadOnlyList<string> ReasonCodes { get; init; }
}

public sealed class ProjectDiagnostics
{
    public required string ProjectKind { get; init; }
    public required string SchemaVersion { get; init; }
    public int MinimumBendRadiusMm { get; init; }
    public int ExteriorWallSpacingMm { get; init; }
    public int ExteriorWallLaneCount { get; init; }
    public int PipeOuterDiameterMm { get; init; }
    public int MinimumLayerAxisSeparationMm { get; init; }
    public int MinimumLayerSurfaceClearanceMm { get; init; }
    public required IReadOnlyList<CircuitAnalysis> Circuits { get; init; }
    public required IReadOnlyList<CollectorServedFloorDetail> CollectorServedFloorDetails { get; init; }
    public required IReadOnlyList<string> MissingServedFloorIds { get; init; }
    public long TotalConcealedServiceLengthMm { get; init; }
    public long TotalOutOfPlaneLengthMm { get; init; }
    public int AxisOnlyCircuitCount { get; init; }
    public bool ServedFloorReferencesApplicable { get; init; }
    public bool ServedFloorReferencesPass { get; init; }
    public bool MaterializedHeatingRoutesPass { get; init; }
    public bool InstallationCompletenessPass { get; init; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public PhysicalInputReadinessDetail? PhysicalInputReadiness { get; init; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? PhysicalInstallationCompletenessPass { get; init; }
    public bool DesignPass => Circuits.All(item => item.DesignPass);
}

public sealed class CircuitAnalysis
{
    public required string CircuitId { get; init; }
    public required string Name { get; init; }
    public int PointCount { get; init; }
    public double LengthMm { get; init; }
    public double AxisLengthMm { get; init; }
    public double PlanAxisLengthMm { get; init; }
    public int ConcealedServiceLengthMm { get; init; }
    public int OutOfPlaneLengthMm { get; init; }
    public bool GridAligned { get; init; }
    public bool Continuous { get; init; }
    public bool Orthogonal { get; init; }
    public bool LengthInRange { get; init; }
    public bool StartAtCollector { get; init; }
    public bool EndAtCollector { get; init; }
    public int SelfIntersections { get; init; }
    public int SelfSurfaceClearanceViolations { get; init; }
    public IReadOnlyList<SelfSurfaceClearanceViolationDetail> SelfSurfaceClearanceViolationDetails { get; init; } = [];
    public int WallIntersections { get; init; }
    public int HeatingBodyWallIntrusions { get; init; }
    public int HorizontalTurnWallIntrusions { get; init; }
    public bool HorizontalTurnWallClearanceApplicable { get; init; }
    public int TransitWallIntersections { get; init; }
    public bool HeatingBodyInsideAssignedRoom { get; init; }
    public int HeatingBodyPointCount { get; init; }
    public int InterCircuitIntersections { get; init; }
    public int InterCircuitSurfaceClearanceViolations { get; init; }
    public double? MinimumInterCircuitAxisClearanceMm { get; init; }
    public double? MinimumInterCircuitSurfaceClearanceMm { get; init; }
    public double? MinimumInterCircuitClearanceErrorBoundMm { get; init; }
    public required IReadOnlyList<SurfaceClearanceViolationDetail> InterCircuitSurfaceClearanceViolationDetails { get; init; }
    public required IReadOnlyList<StackCrossingDetail> StackCrossings { get; init; }
    public int Spacing100Samples { get; init; }
    public int Spacing200Samples { get; init; }
    public int OtherSpacingSamples { get; init; }
    public bool Completed { get; init; }
    public required string RoutingLayer { get; init; }
    public required string SystemRole { get; init; }
    public int DifferentLayerCrossingsIgnored { get; init; }
    public int ExplicitPointElevationCount { get; init; }
    public int VerticalTransitionCount { get; init; }
    public int UnmaterializedElevationChangeCount { get; init; }
    public required IReadOnlyList<VerticalTransitionAnalysisDetail> VerticalTransitions { get; init; }
    public bool VerticalGeometryMaterialized => UnmaterializedElevationChangeCount == 0 && VerticalTransitions.All(item => item.GeometryPass);
    public bool VerticalTransitionRadiusFeasible => VerticalTransitions.All(item => item.RadiusPass);
    public int BendCount { get; init; }
    public int BendRadiusViolationCount { get; init; }
    public required IReadOnlyList<BendRadiusViolationDetail> BendRadiusViolations { get; init; }
    public bool BendRadiusFeasible => BendRadiusViolationCount == 0 && VerticalTransitionRadiusFeasible;
    public required IReadOnlyList<HeatingBodyWallIntrusionDetail> HeatingBodyWallIntrusionDetails { get; init; }
    public required IReadOnlyList<HorizontalTurnWallIntrusionDetail> HorizontalTurnWallIntrusionDetails { get; init; }
    public bool HorizontalTurnWallClearancePass => HorizontalTurnWallIntrusions == 0;
    public required IReadOnlyList<ExteriorWallBandCoverageDetail> ExteriorWallBandCoverageDetails { get; init; }
    public bool Exterior3x100Applicable => ExteriorWallBandCoverageDetails.Count > 0;
    public bool Exterior3x100Pass => !Exterior3x100Applicable || ExteriorWallBandCoverageDetails.All(item => item.CoveragePass);
    public required IReadOnlyList<ExteriorWallBandUsefulSpanDetail> ExteriorWallBandUsefulSpanDetails { get; init; }
    public bool Exterior3x100UsefulSpanApplicable => ExteriorWallBandUsefulSpanDetails.Count > 0;
    public bool Exterior3x100UsefulSpanPass => Exterior3x100UsefulSpanApplicable &&
                                               ExteriorWallBandUsefulSpanDetails.All(item => item.UsefulSpanPass);
    public required ExteriorOpenSpiralTerminalCornerDetail ExteriorOpenSpiralTerminalCorner { get; init; }
    public bool ExteriorOpenSpiralTerminalCornerApplicable => ExteriorOpenSpiralTerminalCorner.Applicable;
    public bool ExteriorOpenSpiralTerminalCornerPass => ExteriorOpenSpiralTerminalCorner.Pass;
    public required ExteriorOpenSpiralMaterializedTerminalRampDetail ExteriorOpenSpiralMaterializedTerminalRamp { get; init; }
    public bool ExteriorOpenSpiralMaterializedTerminalRampApplicable =>
        ExteriorOpenSpiralMaterializedTerminalRamp.Applicable;
    public bool ExteriorOpenSpiralMaterializedTerminalRampPass =>
        ExteriorOpenSpiralMaterializedTerminalRamp.Pass;
    public double RoundedAxisLengthMm { get; init; }
    public double RoundedLengthMm { get; init; }
    public bool RoundedLengthInRange { get; init; }
    public bool TopologyPass => Completed && PointCount >= 2 && GridAligned && Continuous && Orthogonal && VerticalGeometryMaterialized &&
                                SelfIntersections == 0 && SelfSurfaceClearanceViolations == 0 &&
                                InterCircuitIntersections == 0 && InterCircuitSurfaceClearanceViolations == 0;
    public bool Pass => TopologyPass && (SystemRole != "FLOOR_HEATING_LOOP" || LengthInRange && StartAtCollector && EndAtCollector);
    public bool HeatingBodyPlacementPass => HeatingBodyPointCount == 0 || HeatingBodyInsideAssignedRoom && HeatingBodyWallIntrusions == 0;
    public bool EngineeringPass => TopologyPass && BendRadiusFeasible && HeatingBodyPlacementPass &&
                                   (!HorizontalTurnWallClearanceApplicable || HorizontalTurnWallClearancePass) &&
                                   (SystemRole != "FLOOR_HEATING_LOOP" || RoundedLengthInRange && StartAtCollector && EndAtCollector);
    public bool DesignPass => EngineeringPass && Exterior3x100Pass;
}

public sealed class RoundedPlanAxisGeometry
{
    public required IReadOnlyList<Point3Mm> SampledPoints { get; init; }
    public double RadiusMm { get; init; }
    public int TurnCount { get; init; }
    public int FilletCount { get; init; }
    public bool FullyMaterialized { get; init; }
    public double ExactLengthMm { get; init; }
    public double SampledLengthMm { get; init; }
    public double MaximumSagittaMm { get; init; }
    public double LengthUnderestimateMm => Math.Max(0, ExactLengthMm - SampledLengthMm);
}

public static class CircuitAnalyzer
{
    private readonly record struct IndexedCircuitSegment(int CircuitSegmentIndex, PointMm A, PointMm B);
    private readonly record struct PlanPoint(double X, double Y);
    private readonly record struct Vector3(double X, double Y, double Z)
    {
        public double Length => Math.Sqrt(X * X + Y * Y + Z * Z);
        public Vector3 Unit => Length <= 0.0000001 ? new Vector3() : new Vector3(X / Length, Y / Length, Z / Length);
    }
    private readonly record struct MaterializedSegment3D(int CircuitSegmentIndex, Point3Mm A, Point3Mm B, double ApproximationErrorMm);
    private sealed record MaterializedCircuitGeometry(
        IReadOnlyList<MaterializedSegment3D> Segments,
        IReadOnlyList<VerticalTransitionAnalysisDetail> Transitions,
        double AxisLengthMm,
        int UnmaterializedElevationChangeCount);
    private sealed record SelfClearanceAnalysis(
        int PlanContactCount,
        int SurfaceViolationCount,
        IReadOnlyList<SelfSurfaceClearanceViolationDetail> Violations);
    private sealed record ClearanceAnalysis(
        int PlanContactCount,
        int SurfaceViolationCount,
        int ClearPlanCrossingCount,
        double? MinimumAxisClearanceMm,
        double? MinimumAxisClearanceErrorBoundMm,
        IReadOnlyList<SurfaceClearanceViolationDetail> Violations,
        IReadOnlyList<StackCrossingDetail> StackCrossings);
    private sealed record BendAnalysis(
        int TurnCount,
        double RoundedLengthCorrectionMm,
        IReadOnlyList<BendRadiusViolationDetail> Violations,
        IReadOnlyList<HorizontalFillet> HorizontalFillets);
    private sealed record ExteriorRoomPhysicalGate(
        bool R80Pass,
        bool SelfContactPass,
        bool InterCircuitContactPass,
        bool BodyWallPass,
        bool HorizontalTurnWallPass,
        bool Direct100UTurnPass,
        double MinimumSegmentLengthMm)
    {
        public bool Pass => R80Pass && SelfContactPass && InterCircuitContactPass && BodyWallPass &&
                            HorizontalTurnWallPass && Direct100UTurnPass;
    }
    private sealed record HorizontalFillet(
        int PointIndex,
        Point3Mm Vertex,
        Point3Mm ArcStart,
        Point3Mm ArcEnd,
        Point3Mm ArcCenter,
        double RadiusMm,
        double AngleRadians,
        double StartAngleRadians,
        double SignedSweepRadians,
        double TangentLengthMm,
        bool LocallyFeasible)
    {
        public double RoundedLengthCorrectionMm => 2 * TangentLengthMm - RadiusMm * AngleRadians;
    }

    public static CircuitAnalysis Analyze(HomeAuraProject project, ManualCircuit circuit)
    {
        var segments = Segments(circuit.OrderedPoints).ToList();
        var spacings = AnalyzeSpacing(segments);
        var planAxisLength = segments.Sum(s => Distance(s.A, s.B));
        var geometry = MaterializeGeometry(circuit, project.RoutingRules.MinimumBendRadiusMm);
        var axisLength = geometry.AxisLengthMm;
        var totalLength = axisLength + circuit.ConcealedServiceLengthMm + circuit.OutOfPlaneLengthMm;
        var bend = AnalyzeBends(circuit, geometry.Transitions, project.RoutingRules.MinimumBendRadiusMm);
        var bodyPoints = HeatingBodyPoints(circuit);
        var bodySegments = HeatingBodySegments(circuit);
        var bodySegmentIndices = bodySegments.Select(item => item.CircuitSegmentIndex).ToHashSet();
        var transitSegments = segments.Where((_, segmentIndex) => !bodySegmentIndices.Contains(segmentIndex)).ToList();
        var applicableWalls = WallsForCircuit(project, circuit);
        var allWallIntersections = CountWallIntersections(applicableWalls, segments);
        var bodyWallIntrusions = AnalyzeWallIntrusions(applicableWalls, bodySegments);
        var horizontalTurnWallIntrusions = AnalyzeHorizontalTurnWallIntrusions(
            applicableWalls, bend.HorizontalFillets, bodySegmentIndices);
        var exteriorBandCoverage = AnalyzeExteriorWallBands(project, circuit);
        var exteriorBandUsefulSpans = AnalyzeExteriorWallUsefulSpans(project, circuit, exteriorBandCoverage);
        var exteriorOpenSpiralTerminalCorner = AnalyzeExteriorOpenSpiralTerminalCorner(
            project, circuit, exteriorBandCoverage, exteriorBandUsefulSpans);
        var exteriorOpenSpiralMaterializedTerminalRamp = AnalyzeExteriorOpenSpiralMaterializedTerminalRamp(
            project, circuit, exteriorOpenSpiralTerminalCorner);
        var roundedAxisLength = axisLength - bend.RoundedLengthCorrectionMm;
        var roundedLength = roundedAxisLength + circuit.ConcealedServiceLengthMm + circuit.OutOfPlaneLengthMm;
        var selfClearance = AnalyzeSelfClearance(project, circuit, geometry.Segments);
        var interClearance = AnalyzeInterCircuitClearance(project, circuit, geometry.Segments);
        return new CircuitAnalysis
        {
            CircuitId = circuit.Id,
            Name = circuit.Name,
            RoutingLayer = circuit.RoutingLayer,
            SystemRole = circuit.SystemRole,
            Completed = circuit.Completed,
            PointCount = circuit.OrderedPoints.Count,
            LengthMm = totalLength,
            AxisLengthMm = axisLength,
            PlanAxisLengthMm = planAxisLength,
            ConcealedServiceLengthMm = circuit.ConcealedServiceLengthMm,
            OutOfPlaneLengthMm = circuit.OutOfPlaneLengthMm,
            GridAligned = circuit.OrderedPoints.All(p => p.X % project.GridSpacingMm == 0 && p.Y % project.GridSpacingMm == 0),
            Continuous = circuit.OrderedPoints.Count >= 2 && Enumerable.Range(0, circuit.OrderedPoints.Count - 1)
                .All(index => Distance3(ResolvePoint(circuit, circuit.OrderedPoints[index]), ResolvePoint(circuit, circuit.OrderedPoints[index + 1])) > 0.001),
            Orthogonal = segments.All(s => s.A.X == s.B.X || s.A.Y == s.B.Y),
            LengthInRange = totalLength is >= 40_000 and <= 80_000,
            RoundedLengthInRange = roundedLength is >= 40_000 and <= 80_000,
            BendCount = bend.TurnCount,
            BendRadiusViolationCount = bend.Violations.Count,
            BendRadiusViolations = bend.Violations,
            ExplicitPointElevationCount = circuit.OrderedPoints.Count(point => point.Z is not null),
            VerticalTransitionCount = geometry.Transitions.Count,
            UnmaterializedElevationChangeCount = geometry.UnmaterializedElevationChangeCount,
            VerticalTransitions = geometry.Transitions,
            RoundedAxisLengthMm = roundedAxisLength,
            RoundedLengthMm = roundedLength,
            StartAtCollector = circuit.OrderedPoints.Count > 0 && NearAssignedConnection(project, circuit, circuit.OrderedPoints[0], circuit.SupplyPortIndex),
            EndAtCollector = circuit.OrderedPoints.Count > 0 && NearAssignedConnection(project, circuit, circuit.OrderedPoints[^1], circuit.ReturnPortIndex),
            SelfIntersections = selfClearance.PlanContactCount,
            SelfSurfaceClearanceViolations = selfClearance.SurfaceViolationCount,
            SelfSurfaceClearanceViolationDetails = selfClearance.Violations,
            WallIntersections = allWallIntersections,
            HeatingBodyWallIntrusions = bodyWallIntrusions.Count,
            HeatingBodyWallIntrusionDetails = bodyWallIntrusions,
            HorizontalTurnWallIntrusions = horizontalTurnWallIntrusions.Count,
            HorizontalTurnWallClearanceApplicable = circuit.OrderedPoints.Any(point => point.Z is not null),
            HorizontalTurnWallIntrusionDetails = horizontalTurnWallIntrusions,
            ExteriorWallBandCoverageDetails = exteriorBandCoverage,
            ExteriorWallBandUsefulSpanDetails = exteriorBandUsefulSpans,
            ExteriorOpenSpiralTerminalCorner = exteriorOpenSpiralTerminalCorner,
            ExteriorOpenSpiralMaterializedTerminalRamp = exteriorOpenSpiralMaterializedTerminalRamp,
            TransitWallIntersections = CountWallIntersections(applicableWalls, transitSegments),
            HeatingBodyInsideAssignedRoom = HeatingBodyInsideAssignedRoom(project, circuit, bodyPoints, bodySegments),
            HeatingBodyPointCount = bodyPoints.Count,
            InterCircuitIntersections = interClearance.PlanContactCount,
            InterCircuitSurfaceClearanceViolations = interClearance.SurfaceViolationCount,
            MinimumInterCircuitAxisClearanceMm = interClearance.MinimumAxisClearanceMm,
            MinimumInterCircuitSurfaceClearanceMm = interClearance.MinimumAxisClearanceMm - project.RoutingRules.PipeOuterDiameterMm,
            MinimumInterCircuitClearanceErrorBoundMm = interClearance.MinimumAxisClearanceErrorBoundMm,
            InterCircuitSurfaceClearanceViolationDetails = interClearance.Violations,
            StackCrossings = interClearance.StackCrossings,
            DifferentLayerCrossingsIgnored = interClearance.ClearPlanCrossingCount,
            Spacing100Samples = spacings.Count(v => v == 100),
            Spacing200Samples = spacings.Count(v => v == 200),
            OtherSpacingSamples = spacings.Count(v => v is not 100 and not 200),
        };
    }

    public static ProjectDiagnostics AnalyzeProject(HomeAuraProject project)
    {
        var analyses = project.Circuits.Select(circuit => Analyze(project, circuit)).ToArray();
        var analysesByCircuitId = analyses.ToDictionary(item => item.CircuitId, StringComparer.Ordinal);
        var levelIds = project.Levels.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var roomById = project.Rooms.ToDictionary(item => item.Id, StringComparer.Ordinal);
        var collectorById = project.Collectors.ToDictionary(item => item.Id, StringComparer.Ordinal);
        var servedFloorDetails = project.Collectors.Select(collector =>
        {
            var applicable = !string.IsNullOrWhiteSpace(collector.ServedFloorId);
            var servedFloorId = applicable ? collector.ServedFloorId : null;
            var servedFloorExists = !applicable || levelIds.Contains(servedFloorId!);
            var floorRoomIds = applicable
                ? project.Rooms.Where(item => item.FloorId == servedFloorId)
                    .Select(item => item.Id).ToHashSet(StringComparer.Ordinal)
                : [];
            var floorCircuits = applicable
                ? project.Circuits.Where(item => item.CollectorId == collector.Id &&
                                                 item.RoomId is not null && floorRoomIds.Contains(item.RoomId)).ToArray()
                : [];
            return new CollectorServedFloorDetail
            {
                CollectorId = collector.Id,
                ServedFloorId = servedFloorId,
                Applicable = applicable,
                ServedFloorExists = servedFloorExists,
                RoomCount = floorRoomIds.Count,
                HeatingBodyCount = floorCircuits.Sum(item => GetHeatingBodyRanges(item).Count),
                LoopCircuitCount = floorCircuits.Count(item => item.SystemRole == "FLOOR_HEATING_LOOP"),
                AxisCircuitCount = floorCircuits.Count(item => item.SystemRole == "FLOOR_HEATING_AXIS"),
            };
        }).ToArray();
        var servedFloorReferencesApplicable = servedFloorDetails.Any(item => item.Applicable);
        var missingServedFloorIds = servedFloorDetails
            .Where(item => item.Applicable && !item.ServedFloorExists)
            .Select(item => item.ServedFloorId!)
            .Distinct(StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToArray();
        var totalConcealedServiceLengthMm = project.Circuits.Sum(item => (long)item.ConcealedServiceLengthMm);
        var totalOutOfPlaneLengthMm = project.Circuits.Sum(item => (long)item.OutOfPlaneLengthMm);
        var axisOnlyCircuitCount = project.Circuits.Count(item => item.SystemRole == "FLOOR_HEATING_AXIS");
        var servedFloorReferencesPass = !servedFloorReferencesApplicable || missingServedFloorIds.Length == 0;

        bool MaterializedHeatingLoop(ManualCircuit circuit)
        {
            if (circuit.SystemRole != "FLOOR_HEATING_LOOP" || circuit.CollectorId is null ||
                !collectorById.TryGetValue(circuit.CollectorId, out var collector) ||
                string.IsNullOrWhiteSpace(collector.ServedFloorId) || !levelIds.Contains(collector.ServedFloorId) ||
                circuit.RoomId is null || !roomById.TryGetValue(circuit.RoomId, out var room) ||
                room.FloorId != collector.ServedFloorId)
                return false;
            return circuit.Completed && circuit.OrderedPoints.Count >= 2 &&
                   circuit.OrderedPoints.All(point => point.Z is not null) &&
                   GetHeatingBodyRanges(circuit).Count > 0 &&
                   circuit.ConcealedServiceLengthMm == 0 && circuit.OutOfPlaneLengthMm == 0 &&
                   analysesByCircuitId[circuit.Id].VerticalGeometryMaterialized;
        }

        var materializedHeatingRoutesPass = !servedFloorReferencesApplicable ||
            totalConcealedServiceLengthMm == 0 && totalOutOfPlaneLengthMm == 0 && axisOnlyCircuitCount == 0 &&
            servedFloorDetails.Where(item => item.Applicable).All(item =>
                item.ServedFloorExists && item.RoomCount > 0 && item.HeatingBodyCount > 0 &&
                item.LoopCircuitCount > 0 && item.AxisCircuitCount == 0) &&
            project.Circuits.Where(item => item.SystemRole is "FLOOR_HEATING_LOOP" or "FLOOR_HEATING_AXIS")
                .All(MaterializedHeatingLoop);
        var installationCompletenessPass = servedFloorReferencesPass && materializedHeatingRoutesPass;
        var physicalInputReadiness = AnalyzePhysicalInputReadiness(project);
        var exposePhysicalReadiness = project.SchemaVersion == "1.1";

        return new ProjectDiagnostics
        {
            ProjectKind = project.Kind,
            SchemaVersion = project.SchemaVersion,
            MinimumBendRadiusMm = project.RoutingRules.MinimumBendRadiusMm,
            ExteriorWallSpacingMm = project.RoutingRules.ExteriorWallSpacingMm,
            ExteriorWallLaneCount = project.RoutingRules.MaximumParallelTransitPipesAt100Mm,
            PipeOuterDiameterMm = project.RoutingRules.PipeOuterDiameterMm,
            MinimumLayerAxisSeparationMm = project.RoutingRules.MinimumLayerAxisSeparationMm,
            MinimumLayerSurfaceClearanceMm = project.RoutingRules.MinimumLayerSurfaceClearanceMm,
            Circuits = analyses,
            CollectorServedFloorDetails = servedFloorDetails,
            MissingServedFloorIds = missingServedFloorIds,
            TotalConcealedServiceLengthMm = totalConcealedServiceLengthMm,
            TotalOutOfPlaneLengthMm = totalOutOfPlaneLengthMm,
            AxisOnlyCircuitCount = axisOnlyCircuitCount,
            ServedFloorReferencesApplicable = servedFloorReferencesApplicable,
            ServedFloorReferencesPass = servedFloorReferencesPass,
            MaterializedHeatingRoutesPass = materializedHeatingRoutesPass,
            // Port proximity remains a draft topology diagnostic. This structural gate deliberately
            // makes no Eurocone-continuity claim from NearAssignedConnection.
            InstallationCompletenessPass = installationCompletenessPass,
            PhysicalInputReadiness = exposePhysicalReadiness ? physicalInputReadiness : null,
            PhysicalInstallationCompletenessPass = exposePhysicalReadiness
                ? installationCompletenessPass && physicalInputReadiness.InstallationInputReadinessPass &&
                  physicalInputReadiness.RouteOpeningBindingPass
                : null,
        };
    }

    public static PhysicalInputReadinessDetail AnalyzePhysicalInputReadiness(HomeAuraProject project)
    {
        var schema11PhysicalContractPass = true;
        if (project.SchemaVersion == "1.1")
        {
            try { project.ValidateContract(); }
            catch { schema11PhysicalContractPass = false; }
        }
        var levels = project.Levels.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var crossFloorCollectors = project.Collectors
            .Where(item =>
            {
                var hasInstalled = !string.IsNullOrWhiteSpace(item.FloorId);
                var hasServed = !string.IsNullOrWhiteSpace(item.ServedFloorId);
                return hasInstalled && hasServed && item.FloorId != item.ServedFloorId ||
                       project.SchemaVersion == "1.1" && project.Levels.Count > 1 && (!hasInstalled || !hasServed);
            })
            .ToArray();
        // A declared cross-floor collector is applicable even while either referenced level is
        // missing from the project. Missing architecture must fail readiness, never turn the gate off.
        var applicable = crossFloorCollectors.Length > 0;
        var unscopedWallIds = project.Walls.Where(item => string.IsNullOrWhiteSpace(item.FloorId))
            .Select(item => item.Id).Order(StringComparer.Ordinal).ToArray();
        var unscopedWindowIds = project.Windows.Where(item => string.IsNullOrWhiteSpace(item.FloorId))
            .Select(item => item.Id).Order(StringComparer.Ordinal).ToArray();
        var architectureFloorScopePass = !applicable || unscopedWallIds.Length == 0 && unscopedWindowIds.Length == 0;
        var datum = project.SharedSpatialDatum;

        static bool IndependentlyVerified(PhysicalVerification? verification) =>
            verification is { Status: "INDEPENDENTLY_VERIFIED", SurveyToleranceMm: > 0 and <= 1000 } &&
            !string.IsNullOrWhiteSpace(verification.MeasurementSourceType) &&
            !string.IsNullOrWhiteSpace(verification.MeasuredBy) && !string.IsNullOrWhiteSpace(verification.MeasurementDate) &&
            DateOnly.TryParseExact(verification.MeasurementDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.None, out _) &&
            verification.SourceDocumentPaths is not null && verification.PhotoEvidencePaths is not null &&
            verification.IndependentVerificationRecordIds is not null &&
            !verification.SourceDocumentPaths.Any(string.IsNullOrWhiteSpace) &&
            !verification.PhotoEvidencePaths.Any(string.IsNullOrWhiteSpace) &&
            !verification.IndependentVerificationRecordIds.Any(string.IsNullOrWhiteSpace) &&
            (!string.IsNullOrWhiteSpace(verification.SourceDocumentId) || verification.SourceDocumentPaths.Count > 0) &&
            verification.PhotoEvidencePaths.Count > 0 && verification.IndependentVerificationRecordIds.Count > 0;
        static bool DatumMatches(SharedSpatialDatum? sharedDatum, string? reference, string floorId) =>
            sharedDatum is not null && !string.IsNullOrWhiteSpace(reference) && reference == sharedDatum.Id &&
            sharedDatum.FloorIdsBoundToDatum.Contains(floorId, StringComparer.Ordinal);
        static bool DatumDefinitionReady(SharedSpatialDatum? sharedDatum) =>
            sharedDatum is not null &&
            !string.IsNullOrWhiteSpace(sharedDatum.CoordinateReferenceDescription) &&
            !string.IsNullOrWhiteSpace(sharedDatum.HorizontalOriginReference) &&
            !string.IsNullOrWhiteSpace(sharedDatum.VerticalZeroReference) &&
            sharedDatum.ControlPoints is { Count: > 0 } &&
            sharedDatum.ControlPoints.All(point => point.PositionMm is not null &&
                double.IsFinite(point.PositionMm.X) && double.IsFinite(point.PositionMm.Y) && double.IsFinite(point.PositionMm.Z)) &&
            sharedDatum.FloorIdsBoundToDatum.All(floorId => sharedDatum.ControlPoints.Any(point => point.FloorId == floorId)) &&
            sharedDatum.ControlPoints.Any(point => point.Id == sharedDatum.HorizontalOriginReference) &&
            IndependentlyVerified(sharedDatum.PhysicalVerification);
        static bool WallNormalized(WallSegment wall)
        {
            if (wall.VerifiedFinishFaceAOutlineMm is not { Count: >= 2 } first ||
                wall.VerifiedFinishFaceBOutlineMm is not { Count: >= 2 } second || wall.PhysicalVerification is null)
                return false;
            var dx = wall.End.X - wall.Start.X;
            var dy = wall.End.Y - wall.Start.Y;
            if (dx != 0 && dy != 0 || dx == 0 && dy == 0) return false;
            var length = Math.Sqrt((double)dx * dx + (double)dy * dy);
            if (length <= 0.001) return false;
            var unitX = dx / length;
            var unitY = dy / length;
            double Along(PointMm point) => (point.X - wall.Start.X) * unitX + (point.Y - wall.Start.Y) * unitY;
            double Normal(PointMm point) => -(point.X - wall.Start.X) * unitY + (point.Y - wall.Start.Y) * unitX;
            var tolerance = wall.PhysicalVerification.SurveyToleranceMm ?? 0;
            var firstNormal = first.Average(Normal);
            var secondNormal = second.Average(Normal);
            if (Math.Abs(Math.Abs(firstNormal - secondNormal) - wall.ThicknessMm) > tolerance ||
                Math.Abs((firstNormal + secondNormal) / 2) > tolerance)
                return false;
            bool MatchesFace(IReadOnlyList<PointMm> face, double normal)
            {
                var from = face.Min(Along);
                var to = face.Max(Along);
                return Math.Abs(from) <= tolerance && Math.Abs(to - length) <= tolerance &&
                       face.All(point => Math.Abs(Normal(point) - normal) <= tolerance);
            }
            return MatchesFace(first, firstNormal) && MatchesFace(second, secondNormal) &&
                   wall.BaseElevationMmSharedDatum is not null &&
                   wall.TopElevationMmSharedDatum > wall.BaseElevationMmSharedDatum;
        }
        static bool BuildUpReady(FloorBuildUp item, FloorLevel level)
        {
            if (string.IsNullOrWhiteSpace(item.BuildUpId) || item.LayerRegistry is not { Count: > 0 } || item.TotalBuildUpThicknessMm is not > 0 ||
                item.TotalBuildUpThicknessMm != item.LayerRegistry.Sum(layer => layer.ThicknessMm) ||
                item.TotalBuildUpThicknessMm != item.InstalledInsulationMm + item.RemainingHeightMm ||
                item.AllowedPipeAxisElevationMmSharedDatum is null || item.AllowedPipeAxisToleranceMm is not > 0 ||
                level.FinishedFloorElevationMmSharedDatum is null || !IndependentlyVerified(item.PhysicalVerification))
                return false;
            var bottom = level.FinishedFloorElevationMmSharedDatum.Value - item.TotalBuildUpThicknessMm.Value;
            return item.AllowedPipeAxisElevationMmSharedDatum.Value - item.AllowedPipeAxisToleranceMm.Value >= bottom &&
                   item.AllowedPipeAxisElevationMmSharedDatum.Value + item.AllowedPipeAxisToleranceMm.Value <=
                   level.FinishedFloorElevationMmSharedDatum.Value;
        }

        var servedFloorIds = project.Collectors.Where(item => !string.IsNullOrWhiteSpace(item.ServedFloorId))
            .Select(item => item.ServedFloorId!).ToHashSet(StringComparer.Ordinal);
        var requiredPhysicalFloorIds = crossFloorCollectors
            .SelectMany(item => new[] { item.FloorId, item.ServedFloorId })
            .Where(item => !string.IsNullOrWhiteSpace(item)).Select(item => item!)
            .ToHashSet(StringComparer.Ordinal);
        var floorDetails = project.Levels.Select(level =>
        {
            var walls = project.Walls.Where(item => item.FloorId == level.Id).ToArray();
            var windows = project.Windows.Where(item => item.FloorId == level.Id).ToArray();
            var doors = (project.DoorOpenings ?? []).Where(item => item.FloorId == level.Id).ToArray();
            var buildUps = project.FloorBuildUps.Where(item => item.FloorId == level.Id).ToArray();
            var registry = (project.FloorArchitectureRegistryVerifications ?? [])
                .SingleOrDefault(item => item.FloorId == level.Id);
            var registryDeclarationPass = registry is not null && registry.WallsComplete && registry.WindowsComplete &&
                registry.DoorsAndThresholdsComplete && registry.FloorBuildUpComplete && registry.AllowedPipeAxisComplete &&
                DatumMatches(datum, registry.SharedDatumId, level.Id) && IndependentlyVerified(registry.PhysicalVerification);
            var sharedDatumPass = DatumMatches(datum, level.SharedDatumId, level.Id) &&
                level.FinishedFloorElevationMmSharedDatum is not null && DatumDefinitionReady(datum);
            var wallGeometryPass = walls.Length > 0 && walls.All(item => IndependentlyVerified(item.PhysicalVerification) && WallNormalized(item));
            var floorElevation = level.FinishedFloorElevationMmSharedDatum;
            bool WindowReady(WindowOpening item)
            {
                var wall = item.WallId is null ? null : project.Walls.SingleOrDefault(candidate => candidate.Id == item.WallId);
                var tolerance = item.PhysicalVerification?.SurveyToleranceMm ?? 0;
                return IndependentlyVerified(item.PhysicalVerification) && item.VerifiedPlanOutlineMm is { Count: >= 3 } &&
                       item.ClearWidthMm is > 0 && item.SillHeightMm is >= 0 && item.OpeningHeightMm is > 0 &&
                       item.SillElevationMmSharedDatum is not null && floorElevation is not null &&
                       Math.Abs(item.SillElevationMmSharedDatum.Value - (floorElevation.Value + item.SillHeightMm.Value)) <= tolerance &&
                       wall is not null && wall.FloorId == item.FloorId &&
                       HomeAuraProject.IsWallOpeningOutlineReady(wall, item.Start, item.End,
                           item.VerifiedPlanOutlineMm, item.ClearWidthMm, tolerance) &&
                       HomeAuraProject.IsWallOpeningVerticalEnvelopeReady(wall, item.SillElevationMmSharedDatum,
                           item.OpeningHeightMm, tolerance);
            }
            bool DoorReady(DoorOpening item)
            {
                var wall = project.Walls.SingleOrDefault(candidate => candidate.Id == item.WallId);
                var tolerance = item.PhysicalVerification?.SurveyToleranceMm ?? 0;
                var thresholdPass = item.ThresholdDisposition switch
                {
                    "NONE" => item.ThresholdHeightMm is null or 0 && item.ThresholdElevationMmSharedDatum is null,
                    "FLUSH" => item.ThresholdHeightMm is null or 0 && floorElevation is not null &&
                               item.ThresholdElevationMmSharedDatum is not null &&
                               Math.Abs(item.ThresholdElevationMmSharedDatum.Value - floorElevation.Value) <= tolerance,
                    "RAISED" => item.ThresholdHeightMm is > 0 && floorElevation is not null &&
                                item.ThresholdElevationMmSharedDatum is not null &&
                                Math.Abs(item.ThresholdElevationMmSharedDatum.Value -
                                         (floorElevation.Value + item.ThresholdHeightMm.Value)) <= tolerance,
                    _ => false,
                };
                int? bottomElevation = item.ThresholdDisposition switch
                {
                    "NONE" => floorElevation,
                    "FLUSH" or "RAISED" => item.ThresholdElevationMmSharedDatum,
                    _ => null,
                };
                return IndependentlyVerified(item.PhysicalVerification) && item.VerifiedPlanOutlineMm is { Count: >= 3 } &&
                       item.ClearWidthMm is > 0 && item.ClearHeightMm is > 0 && thresholdPass &&
                       wall is not null && wall.FloorId == item.FloorId &&
                       HomeAuraProject.IsWallOpeningOutlineReady(wall, item.Start, item.End,
                           item.VerifiedPlanOutlineMm, item.ClearWidthMm, tolerance) &&
                       HomeAuraProject.IsWallOpeningVerticalEnvelopeReady(wall, bottomElevation,
                           item.ClearHeightMm, tolerance);
            }
            var windowRegistryPass = windows.All(WindowReady);
            var doorRegistryPass = doors.All(DoorReady);
            var floorBuildUpPass = buildUps.Length == 1 && BuildUpReady(buildUps[0], level);
            var requiredByCrossFloorSystem = requiredPhysicalFloorIds.Contains(level.Id);
            var pass = !requiredByCrossFloorSystem || architectureFloorScopePass && sharedDatumPass && registryDeclarationPass &&
                       wallGeometryPass && windowRegistryPass && doorRegistryPass && floorBuildUpPass;
            return new FloorPhysicalInputReadinessDetail
            {
                FloorId = level.Id,
                ServedByCollector = servedFloorIds.Contains(level.Id),
                RequiredByCrossFloorSystem = requiredByCrossFloorSystem,
                RoomCount = project.Rooms.Count(item => item.FloorId == level.Id),
                ExplicitWallCount = walls.Length,
                ExplicitWindowCount = windows.Length,
                ExplicitDoorCount = doors.Length,
                FloorBuildUpCount = buildUps.Length,
                SharedDatumPass = sharedDatumPass,
                RegistryDeclarationPass = registryDeclarationPass,
                WallGeometryPass = wallGeometryPass,
                WindowRegistryPass = windowRegistryPass,
                DoorAndThresholdRegistryPass = doorRegistryPass,
                FloorBuildUpAndPipeAxisPass = floorBuildUpPass,
                Pass = pass,
            };
        }).ToArray();

        static string PairKey(string first, string second) => string.CompareOrdinal(first, second) < 0
            ? $"{first}\0{second}" : $"{second}\0{first}";
        static bool Connects(InterfloorOpening opening, string first, string second) =>
            opening.FromFloorId == first && opening.ToFloorId == second ||
            opening.FromFloorId == second && opening.ToFloorId == first;
        bool ShapeAndAxisReady(InterfloorOpening opening)
        {
            return IndependentlyVerified(opening.PhysicalVerification) &&
                   opening.SharedDatumId == datum?.Id && levels.Contains(opening.FromFloorId) && levels.Contains(opening.ToFloorId) &&
                   (opening.CenterlineMmSharedDatum is null || opening.CenterlineMmSharedDatum.All(point =>
                       double.IsFinite(point.X) && double.IsFinite(point.Y) && point.X >= 0 && point.Y >= 0 &&
                       point.X <= project.CanvasWidthMm && point.Y <= project.CanvasHeightMm)) &&
                   HomeAuraProject.IsInterfloorOpeningShapeAndAxisReady(opening);
        }
        bool StructurallyApproved(InterfloorOpening opening)
        {
            if (opening.StructuralDisposition is not
                { Status: "EXISTING_OPENING_ACCEPTED" or "NEW_OPENING_APPROVED" } disposition ||
                string.IsNullOrWhiteSpace(disposition.RecordId) || string.IsNullOrWhiteSpace(disposition.AuthorityName) ||
                string.IsNullOrWhiteSpace(disposition.ApprovalDate) ||
                !DateOnly.TryParseExact(disposition.ApprovalDate, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture,
                    System.Globalization.DateTimeStyles.None, out _) ||
                disposition.ApprovedClearOutlineMm is not { Count: >= 3 } || disposition.AuthorityDocumentPaths is null ||
                disposition.AuthorityDocumentPaths.Any(string.IsNullOrWhiteSpace) ||
                string.IsNullOrWhiteSpace(disposition.AuthorityDocumentId) && disposition.AuthorityDocumentPaths.Count == 0)
                return false;
            if (opening.SharedDatumId != datum?.Id || !levels.Contains(opening.FromFloorId) || !levels.Contains(opening.ToFloorId) ||
                opening.FromFloorFace.FloorId != opening.FromFloorId || opening.ToFloorFace.FloorId != opening.ToFloorId)
                return false;
            var tolerance = opening.PhysicalVerification?.SurveyToleranceMm ?? 0;
            IReadOnlyList<Point3Mm>? projectedAxis = opening.ClearAxisDefinitionMethod == "CENTERLINE_POLYLINE"
                ? opening.CenterlineMmSharedDatum
                : opening.FromFloorFace.CenterMmSharedDatum is not null && opening.ToFloorFace.CenterMmSharedDatum is not null
                    ? [opening.FromFloorFace.CenterMmSharedDatum, opening.ToFloorFace.CenterMmSharedDatum]
                    : null;
            return HomeAuraProject.PolygonContainsPolygon(disposition.ApprovedClearOutlineMm,
                       opening.FromFloorFace.VerifiedPlanOutlineMm, tolerance) &&
                   HomeAuraProject.PolygonContainsPolygon(disposition.ApprovedClearOutlineMm,
                       opening.ToFloorFace.VerifiedPlanOutlineMm, tolerance) &&
                   HomeAuraProject.PolygonContainsPolyline(disposition.ApprovedClearOutlineMm,
                       projectedAxis, tolerance);
        }

        var explicitCrossFloorCollectors = crossFloorCollectors
            .Where(item => !string.IsNullOrWhiteSpace(item.FloorId) && !string.IsNullOrWhiteSpace(item.ServedFloorId) &&
                           item.FloorId != item.ServedFloorId)
            .ToArray();
        var pairGroups = explicitCrossFloorCollectors.GroupBy(item => PairKey(item.FloorId!, item.ServedFloorId!), StringComparer.Ordinal)
            .Select(group => (Installed: group.First().FloorId!, Served: group.First().ServedFloorId!)).ToArray();
        var openingDetails = pairGroups.Select(pair =>
        {
            var registry = (project.InterfloorOpeningRegistryVerifications ?? []).SingleOrDefault(item =>
                PairKey(item.FromFloorId, item.ToFloorId) == PairKey(pair.Installed, pair.Served));
            var registryPass = registry is { PopulationComplete: true } &&
                DatumMatches(datum, registry.SharedDatumId, pair.Installed) &&
                DatumMatches(datum, registry.SharedDatumId, pair.Served) && IndependentlyVerified(registry.PhysicalVerification);
            var openings = (project.InterfloorOpenings ?? []).Where(item => Connects(item, pair.Installed, pair.Served)).ToArray();
            var verified = openings.Where(ShapeAndAxisReady).ToArray();
            var pairedFacePass = openings.Length > 0 && verified.Length == openings.Length;
            var structuralPass = openings.Length > 0 && openings.All(StructurallyApproved);
            return new InterfloorOpeningReadinessDetail
            {
                FromFloorId = pair.Installed,
                ToFloorId = pair.Served,
                RegistryDeclarationPass = registryPass,
                OpeningCount = openings.Length,
                IndependentlyVerifiedOpeningCount = verified.Length,
                PairedFaceGeometryPass = pairedFacePass,
                StructuralDispositionPass = structuralPass,
                RoutingInputPass = registryPass && pairedFacePass,
            };
        }).ToArray();
        var collectorReferencesPass = crossFloorCollectors.All(item =>
            !string.IsNullOrWhiteSpace(item.FloorId) && !string.IsNullOrWhiteSpace(item.ServedFloorId) &&
            levels.Contains(item.FloorId) && levels.Contains(item.ServedFloorId));
        var verifiedInterfloorOpeningInputPass = schema11PhysicalContractPass && (!applicable || collectorReferencesPass &&
            openingDetails.Length > 0 && openingDetails.All(item => item.RoutingInputPass));
        var verifiedArchitectureInputPass = schema11PhysicalContractPass && (!applicable || architectureFloorScopePass &&
            floorDetails.Where(item => item.RequiredByCrossFloorSystem).All(item => item.Pass) &&
            collectorReferencesPass);
        var structuralDispositionPass = schema11PhysicalContractPass &&
            (!applicable || collectorReferencesPass && openingDetails.Length > 0 &&
                openingDetails.All(item => item.StructuralDispositionPass));
        // v1.1 can validate physical inputs, but it deliberately has no segment-to-opening crossing DTO.
        var routeOpeningBindingPass = schema11PhysicalContractPass && !applicable;
        var collectorDetails = crossFloorCollectors.Select(collector =>
        {
            var opening = string.IsNullOrWhiteSpace(collector.FloorId) || string.IsNullOrWhiteSpace(collector.ServedFloorId)
                ? null
                : openingDetails.SingleOrDefault(item => PairKey(item.FromFloorId, item.ToFloorId) ==
                    PairKey(collector.FloorId, collector.ServedFloorId));
            return new CrossFloorCollectorReadinessDetail
            {
                CollectorId = collector.Id,
                InstalledFloorId = collector.FloorId,
                ServedFloorId = collector.ServedFloorId,
                FloorReferencesPass = !string.IsNullOrWhiteSpace(collector.FloorId) &&
                                      !string.IsNullOrWhiteSpace(collector.ServedFloorId) &&
                                      levels.Contains(collector.FloorId) && levels.Contains(collector.ServedFloorId),
                VerifiedOpeningInputPass = opening?.RoutingInputPass == true,
                MaterializedRouteOpeningBindingPass = false,
            };
        }).ToArray();
        var routingInputReadinessPass = schema11PhysicalContractPass &&
            (!applicable || verifiedArchitectureInputPass && verifiedInterfloorOpeningInputPass);
        var installationInputReadinessPass = schema11PhysicalContractPass &&
            (!applicable || routingInputReadinessPass && structuralDispositionPass);
        var reasons = new List<string>();
        if (!schema11PhysicalContractPass) reasons.Add("SCHEMA_1_1_CONTRACT_INVALID");
        if (applicable && !collectorReferencesPass)
            reasons.Add("CROSS_FLOOR_REFERENCE_MISSING");
        if (applicable && project.Walls.Any(item => requiredPhysicalFloorIds.Contains(item.FloorId ?? "") &&
                ((item.Start.X == item.End.X) == (item.Start.Y == item.End.Y))))
            reasons.Add("UNSUPPORTED_WALL_GEOMETRY");
        if (!architectureFloorScopePass) reasons.Add("UNSCOPED_ARCHITECTURE_OBJECTS");
        if (!verifiedArchitectureInputPass) reasons.Add("VERIFIED_FLOOR_ARCHITECTURE_INCOMPLETE");
        if (!verifiedInterfloorOpeningInputPass) reasons.Add("VERIFIED_INTERFLOOR_OPENING_INPUT_INCOMPLETE");
        if (!structuralDispositionPass) reasons.Add("STRUCTURAL_DISPOSITION_INCOMPLETE");
        if (!routeOpeningBindingPass) reasons.Add("MATERIALIZED_ROUTE_OPENING_BINDING_NOT_MODELED");
        return new PhysicalInputReadinessDetail
        {
            Applicable = applicable,
            ArchitectureFloorScopePass = architectureFloorScopePass,
            UnscopedWallIds = unscopedWallIds,
            UnscopedWindowIds = unscopedWindowIds,
            FloorDetails = floorDetails,
            InterfloorOpeningDetails = openingDetails,
            CrossFloorCollectorDetails = collectorDetails,
            VerifiedArchitectureInputPass = verifiedArchitectureInputPass,
            VerifiedInterfloorOpeningInputPass = verifiedInterfloorOpeningInputPass,
            RoutingInputReadinessPass = routingInputReadinessPass,
            StructuralDispositionPass = structuralDispositionPass,
            RouteOpeningBindingPass = routeOpeningBindingPass,
            InstallationInputReadinessPass = installationInputReadinessPass,
            ReasonCodes = reasons,
        };
    }

    public static IReadOnlyList<HeatingBodyRange> GetHeatingBodyRanges(ManualCircuit circuit)
    {
        if (circuit.HeatingBodyRanges.Count > 0) return circuit.HeatingBodyRanges;
        if (circuit.HeatingBodyStartIndex is null || circuit.HeatingBodyEndIndex is null) return [];
        return [new HeatingBodyRange
        {
            StartIndex = circuit.HeatingBodyStartIndex.Value,
            EndIndex = circuit.HeatingBodyEndIndex.Value,
        }];
    }

    public static bool IsHeatingBodySegment(ManualCircuit circuit, int circuitSegmentIndex) =>
        GetHeatingBodyRanges(circuit).Any(range => circuitSegmentIndex >= range.StartIndex && circuitSegmentIndex < range.EndIndex);

    public static Point3Mm ResolvePoint3(ManualCircuit circuit, PointMm point) => ResolvePoint(circuit, point);

    public static RoundedPlanAxisGeometry SampleRoundedPlanAxis(
        ManualCircuit circuit,
        int radiusMm,
        double maximumSagittaMm = 0.05)
    {
        ArgumentNullException.ThrowIfNull(circuit);
        if (radiusMm <= 0) throw new ArgumentOutOfRangeException(nameof(radiusMm));
        if (!double.IsFinite(maximumSagittaMm) || maximumSagittaMm <= 0)
            throw new ArgumentOutOfRangeException(nameof(maximumSagittaMm));

        var rawPoints = circuit.OrderedPoints.Select(point => ResolvePoint(circuit, point)).ToArray();
        var rawPlanLength = Enumerable.Range(0, Math.Max(0, rawPoints.Length - 1))
            .Sum(index => PlanDistance(rawPoints[index], rawPoints[index + 1]));
        if (rawPoints.Length < 2)
        {
            return new RoundedPlanAxisGeometry
            {
                SampledPoints = rawPoints,
                RadiusMm = radiusMm,
                FullyMaterialized = true,
                ExactLengthMm = rawPlanLength,
                SampledLengthMm = rawPlanLength,
            };
        }

        var materialized = MaterializeGeometry(circuit, radiusMm);
        var bend = AnalyzeBends(circuit, materialized.Transitions, radiusMm);
        var fullyMaterialized = bend.Violations.Count == 0 && bend.HorizontalFillets.Count == bend.TurnCount;
        if (!fullyMaterialized)
        {
            return new RoundedPlanAxisGeometry
            {
                SampledPoints = rawPoints,
                RadiusMm = radiusMm,
                TurnCount = bend.TurnCount,
                FullyMaterialized = false,
                ExactLengthMm = rawPlanLength,
                SampledLengthMm = rawPlanLength,
            };
        }

        var filletByPointIndex = bend.HorizontalFillets.ToDictionary(item => item.PointIndex);
        var sampledPoints = new List<Point3Mm>(rawPoints.Length + bend.HorizontalFillets.Count * 8);
        var maximumActualSagitta = 0d;

        void Add(Point3Mm point)
        {
            if (sampledPoints.Count > 0 && PlanDistance(sampledPoints[^1], point) <= 0.0000001)
            {
                sampledPoints[^1] = point;
                return;
            }
            sampledPoints.Add(point);
        }

        Add(rawPoints[0]);
        for (var pointIndex = 1; pointIndex + 1 < rawPoints.Length; pointIndex++)
        {
            if (!filletByPointIndex.TryGetValue(pointIndex, out var fillet))
            {
                Add(rawPoints[pointIndex]);
                continue;
            }

            Add(fillet.ArcStart);
            var arc = SampleHorizontalFillet(fillet, maximumSagittaMm);
            maximumActualSagitta = Math.Max(maximumActualSagitta, arc.MaximumSagittaMm);
            foreach (var point in arc.Points.Skip(1)) Add(point);
        }
        Add(rawPoints[^1]);

        var exactLength = rawPlanLength - bend.HorizontalFillets.Sum(item => item.RoundedLengthCorrectionMm);
        var sampledLength = Enumerable.Range(0, sampledPoints.Count - 1)
            .Sum(index => PlanDistance(sampledPoints[index], sampledPoints[index + 1]));
        return new RoundedPlanAxisGeometry
        {
            SampledPoints = sampledPoints,
            RadiusMm = radiusMm,
            TurnCount = bend.TurnCount,
            FilletCount = bend.HorizontalFillets.Count,
            FullyMaterialized = true,
            ExactLengthMm = exactLength,
            SampledLengthMm = sampledLength,
            MaximumSagittaMm = maximumActualSagitta,
        };
    }

    private static Point3Mm ResolvePoint(ManualCircuit circuit, PointMm point) =>
        new(point.X, point.Y, point.Z ?? circuit.AxisElevationMm ?? 0);

    private static double PlanDistance(Point3Mm first, Point3Mm second)
    {
        var dx = second.X - first.X;
        var dy = second.Y - first.Y;
        return Math.Sqrt(dx * dx + dy * dy);
    }

    private static MaterializedCircuitGeometry MaterializeGeometry(ManualCircuit circuit, int minimumRadiusMm)
    {
        var transitionBySegment = circuit.VerticalTransitions
            .GroupBy(item => item.SegmentIndex)
            .ToDictionary(group => group.Key, group => group.First());
        var segments = new List<MaterializedSegment3D>();
        var transitionDetails = new List<VerticalTransitionAnalysisDetail>();
        var axisLength = 0d;
        var unmaterializedChanges = 0;

        for (var segmentIndex = 0; segmentIndex + 1 < circuit.OrderedPoints.Count; segmentIndex++)
        {
            var start = ResolvePoint(circuit, circuit.OrderedPoints[segmentIndex]);
            var end = ResolvePoint(circuit, circuit.OrderedPoints[segmentIndex + 1]);
            if (!transitionBySegment.TryGetValue(segmentIndex, out var transition))
            {
                if (Math.Abs(start.Z - end.Z) > 0.001) unmaterializedChanges++;
                segments.Add(new MaterializedSegment3D(segmentIndex, start, end, 0));
                axisLength += Distance3(start, end);
                continue;
            }

            var detail = AnalyzeVerticalTransition(segmentIndex, transition, start, end, minimumRadiusMm);
            transitionDetails.Add(detail);
            if (!detail.GeometryPass)
            {
                segments.Add(new MaterializedSegment3D(segmentIndex, start, end, 0));
                axisLength += Distance3(start, end);
                continue;
            }
            var firstArcSegmentIndex = detail.StartTangentLengthMm > 0.000001 ? 1 : 0;
            var afterArcSegmentIndex = firstArcSegmentIndex + 2 * detail.EffectiveArcSamplesPerHalf;
            for (var sampleIndex = 0; sampleIndex + 1 < detail.SampledAxisPoints.Count; sampleIndex++)
            {
                var approximationError = sampleIndex >= firstArcSegmentIndex && sampleIndex < afterArcSegmentIndex
                    ? detail.MaximumChordErrorMm
                    : 0;
                segments.Add(new MaterializedSegment3D(
                    segmentIndex,
                    detail.SampledAxisPoints[sampleIndex],
                    detail.SampledAxisPoints[sampleIndex + 1],
                    approximationError));
            }
            axisLength += detail.AxisLengthMm;
        }

        return new MaterializedCircuitGeometry(segments, transitionDetails, axisLength, unmaterializedChanges);
    }

    private static VerticalTransitionAnalysisDetail AnalyzeVerticalTransition(
        int segmentIndex,
        VerticalTransition transition,
        Point3Mm start,
        Point3Mm end,
        int minimumRadiusMm)
    {
        var dx = end.X - start.X;
        var dy = end.Y - start.Y;
        var planLength = Math.Sqrt(dx * dx + dy * dy);
        var verticalDelta = Math.Abs(end.Z - start.Z);
        var structurallyFinite = double.IsFinite(transition.RadiusMm) && transition.RadiusMm > 0 &&
                                 double.IsFinite(transition.StartTangentLengthMm) && transition.StartTangentLengthMm >= 0 &&
                                 double.IsFinite(transition.EndTangentLengthMm) && transition.EndTangentLengthMm >= 0;
        var angle = structurallyFinite && verticalDelta > 0 && verticalDelta <= 2 * transition.RadiusMm
            ? Math.Acos(Math.Clamp(1 - verticalDelta / (2 * transition.RadiusMm), -1, 1))
            : double.NaN;
        var arcProjection = double.IsFinite(angle) ? 2 * transition.RadiusMm * Math.Sin(angle) : double.NaN;
        var materializedProjection = transition.StartTangentLengthMm + arcProjection + transition.EndTangentLengthMm;
        var geometryPass = transition.Kind == "S_BEND_R80" && structurallyFinite && verticalDelta > 0.001 && planLength > 0.001 &&
                           (Math.Abs(dx) <= 0.001 || Math.Abs(dy) <= 0.001) && double.IsFinite(arcProjection) &&
                           Math.Abs(materializedProjection - planLength) <= 0.05;
        var effectiveSamples = geometryPass
            ? Math.Max(transition.ArcSamplesPerHalf, RequiredArcSamples(transition.RadiusMm, angle, 0.05))
            : transition.ArcSamplesPerHalf;
        var samples = geometryPass
            ? SampleVerticalTransition(start, end, transition, angle, arcProjection, effectiveSamples)
            : new[] { start, end };
        var arcLength = double.IsFinite(angle) ? 2 * transition.RadiusMm * angle : 0;
        var chordError = geometryPass
            ? transition.RadiusMm * (1 - Math.Cos(angle / (2 * effectiveSamples)))
            : 0;
        return new VerticalTransitionAnalysisDetail
        {
            CircuitSegmentIndex = segmentIndex,
            Kind = transition.Kind,
            Start = start,
            End = end,
            VerticalDeltaMm = verticalDelta,
            PlanProjectionMm = planLength,
            RadiusMm = transition.RadiusMm,
            TurnAngleRadians = double.IsFinite(angle) ? angle : 0,
            RequiredArcProjectionMm = double.IsFinite(arcProjection) ? arcProjection : 0,
            StartTangentLengthMm = transition.StartTangentLengthMm,
            EndTangentLengthMm = transition.EndTangentLengthMm,
            ArcLengthMm = arcLength,
            AxisLengthMm = geometryPass ? transition.StartTangentLengthMm + arcLength + transition.EndTangentLengthMm : Distance3(start, end),
            RequestedArcSamplesPerHalf = transition.ArcSamplesPerHalf,
            EffectiveArcSamplesPerHalf = effectiveSamples,
            MaximumChordErrorMm = chordError,
            GeometryPass = geometryPass,
            RadiusPass = transition.RadiusMm + 0.001 >= minimumRadiusMm,
            SampledAxisPoints = samples,
        };
    }

    private static IReadOnlyList<Point3Mm> SampleVerticalTransition(
        Point3Mm start,
        Point3Mm end,
        VerticalTransition transition,
        double angle,
        double arcProjection,
        int samplesPerHalf)
    {
        var dx = end.X - start.X;
        var dy = end.Y - start.Y;
        var planLength = Math.Sqrt(dx * dx + dy * dy);
        var unitX = dx / planLength;
        var unitY = dy / planLength;
        var verticalSign = Math.Sign(end.Z - start.Z);
        var points = new List<Point3Mm> { start };

        void AddAt(double along, double z)
        {
            var point = new Point3Mm(start.X + unitX * along, start.Y + unitY * along, z);
            if (Distance3(points[^1], point) > 0.000001) points.Add(point);
        }

        AddAt(transition.StartTangentLengthMm, start.Z);
        for (var sample = 1; sample <= samplesPerHalf; sample++)
        {
            var phi = angle * sample / samplesPerHalf;
            var along = transition.StartTangentLengthMm + transition.RadiusMm * Math.Sin(phi);
            var z = start.Z + verticalSign * transition.RadiusMm * (1 - Math.Cos(phi));
            AddAt(along, z);
        }
        for (var sample = 1; sample <= samplesPerHalf; sample++)
        {
            var psi = angle * sample / samplesPerHalf;
            var along = transition.StartTangentLengthMm + transition.RadiusMm * Math.Sin(angle) +
                        transition.RadiusMm * (Math.Sin(angle) - Math.Sin(angle - psi));
            var zOffset = transition.RadiusMm * (1 - 2 * Math.Cos(angle) + Math.Cos(angle - psi));
            AddAt(along, start.Z + verticalSign * zOffset);
        }
        AddAt(transition.StartTangentLengthMm + arcProjection + transition.EndTangentLengthMm, end.Z);
        if (Distance3(points[^1], end) > 0.000001) points.Add(end);
        else points[^1] = end;
        return points;
    }

    private static int RequiredArcSamples(double radiusMm, double angleRadians, double maximumSagittaMm)
    {
        if (radiusMm <= 0 || angleRadians <= 0 || maximumSagittaMm <= 0) return 2;
        var maximumStep = 2 * Math.Acos(Math.Clamp(1 - maximumSagittaMm / radiusMm, -1, 1));
        if (maximumStep <= 0.0000001) return 256;
        return Math.Clamp((int)Math.Ceiling(angleRadians / maximumStep), 2, 256);
    }

    private static (IReadOnlyList<Point3Mm> Points, double MaximumSagittaMm) SampleHorizontalFillet(
        HorizontalFillet fillet,
        double maximumSagittaMm)
    {
        var samples = RequiredArcSamples(fillet.RadiusMm, fillet.AngleRadians, maximumSagittaMm);
        var actualSagitta = fillet.RadiusMm *
                            (1 - Math.Cos(Math.Abs(fillet.SignedSweepRadians) / (2 * samples)));
        var points = Enumerable.Range(0, samples + 1)
            .Select(sample =>
            {
                var angle = fillet.StartAngleRadians + fillet.SignedSweepRadians * sample / samples;
                return new Point3Mm(
                    fillet.ArcCenter.X + fillet.RadiusMm * Math.Cos(angle),
                    fillet.ArcCenter.Y + fillet.RadiusMm * Math.Sin(angle),
                    fillet.ArcCenter.Z);
            })
            .ToArray();
        points[0] = fillet.ArcStart;
        points[^1] = fillet.ArcEnd;
        return (points, actualSagitta);
    }

    private static IReadOnlyList<PointMm> HeatingBodyPoints(ManualCircuit circuit) =>
        GetHeatingBodyRanges(circuit)
            .SelectMany(range => circuit.OrderedPoints.Skip(range.StartIndex).Take(range.EndIndex - range.StartIndex + 1))
            .ToArray();

    private static IReadOnlyList<IndexedCircuitSegment> HeatingBodySegments(ManualCircuit circuit) =>
        GetHeatingBodyRanges(circuit)
            .SelectMany(range => Enumerable.Range(range.StartIndex, range.EndIndex - range.StartIndex)
                .Select(segmentIndex => new IndexedCircuitSegment(
                    segmentIndex,
                    circuit.OrderedPoints[segmentIndex],
                    circuit.OrderedPoints[segmentIndex + 1])))
            .ToArray();

    private static bool HeatingBodyInsideAssignedRoom(
        HomeAuraProject project,
        ManualCircuit circuit,
        IReadOnlyList<PointMm> points,
        IReadOnlyList<IndexedCircuitSegment> segments)
    {
        if (points.Count == 0) return true;
        var room = project.Rooms.SingleOrDefault(item => item.Id == circuit.RoomId);
        if (room is null) return false;
        if (points.Any(point => !Covers(room.Outline, point))) return false;
        foreach (var segment in segments)
        {
            var midpoint = new PointMm((segment.A.X + segment.B.X) / 2, (segment.A.Y + segment.B.Y) / 2);
            if (!Covers(room.Outline, midpoint)) return false;
        }
        return true;
    }

    public static double Distance(PointMm first, PointMm second)
    {
        var dx = first.X - second.X;
        var dy = first.Y - second.Y;
        return Math.Sqrt((double)dx * dx + (double)dy * dy);
    }

    public static double Distance3(Point3Mm first, Point3Mm second)
    {
        var dx = first.X - second.X;
        var dy = first.Y - second.Y;
        var dz = first.Z - second.Z;
        return Math.Sqrt(dx * dx + dy * dy + dz * dz);
    }

    public static PointMm Snap(int x, int y, int grid = 100) => new(
        (int)Math.Round(x / (double)grid, MidpointRounding.AwayFromZero) * grid,
        (int)Math.Round(y / (double)grid, MidpointRounding.AwayFromZero) * grid);

    private static bool NearAssignedConnection(HomeAuraProject project, ManualCircuit circuit, PointMm point, int? connectionIndex)
    {
        if (circuit.ServiceZoneId is not null)
        {
            var zone = project.ServiceZones.SingleOrDefault(item => item.Id == circuit.ServiceZoneId);
            if (zone is not null && Covers(zone.Outline, point)) return true;
        }
        return (circuit.CollectorId is null ? project.Collectors : project.Collectors.Where(item => item.Id == circuit.CollectorId))
            .Any(collector =>
            {
                if (connectionIndex is not null && collector.ResolveConnectionPoints().FirstOrDefault(item => item.ConnectionIndex == connectionIndex) is { } connection)
                {
                    var target = collector.ConnectionPointWorldPosition(connection, collector.MountingWallAngleDegrees(project));
                    var dx = target.X - point.X;
                    var dy = target.Y - point.Y;
                    return Math.Sqrt(dx * dx + dy * dy) <= collector.ConnectionToleranceMm;
                }
                if (collector.HasPhysicalReferenceGeometry) return false;
                return Distance(collector.Position, point) <= collector.ConnectionToleranceMm;
            });
    }

    private static bool Covers(IReadOnlyList<PointMm> polygon, PointMm point)
    {
        if (polygon.Count < 3) return false;
        for (var i = 0; i < polygon.Count; i++)
            if (PointToSegmentDistance(point, polygon[i], polygon[(i + 1) % polygon.Count]) < 0.001) return true;
        var inside = false;
        for (int i = 0, j = polygon.Count - 1; i < polygon.Count; j = i++)
        {
            var a = polygon[i]; var b = polygon[j];
            if ((a.Y > point.Y) != (b.Y > point.Y) &&
                point.X < (double)(b.X - a.X) * (point.Y - a.Y) / (b.Y - a.Y) + a.X) inside = !inside;
        }
        return inside;
    }

    private static double PointToSegmentDistance(PointMm point, PointMm start, PointMm end)
    {
        var dx = end.X - start.X; var dy = end.Y - start.Y;
        if (dx == 0 && dy == 0) return Distance(point, start);
        var t = Math.Clamp(((point.X - start.X) * dx + (point.Y - start.Y) * dy) / (double)(dx * dx + dy * dy), 0, 1);
        var x = start.X + t * dx; var y = start.Y + t * dy;
        return Math.Sqrt(Math.Pow(point.X - x, 2) + Math.Pow(point.Y - y, 2));
    }

    private static IEnumerable<(PointMm A, PointMm B)> Segments(IReadOnlyList<PointMm> points)
    {
        for (var i = 0; i + 1 < points.Count; i++) yield return (points[i], points[i + 1]);
    }

    private static SelfClearanceAnalysis AnalyzeSelfClearance(
        HomeAuraProject project,
        ManualCircuit circuit,
        IReadOnlyList<MaterializedSegment3D> materializedSegments)
    {
        var requiredAxis = RequiredAxisClearance(project);
        var pipeDiameter = project.RoutingRules.PipeOuterDiameterMm;
        var grouped = materializedSegments.GroupBy(item => item.CircuitSegmentIndex).ToDictionary(group => group.Key, group => group.ToArray());
        var planContacts = 0;
        var surfaceViolations = 0;
        var violations = new List<SelfSurfaceClearanceViolationDetail>();
        foreach (var firstIndex in grouped.Keys.Order())
        foreach (var secondIndex in grouped.Keys.Where(index => index >= firstIndex + 2).Order())
        {
            if (firstIndex == 0 && secondIndex == circuit.OrderedPoints.Count - 2 &&
                Distance3(ResolvePoint(circuit, circuit.OrderedPoints[0]), ResolvePoint(circuit, circuit.OrderedPoints[^1])) <= 0.001)
                continue;
            var groupClearance = MinimumSegmentGroupClearance(grouped[firstIndex], grouped[secondIndex]);
            var minimum = groupClearance.ConservativeDistanceMm;
            if (minimum + 0.001 < requiredAxis)
            {
                surfaceViolations++;
                violations.Add(new SelfSurfaceClearanceViolationDetail
                {
                    FirstCircuitSegmentIndex = firstIndex,
                    SecondCircuitSegmentIndex = secondIndex,
                    AxisClearanceMm = minimum,
                    SurfaceClearanceMm = minimum - pipeDiameter,
                    RequiredAxisClearanceMm = requiredAxis,
                    RequiredSurfaceClearanceMm = project.RoutingRules.MinimumLayerSurfaceClearanceMm,
                    ClearanceErrorBoundMm = groupClearance.ErrorBoundMm,
                });
            }
            var crossingClearance = MinimumPlanCrossingAxisClearance(grouped[firstIndex], grouped[secondIndex]);
            if (crossingClearance is not null && crossingClearance.Value + 0.001 < requiredAxis) planContacts++;
        }
        return new SelfClearanceAnalysis(planContacts, surfaceViolations, violations);
    }

    private static ClearanceAnalysis AnalyzeInterCircuitClearance(
        HomeAuraProject project,
        ManualCircuit circuit,
        IReadOnlyList<MaterializedSegment3D> materializedSegments,
        IReadOnlySet<string>? includedOtherCircuitIds = null)
    {
        var requiredAxis = RequiredAxisClearance(project);
        var pipeDiameter = project.RoutingRules.PipeOuterDiameterMm;
        var currentGroups = materializedSegments.GroupBy(item => item.CircuitSegmentIndex).ToDictionary(group => group.Key, group => group.ToArray());
        var contacts = 0;
        var surfaceViolationCount = 0;
        var clearCrossings = 0;
        var minimumAxis = double.PositiveInfinity;
        var minimumAxisErrorBound = 0d;
        var violations = new List<SurfaceClearanceViolationDetail>();
        var stacks = new List<StackCrossingDetail>();

        foreach (var other in project.Circuits.Where(item => item.Id != circuit.Id &&
                     (includedOtherCircuitIds is null || includedOtherCircuitIds.Contains(item.Id)) &&
                     CircuitScopesMayInteract(project, circuit, item)))
        {
            var otherGeometry = MaterializeGeometry(other, project.RoutingRules.MinimumBendRadiusMm);
            var otherGroups = otherGeometry.Segments.GroupBy(item => item.CircuitSegmentIndex).ToDictionary(group => group.Key, group => group.ToArray());
            foreach (var firstGroup in currentGroups)
            foreach (var secondGroup in otherGroups)
            {
                var groupClearance = MinimumSegmentGroupClearance(firstGroup.Value, secondGroup.Value);
                var axisDistance = groupClearance.ConservativeDistanceMm;
                if (axisDistance < minimumAxis)
                {
                    minimumAxis = axisDistance;
                    minimumAxisErrorBound = groupClearance.ErrorBoundMm;
                }
                if (axisDistance + 0.001 < requiredAxis)
                {
                    surfaceViolationCount++;
                    violations.Add(new SurfaceClearanceViolationDetail
                    {
                        CircuitSegmentIndex = firstGroup.Key,
                        OtherCircuitId = other.Id,
                        OtherCircuitSegmentIndex = secondGroup.Key,
                        AxisClearanceMm = axisDistance,
                        SurfaceClearanceMm = axisDistance - pipeDiameter,
                        RequiredAxisClearanceMm = requiredAxis,
                        RequiredSurfaceClearanceMm = project.RoutingRules.MinimumLayerSurfaceClearanceMm,
                        ClearanceErrorBoundMm = groupClearance.ErrorBoundMm,
                    });
                }

                var crossing = BestPlanCrossing(firstGroup.Value, secondGroup.Value);
                if (crossing is null) continue;
                if (crossing.Value.AxisClearanceMm + 0.001 < requiredAxis)
                {
                    contacts++;
                    continue;
                }
                clearCrossings++;
                stacks.Add(new StackCrossingDetail
                {
                    CircuitSegmentIndex = firstGroup.Key,
                    OtherCircuitId = other.Id,
                    OtherCircuitSegmentIndex = secondGroup.Key,
                    Position = new PointMm(
                        (int)Math.Round(crossing.Value.X, MidpointRounding.AwayFromZero),
                        (int)Math.Round(crossing.Value.Y, MidpointRounding.AwayFromZero)),
                    LowerAxisElevationMm = Math.Min(crossing.Value.FirstZ, crossing.Value.SecondZ),
                    UpperAxisElevationMm = Math.Max(crossing.Value.FirstZ, crossing.Value.SecondZ),
                    AxisClearanceMm = crossing.Value.AxisClearanceMm,
                    SurfaceClearanceMm = crossing.Value.AxisClearanceMm - pipeDiameter,
                    ClearanceErrorBoundMm = crossing.Value.ErrorBoundMm,
                });
            }
        }
        return new ClearanceAnalysis(
            contacts,
            surfaceViolationCount,
            clearCrossings,
            double.IsPositiveInfinity(minimumAxis) ? null : minimumAxis,
            double.IsPositiveInfinity(minimumAxis) ? null : minimumAxisErrorBound,
            violations,
            stacks);
    }

    private static double RequiredAxisClearance(HomeAuraProject project) => Math.Max(
        project.RoutingRules.MinimumLayerAxisSeparationMm,
        project.RoutingRules.PipeOuterDiameterMm + project.RoutingRules.MinimumLayerSurfaceClearanceMm);

    private static (double ConservativeDistanceMm, double ErrorBoundMm) MinimumSegmentGroupClearance(
        IReadOnlyList<MaterializedSegment3D> first,
        IReadOnlyList<MaterializedSegment3D> second)
    {
        var bestDistance = double.PositiveInfinity;
        var bestError = 0d;
        foreach (var a in first)
        foreach (var b in second)
        {
            var error = a.ApproximationErrorMm + b.ApproximationErrorMm;
            var conservativeDistance = Math.Max(0, SegmentDistance3(a.A, a.B, b.A, b.B) - error);
            if (conservativeDistance >= bestDistance) continue;
            bestDistance = conservativeDistance;
            bestError = error;
        }
        return (bestDistance, bestError);
    }

    private static double MinimumSegmentGroupDistance(
        IReadOnlyList<MaterializedSegment3D> first,
        IReadOnlyList<MaterializedSegment3D> second) => MinimumSegmentGroupClearance(first, second).ConservativeDistanceMm;

    private static double? MinimumPlanCrossingAxisClearance(
        IReadOnlyList<MaterializedSegment3D> first,
        IReadOnlyList<MaterializedSegment3D> second) => BestPlanCrossing(first, second)?.AxisClearanceMm;

    private static (double X, double Y, double FirstZ, double SecondZ, double AxisClearanceMm, double ErrorBoundMm)? BestPlanCrossing(
        IReadOnlyList<MaterializedSegment3D> first,
        IReadOnlyList<MaterializedSegment3D> second)
    {
        (double X, double Y, double FirstZ, double SecondZ, double AxisClearanceMm, double ErrorBoundMm)? best = null;
        foreach (var a in first)
        foreach (var b in second)
        {
            if (!TryPlanIntersection(a.A, a.B, b.A, b.B, out var x, out var y)) continue;
            var firstZ = ElevationAtPlanPoint(a.A, a.B, x, y);
            var secondZ = ElevationAtPlanPoint(b.A, b.B, x, y);
            var errorBound = a.ApproximationErrorMm + b.ApproximationErrorMm;
            var clearance = Math.Max(0, Math.Abs(firstZ - secondZ) - errorBound);
            if (best is null || clearance < best.Value.AxisClearanceMm)
                best = (x, y, firstZ, secondZ, clearance, errorBound);
        }
        return best;
    }

    private static bool TryPlanIntersection(
        Point3Mm firstStart,
        Point3Mm firstEnd,
        Point3Mm secondStart,
        Point3Mm secondEnd,
        out double x,
        out double y)
    {
        x = y = 0;
        var rx = firstEnd.X - firstStart.X;
        var ry = firstEnd.Y - firstStart.Y;
        var sx = secondEnd.X - secondStart.X;
        var sy = secondEnd.Y - secondStart.Y;
        var qpx = secondStart.X - firstStart.X;
        var qpy = secondStart.Y - firstStart.Y;
        var rxs = Cross2(rx, ry, sx, sy);
        var qpxr = Cross2(qpx, qpy, rx, ry);
        const double tolerance = 0.000001;

        if (Math.Abs(rxs) > tolerance)
        {
            var t = Cross2(qpx, qpy, sx, sy) / rxs;
            var u = Cross2(qpx, qpy, rx, ry) / rxs;
            if (t < -tolerance || t > 1 + tolerance || u < -tolerance || u > 1 + tolerance) return false;
            x = firstStart.X + Math.Clamp(t, 0, 1) * rx;
            y = firstStart.Y + Math.Clamp(t, 0, 1) * ry;
            return true;
        }
        if (Math.Abs(qpxr) > tolerance) return false;

        var rr = rx * rx + ry * ry;
        var ss = sx * sx + sy * sy;
        if (rr <= tolerance && ss <= tolerance)
        {
            if (Math.Sqrt(qpx * qpx + qpy * qpy) > tolerance) return false;
            x = firstStart.X; y = firstStart.Y; return true;
        }
        if (rr <= tolerance)
        {
            if (!PointOnPlanSegment(firstStart.X, firstStart.Y, secondStart, secondEnd)) return false;
            x = firstStart.X; y = firstStart.Y; return true;
        }
        if (ss <= tolerance)
        {
            if (!PointOnPlanSegment(secondStart.X, secondStart.Y, firstStart, firstEnd)) return false;
            x = secondStart.X; y = secondStart.Y; return true;
        }

        var t0 = (qpx * rx + qpy * ry) / rr;
        var t1 = t0 + (sx * rx + sy * ry) / rr;
        var overlapFrom = Math.Max(0, Math.Min(t0, t1));
        var overlapTo = Math.Min(1, Math.Max(t0, t1));
        if (overlapTo + tolerance < overlapFrom) return false;
        var middle = (overlapFrom + overlapTo) / 2;
        x = firstStart.X + middle * rx;
        y = firstStart.Y + middle * ry;
        return true;
    }

    private static bool PointOnPlanSegment(double x, double y, Point3Mm start, Point3Mm end)
    {
        var cross = Cross2(end.X - start.X, end.Y - start.Y, x - start.X, y - start.Y);
        if (Math.Abs(cross) > 0.000001) return false;
        return x >= Math.Min(start.X, end.X) - 0.000001 && x <= Math.Max(start.X, end.X) + 0.000001 &&
               y >= Math.Min(start.Y, end.Y) - 0.000001 && y <= Math.Max(start.Y, end.Y) + 0.000001;
    }

    private static double ElevationAtPlanPoint(Point3Mm start, Point3Mm end, double x, double y)
    {
        var dx = end.X - start.X;
        var dy = end.Y - start.Y;
        var denominator = dx * dx + dy * dy;
        if (denominator <= 0.0000001) return (start.Z + end.Z) / 2;
        var t = Math.Clamp(((x - start.X) * dx + (y - start.Y) * dy) / denominator, 0, 1);
        return start.Z + t * (end.Z - start.Z);
    }

    private static double SegmentDistance3(Point3Mm firstStart, Point3Mm firstEnd, Point3Mm secondStart, Point3Mm secondEnd)
    {
        var u = new Vector3(firstEnd.X - firstStart.X, firstEnd.Y - firstStart.Y, firstEnd.Z - firstStart.Z);
        var v = new Vector3(secondEnd.X - secondStart.X, secondEnd.Y - secondStart.Y, secondEnd.Z - secondStart.Z);
        var w = new Vector3(firstStart.X - secondStart.X, firstStart.Y - secondStart.Y, firstStart.Z - secondStart.Z);
        var a = Dot(u, u);
        var b = Dot(u, v);
        var c = Dot(v, v);
        var d = Dot(u, w);
        var e = Dot(v, w);
        var denominator = a * c - b * b;
        const double epsilon = 0.0000001;

        double sNumerator, sDenominator = denominator;
        double tNumerator, tDenominator = denominator;
        if (a <= epsilon && c <= epsilon) return Distance3(firstStart, secondStart);
        if (a <= epsilon) return PointToSegmentDistance3(firstStart, secondStart, secondEnd);
        if (c <= epsilon) return PointToSegmentDistance3(secondStart, firstStart, firstEnd);
        if (denominator < epsilon)
        {
            sNumerator = 0;
            sDenominator = 1;
            tNumerator = e;
            tDenominator = c;
        }
        else
        {
            sNumerator = b * e - c * d;
            tNumerator = a * e - b * d;
            if (sNumerator < 0)
            {
                sNumerator = 0;
                tNumerator = e;
                tDenominator = c;
            }
            else if (sNumerator > sDenominator)
            {
                sNumerator = sDenominator;
                tNumerator = e + b;
                tDenominator = c;
            }
        }
        if (tNumerator < 0)
        {
            tNumerator = 0;
            if (-d < 0) sNumerator = 0;
            else if (-d > a) sNumerator = sDenominator;
            else { sNumerator = -d; sDenominator = a; }
        }
        else if (tNumerator > tDenominator)
        {
            tNumerator = tDenominator;
            if (-d + b < 0) sNumerator = 0;
            else if (-d + b > a) sNumerator = sDenominator;
            else { sNumerator = -d + b; sDenominator = a; }
        }
        var sc = Math.Abs(sNumerator) < epsilon ? 0 : sNumerator / sDenominator;
        var tc = Math.Abs(tNumerator) < epsilon ? 0 : tNumerator / tDenominator;
        var difference = new Vector3(w.X + sc * u.X - tc * v.X, w.Y + sc * u.Y - tc * v.Y, w.Z + sc * u.Z - tc * v.Z);
        return difference.Length;
    }

    private static double PointToSegmentDistance3(Point3Mm point, Point3Mm start, Point3Mm end)
    {
        var segment = new Vector3(end.X - start.X, end.Y - start.Y, end.Z - start.Z);
        var lengthSquared = Dot(segment, segment);
        if (lengthSquared <= 0.0000001) return Distance3(point, start);
        var fromStart = new Vector3(point.X - start.X, point.Y - start.Y, point.Z - start.Z);
        var t = Math.Clamp(Dot(fromStart, segment) / lengthSquared, 0, 1);
        return Distance3(point, new Point3Mm(start.X + t * segment.X, start.Y + t * segment.Y, start.Z + t * segment.Z));
    }

    private static double Dot(Vector3 first, Vector3 second) => first.X * second.X + first.Y * second.Y + first.Z * second.Z;
    private static double Cross2(double firstX, double firstY, double secondX, double secondY) => firstX * secondY - firstY * secondX;

    private static int CountSelfIntersections(IReadOnlyList<(PointMm A, PointMm B)> segments)
    {
        var count = 0;
        for (var i = 0; i < segments.Count; i++)
        for (var j = i + 2; j < segments.Count; j++)
        {
            if (i == 0 && j == segments.Count - 1 && Same(segments[i].A, segments[j].B)) continue;
            if (Intersects(segments[i], segments[j])) count++;
        }
        return count;
    }

    private static int CountWallIntersections(IEnumerable<WallSegment> walls, IReadOnlyList<(PointMm A, PointMm B)> segments)
    {
        var count = 0;
        foreach (var segment in segments)
        foreach (var wall in walls)
            if (Intersects(segment, (wall.Start, wall.End))) count++;
        return count;
    }

    private static IReadOnlyList<HeatingBodyWallIntrusionDetail> AnalyzeWallIntrusions(
        IEnumerable<WallSegment> walls,
        IReadOnlyList<IndexedCircuitSegment> segments)
    {
        var details = new List<HeatingBodyWallIntrusionDetail>();
        for (var segmentIndex = 0; segmentIndex < segments.Count; segmentIndex++)
        {
            var segment = segments[segmentIndex];
            foreach (var wall in walls)
            {
                var clearance = SegmentDistance((segment.A, segment.B), (wall.Start, wall.End));
                var required = wall.ThicknessMm / 2d;
                if (clearance > required + 0.001) continue;
                details.Add(new HeatingBodyWallIntrusionDetail
                {
                    HeatingBodySegmentIndex = segmentIndex,
                    CircuitSegmentIndex = segment.CircuitSegmentIndex,
                    WallId = wall.Id,
                    SegmentStart = segment.A.Clone(),
                    SegmentEnd = segment.B.Clone(),
                    CenterlineClearanceMm = clearance,
                    RequiredCenterlineClearanceMm = required,
                });
            }
        }
        return details;
    }

    private static IReadOnlyList<HorizontalTurnWallIntrusionDetail> AnalyzeHorizontalTurnWallIntrusions(
        IEnumerable<WallSegment> walls,
        IReadOnlyList<HorizontalFillet> horizontalFillets,
        IReadOnlySet<int> heatingBodySegmentIndices)
    {
        if (horizontalFillets.Count == 0) return [];
        const double maximumChordErrorMm = 0.01;
        var wallArray = walls.ToArray();
        if (wallArray.Length == 0) return [];
        var details = new List<HorizontalTurnWallIntrusionDetail>();

        foreach (var fillet in horizontalFillets.Where(item => item.LocallyFeasible))
        {
            var sampledArc = SampleHorizontalFillet(fillet, maximumChordErrorMm);
            var arcPoints = sampledArc.Points.Select(point => new PlanPoint(point.X, point.Y)).ToArray();

            foreach (var wall in wallArray)
            {
                var wallStart = new PlanPoint(wall.Start.X, wall.Start.Y);
                var wallEnd = new PlanPoint(wall.End.X, wall.End.Y);
                var polylineClearance = double.PositiveInfinity;
                for (var sample = 0; sample + 1 < arcPoints.Length; sample++)
                    polylineClearance = Math.Min(polylineClearance,
                        PlanSegmentDistance(arcPoints[sample], arcPoints[sample + 1], wallStart, wallEnd));
                var conservativeClearance = Math.Max(0, polylineClearance - sampledArc.MaximumSagittaMm);
                var requiredClearance = wall.ThicknessMm / 2d;
                if (conservativeClearance > requiredClearance + 0.001) continue;

                var bodyTurn = heatingBodySegmentIndices.Contains(fillet.PointIndex - 1) &&
                               heatingBodySegmentIndices.Contains(fillet.PointIndex);
                details.Add(new HorizontalTurnWallIntrusionDetail
                {
                    TurnPointIndex = fillet.PointIndex,
                    TurnRole = bodyTurn ? "BODY" : "TRANSIT",
                    WallId = wall.Id,
                    TurnVertex = fillet.Vertex,
                    ArcStart = fillet.ArcStart,
                    ArcEnd = fillet.ArcEnd,
                    ArcCenter = fillet.ArcCenter,
                    RadiusMm = fillet.RadiusMm,
                    CenterlineClearanceMm = conservativeClearance,
                    RequiredCenterlineClearanceMm = requiredClearance,
                    ClearanceErrorBoundMm = sampledArc.MaximumSagittaMm,
                });
            }
        }
        return details;
    }

    private static double PlanSegmentDistance(PlanPoint firstStart, PlanPoint firstEnd, PlanPoint secondStart, PlanPoint secondEnd)
    {
        if (PlanSegmentsIntersect(firstStart, firstEnd, secondStart, secondEnd)) return 0;
        return new[]
        {
            PlanPointToSegmentDistance(firstStart, secondStart, secondEnd),
            PlanPointToSegmentDistance(firstEnd, secondStart, secondEnd),
            PlanPointToSegmentDistance(secondStart, firstStart, firstEnd),
            PlanPointToSegmentDistance(secondEnd, firstStart, firstEnd),
        }.Min();
    }

    private static double PlanPointToSegmentDistance(PlanPoint point, PlanPoint start, PlanPoint end)
    {
        var dx = end.X - start.X;
        var dy = end.Y - start.Y;
        var lengthSquared = dx * dx + dy * dy;
        if (lengthSquared <= 0.0000001)
            return Math.Sqrt(Math.Pow(point.X - start.X, 2) + Math.Pow(point.Y - start.Y, 2));
        var t = Math.Clamp(((point.X - start.X) * dx + (point.Y - start.Y) * dy) / lengthSquared, 0, 1);
        var nearestX = start.X + t * dx;
        var nearestY = start.Y + t * dy;
        return Math.Sqrt(Math.Pow(point.X - nearestX, 2) + Math.Pow(point.Y - nearestY, 2));
    }

    private static bool PlanSegmentsIntersect(PlanPoint firstStart, PlanPoint firstEnd, PlanPoint secondStart, PlanPoint secondEnd)
    {
        const double epsilon = 0.000001;
        static double Orientation(PlanPoint a, PlanPoint b, PlanPoint c) =>
            (b.X - a.X) * (c.Y - a.Y) - (b.Y - a.Y) * (c.X - a.X);
        static bool Within(PlanPoint a, PlanPoint b, PlanPoint point) =>
            point.X >= Math.Min(a.X, b.X) - epsilon && point.X <= Math.Max(a.X, b.X) + epsilon &&
            point.Y >= Math.Min(a.Y, b.Y) - epsilon && point.Y <= Math.Max(a.Y, b.Y) + epsilon;

        var firstA = Orientation(firstStart, firstEnd, secondStart);
        var firstB = Orientation(firstStart, firstEnd, secondEnd);
        var secondA = Orientation(secondStart, secondEnd, firstStart);
        var secondB = Orientation(secondStart, secondEnd, firstEnd);
        if ((firstA > epsilon && firstB < -epsilon || firstA < -epsilon && firstB > epsilon) &&
            (secondA > epsilon && secondB < -epsilon || secondA < -epsilon && secondB > epsilon)) return true;
        return Math.Abs(firstA) <= epsilon && Within(firstStart, firstEnd, secondStart) ||
               Math.Abs(firstB) <= epsilon && Within(firstStart, firstEnd, secondEnd) ||
               Math.Abs(secondA) <= epsilon && Within(secondStart, secondEnd, firstStart) ||
               Math.Abs(secondB) <= epsilon && Within(secondStart, secondEnd, firstEnd);
    }

    private static IReadOnlyList<ExteriorWallBandCoverageDetail> AnalyzeExteriorWallBands(HomeAuraProject project, ManualCircuit circuit)
    {
        if (!IsHeatingBodyRole(circuit.SystemRole) || string.IsNullOrWhiteSpace(circuit.RoomId)) return [];
        var room = project.Rooms.SingleOrDefault(item => item.Id == circuit.RoomId);
        if (room is null || room.Outline.Count < 3) return [];

        var bodySegments = project.Circuits
            .Where(item => IsHeatingBodyRole(item.SystemRole) && item.RoomId == room.Id)
            .SelectMany(item => HeatingBodySegments(item).Select(segment => (CircuitId: item.Id, segment.A, segment.B)))
            .ToArray();
        if (bodySegments.Length == 0) return [];

        var details = new List<ExteriorWallBandCoverageDetail>();
        foreach (var wall in project.Walls.Where(item => item.WallType == "EXTERIOR" && WallAppliesToFloor(item, room.FloorId)))
        {
            if (!TryGetRoomWallOverlap(room, wall, out var overlapStart, out var overlapEnd)) continue;
            if (!TryGetInteriorNormal(room, wall, overlapStart, overlapEnd, out var normalX, out var normalY)) continue;

            var horizontal = wall.Start.Y == wall.End.Y;
            var requiredFrom = horizontal ? (double)Math.Min(overlapStart.X, overlapEnd.X) : Math.Min(overlapStart.Y, overlapEnd.Y);
            var requiredTo = horizontal ? (double)Math.Max(overlapStart.X, overlapEnd.X) : Math.Max(overlapStart.Y, overlapEnd.Y);
            var lowEndpoint = horizontal
                ? new PointMm((int)requiredFrom, overlapStart.Y)
                : new PointMm(overlapStart.X, (int)requiredFrom);
            var highEndpoint = horizontal
                ? new PointMm((int)requiredTo, overlapStart.Y)
                : new PointMm(overlapStart.X, (int)requiredTo);
            requiredFrom += PerpendicularWallEndTrim(project, wall, lowEndpoint);
            requiredTo -= PerpendicularWallEndTrim(project, wall, highEndpoint);
            if (requiredTo - requiredFrom <= 0) continue;

            var windowIntervals = project.Windows
                .Where(item => item.WallId == wall.Id)
                .Select(item => horizontal
                    ? (From: (double)Math.Max(requiredFrom, Math.Min(item.Start.X, item.End.X)), To: (double)Math.Min(requiredTo, Math.Max(item.Start.X, item.End.X)))
                    : (From: (double)Math.Max(requiredFrom, Math.Min(item.Start.Y, item.End.Y)), To: (double)Math.Min(requiredTo, Math.Max(item.Start.Y, item.End.Y))))
                .Where(interval => interval.To > interval.From)
                .ToArray();
            var mergedWindows = MergeIntervals(windowIntervals);
            var requiredWindowLength = IntervalLength(mergedWindows);

            for (var laneIndex = 1; laneIndex <= project.RoutingRules.MaximumParallelTransitPipesAt100Mm; laneIndex++)
            {
                var offsetFromWallCentre = wall.ThicknessMm / 2d + laneIndex * project.RoutingRules.ExteriorWallSpacingMm;
                var targetCoordinate = horizontal
                    ? wall.Start.Y + normalY * offsetFromWallCentre
                    : wall.Start.X + normalX * offsetFromWallCentre;
                var rawCoverage = new List<(double From, double To, string CircuitId)>();
                foreach (var segment in bodySegments)
                {
                    if (horizontal)
                    {
                        if (segment.A.Y != segment.B.Y || Math.Abs(segment.A.Y - targetCoordinate) > 0.001) continue;
                        var from = Math.Max(requiredFrom, Math.Min(segment.A.X, segment.B.X));
                        var to = Math.Min(requiredTo, Math.Max(segment.A.X, segment.B.X));
                        if (to > from) rawCoverage.Add((from, to, segment.CircuitId));
                    }
                    else
                    {
                        if (segment.A.X != segment.B.X || Math.Abs(segment.A.X - targetCoordinate) > 0.001) continue;
                        var from = Math.Max(requiredFrom, Math.Min(segment.A.Y, segment.B.Y));
                        var to = Math.Min(requiredTo, Math.Max(segment.A.Y, segment.B.Y));
                        if (to > from) rawCoverage.Add((from, to, segment.CircuitId));
                    }
                }

                var mergedCoverage = MergeIntervals(rawCoverage.Select(item => (item.From, item.To)));
                var coveredLength = IntervalLength(mergedCoverage);
                var coveredWindowLength = IntersectionLength(mergedCoverage, mergedWindows);
                var coordinate = (int)Math.Round(targetCoordinate, MidpointRounding.AwayFromZero);
                PointMm ToWorld(double value) => horizontal
                    ? new PointMm((int)Math.Round(value, MidpointRounding.AwayFromZero), coordinate)
                    : new PointMm(coordinate, (int)Math.Round(value, MidpointRounding.AwayFromZero));

                details.Add(new ExteriorWallBandCoverageDetail
                {
                    RoomId = room.Id,
                    WallId = wall.Id,
                    LaneIndex = laneIndex,
                    OffsetFromInteriorFaceMm = laneIndex * project.RoutingRules.ExteriorWallSpacingMm,
                    TargetStart = ToWorld(requiredFrom),
                    TargetEnd = ToWorld(requiredTo),
                    RequiredSpanLengthMm = requiredTo - requiredFrom,
                    CoveredSpanLengthMm = coveredLength,
                    CoveragePercent = 100d * coveredLength / (requiredTo - requiredFrom),
                    WindowRequiredSpanLengthMm = requiredWindowLength,
                    WindowCoveredSpanLengthMm = coveredWindowLength,
                    WindowCoveragePercent = requiredWindowLength <= 0.001 ? 100 : 100d * coveredWindowLength / requiredWindowLength,
                    ContributingCircuitIds = rawCoverage.Select(item => item.CircuitId).Distinct(StringComparer.Ordinal).Order().ToArray(),
                    CoveredIntervals = mergedCoverage.Select(interval => new ExteriorBandCoveredInterval
                    {
                        Start = ToWorld(interval.From),
                        End = ToWorld(interval.To),
                    }).ToArray(),
                });
            }
        }
        return details;
    }

    private static IReadOnlyList<ExteriorWallBandUsefulSpanDetail> AnalyzeExteriorWallUsefulSpans(
        HomeAuraProject project,
        ManualCircuit circuit,
        IReadOnlyList<ExteriorWallBandCoverageDetail> rawDetails)
    {
        if (rawDetails.Count == 0 || !IsHeatingBodyRole(circuit.SystemRole) || string.IsNullOrWhiteSpace(circuit.RoomId))
            return [];
        var room = project.Rooms.SingleOrDefault(item => item.Id == circuit.RoomId);
        if (room is null) return [];

        var result = new List<ExteriorWallBandUsefulSpanDetail>();
        var cornerEnvelope = ExteriorCornerEnvelopeMm(project);
        ExteriorRoomPhysicalGate? roomPhysicalGate = null;
        foreach (var wallGroup in rawDetails.GroupBy(item => item.WallId))
        {
            var wall = project.Walls.SingleOrDefault(item => item.Id == wallGroup.Key);
            if (wall is null || !TryGetRoomWallOverlap(room, wall, out var overlapStart, out var overlapEnd) ||
                !TryGetInteriorNormal(room, wall, overlapStart, overlapEnd, out var normalX, out var normalY))
                continue;
            var horizontal = wall.Start.Y == wall.End.Y;
            var orderedRawDetails = wallGroup.OrderBy(item => item.LaneIndex).ToArray();
            var laneOne = orderedRawDetails.SingleOrDefault(item => item.LaneIndex == 1);
            if (laneOne is null) continue;

            static (double From, double To) AlongWall(ExteriorBandCoveredInterval interval, bool horizontalWall) =>
                horizontalWall
                    ? (Math.Min(interval.Start.X, interval.End.X), Math.Max(interval.Start.X, interval.End.X))
                    : (Math.Min(interval.Start.Y, interval.End.Y), Math.Max(interval.Start.Y, interval.End.Y));
            var rawFrom = horizontal
                ? (double)Math.Min(overlapStart.X, overlapEnd.X)
                : Math.Min(overlapStart.Y, overlapEnd.Y);
            var rawTo = horizontal
                ? (double)Math.Max(overlapStart.X, overlapEnd.X)
                : Math.Max(overlapStart.Y, overlapEnd.Y);
            var lowEndpoint = horizontal
                ? new PointMm((int)rawFrom, overlapStart.Y)
                : new PointMm(overlapStart.X, (int)rawFrom);
            var highEndpoint = horizontal
                ? new PointMm((int)rawTo, overlapStart.Y)
                : new PointMm(overlapStart.X, (int)rawTo);
            rawFrom += PerpendicularWallEndTrim(project, wall, lowEndpoint);
            rawTo -= PerpendicularWallEndTrim(project, wall, highEndpoint);
            var laneOneCoverage = MergeIntervals(laneOne.CoveredIntervals.Select(item => AlongWall(item, horizontal)));
            var territoryIntervals = PartitionExteriorWallSpan(
                project, room, wall, rawFrom, rawTo, normalX, normalY);
            var effectiveCandidates = territoryIntervals
                .Select(item => (From: item.From + cornerEnvelope, To: item.To - cornerEnvelope))
                .Where(item => item.To - item.From > 0.001)
                .ToArray();
            var effectiveRequired = effectiveCandidates
                .Where(item => IntersectionLength([item], laneOneCoverage) > 0.001)
                .ToArray();
            if (effectiveRequired.Length == 0) continue;

            var selectedTerritories = territoryIntervals
                .Where(item => effectiveRequired.Any(required =>
                    Math.Abs(required.From - item.From - cornerEnvelope) <= 0.001 &&
                    Math.Abs(item.To - cornerEnvelope - required.To) <= 0.001))
                .ToArray();
            var windows = MergeIntervals(project.Windows
                .Where(item => item.WallId == wall.Id)
                .Select(item => horizontal
                    ? ((double)Math.Min(item.Start.X, item.End.X), (double)Math.Max(item.Start.X, item.End.X))
                    : ((double)Math.Min(item.Start.Y, item.End.Y), (double)Math.Max(item.Start.Y, item.End.Y))));
            var requiredWindows = IntersectIntervals(windows, effectiveRequired);
            var requiredWindowLength = IntervalLength(requiredWindows);
            IReadOnlyList<IReadOnlyList<(double From, double To)>>? previousLaneCoverage = null;

            foreach (var raw in orderedRawDetails)
            {
                var coordinate = horizontal ? raw.TargetStart.Y : raw.TargetStart.X;
                PointMm ToWorld(double value) => horizontal
                    ? new PointMm((int)Math.Round(value, MidpointRounding.AwayFromZero), coordinate)
                    : new PointMm(coordinate, (int)Math.Round(value, MidpointRounding.AwayFromZero));
                ExteriorBandCoveredInterval ToWorldInterval((double From, double To) interval) => new()
                {
                    Start = ToWorld(interval.From),
                    End = ToWorld(interval.To),
                };

                var rawCoverage = MergeIntervals(raw.CoveredIntervals.Select(item => AlongWall(item, horizontal)));
                var coverageByTerritory = effectiveRequired
                    .Select(required => (IReadOnlyList<(double From, double To)>)MergeIntervals(rawCoverage
                        .Select(covered => (From: Math.Max(required.From, covered.From), To: Math.Min(required.To, covered.To)))))
                    .ToArray();
                var coveredIntervals = coverageByTerritory.SelectMany(item => item).ToArray();
                var coveredLength = IntervalLength(coveredIntervals);
                var effectiveRequiredLength = IntervalLength(effectiveRequired);
                var coveredWindowLength = IntersectionLength(coveredIntervals, requiredWindows);
                var coveragePercent = effectiveRequiredLength <= 0.001 ? 0 : 100d * coveredLength / effectiveRequiredLength;
                var windowCoveragePercent = requiredWindowLength <= 0.001 ? 100 : 100d * coveredWindowLength / requiredWindowLength;
                var contiguous = coverageByTerritory.All(item => item.Count == 1);
                var maximumStartTaper = coverageByTerritory
                    .Select((covered, index) => covered.Count == 0
                        ? effectiveRequired[index].To - effectiveRequired[index].From
                        : Math.Max(0, covered[0].From - effectiveRequired[index].From))
                    .DefaultIfEmpty(0)
                    .Max();
                var maximumEndTaper = coverageByTerritory
                    .Select((covered, index) => covered.Count == 0
                        ? effectiveRequired[index].To - effectiveRequired[index].From
                        : Math.Max(0, effectiveRequired[index].To - covered[^1].To))
                    .DefaultIfEmpty(0)
                    .Max();
                var nestedWithPrevious = previousLaneCoverage is null ||
                    coverageByTerritory.Select((covered, index) => (covered, previous: previousLaneCoverage[index]))
                        .All(pair => pair.covered.Count == 1 && pair.previous.Count == 1 &&
                                     pair.covered[0].From + 0.001 >= pair.previous[0].From &&
                                     pair.covered[^1].To <= pair.previous[^1].To + 0.001);
                var taperAllowance = Math.Max(0, raw.LaneIndex - 1) * 2d * cornerEnvelope;
                var nestedCornerTaperPass = contiguous && nestedWithPrevious &&
                    maximumStartTaper <= taperAllowance + 0.001 &&
                    maximumEndTaper <= taperAllowance + 0.001;
                var staggeredEvaluated = previousLaneCoverage is not null && !nestedWithPrevious;
                var previousLaneStartExtension = 0d;
                var previousLaneEndExtension = 0d;
                var singleEndpointExtension = false;
                var extensionWithinCornerEnvelope = false;
                var alternatingEndpoint = false;
                var oppositeTaperWithinAllowance = false;
                var extensionOutsideRequiredWindow = false;
                var staggeredTurnoutPass = false;
                var staggeredReason = nestedCornerTaperPass
                    ? "NOT_REQUIRED_STRICT_NESTED_CORNER_TAPER"
                    : "NOT_EVALUATED_NO_PREVIOUS_LANE";
                ExteriorRoomPhysicalGate? evaluatedPhysicalGate = null;
                if (staggeredEvaluated)
                {
                    if (effectiveRequired.Length != 1)
                    {
                        staggeredReason = "REJECT_STAGGERED_MULTI_TERRITORY_UNPROVEN";
                    }
                    else if (!contiguous || previousLaneCoverage![0].Count != 1)
                    {
                        staggeredReason = "REJECT_STAGGERED_REQUIRES_CONTIGUOUS_CURRENT_AND_PREVIOUS_LANES";
                    }
                    else
                    {
                        var required = effectiveRequired[0];
                        var current = coverageByTerritory[0][0];
                        var previous = previousLaneCoverage[0][0];
                        previousLaneStartExtension = Math.Max(0, previous.From - current.From);
                        previousLaneEndExtension = Math.Max(0, current.To - previous.To);
                        singleEndpointExtension = previousLaneStartExtension > 0.001 ^ previousLaneEndExtension > 0.001;
                        var extensionLength = Math.Max(previousLaneStartExtension, previousLaneEndExtension);
                        extensionWithinCornerEnvelope = singleEndpointExtension && extensionLength <= cornerEnvelope + 0.001;
                        var previousStartTaper = Math.Max(0, previous.From - required.From);
                        var previousEndTaper = Math.Max(0, required.To - previous.To);
                        var extensionZones = new List<(double From, double To)>();
                        if (previousLaneStartExtension > 0.001)
                        {
                            alternatingEndpoint = previousStartTaper > 0.001 && maximumEndTaper > 0.001;
                            oppositeTaperWithinAllowance = maximumEndTaper > 0.001 &&
                                                            maximumEndTaper <= taperAllowance + 0.001;
                            extensionZones.Add((current.From, previous.From));
                        }
                        if (previousLaneEndExtension > 0.001)
                        {
                            alternatingEndpoint = previousEndTaper > 0.001 && maximumStartTaper > 0.001;
                            oppositeTaperWithinAllowance = maximumStartTaper > 0.001 &&
                                                            maximumStartTaper <= taperAllowance + 0.001;
                            extensionZones.Add((previous.To, current.To));
                        }
                        extensionOutsideRequiredWindow = extensionZones.Count == 1 &&
                                                         IntersectionLength(extensionZones, requiredWindows) <= 0.001;
                        roomPhysicalGate ??= AnalyzeExteriorRoomPhysicalGate(project, room.Id);
                        evaluatedPhysicalGate = roomPhysicalGate;
                        staggeredTurnoutPass = singleEndpointExtension && extensionWithinCornerEnvelope &&
                            alternatingEndpoint && oppositeTaperWithinAllowance && extensionOutsideRequiredWindow &&
                            coveragePercent + 0.000001 >= 90 &&
                            (requiredWindowLength <= 0.001 || windowCoveragePercent + 0.000001 >= 100) &&
                            evaluatedPhysicalGate.Pass;
                        staggeredReason = StaggeredTurnoutReason(
                            singleEndpointExtension,
                            extensionWithinCornerEnvelope,
                            alternatingEndpoint,
                            oppositeTaperWithinAllowance,
                            extensionOutsideRequiredWindow,
                            coveragePercent,
                            requiredWindowLength,
                            windowCoveragePercent,
                            evaluatedPhysicalGate);
                    }
                }

                result.Add(new ExteriorWallBandUsefulSpanDetail
                {
                    RoomId = room.Id,
                    WallId = wall.Id,
                    LaneIndex = raw.LaneIndex,
                    OffsetFromInteriorFaceMm = raw.OffsetFromInteriorFaceMm,
                    Derivation = "WALL_INNER_FACE_PARTITIONS_AND_SNAPPED_R80_ENVELOPE",
                    CornerEnvelopeMm = cornerEnvelope,
                    SelectedTerritoryIntervals = selectedTerritories.Select(ToWorldInterval).ToArray(),
                    EffectiveRequiredIntervals = effectiveRequired.Select(ToWorldInterval).ToArray(),
                    EffectiveRequiredSpanLengthMm = effectiveRequiredLength,
                    CoveredSpanLengthMm = coveredLength,
                    CoveragePercent = coveragePercent,
                    WindowRequiredSpanLengthMm = requiredWindowLength,
                    WindowCoveredSpanLengthMm = coveredWindowLength,
                    WindowCoveragePercent = windowCoveragePercent,
                    ContributingCircuitIds = raw.ContributingCircuitIds,
                    CoveredIntervals = coveredIntervals.Select(ToWorldInterval).ToArray(),
                    MaximumStartTaperMm = maximumStartTaper,
                    MaximumEndTaperMm = maximumEndTaper,
                    NestedCornerTaperAllowanceMm = taperAllowance,
                    ContiguousCoveragePass = contiguous,
                    NestedWithPreviousLanePass = nestedWithPrevious,
                    NestedCornerTaperPass = nestedCornerTaperPass,
                    StaggeredTurnoutEvaluated = staggeredEvaluated,
                    PreviousLaneStartExtensionMm = previousLaneStartExtension,
                    PreviousLaneEndExtensionMm = previousLaneEndExtension,
                    SingleEndpointExtensionPass = singleEndpointExtension,
                    ExtensionWithinCornerEnvelopePass = extensionWithinCornerEnvelope,
                    AlternatingEndpointPass = alternatingEndpoint,
                    OppositeTaperWithinAllowancePass = oppositeTaperWithinAllowance,
                    ExtensionOutsideRequiredWindowPass = extensionOutsideRequiredWindow,
                    AggregateRoomR80Pass = evaluatedPhysicalGate?.R80Pass,
                    AggregateRoomSelfContactPass = evaluatedPhysicalGate?.SelfContactPass,
                    AggregateRoomInterCircuitContactPass = evaluatedPhysicalGate?.InterCircuitContactPass,
                    AggregateRoomBodyWallPass = evaluatedPhysicalGate?.BodyWallPass,
                    AggregateRoomHorizontalTurnWallPass = evaluatedPhysicalGate?.HorizontalTurnWallPass,
                    AggregateRoomDirect100UTurnPass = evaluatedPhysicalGate?.Direct100UTurnPass,
                    AggregateRoomMinimumSegmentLengthMm = evaluatedPhysicalGate?.MinimumSegmentLengthMm,
                    AggregateRoomPhysicalGatePass = evaluatedPhysicalGate?.Pass,
                    StaggeredTurnoutPass = staggeredTurnoutPass,
                    StaggeredTurnoutReason = staggeredReason,
                    UsefulSpanMode = nestedCornerTaperPass
                        ? "STRICT_NESTED_CORNER_TAPER"
                        : staggeredTurnoutPass ? "STAGGERED_ALTERNATING_TURNOUT" : "REJECTED",
                    RawRequiredSpanLengthMm = raw.RequiredSpanLengthMm,
                    RawCoveragePercent = raw.CoveragePercent,
                    RawCoveragePass = raw.CoveragePass,
                });
                previousLaneCoverage = coverageByTerritory;
            }
        }
        return result;
    }

    private static ExteriorOpenSpiralTerminalCornerDetail AnalyzeExteriorOpenSpiralTerminalCorner(
        HomeAuraProject project,
        ManualCircuit circuit,
        IReadOnlyList<ExteriorWallBandCoverageDetail> rawDetails,
        IReadOnlyList<ExteriorWallBandUsefulSpanDetail> usefulDetails)
    {
        var roomId = circuit.RoomId ?? "";
        ExteriorOpenSpiralTerminalCornerDetail Result(
            bool applicable,
            bool pass,
            string reason,
            IReadOnlyList<ExteriorOpenSpiralLaneDetail>? lanes = null,
            string? terminalWallId = null,
            string? terminalSide = null,
            int heatingBodyCircuitCount = 0,
            int heatingBodyRangeCount = 0,
            int exteriorWallCount = 0,
            bool exactlyOneTerminalWallPass = false,
            bool allOtherWallsStrictNestedPass = false,
            bool terminalWallHasNoRequiredWindowPass = false,
            bool terminalWallAdjacentStrictExteriorPass = false,
            bool alignedTerminalSidePass = false,
            bool terminalTaperSequencePass = false,
            bool basicTopologyPass = false,
            bool globalInterCircuitContactPass = false,
            ExteriorRoomPhysicalGate? physicalGate = null) => new()
        {
            RoomId = roomId,
            Applicable = applicable,
            Pass = pass,
            Reason = reason,
            TerminalWallId = terminalWallId,
            TerminalSide = terminalSide,
            HeatingBodyCircuitCount = heatingBodyCircuitCount,
            HeatingBodyRangeCount = heatingBodyRangeCount,
            ExteriorWallCount = exteriorWallCount,
            RequiredLaneCount = project.RoutingRules.MaximumParallelTransitPipesAt100Mm,
            ExactlyOneTerminalWallPass = exactlyOneTerminalWallPass,
            AllOtherWallsStrictNestedPass = allOtherWallsStrictNestedPass,
            TerminalWallHasNoRequiredWindowPass = terminalWallHasNoRequiredWindowPass,
            TerminalWallAdjacentStrictExteriorPass = terminalWallAdjacentStrictExteriorPass,
            AlignedTerminalSidePass = alignedTerminalSidePass,
            TerminalTaperSequencePass = terminalTaperSequencePass,
            BasicTopologyPass = basicTopologyPass,
            GlobalInterCircuitContactPass = globalInterCircuitContactPass,
            AggregateRoomPhysicalGatePass = physicalGate?.Pass == true,
            AggregateRoomDirect100UTurnPass = physicalGate?.Direct100UTurnPass == true,
            AggregateRoomMinimumSegmentLengthPass = physicalGate is not null &&
                                                    physicalGate.MinimumSegmentLengthMm + 0.001 >=
                                                    project.RoutingRules.FieldSpacingMm,
            AggregateRoomMinimumSegmentLengthMm = physicalGate?.MinimumSegmentLengthMm ?? 0,
            Lanes = lanes ?? [],
        };

        if (rawDetails.Count == 0 || !IsHeatingBodyRole(circuit.SystemRole) || string.IsNullOrWhiteSpace(roomId))
            return Result(false, false, "NOT_APPLICABLE_NO_EXTERIOR_HEATING_BODY");

        var expectedExteriorWallIds = rawDetails.Select(item => item.WallId)
            .ToHashSet(StringComparer.Ordinal);

        var roomCircuits = project.Circuits
            .Where(item => IsHeatingBodyRole(item.SystemRole) && item.RoomId == roomId)
            .ToArray();
        var heatingBodyRangeCount = circuit.HeatingBodyRanges.Count > 0
            ? circuit.HeatingBodyRanges.Count
            : circuit.HeatingBodyStartIndex is not null && circuit.HeatingBodyEndIndex is not null ? 1 : 0;
        if (roomCircuits.Length != 1 || roomCircuits[0].Id != circuit.Id)
            return Result(false, false, "NOT_APPLICABLE_REQUIRES_ONE_COHERENT_ROOM_BODY",
                heatingBodyCircuitCount: roomCircuits.Length,
                heatingBodyRangeCount: heatingBodyRangeCount,
                exteriorWallCount: expectedExteriorWallIds.Count);
        if (heatingBodyRangeCount != 1)
            return Result(true, false, "REJECT_OPEN_SPIRAL_REQUIRES_ONE_COHERENT_BODY_RANGE",
                heatingBodyCircuitCount: roomCircuits.Length,
                heatingBodyRangeCount: heatingBodyRangeCount,
                exteriorWallCount: expectedExteriorWallIds.Count);

        var cornerEnvelope = ExteriorCornerEnvelopeMm(project);
        var circuitGeometry = MaterializeGeometry(circuit, project.RoutingRules.MinimumBendRadiusMm);
        var laneDetails = new List<ExteriorOpenSpiralLaneDetail>();
        var wallStates = new List<(string WallId, bool Strict, bool Open, string? Side, bool Sequence, bool NoWindow)>();
        foreach (var wallGroup in usefulDetails.GroupBy(item => item.WallId, StringComparer.Ordinal))
        {
            var wall = project.Walls.SingleOrDefault(item => item.Id == wallGroup.Key);
            if (wall is null) continue;
            var horizontal = wall.Start.Y == wall.End.Y;
            static (double From, double To) AlongWall(ExteriorBandCoveredInterval interval, bool horizontalWall) =>
                horizontalWall
                    ? (Math.Min(interval.Start.X, interval.End.X), Math.Max(interval.Start.X, interval.End.X))
                    : (Math.Min(interval.Start.Y, interval.End.Y), Math.Max(interval.Start.Y, interval.End.Y));
            var windows = MergeIntervals(project.Windows
                .Where(item => item.WallId == wall.Id)
                .Select(item => horizontal
                    ? ((double)Math.Min(item.Start.X, item.End.X), (double)Math.Max(item.Start.X, item.End.X))
                    : ((double)Math.Min(item.Start.Y, item.End.Y), (double)Math.Max(item.Start.Y, item.End.Y))));

            var groupLanes = new List<ExteriorOpenSpiralLaneDetail>();
            foreach (var useful in wallGroup.OrderBy(item => item.LaneIndex))
            {
                var coordinate = horizontal
                    ? useful.SelectedTerritoryIntervals.FirstOrDefault()?.Start.Y ?? wall.Start.Y
                    : useful.SelectedTerritoryIntervals.FirstOrDefault()?.Start.X ?? wall.Start.X;
                PointMm ToWorld(double value) => horizontal
                    ? new PointMm((int)Math.Round(value, MidpointRounding.AwayFromZero), coordinate)
                    : new PointMm(coordinate, (int)Math.Round(value, MidpointRounding.AwayFromZero));
                ExteriorBandCoveredInterval ToWorldInterval((double From, double To) interval) => new()
                {
                    Start = ToWorld(interval.From),
                    End = ToWorld(interval.To),
                };

                var laneEnvelope = useful.LaneIndex * cornerEnvelope;
                var required = useful.SelectedTerritoryIntervals
                    .Select(item => AlongWall(item, horizontal))
                    .Select(item => (From: item.From + laneEnvelope, To: item.To - laneEnvelope))
                    .Where(item => item.To - item.From > 0.001)
                    .ToArray();
                var coveredRaw = MergeIntervals(useful.CoveredIntervals.Select(item => AlongWall(item, horizontal)));
                var coverageByTerritory = required
                    .Select(requiredInterval => (IReadOnlyList<(double From, double To)>)MergeIntervals(coveredRaw
                        .Select(covered => (From: Math.Max(requiredInterval.From, covered.From),
                                            To: Math.Min(requiredInterval.To, covered.To)))))
                    .ToArray();
                var covered = coverageByTerritory.SelectMany(item => item).ToArray();
                var requiredLength = IntervalLength(required);
                var coveredLength = IntervalLength(covered);
                var requiredWindows = IntersectIntervals(windows, required);
                var requiredWindowLength = IntervalLength(requiredWindows);
                var coveredWindowLength = IntersectionLength(covered, requiredWindows);
                var contiguous = required.Length > 0 && coverageByTerritory.All(item => item.Count == 1);
                var startTaper = coverageByTerritory
                    .Select((item, index) => item.Count == 0
                        ? required[index].To - required[index].From
                        : Math.Max(0, item[0].From - required[index].From))
                    .DefaultIfEmpty(double.PositiveInfinity).Max();
                var endTaper = coverageByTerritory
                    .Select((item, index) => item.Count == 0
                        ? required[index].To - required[index].From
                        : Math.Max(0, required[index].To - item[^1].To))
                    .DefaultIfEmpty(double.PositiveInfinity).Max();
                var coveragePercent = requiredLength <= 0.001 ? 0 : 100d * coveredLength / requiredLength;
                var windowCoveragePercent = requiredWindowLength <= 0.001
                    ? 100
                    : 100d * coveredWindowLength / requiredWindowLength;
                var strictNestedPass = contiguous && coveragePercent + 0.000001 >= 100 &&
                                       windowCoveragePercent + 0.000001 >= 100;
                var exactlyOneTaperedSide = startTaper > 0.001 ^ endTaper > 0.001;
                var terminalTaperAllowance = (useful.LaneIndex + 1) * cornerEnvelope;
                var openTerminalPass = required.Length == 1 && contiguous && exactlyOneTaperedSide &&
                                       Math.Max(startTaper, endTaper) <= terminalTaperAllowance + 0.001;
                var detail = new ExteriorOpenSpiralLaneDetail
                {
                    WallId = wall.Id,
                    LaneIndex = useful.LaneIndex,
                    LaneSpecificCornerEnvelopeMm = laneEnvelope,
                    EffectiveRequiredIntervals = required.Select(ToWorldInterval).ToArray(),
                    CoveredIntervals = covered.Select(ToWorldInterval).ToArray(),
                    EffectiveRequiredSpanLengthMm = requiredLength,
                    CoveredSpanLengthMm = coveredLength,
                    CoveragePercent = coveragePercent,
                    WindowRequiredSpanLengthMm = requiredWindowLength,
                    WindowCoveredSpanLengthMm = coveredWindowLength,
                    WindowCoveragePercent = windowCoveragePercent,
                    ContiguousCoveragePass = contiguous,
                    StartTerminalTaperMm = startTaper,
                    EndTerminalTaperMm = endTaper,
                    OpenTerminalTaperAllowanceMm = terminalTaperAllowance,
                    StrictNestedLanePass = strictNestedPass,
                    OpenTerminalLanePass = openTerminalPass,
                };
                groupLanes.Add(detail);
                laneDetails.Add(detail);
            }

            var completeLaneSet = groupLanes.Count == project.RoutingRules.MaximumParallelTransitPipesAt100Mm &&
                                  groupLanes.Select(item => item.LaneIndex)
                                      .SequenceEqual(Enumerable.Range(1, project.RoutingRules.MaximumParallelTransitPipesAt100Mm));
            var strictWall = completeLaneSet && groupLanes.All(item => item.StrictNestedLanePass);
            var openWall = completeLaneSet && groupLanes.All(item => item.OpenTerminalLanePass);
            string? side = null;
            if (openWall)
            {
                var allStart = groupLanes.All(item => item.StartTerminalTaperMm > 0.001 &&
                                                       item.EndTerminalTaperMm <= 0.001);
                var allEnd = groupLanes.All(item => item.EndTerminalTaperMm > 0.001 &&
                                                     item.StartTerminalTaperMm <= 0.001);
                side = allStart ? "START" : allEnd ? "END" : null;
                openWall &= side is not null;
            }
            var orderedTapers = groupLanes.OrderBy(item => item.LaneIndex)
                .Select(item => Math.Max(item.StartTerminalTaperMm, item.EndTerminalTaperMm)).ToArray();
            var groupTerminalSequence = openWall && orderedTapers.Length > 0 &&
                                        orderedTapers[0] + 0.001 >= cornerEnvelope &&
                                        orderedTapers[0] <= 2 * cornerEnvelope + 0.001 &&
                                        orderedTapers.Skip(1).Select((value, index) =>
                                            Math.Abs(value - orderedTapers[index] - cornerEnvelope) <= 0.001).All(item => item);
            wallStates.Add((wall.Id, strictWall, openWall, side, groupTerminalSequence,
                groupLanes.All(item => item.WindowRequiredSpanLengthMm <= 0.001)));
        }

        var physicalGate = AnalyzeExteriorRoomPhysicalGate(project, roomId);
        var globalInterClearance = AnalyzeInterCircuitClearance(project, circuit, circuitGeometry.Segments);
        var globalInterCircuitContactPass = globalInterClearance.PlanContactCount == 0 &&
                                            globalInterClearance.SurfaceViolationCount == 0;
        var basicTopologyPass = circuit.Completed && circuit.OrderedPoints.Count >= 2 &&
                                circuit.OrderedPoints.All(point => point.X % project.GridSpacingMm == 0 &&
                                                                  point.Y % project.GridSpacingMm == 0) &&
                                Segments(circuit.OrderedPoints).All(segment =>
                                    segment.A.X == segment.B.X ^ segment.A.Y == segment.B.Y);
        var terminalWalls = wallStates.Where(item => item.Open).ToArray();
        var exactlyOneTerminalWall = terminalWalls.Length == 1;
        var terminalWall = exactlyOneTerminalWall ? terminalWalls[0] : default;
        var allOtherWallsStrict = exactlyOneTerminalWall && wallStates
            .Where(item => item.WallId != terminalWall.WallId)
            .All(item => item.Strict);
        var noRequiredWindow = exactlyOneTerminalWall && terminalWall.NoWindow;
        var terminalWallAdjacentStrictExterior = false;
        if (exactlyOneTerminalWall)
        {
            var terminalWallGeometry = project.Walls.Single(item => item.Id == terminalWall.WallId);
            static bool SamePoint(PointMm first, PointMm second) => first.X == second.X && first.Y == second.Y;
            static PointMm EndpointForSide(WallSegment wall, string side)
            {
                if (wall.Start.Y == wall.End.Y)
                {
                    var start = wall.Start.X <= wall.End.X ? wall.Start : wall.End;
                    var end = wall.Start.X <= wall.End.X ? wall.End : wall.Start;
                    return side == "START" ? start : end;
                }

                var verticalStart = wall.Start.Y <= wall.End.Y ? wall.Start : wall.End;
                var verticalEnd = wall.Start.Y <= wall.End.Y ? wall.End : wall.Start;
                return side == "START" ? verticalStart : verticalEnd;
            }

            var terminalEndpoint = EndpointForSide(terminalWallGeometry, terminalWall.Side!);
            terminalWallAdjacentStrictExterior = wallStates.Where(item => item.Strict && item.WallId != terminalWall.WallId)
                .Select(item => project.Walls.Single(wall => wall.Id == item.WallId))
                .Any(wall => AxisWallsPerpendicular(terminalWallGeometry, wall) &&
                             (SamePoint(terminalEndpoint, wall.Start) || SamePoint(terminalEndpoint, wall.End)));
        }
        var alignedSide = exactlyOneTerminalWall && terminalWall.Side is not null;
        var terminalSequence = exactlyOneTerminalWall && terminalWall.Sequence;
        var observedWallIds = wallStates.Select(item => item.WallId).ToHashSet(StringComparer.Ordinal);
        var completeWallLaneSets = expectedExteriorWallIds.Count > 0 &&
            expectedExteriorWallIds.SetEquals(observedWallIds) &&
            wallStates.Count * project.RoutingRules.MaximumParallelTransitPipesAt100Mm == laneDetails.Count;
        var minimumSegmentLengthPass = physicalGate.MinimumSegmentLengthMm + 0.001 >=
                                       project.RoutingRules.FieldSpacingMm;
        var pass = completeWallLaneSets && exactlyOneTerminalWall && allOtherWallsStrict && noRequiredWindow &&
                   terminalWallAdjacentStrictExterior && alignedSide && terminalSequence &&
                   basicTopologyPass && globalInterCircuitContactPass &&
                   minimumSegmentLengthPass && physicalGate.Pass;
        string reason;
        if (pass) reason = "PASS_OPEN_SPIRAL_TERMINAL_CORNER_ON_WINDOWLESS_WALL";
        else if (!completeWallLaneSets) reason = "REJECT_OPEN_SPIRAL_INCOMPLETE_EXTERIOR_LANE_SET";
        else if (!exactlyOneTerminalWall) reason = "REJECT_OPEN_SPIRAL_REQUIRES_EXACTLY_ONE_TERMINAL_WALL";
        else if (!allOtherWallsStrict) reason = "REJECT_OPEN_SPIRAL_NON_TERMINAL_WALL_NOT_STRICT_NESTED";
        else if (!noRequiredWindow) reason = "REJECT_OPEN_SPIRAL_TERMINAL_WALL_HAS_REQUIRED_WINDOW";
        else if (!terminalWallAdjacentStrictExterior)
            reason = "REJECT_OPEN_SPIRAL_TERMINAL_WALL_HAS_NO_ADJACENT_STRICT_EXTERIOR";
        else if (!alignedSide) reason = "REJECT_OPEN_SPIRAL_TERMINAL_TAPERS_NOT_ALIGNED";
        else if (!terminalSequence) reason = "REJECT_OPEN_SPIRAL_TERMINAL_TAPER_SEQUENCE";
        else if (!basicTopologyPass) reason = "REJECT_OPEN_SPIRAL_BASIC_TOPOLOGY_GATE";
        else if (!globalInterCircuitContactPass) reason = "REJECT_OPEN_SPIRAL_GLOBAL_INTER_CIRCUIT_CONTACT";
        else if (!physicalGate.Direct100UTurnPass) reason = "REJECT_OPEN_SPIRAL_DIRECT_100MM_U_TURN";
        else if (!minimumSegmentLengthPass) reason = "REJECT_OPEN_SPIRAL_MINIMUM_SEGMENT_LENGTH";
        else if (!physicalGate.R80Pass) reason = "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_R80_GATE";
        else if (!physicalGate.SelfContactPass) reason = "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_SELF_CONTACT";
        else if (!physicalGate.InterCircuitContactPass)
            reason = "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_INTER_CIRCUIT_CONTACT";
        else if (!physicalGate.BodyWallPass) reason = "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_BODY_WALL_GATE";
        else reason = "REJECT_OPEN_SPIRAL_AGGREGATE_ROOM_TURN_WALL_GATE";
        return Result(
            true,
            pass,
            reason,
            laneDetails,
            exactlyOneTerminalWall ? terminalWall.WallId : null,
            exactlyOneTerminalWall ? terminalWall.Side : null,
            roomCircuits.Length,
            heatingBodyRangeCount,
            expectedExteriorWallIds.Count,
            exactlyOneTerminalWall,
            allOtherWallsStrict,
            noRequiredWindow,
            terminalWallAdjacentStrictExterior,
            alignedSide,
            terminalSequence,
            basicTopologyPass,
            globalInterCircuitContactPass,
            physicalGate);
    }

    private static ExteriorOpenSpiralMaterializedTerminalRampDetail
        AnalyzeExteriorOpenSpiralMaterializedTerminalRamp(
            HomeAuraProject project,
            ManualCircuit circuit,
            ExteriorOpenSpiralTerminalCornerDetail baseOpen)
    {
        var roomId = circuit.RoomId ?? "";
        ExteriorOpenSpiralMaterializedTerminalRampDetail Result(
            bool applicable,
            bool pass,
            string reason,
            HeatingBodyRange? bodyRange = null,
            string? bodyEndpointSide = null,
            int? circuitSegmentIndex = null,
            string? transitionKind = null,
            bool transitionMaterializedPass = false,
            string? wallId = null,
            int? laneIndex = null,
            ExteriorBandCoveredInterval? missingInterval = null,
            ExteriorBandCoveredInterval? rampProjectedInterval = null,
            double missingLengthMm = 0,
            double rampProjectedLengthMm = 0,
            bool adjacentBodyEndpointPass = false,
            bool sameHeadingContinuationPass = false,
            bool exactGapMatchPass = false,
            bool windowlessGapPass = false,
            bool noTerminalWallOrOtherLaneContributionPass = false,
            bool deficientWallSharesOpenCornerPass = false,
            bool gapAtSharedOpenCornerPass = false,
            bool assignedRoomWallClearPass = false,
            bool fullCircuitPhysicalGatePass = false,
            bool nativeCollectorTerminalTolerancePass = false,
            bool globalInterCircuitContactPass = false,
            int completionCandidateCount = 0,
            double augmentedCoveragePercent = 0,
            double augmentedWindowCoveragePercent = 0,
            bool augmentedStrictLanePass = false,
            bool augmentedAllNonTerminalWallsStrictPass = false,
            bool augmentedOpenCornerAdjacencyPass = false,
            string? openTerminalWallId = null,
            string? openTerminalSide = null) => new()
        {
            RoomId = roomId,
            Applicable = applicable,
            Pass = pass,
            Reason = reason,
            BodyRangeStartIndex = bodyRange?.StartIndex ?? 0,
            BodyRangeEndIndex = bodyRange?.EndIndex ?? 0,
            BodyEndpointSide = bodyEndpointSide,
            CircuitSegmentIndex = circuitSegmentIndex,
            TransitionKind = transitionKind,
            TransitionMaterializedPass = transitionMaterializedPass,
            WallId = wallId,
            LaneIndex = laneIndex,
            MissingInterval = missingInterval,
            RampProjectedInterval = rampProjectedInterval,
            MissingLengthMm = missingLengthMm,
            RampProjectedLengthMm = rampProjectedLengthMm,
            AdjacentBodyEndpointPass = adjacentBodyEndpointPass,
            SameHeadingContinuationPass = sameHeadingContinuationPass,
            ExactGapMatchPass = exactGapMatchPass,
            WindowlessGapPass = windowlessGapPass,
            NoTerminalWallOrOtherLaneContributionPass = noTerminalWallOrOtherLaneContributionPass,
            DeficientWallSharesOpenCornerPass = deficientWallSharesOpenCornerPass,
            GapAtSharedOpenCornerPass = gapAtSharedOpenCornerPass,
            AssignedRoomWallClearPass = assignedRoomWallClearPass,
            FullCircuitPhysicalGatePass = fullCircuitPhysicalGatePass,
            NativeCollectorTerminalTolerancePass = nativeCollectorTerminalTolerancePass,
            GlobalInterCircuitContactPass = globalInterCircuitContactPass,
            CompletionCandidateCount = completionCandidateCount,
            AugmentedCoveragePercent = augmentedCoveragePercent,
            AugmentedWindowCoveragePercent = augmentedWindowCoveragePercent,
            AugmentedStrictLanePass = augmentedStrictLanePass,
            AugmentedAllNonTerminalWallsStrictPass = augmentedAllNonTerminalWallsStrictPass,
            AugmentedOpenCornerAdjacencyPass = augmentedOpenCornerAdjacencyPass,
            OpenTerminalWallId = openTerminalWallId,
            OpenTerminalSide = openTerminalSide,
        };

        if (!baseOpen.Applicable || !IsHeatingBodyRole(circuit.SystemRole) || string.IsNullOrWhiteSpace(roomId))
            return Result(false, false, "NOT_APPLICABLE_NO_OPEN_SPIRAL_EVIDENCE");
        if (baseOpen.Pass)
            return Result(false, false, "NOT_APPLICABLE_BASE_OPEN_SPIRAL_ALREADY_PASSES");
        if (baseOpen.Reason != "REJECT_OPEN_SPIRAL_NON_TERMINAL_WALL_NOT_STRICT_NESTED")
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_BASE_FAILURE_NOT_ELIGIBLE");

        var bodyRanges = GetHeatingBodyRanges(circuit);
        if (bodyRanges.Count != 1)
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_ONE_BODY_RANGE");
        var bodyRange = bodyRanges[0];
        var room = project.Rooms.SingleOrDefault(item => item.Id == roomId);
        if (room is null)
            return Result(false, false, "NOT_APPLICABLE_ASSIGNED_ROOM_MISSING", bodyRange);

        var laneGroups = baseOpen.Lanes.GroupBy(item => item.WallId, StringComparer.Ordinal).ToArray();
        var openGroups = laneGroups.Where(group =>
                group.Count() == project.RoutingRules.MaximumParallelTransitPipesAt100Mm &&
                group.All(item => item.OpenTerminalLanePass))
            .ToArray();
        if (openGroups.Length != 1 || !baseOpen.ExactlyOneTerminalWallPass ||
            !baseOpen.TerminalWallHasNoRequiredWindowPass || !baseOpen.AlignedTerminalSidePass ||
            !baseOpen.TerminalTaperSequencePass || !baseOpen.BasicTopologyPass)
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_ONE_VALID_OPEN_WALL",
                bodyRange, openTerminalWallId: baseOpen.TerminalWallId, openTerminalSide: baseOpen.TerminalSide);

        var openWallId = openGroups[0].Key;
        var nonTerminalLanes = baseOpen.Lanes.Where(item => item.WallId != openWallId).ToArray();
        var failedLanes = nonTerminalLanes.Where(item => !item.StrictNestedLanePass).ToArray();
        if (failedLanes.Length != 1 || nonTerminalLanes.Count(item => item.StrictNestedLanePass) + 1 != nonTerminalLanes.Length)
            return Result(true, false,
                "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_EXACTLY_ONE_NONTERMINAL_LANE_GAP",
                bodyRange, openTerminalWallId: openWallId, openTerminalSide: baseOpen.TerminalSide);

        var failedLane = failedLanes[0];
        var wall = project.Walls.Single(item => item.Id == failedLane.WallId);
        var horizontal = wall.Start.Y == wall.End.Y;
        static (double From, double To) AlongWall(ExteriorBandCoveredInterval interval, bool horizontalWall) =>
            horizontalWall
                ? (Math.Min(interval.Start.X, interval.End.X), Math.Max(interval.Start.X, interval.End.X))
                : (Math.Min(interval.Start.Y, interval.End.Y), Math.Max(interval.Start.Y, interval.End.Y));
        var required = failedLane.EffectiveRequiredIntervals.Select(item => AlongWall(item, horizontal)).ToArray();
        var covered = failedLane.CoveredIntervals.Select(item => AlongWall(item, horizontal)).ToArray();
        if (required.Length != 1 || covered.Length != 1)
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_ONE_CONTIGUOUS_GAP",
                bodyRange, wallId: failedLane.WallId, laneIndex: failedLane.LaneIndex,
                openTerminalWallId: openWallId, openTerminalSide: baseOpen.TerminalSide);

        var startMissing = covered[0].From - required[0].From > 0.001;
        var endMissing = required[0].To - covered[0].To > 0.001;
        if (!(startMissing ^ endMissing))
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_MUST_BE_ONE_ENDPOINT",
                bodyRange, wallId: failedLane.WallId, laneIndex: failedLane.LaneIndex,
                openTerminalWallId: openWallId, openTerminalSide: baseOpen.TerminalSide);

        var missing = startMissing
            ? (From: required[0].From, To: covered[0].From)
            : (From: covered[0].To, To: required[0].To);
        var missingLength = missing.To - missing.From;
        var coordinate = horizontal
            ? failedLane.EffectiveRequiredIntervals[0].Start.Y
            : failedLane.EffectiveRequiredIntervals[0].Start.X;
        PointMm ToWorld(double value) => horizontal
            ? new PointMm((int)Math.Round(value, MidpointRounding.AwayFromZero), coordinate)
            : new PointMm(coordinate, (int)Math.Round(value, MidpointRounding.AwayFromZero));
        ExteriorBandCoveredInterval ToWorldInterval((double From, double To) interval) => new()
        {
            Start = ToWorld(interval.From),
            End = ToWorld(interval.To),
        };
        var missingWorld = ToWorldInterval(missing);
        var windowlessGap = failedLane.WindowRequiredSpanLengthMm <= 0.001 &&
                            !project.Windows.Any(item => item.WallId == failedLane.WallId) &&
                            failedLane.WindowCoveragePercent + 0.000001 >= 100;
        if (Math.Abs(missingLength - project.RoutingRules.FieldSpacingMm) > 0.001)
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_NOT_EXACT_FIELD_SPACING",
                bodyRange, wallId: failedLane.WallId, laneIndex: failedLane.LaneIndex,
                missingInterval: missingWorld, missingLengthMm: missingLength,
                windowlessGapPass: windowlessGap,
                openTerminalWallId: openWallId, openTerminalSide: baseOpen.TerminalSide);
        if (!windowlessGap)
            return Result(true, false, "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_OVERLAPS_REQUIRED_WINDOW",
                bodyRange, wallId: failedLane.WallId, laneIndex: failedLane.LaneIndex,
                missingInterval: missingWorld, missingLengthMm: missingLength,
                openTerminalWallId: openWallId, openTerminalSide: baseOpen.TerminalSide);

        var geometry = MaterializeGeometry(circuit, project.RoutingRules.MinimumBendRadiusMm);
        var adjacentIndices = new[] { bodyRange.StartIndex - 1, bodyRange.EndIndex }
            .Where(index => index >= 0 && index + 1 < circuit.OrderedPoints.Count)
            .ToArray();
        var candidates = new List<(int SegmentIndex, string EndpointSide, bool AdjacentEndpoint,
            bool SameHeading, bool ExactGap, string? TransitionKind, bool TransitionMaterialized,
            bool RoomWallClear, ExteriorBandCoveredInterval ProjectedInterval, double ProjectedLength)>();
        foreach (var segmentIndex in adjacentIndices)
        {
            var first = circuit.OrderedPoints[segmentIndex];
            var second = circuit.OrderedPoints[segmentIndex + 1];
            var onLane = horizontal
                ? first.Y == coordinate && second.Y == coordinate
                : first.X == coordinate && second.X == coordinate;
            if (!onLane) continue;
            var projected = horizontal
                ? (From: (double)Math.Min(first.X, second.X), To: Math.Max(first.X, second.X))
                : (From: (double)Math.Min(first.Y, second.Y), To: Math.Max(first.Y, second.Y));
            var exactGap = Math.Abs(projected.From - missing.From) <= 0.001 &&
                           Math.Abs(projected.To - missing.To) <= 0.001;
            if (!exactGap) continue;

            var endpointSide = segmentIndex == bodyRange.StartIndex - 1 ? "START" : "END";
            var bodyPointIndex = endpointSide == "START" ? bodyRange.StartIndex : bodyRange.EndIndex;
            var bodyPoint = circuit.OrderedPoints[bodyPointIndex];
            var adjacentEndpoint = endpointSide == "START"
                ? first.X == bodyPoint.X && first.Y == bodyPoint.Y && first.Z == bodyPoint.Z ||
                  second.X == bodyPoint.X && second.Y == bodyPoint.Y && second.Z == bodyPoint.Z
                : first.X == bodyPoint.X && first.Y == bodyPoint.Y && first.Z == bodyPoint.Z ||
                  second.X == bodyPoint.X && second.Y == bodyPoint.Y && second.Z == bodyPoint.Z;
            var bodyDirection = endpointSide == "START"
                ? (X: circuit.OrderedPoints[bodyRange.StartIndex + 1].X - bodyPoint.X,
                   Y: circuit.OrderedPoints[bodyRange.StartIndex + 1].Y - bodyPoint.Y)
                : (X: bodyPoint.X - circuit.OrderedPoints[bodyRange.EndIndex - 1].X,
                   Y: bodyPoint.Y - circuit.OrderedPoints[bodyRange.EndIndex - 1].Y);
            var rampDirection = endpointSide == "START"
                ? (X: bodyPoint.X - first.X, Y: bodyPoint.Y - first.Y)
                : (X: second.X - bodyPoint.X, Y: second.Y - bodyPoint.Y);
            var sameHeading = bodyDirection.X * rampDirection.Y - bodyDirection.Y * rampDirection.X == 0 &&
                              bodyDirection.X * rampDirection.X + bodyDirection.Y * rampDirection.Y > 0;
            var transitionRecords = circuit.VerticalTransitions
                .Where(item => item.SegmentIndex == segmentIndex).ToArray();
            var transitionAnalysis = geometry.Transitions
                .SingleOrDefault(item => item.CircuitSegmentIndex == segmentIndex);
            var transitionKind = transitionRecords.Length == 1 ? transitionRecords[0].Kind : null;
            var bodyPoint3 = ResolvePoint(circuit, bodyPoint);
            var otherPoint = endpointSide == "START" ? ResolvePoint(circuit, first) : ResolvePoint(circuit, second);
            var transitionMaterialized = transitionRecords.Length == 1 && transitionAnalysis?.MaterializedPass == true &&
                transitionRecords[0].Kind.Equals("S_BEND_R80", StringComparison.OrdinalIgnoreCase) &&
                Math.Abs(bodyPoint3.Z - (circuit.AxisElevationMm ?? bodyPoint3.Z)) <= 0.001 &&
                Math.Abs(otherPoint.Z - bodyPoint3.Z) > 0.001;
            var indexed = new IndexedCircuitSegment(segmentIndex, first, second);
            var roomWallClear = HeatingBodyInsideAssignedRoom(project, circuit, [first, second], [indexed]) &&
                                AnalyzeWallIntrusions(WallsForCircuit(project, circuit), [indexed]).Count == 0;
            candidates.Add((segmentIndex, endpointSide, adjacentEndpoint, sameHeading, exactGap,
                transitionKind, transitionMaterialized, roomWallClear, ToWorldInterval(projected),
                projected.To - projected.From));
        }

        var candidate = candidates.Count == 1 ? candidates[0] : default;
        var adjacentBodyEndpointPass = candidates.Count == 1 && candidate.AdjacentEndpoint;
        var sameHeadingContinuationPass = candidates.Count == 1 && candidate.SameHeading;
        var exactGapMatchPass = candidates.Count == 1 && candidate.ExactGap;
        var transitionMaterializedPass = candidates.Count == 1 && candidate.TransitionMaterialized;
        var assignedRoomWallClearPass = candidates.Count == 1 && candidate.RoomWallClear;
        var augmentedCoverage = 100d * (failedLane.CoveredSpanLengthMm + missingLength) /
                                failedLane.EffectiveRequiredSpanLengthMm;
        var augmentedWindowCoverage = failedLane.WindowCoveragePercent;
        var augmentedStrictLanePass = Math.Abs(augmentedCoverage - 100) <= 0.000001 &&
                                      augmentedWindowCoverage + 0.000001 >= 100;

        var physicalGate = AnalyzeExteriorRoomPhysicalGate(project, roomId);
        var globalInter = AnalyzeInterCircuitClearance(project, circuit, geometry.Segments);
        var globalInterPass = globalInter.PlanContactCount == 0 && globalInter.SurfaceViolationCount == 0;
        var bend = AnalyzeBends(circuit, geometry.Transitions, project.RoutingRules.MinimumBendRadiusMm);
        var roundedLength = geometry.AxisLengthMm - bend.RoundedLengthCorrectionMm +
                            circuit.ConcealedServiceLengthMm + circuit.OutOfPlaneLengthMm;
        var lengthPass = circuit.SystemRole != "FLOOR_HEATING_LOOP" ||
                         roundedLength is >= 40_000 and <= 80_000;
        var collectorTerminalPass = circuit.SystemRole != "FLOOR_HEATING_LOOP" ||
            circuit.OrderedPoints.Count > 0 &&
            NearAssignedConnection(project, circuit, circuit.OrderedPoints[0], circuit.SupplyPortIndex) &&
            NearAssignedConnection(project, circuit, circuit.OrderedPoints[^1], circuit.ReturnPortIndex);
        var fullCircuitPhysicalPass = baseOpen.BasicTopologyPass && physicalGate.Pass &&
            physicalGate.MinimumSegmentLengthMm + 0.001 >= project.RoutingRules.FieldSpacingMm &&
            lengthPass;

        static bool SamePoint(PointMm first, PointMm second) => first.X == second.X && first.Y == second.Y;
        static PointMm EndpointForSide(WallSegment selectedWall, string side)
        {
            if (selectedWall.Start.Y == selectedWall.End.Y)
            {
                var start = selectedWall.Start.X <= selectedWall.End.X ? selectedWall.Start : selectedWall.End;
                var end = selectedWall.Start.X <= selectedWall.End.X ? selectedWall.End : selectedWall.Start;
                return side == "START" ? start : end;
            }
            var verticalStart = selectedWall.Start.Y <= selectedWall.End.Y ? selectedWall.Start : selectedWall.End;
            var verticalEnd = selectedWall.Start.Y <= selectedWall.End.Y ? selectedWall.End : selectedWall.Start;
            return side == "START" ? verticalStart : verticalEnd;
        }
        var augmentedStrictWallIds = laneGroups
            .Where(group => group.Key != openWallId && group.All(item =>
                item.StrictNestedLanePass || item.WallId == failedLane.WallId &&
                item.LaneIndex == failedLane.LaneIndex && augmentedStrictLanePass))
            .Select(group => group.Key).ToHashSet(StringComparer.Ordinal);
        var allNonTerminalWallsStrict = laneGroups.Where(group => group.Key != openWallId)
            .All(group => augmentedStrictWallIds.Contains(group.Key));
        var openWall = project.Walls.Single(item => item.Id == openWallId);
        var openEndpoint = EndpointForSide(openWall, baseOpen.TerminalSide!);
        var failedWall = project.Walls.Single(item => item.Id == failedLane.WallId);
        var failedWallStart = EndpointForSide(failedWall, "START");
        var failedWallEnd = EndpointForSide(failedWall, "END");
        var sharedFailedWallSide = AxisWallsPerpendicular(openWall, failedWall)
            ? SamePoint(openEndpoint, failedWallStart)
                ? "START"
                : SamePoint(openEndpoint, failedWallEnd) ? "END" : null
            : null;
        var deficientWallSharesOpenCorner = sharedFailedWallSide is not null;
        var gapAtSharedOpenCorner = sharedFailedWallSide is not null &&
            (startMissing && sharedFailedWallSide == "START" || endMissing && sharedFailedWallSide == "END");
        static bool PositiveCollinearOverlap(
            ExteriorBandCoveredInterval first,
            ExteriorBandCoveredInterval second)
        {
            var firstHorizontal = first.Start.Y == first.End.Y;
            var secondHorizontal = second.Start.Y == second.End.Y;
            if (firstHorizontal != secondHorizontal) return false;
            if (firstHorizontal)
            {
                if (first.Start.Y != second.Start.Y) return false;
                var from = Math.Max(Math.Min(first.Start.X, first.End.X), Math.Min(second.Start.X, second.End.X));
                var to = Math.Min(Math.Max(first.Start.X, first.End.X), Math.Max(second.Start.X, second.End.X));
                return to - from > 0.001;
            }
            if (first.Start.X != second.Start.X) return false;
            var verticalFrom = Math.Max(Math.Min(first.Start.Y, first.End.Y), Math.Min(second.Start.Y, second.End.Y));
            var verticalTo = Math.Min(Math.Max(first.Start.Y, first.End.Y), Math.Max(second.Start.Y, second.End.Y));
            return verticalTo - verticalFrom > 0.001;
        }
        var noOtherLaneOverlap = candidates.Count == 1 && !baseOpen.Lanes
            .Where(item => item.WallId != failedLane.WallId || item.LaneIndex != failedLane.LaneIndex)
            .SelectMany(item => item.EffectiveRequiredIntervals)
            .Any(interval => PositiveCollinearOverlap(candidate.ProjectedInterval, interval));
        var noTerminalWallOrOtherLaneContribution = candidates.Count == 1 &&
            failedLane.WallId != openWallId && noOtherLaneOverlap;
        var augmentedOpenAdjacencyPass = augmentedStrictWallIds
            .Select(id => project.Walls.Single(item => item.Id == id))
            .Any(strictWall => AxisWallsPerpendicular(openWall, strictWall) &&
                               (SamePoint(openEndpoint, strictWall.Start) || SamePoint(openEndpoint, strictWall.End)));

        var pass = candidates.Count == 1 && adjacentBodyEndpointPass && sameHeadingContinuationPass &&
                   exactGapMatchPass && transitionMaterializedPass && assignedRoomWallClearPass &&
                   noTerminalWallOrOtherLaneContribution && deficientWallSharesOpenCorner &&
                   gapAtSharedOpenCorner &&
                   augmentedStrictLanePass && allNonTerminalWallsStrict && augmentedOpenAdjacencyPass &&
                   fullCircuitPhysicalPass && collectorTerminalPass && globalInterPass;
        string reason;
        if (pass) reason = "PASS_MATERIALIZED_TERMINAL_RAMP_COMPLETES_EXTERIOR_LANE";
        else if (candidates.Count != 1)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_REQUIRES_EXACTLY_ONE_ADJACENT_CANDIDATE";
        else if (!adjacentBodyEndpointPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_NOT_ADJACENT_TO_BODY_ENDPOINT";
        else if (!sameHeadingContinuationPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_NOT_SAME_HEADING_CONTINUATION";
        else if (!exactGapMatchPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_NOT_EXACT_GAP_MATCH";
        else if (!transitionMaterializedPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_S_BEND_NOT_MATERIALIZED";
        else if (!noTerminalWallOrOtherLaneContribution)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_TERMINAL_WALL_OR_OTHER_LANE_CONTRIBUTION";
        else if (!deficientWallSharesOpenCorner)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_DEFICIENT_WALL_NOT_AT_OPEN_CORNER";
        else if (!gapAtSharedOpenCorner)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_GAP_NOT_AT_SHARED_OPEN_CORNER";
        else if (!assignedRoomWallClearPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_NOT_ROOM_AND_WALL_CLEAR";
        else if (!augmentedStrictLanePass || !allNonTerminalWallsStrict)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_AUGMENTED_EXTERIOR_NOT_STRICT";
        else if (!augmentedOpenAdjacencyPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_OPEN_CORNER_NOT_ADJACENT_AFTER_COMPLETION";
        else if (!globalInterPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_GLOBAL_INTER_CIRCUIT_CONTACT";
        else if (!fullCircuitPhysicalPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_FULL_CIRCUIT_PHYSICAL_GATE";
        else if (!collectorTerminalPass)
            reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_NATIVE_TERMINAL_TOLERANCE";
        else reason = "REJECT_MATERIALIZED_TERMINAL_RAMP_UNKNOWN";

        return Result(true, pass, reason, bodyRange,
            candidates.Count == 1 ? candidate.EndpointSide : null,
            candidates.Count == 1 ? candidate.SegmentIndex : null,
            candidates.Count == 1 ? candidate.TransitionKind : null,
            transitionMaterializedPass,
            failedLane.WallId,
            failedLane.LaneIndex,
            missingWorld,
            candidates.Count == 1 ? candidate.ProjectedInterval : null,
            missingLength,
            candidates.Count == 1 ? candidate.ProjectedLength : 0,
            adjacentBodyEndpointPass,
            sameHeadingContinuationPass,
            exactGapMatchPass,
            windowlessGap,
            noTerminalWallOrOtherLaneContribution,
            deficientWallSharesOpenCorner,
            gapAtSharedOpenCorner,
            assignedRoomWallClearPass,
            fullCircuitPhysicalPass,
            collectorTerminalPass,
            globalInterPass,
            candidates.Count,
            augmentedCoverage,
            augmentedWindowCoverage,
            augmentedStrictLanePass,
            allNonTerminalWallsStrict,
            augmentedOpenAdjacencyPass,
            openWallId,
            baseOpen.TerminalSide);
    }

    private static string StaggeredTurnoutReason(
        bool singleEndpointExtension,
        bool extensionWithinCornerEnvelope,
        bool alternatingEndpoint,
        bool oppositeTaperWithinAllowance,
        bool extensionOutsideRequiredWindow,
        double coveragePercent,
        double requiredWindowLength,
        double windowCoveragePercent,
        ExteriorRoomPhysicalGate physicalGate)
    {
        if (!singleEndpointExtension) return "REJECT_STAGGERED_REQUIRES_EXACTLY_ONE_EXTENDED_ENDPOINT";
        if (!extensionWithinCornerEnvelope) return "REJECT_STAGGERED_EXTENSION_EXCEEDS_CORNER_ENVELOPE";
        if (!alternatingEndpoint) return "REJECT_STAGGERED_ENDPOINTS_DO_NOT_ALTERNATE";
        if (!oppositeTaperWithinAllowance) return "REJECT_STAGGERED_OPPOSITE_TAPER_EXCEEDS_LANE_ALLOWANCE";
        if (!extensionOutsideRequiredWindow) return "REJECT_STAGGERED_EXTENSION_OVERLAPS_REQUIRED_WINDOW";
        if (coveragePercent + 0.000001 < 90) return "REJECT_STAGGERED_USEFUL_COVERAGE_BELOW_90_PERCENT";
        if (requiredWindowLength > 0.001 && windowCoveragePercent + 0.000001 < 100)
            return "REJECT_STAGGERED_WINDOW_PROJECTION_BELOW_100_PERCENT";
        if (!physicalGate.Direct100UTurnPass) return "REJECT_STAGGERED_DIRECT_100MM_U_TURN";
        if (!physicalGate.R80Pass) return "REJECT_STAGGERED_AGGREGATE_ROOM_R80_GATE";
        if (!physicalGate.SelfContactPass) return "REJECT_STAGGERED_AGGREGATE_ROOM_SELF_CONTACT";
        if (!physicalGate.InterCircuitContactPass) return "REJECT_STAGGERED_AGGREGATE_ROOM_INTER_CIRCUIT_CONTACT";
        if (!physicalGate.BodyWallPass) return "REJECT_STAGGERED_AGGREGATE_ROOM_BODY_WALL_GATE";
        if (!physicalGate.HorizontalTurnWallPass) return "REJECT_STAGGERED_AGGREGATE_ROOM_TURN_WALL_GATE";
        return "PASS_STAGGERED_ALTERNATING_TURNOUT_OUTSIDE_REQUIRED_WINDOW";
    }

    private static ExteriorRoomPhysicalGate AnalyzeExteriorRoomPhysicalGate(HomeAuraProject project, string roomId)
    {
        var roomCircuits = project.Circuits
            .Where(item => IsHeatingBodyRole(item.SystemRole) && item.RoomId == roomId)
            .ToArray();
        var roomCircuitIds = roomCircuits.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var roomFloorId = project.Rooms.SingleOrDefault(item => item.Id == roomId)?.FloorId;
        var roomWalls = project.Walls.Where(item => WallAppliesToFloor(item, roomFloorId)).ToArray();
        var r80Pass = true;
        var selfContactPass = true;
        var interCircuitContactPass = true;
        var bodyWallPass = true;
        var horizontalTurnWallPass = true;
        var direct100UTurnPass = true;
        var minimumSegmentLength = double.PositiveInfinity;
        foreach (var roomCircuit in roomCircuits)
        {
            var geometry = MaterializeGeometry(roomCircuit, project.RoutingRules.MinimumBendRadiusMm);
            var bend = AnalyzeBends(roomCircuit, geometry.Transitions, project.RoutingRules.MinimumBendRadiusMm);
            var bodySegments = HeatingBodySegments(roomCircuit);
            var bodySegmentIndices = bodySegments.Select(item => item.CircuitSegmentIndex).ToHashSet();
            var selfClearance = AnalyzeSelfClearance(project, roomCircuit, geometry.Segments);
            var interClearance = AnalyzeInterCircuitClearance(project, roomCircuit, geometry.Segments, roomCircuitIds);
            r80Pass &= bend.Violations.Count == 0 && geometry.UnmaterializedElevationChangeCount == 0 &&
                       geometry.Transitions.All(item => item.MaterializedPass);
            selfContactPass &= selfClearance.PlanContactCount == 0 && selfClearance.SurfaceViolationCount == 0;
            interCircuitContactPass &= interClearance.PlanContactCount == 0 && interClearance.SurfaceViolationCount == 0;
            bodyWallPass &= HeatingBodyInsideAssignedRoom(
                                project, roomCircuit, HeatingBodyPoints(roomCircuit), bodySegments) &&
                            AnalyzeWallIntrusions(roomWalls, bodySegments).Count == 0;
            horizontalTurnWallPass &= AnalyzeHorizontalTurnWallIntrusions(
                roomWalls, bend.HorizontalFillets, bodySegmentIndices).Count == 0;
            direct100UTurnPass &= !HasDirectOnePitchUTurn(roomCircuit, project.RoutingRules.ExteriorWallSpacingMm);
            foreach (var segment in Segments(roomCircuit.OrderedPoints))
                minimumSegmentLength = Math.Min(minimumSegmentLength,
                    Distance3(ResolvePoint(roomCircuit, segment.A), ResolvePoint(roomCircuit, segment.B)));
        }
        return new ExteriorRoomPhysicalGate(
            r80Pass,
            selfContactPass,
            interCircuitContactPass,
            bodyWallPass,
            horizontalTurnWallPass,
            direct100UTurnPass,
            double.IsPositiveInfinity(minimumSegmentLength) ? 0 : minimumSegmentLength);
    }

    private static bool HasDirectOnePitchUTurn(ManualCircuit circuit, int pitchMm)
    {
        foreach (var range in GetHeatingBodyRanges(circuit))
        for (var pointIndex = range.StartIndex + 1; pointIndex + 2 <= range.EndIndex; pointIndex++)
        {
            var a = circuit.OrderedPoints[pointIndex - 1];
            var b = circuit.OrderedPoints[pointIndex];
            var c = circuit.OrderedPoints[pointIndex + 1];
            var d = circuit.OrderedPoints[pointIndex + 2];
            if (Math.Abs(Distance(b, c) - pitchMm) > 0.001) continue;
            var incomingX = b.X - a.X;
            var incomingY = b.Y - a.Y;
            var connectorX = c.X - b.X;
            var connectorY = c.Y - b.Y;
            var outgoingX = d.X - c.X;
            var outgoingY = d.Y - c.Y;
            var firstTurn = incomingX * connectorX + incomingY * connectorY == 0;
            var secondTurn = connectorX * outgoingX + connectorY * outgoingY == 0;
            var outerSegmentsOpposite = incomingX * outgoingY - incomingY * outgoingX == 0 &&
                                        incomingX * outgoingX + incomingY * outgoingY < 0;
            if (firstTurn && secondTurn && outerSegmentsOpposite) return true;
        }
        return false;
    }

    private static double ExteriorCornerEnvelopeMm(HomeAuraProject project)
    {
        var physicalEnvelope = project.RoutingRules.MinimumBendRadiusMm +
                               project.RoutingRules.PipeOuterDiameterMm / 2d;
        var snappedEnvelope = project.GridSpacingMm > 0
            ? Math.Ceiling(physicalEnvelope / project.GridSpacingMm) * project.GridSpacingMm
            : physicalEnvelope;
        return Math.Max(project.RoutingRules.ExteriorWallSpacingMm, snappedEnvelope);
    }

    private static IReadOnlyList<(double From, double To)> PartitionExteriorWallSpan(
        HomeAuraProject project,
        RoomZone room,
        WallSegment exteriorWall,
        double rawFrom,
        double rawTo,
        int normalX,
        int normalY)
    {
        var horizontal = exteriorWall.Start.Y == exteriorWall.End.Y;
        var probeDistance = exteriorWall.ThicknessMm / 2d + 1;
        var partitionSolids = new List<(double From, double To)>();
        foreach (var partition in project.Walls.Where(item => item.Id != exteriorWall.Id && item.WallType == "INTERIOR" &&
                                                        WallAppliesToFloor(item, room.FloorId)))
        {
            if (horizontal ? partition.Start.X != partition.End.X : partition.Start.Y != partition.End.Y) continue;
            var coordinate = horizontal ? (double)partition.Start.X : partition.Start.Y;
            if (coordinate <= rawFrom + 0.001 || coordinate >= rawTo - 0.001) continue;
            var intersection = horizontal
                ? new PointMm(partition.Start.X, exteriorWall.Start.Y)
                : new PointMm(exteriorWall.Start.X, partition.Start.Y);
            if (PointToSegmentDistance(intersection, partition.Start, partition.End) > 0.001) continue;
            var probe = horizontal
                ? new PointMm(partition.Start.X,
                    (int)Math.Round(exteriorWall.Start.Y + normalY * probeDistance, MidpointRounding.AwayFromZero))
                : new PointMm(
                    (int)Math.Round(exteriorWall.Start.X + normalX * probeDistance, MidpointRounding.AwayFromZero),
                    partition.Start.Y);
            if (!Covers(room.Outline, probe) || PointToSegmentDistance(probe, partition.Start, partition.End) > 0.001)
                continue;
            var halfThickness = partition.ThicknessMm / 2d;
            partitionSolids.Add((Math.Max(rawFrom, coordinate - halfThickness),
                Math.Min(rawTo, coordinate + halfThickness)));
        }

        var cells = new List<(double From, double To)>();
        var cursor = rawFrom;
        foreach (var solid in MergeIntervals(partitionSolids))
        {
            if (solid.From > cursor + 0.001) cells.Add((cursor, solid.From));
            cursor = Math.Max(cursor, solid.To);
        }
        if (rawTo > cursor + 0.001) cells.Add((cursor, rawTo));
        return cells;
    }

    private static string? ResolveSingleFloorCircuitScope(HomeAuraProject project, ManualCircuit circuit)
    {
        var collector = circuit.CollectorId is null
            ? null
            : project.Collectors.SingleOrDefault(item => item.Id == circuit.CollectorId);
        if (collector is not null && !string.IsNullOrWhiteSpace(collector.FloorId) &&
            !string.IsNullOrWhiteSpace(collector.ServedFloorId) && collector.FloorId != collector.ServedFloorId)
            return null;
        var roomFloor = circuit.RoomId is null
            ? null
            : project.Rooms.SingleOrDefault(item => item.Id == circuit.RoomId)?.FloorId;
        if (!string.IsNullOrWhiteSpace(roomFloor)) return roomFloor;
        if (collector is null) return null;
        if (!string.IsNullOrWhiteSpace(collector.ServedFloorId) &&
            (string.IsNullOrWhiteSpace(collector.FloorId) || collector.FloorId == collector.ServedFloorId))
            return collector.ServedFloorId;
        return !string.IsNullOrWhiteSpace(collector.FloorId) && string.IsNullOrWhiteSpace(collector.ServedFloorId)
            ? collector.FloorId
            : null;
    }

    private static bool WallAppliesToFloor(WallSegment wall, string? floorId) =>
        string.IsNullOrWhiteSpace(floorId) || string.IsNullOrWhiteSpace(wall.FloorId) || wall.FloorId == floorId;

    private static IReadOnlyList<WallSegment> WallsForCircuit(HomeAuraProject project, ManualCircuit circuit)
    {
        var floorId = ResolveSingleFloorCircuitScope(project, circuit);
        return project.Walls.Where(wall => WallAppliesToFloor(wall, floorId)).ToArray();
    }

    private static bool CircuitScopesMayInteract(HomeAuraProject project, ManualCircuit first, ManualCircuit second)
    {
        var firstFloor = ResolveSingleFloorCircuitScope(project, first);
        var secondFloor = ResolveSingleFloorCircuitScope(project, second);
        return string.IsNullOrWhiteSpace(firstFloor) || string.IsNullOrWhiteSpace(secondFloor) || firstFloor == secondFloor;
    }

    private static bool IsHeatingBodyRole(string systemRole) =>
        systemRole is "FLOOR_HEATING_LOOP" or "FLOOR_HEATING_AXIS";

    private static bool TryGetRoomWallOverlap(RoomZone room, WallSegment wall, out PointMm overlapStart, out PointMm overlapEnd)
    {
        overlapStart = new PointMm();
        overlapEnd = new PointMm();
        var wallHorizontal = wall.Start.Y == wall.End.Y;
        var wallVertical = wall.Start.X == wall.End.X;
        if (!wallHorizontal && !wallVertical) return false;
        var closedOutline = room.Outline.Concat([room.Outline[0]]).ToArray();

        foreach (var edge in Segments(closedOutline))
        {
            if (wallHorizontal && edge.A.Y == edge.B.Y && edge.A.Y == wall.Start.Y)
            {
                var from = Math.Max(Math.Min(wall.Start.X, wall.End.X), Math.Min(edge.A.X, edge.B.X));
                var to = Math.Min(Math.Max(wall.Start.X, wall.End.X), Math.Max(edge.A.X, edge.B.X));
                if (to <= from) continue;
                overlapStart = new PointMm(from, wall.Start.Y);
                overlapEnd = new PointMm(to, wall.Start.Y);
                return true;
            }
            if (wallVertical && edge.A.X == edge.B.X && edge.A.X == wall.Start.X)
            {
                var from = Math.Max(Math.Min(wall.Start.Y, wall.End.Y), Math.Min(edge.A.Y, edge.B.Y));
                var to = Math.Min(Math.Max(wall.Start.Y, wall.End.Y), Math.Max(edge.A.Y, edge.B.Y));
                if (to <= from) continue;
                overlapStart = new PointMm(wall.Start.X, from);
                overlapEnd = new PointMm(wall.Start.X, to);
                return true;
            }
        }
        return false;
    }

    private static bool AxisWallsPerpendicular(WallSegment first, WallSegment second)
    {
        var firstHorizontal = first.Start.Y == first.End.Y && first.Start.X != first.End.X;
        var firstVertical = first.Start.X == first.End.X && first.Start.Y != first.End.Y;
        var secondHorizontal = second.Start.Y == second.End.Y && second.Start.X != second.End.X;
        var secondVertical = second.Start.X == second.End.X && second.Start.Y != second.End.Y;
        return firstHorizontal && secondVertical || firstVertical && secondHorizontal;
    }

    private static double PerpendicularWallEndTrim(HomeAuraProject project, WallSegment wall, PointMm endpoint)
    {
        var horizontal = wall.Start.Y == wall.End.Y;
        return project.Walls
            .Where(item => item.Id != wall.Id)
            .Where(item => WallAppliesToFloor(item, wall.FloorId))
            .Where(item => horizontal ? item.Start.X == item.End.X : item.Start.Y == item.End.Y)
            .Where(item => PointToSegmentDistance(endpoint, item.Start, item.End) <= 0.001)
            .Select(item => item.ThicknessMm / 2d)
            .DefaultIfEmpty(0)
            .Max();
    }

    private static bool TryGetInteriorNormal(
        RoomZone room,
        WallSegment wall,
        PointMm overlapStart,
        PointMm overlapEnd,
        out int normalX,
        out int normalY)
    {
        normalX = 0;
        normalY = 0;
        var midpoint = new PointMm((overlapStart.X + overlapEnd.X) / 2, (overlapStart.Y + overlapEnd.Y) / 2);
        var probeDistance = wall.ThicknessMm / 2 + 1;
        if (wall.Start.Y == wall.End.Y)
        {
            var positive = Covers(room.Outline, new PointMm(midpoint.X, midpoint.Y + probeDistance));
            var negative = Covers(room.Outline, new PointMm(midpoint.X, midpoint.Y - probeDistance));
            if (positive == negative) return false;
            normalY = positive ? 1 : -1;
            return true;
        }
        var right = Covers(room.Outline, new PointMm(midpoint.X + probeDistance, midpoint.Y));
        var left = Covers(room.Outline, new PointMm(midpoint.X - probeDistance, midpoint.Y));
        if (right == left) return false;
        normalX = right ? 1 : -1;
        return true;
    }

    private static IReadOnlyList<(double From, double To)> MergeIntervals(IEnumerable<(double From, double To)> source)
    {
        var ordered = source.Where(item => item.To > item.From).OrderBy(item => item.From).ThenBy(item => item.To).ToArray();
        if (ordered.Length == 0) return [];
        var merged = new List<(double From, double To)> { ordered[0] };
        foreach (var interval in ordered.Skip(1))
        {
            var current = merged[^1];
            if (interval.From > current.To + 0.001)
            {
                merged.Add(interval);
                continue;
            }
            merged[^1] = (current.From, Math.Max(current.To, interval.To));
        }
        return merged;
    }

    private static IReadOnlyList<(double From, double To)> IntersectIntervals(
        IReadOnlyList<(double From, double To)> first,
        IReadOnlyList<(double From, double To)> second) =>
        MergeIntervals(first.SelectMany(a => second.Select(b =>
            (From: Math.Max(a.From, b.From), To: Math.Min(a.To, b.To)))));

    private static double IntervalLength(IEnumerable<(double From, double To)> intervals) =>
        intervals.Sum(item => Math.Max(0, item.To - item.From));

    private static double IntersectionLength(
        IReadOnlyList<(double From, double To)> first,
        IReadOnlyList<(double From, double To)> second)
    {
        var total = 0d;
        foreach (var a in first)
        foreach (var b in second)
            total += Math.Max(0, Math.Min(a.To, b.To) - Math.Max(a.From, b.From));
        return total;
    }

    private static double SegmentDistance((PointMm A, PointMm B) first, (PointMm A, PointMm B) second)
    {
        if (Intersects(first, second)) return 0;
        return new[]
        {
            PointToSegmentDistance(first.A, second.A, second.B),
            PointToSegmentDistance(first.B, second.A, second.B),
            PointToSegmentDistance(second.A, first.A, first.B),
            PointToSegmentDistance(second.B, first.A, first.B),
        }.Min();
    }

    private static BendAnalysis AnalyzeBends(
        ManualCircuit circuit,
        IReadOnlyList<VerticalTransitionAnalysisDetail> transitions,
        int radiusMm)
    {
        var points = circuit.OrderedPoints;
        if (points.Count < 2) return new BendAnalysis(0, 0, [], []);
        var transitionBySegment = transitions.ToDictionary(item => item.CircuitSegmentIndex);
        var tangentRequirements = new double[points.Count];
        var turns = new bool[points.Count];
        var horizontalFillets = new List<HorizontalFillet>();
        var roundedCorrection = 0d;
        for (var pointIndex = 1; pointIndex + 1 < points.Count; pointIndex++)
        {
            var incoming = SegmentEndpointDirection(circuit, pointIndex - 1, transitionBySegment);
            var outgoing = SegmentEndpointDirection(circuit, pointIndex, transitionBySegment);
            if (incoming.Length <= 0.000001 || outgoing.Length <= 0.000001) continue;
            var cosine = Math.Clamp(Dot(incoming.Unit, outgoing.Unit), -1, 1);
            var angle = Math.Acos(cosine);
            if (angle <= 0.000001) continue;
            turns[pointIndex] = true;
            if (angle >= Math.PI - 0.000001)
            {
                tangentRequirements[pointIndex] = 1_000_000_000d;
                continue;
            }
            var tangent = radiusMm * Math.Tan(angle / 2);
            tangentRequirements[pointIndex] = tangent;
            roundedCorrection += 2 * tangent - radiusMm * angle;

            var incomingUnit = incoming.Unit;
            var outgoingUnit = outgoing.Unit;
            var cross = Cross2(incomingUnit.X, incomingUnit.Y, outgoingUnit.X, outgoingUnit.Y);
            if (Math.Abs(incomingUnit.Z) > 0.000001 || Math.Abs(outgoingUnit.Z) > 0.000001 ||
                Math.Abs(cross) <= 0.000001)
                continue;

            var vertex = ResolvePoint(circuit, points[pointIndex]);
            var arcStart = new Point3Mm(
                vertex.X - incomingUnit.X * tangent,
                vertex.Y - incomingUnit.Y * tangent,
                vertex.Z);
            var arcEnd = new Point3Mm(
                vertex.X + outgoingUnit.X * tangent,
                vertex.Y + outgoingUnit.Y * tangent,
                vertex.Z);
            var bisectorX = outgoingUnit.X - incomingUnit.X;
            var bisectorY = outgoingUnit.Y - incomingUnit.Y;
            var bisectorLength = Math.Sqrt(bisectorX * bisectorX + bisectorY * bisectorY);
            if (bisectorLength <= 0.000001) continue;
            var centerDistance = radiusMm / Math.Sin(angle / 2);
            var center = new Point3Mm(
                vertex.X + bisectorX / bisectorLength * centerDistance,
                vertex.Y + bisectorY / bisectorLength * centerDistance,
                vertex.Z);
            var incomingAvailable = transitionBySegment.TryGetValue(pointIndex - 1, out var incomingTransition) && incomingTransition.GeometryPass
                ? incomingTransition.EndTangentLengthMm
                : PlanDistance(ResolvePoint(circuit, points[pointIndex - 1]), vertex);
            var outgoingAvailable = transitionBySegment.TryGetValue(pointIndex, out var outgoingTransition) && outgoingTransition.GeometryPass
                ? outgoingTransition.StartTangentLengthMm
                : PlanDistance(vertex, ResolvePoint(circuit, points[pointIndex + 1]));
            horizontalFillets.Add(new HorizontalFillet(
                pointIndex,
                vertex,
                arcStart,
                arcEnd,
                center,
                radiusMm,
                angle,
                Math.Atan2(arcStart.Y - center.Y, arcStart.X - center.X),
                Math.Sign(cross) * angle,
                tangent,
                incomingAvailable + 0.001 >= tangent && outgoingAvailable + 0.001 >= tangent));
        }

        var violations = new List<BendRadiusViolationDetail>();
        for (var segmentIndex = 0; segmentIndex + 1 < points.Count; segmentIndex++)
        {
            var requiredStart = tangentRequirements[segmentIndex];
            var requiredEnd = tangentRequirements[segmentIndex + 1];
            var required = requiredStart + requiredEnd;
            if (required <= 0.000001) continue;
            double available;
            bool fits;
            if (transitionBySegment.TryGetValue(segmentIndex, out var transition) && transition.GeometryPass)
            {
                available = transition.StartTangentLengthMm + transition.EndTangentLengthMm;
                fits = requiredStart <= transition.StartTangentLengthMm + 0.001 &&
                       requiredEnd <= transition.EndTangentLengthMm + 0.001;
            }
            else
            {
                available = Distance3(ResolvePoint(circuit, points[segmentIndex]), ResolvePoint(circuit, points[segmentIndex + 1]));
                fits = available + 0.001 >= required;
            }
            if (fits) continue;
            violations.Add(new BendRadiusViolationDetail
            {
                SegmentIndex = segmentIndex,
                Start = points[segmentIndex].Clone(),
                End = points[segmentIndex + 1].Clone(),
                TurnAtStart = turns[segmentIndex],
                TurnAtEnd = turns[segmentIndex + 1],
                AvailableLengthMm = available,
                RequiredTangentLengthMm = required >= int.MaxValue ? int.MaxValue : (int)Math.Ceiling(required - 0.0000001),
                RequiredTangentLengthExactMm = required,
            });
        }
        return new BendAnalysis(turns.Count(value => value), roundedCorrection, violations, horizontalFillets);
    }

    private static Vector3 SegmentEndpointDirection(
        ManualCircuit circuit,
        int segmentIndex,
        IReadOnlyDictionary<int, VerticalTransitionAnalysisDetail> transitions)
    {
        var start = ResolvePoint(circuit, circuit.OrderedPoints[segmentIndex]);
        var end = ResolvePoint(circuit, circuit.OrderedPoints[segmentIndex + 1]);
        if (transitions.TryGetValue(segmentIndex, out var transition) && transition.GeometryPass)
            return new Vector3(end.X - start.X, end.Y - start.Y, 0).Unit;
        return new Vector3(end.X - start.X, end.Y - start.Y, end.Z - start.Z).Unit;
    }

    private static List<int> AnalyzeSpacing(IReadOnlyList<(PointMm A, PointMm B)> segments)
    {
        var values = new List<int>();
        for (var i = 0; i < segments.Count; i++)
        for (var j = i + 2; j < segments.Count; j++)
        {
            var first = segments[i]; var second = segments[j];
            if (first.A.Y == first.B.Y && second.A.Y == second.B.Y && Overlap(first.A.X, first.B.X, second.A.X, second.B.X))
                values.Add(Math.Abs(first.A.Y - second.A.Y));
            else if (first.A.X == first.B.X && second.A.X == second.B.X && Overlap(first.A.Y, first.B.Y, second.A.Y, second.B.Y))
                values.Add(Math.Abs(first.A.X - second.A.X));
        }
        return values.Where(v => v > 0 && v <= 1000).ToList();
    }

    private static bool Overlap(int a, int b, int c, int d) => Math.Max(Math.Min(a, b), Math.Min(c, d)) < Math.Min(Math.Max(a, b), Math.Max(c, d));
    private static bool Same(PointMm a, PointMm b) => a.X == b.X && a.Y == b.Y;

    private static bool Intersects((PointMm A, PointMm B) first, (PointMm A, PointMm B) second)
    {
        static long Cross(PointMm a, PointMm b, PointMm c) => (long)(b.X - a.X) * (c.Y - a.Y) - (long)(b.Y - a.Y) * (c.X - a.X);
        static bool Within(PointMm a, PointMm b, PointMm p) => p.X >= Math.Min(a.X, b.X) && p.X <= Math.Max(a.X, b.X) && p.Y >= Math.Min(a.Y, b.Y) && p.Y <= Math.Max(a.Y, b.Y);
        var c1 = Cross(first.A, first.B, second.A); var c2 = Cross(first.A, first.B, second.B);
        var c3 = Cross(second.A, second.B, first.A); var c4 = Cross(second.A, second.B, first.B);
        if ((c1 > 0 && c2 < 0 || c1 < 0 && c2 > 0) && (c3 > 0 && c4 < 0 || c3 < 0 && c4 > 0)) return true;
        return c1 == 0 && Within(first.A, first.B, second.A) || c2 == 0 && Within(first.A, first.B, second.B) || c3 == 0 && Within(second.A, second.B, first.A) || c4 == 0 && Within(second.A, second.B, first.B);
    }
}
