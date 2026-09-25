using System.Globalization;
using System.Text;
using System.Text.Json;

namespace HomeAura.NativeEditor;

internal static class Program
{
    [STAThread]
    private static void Main(string[] args)
    {
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.GetCultureInfo("ru-RU");
        ApplicationConfiguration.Initialize();
        if (args.Length == 3 && args[0].Equals("--export-diagnostics", StringComparison.OrdinalIgnoreCase))
        {
            var project = HomeAuraProject.FromJson(File.ReadAllText(args[1], Encoding.UTF8));
            var report = CircuitAnalyzer.AnalyzeProject(project);
            var options = new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            };
            File.WriteAllText(args[2], JsonSerializer.Serialize(report, options) + Environment.NewLine, new UTF8Encoding(false));
            return;
        }
        if (args.Length == 3 && (args[0].Equals("--export-png", StringComparison.OrdinalIgnoreCase)
            || args[0].Equals("--export-png-clean", StringComparison.OrdinalIgnoreCase)))
        {
            var clean = args[0].Equals("--export-png-clean", StringComparison.OrdinalIgnoreCase);
            var project = HomeAuraProject.FromJson(File.ReadAllText(args[1], Encoding.UTF8));
            ExportPng(project, args[2], clean, null, false);
            return;
        }
        if (args.Length == 4 && (args[0].Equals("--export-room-png", StringComparison.OrdinalIgnoreCase)
            || args[0].Equals("--export-room-png-clean", StringComparison.OrdinalIgnoreCase)
            || args[0].Equals("--export-room-png-diagnostics", StringComparison.OrdinalIgnoreCase)))
        {
            var clean = args[0].Equals("--export-room-png-clean", StringComparison.OrdinalIgnoreCase);
            var diagnostics = args[0].Equals("--export-room-png-diagnostics", StringComparison.OrdinalIgnoreCase);
            var project = HomeAuraProject.FromJson(File.ReadAllText(args[1], Encoding.UTF8));
            if (project.Rooms.All(item => item.Id != args[3]))
                throw new InvalidDataException($"Помещение {args[3]} не найдено.");
            ExportPng(project, args[2], clean, args[3], diagnostics);
            return;
        }
        Application.Run(new MainForm(args.FirstOrDefault()));
    }

    private static void ExportPng(HomeAuraProject project, string outputPath, bool clean, string? roomId, bool diagnostics)
    {
        using var host = new Form
        {
            ClientSize = new Size(1144, 836),
            FormBorderStyle = FormBorderStyle.None,
            ShowInTaskbar = false,
            StartPosition = FormStartPosition.Manual,
            Location = new Point(-32000, -32000),
        };
        using var canvas = new EditorCanvas
        {
            Dock = DockStyle.Fill,
            ShowRoomLabels = !clean,
            ShowServiceLabels = !clean,
            ShowCollectorLabels = !clean,
            ShowEngineeringDiagnostics = diagnostics,
            Show3DRouteMarkers = diagnostics,
            ShowRoutingRoleStyles = !clean,
        };
        host.Controls.Add(canvas);
        host.Shown += (_, _) =>
        {
            canvas.NewProject(project);
            if (roomId is not null) canvas.TryFitToRoom(roomId);
            using var image = new Bitmap(canvas.Width, canvas.Height);
            canvas.DrawToBitmap(image, new Rectangle(Point.Empty, image.Size));
            image.Save(outputPath, System.Drawing.Imaging.ImageFormat.Png);
            host.Close();
        };
        Application.Run(host);
    }
}
