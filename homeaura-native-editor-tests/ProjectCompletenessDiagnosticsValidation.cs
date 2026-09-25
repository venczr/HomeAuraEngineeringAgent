using HomeAura.NativeEditor;

internal static class ProjectCompletenessDiagnosticsValidation
{
    public static void Run()
    {
        ValidateLegacyNotApplicable();
        ValidateMissingServedFloor();
        ValidateMaterializedTwoFloorProject();
        ValidateCurrentD178Boundary();
    }

    private static void ValidateLegacyNotApplicable()
    {
        var project = new HomeAuraProject { CanvasWidthMm = 6000, CanvasHeightMm = 6000 };
        project.Collectors.Add(new Collector { Id = "K-LEGACY", Position = new(500, 500) });
        project.Circuits.Add(new ManualCircuit
        {
            Id = "LEGACY-AXIS", SystemRole = "FLOOR_HEATING_AXIS", Completed = true,
            ConcealedServiceLengthMm = 1200, OutOfPlaneLengthMm = 3000,
            OrderedPoints = [new(1000, 1000), new(3000, 1000)],
        });

        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);
        Check(!diagnostics.ServedFloorReferencesApplicable, "Legacy project became served-floor applicable.");
        Check(diagnostics.ServedFloorReferencesPass && diagnostics.MaterializedHeatingRoutesPass &&
              diagnostics.InstallationCompletenessPass, "Legacy not-applicable project did not preserve pass semantics.");
        Equal(1200L, diagnostics.TotalConcealedServiceLengthMm, "Legacy concealed total");
        Equal(3000L, diagnostics.TotalOutOfPlaneLengthMm, "Legacy out-of-plane total");
        Equal(1, diagnostics.AxisOnlyCircuitCount, "Legacy AXIS total");
        Equal(0, diagnostics.MissingServedFloorIds.Count, "Legacy missing floors");
        var detail = Single(diagnostics.CollectorServedFloorDetails, "legacy collector detail");
        Check(!detail.Applicable && detail.ServedFloorExists && detail.ServedFloorId is null,
            "Legacy collector applicability changed.");
    }

    private static void ValidateMissingServedFloor()
    {
        var project = MaterializedTwoFloorProject();
        project.Levels.RemoveAll(item => item.Id == "ATTIC");
        project.Rooms.RemoveAll(item => item.FloorId == "ATTIC");
        project.Circuits.RemoveAll(item => item.CollectorId == "K2");

        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);
        Check(diagnostics.ServedFloorReferencesApplicable, "Served-floor reference was not applicable.");
        Check(!diagnostics.ServedFloorReferencesPass && !diagnostics.MaterializedHeatingRoutesPass &&
              !diagnostics.InstallationCompletenessPass, "Missing ATTIC incorrectly passed completeness.");
        Equal("ATTIC", Single(diagnostics.MissingServedFloorIds, "missing served floor"), "Missing floor id");

        var floor1 = diagnostics.CollectorServedFloorDetails.Single(item => item.CollectorId == "K1");
        Check(floor1.Applicable && floor1.ServedFloorExists, "Existing FLOOR_1 was not recognized.");
        Equal(1, floor1.RoomCount, "FLOOR_1 room count");
        Equal(1, floor1.HeatingBodyCount, "FLOOR_1 body count");
        Equal(1, floor1.LoopCircuitCount, "FLOOR_1 LOOP count");
        Equal(0, floor1.AxisCircuitCount, "FLOOR_1 AXIS count");

        var attic = diagnostics.CollectorServedFloorDetails.Single(item => item.CollectorId == "K2");
        Check(attic.Applicable && !attic.ServedFloorExists, "Missing ATTIC detail changed.");
        Equal(0, attic.RoomCount, "Missing ATTIC room count");
        Equal(0, attic.HeatingBodyCount, "Missing ATTIC body count");
        Equal(0, attic.LoopCircuitCount, "Missing ATTIC LOOP count");
        Equal(0, attic.AxisCircuitCount, "Missing ATTIC AXIS count");
    }

    private static void ValidateMaterializedTwoFloorProject()
    {
        var project = MaterializedTwoFloorProject();
        project.ValidateContract();
        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);

        Check(diagnostics.ServedFloorReferencesApplicable && diagnostics.ServedFloorReferencesPass,
            "Valid two-floor served-floor references failed.");
        Check(diagnostics.MaterializedHeatingRoutesPass && diagnostics.InstallationCompletenessPass,
            "Valid materialized two-floor project failed completeness.");
        Equal(0L, diagnostics.TotalConcealedServiceLengthMm, "Two-floor concealed total");
        Equal(0L, diagnostics.TotalOutOfPlaneLengthMm, "Two-floor out-of-plane total");
        Equal(0, diagnostics.AxisOnlyCircuitCount, "Two-floor AXIS total");
        Equal(0, diagnostics.MissingServedFloorIds.Count, "Two-floor missing floors");
        Equal(2, diagnostics.CollectorServedFloorDetails.Count, "Two-floor collector detail count");
        Check(diagnostics.CollectorServedFloorDetails.All(item => item.Applicable && item.ServedFloorExists &&
              item.RoomCount == 1 && item.HeatingBodyCount == 1 && item.LoopCircuitCount == 1 &&
              item.AxisCircuitCount == 0), "Valid per-floor counts changed.");

        var firstCircuit = project.Circuits[0];
        var circuitAnalysis = CircuitAnalyzer.Analyze(project, firstCircuit);
        Check(!circuitAnalysis.StartAtCollector && !circuitAnalysis.EndAtCollector,
            "Synthetic endpoints unexpectedly entered the draft collector tolerance.");
        Check(diagnostics.InstallationCompletenessPass,
            "Structural completeness was incorrectly coupled to NearAssignedConnection.");
        Check(!diagnostics.DesignPass, "Existing DesignPass semantics unexpectedly changed.");
    }

    private static void ValidateCurrentD178Boundary()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var path = Path.Combine(root, "homeaura-native-editor", "examples", "proposals",
            "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178", "HomeAura_Floor1_BoilerPair_D178.homeaura.json");
        var project = HomeAuraProject.FromJson(File.ReadAllText(path));
        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);

        Check(diagnostics.ServedFloorReferencesApplicable, "D178 served-floor diagnostics are not applicable.");
        Equal("ATTIC", Single(diagnostics.MissingServedFloorIds, "D178 missing floor"), "D178 missing floor id");
        Equal(140_400L, diagnostics.TotalConcealedServiceLengthMm, "D178 concealed total");
        Equal(0L, diagnostics.TotalOutOfPlaneLengthMm, "D178 out-of-plane total");
        Equal(6, diagnostics.AxisOnlyCircuitCount, "D178 AXIS total");

        var floor1 = diagnostics.CollectorServedFloorDetails.Single(item => item.CollectorId == "K1");
        Equal(8, floor1.RoomCount, "D178 FLOOR_1 room count");
        Equal(27, floor1.HeatingBodyCount, "D178 FLOOR_1 body count");
        Equal(8, floor1.LoopCircuitCount, "D178 FLOOR_1 LOOP count");
        Equal(6, floor1.AxisCircuitCount, "D178 FLOOR_1 AXIS count");
        var attic = diagnostics.CollectorServedFloorDetails.Single(item => item.CollectorId == "K2");
        Check(!attic.ServedFloorExists && attic.RoomCount == 0 && attic.HeatingBodyCount == 0 &&
              attic.LoopCircuitCount == 0 && attic.AxisCircuitCount == 0, "D178 ATTIC boundary changed.");
        Check(!diagnostics.ServedFloorReferencesPass && !diagnostics.MaterializedHeatingRoutesPass &&
              !diagnostics.InstallationCompletenessPass, "D178 incorrectly became installation-complete.");
    }

    private static HomeAuraProject MaterializedTwoFloorProject()
    {
        var project = new HomeAuraProject { CanvasWidthMm = 12_000, CanvasHeightMm = 12_000 };
        project.Levels.AddRange([
            new FloorLevel { Id = "FLOOR_1", Name = "Этаж 1", Origin = new(0, 0) },
            new FloorLevel { Id = "ATTIC", Name = "Этаж 2", Origin = new(0, 6000) },
        ]);
        project.Rooms.AddRange([
            new RoomZone
            {
                Id = "F1-R1", FloorId = "FLOOR_1", Name = "Room 1",
                Outline = [new(500, 500), new(5500, 500), new(5500, 4500), new(500, 4500)],
                LabelPosition = new(1000, 1000),
            },
            new RoomZone
            {
                Id = "A-R1", FloorId = "ATTIC", Name = "Room 2",
                Outline = [new(6500, 6500), new(11_500, 6500), new(11_500, 10_500), new(6500, 10_500)],
                LabelPosition = new(7000, 7000),
            },
        ]);
        project.Collectors.AddRange([
            new Collector { Id = "K1", Position = new(500, 500), FloorId = "FLOOR_1", ServedFloorId = "FLOOR_1" },
            new Collector { Id = "K2", Position = new(500, 6500), FloorId = "FLOOR_1", ServedFloorId = "ATTIC" },
        ]);
        project.Circuits.AddRange([
            MaterializedLoop("F1-C1", "K1", "F1-R1",
                [new(1000, 1000, 108), new(5000, 1000, 108), new(5000, 4000, 108), new(1000, 4000, 108)]),
            MaterializedLoop("A-C1", "K2", "A-R1",
                [new(7000, 7000, 108), new(11_000, 7000, 108), new(11_000, 10_000, 108), new(7000, 10_000, 108)]),
        ]);
        return project;
    }

    private static ManualCircuit MaterializedLoop(
        string id, string collectorId, string roomId, List<PointMm> points) => new()
    {
        Id = id, Name = id, CollectorId = collectorId, RoomId = roomId,
        SystemRole = "FLOOR_HEATING_LOOP", RoutingLayer = "HEATING_PLANE", Completed = true,
        OrderedPoints = points, HeatingBodyStartIndex = 0, HeatingBodyEndIndex = points.Count - 1,
    };

    private static T Single<T>(IReadOnlyList<T> values, string label)
    {
        if (values.Count != 1) throw new InvalidDataException($"{label}: expected one item, got {values.Count}.");
        return values[0];
    }

    private static void Equal<T>(T expected, T actual, string label) where T : notnull
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
