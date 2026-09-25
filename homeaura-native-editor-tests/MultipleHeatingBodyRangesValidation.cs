using HomeAura.NativeEditor;

internal static class MultipleHeatingBodyRangesValidation
{
    public static void Run()
    {
        var project = Fixture();
        project.ValidateContract();
        var circuit = project.Circuits.Single(item => item.Id == "MULTI");
        var analysis = CircuitAnalyzer.Analyze(project, circuit);

        Check(analysis.HeatingBodyPointCount == 6, "Two three-point body ranges were not counted independently.");
        Check(analysis.HeatingBodyInsideAssignedRoom, "Valid separated body ranges were reported outside their room.");
        Check(analysis.HeatingBodyWallIntrusions == 0 && analysis.HeatingBodyWallIntrusionDetails.Count == 0,
            "Middle transit was incorrectly included in body/wall intrusion analysis.");
        Check(analysis.TransitWallIntersections == 1,
            "The middle transit segment crossing the wall was not classified as transit.");
        Check(CircuitAnalyzer.IsHeatingBodySegment(circuit, 0) && CircuitAnalyzer.IsHeatingBodySegment(circuit, 1) &&
              !CircuitAnalyzer.IsHeatingBodySegment(circuit, 2) &&
              CircuitAnalyzer.IsHeatingBodySegment(circuit, 3) && CircuitAnalyzer.IsHeatingBodySegment(circuit, 4),
            "Renderer-facing segment classification does not preserve the solid/dashed/solid runs.");

        var restored = HomeAuraProject.FromJson(project.ToJson());
        var restoredCircuit = restored.Circuits.Single(item => item.Id == "MULTI");
        Check(restoredCircuit.HeatingBodyStartIndex is null && restoredCircuit.HeatingBodyEndIndex is null,
            "Multi-range round-trip unexpectedly materialized legacy indices.");
        Check(restoredCircuit.HeatingBodyRanges.Count == 2 &&
              restoredCircuit.HeatingBodyRanges[0].StartIndex == 0 && restoredCircuit.HeatingBodyRanges[0].EndIndex == 2 &&
              restoredCircuit.HeatingBodyRanges[1].StartIndex == 3 && restoredCircuit.HeatingBodyRanges[1].EndIndex == 5,
            "Multi-range JSON round-trip changed the ordered ranges.");

        var accepted = project.DeepClone();
        accepted.Training.Label = "ACCEPTED";
        var rotated = OwnerStyleProposalGenerator.RotateAcceptedExampleCounterClockwise(accepted);
        var rotatedCircuit = rotated.Circuits.Single(item => item.Name == circuit.Name);
        Check(rotatedCircuit.HeatingBodyRanges.Count == 2 &&
              !ReferenceEquals(rotatedCircuit.HeatingBodyRanges, accepted.Circuits[0].HeatingBodyRanges) &&
              !ReferenceEquals(rotatedCircuit.HeatingBodyRanges[0], accepted.Circuits[0].HeatingBodyRanges[0]),
            "Owner-style proposal did not deep-copy heating_body_ranges.");

        var invalid = project.DeepClone();
        invalid.Circuits[0].HeatingBodyStartIndex = 0;
        invalid.Circuits[0].HeatingBodyEndIndex = 2;
        Throws<InvalidDataException>(() => invalid.ValidateContract(), "Legacy and multi-range body metadata were accepted together.");
        invalid = project.DeepClone();
        invalid.Circuits[0].HeatingBodyRanges.Reverse();
        Throws<InvalidDataException>(() => invalid.ValidateContract(), "Unsorted body ranges were accepted.");

        var floorService = new ManualCircuit
        {
            Id = "K1-LOWER-SERVICE",
            Name = "Нижняя подводка K1",
            RoutingLayer = "LOWER_SERVICE_LAYER",
            SystemRole = "FLOOR_SERVICE_LEG",
            OrderedPoints = [new(1000, 5500), new(2000, 5500)],
            Completed = true,
        };
        project.Circuits.Add(floorService);
        var serviceRestored = HomeAuraProject.FromJson(project.ToJson()).Circuits.Single(item => item.Id == floorService.Id);
        Check(serviceRestored.SystemRole == "FLOOR_SERVICE_LEG", "FLOOR_SERVICE_LEG did not survive round-trip.");
    }

    private static HomeAuraProject Fixture()
    {
        var project = new HomeAuraProject { CanvasWidthMm = 6000, CanvasHeightMm = 6000 };
        project.Rooms.Add(new RoomZone
        {
            Id = "ROOM",
            Name = "Комната",
            Outline = [new(1000, 1000), new(5000, 1000), new(5000, 5000), new(1000, 5000)],
            LabelPosition = new(1500, 4500),
        });
        project.Walls.Add(new WallSegment
        {
            Id = "MIDDLE-WALL",
            WallType = "INTERIOR",
            ThicknessMm = 200,
            Start = new(3000, 1000),
            End = new(3000, 5000),
        });
        project.Circuits.Add(new ManualCircuit
        {
            Id = "MULTI",
            Name = "Два тела через транзит",
            RoomId = "ROOM",
            Completed = true,
            OrderedPoints =
            [
                new(1500, 1500), new(2500, 1500), new(2500, 2500),
                new(3500, 2500), new(3500, 3500), new(4500, 3500),
            ],
            HeatingBodyRanges =
            [
                new HeatingBodyRange { StartIndex = 0, EndIndex = 2 },
                new HeatingBodyRange { StartIndex = 3, EndIndex = 5 },
            ],
        });
        return project;
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static void Throws<T>(Action action, string message) where T : Exception
    {
        try { action(); }
        catch (T) { return; }
        throw new InvalidOperationException(message);
    }
}
