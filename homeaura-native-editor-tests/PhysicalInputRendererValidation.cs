using System.Drawing;
using System.Reflection;
using HomeAura.NativeEditor;

internal static class PhysicalInputRendererValidation
{
    private static readonly Color Background = Color.FromArgb(12, 22, 29);
    private static readonly Color ExteriorWall = Color.FromArgb(196, 181, 155);
    private static readonly Color InteriorWall = Color.FromArgb(218, 231, 236);
    private static readonly Color WindowBlue = Color.FromArgb(125, 211, 252);
    private static readonly Color VerifiedDoorGreen = Color.FromArgb(74, 222, 128);
    private static readonly Color UnverifiedAmber = Color.FromArgb(251, 191, 36);
    private static readonly Color OpeningViolet = Color.FromArgb(216, 180, 254);
    private static readonly Color ExclusionRed = Color.FromArgb(248, 113, 113);
    private static readonly Color CollectorBlue = Color.FromArgb(96, 165, 250);

    public static void Run()
    {
        var project = Fixture();

        using (var fitCanvas = CreateCanvas(project, activeFloorId: null))
        {
            Check(fitCanvas.ActiveFloorId is null, "A new canvas unexpectedly selected a floor.");
            Check(fitCanvas.TryFitToRoom("R-ATTIC"), "TryFitToRoom rejected the ATTIC room fixture.");
            Equal("ATTIC", fitCanvas.ActiveFloorId,
                "TryFitToRoom did not select the room's floor before fitting its bounds.");
            Check(fitCanvas.TryFitToRoom("R-FLOOR-1"), "TryFitToRoom rejected the FLOOR_1 room fixture.");
            Equal("FLOOR_1", fitCanvas.ActiveFloorId,
                "TryFitToRoom did not switch back to the FLOOR_1 room's floor.");
        }

        var readiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(project);
        Check(readiness.Applicable, "The cross-floor collector did not make physical input readiness applicable.");
        SequenceEqual(["W-UNSCOPED"], readiness.UnscopedWallIds,
            "The renderer's conservatively visible unscoped wall was not exposed by diagnostics.");
        SequenceEqual(["WIN-UNSCOPED"], readiness.UnscopedWindowIds,
            "The renderer's conservatively visible unscoped window was not exposed by diagnostics.");
        Check(readiness.ReasonCodes.Contains("UNSCOPED_ARCHITECTURE_OBJECTS", StringComparer.Ordinal),
            "Unscoped architecture did not fail closed in physical input diagnostics.");

        using var floorCanvas = CreateCanvas(project, "FLOOR_1");
        using var atticCanvas = CreateCanvas(project, "ATTIC");
        using var floor = Render(floorCanvas);
        using var attic = Render(atticCanvas);

        AssertCoincidentFloorObjects(floorCanvas, atticCanvas, floor, attic);
        AssertCollectors(floorCanvas, atticCanvas, floor, attic);
        AssertOpeningFacesAndExclusion(floorCanvas, atticCanvas, floor, attic);
        AssertUnscopedArchitecture(floorCanvas, atticCanvas, floor, attic);
    }

    private static void AssertCoincidentFloorObjects(
        EditorCanvas floorCanvas,
        EditorCanvas atticCanvas,
        Bitmap floor,
        Bitmap attic)
    {
        var wallPointFloor = ScreenPoint(floorCanvas, 1000, 500);
        var wallPointAttic = ScreenPoint(atticCanvas, 1000, 500);
        Check(HasColorNear(floor, wallPointFloor, ExteriorWall, 2, 28),
            "FLOOR_1 did not render its tagged exterior wall at the coincident wall axis.");
        Check(!HasColorNear(floor, wallPointFloor, InteriorWall, 2, 28),
            "FLOOR_1 also rendered the coincident ATTIC wall.");
        Check(HasColorNear(attic, wallPointAttic, InteriorWall, 2, 28),
            "ATTIC did not render its tagged interior wall at the coincident wall axis.");
        Check(!HasColorNear(attic, wallPointAttic, ExteriorWall, 2, 28),
            "ATTIC also rendered the coincident FLOOR_1 wall.");

        var windowCentreFloor = ScreenPoint(floorCanvas, 1100, 1000);
        var windowCentreAttic = ScreenPoint(atticCanvas, 1100, 1000);
        Check(HasColorNear(floor, windowCentreFloor, WindowBlue, 2, 30) &&
              HasColorNear(attic, windowCentreAttic, WindowBlue, 2, 30),
            "The active floor's coincident window was not rendered in window blue.");
        var wideWindowProbeFloor = new PointF(windowCentreFloor.X, windowCentreFloor.Y + 12);
        var wideWindowProbeAttic = new PointF(windowCentreAttic.X, windowCentreAttic.Y + 12);
        Check(HasColorNear(floor, wideWindowProbeFloor, WindowBlue, 1, 35),
            "FLOOR_1 did not render its 300 mm-wall window width.");
        Check(!HasColorNear(attic, wideWindowProbeAttic, WindowBlue, 1, 35),
            "ATTIC also rendered the wider coincident FLOOR_1 window.");

        var doorPointFloor = ScreenPoint(floorCanvas, 1100, 2000);
        var doorPointAttic = ScreenPoint(atticCanvas, 1100, 2000);
        Check(HasColorNear(floor, doorPointFloor, VerifiedDoorGreen, 2, 32),
            "FLOOR_1 did not render its verified coincident door in green.");
        Check(!HasColorNear(floor, doorPointFloor, UnverifiedAmber, 2, 32),
            "FLOOR_1 also rendered the coincident unverified ATTIC door.");
        Check(HasColorNear(attic, doorPointAttic, UnverifiedAmber, 2, 32),
            "ATTIC did not render its unverified coincident door in amber.");
        Check(!HasColorNear(attic, doorPointAttic, VerifiedDoorGreen, 2, 32),
            "ATTIC also rendered the coincident verified FLOOR_1 door.");

        var routePointFloor = ScreenPoint(floorCanvas, 1100, 2500);
        var routePointAttic = ScreenPoint(atticCanvas, 1100, 2500);
        var floorRoute = ColorTranslator.FromHtml("#FF2020");
        var atticRoute = ColorTranslator.FromHtml("#E020FF");
        Check(HasColorNear(floor, routePointFloor, floorRoute, 2, 28),
            "FLOOR_1 did not render its tagged coincident route.");
        Check(!HasColorNear(floor, routePointFloor, atticRoute, 2, 28),
            "FLOOR_1 also rendered the coincident ATTIC route.");
        Check(HasColorNear(attic, routePointAttic, atticRoute, 2, 28),
            "ATTIC did not render its tagged coincident route.");
        Check(!HasColorNear(attic, routePointAttic, floorRoute, 2, 28),
            "ATTIC also rendered the coincident FLOOR_1 route.");

        var crossFloorRoute = ColorTranslator.FromHtml("#22D3EE");
        Check(HasColorNear(floor, ScreenPoint(floorCanvas, 2850, 2500), crossFloorRoute, 2, 28) &&
              HasColorNear(attic, ScreenPoint(atticCanvas, 2850, 2500), crossFloorRoute, 2, 28),
            "The explicitly cross-floor route was incorrectly hidden on one of its two floors.");
    }

    private static void AssertCollectors(
        EditorCanvas floorCanvas,
        EditorCanvas atticCanvas,
        Bitmap floor,
        Bitmap attic)
    {
        var floorCollectorOnFloor = ScreenPoint(floorCanvas, 700, 3200);
        var atticCollectorOnFloor = ScreenPoint(floorCanvas, 1500, 3200);
        var floorCollectorOnAttic = ScreenPoint(atticCanvas, 700, 3200);
        var atticCollectorOnAttic = ScreenPoint(atticCanvas, 1500, 3200);

        Check(HasCollectorPalette(floor, floorCollectorOnFloor),
            "FLOOR_1 did not render its installed collector.");
        Check(!HasCollectorPalette(floor, atticCollectorOnFloor),
            "FLOOR_1 rendered the collector installed on ATTIC.");
        Check(!HasCollectorPalette(attic, floorCollectorOnAttic),
            "ATTIC rendered the collector installed on FLOOR_1.");
        Check(HasCollectorPalette(attic, atticCollectorOnAttic),
            "ATTIC did not render its installed collector.");
    }

    private static void AssertOpeningFacesAndExclusion(
        EditorCanvas floorCanvas,
        EditorCanvas atticCanvas,
        Bitmap floor,
        Bitmap attic)
    {
        Check(HasColorInWorldBox(floor, floorCanvas, 2380, 380, 2720, 720, OpeningViolet, 45),
            "FLOOR_1 did not render the FLOOR_1 face of the interfloor opening.");
        Check(!HasColorInWorldBox(attic, atticCanvas, 2380, 380, 2720, 720, OpeningViolet, 45),
            "ATTIC rendered the FLOOR_1 face of the interfloor opening.");
        Check(HasColorInWorldBox(attic, atticCanvas, 2980, 380, 3320, 720, OpeningViolet, 45),
            "ATTIC did not render the ATTIC face of the interfloor opening.");

        Check(HasColorInWorldBox(floor, floorCanvas, 2980, 380, 3320, 720, ExclusionRed, 45),
            "The FLOOR_1 generic exclusion was not rendered with exclusion styling.");
        Check(!HasColorInWorldBox(floor, floorCanvas, 2980, 380, 3320, 720, OpeningViolet, 45),
            "A generic ExclusionZone was incorrectly rendered as the ATTIC opening face.");
    }

    private static void AssertUnscopedArchitecture(
        EditorCanvas floorCanvas,
        EditorCanvas atticCanvas,
        Bitmap floor,
        Bitmap attic)
    {
        foreach (var (canvas, bitmap, floorId) in new[]
                 {
                     (floorCanvas, floor, "FLOOR_1"),
                     (atticCanvas, attic, "ATTIC"),
                 })
        {
            Check(HasColorNear(bitmap, ScreenPoint(canvas, 2300, 1500), UnverifiedAmber, 2, 32),
                $"{floorId} hid the conservatively visible wall without floor_id or lost its amber diagnostic.");
            Check(HasColorNear(bitmap, ScreenPoint(canvas, 2800, 1500), UnverifiedAmber, 2, 32),
                $"{floorId} hid the conservatively visible window without floor_id or lost its amber diagnostic.");
        }
    }

    private static HomeAuraProject Fixture()
    {
        var floorOutline = Rectangle(0, 0, 4000, 4000);
        var roomOutline = Rectangle(100, 200, 1900, 3500);
        var project = new HomeAuraProject
        {
            SchemaVersion = "1.1",
            CanvasWidthMm = 4000,
            CanvasHeightMm = 4000,
            GridSpacingMm = 100,
            Levels =
            [
                new FloorLevel { Id = "FLOOR_1", Name = "Floor 1", Outline = Clone(floorOutline), LabelPosition = new(100, 3900) },
                new FloorLevel { Id = "ATTIC", Name = "Attic", Outline = Clone(floorOutline), LabelPosition = new(100, 3900) },
            ],
            Rooms =
            [
                new RoomZone { Id = "R-FLOOR-1", FloorId = "FLOOR_1", Name = "Floor room", Outline = Clone(roomOutline), LabelPosition = new(200, 3400) },
                new RoomZone { Id = "R-ATTIC", FloorId = "ATTIC", Name = "Attic room", Outline = Clone(roomOutline), LabelPosition = new(200, 3400) },
            ],
            Walls =
            [
                Wall("W-FLOOR-1", "FLOOR_1", 400, 500, 1800, 500, "EXTERIOR", 120),
                Wall("W-ATTIC", "ATTIC", 400, 500, 1800, 500, "INTERIOR", 120),
                Wall("W-WIN-FLOOR-1", "FLOOR_1", 400, 1000, 1800, 1000, "EXTERIOR", 300),
                Wall("W-WIN-ATTIC", "ATTIC", 400, 1000, 1800, 1000, "INTERIOR", 50),
                Wall("W-DOOR-FLOOR-1", "FLOOR_1", 400, 2000, 1800, 2000, "INTERIOR", 100),
                Wall("W-DOOR-ATTIC", "ATTIC", 400, 2000, 1800, 2000, "INTERIOR", 100),
                Wall("W-UNSCOPED", null, 2200, 1500, 3500, 1500, "EXTERIOR", 120),
            ],
            Windows =
            [
                Window("WIN-FLOOR-1", "FLOOR_1", "W-WIN-FLOOR-1", 600, 1000, 1600, 1000),
                Window("WIN-ATTIC", "ATTIC", "W-WIN-ATTIC", 600, 1000, 1600, 1000),
                Window("WIN-UNSCOPED", null, "W-UNSCOPED", 2500, 1500, 3200, 1500),
            ],
            DoorOpenings =
            [
                new DoorOpening
                {
                    Id = "DOOR-FLOOR-1", FloorId = "FLOOR_1", WallId = "W-DOOR-FLOOR-1",
                    Start = new(600, 2000), End = new(1600, 2000),
                    PhysicalVerification = new PhysicalVerification { Status = "INDEPENDENTLY_VERIFIED" },
                },
                new DoorOpening
                {
                    Id = "DOOR-ATTIC", FloorId = "ATTIC", WallId = "W-DOOR-ATTIC",
                    Start = new(600, 2000), End = new(1600, 2000),
                    PhysicalVerification = new PhysicalVerification { Status = "UNVERIFIED" },
                },
            ],
            Exclusions =
            [
                new ExclusionZone
                {
                    Id = "X-GENERIC-FLOOR-1", FloorId = "FLOOR_1", Name = "Generic exclusion",
                    Outline = Rectangle(3000, 400, 3300, 700),
                },
            ],
            InterfloorOpenings =
            [
                new InterfloorOpening
                {
                    Id = "IO-01", FromFloorId = "FLOOR_1", ToFloorId = "ATTIC",
                    FromFloorFace = new InterfloorOpeningFace
                    {
                        FloorId = "FLOOR_1", VerifiedPlanOutlineMm = Rectangle(2400, 400, 2700, 700),
                    },
                    ToFloorFace = new InterfloorOpeningFace
                    {
                        FloorId = "ATTIC", VerifiedPlanOutlineMm = Rectangle(3000, 400, 3300, 700),
                    },
                },
            ],
            Collectors =
            [
                Collector("C-FLOOR-1", 700, 3200, "FLOOR_1", "FLOOR_1"),
                Collector("C-ATTIC", 1500, 3200, "ATTIC", "ATTIC"),
                new Collector
                {
                    Id = "C-CROSS", Position = new(3300, 3200), Ports = 2,
                    FloorId = "FLOOR_1", ServedFloorId = "ATTIC", VisibleOnPlan = false,
                },
            ],
            Circuits =
            [
                Circuit("ROUTE-FLOOR-1", "#FF2020", "R-FLOOR-1", "C-FLOOR-1", 400, 2500, 1800, 2500),
                Circuit("ROUTE-ATTIC", "#E020FF", "R-ATTIC", "C-ATTIC", 400, 2500, 1800, 2500),
                Circuit("ROUTE-CROSS", "#22D3EE", "R-ATTIC", "C-CROSS", 2200, 2500, 3500, 2500),
            ],
        };
        return project;
    }

    private static WallSegment Wall(
        string id,
        string? floorId,
        int startX,
        int startY,
        int endX,
        int endY,
        string wallType,
        int thicknessMm) =>
        new()
        {
            Id = id, FloorId = floorId, Start = new(startX, startY), End = new(endX, endY),
            WallType = wallType, ThicknessMm = thicknessMm,
        };

    private static WindowOpening Window(
        string id,
        string? floorId,
        string wallId,
        int startX,
        int startY,
        int endX,
        int endY) =>
        new()
        {
            Id = id, FloorId = floorId, WallId = wallId,
            Start = new(startX, startY), End = new(endX, endY),
        };

    private static Collector Collector(string id, int x, int y, string floorId, string servedFloorId) =>
        new()
        {
            Id = id, Position = new(x, y), Ports = 2, FloorId = floorId, ServedFloorId = servedFloorId,
            ReferenceWidthMm = 400, ReferenceDepthMm = 100,
        };

    private static ManualCircuit Circuit(
        string id,
        string color,
        string roomId,
        string collectorId,
        int startX,
        int startY,
        int endX,
        int endY) =>
        new()
        {
            Id = id, Name = id, Color = color, RoomId = roomId, CollectorId = collectorId,
            Completed = true, RoutingLayer = "HEATING_PLANE", SystemRole = "FLOOR_HEATING_LOOP",
            OrderedPoints = [new(startX, startY), new(endX, endY)],
        };

    private static EditorCanvas CreateCanvas(HomeAuraProject project, string? activeFloorId)
    {
        var canvas = new EditorCanvas
        {
            Size = new Size(720, 720),
            ShowGrid = false,
            ShowRoomLabels = false,
            ShowServiceLabels = false,
            ShowCollectorLabels = false,
            ShowEngineeringDiagnostics = false,
            Show3DRouteMarkers = false,
            ShowRoutingRoleStyles = false,
        };
        canvas.CreateControl();
        canvas.NewProject(project);
        canvas.ActiveFloorId = activeFloorId;
        canvas.FitToProject();
        return canvas;
    }

    private static Bitmap Render(EditorCanvas canvas)
    {
        var bitmap = new Bitmap(canvas.Width, canvas.Height);
        using (var graphics = Graphics.FromImage(bitmap)) graphics.Clear(Background);
        canvas.DrawToBitmap(bitmap, new Rectangle(Point.Empty, bitmap.Size));
        return bitmap;
    }

    private static PointF ScreenPoint(EditorCanvas canvas, int x, int y)
    {
        var method = typeof(EditorCanvas).GetMethod(
            "WorldToScreen",
            BindingFlags.Instance | BindingFlags.NonPublic,
            binder: null,
            types: [typeof(PointMm)],
            modifiers: null) ?? throw new MissingMethodException(typeof(EditorCanvas).FullName, "WorldToScreen(PointMm)");
        return (PointF)(method.Invoke(canvas, [new PointMm(x, y)]) ??
                        throw new InvalidOperationException("WorldToScreen returned null."));
    }

    private static bool HasCollectorPalette(Bitmap bitmap, PointF centre) =>
        HasColorNear(bitmap, centre, ExclusionRed, 28, 36) &&
        HasColorNear(bitmap, centre, CollectorBlue, 28, 36);

    private static bool HasColorNear(Bitmap bitmap, PointF point, Color expected, int radius, int tolerance)
    {
        var centreX = (int)Math.Round(point.X);
        var centreY = (int)Math.Round(point.Y);
        for (var y = Math.Max(0, centreY - radius); y <= Math.Min(bitmap.Height - 1, centreY + radius); y++)
        for (var x = Math.Max(0, centreX - radius); x <= Math.Min(bitmap.Width - 1, centreX + radius); x++)
            if (ColorDistance(bitmap.GetPixel(x, y), expected) <= tolerance) return true;
        return false;
    }

    private static bool HasColorInWorldBox(
        Bitmap bitmap,
        EditorCanvas canvas,
        int minX,
        int minY,
        int maxX,
        int maxY,
        Color expected,
        int tolerance)
    {
        var first = ScreenPoint(canvas, minX, minY);
        var second = ScreenPoint(canvas, maxX, maxY);
        var left = Math.Max(0, (int)Math.Floor(Math.Min(first.X, second.X)));
        var right = Math.Min(bitmap.Width - 1, (int)Math.Ceiling(Math.Max(first.X, second.X)));
        var top = Math.Max(0, (int)Math.Floor(Math.Min(first.Y, second.Y)));
        var bottom = Math.Min(bitmap.Height - 1, (int)Math.Ceiling(Math.Max(first.Y, second.Y)));
        for (var y = top; y <= bottom; y++)
        for (var x = left; x <= right; x++)
            if (ColorDistance(bitmap.GetPixel(x, y), expected) <= tolerance) return true;
        return false;
    }

    private static int ColorDistance(Color first, Color second) =>
        Math.Abs(first.R - second.R) + Math.Abs(first.G - second.G) + Math.Abs(first.B - second.B);

    private static List<PointMm> Rectangle(int minX, int minY, int maxX, int maxY) =>
        [new(minX, minY), new(maxX, minY), new(maxX, maxY), new(minX, maxY)];

    private static List<PointMm> Clone(IEnumerable<PointMm> points) => points.Select(item => item.Clone()).ToList();

    private static void Equal(string expected, string? actual, string message)
    {
        if (!string.Equals(expected, actual, StringComparison.Ordinal))
            throw new InvalidOperationException($"{message} Expected {expected}, got {actual ?? "<null>"}.");
    }

    private static void SequenceEqual(IEnumerable<string> expected, IEnumerable<string> actual, string message)
    {
        if (!expected.SequenceEqual(actual, StringComparer.Ordinal))
            throw new InvalidOperationException($"{message} Expected [{string.Join(", ", expected)}], got [{string.Join(", ", actual)}].");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
