using System.Text.Json;
using System.Text.Json.Serialization;
using System.Globalization;

namespace HomeAura.NativeEditor;

public sealed class PointMm
{
    [JsonPropertyName("x_mm")] public int X { get; set; }
    [JsonPropertyName("y_mm")] public int Y { get; set; }
    [JsonPropertyName("z_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? Z { get; set; }

    public PointMm() { }
    public PointMm(int x, int y) { X = x; Y = y; }
    public PointMm(int x, int y, int z) { X = x; Y = y; Z = z; }
    public PointMm Clone() => Z is null ? new(X, Y) : new(X, Y, Z.Value);
}

public sealed class Point3Mm
{
    [JsonPropertyName("x_mm")] public double X { get; init; }
    [JsonPropertyName("y_mm")] public double Y { get; init; }
    [JsonPropertyName("z_mm")] public double Z { get; init; }

    public Point3Mm() { }
    public Point3Mm(double x, double y, double z) { X = x; Y = y; Z = z; }
}

public sealed class CollectorConnectionPoint
{
    [JsonPropertyName("connection_index")] public int ConnectionIndex { get; set; }
    [JsonPropertyName("loop_index")] public int LoopIndex { get; set; }
    [JsonPropertyName("header")] public string Header { get; set; } = "SUPPLY";
    [JsonPropertyName("local_position_mm")] public Point3Mm LocalPositionMm { get; set; } = new();
}

public sealed class VerticalTransition
{
    [JsonPropertyName("segment_index")] public int SegmentIndex { get; set; }
    [JsonPropertyName("kind")] public string Kind { get; set; } = "S_BEND_R80";
    [JsonPropertyName("radius_mm")] public double RadiusMm { get; set; } = 80;
    [JsonPropertyName("start_tangent_length_mm")] public double StartTangentLengthMm { get; set; }
    [JsonPropertyName("end_tangent_length_mm")] public double EndTangentLengthMm { get; set; }
    [JsonPropertyName("arc_samples_per_half")] public int ArcSamplesPerHalf { get; set; } = 8;
}

public sealed class WallSegment
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("start")] public PointMm Start { get; set; } = new();
    [JsonPropertyName("end")] public PointMm End { get; set; } = new();
    [JsonPropertyName("wall_type")] public string WallType { get; set; } = "INTERIOR";
    [JsonPropertyName("thickness_mm")] public int ThicknessMm { get; set; } = 200;
    [JsonPropertyName("floor_id"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? FloorId { get; set; }
    [JsonPropertyName("verified_finish_face_a_outline_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<PointMm>? VerifiedFinishFaceAOutlineMm { get; set; }
    [JsonPropertyName("verified_finish_face_b_outline_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<PointMm>? VerifiedFinishFaceBOutlineMm { get; set; }
    [JsonPropertyName("base_elevation_mm_shared_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? BaseElevationMmSharedDatum { get; set; }
    [JsonPropertyName("top_elevation_mm_shared_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? TopElevationMmSharedDatum { get; set; }
    [JsonPropertyName("physical_verification"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class WindowOpening
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("wall_id")] public string? WallId { get; set; }
    [JsonPropertyName("start")] public PointMm Start { get; set; } = new();
    [JsonPropertyName("end")] public PointMm End { get; set; } = new();
    [JsonPropertyName("sill_height_mm")] public int? SillHeightMm { get; set; }
    [JsonPropertyName("opening_height_mm")] public int? OpeningHeightMm { get; set; }
    [JsonPropertyName("floor_id"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? FloorId { get; set; }
    [JsonPropertyName("verified_plan_outline_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<PointMm>? VerifiedPlanOutlineMm { get; set; }
    [JsonPropertyName("clear_width_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public double? ClearWidthMm { get; set; }
    [JsonPropertyName("sill_elevation_mm_shared_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? SillElevationMmSharedDatum { get; set; }
    [JsonPropertyName("physical_verification"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class PhysicalVerification
{
    [JsonPropertyName("status")] public string Status { get; set; } = "UNVERIFIED";
    [JsonPropertyName("measurement_source_type")] public string? MeasurementSourceType { get; set; }
    [JsonPropertyName("source_document_id")] public string? SourceDocumentId { get; set; }
    [JsonPropertyName("source_document_paths")] public List<string> SourceDocumentPaths { get; set; } = [];
    [JsonPropertyName("photo_evidence_paths")] public List<string> PhotoEvidencePaths { get; set; } = [];
    [JsonPropertyName("measured_by")] public string? MeasuredBy { get; set; }
    [JsonPropertyName("measurement_date")] public string? MeasurementDate { get; set; }
    [JsonPropertyName("survey_tolerance_mm")] public double? SurveyToleranceMm { get; set; }
    [JsonPropertyName("independent_verification_record_ids")] public List<string> IndependentVerificationRecordIds { get; set; } = [];
}

public sealed class DatumControlPoint
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "";
    [JsonPropertyName("position_mm")] public Point3Mm PositionMm { get; set; } = new();
    [JsonPropertyName("reference_description")] public string ReferenceDescription { get; set; } = "";
}

public sealed class SharedSpatialDatum
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("coordinate_reference_description")] public string? CoordinateReferenceDescription { get; set; }
    [JsonPropertyName("horizontal_origin_reference")] public string? HorizontalOriginReference { get; set; }
    [JsonPropertyName("vertical_zero_reference")] public string? VerticalZeroReference { get; set; }
    [JsonPropertyName("floor_ids_bound_to_datum")] public List<string> FloorIdsBoundToDatum { get; set; } = [];
    [JsonPropertyName("control_points")] public List<DatumControlPoint> ControlPoints { get; set; } = [];
    [JsonPropertyName("physical_verification")] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class DoorOpening
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "";
    [JsonPropertyName("wall_id")] public string WallId { get; set; } = "";
    [JsonPropertyName("start")] public PointMm Start { get; set; } = new();
    [JsonPropertyName("end")] public PointMm End { get; set; } = new();
    [JsonPropertyName("verified_plan_outline_mm")] public List<PointMm>? VerifiedPlanOutlineMm { get; set; }
    [JsonPropertyName("clear_width_mm")] public double? ClearWidthMm { get; set; }
    [JsonPropertyName("clear_height_mm")] public int? ClearHeightMm { get; set; }
    [JsonPropertyName("threshold_disposition")] public string? ThresholdDisposition { get; set; }
    [JsonPropertyName("threshold_height_mm")] public int? ThresholdHeightMm { get; set; }
    [JsonPropertyName("threshold_elevation_mm_shared_datum")] public int? ThresholdElevationMmSharedDatum { get; set; }
    [JsonPropertyName("physical_verification")] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class InterfloorOpeningFace
{
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "";
    [JsonPropertyName("verified_plan_outline_mm")] public List<PointMm> VerifiedPlanOutlineMm { get; set; } = [];
    [JsonPropertyName("center_mm_shared_datum")] public Point3Mm? CenterMmSharedDatum { get; set; }
    [JsonPropertyName("face_elevation_min_mm_shared_datum")] public int? FaceElevationMinMmSharedDatum { get; set; }
    [JsonPropertyName("face_elevation_max_mm_shared_datum")] public int? FaceElevationMaxMmSharedDatum { get; set; }
}

public sealed class StructuralDisposition
{
    [JsonPropertyName("status")] public string Status { get; set; } = "UNREVIEWED";
    [JsonPropertyName("record_id")] public string? RecordId { get; set; }
    [JsonPropertyName("authority_name")] public string? AuthorityName { get; set; }
    [JsonPropertyName("authority_document_id")] public string? AuthorityDocumentId { get; set; }
    [JsonPropertyName("authority_document_paths")] public List<string> AuthorityDocumentPaths { get; set; } = [];
    [JsonPropertyName("approved_clear_outline_mm")] public List<PointMm> ApprovedClearOutlineMm { get; set; } = [];
    [JsonPropertyName("approval_date")] public string? ApprovalDate { get; set; }
    [JsonPropertyName("conditions")] public List<string> Conditions { get; set; } = [];
}

public sealed class InterfloorOpening
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("opening_type")] public string OpeningType { get; set; } = "SLAB_OPENING";
    [JsonPropertyName("shape_type")] public string? ShapeType { get; set; }
    [JsonPropertyName("from_floor_id")] public string FromFloorId { get; set; } = "";
    [JsonPropertyName("to_floor_id")] public string ToFloorId { get; set; } = "";
    [JsonPropertyName("shared_datum_id")] public string SharedDatumId { get; set; } = "";
    [JsonPropertyName("from_floor_face")] public InterfloorOpeningFace FromFloorFace { get; set; } = new();
    [JsonPropertyName("to_floor_face")] public InterfloorOpeningFace ToFloorFace { get; set; } = new();
    [JsonPropertyName("clear_depth_mm")] public int? ClearDepthMm { get; set; }
    [JsonPropertyName("clear_diameter_mm")] public double? ClearDiameterMm { get; set; }
    [JsonPropertyName("clear_width_mm")] public double? ClearWidthMm { get; set; }
    [JsonPropertyName("clear_length_mm")] public double? ClearLengthMm { get; set; }
    [JsonPropertyName("clear_bottom_elevation_mm_shared_datum")] public int? ClearBottomElevationMmSharedDatum { get; set; }
    [JsonPropertyName("clear_top_elevation_mm_shared_datum")] public int? ClearTopElevationMmSharedDatum { get; set; }
    [JsonPropertyName("clear_axis_definition_method")] public string? ClearAxisDefinitionMethod { get; set; }
    [JsonPropertyName("centerline_mm_shared_datum")] public List<Point3Mm>? CenterlineMmSharedDatum { get; set; }
    [JsonPropertyName("clear_axis_vector")] public Point3Mm? ClearAxisVector { get; set; }
    [JsonPropertyName("clear_axis_azimuth_degrees_shared_datum")] public double? ClearAxisAzimuthDegreesSharedDatum { get; set; }
    [JsonPropertyName("clear_axis_inclination_degrees_shared_datum")] public double? ClearAxisInclinationDegreesSharedDatum { get; set; }
    [JsonPropertyName("clear_axis_orientation_tolerance_degrees")] public double? ClearAxisOrientationToleranceDegrees { get; set; }
    [JsonPropertyName("clear_axis_direction")] public string? ClearAxisDirection { get; set; }
    [JsonPropertyName("physical_verification")] public PhysicalVerification? PhysicalVerification { get; set; }
    [JsonPropertyName("structural_disposition")] public StructuralDisposition? StructuralDisposition { get; set; }
}

public sealed class Collector
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("position")] public PointMm Position { get; set; } = new();
    [JsonPropertyName("ports")] public int Ports { get; set; } = 12;
    [JsonPropertyName("rotation_degrees")] public int RotationDegrees { get; set; }
    [JsonPropertyName("connection_tolerance_mm")] public int ConnectionToleranceMm { get; set; } = 400;
    [JsonPropertyName("floor_id")] public string? FloorId { get; set; }
    [JsonPropertyName("served_floor_id")] public string? ServedFloorId { get; set; }
    [JsonPropertyName("mounting_wall_id")] public string? MountingWallId { get; set; }
    [JsonPropertyName("visible_on_plan")] public bool VisibleOnPlan { get; set; } = true;
    [JsonPropertyName("external_to_plan")] public bool ExternalToPlan { get; set; }
    [JsonPropertyName("pipe_outlet_direction")] public string PipeOutletDirection { get; set; } = "DOWN";
    [JsonPropertyName("reference_width_mm")] public int ReferenceWidthMm { get; set; } = 750;
    [JsonPropertyName("reference_depth_mm")] public int ReferenceDepthMm { get; set; } = 100;
    [JsonPropertyName("reference_height_mm")] public int ReferenceHeightMm { get; set; } = 320;
    [JsonPropertyName("equipment_status")] public string EquipmentStatus { get; set; } = "DRAFT_UNSELECTED";
    [JsonPropertyName("reference_source")] public string? ReferenceSource { get; set; }
    [JsonPropertyName("manufacturer"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? Manufacturer { get; set; }
    [JsonPropertyName("model"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? Model { get; set; }
    [JsonPropertyName("part_number"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? PartNumber { get; set; }
    [JsonPropertyName("loop_count"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? LoopCount { get; set; }
    [JsonPropertyName("connection_point_count"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? ConnectionPointCount { get; set; }
    [JsonPropertyName("header_pitch_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? HeaderPitchMm { get; set; }
    [JsonPropertyName("loop_connection_pitch_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? LoopConnectionPitchMm { get; set; }
    [JsonPropertyName("reference_length_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? ReferenceLengthMm { get; set; }
    [JsonPropertyName("connection_points"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<CollectorConnectionPoint>? ConnectionPoints { get; set; }

    [JsonIgnore] public int ConnectionCapacity => ConnectionPointCount ?? Ports;
    [JsonIgnore] public bool HasPhysicalReferenceGeometry =>
        LoopCount is > 0 && ConnectionPointCount is > 0 && HeaderPitchMm is > 0 &&
        LoopConnectionPitchMm is > 0 && ReferenceLengthMm is > 0;

    public List<CollectorConnectionPoint> BuildReferenceConnectionPoints()
    {
        if (!HasPhysicalReferenceGeometry)
            throw new InvalidOperationException($"{Id}: для построения точек коллектора нужны число петель, число подключений, оба шага и справочная длина.");
        var loopCount = LoopCount ?? throw new InvalidOperationException($"{Id}: число петель не задано.");
        var connectionPointCount = ConnectionPointCount ?? throw new InvalidOperationException($"{Id}: число подключений не задано.");
        var loopPitch = LoopConnectionPitchMm ?? throw new InvalidOperationException($"{Id}: шаг подключений не задан.");
        var headerPitch = HeaderPitchMm ?? throw new InvalidOperationException($"{Id}: шаг коллекторных балок не задан.");
        if (connectionPointCount != loopCount * 2)
            throw new InvalidOperationException($"{Id}: каждой петле коллектора нужны отдельные точки подачи и обратки.");

        var result = new List<CollectorConnectionPoint>(connectionPointCount);
        var firstAlong = -(loopCount - 1) * loopPitch / 2d;
        for (var loopIndex = 0; loopIndex < loopCount; loopIndex++)
        {
            var along = firstAlong + loopIndex * loopPitch;
            result.Add(new CollectorConnectionPoint
            {
                ConnectionIndex = loopIndex * 2,
                LoopIndex = loopIndex,
                Header = "SUPPLY",
                LocalPositionMm = new Point3Mm(along, -headerPitch / 2d, 0),
            });
            result.Add(new CollectorConnectionPoint
            {
                ConnectionIndex = loopIndex * 2 + 1,
                LoopIndex = loopIndex,
                Header = "RETURN",
                LocalPositionMm = new Point3Mm(along, headerPitch / 2d, 0),
            });
        }
        return result;
    }

    public IReadOnlyList<CollectorConnectionPoint> ResolveConnectionPoints() =>
        ConnectionPoints is { Count: > 0 } ? ConnectionPoints : HasPhysicalReferenceGeometry ? BuildReferenceConnectionPoints() : [];

    public void MaterializeReferenceConnectionPoints()
    {
        ConnectionPoints = BuildReferenceConnectionPoints();
    }

    public double MountingWallAngleDegrees(HomeAuraProject project)
    {
        if (MountingWallId is null) return 0;
        var wall = project.Walls.SingleOrDefault(item => item.Id == MountingWallId);
        return wall is null ? 0 : Math.Atan2(wall.End.Y - wall.Start.Y, wall.End.X - wall.Start.X) * 180d / Math.PI;
    }

    public Point3Mm ConnectionPointWorldPosition(CollectorConnectionPoint point, double mountingWallAngleDegrees)
    {
        var radians = (mountingWallAngleDegrees + RotationDegrees) * Math.PI / 180d;
        var cosine = Math.Cos(radians);
        var sine = Math.Sin(radians);
        var local = point.LocalPositionMm;
        return new Point3Mm(
            Position.X + local.X * cosine - local.Y * sine,
            Position.Y + local.X * sine + local.Y * cosine,
            local.Z);
    }
}

public sealed class ManualCircuit
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("name")] public string Name { get; set; } = "Контур 1";
    [JsonPropertyName("color")] public string Color { get; set; } = "#29B6F6";
    [JsonPropertyName("ordered_points")] public List<PointMm> OrderedPoints { get; set; } = [];
    [JsonPropertyName("vertical_transitions")] public List<VerticalTransition> VerticalTransitions { get; set; } = [];
    [JsonPropertyName("completed")] public bool Completed { get; set; }
    [JsonPropertyName("collector_id")] public string? CollectorId { get; set; }
    [JsonPropertyName("supply_port_index")] public int? SupplyPortIndex { get; set; }
    [JsonPropertyName("return_port_index")] public int? ReturnPortIndex { get; set; }
    [JsonPropertyName("service_zone_id")] public string? ServiceZoneId { get; set; }
    [JsonPropertyName("concealed_service_length_mm")] public int ConcealedServiceLengthMm { get; set; }
    [JsonPropertyName("out_of_plane_length_mm")] public int OutOfPlaneLengthMm { get; set; }
    [JsonPropertyName("routing_layer")] public string RoutingLayer { get; set; } = "HEATING_PLANE";
    [JsonPropertyName("system_role")] public string SystemRole { get; set; } = "FLOOR_HEATING_LOOP";
    [JsonPropertyName("axis_elevation_mm")] public int? AxisElevationMm { get; set; }
    [JsonPropertyName("visible_on_plan")] public bool VisibleOnPlan { get; set; } = true;
    [JsonPropertyName("room_id")] public string? RoomId { get; set; }
    [JsonPropertyName("heating_body_start_index")] public int? HeatingBodyStartIndex { get; set; }
    [JsonPropertyName("heating_body_end_index")] public int? HeatingBodyEndIndex { get; set; }
    [JsonPropertyName("heating_body_ranges")] public List<HeatingBodyRange> HeatingBodyRanges { get; set; } = [];
}

public sealed class HeatingBodyRange
{
    [JsonPropertyName("start_index")] public int StartIndex { get; set; }
    [JsonPropertyName("end_index")] public int EndIndex { get; set; }
}

public sealed class TrainingMetadata
{
    [JsonPropertyName("label")] public string Label { get; set; } = "DRAFT";
    [JsonPropertyName("notes")] public string Notes { get; set; } = "";
    [JsonPropertyName("author_intent")] public string AuthorIntent { get; set; } = "Manual reference drawing";
}

public sealed class FloorLevel
{
    [JsonPropertyName("id")] public string Id { get; set; } = "FLOOR_1";
    [JsonPropertyName("name")] public string Name { get; set; } = "Этаж 1";
    [JsonPropertyName("origin")] public PointMm Origin { get; set; } = new();
    [JsonPropertyName("outline")] public List<PointMm> Outline { get; set; } = [];
    [JsonPropertyName("label_position")] public PointMm LabelPosition { get; set; } = new();
    [JsonPropertyName("shared_datum_id"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? SharedDatumId { get; set; }
    [JsonPropertyName("finished_floor_elevation_mm_shared_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? FinishedFloorElevationMmSharedDatum { get; set; }
}

public sealed class RoomZone
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "FLOOR_1";
    [JsonPropertyName("name")] public string Name { get; set; } = "Помещение";
    [JsonPropertyName("area_m2")] public double? AreaM2 { get; set; }
    [JsonPropertyName("outline")] public List<PointMm> Outline { get; set; } = [];
    [JsonPropertyName("label_position")] public PointMm LabelPosition { get; set; } = new();
    [JsonPropertyName("heating_allowed")] public bool HeatingAllowed { get; set; } = true;
    [JsonPropertyName("fill_color")] public string FillColor { get; set; } = "#173742";
}

public sealed class ExclusionZone
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "FLOOR_1";
    [JsonPropertyName("name")] public string Name { get; set; } = "Запрет укладки";
    [JsonPropertyName("outline")] public List<PointMm> Outline { get; set; } = [];
    [JsonPropertyName("fill_color")] public string FillColor { get; set; } = "#7F1D1D";
}

public sealed class ServiceZone
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "FLOOR_1";
    [JsonPropertyName("name")] public string Name { get; set; } = "Сервисный канал";
    [JsonPropertyName("outline")] public List<PointMm> Outline { get; set; } = [];
    [JsonPropertyName("fill_color")] public string FillColor { get; set; } = "#164E63";
    [JsonPropertyName("note")] public string Note { get; set; } = "";
    [JsonPropertyName("collector_id")] public string? CollectorId { get; set; }
    [JsonPropertyName("clear_height_mm")] public int? ClearHeightMm { get; set; }
    [JsonPropertyName("pipe_capacity")] public int? PipeCapacity { get; set; }
    [JsonPropertyName("required_pipe_count")] public int? RequiredPipeCount { get; set; }
    [JsonPropertyName("required_plan_width_mm")] public int? RequiredPlanWidthMm { get; set; }
    [JsonPropertyName("pipe_geometry_materialized")] public bool PipeGeometryMaterialized { get; set; }
}

public sealed class FloorBuildUp
{
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "FLOOR_1";
    [JsonPropertyName("installed_insulation_mm")] public int InstalledInsulationMm { get; set; }
    [JsonPropertyName("remaining_height_mm")] public int RemainingHeightMm { get; set; }
    [JsonPropertyName("build_up_id"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public string? BuildUpId { get; set; }
    [JsonPropertyName("layer_registry"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<FloorLayer>? LayerRegistry { get; set; }
    [JsonPropertyName("total_build_up_thickness_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? TotalBuildUpThicknessMm { get; set; }
    [JsonPropertyName("allowed_pipe_axis_elevation_mm_shared_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? AllowedPipeAxisElevationMmSharedDatum { get; set; }
    [JsonPropertyName("allowed_pipe_axis_tolerance_mm"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public int? AllowedPipeAxisToleranceMm { get; set; }
    [JsonPropertyName("physical_verification"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class FloorLayer
{
    [JsonPropertyName("id")] public string Id { get; set; } = Guid.NewGuid().ToString("N");
    [JsonPropertyName("material")] public string Material { get; set; } = "";
    [JsonPropertyName("thickness_mm")] public int ThicknessMm { get; set; }
}

public sealed class FloorArchitectureRegistryVerification
{
    [JsonPropertyName("floor_id")] public string FloorId { get; set; } = "";
    [JsonPropertyName("shared_datum_id")] public string SharedDatumId { get; set; } = "";
    [JsonPropertyName("walls_complete")] public bool WallsComplete { get; set; }
    [JsonPropertyName("windows_complete")] public bool WindowsComplete { get; set; }
    [JsonPropertyName("doors_and_thresholds_complete")] public bool DoorsAndThresholdsComplete { get; set; }
    [JsonPropertyName("floor_build_up_complete")] public bool FloorBuildUpComplete { get; set; }
    [JsonPropertyName("allowed_pipe_axis_complete")] public bool AllowedPipeAxisComplete { get; set; }
    [JsonPropertyName("physical_verification")] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class InterfloorOpeningRegistryVerification
{
    [JsonPropertyName("from_floor_id")] public string FromFloorId { get; set; } = "";
    [JsonPropertyName("to_floor_id")] public string ToFloorId { get; set; } = "";
    [JsonPropertyName("shared_datum_id")] public string SharedDatumId { get; set; } = "";
    [JsonPropertyName("population_complete")] public bool PopulationComplete { get; set; }
    [JsonPropertyName("physical_verification")] public PhysicalVerification? PhysicalVerification { get; set; }
}

public sealed class RoutingRules
{
    [JsonPropertyName("pipe_outer_diameter_mm")] public int PipeOuterDiameterMm { get; set; } = 16;
    [JsonPropertyName("minimum_bend_radius_mm")] public int MinimumBendRadiusMm { get; set; } = 80;
    [JsonPropertyName("exterior_wall_spacing_mm")] public int ExteriorWallSpacingMm { get; set; } = 100;
    [JsonPropertyName("field_spacing_mm")] public int FieldSpacingMm { get; set; } = 200;
    [JsonPropertyName("maximum_parallel_transit_pipes_at_100mm")] public int MaximumParallelTransitPipesAt100Mm { get; set; } = 3;
    [JsonPropertyName("minimum_layer_axis_separation_mm")] public int MinimumLayerAxisSeparationMm { get; set; } = 25;
    [JsonPropertyName("minimum_layer_surface_clearance_mm")] public int MinimumLayerSurfaceClearanceMm { get; set; } = 5;
    [JsonPropertyName("transit_lane_geometry_verified")] public bool TransitLaneGeometryVerified { get; set; }
    [JsonPropertyName("exterior_edge_zone_applied")] public bool ExteriorEdgeZoneApplied { get; set; }
    [JsonPropertyName("owner_accepted_reference_required"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public bool? OwnerAcceptedReferenceRequired { get; set; }
}

public sealed class HomeAuraProject
{
    [JsonPropertyName("schema_version")] public string SchemaVersion { get; set; } = "1.0";
    [JsonPropertyName("kind")] public string Kind { get; set; } = "homeaura-manual-routing-example";
    [JsonPropertyName("units")] public string Units { get; set; } = "mm";
    [JsonPropertyName("grid_spacing_mm")] public int GridSpacingMm { get; set; } = 100;
    [JsonPropertyName("canvas_width_mm")] public int CanvasWidthMm { get; set; } = 12000;
    [JsonPropertyName("canvas_height_mm")] public int CanvasHeightMm { get; set; } = 8000;
    [JsonPropertyName("levels")] public List<FloorLevel> Levels { get; set; } = [];
    [JsonPropertyName("rooms")] public List<RoomZone> Rooms { get; set; } = [];
    [JsonPropertyName("exclusions")] public List<ExclusionZone> Exclusions { get; set; } = [];
    [JsonPropertyName("service_zones")] public List<ServiceZone> ServiceZones { get; set; } = [];
    [JsonPropertyName("floor_build_ups")] public List<FloorBuildUp> FloorBuildUps { get; set; } = [];
    [JsonPropertyName("routing_rules")] public RoutingRules RoutingRules { get; set; } = new();
    [JsonPropertyName("walls")] public List<WallSegment> Walls { get; set; } = [];
    [JsonPropertyName("windows")] public List<WindowOpening> Windows { get; set; } = [];
    [JsonPropertyName("shared_spatial_datum"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public SharedSpatialDatum? SharedSpatialDatum { get; set; }
    [JsonPropertyName("door_openings"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<DoorOpening>? DoorOpenings { get; set; }
    [JsonPropertyName("interfloor_openings"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<InterfloorOpening>? InterfloorOpenings { get; set; }
    [JsonPropertyName("floor_architecture_registry_verifications"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<FloorArchitectureRegistryVerification>? FloorArchitectureRegistryVerifications { get; set; }
    [JsonPropertyName("interfloor_opening_registry_verifications"), JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] public List<InterfloorOpeningRegistryVerification>? InterfloorOpeningRegistryVerifications { get; set; }
    [JsonPropertyName("collectors")] public List<Collector> Collectors { get; set; } = [];
    [JsonPropertyName("circuits")] public List<ManualCircuit> Circuits { get; set; } = [];
    [JsonPropertyName("training_metadata")] public TrainingMetadata Training { get; set; } = new();

    public static HomeAuraProject CreateBlank() => new();

    public HomeAuraProject DeepClone() => FromJson(ToJson());

    public string ToJson() => JsonSerializer.Serialize(this, JsonOptions);

    public static HomeAuraProject FromJson(string json)
    {
        using (var document = JsonDocument.Parse(json))
        {
            var root = document.RootElement;
            var declaresSchema11 = root.TryGetProperty("schema_version", out var schema) &&
                                   schema.ValueKind == JsonValueKind.String && schema.GetString() == "1.1";
            if (!declaresSchema11 && ContainsSchema11Member(root))
                throw new InvalidDataException("Физические данные этажей и проёмов требуют schema_version 1.1.");
        }
        var project = JsonSerializer.Deserialize<HomeAuraProject>(json, JsonOptions)
            ?? throw new InvalidDataException("Файл проекта пуст.");
        project.ValidateContract();
        return project;
    }

    private static bool ContainsSchema11Member(JsonElement root)
    {
        foreach (var name in new[]
                 {
                     "shared_spatial_datum", "door_openings", "interfloor_openings",
                     "floor_architecture_registry_verifications", "interfloor_opening_registry_verifications"
                 })
            if (root.TryGetProperty(name, out _)) return true;
        static bool AnyObjectHas(JsonElement rootElement, string collection, params string[] names)
        {
            if (!rootElement.TryGetProperty(collection, out var items) || items.ValueKind != JsonValueKind.Array) return false;
            return items.EnumerateArray().Any(item => item.ValueKind == JsonValueKind.Object &&
                names.Any(name => item.TryGetProperty(name, out _)));
        }
        return AnyObjectHas(root, "levels", "shared_datum_id", "finished_floor_elevation_mm_shared_datum") ||
               AnyObjectHas(root, "walls", "floor_id", "verified_finish_face_a_outline_mm", "verified_finish_face_b_outline_mm",
                   "base_elevation_mm_shared_datum", "top_elevation_mm_shared_datum", "physical_verification") ||
               AnyObjectHas(root, "windows", "floor_id", "verified_plan_outline_mm", "clear_width_mm",
                   "sill_elevation_mm_shared_datum", "physical_verification") ||
               AnyObjectHas(root, "floor_build_ups", "build_up_id", "layer_registry", "total_build_up_thickness_mm",
                   "allowed_pipe_axis_elevation_mm_shared_datum", "allowed_pipe_axis_tolerance_mm", "physical_verification");
    }

    public void ValidateContract()
    {
        if (SchemaVersion is not ("1.0" or "1.1") || Kind != "homeaura-manual-routing-example" || Units != "mm")
            throw new InvalidDataException("Это не проект HomeAura Manual Editor 1.0/1.1.");
        if (SchemaVersion == "1.0" && HasSchema11Data())
            throw new InvalidDataException("Физические данные этажей и проёмов требуют schema_version 1.1.");
        if (GridSpacingMm is not (50 or 100 or 200))
            throw new InvalidDataException("Редактор поддерживает сетку 50, 100 или 200 мм.");
        if (Training.Label is not ("DRAFT" or "ACCEPTED" or "REJECTED"))
            throw new InvalidDataException("Метка примера должна быть DRAFT, ACCEPTED или REJECTED.");
        if (CanvasWidthMm < 2000 || CanvasHeightMm < 2000 || CanvasWidthMm > 100_000 || CanvasHeightMm > 100_000)
            throw new InvalidDataException("Размер холста выходит за пределы редактора.");
        foreach (var point in AllPoints())
        {
            if (point.X < 0 || point.Y < 0 || point.X > CanvasWidthMm || point.Y > CanvasHeightMm)
                throw new InvalidDataException("Точка выходит за границы холста.");
        }
        foreach (var point in Collectors.Select(item => item.Position)
                     .Concat(Circuits.SelectMany(item => item.OrderedPoints)))
        {
            if (point.X % GridSpacingMm != 0 || point.Y % GridSpacingMm != 0)
                throw new InvalidDataException($"Оси труб и коллекторы должны лежать на сетке {GridSpacingMm} мм.");
        }
        var identifiers = Levels.Select(item => item.Id).Concat(Rooms.Select(item => item.Id)).Concat(Exclusions.Select(item => item.Id))
            .Concat(ServiceZones.Select(item => item.Id))
            .Concat(Walls.Select(item => item.Id)).Concat(Windows.Select(item => item.Id))
            .Concat((DoorOpenings ?? []).Select(item => item.Id))
            .Concat((InterfloorOpenings ?? []).Select(item => item.Id))
            .Concat(SharedSpatialDatum is null ? [] : new[] { SharedSpatialDatum.Id })
            .Concat(SharedSpatialDatum?.ControlPoints?.Select(item => item.Id) ?? [])
            .Concat(FloorBuildUps.Select(item => item.BuildUpId).OfType<string>())
            .Concat(FloorBuildUps.SelectMany(item => item.LayerRegistry ?? []).Select(item => item.Id))
            .Concat(Collectors.Select(item => item.Id)).Concat(Circuits.Select(item => item.Id)).ToList();
        if (identifiers.Any(string.IsNullOrWhiteSpace) || identifiers.Distinct(StringComparer.Ordinal).Count() != identifiers.Count)
            throw new InvalidDataException("Идентификаторы объектов должны быть непустыми и уникальными.");
        if (SchemaVersion == "1.1") ValidateSchema11Contract();
        foreach (var circuit in Circuits)
        {
            var collector = circuit.CollectorId is null ? null : Collectors.SingleOrDefault(item => item.Id == circuit.CollectorId);
            var serviceZone = circuit.ServiceZoneId is null ? null : ServiceZones.SingleOrDefault(item => item.Id == circuit.ServiceZoneId);
            if (circuit.CollectorId is not null && collector is null) throw new InvalidDataException($"{circuit.Name}: назначенный коллектор не найден.");
            if (circuit.ServiceZoneId is not null && serviceZone is null) throw new InvalidDataException($"{circuit.Name}: назначенная сервисная зона не найдена.");
            if (serviceZone is not null && serviceZone.CollectorId != circuit.CollectorId) throw new InvalidDataException($"{circuit.Name}: сервисная зона относится к другому коллектору.");
            if (circuit.SupplyPortIndex is < 0 || circuit.ReturnPortIndex is < 0)
                throw new InvalidDataException($"{circuit.Name}: индекс порта не может быть отрицательным.");
            if (collector is not null && (circuit.SupplyPortIndex >= collector.ConnectionCapacity || circuit.ReturnPortIndex >= collector.ConnectionCapacity))
                throw new InvalidDataException($"{circuit.Name}: назначенный порт отсутствует на коллекторе.");
            if (circuit.SupplyPortIndex is not null && circuit.SupplyPortIndex == circuit.ReturnPortIndex)
                throw new InvalidDataException($"{circuit.Name}: подача и обратка должны иметь разные порты.");
            if (collector?.HasPhysicalReferenceGeometry == true)
            {
                if (circuit.SupplyPortIndex is null && circuit.ReturnPortIndex is null)
                    throw new InvalidDataException($"{circuit.Name}: точный коллектор требует явного индекса подключения.");
                if (circuit.SystemRole == "FLOOR_HEATING_LOOP" && (circuit.SupplyPortIndex is null || circuit.ReturnPortIndex is null))
                    throw new InvalidDataException($"{circuit.Name}: полный контур точного коллектора требует точек подачи и обратки.");

                var physicalPoints = collector.ResolveConnectionPoints();
                var supplyPoint = circuit.SupplyPortIndex is null ? null : physicalPoints.FirstOrDefault(item => item.ConnectionIndex == circuit.SupplyPortIndex);
                var returnPoint = circuit.ReturnPortIndex is null ? null : physicalPoints.FirstOrDefault(item => item.ConnectionIndex == circuit.ReturnPortIndex);
                if (circuit.SupplyPortIndex is not null && supplyPoint?.Header != "SUPPLY")
                    throw new InvalidDataException($"{circuit.Name}: индекс подачи должен указывать на балку SUPPLY.");
                if (circuit.ReturnPortIndex is not null && returnPoint?.Header != "RETURN")
                    throw new InvalidDataException($"{circuit.Name}: индекс обратки должен указывать на балку RETURN.");
                if (supplyPoint is not null && returnPoint is not null && supplyPoint.LoopIndex != returnPoint.LoopIndex)
                    throw new InvalidDataException($"{circuit.Name}: подача и обратка должны относиться к одной паре коллектора.");
            }
            if (circuit.ConcealedServiceLengthMm is < 0 or > 100_000)
                throw new InvalidDataException($"{circuit.Name}: длина скрытого сервисного участка вне допустимого диапазона.");
            if (circuit.OutOfPlaneLengthMm is < 0 or > 100_000)
                throw new InvalidDataException($"{circuit.Name}: длина вертикального/внеплоскостного участка вне допустимого диапазона.");
            if (circuit.RoutingLayer is not ("HEATING_PLANE" or "LOWER_SERVICE_LAYER" or "VERTICAL_RISER_PROJECTION"))
                throw new InvalidDataException($"{circuit.Name}: неизвестный инженерный слой {circuit.RoutingLayer}.");
            if (circuit.SystemRole is not ("FLOOR_HEATING_LOOP" or "FLOOR_HEATING_AXIS" or "FLOOR_SERVICE_LEG" or "INTERFLOOR_SERVICE_LEG" or "RISER_PROJECTION"))
                throw new InvalidDataException($"{circuit.Name}: неизвестная роль трубы {circuit.SystemRole}.");
            if (circuit.AxisElevationMm is < -1000 or > 5000)
                throw new InvalidDataException($"{circuit.Name}: высотная отметка оси трубы вне допустимого диапазона.");
            if (circuit.OrderedPoints.Any(point => point.Z is < -1000 or > 5000))
                throw new InvalidDataException($"{circuit.Name}: Z-координата точки трубы вне допустимого диапазона.");
            var transitionSegments = new HashSet<int>();
            foreach (var transition in circuit.VerticalTransitions)
            {
                if (!transitionSegments.Add(transition.SegmentIndex))
                    throw new InvalidDataException($"{circuit.Name}: один сегмент не может иметь несколько вертикальных переходов.");
                if (transition.SegmentIndex < 0 || transition.SegmentIndex + 1 >= circuit.OrderedPoints.Count)
                    throw new InvalidDataException($"{circuit.Name}: вертикальный переход ссылается на отсутствующий сегмент.");
                if (transition.Kind != "S_BEND_R80")
                    throw new InvalidDataException($"{circuit.Name}: неизвестный тип вертикального перехода {transition.Kind}.");
                if (!double.IsFinite(transition.RadiusMm) || transition.RadiusMm is < 40 or > 500 ||
                    !double.IsFinite(transition.StartTangentLengthMm) || transition.StartTangentLengthMm is < 0 or > 100_000 ||
                    !double.IsFinite(transition.EndTangentLengthMm) || transition.EndTangentLengthMm is < 0 or > 100_000 ||
                    transition.ArcSamplesPerHalf is < 2 or > 64)
                    throw new InvalidDataException($"{circuit.Name}: параметры вертикального S-перехода вне допустимого диапазона.");

                var start = circuit.OrderedPoints[transition.SegmentIndex];
                var end = circuit.OrderedPoints[transition.SegmentIndex + 1];
                var startZ = start.Z ?? circuit.AxisElevationMm ?? 0;
                var endZ = end.Z ?? circuit.AxisElevationMm ?? 0;
                var verticalDelta = Math.Abs(endZ - startZ);
                var dx = end.X - start.X;
                var dy = end.Y - start.Y;
                var planLength = Math.Sqrt((double)dx * dx + (double)dy * dy);
                if (verticalDelta == 0 || planLength <= 0.001 || dx != 0 && dy != 0)
                    throw new InvalidDataException($"{circuit.Name}: S-переход требует ненулевой ортогональный плановый пробег и разные Z концов.");
                if (verticalDelta > 2 * transition.RadiusMm + 0.001)
                    throw new InvalidDataException($"{circuit.Name}: перепад S-перехода превышает геометрический предел 2R.");
                var angle = Math.Acos(1 - verticalDelta / (2 * transition.RadiusMm));
                var requiredArcProjection = 2 * transition.RadiusMm * Math.Sin(angle);
                var materializedProjection = transition.StartTangentLengthMm + requiredArcProjection + transition.EndTangentLengthMm;
                if (Math.Abs(materializedProjection - planLength) > 0.05)
                    throw new InvalidDataException($"{circuit.Name}: касательные и дуги S-перехода не замыкают плановую длину сегмента.");
            }
            if ((circuit.HeatingBodyStartIndex is null) != (circuit.HeatingBodyEndIndex is null))
                throw new InvalidDataException($"{circuit.Name}: начало и конец отопительного тела должны задаваться вместе.");
            if (circuit.HeatingBodyRanges.Count > 0 && circuit.HeatingBodyStartIndex is not null)
                throw new InvalidDataException($"{circuit.Name}: legacy-диапазон и heating_body_ranges нельзя задавать одновременно.");
            var heatingBodyRanges = circuit.HeatingBodyRanges.Count > 0
                ? circuit.HeatingBodyRanges
                : circuit.HeatingBodyStartIndex is not null
                    ? [new HeatingBodyRange { StartIndex = circuit.HeatingBodyStartIndex.Value, EndIndex = circuit.HeatingBodyEndIndex!.Value }]
                    : [];
            for (var rangeIndex = 0; rangeIndex < heatingBodyRanges.Count; rangeIndex++)
            {
                var range = heatingBodyRanges[rangeIndex];
                if (range.StartIndex < 0 || range.EndIndex <= range.StartIndex || range.EndIndex >= circuit.OrderedPoints.Count)
                    throw new InvalidDataException($"{circuit.Name}: диапазон отопительного тела выходит за ordered_points.");
                if (rangeIndex > 0 && range.StartIndex <= heatingBodyRanges[rangeIndex - 1].EndIndex)
                    throw new InvalidDataException($"{circuit.Name}: heating_body_ranges должны быть отсортированы и не пересекаться.");
            }
            if (heatingBodyRanges.Count > 0 && string.IsNullOrWhiteSpace(circuit.RoomId))
                throw new InvalidDataException($"{circuit.Name}: для отопительного тела должно быть назначено помещение.");
            if (circuit.RoomId is not null)
            {
                var room = Rooms.SingleOrDefault(item => item.Id == circuit.RoomId);
                if (room is null) throw new InvalidDataException($"{circuit.Name}: назначенное помещение не найдено.");
                if (!room.HeatingAllowed) throw new InvalidDataException($"{circuit.Name}: в назначенном помещении запрещён тёплый пол.");
            }
        }
        foreach (var zone in ServiceZones)
        {
            if (zone.CollectorId is not null && Collectors.All(item => item.Id != zone.CollectorId))
                throw new InvalidDataException($"{zone.Name}: назначенный коллектор не найден.");
            if (zone.ClearHeightMm is < 0 or > 1000 || zone.PipeCapacity is < 0 or > 200 ||
                zone.RequiredPipeCount is < 0 or > 200 || zone.RequiredPlanWidthMm is < 0 or > 10000)
                throw new InvalidDataException($"{zone.Name}: параметры сервисной зоны вне допустимого диапазона.");
            if (zone.PipeGeometryMaterialized && zone.RequiredPipeCount is not null && zone.PipeCapacity < zone.RequiredPipeCount)
                throw new InvalidDataException($"{zone.Name}: материализованная сервисная зона имеет недостаточную ёмкость.");
        }
        foreach (var buildUp in FloorBuildUps)
        {
            if (Levels.All(item => item.Id != buildUp.FloorId))
                throw new InvalidDataException("Конструкция пола ссылается на отсутствующий этаж.");
            if (buildUp.InstalledInsulationMm is < 0 or > 1000 || buildUp.RemainingHeightMm is < 0 or > 1000)
                throw new InvalidDataException("Толщина конструкции пола вне допустимого диапазона.");
        }
        if (RoutingRules.PipeOuterDiameterMm is < 8 or > 40 || RoutingRules.MinimumBendRadiusMm is < 40 or > 500 ||
            RoutingRules.ExteriorWallSpacingMm is < 50 or > 500 || RoutingRules.FieldSpacingMm is < 100 or > 500 ||
            RoutingRules.MaximumParallelTransitPipesAt100Mm is < 1 or > 3 || RoutingRules.MinimumLayerAxisSeparationMm is < 16 or > 100 ||
            RoutingRules.MinimumLayerSurfaceClearanceMm is < 1 or > 50)
            throw new InvalidDataException("Правила раскладки пола вне допустимого диапазона.");
        if (RoutingRules.MinimumLayerAxisSeparationMm < RoutingRules.PipeOuterDiameterMm + RoutingRules.MinimumLayerSurfaceClearanceMm)
            throw new InvalidDataException("Разнесение осей слоёв должно быть не меньше наружного диаметра трубы плюс поверхностный зазор.");
        foreach (var wall in Walls)
        {
            if (wall.ThicknessMm is < 50 or > 1000)
                throw new InvalidDataException("Толщина стены должна быть от 50 до 1000 мм.");
        }
        foreach (var window in Windows)
        {
            if (window.Start.X == window.End.X && window.Start.Y == window.End.Y)
                throw new InvalidDataException("Оконный проём должен иметь ненулевую длину.");
            if (window.WallId is not null && Walls.All(item => item.Id != window.WallId))
                throw new InvalidDataException("Оконный проём ссылается на отсутствующую стену.");
            if (window.WallId is not null)
            {
                var wall = Walls.Single(item => item.Id == window.WallId);
                if (DistanceToSegment(window.Start, wall.Start, wall.End) > 1 || DistanceToSegment(window.End, wall.Start, wall.End) > 1)
                    throw new InvalidDataException("Оба края оконного проёма должны лежать на указанной стене.");
            }
            if (window.SillHeightMm is < 0 or > 5000 || window.OpeningHeightMm is < 100 or > 5000)
                throw new InvalidDataException("Размеры оконного проёма вне допустимого диапазона.");
        }
        if (Collectors.Any(item => item.RotationDegrees is not (0 or 90 or 180 or 270)))
            throw new InvalidDataException("Коллектор можно поворачивать только с шагом 90 градусов.");
        if (Collectors.Any(item => item.ConnectionToleranceMm is < 100 or > 5000))
            throw new InvalidDataException("Допуск подключения к коллектору должен быть от 100 до 5000 мм.");
        if (Collectors.Any(item => item.PipeOutletDirection is not ("DOWN" or "UP" or "LEFT" or "RIGHT")))
            throw new InvalidDataException("Направление выходов коллектора должно быть DOWN, UP, LEFT или RIGHT.");
        if (Collectors.Any(item => item.ReferenceWidthMm is < 200 or > 3000 || item.ReferenceDepthMm is < 50 or > 1000 || item.ReferenceHeightMm is < 150 or > 2000))
            throw new InvalidDataException("Справочные габариты коллектора вне допустимого диапазона.");
        if (Collectors.Any(item => item.EquipmentStatus is not ("DRAFT_UNSELECTED" or "SELECTED_REFERENCE" or "INSTALLED")))
            throw new InvalidDataException("Статус оборудования коллектора неизвестен.");
        foreach (var collector in Collectors)
        {
            if (!collector.ExternalToPlan && collector.FloorId is not null && Levels.All(item => item.Id != collector.FloorId))
                throw new InvalidDataException($"{collector.Id}: этаж установки коллектора не найден.");
            if (!collector.ExternalToPlan && collector.MountingWallId is not null && Walls.All(item => item.Id != collector.MountingWallId))
                throw new InvalidDataException($"{collector.Id}: стена установки коллектора не найдена.");
            if (collector.LoopCount is < 1 or > 64 || collector.ConnectionPointCount is < 2 or > 128)
                throw new InvalidDataException($"{collector.Id}: число петель или точек подключения коллектора вне допустимого диапазона.");
            if (collector.HeaderPitchMm is < 20 or > 1000 || collector.LoopConnectionPitchMm is < 20 or > 300 || collector.ReferenceLengthMm is < 200 or > 3000)
                throw new InvalidDataException($"{collector.Id}: физические размеры коллектора вне допустимого диапазона.");
            var physicalFields = new[]
            {
                collector.LoopCount is not null,
                collector.ConnectionPointCount is not null,
                collector.HeaderPitchMm is not null,
                collector.LoopConnectionPitchMm is not null,
                collector.ReferenceLengthMm is not null,
            };
            if (physicalFields.Any(value => value) && physicalFields.Any(value => !value))
                throw new InvalidDataException($"{collector.Id}: точная геометрия коллектора задаётся только полным набором физических полей.");
            if (collector.ConnectionPointCount is not null && collector.ConnectionPointCount != collector.Ports)
                throw new InvalidDataException($"{collector.Id}: connection_point_count должен совпадать с совместимым полем ports.");
            if (collector.LoopCount is not null && collector.ConnectionPointCount is not null && collector.ConnectionPointCount != collector.LoopCount * 2)
                throw new InvalidDataException($"{collector.Id}: число точек подключения должно быть вдвое больше числа петель.");
            if (collector.LoopCount is not null && collector.LoopConnectionPitchMm is not null && collector.ReferenceLengthMm is not null &&
                (collector.LoopCount - 1) * collector.LoopConnectionPitchMm > collector.ReferenceLengthMm)
                throw new InvalidDataException($"{collector.Id}: ряд петлевых подключений не помещается в справочную длину коллектора.");
            if (collector.HeaderPitchMm is not null && collector.HeaderPitchMm > collector.ReferenceDepthMm)
                throw new InvalidDataException($"{collector.Id}: расстояние между балками не помещается в плановую глубину коллектора.");
            foreach (var value in new[] { collector.Manufacturer, collector.Model, collector.PartNumber })
                if (value is not null && string.IsNullOrWhiteSpace(value))
                    throw new InvalidDataException($"{collector.Id}: реквизиты оборудования не могут быть пустыми строками.");

            if (collector.HasPhysicalReferenceGeometry && !collector.ExternalToPlan)
            {
                if (collector.MountingWallId is null)
                    throw new InvalidDataException($"{collector.Id}: точный коллектор должен иметь монтажную стену.");
                var mountingWall = Walls.Single(item => item.Id == collector.MountingWallId);
                var dx = mountingWall.End.X - mountingWall.Start.X;
                var dy = mountingWall.End.Y - mountingWall.Start.Y;
                var wallLength = Math.Sqrt((double)dx * dx + (double)dy * dy);
                if (wallLength < 1)
                    throw new InvalidDataException($"{collector.Id}: монтажная стена коллектора не может иметь нулевую длину.");
                var unitX = dx / wallLength;
                var unitY = dy / wallLength;
                var relativeX = collector.Position.X - mountingWall.Start.X;
                var relativeY = collector.Position.Y - mountingWall.Start.Y;
                var along = relativeX * unitX + relativeY * unitY;
                var normalDistance = Math.Abs(relativeX * unitY - relativeY * unitX);
                var radians = collector.RotationDegrees * Math.PI / 180d;
                var alongHalfExtent = Math.Abs(Math.Cos(radians)) * collector.ReferenceLengthMm!.Value / 2d +
                                      Math.Abs(Math.Sin(radians)) * collector.ReferenceDepthMm / 2d;
                var normalHalfExtent = Math.Abs(Math.Sin(radians)) * collector.ReferenceLengthMm.Value / 2d +
                                       Math.Abs(Math.Cos(radians)) * collector.ReferenceDepthMm / 2d;
                if (along < alongHalfExtent - 0.001 || along > wallLength - alongHalfExtent + 0.001)
                    throw new InvalidDataException($"{collector.Id}: корпус точного коллектора выходит за торец монтажной стены.");
                if (normalDistance > mountingWall.ThicknessMm / 2d + normalHalfExtent + 1)
                    throw new InvalidDataException($"{collector.Id}: корпус точного коллектора пространственно оторван от монтажной стены.");
            }

            if (collector.ConnectionPoints is { Count: > 0 })
            {
                if (!collector.HasPhysicalReferenceGeometry)
                    throw new InvalidDataException($"{collector.Id}: явные точки подключения требуют полного набора физических размеров.");
                if (collector.ConnectionPoints.Count != collector.ConnectionPointCount)
                    throw new InvalidDataException($"{collector.Id}: число явных точек подключения не совпадает с connection_point_count.");

                var expected = collector.BuildReferenceConnectionPoints().OrderBy(item => item.ConnectionIndex).ToArray();
                var actual = collector.ConnectionPoints.OrderBy(item => item.ConnectionIndex).ToArray();
                if (actual.Select(item => item.ConnectionIndex).Distinct().Count() != actual.Length)
                    throw new InvalidDataException($"{collector.Id}: индексы точек подключения должны быть уникальными.");
                for (var index = 0; index < expected.Length; index++)
                {
                    var left = actual[index];
                    var right = expected[index];
                    var local = left.LocalPositionMm;
                    if (left.ConnectionIndex != right.ConnectionIndex || left.LoopIndex != right.LoopIndex || left.Header != right.Header ||
                        !double.IsFinite(local.X) || !double.IsFinite(local.Y) || !double.IsFinite(local.Z) ||
                        Math.Abs(local.X - right.LocalPositionMm.X) > 0.001 || Math.Abs(local.Y - right.LocalPositionMm.Y) > 0.001 || Math.Abs(local.Z) > 0.001)
                        throw new InvalidDataException($"{collector.Id}: явная геометрия точки подключения {left.ConnectionIndex} не соответствует шагам коллектора.");
                }
            }
        }
        var assignedPorts = Circuits.Where(item => item.CollectorId is not null)
            .SelectMany(item => new[] { (item.CollectorId!, item.SupplyPortIndex), (item.CollectorId!, item.ReturnPortIndex) })
            .Where(item => item.Item2 is not null).ToList();
        if (assignedPorts.Distinct().Count() != assignedPorts.Count)
            throw new InvalidDataException("Один порт коллектора назначен нескольким трубам.");
    }

    private bool HasSchema11Data() =>
        SharedSpatialDatum is not null || DoorOpenings is not null || InterfloorOpenings is not null ||
        FloorArchitectureRegistryVerifications is not null || InterfloorOpeningRegistryVerifications is not null ||
        Levels.Any(item => item.SharedDatumId is not null || item.FinishedFloorElevationMmSharedDatum is not null) ||
        Walls.Any(item => item.FloorId is not null || item.VerifiedFinishFaceAOutlineMm is not null ||
                          item.VerifiedFinishFaceBOutlineMm is not null || item.BaseElevationMmSharedDatum is not null ||
                          item.TopElevationMmSharedDatum is not null || item.PhysicalVerification is not null) ||
        Windows.Any(item => item.FloorId is not null || item.VerifiedPlanOutlineMm is not null ||
                            item.ClearWidthMm is not null || item.SillElevationMmSharedDatum is not null ||
                            item.PhysicalVerification is not null) ||
        FloorBuildUps.Any(item => item.BuildUpId is not null || item.LayerRegistry is not null ||
                                  item.TotalBuildUpThicknessMm is not null ||
                                  item.AllowedPipeAxisElevationMmSharedDatum is not null ||
                                  item.AllowedPipeAxisToleranceMm is not null || item.PhysicalVerification is not null);

    private void ValidateSchema11Contract()
    {
        var levelIds = Levels.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var wallById = Walls.ToDictionary(item => item.Id, StringComparer.Ordinal);
        var datumId = SharedSpatialDatum?.Id;

        if (Rooms.Any(item => !levelIds.Contains(item.FloorId)) ||
            Exclusions.Any(item => !levelIds.Contains(item.FloorId)) ||
            ServiceZones.Any(item => !levelIds.Contains(item.FloorId)))
            throw new InvalidDataException("Помещения, запретные и сервисные зоны schema 1.1 должны ссылаться на существующий этаж.");
        foreach (var collector in Collectors)
        {
            if (collector.FloorId is not null && !levelIds.Contains(collector.FloorId) ||
                collector.ServedFloorId is not null && !levelIds.Contains(collector.ServedFloorId))
                throw new InvalidDataException($"{collector.Id}: этаж установки или обслуживания коллектора не найден.");
            if (collector.MountingWallId is not null && wallById.TryGetValue(collector.MountingWallId, out var mountingWall) &&
                collector.FloorId is not null && mountingWall.FloorId != collector.FloorId)
                throw new InvalidDataException($"{collector.Id}: монтажная стена должна иметь тот же явно заданный этаж.");
        }

        if (SharedSpatialDatum is not null)
        {
            var controlPoints = SharedSpatialDatum.ControlPoints;
            if (string.IsNullOrWhiteSpace(SharedSpatialDatum.Id) ||
                SharedSpatialDatum.FloorIdsBoundToDatum is null ||
                controlPoints is null ||
                SharedSpatialDatum.FloorIdsBoundToDatum.Count == 0 ||
                SharedSpatialDatum.FloorIdsBoundToDatum.Any(item => !levelIds.Contains(item)) ||
                SharedSpatialDatum.FloorIdsBoundToDatum.Distinct(StringComparer.Ordinal).Count() != SharedSpatialDatum.FloorIdsBoundToDatum.Count)
                throw new InvalidDataException("Общая система координат должна иметь уникальный id и ссылаться только на существующие этажи.");
            ValidatePhysicalVerification(SharedSpatialDatum.PhysicalVerification, "Общая система координат");
            foreach (var point in controlPoints ?? [])
            {
                if (string.IsNullOrWhiteSpace(point.Id) || !levelIds.Contains(point.FloorId) ||
                    string.IsNullOrWhiteSpace(point.ReferenceDescription) ||
                    point.PositionMm is null || !double.IsFinite(point.PositionMm.X) ||
                    !double.IsFinite(point.PositionMm.Y) || !double.IsFinite(point.PositionMm.Z))
                    throw new InvalidDataException("Контрольная точка общей системы координат заполнена некорректно.");
            }
            controlPoints ??= [];
            if (SharedSpatialDatum.PhysicalVerification?.Status == "INDEPENDENTLY_VERIFIED" &&
                (controlPoints.Count == 0 ||
                 SharedSpatialDatum.FloorIdsBoundToDatum.Any(floorId =>
                     controlPoints.All(point => point.FloorId != floorId)) ||
                 string.IsNullOrWhiteSpace(SharedSpatialDatum.HorizontalOriginReference) ||
                 controlPoints.All(point => point.Id != SharedSpatialDatum.HorizontalOriginReference)))
                throw new InvalidDataException("Независимо проверенная общая система координат требует контрольную точку каждого этажа и разрешимый horizontal_origin_reference.");
        }

        foreach (var level in Levels)
        {
            if (level.SharedDatumId is not null && (datumId is null || level.SharedDatumId != datumId))
                throw new InvalidDataException($"{level.Id}: этаж ссылается на отсутствующую общую систему координат.");
            if (level.FinishedFloorElevationMmSharedDatum is < -10_000 or > 100_000)
                throw new InvalidDataException($"{level.Id}: отметка чистого пола вне допустимого диапазона.");
        }

        foreach (var wall in Walls)
        {
            if (wall.FloorId is not null && !levelIds.Contains(wall.FloorId))
                throw new InvalidDataException($"{wall.Id}: этаж стены не найден.");
            if ((wall.VerifiedFinishFaceAOutlineMm is null) != (wall.VerifiedFinishFaceBOutlineMm is null))
                throw new InvalidDataException($"{wall.Id}: обе проверенные грани стены должны задаваться вместе.");
            ValidateOptionalOutline(wall.VerifiedFinishFaceAOutlineMm, $"{wall.Id}: грань A стены", minimumPoints: 2);
            ValidateOptionalOutline(wall.VerifiedFinishFaceBOutlineMm, $"{wall.Id}: грань B стены", minimumPoints: 2);
            if ((wall.BaseElevationMmSharedDatum is null) != (wall.TopElevationMmSharedDatum is null) ||
                wall.BaseElevationMmSharedDatum is not null && wall.TopElevationMmSharedDatum <= wall.BaseElevationMmSharedDatum)
                throw new InvalidDataException($"{wall.Id}: нижняя и верхняя отметки стены заданы некорректно.");
            ValidatePhysicalVerification(wall.PhysicalVerification, wall.Id);
        }

        foreach (var window in Windows)
        {
            if (window.FloorId is not null && !levelIds.Contains(window.FloorId))
                throw new InvalidDataException($"{window.Id}: этаж окна не найден.");
            var parentWall = window.WallId is null ? null : wallById.GetValueOrDefault(window.WallId);
            if (parentWall is not null && window.FloorId is not null && parentWall.FloorId != window.FloorId)
                throw new InvalidDataException($"{window.Id}: явно заданное окно должно ссылаться на стену того же явно заданного этажа.");
            ValidateOptionalOutline(window.VerifiedPlanOutlineMm, $"{window.Id}: плановый контур окна", minimumPoints: 3);
            ValidateOpeningWidth(window.Id, window.Start, window.End, window.ClearWidthMm, window.PhysicalVerification);
            if (window.VerifiedPlanOutlineMm is not null &&
                !IsWallOpeningOutlineReady(parentWall, window.Start, window.End, window.VerifiedPlanOutlineMm,
                    window.ClearWidthMm, window.PhysicalVerification?.SurveyToleranceMm ?? 0))
                throw new InvalidDataException($"{window.Id}: проверенный контур окна не согласован с краями и телом стены.");
            if (window.SillElevationMmSharedDatum is not null && window.OpeningHeightMm is not null &&
                !IsWallOpeningVerticalEnvelopeReady(parentWall, window.SillElevationMmSharedDatum,
                    window.OpeningHeightMm, window.PhysicalVerification?.SurveyToleranceMm ?? 0))
                throw new InvalidDataException($"{window.Id}: вертикальный проём окна выходит за проверенные отметки стены.");
            ValidatePhysicalVerification(window.PhysicalVerification, window.Id);
        }

        foreach (var door in DoorOpenings ?? [])
        {
            if (!levelIds.Contains(door.FloorId))
                throw new InvalidDataException($"{door.Id}: этаж двери не найден.");
            if (!wallById.TryGetValue(door.WallId, out var wall) || wall.FloorId is null || wall.FloorId != door.FloorId)
                throw new InvalidDataException($"{door.Id}: дверь должна ссылаться на стену того же явно заданного этажа.");
            if (door.Start.X == door.End.X && door.Start.Y == door.End.Y ||
                DistanceToSegment(door.Start, wall.Start, wall.End) > 1 || DistanceToSegment(door.End, wall.Start, wall.End) > 1)
                throw new InvalidDataException($"{door.Id}: оба края двери должны образовывать ненулевой участок указанной стены.");
            ValidateOptionalOutline(door.VerifiedPlanOutlineMm, $"{door.Id}: плановый контур двери", minimumPoints: 3);
            ValidateOpeningWidth(door.Id, door.Start, door.End, door.ClearWidthMm, door.PhysicalVerification);
            if (door.VerifiedPlanOutlineMm is not null &&
                !IsWallOpeningOutlineReady(wall, door.Start, door.End, door.VerifiedPlanOutlineMm,
                    door.ClearWidthMm, door.PhysicalVerification?.SurveyToleranceMm ?? 0))
                throw new InvalidDataException($"{door.Id}: проверенный контур двери не согласован с краями и телом стены.");
            if (door.ClearHeightMm is < 100 or > 5000 || door.ThresholdHeightMm is < 0 or > 1000 ||
                door.ThresholdDisposition is not null and not ("NONE" or "FLUSH" or "RAISED"))
                throw new InvalidDataException($"{door.Id}: размеры или тип порога двери некорректны.");
            if (door.ThresholdDisposition is "NONE" or "FLUSH" && door.ThresholdHeightMm is > 0 ||
                door.ThresholdDisposition == "RAISED" &&
                (door.ThresholdHeightMm is not > 0 || door.ThresholdElevationMmSharedDatum is null) ||
                door.ThresholdDisposition is null &&
                (door.ThresholdHeightMm is not null || door.ThresholdElevationMmSharedDatum is not null))
                throw new InvalidDataException($"{door.Id}: высота порога не соответствует его типу.");
            var floor = Levels.Single(item => item.Id == door.FloorId);
            int? doorBottomElevation = door.ThresholdDisposition switch
            {
                "NONE" => floor.FinishedFloorElevationMmSharedDatum,
                "FLUSH" or "RAISED" => door.ThresholdElevationMmSharedDatum,
                _ => null,
            };
            if (doorBottomElevation is not null && door.ClearHeightMm is not null &&
                !IsWallOpeningVerticalEnvelopeReady(wall, doorBottomElevation, door.ClearHeightMm,
                    door.PhysicalVerification?.SurveyToleranceMm ?? 0))
                throw new InvalidDataException($"{door.Id}: вертикальный проём двери выходит за проверенные отметки стены.");
            ValidatePhysicalVerification(door.PhysicalVerification, door.Id);
        }
        ValidateWallOpeningOverlaps();

        foreach (var buildUp in FloorBuildUps)
        {
            if (buildUp.LayerRegistry is not null)
            {
                if (buildUp.LayerRegistry.Count == 0 || buildUp.LayerRegistry.Any(item =>
                        string.IsNullOrWhiteSpace(item.Id) || string.IsNullOrWhiteSpace(item.Material) || item.ThicknessMm is < 1 or > 2000) ||
                    buildUp.LayerRegistry.Select(item => item.Id).Distinct(StringComparer.Ordinal).Count() != buildUp.LayerRegistry.Count)
                    throw new InvalidDataException($"{buildUp.FloorId}: реестр слоёв пола заполнен некорректно.");
                if (buildUp.TotalBuildUpThicknessMm is not null &&
                    buildUp.TotalBuildUpThicknessMm != buildUp.LayerRegistry.Sum(item => item.ThicknessMm))
                    throw new InvalidDataException($"{buildUp.FloorId}: суммарная толщина не совпадает с реестром слоёв.");
            }
            if (buildUp.TotalBuildUpThicknessMm is not null &&
                buildUp.TotalBuildUpThicknessMm != buildUp.InstalledInsulationMm + buildUp.RemainingHeightMm)
                throw new InvalidDataException($"{buildUp.FloorId}: суммарная толщина не совпадает с migration-summary изоляции и оставшейся высоты.");
            if (buildUp.TotalBuildUpThicknessMm is < 1 or > 5000 ||
                buildUp.AllowedPipeAxisElevationMmSharedDatum is < -10_000 or > 100_000 ||
                buildUp.AllowedPipeAxisToleranceMm is < 1 or > 1000)
                throw new InvalidDataException($"{buildUp.FloorId}: физические параметры конструкции пола некорректны.");
            var level = Levels.Single(item => item.Id == buildUp.FloorId);
            if (buildUp.TotalBuildUpThicknessMm is not null && buildUp.AllowedPipeAxisElevationMmSharedDatum is not null &&
                buildUp.AllowedPipeAxisToleranceMm is not null && level.FinishedFloorElevationMmSharedDatum is not null)
            {
                var buildUpBottom = level.FinishedFloorElevationMmSharedDatum.Value - buildUp.TotalBuildUpThicknessMm.Value;
                if (buildUp.AllowedPipeAxisElevationMmSharedDatum.Value - buildUp.AllowedPipeAxisToleranceMm.Value < buildUpBottom ||
                    buildUp.AllowedPipeAxisElevationMmSharedDatum.Value + buildUp.AllowedPipeAxisToleranceMm.Value >
                    level.FinishedFloorElevationMmSharedDatum.Value)
                    throw new InvalidDataException($"{buildUp.FloorId}: допуск оси трубы выходит за проверенный пирог пола.");
            }
            ValidatePhysicalVerification(buildUp.PhysicalVerification, $"{buildUp.FloorId}: конструкция пола");
        }

        foreach (var opening in InterfloorOpenings ?? [])
        {
            if (opening.OpeningType is not ("SLAB_OPENING" or "CORE_PENETRATION" or "SHAFT" or "STAIR_VOID") ||
                !levelIds.Contains(opening.FromFloorId) || !levelIds.Contains(opening.ToFloorId) ||
                opening.FromFloorId == opening.ToFloorId)
                throw new InvalidDataException($"{opening.Id}: тип или пара этажей межэтажного проёма некорректны.");
            if (datumId is null || opening.SharedDatumId != datumId ||
                opening.FromFloorFace is null || opening.ToFloorFace is null ||
                opening.FromFloorFace.FloorId != opening.FromFloorId || opening.ToFloorFace.FloorId != opening.ToFloorId)
                throw new InvalidDataException($"{opening.Id}: грани проёма должны быть привязаны к общей системе координат и своим этажам.");
            if (opening.CenterlineMmSharedDatum?.Any(point => !double.IsFinite(point.X) || !double.IsFinite(point.Y) ||
                    point.X < 0 || point.Y < 0 || point.X > CanvasWidthMm || point.Y > CanvasHeightMm) == true)
                throw new InvalidDataException($"{opening.Id}: осевая полилиния выходит за границы холста.");
            var independentlyVerified = opening.PhysicalVerification?.Status == "INDEPENDENTLY_VERIFIED";
            ValidateOptionalOutline(opening.FromFloorFace.VerifiedPlanOutlineMm is { Count: > 0 } fromOutline ? fromOutline : null,
                $"{opening.Id}: нижняя грань проёма", minimumPoints: 3, required: independentlyVerified);
            ValidateOptionalOutline(opening.ToFloorFace.VerifiedPlanOutlineMm is { Count: > 0 } toOutline ? toOutline : null,
                $"{opening.Id}: верхняя грань проёма", minimumPoints: 3, required: independentlyVerified);
            ValidateElevationPair(opening.FromFloorFace.FaceElevationMinMmSharedDatum,
                opening.FromFloorFace.FaceElevationMaxMmSharedDatum, $"{opening.Id}: отметки первой грани");
            ValidateElevationPair(opening.ToFloorFace.FaceElevationMinMmSharedDatum,
                opening.ToFloorFace.FaceElevationMaxMmSharedDatum, $"{opening.Id}: отметки второй грани");
            if (opening.ClearDepthMm is < 1 or > 10_000 ||
                (opening.ClearBottomElevationMmSharedDatum is null) != (opening.ClearTopElevationMmSharedDatum is null) ||
                opening.ClearBottomElevationMmSharedDatum is not null &&
                opening.ClearTopElevationMmSharedDatum <= opening.ClearBottomElevationMmSharedDatum)
                throw new InvalidDataException($"{opening.Id}: глубина или высотный интервал проёма некорректны.");
            ValidateOpeningShapeAndAxis(opening, independentlyVerified);
            ValidatePhysicalVerification(opening.PhysicalVerification, opening.Id);
            ValidateStructuralDisposition(opening.StructuralDisposition, opening.Id);
            ValidateStructuralOpeningEnvelope(opening);
        }

        var floorRegistryKeys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var registry in FloorArchitectureRegistryVerifications ?? [])
        {
            if (!levelIds.Contains(registry.FloorId) || datumId is null || registry.SharedDatumId != datumId ||
                !floorRegistryKeys.Add(registry.FloorId))
                throw new InvalidDataException("Реестр проверки архитектуры этажа имеет неверную ссылку или дубликат.");
            ValidatePhysicalVerification(registry.PhysicalVerification, $"{registry.FloorId}: реестр архитектуры");
        }

        var pairRegistryKeys = new HashSet<string>(StringComparer.Ordinal);
        foreach (var registry in InterfloorOpeningRegistryVerifications ?? [])
        {
            if (!levelIds.Contains(registry.FromFloorId) || !levelIds.Contains(registry.ToFloorId) ||
                registry.FromFloorId == registry.ToFloorId || datumId is null || registry.SharedDatumId != datumId)
                throw new InvalidDataException("Реестр межэтажных проёмов имеет неверную пару этажей или datum.");
            var key = string.CompareOrdinal(registry.FromFloorId, registry.ToFloorId) < 0
                ? $"{registry.FromFloorId}\0{registry.ToFloorId}"
                : $"{registry.ToFloorId}\0{registry.FromFloorId}";
            if (!pairRegistryKeys.Add(key)) throw new InvalidDataException("Пара этажей реестра межэтажных проёмов продублирована.");
            ValidatePhysicalVerification(registry.PhysicalVerification, $"{registry.FromFloorId}/{registry.ToFloorId}: реестр проёмов");
        }
    }

    private static void ValidatePhysicalVerification(PhysicalVerification? verification, string owner)
    {
        if (verification is null) return;
        if (verification.Status is not ("UNVERIFIED" or "MEASURED" or "INDEPENDENTLY_VERIFIED") ||
            verification.SurveyToleranceMm is not null &&
            (!double.IsFinite(verification.SurveyToleranceMm.Value) || verification.SurveyToleranceMm is <= 0 or > 1000))
            throw new InvalidDataException($"{owner}: статус или допуск физической проверки некорректны.");
        foreach (var values in new[] { verification.SourceDocumentPaths, verification.PhotoEvidencePaths, verification.IndependentVerificationRecordIds })
            if (values is null || values.Any(string.IsNullOrWhiteSpace))
                throw new InvalidDataException($"{owner}: ссылки доказательств не могут быть null или пустыми строками.");
        if (verification.MeasurementDate is not null &&
            !DateOnly.TryParseExact(verification.MeasurementDate, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out _))
            throw new InvalidDataException($"{owner}: дата измерения должна иметь формат yyyy-MM-dd.");
        var measured = verification.Status is "MEASURED" or "INDEPENDENTLY_VERIFIED";
        if (measured &&
            (string.IsNullOrWhiteSpace(verification.MeasurementSourceType) ||
             string.IsNullOrWhiteSpace(verification.MeasuredBy) || string.IsNullOrWhiteSpace(verification.MeasurementDate) ||
             verification.SurveyToleranceMm is null ||
             string.IsNullOrWhiteSpace(verification.SourceDocumentId) && verification.SourceDocumentPaths.Count == 0 ||
             verification.PhotoEvidencePaths.Count == 0))
            throw new InvalidDataException($"{owner}: измеренный объект требует источник, исполнителя, дату, допуск и фото.");
        if (verification.Status == "INDEPENDENTLY_VERIFIED" && verification.IndependentVerificationRecordIds.Count == 0)
            throw new InvalidDataException($"{owner}: независимая проверка требует отдельную запись проверки.");
    }

    private static void ValidateOpeningShapeAndAxis(InterfloorOpening opening, bool independentlyVerified)
    {
        if (opening.ShapeType is not null and not ("CIRCULAR" or "RECTANGULAR" or "NONRECTANGULAR") ||
            opening.ClearAxisDefinitionMethod is not null and not ("FACE_CENTERS" or "CENTERLINE_POLYLINE" or "VECTOR_AND_ORIENTATION") ||
            opening.ClearAxisDirection is not null and not ("FROM_TO" or "TO_FROM"))
            throw new InvalidDataException($"{opening.Id}: тип формы или способ задания оси неизвестен.");
        foreach (var dimension in new[] { opening.ClearDiameterMm, opening.ClearWidthMm, opening.ClearLengthMm })
            if (dimension is not null && (!double.IsFinite(dimension.Value) || dimension is <= 0 or > 20_000))
                throw new InvalidDataException($"{opening.Id}: размер поперечного сечения проёма некорректен.");
        if (opening.ClearAxisAzimuthDegreesSharedDatum is not null &&
            (!double.IsFinite(opening.ClearAxisAzimuthDegreesSharedDatum.Value) || opening.ClearAxisAzimuthDegreesSharedDatum is < 0 or >= 360) ||
            opening.ClearAxisInclinationDegreesSharedDatum is not null &&
            (!double.IsFinite(opening.ClearAxisInclinationDegreesSharedDatum.Value) || opening.ClearAxisInclinationDegreesSharedDatum is < -90 or > 90) ||
            opening.ClearAxisOrientationToleranceDegrees is not null &&
            (!double.IsFinite(opening.ClearAxisOrientationToleranceDegrees.Value) || opening.ClearAxisOrientationToleranceDegrees is <= 0 or > 10))
            throw new InvalidDataException($"{opening.Id}: угловая ориентация оси проёма некорректна.");

        static bool Finite(Point3Mm? point) => point is not null &&
            double.IsFinite(point.X) && double.IsFinite(point.Y) && double.IsFinite(point.Z);
        static double Distance3(Point3Mm first, Point3Mm second) => Math.Sqrt(
            Math.Pow(first.X - second.X, 2) + Math.Pow(first.Y - second.Y, 2) + Math.Pow(first.Z - second.Z, 2));
        static double NormalizeAzimuth(double degrees) => (degrees % 360 + 360) % 360;
        static double AngularDifference(double first, double second)
        {
            var difference = Math.Abs(NormalizeAzimuth(first) - NormalizeAzimuth(second));
            return Math.Min(difference, 360 - difference);
        }
        static (double Width, double Length) AxisAlignedBounds(IReadOnlyList<PointMm> outline) =>
            (outline.Max(point => point.X) - outline.Min(point => point.X),
             outline.Max(point => point.Y) - outline.Min(point => point.Y));
        static bool RectangularFace(IReadOnlyList<PointMm> outline, double allowance)
        {
            var vertices = outline.ToList();
            if (vertices.Count > 1 && PointDistance(vertices[0], vertices[^1]) <= Math.Max(0.001, allowance))
                vertices.RemoveAt(vertices.Count - 1);
            if (vertices.Count != 4) return false;
            var minX = vertices.Min(point => point.X); var maxX = vertices.Max(point => point.X);
            var minY = vertices.Min(point => point.Y); var maxY = vertices.Max(point => point.Y);
            if (maxX - minX <= allowance || maxY - minY <= allowance) return false;
            var corners = new[]
            {
                new PointMm(minX, minY), new PointMm(maxX, minY),
                new PointMm(maxX, maxY), new PointMm(minX, maxY),
            };
            return corners.All(corner => vertices.Any(vertex => PointDistance(corner, vertex) <= allowance + 0.001));
        }
        static bool CircularFace(IReadOnlyList<PointMm> outline, Point3Mm center, double diameter, double allowance)
        {
            var vertices = outline.ToList();
            if (vertices.Count > 1 && PointDistance(vertices[0], vertices[^1]) <= Math.Max(0.001, allowance))
                vertices.RemoveAt(vertices.Count - 1);
            if (vertices.DistinctBy(point => (point.X, point.Y)).Count() < 8) return false;
            var radius = diameter / 2;
            return vertices.All(point =>
                Math.Abs(Math.Sqrt(Math.Pow(point.X - center.X, 2) + Math.Pow(point.Y - center.Y, 2)) - radius) <= allowance + 0.001);
        }
        static (double X, double Y)? PolygonCentroid(IReadOnlyList<PointMm> outline)
        {
            var areaTimesTwo = 0d; var xSum = 0d; var ySum = 0d;
            for (var index = 0; index < outline.Count; index++)
            {
                var next = outline[(index + 1) % outline.Count];
                var cross = (double)outline[index].X * next.Y - (double)next.X * outline[index].Y;
                areaTimesTwo += cross;
                xSum += (outline[index].X + next.X) * cross;
                ySum += (outline[index].Y + next.Y) * cross;
            }
            return Math.Abs(areaTimesTwo) <= 0.001 ? null : (xSum / (3 * areaTimesTwo), ySum / (3 * areaTimesTwo));
        }

        var fromCenter = opening.FromFloorFace.CenterMmSharedDatum;
        var toCenter = opening.ToFloorFace.CenterMmSharedDatum;
        if (fromCenter is not null && !Finite(fromCenter) || toCenter is not null && !Finite(toCenter))
            throw new InvalidDataException($"{opening.Id}: центр грани содержит нечисловую координату.");
        if (opening.CenterlineMmSharedDatum is not null)
        {
            if (opening.CenterlineMmSharedDatum.Count < 2 || opening.CenterlineMmSharedDatum.Any(point => !Finite(point)) ||
                opening.CenterlineMmSharedDatum.Zip(opening.CenterlineMmSharedDatum.Skip(1), Distance3).Any(length => length <= 0.001))
                throw new InvalidDataException($"{opening.Id}: осевая линия проёма вырождена.");
        }
        if (opening.ClearAxisVector is not null &&
            (!Finite(opening.ClearAxisVector) || Math.Sqrt(Math.Pow(opening.ClearAxisVector.X, 2) +
                Math.Pow(opening.ClearAxisVector.Y, 2) + Math.Pow(opening.ClearAxisVector.Z, 2)) <= 0.001))
            throw new InvalidDataException($"{opening.Id}: вектор оси проёма вырожден.");

        var tolerance = opening.PhysicalVerification?.SurveyToleranceMm ?? 0;
        var fromOutline = opening.FromFloorFace.VerifiedPlanOutlineMm ?? [];
        var toOutline = opening.ToFloorFace.VerifiedPlanOutlineMm ?? [];
        static bool CenterWithinBounds(Point3Mm center, IReadOnlyList<PointMm> outline, double allowance) =>
            center.X >= outline.Min(point => point.X) - allowance && center.X <= outline.Max(point => point.X) + allowance &&
            center.Y >= outline.Min(point => point.Y) - allowance && center.Y <= outline.Max(point => point.Y) + allowance;

        if (opening.ShapeType == "CIRCULAR" && (opening.ClearWidthMm is not null || opening.ClearLengthMm is not null) ||
            opening.ShapeType == "RECTANGULAR" && opening.ClearDiameterMm is not null ||
            opening.ShapeType == "NONRECTANGULAR" &&
            (opening.ClearDiameterMm is not null || opening.ClearWidthMm is not null || opening.ClearLengthMm is not null))
            throw new InvalidDataException($"{opening.Id}: скалярные размеры противоречат объявленной форме проёма.");

        var outlinesReady = fromOutline.Count >= 3 && toOutline.Count >= 3;
        if (opening.ShapeType == "CIRCULAR")
        {
            if (independentlyVerified && opening.ClearDiameterMm is null)
                throw new InvalidDataException($"{opening.Id}: независимо проверенный круглый проём требует диаметр.");
            if (independentlyVerified && opening.ClearDiameterMm is not null &&
                (!CircularFace(fromOutline, fromCenter!, opening.ClearDiameterMm.Value, tolerance) ||
                 !CircularFace(toOutline, toCenter!, opening.ClearDiameterMm.Value, tolerance)))
                throw new InvalidDataException($"{opening.Id}: каждая грань CIRCULAR требует не менее восьми проверенных точек на объявленной окружности.");
            if (opening.ClearDiameterMm is not null && outlinesReady &&
                new[] { AxisAlignedBounds(fromOutline), AxisAlignedBounds(toOutline) }.Any(item =>
                    Math.Abs(item.Width - opening.ClearDiameterMm.Value) > tolerance ||
                    Math.Abs(item.Length - opening.ClearDiameterMm.Value) > tolerance))
                throw new InvalidDataException($"{opening.Id}: круглая форма не согласована с диаметром и контурами.");
        }
        else if (opening.ShapeType == "RECTANGULAR")
        {
            if (independentlyVerified && (opening.ClearWidthMm is null || opening.ClearLengthMm is null))
                throw new InvalidDataException($"{opening.Id}: независимо проверенный прямоугольный проём требует ширину и длину.");
            if (independentlyVerified && (!RectangularFace(fromOutline, tolerance) || !RectangularFace(toOutline, tolerance)))
                throw new InvalidDataException($"{opening.Id}: каждая грань RECTANGULAR должна быть четырёхугольником с прямыми углами и параллельными противоположными сторонами.");
            if (opening.ClearWidthMm is not null && opening.ClearLengthMm is not null && outlinesReady)
            {
                foreach (var dimensions in new[] { AxisAlignedBounds(fromOutline), AxisAlignedBounds(toOutline) })
                    if (Math.Abs(dimensions.Width - opening.ClearWidthMm.Value) > tolerance ||
                        Math.Abs(dimensions.Length - opening.ClearLengthMm.Value) > tolerance)
                        throw new InvalidDataException($"{opening.Id}: каждая грань прямоугольного проёма должна совпадать с объявленными шириной и длиной.");
            }
        }

        if (fromCenter is not null && fromOutline.Count >= 3 && !CenterWithinBounds(fromCenter, fromOutline, tolerance) ||
            toCenter is not null && toOutline.Count >= 3 && !CenterWithinBounds(toCenter, toOutline, tolerance))
            throw new InvalidDataException($"{opening.Id}: центр грани лежит вне её проверенного контура.");
        if (independentlyVerified)
        {
            foreach (var (outline, center) in new[] { (fromOutline, fromCenter!), (toOutline, toCenter!) })
            {
                var derivedCenter = opening.ShapeType == "NONRECTANGULAR"
                    ? PolygonCentroid(outline)
                    : ((double X, double Y)?)(
                        (outline.Min(point => point.X) + outline.Max(point => point.X)) / 2d,
                        (outline.Min(point => point.Y) + outline.Max(point => point.Y)) / 2d);
                if (derivedCenter is null || Math.Abs(center.X - derivedCenter.Value.X) > tolerance ||
                    Math.Abs(center.Y - derivedCenter.Value.Y) > tolerance)
                    throw new InvalidDataException($"{opening.Id}: центр грани не совпадает с центром проверенного контура.");
            }
        }
        static bool CenterElevationPass(Point3Mm? center, InterfloorOpeningFace face, double allowance) =>
            center is null || face.FaceElevationMinMmSharedDatum is null ||
            center.Z >= face.FaceElevationMinMmSharedDatum - allowance && center.Z <= face.FaceElevationMaxMmSharedDatum + allowance;
        if (!CenterElevationPass(fromCenter, opening.FromFloorFace, tolerance) ||
            !CenterElevationPass(toCenter, opening.ToFloorFace, tolerance))
            throw new InvalidDataException($"{opening.Id}: центр грани не согласован с её высотным диапазоном.");

        var hasVectorRepresentation = opening.ClearAxisVector is not null || opening.ClearAxisAzimuthDegreesSharedDatum is not null ||
            opening.ClearAxisInclinationDegreesSharedDatum is not null || opening.ClearAxisOrientationToleranceDegrees is not null ||
            opening.ClearAxisDirection is not null;
        if (opening.ClearAxisDefinitionMethod == "FACE_CENTERS" &&
                (opening.CenterlineMmSharedDatum is not null || hasVectorRepresentation) ||
            opening.ClearAxisDefinitionMethod == "CENTERLINE_POLYLINE" && hasVectorRepresentation ||
            opening.ClearAxisDefinitionMethod == "VECTOR_AND_ORIENTATION" && opening.CenterlineMmSharedDatum is not null)
            throw new InvalidDataException($"{opening.Id}: проём содержит неиспользуемое второе представление оси.");

        if (independentlyVerified &&
            (opening.ShapeType is null || opening.ClearAxisDefinitionMethod is null || !Finite(fromCenter) || !Finite(toCenter) ||
             !outlinesReady || opening.FromFloorFace.FaceElevationMinMmSharedDatum is null ||
             opening.FromFloorFace.FaceElevationMaxMmSharedDatum is null ||
             opening.ToFloorFace.FaceElevationMinMmSharedDatum is null ||
             opening.ToFloorFace.FaceElevationMaxMmSharedDatum is null || opening.ClearDepthMm is null ||
             opening.ClearBottomElevationMmSharedDatum is null || opening.ClearTopElevationMmSharedDatum is null))
            throw new InvalidDataException($"{opening.Id}: независимо проверенный проём требует форму, обе грани, центры, ось, глубину и отметки.");

        double? centerDistance = fromCenter is not null && toCenter is not null ? Distance3(fromCenter, toCenter) : null;
        if (centerDistance is <= 0.001)
            throw new InvalidDataException($"{opening.Id}: центры граней проёма совпадают.");

        if (opening.ClearBottomElevationMmSharedDatum is not null && opening.ClearTopElevationMmSharedDatum is not null &&
            opening.ClearDepthMm is not null)
        {
            var bottom = opening.ClearBottomElevationMmSharedDatum.Value;
            var top = opening.ClearTopElevationMmSharedDatum.Value;
            var elevationSpan = opening.ClearTopElevationMmSharedDatum.Value - opening.ClearBottomElevationMmSharedDatum.Value;
            if (elevationSpan > opening.ClearDepthMm.Value + tolerance)
                throw new InvalidDataException($"{opening.Id}: высотный пролёт проёма не может превышать длину его оси.");
            if (new[] { opening.FromFloorFace, opening.ToFloorFace }.Any(face =>
                    face.FaceElevationMinMmSharedDatum is not null &&
                    face.FaceElevationMinMmSharedDatum < bottom - tolerance ||
                    face.FaceElevationMaxMmSharedDatum is not null &&
                    face.FaceElevationMaxMmSharedDatum > top + tolerance))
                throw new InvalidDataException($"{opening.Id}: диапазон отметок грани выходит за объявленный высотный интервал проёма.");
            if (fromCenter is not null && toCenter is not null &&
                (Math.Abs(Math.Min(fromCenter.Z, toCenter.Z) - opening.ClearBottomElevationMmSharedDatum.Value) > tolerance ||
                 Math.Abs(Math.Max(fromCenter.Z, toCenter.Z) - opening.ClearTopElevationMmSharedDatum.Value) > tolerance))
                throw new InvalidDataException($"{opening.Id}: общий высотный интервал не совпадает с центрами граней проёма.");
        }

        if (opening.ClearAxisDefinitionMethod == "FACE_CENTERS")
        {
            if (centerDistance is not null && opening.ClearDepthMm is not null &&
                Math.Abs(centerDistance.Value - opening.ClearDepthMm.Value) > tolerance)
                throw new InvalidDataException($"{opening.Id}: глубина не согласована с центрами граней.");
            return;
        }
        if (opening.ClearAxisDefinitionMethod == "CENTERLINE_POLYLINE")
        {
            if (independentlyVerified && opening.CenterlineMmSharedDatum is not { Count: >= 2 })
                throw new InvalidDataException($"{opening.Id}: независимо проверенный проём требует осевую полилинию.");
            if (opening.CenterlineMmSharedDatum is { Count: >= 2 } centerline)
            {
                if (centerline.Any(point => !Finite(point)))
                    throw new InvalidDataException($"{opening.Id}: осевая полилиния содержит некорректную точку.");
                if (fromCenter is not null && Distance3(centerline[0], fromCenter) > tolerance ||
                    toCenter is not null && Distance3(centerline[^1], toCenter) > tolerance)
                    throw new InvalidDataException($"{opening.Id}: осевая полилиния не замыкается на центры граней.");
                if (opening.ClearBottomElevationMmSharedDatum is not null &&
                    opening.ClearTopElevationMmSharedDatum is not null &&
                    centerline.Any(point => point.Z < opening.ClearBottomElevationMmSharedDatum.Value - tolerance ||
                                            point.Z > opening.ClearTopElevationMmSharedDatum.Value + tolerance))
                    throw new InvalidDataException($"{opening.Id}: осевая полилиния выходит за объявленный высотный интервал проёма.");
                var centerlineLength = centerline.Zip(centerline.Skip(1), Distance3).Sum();
                if (opening.ClearDepthMm is not null && Math.Abs(centerlineLength - opening.ClearDepthMm.Value) > tolerance)
                    throw new InvalidDataException($"{opening.Id}: глубина не совпадает с длиной принятой осевой полилинии.");
            }
            return;
        }
        if (opening.ClearAxisDefinitionMethod != "VECTOR_AND_ORIENTATION") return;
        if (independentlyVerified && (opening.ClearAxisVector is null || opening.ClearAxisDirection is null ||
            opening.ClearAxisAzimuthDegreesSharedDatum is null || opening.ClearAxisInclinationDegreesSharedDatum is null ||
            opening.ClearAxisOrientationToleranceDegrees is null))
            throw new InvalidDataException($"{opening.Id}: векторный способ требует ненулевой вектор, азимут, наклон, допуск и направление.");
        if (opening.ClearAxisVector is null) return;
        var vector = opening.ClearAxisVector;
        var vectorLength = Math.Sqrt(vector.X * vector.X + vector.Y * vector.Y + vector.Z * vector.Z);
        var vectorAzimuth = NormalizeAzimuth(Math.Atan2(vector.Y, vector.X) * 180 / Math.PI);
        var vectorInclination = Math.Atan2(vector.Z, Math.Sqrt(vector.X * vector.X + vector.Y * vector.Y)) * 180 / Math.PI;
        if (opening.ClearAxisAzimuthDegreesSharedDatum is not null && opening.ClearAxisOrientationToleranceDegrees is not null &&
                AngularDifference(vectorAzimuth, opening.ClearAxisAzimuthDegreesSharedDatum.Value) > opening.ClearAxisOrientationToleranceDegrees ||
            opening.ClearAxisInclinationDegreesSharedDatum is not null && opening.ClearAxisOrientationToleranceDegrees is not null &&
                Math.Abs(vectorInclination - opening.ClearAxisInclinationDegreesSharedDatum.Value) > opening.ClearAxisOrientationToleranceDegrees)
            throw new InvalidDataException($"{opening.Id}: вектор оси не согласован с объявленной ориентацией.");
        if (centerDistance is not null)
        {
            var displacement = new Point3Mm(toCenter!.X - fromCenter!.X, toCenter.Y - fromCenter.Y, toCenter.Z - fromCenter.Z);
            var dot = displacement.X * vector.X + displacement.Y * vector.Y + displacement.Z * vector.Z;
            var cosine = Math.Clamp(Math.Abs(dot) / (centerDistance.Value * vectorLength), -1, 1);
            var alignmentErrorDegrees = Math.Acos(cosine) * 180 / Math.PI;
            if (opening.ClearAxisOrientationToleranceDegrees is not null &&
                    alignmentErrorDegrees > opening.ClearAxisOrientationToleranceDegrees ||
                opening.ClearAxisDirection == "FROM_TO" && dot <= 0 || opening.ClearAxisDirection == "TO_FROM" && dot >= 0 ||
                opening.ClearDepthMm is not null && Math.Abs(centerDistance.Value - opening.ClearDepthMm.Value) > tolerance)
                throw new InvalidDataException($"{opening.Id}: вектор оси не согласован с центрами, направлением или глубиной.");
        }
    }

    private static void ValidateStructuralDisposition(StructuralDisposition? disposition, string owner)
    {
        if (disposition is null) return;
        if (disposition.Status is not ("UNREVIEWED" or "EXISTING_OPENING_ACCEPTED" or "NEW_OPENING_APPROVED" or "PROHIBITED") ||
            disposition.AuthorityDocumentPaths is null || disposition.ApprovedClearOutlineMm is null || disposition.Conditions is null ||
            disposition.AuthorityDocumentPaths.Any(string.IsNullOrWhiteSpace) || disposition.Conditions.Any(string.IsNullOrWhiteSpace))
            throw new InvalidDataException($"{owner}: конструктивное решение заполнено некорректно.");
        ValidateOptionalOutline(disposition.ApprovedClearOutlineMm.Count == 0 ? null : disposition.ApprovedClearOutlineMm,
            $"{owner}: разрешённый конструктивом контур", minimumPoints: 3);
        if (disposition.ApprovalDate is not null &&
            !DateOnly.TryParseExact(disposition.ApprovalDate, "yyyy-MM-dd", CultureInfo.InvariantCulture,
                DateTimeStyles.None, out _))
            throw new InvalidDataException($"{owner}: дата конструктивного решения должна иметь формат yyyy-MM-dd.");
        if (disposition.Status is "EXISTING_OPENING_ACCEPTED" or "NEW_OPENING_APPROVED" &&
            (string.IsNullOrWhiteSpace(disposition.RecordId) || string.IsNullOrWhiteSpace(disposition.AuthorityName) ||
             string.IsNullOrWhiteSpace(disposition.AuthorityDocumentId) && disposition.AuthorityDocumentPaths.Count == 0 ||
             string.IsNullOrWhiteSpace(disposition.ApprovalDate) || disposition.ApprovedClearOutlineMm.Count < 3))
            throw new InvalidDataException($"{owner}: разрешение требует запись, ответственное лицо и документ.");
    }

    private static void ValidateStructuralOpeningEnvelope(InterfloorOpening opening)
    {
        if (opening.StructuralDisposition is not
            { Status: "EXISTING_OPENING_ACCEPTED" or "NEW_OPENING_APPROVED", ApprovedClearOutlineMm.Count: >= 3 } disposition)
            return;
        var tolerance = opening.PhysicalVerification?.SurveyToleranceMm ?? 0;
        if (new[] { opening.FromFloorFace.VerifiedPlanOutlineMm, opening.ToFloorFace.VerifiedPlanOutlineMm }
            .Any(face => face is null || !PolygonContainsPolygon(disposition.ApprovedClearOutlineMm, face, tolerance)))
            throw new InvalidDataException($"{opening.Id}: конструктивно разрешённый контур не покрывает обе проверенные грани проёма.");
        IReadOnlyList<Point3Mm>? projectedAxis = opening.ClearAxisDefinitionMethod == "CENTERLINE_POLYLINE"
            ? opening.CenterlineMmSharedDatum
            : opening.FromFloorFace.CenterMmSharedDatum is not null && opening.ToFloorFace.CenterMmSharedDatum is not null
                ? [opening.FromFloorFace.CenterMmSharedDatum, opening.ToFloorFace.CenterMmSharedDatum]
                : null;
        if (!PolygonContainsPolyline(disposition.ApprovedClearOutlineMm, projectedAxis, tolerance))
            throw new InvalidDataException($"{opening.Id}: проекция принятой оси выходит за конструктивно разрешённый контур.");
    }

    internal static bool PolygonContainsPolygon(
        IReadOnlyList<PointMm>? container,
        IReadOnlyList<PointMm>? subject,
        double allowance)
    {
        if (container is null || subject is null || !double.IsFinite(allowance) || allowance < 0 ||
            !IsSimplePolygon(container) || !IsSimplePolygon(subject))
            return false;
        for (var subjectIndex = 0; subjectIndex < subject.Count; subjectIndex++)
        {
            var start = subject[subjectIndex];
            var end = subject[(subjectIndex + 1) % subject.Count];
            if (!PolygonContainsSegment(container, start.X, start.Y, end.X, end.Y, allowance)) return false;
        }
        return true;
    }

    internal static bool PolygonContainsPolyline(
        IReadOnlyList<PointMm>? container,
        IReadOnlyList<Point3Mm>? polyline,
        double allowance)
    {
        if (container is null || polyline is not { Count: >= 2 } ||
            !double.IsFinite(allowance) || allowance < 0 || !IsSimplePolygon(container) ||
            polyline.Any(point => !double.IsFinite(point.X) || !double.IsFinite(point.Y)))
            return false;
        return polyline.Zip(polyline.Skip(1), (start, end) => (start, end)).All(segment =>
            PolygonContainsSegment(container, segment.start.X, segment.start.Y,
                segment.end.X, segment.end.Y, allowance));
    }

    private static bool PolygonContainsSegment(
        IReadOnlyList<PointMm> container,
        double startX,
        double startY,
        double endX,
        double endY,
        double allowance)
    {
        var parameters = new List<double> { 0, 1 };
        for (var boundaryIndex = 0; boundaryIndex < container.Count; boundaryIndex++)
            if (AddPolygonBoundaryParameters(startX, startY, endX, endY, container[boundaryIndex],
                    container[(boundaryIndex + 1) % container.Count], parameters))
                return false;
        var ordered = parameters.Order().DistinctBy(value => Math.Round(value, 9)).ToArray();
        if (ordered.Any(parameter => !PolygonCoversPoint(container,
                startX + parameter * (endX - startX),
                startY + parameter * (endY - startY), allowance)))
            return false;
        for (var index = 0; index + 1 < ordered.Length; index++)
        {
            var midpoint = (ordered[index] + ordered[index + 1]) / 2;
            if (!PolygonCoversPoint(container,
                    startX + midpoint * (endX - startX),
                    startY + midpoint * (endY - startY), allowance))
                return false;
        }
        return true;
    }

    private static bool PolygonCoversPoint(
        IReadOnlyList<PointMm> polygon,
        double x,
        double y,
        double tolerance)
    {
        for (var index = 0; index < polygon.Count; index++)
        {
            var start = polygon[index];
            var end = polygon[(index + 1) % polygon.Count];
            var dx = end.X - start.X;
            var dy = end.Y - start.Y;
            var lengthSquared = (double)dx * dx + (double)dy * dy;
            var parameter = lengthSquared <= 0.001 ? 0 :
                Math.Clamp(((x - start.X) * dx + (y - start.Y) * dy) / lengthSquared, 0, 1);
            var nearestX = start.X + parameter * dx;
            var nearestY = start.Y + parameter * dy;
            if (Math.Sqrt(Math.Pow(x - nearestX, 2) + Math.Pow(y - nearestY, 2)) <= tolerance + 0.001)
                return true;
        }
        var inside = false;
        for (int index = 0, previous = polygon.Count - 1; index < polygon.Count; previous = index++)
        {
            var first = polygon[index];
            var second = polygon[previous];
            if ((first.Y > y) != (second.Y > y) &&
                x < (double)(second.X - first.X) * (y - first.Y) / (second.Y - first.Y) + first.X)
                inside = !inside;
        }
        return inside;
    }

    private static bool AddPolygonBoundaryParameters(
        double subjectStartX,
        double subjectStartY,
        double subjectEndX,
        double subjectEndY,
        PointMm boundaryStart,
        PointMm boundaryEnd,
        List<double> parameters)
    {
        var rx = subjectEndX - subjectStartX;
        var ry = subjectEndY - subjectStartY;
        var sx = (double)boundaryEnd.X - boundaryStart.X;
        var sy = (double)boundaryEnd.Y - boundaryStart.Y;
        var qpx = boundaryStart.X - subjectStartX;
        var qpy = boundaryStart.Y - subjectStartY;
        var cross = rx * sy - ry * sx;
        var collinear = qpx * ry - qpy * rx;
        const double epsilon = 0.000001;
        if (Math.Abs(cross) > epsilon)
        {
            var subjectParameter = (qpx * sy - qpy * sx) / cross;
            var boundaryParameter = (qpx * ry - qpy * rx) / cross;
            if (subjectParameter >= -epsilon && subjectParameter <= 1 + epsilon &&
                boundaryParameter >= -epsilon && boundaryParameter <= 1 + epsilon)
            {
                parameters.Add(Math.Clamp(subjectParameter, 0, 1));
                return subjectParameter > epsilon && subjectParameter < 1 - epsilon;
            }
            return false;
        }
        if (Math.Abs(collinear) > epsilon) return false;
        var lengthSquared = rx * rx + ry * ry;
        if (lengthSquared <= epsilon) return false;
        parameters.Add(Math.Clamp((qpx * rx + qpy * ry) / lengthSquared, 0, 1));
        parameters.Add(Math.Clamp(((boundaryEnd.X - subjectStartX) * rx +
                                   (boundaryEnd.Y - subjectStartY) * ry) / lengthSquared, 0, 1));
        return false;
    }

    internal static bool IsSimplePolygon(IReadOnlyList<PointMm>? outline)
    {
        if (outline is null) return false;
        var vertices = outline.ToList();
        if (vertices.Count > 1 && PointDistance(vertices[0], vertices[^1]) <= 0.001)
            vertices.RemoveAt(vertices.Count - 1);
        if (vertices.Count < 3) return false;
        static double Cross(PointMm first, PointMm second, PointMm third) =>
            ((double)second.X - first.X) * (third.Y - first.Y) -
            ((double)second.Y - first.Y) * (third.X - first.X);
        static bool OnSegment(PointMm first, PointMm second, PointMm point)
        {
            const double localEpsilon = 0.000001;
            return Math.Abs(Cross(first, second, point)) <= localEpsilon &&
                   point.X >= Math.Min(first.X, second.X) - localEpsilon &&
                   point.X <= Math.Max(first.X, second.X) + localEpsilon &&
                   point.Y >= Math.Min(first.Y, second.Y) - localEpsilon &&
                   point.Y <= Math.Max(first.Y, second.Y) + localEpsilon;
        }
        static bool Intersects(PointMm firstStart, PointMm firstEnd, PointMm secondStart, PointMm secondEnd)
        {
            const double localEpsilon = 0.000001;
            var first = Cross(firstStart, firstEnd, secondStart);
            var second = Cross(firstStart, firstEnd, secondEnd);
            var third = Cross(secondStart, secondEnd, firstStart);
            var fourth = Cross(secondStart, secondEnd, firstEnd);
            if ((first > localEpsilon && second < -localEpsilon || first < -localEpsilon && second > localEpsilon) &&
                (third > localEpsilon && fourth < -localEpsilon || third < -localEpsilon && fourth > localEpsilon))
                return true;
            return Math.Abs(first) <= localEpsilon && OnSegment(firstStart, firstEnd, secondStart) ||
                   Math.Abs(second) <= localEpsilon && OnSegment(firstStart, firstEnd, secondEnd) ||
                   Math.Abs(third) <= localEpsilon && OnSegment(secondStart, secondEnd, firstStart) ||
                   Math.Abs(fourth) <= localEpsilon && OnSegment(secondStart, secondEnd, firstEnd);
        }

        for (var index = 0; index < vertices.Count; index++)
            if (PointDistance(vertices[index], vertices[(index + 1) % vertices.Count]) <= 0.001)
                return false;
        for (var first = 0; first < vertices.Count; first++)
        {
            var firstNext = (first + 1) % vertices.Count;
            for (var second = first + 1; second < vertices.Count; second++)
            {
                var secondNext = (second + 1) % vertices.Count;
                if (first == second || firstNext == second || secondNext == first) continue;
                if (Intersects(vertices[first], vertices[firstNext], vertices[second], vertices[secondNext]))
                    return false;
            }
        }
        return true;
    }

    internal static bool IsInterfloorOpeningShapeAndAxisReady(InterfloorOpening? opening)
    {
        if (opening?.PhysicalVerification?.Status != "INDEPENDENTLY_VERIFIED" ||
            opening.FromFloorFace is null || opening.ToFloorFace is null ||
            opening.FromFloorId == opening.ToFloorId || opening.FromFloorFace.FloorId != opening.FromFloorId ||
            opening.ToFloorFace.FloorId != opening.ToFloorId || string.IsNullOrWhiteSpace(opening.SharedDatumId))
            return false;
        try
        {
            var fromOutline = opening.FromFloorFace.VerifiedPlanOutlineMm;
            var toOutline = opening.ToFloorFace.VerifiedPlanOutlineMm;
            ValidateOptionalOutline(fromOutline is { Count: > 0 } ? fromOutline : null,
                $"{opening.Id}: первая грань", minimumPoints: 3, required: true);
            ValidateOptionalOutline(toOutline is { Count: > 0 } ? toOutline : null,
                $"{opening.Id}: вторая грань", minimumPoints: 3, required: true);
            ValidateElevationPair(opening.FromFloorFace.FaceElevationMinMmSharedDatum,
                opening.FromFloorFace.FaceElevationMaxMmSharedDatum, $"{opening.Id}: первая грань");
            ValidateElevationPair(opening.ToFloorFace.FaceElevationMinMmSharedDatum,
                opening.ToFloorFace.FaceElevationMaxMmSharedDatum, $"{opening.Id}: вторая грань");
            if (opening.ClearDepthMm is < 1 or > 10_000 ||
                (opening.ClearBottomElevationMmSharedDatum is null) != (opening.ClearTopElevationMmSharedDatum is null) ||
                opening.ClearBottomElevationMmSharedDatum is not null &&
                opening.ClearTopElevationMmSharedDatum <= opening.ClearBottomElevationMmSharedDatum)
                return false;
            ValidatePhysicalVerification(opening.PhysicalVerification, opening.Id);
            ValidateOpeningShapeAndAxis(opening, independentlyVerified: true);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static void ValidateOpeningWidth(string id, PointMm start, PointMm end, double? clearWidthMm, PhysicalVerification? verification)
    {
        if (clearWidthMm is null) return;
        if (!double.IsFinite(clearWidthMm.Value) || clearWidthMm is <= 0 or > 20_000)
            throw new InvalidDataException($"{id}: ширина проёма некорректна.");
        var measured = PointDistance(start, end);
        var tolerance = verification?.SurveyToleranceMm ?? 1;
        if (Math.Abs(measured - clearWidthMm.Value) > tolerance)
            throw new InvalidDataException($"{id}: ширина проёма не совпадает с его краями.");
    }

    internal static bool IsWallOpeningOutlineReady(
        WallSegment? wall,
        PointMm start,
        PointMm end,
        IReadOnlyList<PointMm>? outline,
        double? clearWidthMm,
        double tolerance)
    {
        if (wall is null || outline is null || clearWidthMm is not > 0) return false;
        var vertices = outline.ToList();
        if (vertices.Count > 1 && PointDistance(vertices[0], vertices[^1]) <= tolerance + 0.001)
            vertices.RemoveAt(vertices.Count - 1);
        if (vertices.Count != 4) return false;
        var dx = wall.End.X - wall.Start.X;
        var dy = wall.End.Y - wall.Start.Y;
        var wallLength = Math.Sqrt((double)dx * dx + (double)dy * dy);
        if (wallLength <= 0.001) return false;
        var unitX = dx / wallLength;
        var unitY = dy / wallLength;
        double Along(PointMm point) => (point.X - wall.Start.X) * unitX + (point.Y - wall.Start.Y) * unitY;
        double Normal(PointMm point) => -(point.X - wall.Start.X) * unitY + (point.Y - wall.Start.Y) * unitX;
        var expectedFrom = Math.Min(Along(start), Along(end));
        var expectedTo = Math.Max(Along(start), Along(end));
        var along = vertices.Select(Along).ToArray();
        var normal = vertices.Select(Normal).ToArray();
        if (Math.Abs(along.Min() - expectedFrom) > tolerance || Math.Abs(along.Max() - expectedTo) > tolerance ||
            Math.Abs(expectedTo - expectedFrom - clearWidthMm.Value) > tolerance ||
            Math.Abs(normal.Min() + wall.ThicknessMm / 2d) > tolerance ||
            Math.Abs(normal.Max() - wall.ThicknessMm / 2d) > tolerance)
            return false;
        var expectedCorners = new[]
        {
            (expectedFrom, -wall.ThicknessMm / 2d), (expectedTo, -wall.ThicknessMm / 2d),
            (expectedTo, wall.ThicknessMm / 2d), (expectedFrom, wall.ThicknessMm / 2d),
        };
        return expectedCorners.All(corner => vertices.Any((point) =>
            Math.Abs(Along(point) - corner.Item1) <= tolerance && Math.Abs(Normal(point) - corner.Item2) <= tolerance));
    }

    internal static bool IsWallOpeningVerticalEnvelopeReady(
        WallSegment? wall,
        int? bottomElevationMmSharedDatum,
        int? clearHeightMm,
        double tolerance)
    {
        if (wall?.BaseElevationMmSharedDatum is null || wall.TopElevationMmSharedDatum is null ||
            wall.TopElevationMmSharedDatum <= wall.BaseElevationMmSharedDatum ||
            bottomElevationMmSharedDatum is null || clearHeightMm is not > 0 ||
            !double.IsFinite(tolerance) || tolerance < 0)
            return false;
        var bottom = (double)bottomElevationMmSharedDatum.Value;
        var top = bottom + clearHeightMm.Value;
        return bottom >= wall.BaseElevationMmSharedDatum.Value - tolerance &&
               top <= wall.TopElevationMmSharedDatum.Value + tolerance;
    }

    private static void ValidateElevationPair(int? minimum, int? maximum, string owner)
    {
        if ((minimum is null) != (maximum is null) || minimum is not null && maximum < minimum)
            throw new InvalidDataException($"{owner} заданы некорректно.");
    }

    private static void ValidateOptionalOutline(List<PointMm>? outline, string owner, int minimumPoints, bool required = false)
    {
        if (outline is null)
        {
            if (required) throw new InvalidDataException($"{owner} отсутствует.");
            return;
        }
        if (outline.Count < minimumPoints || outline.Zip(outline.Skip(1).Append(outline[0]), (a, b) => PointDistance(a, b)).All(value => value <= 0.001))
            throw new InvalidDataException($"{owner} вырожден.");
        if (minimumPoints >= 3)
        {
            var area2 = 0d;
            for (var index = 0; index < outline.Count; index++)
            {
                var next = outline[(index + 1) % outline.Count];
                area2 += (double)outline[index].X * next.Y - (double)next.X * outline[index].Y;
            }
            if (Math.Abs(area2) <= 0.001) throw new InvalidDataException($"{owner} не имеет площади.");
            if (!IsSimplePolygon(outline)) throw new InvalidDataException($"{owner} самопересекается.");
        }
    }

    private void ValidateWallOpeningOverlaps()
    {
        var openings = Windows.Where(item => item.WallId is not null)
            .Select(item => (item.Id, WallId: item.WallId!, item.Start, item.End))
            .Concat((DoorOpenings ?? []).Select(item => (item.Id, item.WallId, item.Start, item.End)))
            .GroupBy(item => item.WallId, StringComparer.Ordinal);
        foreach (var group in openings)
        {
            if (!Walls.Any(item => item.Id == group.Key)) continue;
            var wall = Walls.Single(item => item.Id == group.Key);
            var dx = wall.End.X - wall.Start.X;
            var dy = wall.End.Y - wall.Start.Y;
            var length = Math.Sqrt((double)dx * dx + (double)dy * dy);
            if (length <= 0.001) continue;
            var intervals = group.Select(item =>
            {
                double Along(PointMm point) => ((point.X - wall.Start.X) * dx + (point.Y - wall.Start.Y) * dy) / length;
                var first = Along(item.Start); var second = Along(item.End);
                return (item.Id, From: Math.Min(first, second), To: Math.Max(first, second));
            }).OrderBy(item => item.From).ThenBy(item => item.To).ToArray();
            for (var index = 1; index < intervals.Length; index++)
                if (intervals[index].From < intervals[index - 1].To - 0.001)
                    throw new InvalidDataException($"Проёмы {intervals[index - 1].Id} и {intervals[index].Id} пересекаются на одной стене.");
        }
    }

    private static double PointDistance(PointMm first, PointMm second) =>
        Math.Sqrt(Math.Pow(first.X - second.X, 2) + Math.Pow(first.Y - second.Y, 2));

    private static double DistanceToSegment(PointMm point, PointMm start, PointMm end)
    {
        var dx = end.X - start.X; var dy = end.Y - start.Y;
        if (dx == 0 && dy == 0) return Math.Sqrt(Math.Pow(point.X - start.X, 2) + Math.Pow(point.Y - start.Y, 2));
        var denominator = (double)dx * dx + (double)dy * dy;
        var t = Math.Clamp(((double)(point.X - start.X) * dx + (double)(point.Y - start.Y) * dy) / denominator, 0d, 1d);
        var x = start.X + t * dx; var y = start.Y + t * dy;
        return Math.Sqrt(Math.Pow(point.X - x, 2) + Math.Pow(point.Y - y, 2));
    }

    public IEnumerable<PointMm> AllPoints()
    {
        foreach (var level in Levels) { foreach (var point in level.Outline) yield return point; yield return level.Origin; yield return level.LabelPosition; }
        foreach (var room in Rooms) { foreach (var point in room.Outline) yield return point; yield return room.LabelPosition; }
        foreach (var zone in Exclusions) foreach (var point in zone.Outline) yield return point;
        foreach (var zone in ServiceZones) foreach (var point in zone.Outline) yield return point;
        foreach (var wall in Walls)
        {
            yield return wall.Start; yield return wall.End;
            foreach (var point in wall.VerifiedFinishFaceAOutlineMm ?? []) yield return point;
            foreach (var point in wall.VerifiedFinishFaceBOutlineMm ?? []) yield return point;
        }
        foreach (var window in Windows)
        {
            yield return window.Start; yield return window.End;
            foreach (var point in window.VerifiedPlanOutlineMm ?? []) yield return point;
        }
        foreach (var door in DoorOpenings ?? [])
        {
            yield return door.Start; yield return door.End;
            foreach (var point in door.VerifiedPlanOutlineMm ?? []) yield return point;
        }
        foreach (var opening in InterfloorOpenings ?? [])
        {
            foreach (var point in opening.FromFloorFace?.VerifiedPlanOutlineMm ?? []) yield return point;
            foreach (var point in opening.ToFloorFace?.VerifiedPlanOutlineMm ?? []) yield return point;
            foreach (var point in opening.StructuralDisposition?.ApprovedClearOutlineMm ?? []) yield return point;
        }
        foreach (var collector in Collectors) yield return collector.Position;
        foreach (var circuit in Circuits) foreach (var point in circuit.OrderedPoints) yield return point;
    }

    public static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.Never,
    };
}
