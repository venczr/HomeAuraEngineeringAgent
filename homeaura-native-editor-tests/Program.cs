using HomeAura.NativeEditor;

var tests = new (string Name, Action Run)[]
{
    ("100 mm grid snapping", TestSnap),
    ("project round-trip preserves ordered route", TestRoundTrip),
    ("off-grid project is rejected", TestOffGridRejected),
    ("analysis is read-only and deterministic", TestAnalysisDeterministic),
    ("self-intersection is detected", TestSelfIntersection),
    ("training label and notes persist", TestTrainingMetadata),
    ("invalid training label is rejected", TestInvalidTrainingLabel),
    ("inter-circuit crossing is detected", TestInterCircuitCrossing),
    ("different routing layers cross without false conflict", TestDifferentRoutingLayers),
    ("50 mm engineering grid persists", TestFiftyMillimetreGrid),
    ("80 mm bend radius rejects a short segment between turns", TestBendRadius),
    ("unfinished circuit cannot pass", TestUnfinishedCircuit),
    ("collector assignment persists", TestCollectorAssignment),
    ("duplicate collector port is rejected", TestDuplicateCollectorPort),
    ("7000x3200 south-exterior owner example is valid", TestRoomFixture),
    ("collector rotation persists", TestCollectorRotation),
    ("invalid collector rotation is rejected", TestInvalidCollectorRotation),
    ("wall thickness and blue window contract persist", TestWallAndWindowContract),
    ("heating body stays in room while transit may cross walls", TestHeatingBodyPlacement),
    ("owner accepted example metrics are locked", TestOwnerAcceptedExample),
    ("AI proposal rotates owner style without geometry damage", TestOwnerStyleProposal),
    ("two-floor DRAFT publishes only non-contact bodies and honest REWORK", TwoFloorDraftValidation.Run),
    ("two-floor geometry negative relation fixtures", TwoFloorGeometryNegativeValidation.Run),
    ("D151 native house projects are editable and contact-free", NativeHouseRework151Validation.Run),
    ("D153-D164 exact native house, walls, windows, manifolds, audited dual-rise, and golden-mean layouts", NativeExactHouseValidation.Run),
    ("D165 materializes complete K1 routes and honest attic floor axes", MaterializedRouteBaseline165Validation.Run),
    ("D166 materializes 22 K2 service legs with explicit vertical separation", K2ServiceLayer166Validation.Run),
    ("D167-D169 scale collectors and enforce R80 plus explicit layer clearance", EngineeringBendValidation167168.Run),
    ("D170 rebuilds wall-safe bodies from owner markup with real exterior 3x100 bands", OwnerMarkupCorrection170Validation.Run),
    ("D171 applies the owner's ACCEPTED counterflow grammar and reduces kitchen to three bodies", OwnerAcceptedAnalogue171Validation.Run),
    ("D172 validates the Claude/Kimi control pair without hiding provider or R80 failures", ProviderPair172Validation.Run),
    ("geometry diagnostics expose R80, wall intrusion, and joint exterior 3x100 details", EngineeringDiagnosticsValidation.Run),
    ("multiple heating-body ranges keep wall-crossing gaps as transit", MultipleHeatingBodyRangesValidation.Run),
    ("D173 jointly weaves the room pair without short R80 U-turns or false route balance", JointWeave173Validation.Run),
    ("D174 balances a multi-range room pair without hiding 3D ramps or inherited R80 debt", LowerServicePair174Validation.Run),
    ("explicit Point3 S-bends enforce 3D length, R80, contacts, clearance, and continuity", ThreeDimensionalRoutingValidation.Run),
    ("Uponor FM14 collectors preserve exact 14/28 physical geometry and inverted same-wall placement", CollectorEquipmentValidation.Run),
    ("D175 materializes four continuous R80 Point3 floor routes and two owner-style hall spirals", PhysicalFourLoop175Validation.Run),
    ("D176 rebuilds the wet-area pair with nine owner-style bodies and two contact-free Point3 chains", WetPair176Validation.Run),
    ("D177 moves the physical C11 R80 turns clear of W015 and exposes deferred collector tails", WetPairPhysicalTurnFix177Validation.Run),
    ("D178 rebuilds the boiler room as two balanced Point3 loops with exact exterior L-bands", BoilerPair178Validation.Run),
    ("project diagnostics expose served-floor and materialized-route completeness separately", ProjectCompletenessDiagnosticsValidation.Run),
    ("two owner PDFs lock the two-floor layout grammar and exact labelled lengths", OwnerTwoFloorReferenceValidation.Run),
    ("clean rendering samples physical R80 fillets while engineering view keeps control vertices", RoundedCleanRenderValidation.Run),
    ("D180 appends only verified ATTIC room architecture and keeps all K2 routes unmaterialized", TwoFloorArchitectureBaseline180Validation.Run),
    ("D181 derives exact ATTIC complement wall-domain candidates without inventing construction or openings", AtticSourceWallDomains181Validation.Run),
    ("R03 independent owner gate rejects numeric serpentines and disconnected void-fill seams", R03OwnerAcceptanceGateValidation.Run),
    ("D182 proves the wall-safe R03 owner BODY fixture while keeping Point3 transit pending", R03OwnerBodyFixture182Validation.Run),
    ("D183 materializes only C07-C09 as exact balanced Point3 terminal-grid routes while Eurocone tails stay deferred", R03Point3Routes183Validation.Run),
    ("D184 materializes only R07 C03-C04 as strict owner-style Point3 routes while Eurocone tails stay deferred", R07Point3Routes184Validation.Run),
    ("D185 officially publishes only C12 as a bounded-terminal Point3 loop while exact Eurocone tails stay blocked by the 80 m lower bound", C12BoundedTerminal185Validation.Run),
    ("D186 officially publishes an evidence-only verified physical-input gate while all geometry and installation claims remain blocked", AtticVerifiedPhysicalInputGate186Validation.Run),
    ("schema 1.1 keeps legacy bytes stable and fails closed on unverified cross-floor physical input", PhysicalInputSchemaValidation.Run),
    ("schema 1.1 active-floor renderer keeps physical objects and opening faces on their declared floors", PhysicalInputRendererValidation.Run),
    ("corner- and partition-aware exterior useful spans preserve raw audit and clear D183 owner lanes", ExteriorUsefulSpanValidation.Run),
    ("bounded staggered exterior turnouts pass R07 but reject excessive, window, and contact cases", ExteriorStaggeredTurnoutValidation.Run),
    ("single-room counterflow spirals expose one bounded windowless terminal corner without weakening raw exterior evidence", ExteriorOpenSpiralTerminalCornerValidation.Run),
};

var failed = 0;
foreach (var test in tests)
{
    try { test.Run(); Console.WriteLine($"PASS  {test.Name}"); }
    catch (Exception error) { failed++; Console.WriteLine($"FAIL  {test.Name}: {error.Message}"); }
}
Console.WriteLine($"RESULT {tests.Length - failed}/{tests.Length} passed");
return failed == 0 ? 0 : 1;

static void TestSnap()
{
    var point = CircuitAnalyzer.Snap(149, 251);
    Equal(100, point.X); Equal(300, point.Y);
}

static void TestRoundTrip()
{
    var project = Fixture();
    var expected = project.Circuits[0].OrderedPoints.Select(PointText).ToArray();
    var restored = HomeAuraProject.FromJson(project.ToJson());
    SequenceEqual(expected, restored.Circuits[0].OrderedPoints.Select(PointText).ToArray());
    Equal(100, restored.GridSpacingMm); Equal("mm", restored.Units);
}

static void TestOffGridRejected()
{
    var project = Fixture(); project.Circuits[0].OrderedPoints[1].X = 155;
    Throws<InvalidDataException>(() => project.ValidateContract());
}

static void TestAnalysisDeterministic()
{
    var project = Fixture(); var before = project.ToJson();
    var first = CircuitAnalyzer.Analyze(project, project.Circuits[0]);
    var second = CircuitAnalyzer.Analyze(project, project.Circuits[0]);
    Equal(first.LengthMm, second.LengthMm); Equal(first.SelfIntersections, second.SelfIntersections);
    Equal(before, project.ToJson());
}

static void TestSelfIntersection()
{
    var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };
    var circuit = new ManualCircuit { OrderedPoints = [new(500, 500), new(3500, 3500), new(500, 3500), new(3500, 500)] };
    project.Circuits.Add(circuit);
    True(CircuitAnalyzer.Analyze(project, circuit).SelfIntersections > 0, "Crossing was not detected.");
}

static void TestTrainingMetadata()
{
    var project = Fixture(); project.Training.Label = "ACCEPTED"; project.Training.Notes = "Так прокладывать правильно";
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal("ACCEPTED", restored.Training.Label); Equal("Так прокладывать правильно", restored.Training.Notes);
}

static void TestInvalidTrainingLabel()
{
    var project = Fixture(); project.Training.Label = "GOOD";
    Throws<InvalidDataException>(() => project.ValidateContract());
}

static void TestInterCircuitCrossing()
{
    var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };
    var first = new ManualCircuit { OrderedPoints = [new(500, 2000), new(3500, 2000)] };
    var second = new ManualCircuit { OrderedPoints = [new(2000, 500), new(2000, 3500)] };
    project.Circuits.AddRange([first, second]);
    Equal(1, CircuitAnalyzer.Analyze(project, first).InterCircuitIntersections);
}

static void TestDifferentRoutingLayers()
{
    var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };
    var heating = new ManualCircuit { Completed = true, AxisElevationMm = 108, OrderedPoints = [new(500, 2000), new(3500, 2000)] };
    var service = new ManualCircuit
    {
        Completed = true, RoutingLayer = "LOWER_SERVICE_LAYER", SystemRole = "INTERFLOOR_SERVICE_LEG", AxisElevationMm = 135,
        OrderedPoints = [new(2000, 500), new(2000, 3500)]
    };
    project.Circuits.AddRange([heating, service]);
    var heatingAnalysis = CircuitAnalyzer.Analyze(project, heating);
    var serviceAnalysis = CircuitAnalyzer.Analyze(project, service);
    Equal(0, heatingAnalysis.InterCircuitIntersections);
    Equal(1, heatingAnalysis.DifferentLayerCrossingsIgnored);
    True(serviceAnalysis.TopologyPass, "Service leg on a lower layer did not pass bounded topology.");
    service.AxisElevationMm = 120;
    Equal(1, CircuitAnalyzer.Analyze(project, heating).InterCircuitIntersections);
    project.RoutingRules.PipeOuterDiameterMm = 32;
    project.RoutingRules.MinimumLayerAxisSeparationMm = 25;
    Throws<InvalidDataException>(() => project.ValidateContract());
}

static void TestFiftyMillimetreGrid()
{
    var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000, GridSpacingMm = 50 };
    project.Collectors.Add(new Collector { Position = new(2050, 3500) });
    project.Circuits.Add(new ManualCircuit { OrderedPoints = [new(2050, 3500), new(2050, 3000), new(350, 3000)] });
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal(50, restored.GridSpacingMm);
    True(CircuitAnalyzer.Analyze(restored, restored.Circuits[0]).GridAligned, "50 mm points were rejected by the analyzer.");
    restored.Circuits[0].OrderedPoints[1].X = 2025;
    Throws<InvalidDataException>(() => restored.ValidateContract());
}

static void TestBendRadius()
{
    var project = new HomeAuraProject { CanvasWidthMm = 4000, CanvasHeightMm = 4000 };
    var circuit = new ManualCircuit
    {
        Completed = true,
        OrderedPoints = [new(500, 500), new(1500, 500), new(1500, 600), new(2500, 600)]
    };
    project.Circuits.Add(circuit);
    var analysis = CircuitAnalyzer.Analyze(project, circuit);
    Equal(1, analysis.BendRadiusViolationCount);
    True(!analysis.BendRadiusFeasible && !analysis.EngineeringPass, "Two R80 tangencies incorrectly fit inside 100 mm.");
    circuit.OrderedPoints[2].Y = 700;
    True(CircuitAnalyzer.Analyze(project, circuit).BendRadiusFeasible, "Two R80 tangencies did not fit inside 200 mm.");
}

static void TestUnfinishedCircuit()
{
    var project = Fixture(); project.Circuits[0].Completed = false;
    True(!CircuitAnalyzer.Analyze(project, project.Circuits[0]).Pass, "Unfinished circuit passed analysis.");
}

static void TestCollectorAssignment()
{
    var project = Fixture();
    project.Circuits[0].CollectorId = project.Collectors[0].Id;
    project.Circuits[0].SupplyPortIndex = 0; project.Circuits[0].ReturnPortIndex = 1;
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal(project.Collectors[0].Id, restored.Circuits[0].CollectorId);
    Equal(0, restored.Circuits[0].SupplyPortIndex); Equal(1, restored.Circuits[0].ReturnPortIndex);
}

static void TestDuplicateCollectorPort()
{
    var project = Fixture(); var collector = project.Collectors[0];
    project.Circuits[0].CollectorId = collector.Id; project.Circuits[0].SupplyPortIndex = 0; project.Circuits[0].ReturnPortIndex = 1;
    project.Circuits.Add(new ManualCircuit { Name = "Контур 2", CollectorId = collector.Id, SupplyPortIndex = 0, ReturnPortIndex = 2, OrderedPoints = [new(3500, 3200), new(3500, 3000)] });
    Throws<InvalidDataException>(() => project.ValidateContract());
}

static void TestRoomFixture()
{
    var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor", "examples", "room-7000x3200-south-exterior.homeaura.json"));
    var project = HomeAuraProject.FromJson(File.ReadAllText(path));
    Equal(7000, project.CanvasWidthMm); Equal(3200, project.CanvasHeightMm);
    Equal(1, project.Walls.Count(item => item.WallType == "EXTERIOR"));
    var exterior = project.Walls.Single(item => item.WallType == "EXTERIOR");
    Equal(0, exterior.Start.Y); Equal(0, exterior.End.Y);
    Equal(1, project.Collectors.Count); Equal(2, project.Circuits.Count); Equal("ACCEPTED", project.Training.Label);
}

static void TestCollectorRotation()
{
    var project = Fixture(); project.Collectors[0].RotationDegrees = 270;
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal(270, restored.Collectors[0].RotationDegrees);
}

static void TestInvalidCollectorRotation()
{
    var project = Fixture(); project.Collectors[0].RotationDegrees = 45;
    Throws<InvalidDataException>(() => project.ValidateContract());
}

static void TestWallAndWindowContract()
{
    var project = Fixture();
    project.Walls[0].ThicknessMm = 400;
    project.Windows.Add(new WindowOpening { WallId = project.Walls[0].Id, Start = new(1000, 0), End = new(2400, 0), SillHeightMm = 900, OpeningHeightMm = 1400 });
    project.Collectors[0].FloorId = null;
    project.Collectors[0].ServedFloorId = "ATTIC";
    project.Collectors[0].PipeOutletDirection = "UP";
    project.RoutingRules.PipeOuterDiameterMm = 16;
    project.RoutingRules.MinimumBendRadiusMm = 80;
    project.RoutingRules.ExteriorWallSpacingMm = 100;
    project.RoutingRules.FieldSpacingMm = 200;
    project.RoutingRules.MaximumParallelTransitPipesAt100Mm = 3;
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal(400, restored.Walls[0].ThicknessMm);
    Equal(1, restored.Windows.Count);
    Equal(project.Walls[0].Id, restored.Windows[0].WallId);
    Equal("UP", restored.Collectors[0].PipeOutletDirection);
    Equal(3, restored.RoutingRules.MaximumParallelTransitPipesAt100Mm);
    restored.Windows[0].Start = new(1000, 100);
    Throws<InvalidDataException>(() => restored.ValidateContract());
    restored.Windows[0].Start = new(1000, 0);
    restored.Walls[0].ThicknessMm = 20;
    Throws<InvalidDataException>(() => restored.ValidateContract());
}

static void TestHeatingBodyPlacement()
{
    var project = new HomeAuraProject { CanvasWidthMm = 5000, CanvasHeightMm = 4000 };
    project.Rooms.Add(new RoomZone
    {
        Id = "ROOM", Outline = [new(1000, 500), new(4500, 500), new(4500, 3500), new(1000, 3500)]
    });
    project.Walls.Add(new WallSegment
    {
        Id = "WALL", Start = new(1000, 500), End = new(1000, 3500), ThicknessMm = 200
    });
    var circuit = new ManualCircuit
    {
        Completed = true, RoomId = "ROOM", HeatingBodyStartIndex = 1, HeatingBodyEndIndex = 3,
        OrderedPoints = [new(500, 1000), new(1200, 1000), new(1200, 3000), new(3000, 3000), new(500, 3200)]
    };
    project.Circuits.Add(circuit);
    var analysis = CircuitAnalyzer.Analyze(project, circuit);
    True(analysis.HeatingBodyPlacementPass, "Valid body was rejected.");
    True(analysis.TransitWallIntersections > 0, "Transit wall crossing was not classified.");
    circuit.OrderedPoints[1].X = 1100;
    analysis = CircuitAnalyzer.Analyze(project, circuit);
    True(!analysis.HeatingBodyPlacementPass && analysis.HeatingBodyWallIntrusions > 0, "Body inside wall passed.");
    project.ValidateContract();
    var restored = HomeAuraProject.FromJson(project.ToJson());
    Equal("ROOM", restored.Circuits[0].RoomId);
    Equal(1, restored.Circuits[0].HeatingBodyStartIndex);
    Equal(3, restored.Circuits[0].HeatingBodyEndIndex);
}

static void TestOwnerAcceptedExample()
{
    var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor", "examples", "room-7000x3200-south-exterior.homeaura.json"));
    var project = HomeAuraProject.FromJson(File.ReadAllText(path));
    Equal("ACCEPTED", project.Training.Label); Equal(2, project.Circuits.Count);
    var analyses = project.Circuits.Select(item => CircuitAnalyzer.Analyze(project, item)).ToArray();
    Equal(62100d, analyses[0].LengthMm); Equal(57300d, analyses[1].LengthMm);
    Equal(4800d, Math.Abs(analyses[0].LengthMm - analyses[1].LengthMm));
    True(analyses.All(item => item.SelfIntersections == 0), "Owner example has a self-intersection.");
    True(analyses.All(item => item.InterCircuitIntersections == 0), "Owner circuits intersect each other.");
    True(analyses.All(item => item.StartAtCollector && item.EndAtCollector), "Owner circuit is not collector-connected.");
    var southLevels = project.Circuits.SelectMany(item => HorizontalLevels(item, 500)).Distinct().Order().ToArray();
    SequenceEqual(new[] { 100, 200, 300, 500 }, southLevels);
    True(ContainsSequence(project.Circuits[0].OrderedPoints, [(1900,1900),(1900,1500),(1700,1500),(1700,1700),(1500,1700),(1500,1300),(2000,1300)]), "Circuit 1 centre closure changed.");
    True(ContainsSequence(project.Circuits[1].OrderedPoints, [(4400,1500),(4400,2000),(4900,2000),(4900,1800),(4600,1800),(4600,1600),(5100,1600)]), "Circuit 2 centre closure changed.");
}

static void TestOwnerStyleProposal()
{
    var path = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "homeaura-native-editor", "examples", "accepted", "OWNER_EXAMPLE_001_7000x3200.homeaura.json"));
    var source = HomeAuraProject.FromJson(File.ReadAllText(path));
    var proposal = OwnerStyleProposalGenerator.RotateAcceptedExampleCounterClockwise(source);
    Equal(3200, proposal.CanvasWidthMm); Equal(7000, proposal.CanvasHeightMm); Equal("DRAFT", proposal.Training.Label);
    var exterior = proposal.Walls.Single(item => item.WallType == "EXTERIOR");
    Equal(0, exterior.Start.X); Equal(0, exterior.End.X);
    var sourceLengths = source.Circuits.Select(item => CircuitAnalyzer.Analyze(source, item).LengthMm).ToArray();
    var proposalAnalyses = proposal.Circuits.Select(item => CircuitAnalyzer.Analyze(proposal, item)).ToArray();
    SequenceEqual(sourceLengths, proposalAnalyses.Select(item => item.LengthMm));
    True(proposalAnalyses.All(item => item.SelfIntersections == 0 && item.InterCircuitIntersections == 0), "Rotated proposal has crossings.");
    True(proposalAnalyses.All(item => item.StartAtCollector && item.EndAtCollector), "Rotated proposal is disconnected from collector.");
    var westLevels = proposal.Circuits.SelectMany(item => VerticalLevels(item, 500)).Distinct().Order().ToArray();
    SequenceEqual(new[] { 100, 200, 300, 500 }, westLevels);
    Equal(source.Walls[0].ThicknessMm, proposal.Walls[0].ThicknessMm);
    Equal(source.Circuits[0].RoutingLayer, proposal.Circuits[0].RoutingLayer);
}

static IEnumerable<int> HorizontalLevels(ManualCircuit circuit, int maximumY)
{
    for (var index = 1; index < circuit.OrderedPoints.Count; index++)
    {
        var first = circuit.OrderedPoints[index - 1]; var second = circuit.OrderedPoints[index];
        if (first.Y == second.Y && first.Y <= maximumY && Math.Abs(first.X - second.X) >= 1000) yield return first.Y;
    }
}

static IEnumerable<int> VerticalLevels(ManualCircuit circuit, int maximumX)
{
    for (var index = 1; index < circuit.OrderedPoints.Count; index++)
    {
        var first = circuit.OrderedPoints[index - 1]; var second = circuit.OrderedPoints[index];
        if (first.X == second.X && first.X <= maximumX && Math.Abs(first.Y - second.Y) >= 1000) yield return first.X;
    }
}

static bool ContainsSequence(IReadOnlyList<PointMm> points, (int X, int Y)[] expected)
{
    for (var start = 0; start + expected.Length <= points.Count; start++)
        if (expected.Select((point, offset) => points[start + offset].X == point.X && points[start + offset].Y == point.Y).All(value => value)) return true;
    return false;
}

static HomeAuraProject Fixture()
{
    var project = new HomeAuraProject { CanvasWidthMm = 7000, CanvasHeightMm = 3200 };
    project.Walls.AddRange([
        new WallSegment { Start = new(0, 0), End = new(7000, 0), WallType = "EXTERIOR" },
        new WallSegment { Start = new(7000, 0), End = new(7000, 3200) },
        new WallSegment { Start = new(7000, 3200), End = new(0, 3200) },
        new WallSegment { Start = new(0, 3200), End = new(0, 0) },
    ]);
    project.Collectors.Add(new Collector { Position = new(3500, 3200) });
    project.Circuits.Add(new ManualCircuit
    {
        Name = "Контур 1",
        Completed = true,
        OrderedPoints = [new(3400, 3200), new(3400, 2800), new(400, 2800), new(400, 300), new(6600, 300), new(6600, 2600), new(3600, 2600), new(3600, 3200)]
    });
    project.ValidateContract(); return project;
}

static string PointText(PointMm point) => $"{point.X},{point.Y}";
static void True(bool condition, string message) { if (!condition) throw new Exception(message); }
static void Equal<T>(T expected, T actual) { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new Exception($"Expected {expected}, got {actual}."); }
static void SequenceEqual<T>(IEnumerable<T> expected, IEnumerable<T> actual) { if (!expected.SequenceEqual(actual)) throw new Exception("Sequences differ."); }
static void Throws<T>(Action action) where T : Exception { try { action(); } catch (T) { return; } throw new Exception($"Expected {typeof(T).Name}."); }
