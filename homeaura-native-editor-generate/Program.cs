using System.Text;
using System.Text.Json;
using HomeAura.NativeEditor;

if (args.Length != 3 || args[0] != "owner-style-r90")
{
    Console.Error.WriteLine("Usage: owner-style-r90 <accepted-source.homeaura.json> <proposal.homeaura.json>");
    return 2;
}

var source = HomeAuraProject.FromJson(File.ReadAllText(args[1], Encoding.UTF8));
var proposal = OwnerStyleProposalGenerator.RotateAcceptedExampleCounterClockwise(source);
var output = Path.GetFullPath(args[2]);
Directory.CreateDirectory(Path.GetDirectoryName(output)!);
File.WriteAllText(output, proposal.ToJson() + Environment.NewLine, new UTF8Encoding(false));

var analyses = proposal.Circuits.Select(item => CircuitAnalyzer.Analyze(proposal, item)).ToArray();
var report = new
{
    proposal_id = "AI_PROPOSAL_001",
    status = "DRAFT_OWNER_REVIEW_REQUIRED",
    source = Path.GetFullPath(args[1]),
    output,
    room_mm = new[] { proposal.CanvasWidthMm, proposal.CanvasHeightMm },
    exterior_wall = "WEST",
    dense_wall_pass_x_mm = new[] { 100, 200, 300 },
    first_field_pass_x_mm = 500,
    circuits = analyses.Select(item => new
    {
        item.Name, item.PointCount, item.LengthMm, item.SelfIntersections,
        item.InterCircuitIntersections, item.StartAtCollector, item.EndAtCollector
    }),
    length_difference_mm = Math.Abs(analyses[0].LengthMm - analyses[1].LengthMm),
    owner_decision = "PENDING"
};
var reportPath = Path.ChangeExtension(output, ".report.json");
File.WriteAllText(reportPath, JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine, new UTF8Encoding(false));
Console.WriteLine(output);
Console.WriteLine(reportPath);
return 0;
