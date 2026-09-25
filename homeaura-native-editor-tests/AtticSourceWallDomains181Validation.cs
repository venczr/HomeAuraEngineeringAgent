using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class AtticSourceWallDomains181Validation
{
    private const string D153Sha = "210B36EE163117F6266EBD9234962CCDC1D2035E8ED1A804C35E975C096911DA";
    private const string D180Sha = "C9071982B1A9D96FE77532CEECF7DD22685EE7E05B3A3218AC440D61B776FD4A";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var d153 = Path.Combine(proposals, "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153", "HomeAura_Attic_ExactHouse_D153.homeaura.json");
        var d180 = Path.Combine(proposals, "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180", "HomeAura_TwoFloor_ArchitectureBaseline_D180.homeaura.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181");
        var projectPath = Path.Combine(directory, "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json");
        Equal(D153Sha, Sha(d153), "D153 source");
        Equal(D180Sha, Sha(d180), "D180 source");

        using var before = JsonDocument.Parse(File.ReadAllText(d180));
        using var after = JsonDocument.Parse(File.ReadAllText(projectPath));
        foreach (var property in before.RootElement.EnumerateObject())
        {
            Check(after.RootElement.TryGetProperty(property.Name, out var current), $"D181 lost {property.Name}.");
            if (property.Name != "training_metadata")
                Check(JsonElement.DeepEquals(property.Value, current), $"D181 changed D180 {property.Name}.");
        }
        var metadata = after.RootElement.GetProperty("training_metadata");
        Check(metadata.GetProperty("notes").GetString()!.Contains("no ATTIC wall", StringComparison.Ordinal),
            "D181 did not supersede stale D176 metadata.");

        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        Check(project.Walls.All(item => item.Id.StartsWith("FLOOR_1-", StringComparison.Ordinal)),
            "D181 materialized an ATTIC wall.");
        Check(project.Windows.All(item => item.Id.StartsWith("F1-", StringComparison.Ordinal)),
            "D181 materialized an ATTIC window.");
        Check(project.Circuits.All(item => item.CollectorId != "K2"), "D181 materialized a K2 route.");
        Check(!CircuitAnalyzer.AnalyzeProject(project).InstallationCompletenessPass,
            "D181 incorrectly became installation-ready.");

        using var contractDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory,
            "attic_source_wall_domains_contract.json")));
        var contract = contractDocument.RootElement;
        Equal("EXACT_COMPLEMENT_DOMAIN_CANDIDATES_ONLY_NOT_INSTALLATION_READY",
            contract.GetProperty("status").GetString(), "status");
        Equal(2, contract.GetProperty("complete_residual").GetProperty("component_count").GetInt32(), "residual components");
        Equal(17, contract.GetProperty("opposing_finish_face_gap_candidate_count").GetInt32(), "face gaps");
        Equal(8, contract.GetProperty("narrow_junction_candidate_count").GetInt32(), "junctions");
        Equal(2, contract.GetProperty("wall_partition_candidate_domain_count").GetInt32(), "candidate domains");
        Equal(2, contract.GetProperty("broad_exterior_or_unassigned_residual_count").GetInt32(), "broad residuals");
        var areas = contract.GetProperty("area_balance_m2");
        Near(37.049699, areas.GetProperty("complete_residual").GetDouble(), "residual area");
        Near(9.499525, areas.GetProperty("wall_partition_candidate_union").GetDouble(), "candidate wall area");
        Near(27.550174, areas.GetProperty("broad_exterior_or_unassigned_residual").GetDouble(), "broad residual area");
        Near(0, areas.GetProperty("balance_error_m2").GetDouble(), "area balance");
        var widths = contract.GetProperty("opposing_finish_face_gap_candidates").EnumerateArray()
            .Select(item => item.GetProperty("gap_width_mm").GetInt32()).Distinct().Order().ToArray();
        Check(widths.SequenceEqual(new[] { 108, 140, 163, 216, 220, 221 }), "D181 gap widths changed.");
        var boundary = contract.GetProperty("materialization_boundary");
        Check(boundary.GetProperty("ATTIC_project_wall_count_added").GetInt32() == 0 &&
              boundary.GetProperty("K2_route_count_added").GetInt32() == 0 &&
              !boundary.GetProperty("sleeves_added").GetBoolean() &&
              !boundary.GetProperty("installation_ready").GetBoolean(), "D181 materialization boundary changed.");
        foreach (var field in new[] { "windows", "door_and_threshold_openings", "slab_holes_and_penetrations" })
            Check(boundary.GetProperty(field).GetString()!.Contains("UNVERIFIED", StringComparison.Ordinal),
                $"D181 {field} was invented.");

        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifest.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"Manifest mismatch: {path}");
        }
        var package = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181.zip");
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length, "D181 ZIP member count changed.");
    }

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Near(double expected, double actual, string label)
    { if (Math.Abs(expected - actual) > 0.000001) throw new InvalidDataException($"{label}: {actual}"); }
    private static void Equal<T>(T expected, T actual, string label)
    { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new InvalidDataException($"{label}: {actual}"); }
    private static void Check(bool value, string message)
    { if (!value) throw new InvalidDataException(message); }
}
