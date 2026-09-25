using System.Drawing;
using HomeAura.NativeEditor;

internal static class RoundedCleanRenderValidation
{
    public static void Run()
    {
        var project = new HomeAuraProject
        {
            CanvasWidthMm = 1000,
            CanvasHeightMm = 1000,
            GridSpacingMm = 100,
        };
        project.RoutingRules.MinimumBendRadiusMm = 80;
        var circuit = new ManualCircuit
        {
            Id = "SYNTHETIC-R80",
            Name = "Synthetic R80 clean render",
            Color = "#FF0000",
            RoutingLayer = "HEATING_PLANE",
            SystemRole = "FLOOR_HEATING_LOOP",
            Completed = true,
            OrderedPoints = [new(200, 200), new(800, 200), new(800, 800)],
        };
        project.Circuits.Add(circuit);

        var rounded = CircuitAnalyzer.SampleRoundedPlanAxis(
            circuit,
            project.RoutingRules.MinimumBendRadiusMm,
            maximumSagittaMm: 0.05);
        var analysis = CircuitAnalyzer.Analyze(project, circuit);
        var expectedLength = 1200 - 160 + 80 * Math.PI / 2;

        Check(rounded.FullyMaterialized && rounded.TurnCount == 1 && rounded.FilletCount == 1,
            "The feasible horizontal corner was not materialized as one R80 fillet.");
        Close(expectedLength, rounded.ExactLengthMm, 0.000001,
            "Rounded plan geometry did not use the exact R80 tangent/arc length.");
        Close(analysis.RoundedAxisLengthMm, rounded.ExactLengthMm, 0.000001,
            "Renderer geometry and CircuitAnalyzer rounded length diverged.");
        Check(rounded.MaximumSagittaMm <= 0.05 + 0.000001,
            "Horizontal arc sampling exceeded its conservative sagitta bound.");
        Check(rounded.SampledLengthMm <= rounded.ExactLengthMm + 0.000001 &&
              rounded.LengthUnderestimateMm < 0.05,
            "Sampled R80 polyline is not a bounded lower approximation of the exact arc.");
        Check(Contains(rounded.SampledPoints, 720, 200) && Contains(rounded.SampledPoints, 800, 280) &&
              !Contains(rounded.SampledPoints, 800, 200),
            "R80 tangent points were not substituted for the sharp control vertex.");

        using var clean = Render(project, showRoutingRoleStyles: false);
        using var engineering = Render(project, showRoutingRoleStyles: true);
        var sharpVertex = new Point(296, 296);
        var background = Color.FromArgb(12, 22, 29);
        var cleanStraight = clean.GetPixel(200, 296);
        Check(cleanStraight.R > 180 && cleanStraight.G < 100 && cleanStraight.B < 100,
            "Clean render no longer draws the circuit as a solid route.");
        Check(ColorDistance(clean.GetPixel(sharpVertex.X, sharpVertex.Y), background) < 12,
            "Clean render still paints the sharp 90-degree control vertex.");
        var engineeringVertex = engineering.GetPixel(sharpVertex.X, sharpVertex.Y);
        Check(engineeringVertex.R > 180 && engineeringVertex.G < 100 && engineeringVertex.B < 100,
            "Engineering render no longer preserves the sharp control geometry.");
    }

    private static Bitmap Render(HomeAuraProject project, bool showRoutingRoleStyles)
    {
        using var canvas = new EditorCanvas
        {
            Size = new Size(400, 400),
            ShowGrid = false,
            ShowRoomLabels = false,
            ShowServiceLabels = false,
            ShowCollectorLabels = false,
            ShowEngineeringDiagnostics = false,
            Show3DRouteMarkers = false,
            ShowRoutingRoleStyles = showRoutingRoleStyles,
        };
        canvas.CreateControl();
        canvas.NewProject(project);
        var bitmap = new Bitmap(canvas.Width, canvas.Height);
        canvas.DrawToBitmap(bitmap, new Rectangle(Point.Empty, bitmap.Size));
        return bitmap;
    }

    private static bool Contains(IEnumerable<Point3Mm> points, double x, double y) =>
        points.Any(point => Math.Abs(point.X - x) <= 0.000001 && Math.Abs(point.Y - y) <= 0.000001);

    private static int ColorDistance(Color first, Color second) =>
        Math.Abs(first.R - second.R) + Math.Abs(first.G - second.G) + Math.Abs(first.B - second.B);

    private static void Close(double expected, double actual, double tolerance, string message)
    {
        if (Math.Abs(expected - actual) > tolerance)
            throw new InvalidOperationException($"{message} Expected {expected:R}, got {actual:R}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
