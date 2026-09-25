using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;

internal static class R03OwnerBodyFixture182Validation
{
    private const string D181Sha = "253E0DD8DBD59227BBE0147DBFECB201EDAAD56F19E4B3B0511B22254B8C55F2";
    private const string ContractSha = "BC4F7A3FAB3969E83516F9E82772A3F7727BAF9870F93ECB094D3691361E08D8";
    private const string PngSha = "85B84007072B1EB1DDCA4617188E8C13D3153DF3083889EC2DB2702B9427B424";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var d181 = Path.Combine(proposals, "HA_TWO_FLOOR_ATTIC_SOURCE_WALL_DOMAINS_181",
            "HomeAura_TwoFloor_SourceWallDomains_D181.homeaura.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_R03_OWNER_BODY_FIXTURE_182");
        var contractPath = Path.Combine(directory, "r03_owner_body_fixture_contract.json");
        var pngPath = Path.Combine(directory, "HomeAura_R03_D182_OwnerBodyFixture.png");
        Equal(D181Sha, Sha(d181), "D181 source");
        Equal(ContractSha, Sha(contractPath), "D182 contract");
        Equal(PngSha, Sha(pngPath), "D182 PNG");

        using var document = JsonDocument.Parse(File.ReadAllText(contractPath));
        var rootElement = document.RootElement;
        Equal("BODY_HARD_GATES_PASS_TRANSIT_PENDING", rootElement.GetProperty("status").GetString(), "status");
        Check(!rootElement.GetProperty("publishable_as_project").GetBoolean() &&
              !rootElement.GetProperty("official_project_modified").GetBoolean() &&
              !rootElement.GetProperty("complete_route_counts_changed").GetBoolean(),
            "D182 crossed its evidence-only boundary.");

        var search = rootElement.GetProperty("search");
        Equal(380, search.GetProperty("evaluated_candidate_count").GetInt32(), "search count");
        Equal(338, search.GetProperty("coverage_96_percent_candidate_count").GetInt32(), "coverage candidates");
        Equal(247, search.GetProperty("all_numeric_gate_candidate_count").GetInt32(), "all-gate candidates");

        var routes = rootElement.GetProperty("routes_grid_100mm");
        var seam = routes.GetProperty("C08_body_ranges").GetProperty("compact_centre_residue_seam")
            .EnumerateArray().Select(Point).ToArray();
        Check(seam.SequenceEqual(new[] { (179, 148), (195, 148) }), "C08 centre seam changed.");
        Equal(28, routes.GetProperty("C07_exterior_owner_plus_local_bottom_residue").GetArrayLength(), "C07 points");
        Equal(26, routes.GetProperty("C08_body_ranges").GetProperty("main_counterflow_spiral").GetArrayLength(), "C08 main points");
        Equal(26, routes.GetProperty("C09_counterflow_spiral").GetArrayLength(), "C09 points");

        var identity = rootElement.GetProperty("ordered_point_sha256");
        Equal("FCEDA77703B99C57935D9BA0209AB269DDAB4AEA5539374DC589032FFA1E0D8A",
            identity.GetProperty("C08_shelf").GetString(), "C08 shelf digest");
        Equal("F861216E372893B0198A7181EDD6FCEE7CCDB570B7AE5E3E16A9FBD5845FB599",
            identity.GetProperty("C08_main").GetString(), "C08 main digest");
        Equal("BF78E24A10F9785D7656DC05A0F1CC8BC7012F1D55B4170C758C23EC0E2976B1",
            identity.GetProperty("C08_seam").GetString(), "C08 seam digest");

        var metrics = rootElement.GetProperty("physical_body_metrics");
        Near(96.68922372440188, metrics.GetProperty("physical_round100_coverage_percent").GetDouble(), "coverage");
        Near(30.176706724385827, metrics.GetProperty("served_area_m2").GetDouble(), "served area");
        Near(200, metrics.GetProperty("maximum_sample_distance_mm").GetDouble(), "max distance");
        Equal(0, metrics.GetProperty("sample_over_200mm_count").GetInt32(), "samples over 200");
        Equal(0, metrics.GetProperty("R80_body_range_violation_count").GetInt32(), "R80");
        Equal(0, metrics.GetProperty("body_wall_intrusion_count").GetInt32(), "BODY wall intrusions");
        var lengths = metrics.GetProperty("provisional_complete_lengths_mm_using_inherited_concealed_service")
            .EnumerateArray().Select(item => item.GetDouble()).ToArray();
        Check(lengths.Length == 3 && lengths.All(value => value is >= 40_000 and <= 80_000), "D182 lengths changed.");
        Near(1_000, metrics.GetProperty("provisional_complete_length_spread_mm").GetDouble(), "length spread");

        var gates = rootElement.GetProperty("gates");
        Check(gates.GetProperty("owner_morphology_pass").GetBoolean() &&
              gates.GetProperty("body_hard_gates_pass").GetBoolean() &&
              !gates.GetProperty("collector_continuous_route_pass").GetBoolean() &&
              !gates.GetProperty("materialized_transit_between_C08_ranges_pass").GetBoolean() &&
              !gates.GetProperty("complete_route_hard_gates_pass").GetBoolean(),
            "D182 BODY/TRANSIT gate boundary changed.");
        var rejected = rootElement.GetProperty("rejected_connected_weave");
        Equal("ENGINEERING_PASS_COVERAGE_FAIL", rejected.GetProperty("status").GetString(), "rejected weave");
        Check(rejected.GetProperty("physical_round100_coverage_percent").GetDouble() < 96 &&
              rejected.GetProperty("sample_over_200mm_count").GetInt32() == 12,
            "Rejected connected weave was incorrectly promoted.");

        using var manifestDocument = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        foreach (var item in manifestDocument.RootElement.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(), $"D182 manifest mismatch: {path}");
        }
        var package = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_R03_OWNER_BODY_FIXTURE_182.zip");
        using var archive = ZipFile.OpenRead(package);
        Equal(Directory.GetFiles(directory).Length, archive.Entries.Count, "D182 ZIP member count");
    }

    private static (int X, int Y) Point(JsonElement element)
    {
        var values = element.EnumerateArray().Select(item => item.GetInt32()).ToArray();
        return (values[0], values[1]);
    }

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private static void Near(double expected, double actual, string label)
    { if (Math.Abs(expected - actual) > 0.000001) throw new InvalidDataException($"{label}: {actual}"); }
    private static void Equal<T>(T expected, T actual, string label)
    { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new InvalidDataException($"{label}: {actual}"); }
    private static void Check(bool value, string message)
    { if (!value) throw new InvalidDataException(message); }
}
