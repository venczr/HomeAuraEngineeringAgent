using System.Text.Json;
using HomeAura.NativeEditor;

internal static class CollectorEquipmentValidation
{
    public static void Run()
    {
        var sourcePath = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..",
            "manufacturer-data", "uponor_vario_s_fm_14_design_reference.json"));
        using var source = JsonDocument.Parse(File.ReadAllText(sourcePath));
        var root = source.RootElement;
        Equal("1140845", root.GetProperty("official_variant_part_number").GetString(), "official part number");
        Equal(14, root.GetProperty("heating_circuit_count").GetInt32(), "official loop count");
        Equal(50, root.GetProperty("loop_pitch_mm").GetInt32(), "official loop pitch");
        Equal(225, root.GetProperty("header_pitch_mm").GetInt32(), "official header pitch");
        Equal(814, root.GetProperty("dimensions_mm").GetProperty("L1").GetInt32(), "official L1");

        var project = new HomeAuraProject { CanvasWidthMm = 5000, CanvasHeightMm = 4000, GridSpacingMm = 100 };
        project.Levels.AddRange([
            new FloorLevel { Id = "FLOOR_1", Name = "Этаж 1" },
            new FloorLevel { Id = "ATTIC", Name = "Этаж 2" },
        ]);
        project.Walls.Add(new WallSegment
        {
            Id = "FLOOR_1-W025",
            Start = new PointMm(1600, 500),
            End = new PointMm(1600, 3500),
            ThicknessMm = 200,
        });

        var k1 = CreateReferenceCollector("K1", new PointMm(1800, 1200), "FLOOR_1", 0, "DOWN");
        var k2 = CreateReferenceCollector("K2", new PointMm(1800, 2600), "ATTIC", 180, "UP");
        k1.MaterializeReferenceConnectionPoints();
        k2.MaterializeReferenceConnectionPoints();
        project.Collectors.AddRange([k1, k2]);
        project.ValidateContract();

        Equal("FLOOR_1-W025", k1.MountingWallId, "K1 mounting wall");
        Equal(k1.MountingWallId, k2.MountingWallId, "same-wall placement metadata");
        Equal(180, k2.RotationDegrees, "K2 inversion");
        Equal("ATTIC", k2.ServedFloorId, "K2 served floor");
        Equal(14, k1.LoopCount, "loop count");
        Equal(28, k1.ConnectionCapacity, "connection capacity");
        Equal(814, k1.ReferenceLengthMm, "reference length");
        Equal(235, k1.ReferenceDepthMm, "reference plan depth");
        Equal(225, k1.HeaderPitchMm, "header pitch");
        Equal(50, k1.LoopConnectionPitchMm, "loop pitch");

        var points = k1.ResolveConnectionPoints().OrderBy(item => item.ConnectionIndex).ToArray();
        Equal(28, points.Length, "materialized point count");
        for (var loopIndex = 0; loopIndex < 14; loopIndex++)
        {
            var supply = points[loopIndex * 2];
            var reverse = points[loopIndex * 2 + 1];
            var expectedAlong = -325d + loopIndex * 50d;
            Equal(loopIndex * 2, supply.ConnectionIndex, $"supply index {loopIndex}");
            Equal(loopIndex * 2 + 1, reverse.ConnectionIndex, $"return index {loopIndex}");
            Equal(loopIndex, supply.LoopIndex, $"supply loop {loopIndex}");
            Equal(loopIndex, reverse.LoopIndex, $"return loop {loopIndex}");
            Equal("SUPPLY", supply.Header, $"supply header {loopIndex}");
            Equal("RETURN", reverse.Header, $"return header {loopIndex}");
            Near(expectedAlong, supply.LocalPositionMm.X, 0.0001, $"supply station {loopIndex}");
            Near(expectedAlong, reverse.LocalPositionMm.X, 0.0001, $"return station {loopIndex}");
            Near(-112.5, supply.LocalPositionMm.Y, 0.0001, $"supply row {loopIndex}");
            Near(112.5, reverse.LocalPositionMm.Y, 0.0001, $"return row {loopIndex}");
        }
        Near(650, points[^2].LocalPositionMm.X - points[0].LocalPositionMm.X, 0.0001, "14-station span");
        Near(225, points[1].LocalPositionMm.Y - points[0].LocalPositionMm.Y, 0.0001, "two-header spacing");

        var wallAngle = k1.MountingWallAngleDegrees(project);
        Near(90, wallAngle, 0.0001, "wall alignment angle");
        var k1World = k1.ConnectionPointWorldPosition(points[0], wallAngle);
        var k2Point = k2.ResolveConnectionPoints().Single(item => item.ConnectionIndex == 0);
        var k2World = k2.ConnectionPointWorldPosition(k2Point, k2.MountingWallAngleDegrees(project));
        Near(0, (k1World.X - k1.Position.X) + (k2World.X - k2.Position.X), 0.0001, "180-degree X inversion");
        Near(0, (k1World.Y - k1.Position.Y) + (k2World.Y - k2.Position.Y), 0.0001, "180-degree Y inversion");

        var json = project.ToJson();
        True(json.Contains("\"manufacturer\"", StringComparison.Ordinal), "manufacturer was not serialized");
        True(json.Contains("\"connection_points\"", StringComparison.Ordinal), "physical points were not serialized");
        var restored = HomeAuraProject.FromJson(json);
        var restoredK2 = restored.Collectors.Single(item => item.Id == "K2");
        Equal("GF Building Flow Solutions / Uponor", restoredK2.Manufacturer, "manufacturer round-trip");
        Equal("Uponor Vario S manifold FM 14xG3/4 Euro - G1", restoredK2.Model, "model round-trip");
        Equal("1140845", restoredK2.PartNumber, "part number round-trip");
        Equal(28, restoredK2.ConnectionPoints?.Count, "point geometry round-trip");
        Equal(180, restoredK2.RotationDegrees, "rotation round-trip");

        var paired = project.DeepClone();
        paired.Circuits.Add(new ManualCircuit
        {
            Id = "PAIR-0",
            Name = "Точная пара 1",
            Completed = true,
            CollectorId = "K1",
            SupplyPortIndex = 0,
            ReturnPortIndex = 1,
            OrderedPoints = [new PointMm(1900, 900), new PointMm(1700, 900)],
        });
        paired.ValidateContract();
        var pairedAnalysis = CircuitAnalyzer.Analyze(paired, paired.Circuits.Single());
        True(pairedAnalysis.StartAtCollector && pairedAnalysis.EndAtCollector, "exact paired endpoints were not resolved to physical points");

        var supplyLeg = project.DeepClone();
        supplyLeg.Circuits.Add(new ManualCircuit
        {
            Id = "SUPPLY-LEG-0",
            Name = "Отдельная подающая подводка",
            Completed = true,
            SystemRole = "FLOOR_SERVICE_LEG",
            RoutingLayer = "LOWER_SERVICE_LAYER",
            CollectorId = "K1",
            SupplyPortIndex = 0,
            OrderedPoints = [new PointMm(1900, 900), new PointMm(2300, 900)],
        });
        supplyLeg.ValidateContract();

        var reversedHeaders = project.DeepClone();
        reversedHeaders.Circuits.Add(new ManualCircuit
        {
            Id = "REVERSED",
            Name = "Перепутанные балки",
            Completed = true,
            CollectorId = "K1",
            SupplyPortIndex = 1,
            ReturnPortIndex = 0,
            OrderedPoints = [new PointMm(1700, 900), new PointMm(1900, 900)],
        });
        Throws<InvalidDataException>(() => reversedHeaders.ValidateContract(), "reversed supply/return headers");

        var crossedPairs = project.DeepClone();
        crossedPairs.Circuits.Add(new ManualCircuit
        {
            Id = "CROSS-PAIR",
            Name = "Разные пары",
            Completed = true,
            CollectorId = "K1",
            SupplyPortIndex = 0,
            ReturnPortIndex = 3,
            OrderedPoints = [new PointMm(1900, 900), new PointMm(1700, 900)],
        });
        Throws<InvalidDataException>(() => crossedPairs.ValidateContract(), "cross-pair 0/3 assignment");

        var missingIndices = project.DeepClone();
        missingIndices.Circuits.Add(new ManualCircuit
        {
            Id = "NO-INDEX",
            Name = "Нет индексов",
            Completed = true,
            CollectorId = "K1",
            OrderedPoints = [new PointMm(1800, 1100), new PointMm(1800, 1300)],
        });
        var missingAnalysis = CircuitAnalyzer.Analyze(missingIndices, missingIndices.Circuits.Single());
        True(!missingAnalysis.StartAtCollector && !missingAnalysis.EndAtCollector, "physical collector fell back to its centre without port indices");
        Throws<InvalidDataException>(() => missingIndices.ValidateContract(), "omitted physical port indices");

        var detached = project.DeepClone();
        detached.Collectors.Single(item => item.Id == "K1").Position = new PointMm(3000, 1200);
        Throws<InvalidDataException>(() => detached.ValidateContract(), "collector detached from mounting wall");

        var legacy = new HomeAuraProject { CanvasWidthMm = 3000, CanvasHeightMm = 3000 };
        legacy.Collectors.Add(new Collector { Id = "LEGACY", Position = new PointMm(1500, 1500), Ports = 12 });
        var legacyJson = legacy.ToJson();
        var restoredLegacy = HomeAuraProject.FromJson(legacyJson).Collectors.Single();
        Equal(12, restoredLegacy.ConnectionCapacity, "legacy ports capacity");
        True(!restoredLegacy.HasPhysicalReferenceGeometry, "legacy collector unexpectedly entered physical mode");
        Equal(0, restoredLegacy.ResolveConnectionPoints().Count, "legacy collector unexpectedly gained physical points");
        True(!legacyJson.Contains("\"loop_count\"", StringComparison.Ordinal), "optional physical fields polluted legacy JSON");

        var partial = legacy.DeepClone();
        partial.Collectors[0].LoopCount = 14;
        Throws<InvalidDataException>(() => partial.ValidateContract(), "partial physical collector metadata");

        var invalid = project.DeepClone();
        invalid.Collectors[0].ConnectionPoints![0].LocalPositionMm = new Point3Mm(-324, -112.5, 0);
        Throws<InvalidDataException>(() => invalid.ValidateContract(), "altered 50 mm station geometry");
    }

    private static Collector CreateReferenceCollector(string id, PointMm position, string servedFloorId, int rotation, string outlet) => new()
    {
        Id = id,
        Position = position,
        Ports = 28,
        RotationDegrees = rotation,
        ConnectionToleranceMm = 400,
        FloorId = "FLOOR_1",
        ServedFloorId = servedFloorId,
        MountingWallId = "FLOOR_1-W025",
        PipeOutletDirection = outlet,
        ReferenceWidthMm = 814,
        ReferenceDepthMm = 235,
        ReferenceHeightMm = 320,
        EquipmentStatus = "SELECTED_REFERENCE",
        ReferenceSource = "manufacturer-data/uponor_vario_s_fm_14_design_reference.json",
        Manufacturer = "GF Building Flow Solutions / Uponor",
        Model = "Uponor Vario S manifold FM 14xG3/4 Euro - G1",
        PartNumber = "1140845",
        LoopCount = 14,
        ConnectionPointCount = 28,
        HeaderPitchMm = 225,
        LoopConnectionPitchMm = 50,
        ReferenceLengthMm = 814,
    };

    private static void Equal<T>(T expected, T actual, string label)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new Exception($"{label}: expected {expected}, got {actual}");
    }

    private static void Near(double expected, double actual, double tolerance, string label)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new Exception($"{label}: expected {expected}, got {actual}");
    }

    private static void True(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
    }

    private static void Throws<T>(Action action, string label) where T : Exception
    {
        try { action(); }
        catch (T) { return; }
        throw new Exception($"{label}: expected {typeof(T).Name}");
    }
}
