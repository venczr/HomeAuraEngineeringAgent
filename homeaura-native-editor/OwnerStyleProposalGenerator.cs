namespace HomeAura.NativeEditor;

public static class OwnerStyleProposalGenerator
{
    public static HomeAuraProject RotateAcceptedExampleCounterClockwise(HomeAuraProject source)
    {
        source.ValidateContract();
        if (source.SchemaVersion != "1.0")
            throw new InvalidOperationException("Генератор стиля владельца поддерживает только schema_version 1.0; физические данные 1.1 нельзя безопасно преобразовать этой операцией.");
        if (source.Training.Label != "ACCEPTED")
            throw new InvalidOperationException("Источник предложения должен быть принятым эталоном владельца.");

        PointMm Rotate(PointMm point) => point.Z is null
            ? new(point.Y, source.CanvasWidthMm - point.X)
            : new(point.Y, source.CanvasWidthMm - point.X, point.Z.Value);
        var collectorIds = source.Collectors.ToDictionary(item => item.Id, item => $"ai001_{item.Id}", StringComparer.Ordinal);
        var serviceZoneIds = source.ServiceZones.ToDictionary(item => item.Id, item => $"ai001_{item.Id}", StringComparer.Ordinal);
        var proposal = new HomeAuraProject
        {
            SchemaVersion = source.SchemaVersion,
            Kind = source.Kind,
            Units = source.Units,
            CanvasWidthMm = source.CanvasHeightMm,
            CanvasHeightMm = source.CanvasWidthMm,
            GridSpacingMm = source.GridSpacingMm,
            Levels = source.Levels.Select(item => new FloorLevel
            {
                Id = item.Id,
                Name = item.Name,
                Origin = Rotate(item.Origin),
                Outline = item.Outline.Select(Rotate).ToList(),
                LabelPosition = Rotate(item.LabelPosition),
            }).ToList(),
            Rooms = source.Rooms.Select(item => new RoomZone
            {
                Id = item.Id,
                FloorId = item.FloorId,
                Name = item.Name,
                AreaM2 = item.AreaM2,
                Outline = item.Outline.Select(Rotate).ToList(),
                LabelPosition = Rotate(item.LabelPosition),
                HeatingAllowed = item.HeatingAllowed,
                FillColor = item.FillColor,
            }).ToList(),
            Exclusions = source.Exclusions.Select(item => new ExclusionZone
            {
                Id = item.Id,
                FloorId = item.FloorId,
                Name = item.Name,
                Outline = item.Outline.Select(Rotate).ToList(),
                FillColor = item.FillColor,
            }).ToList(),
            Walls = source.Walls.Select(item => new WallSegment
            {
                Id = $"ai001_{item.Id}", Start = Rotate(item.Start), End = Rotate(item.End), WallType = item.WallType,
                ThicknessMm = item.ThicknessMm
            }).ToList(),
            Windows = source.Windows.Select(item => new WindowOpening
            {
                Id = $"ai001_{item.Id}", WallId = item.WallId is null ? null : $"ai001_{item.WallId}",
                Start = Rotate(item.Start), End = Rotate(item.End), SillHeightMm = item.SillHeightMm,
                OpeningHeightMm = item.OpeningHeightMm
            }).ToList(),
            Collectors = source.Collectors.Select(item => new Collector
            {
                Id = collectorIds[item.Id], Position = Rotate(item.Position), Ports = item.Ports,
                RotationDegrees = (item.RotationDegrees + 90) % 360,
                ConnectionToleranceMm = item.ConnectionToleranceMm,
                FloorId = item.FloorId, ServedFloorId = item.ServedFloorId,
                MountingWallId = item.MountingWallId is null ? null : $"ai001_{item.MountingWallId}",
                VisibleOnPlan = item.VisibleOnPlan, ExternalToPlan = item.ExternalToPlan,
                PipeOutletDirection = item.PipeOutletDirection switch { "DOWN" => "RIGHT", "RIGHT" => "UP", "UP" => "LEFT", _ => "DOWN" },
                ReferenceWidthMm = item.ReferenceWidthMm, ReferenceDepthMm = item.ReferenceDepthMm,
                ReferenceHeightMm = item.ReferenceHeightMm, EquipmentStatus = item.EquipmentStatus,
                ReferenceSource = item.ReferenceSource
            }).ToList(),
            ServiceZones = source.ServiceZones.Select(item => new ServiceZone
            {
                Id = serviceZoneIds[item.Id],
                FloorId = item.FloorId,
                Name = item.Name,
                Outline = item.Outline.Select(Rotate).ToList(),
                FillColor = item.FillColor,
                Note = item.Note,
                CollectorId = item.CollectorId is null ? null : collectorIds[item.CollectorId],
                ClearHeightMm = item.ClearHeightMm,
                PipeCapacity = item.PipeCapacity,
                RequiredPipeCount = item.RequiredPipeCount,
                RequiredPlanWidthMm = item.RequiredPlanWidthMm,
                PipeGeometryMaterialized = item.PipeGeometryMaterialized,
            }).ToList(),
            FloorBuildUps = source.FloorBuildUps.Select(item => new FloorBuildUp
            {
                FloorId = item.FloorId,
                InstalledInsulationMm = item.InstalledInsulationMm,
                RemainingHeightMm = item.RemainingHeightMm,
            }).ToList(),
            RoutingRules = new RoutingRules
            {
                PipeOuterDiameterMm = source.RoutingRules.PipeOuterDiameterMm,
                MinimumBendRadiusMm = source.RoutingRules.MinimumBendRadiusMm,
                ExteriorWallSpacingMm = source.RoutingRules.ExteriorWallSpacingMm,
                FieldSpacingMm = source.RoutingRules.FieldSpacingMm,
                MaximumParallelTransitPipesAt100Mm = source.RoutingRules.MaximumParallelTransitPipesAt100Mm,
                MinimumLayerAxisSeparationMm = source.RoutingRules.MinimumLayerAxisSeparationMm,
                MinimumLayerSurfaceClearanceMm = source.RoutingRules.MinimumLayerSurfaceClearanceMm,
                TransitLaneGeometryVerified = source.RoutingRules.TransitLaneGeometryVerified,
                ExteriorEdgeZoneApplied = source.RoutingRules.ExteriorEdgeZoneApplied,
                OwnerAcceptedReferenceRequired = source.RoutingRules.OwnerAcceptedReferenceRequired,
            },
            Circuits = source.Circuits.Select(item => new ManualCircuit
            {
                Id = $"ai001_{item.Id}", Name = item.Name, Color = item.Color,
                OrderedPoints = item.OrderedPoints.Select(Rotate).ToList(), Completed = item.Completed,
                VerticalTransitions = item.VerticalTransitions.Select(transition => new VerticalTransition
                {
                    SegmentIndex = transition.SegmentIndex,
                    Kind = transition.Kind,
                    RadiusMm = transition.RadiusMm,
                    StartTangentLengthMm = transition.StartTangentLengthMm,
                    EndTangentLengthMm = transition.EndTangentLengthMm,
                    ArcSamplesPerHalf = transition.ArcSamplesPerHalf,
                }).ToList(),
                CollectorId = item.CollectorId is null ? null : collectorIds[item.CollectorId],
                SupplyPortIndex = item.SupplyPortIndex, ReturnPortIndex = item.ReturnPortIndex,
                ServiceZoneId = item.ServiceZoneId is null ? null : serviceZoneIds[item.ServiceZoneId], ConcealedServiceLengthMm = item.ConcealedServiceLengthMm,
                OutOfPlaneLengthMm = item.OutOfPlaneLengthMm,
                RoutingLayer = item.RoutingLayer, SystemRole = item.SystemRole,
                AxisElevationMm = item.AxisElevationMm, VisibleOnPlan = item.VisibleOnPlan,
                RoomId = item.RoomId, HeatingBodyStartIndex = item.HeatingBodyStartIndex,
                HeatingBodyEndIndex = item.HeatingBodyEndIndex,
                HeatingBodyRanges = item.HeatingBodyRanges.Select(range => new HeatingBodyRange
                {
                    StartIndex = range.StartIndex,
                    EndIndex = range.EndIndex,
                }).ToList()
            }).ToList(),
            Training = new TrainingMetadata
            {
                Label = "DRAFT",
                AuthorIntent = "AI-generated proposal for owner review",
                Notes = "AI PROPOSAL 001. Комната 3200 x 7000 мм. Западная стена наружная. Геометрия самостоятельно получена из принятого стиля владельца поворотом инженерной задачи на 90°: три прохода 100/200/300 мм у наружной стены, далее поле 200 мм; длины и принятые центральные замыкания сохранены. Требуется оценка владельца ACCEPTED или REJECTED."
            }
        };
        proposal.ValidateContract();
        return proposal;
    }
}
