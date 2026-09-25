using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using HomeAura.NativeEditor;

internal static class TwoFloorArchitectureBaseline180Validation
{
    private const string D178Sha = "424D79B33D7BE8F3B0898410386A70E221F831E9B65734C646008A1FDF09438F";
    private const string D153Sha = "210B36EE163117F6266EBD9234962CCDC1D2035E8ED1A804C35E975C096911DA";
    private const string D180ProjectSha = "C9071982B1A9D96FE77532CEECF7DD22685EE7E05B3A3218AC440D61B776FD4A";
    private const string D180PackageSha = "E9CEBA211838B092C877EB6965D5F1F829E90B68C89756C8B4CC8000BE2D7655";

    public static void Run()
    {
        var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var d178Path = Path.Combine(proposals, "HA_TWO_FLOOR_FLOOR1_BOILER_PAIR_178",
            "HomeAura_Floor1_BoilerPair_D178.homeaura.json");
        var d153Path = Path.Combine(proposals, "HA_TWO_FLOOR_NATIVE_EDITOR_EXACT_HOUSE_153",
            "HomeAura_Attic_ExactHouse_D153.homeaura.json");
        var directory = Path.Combine(proposals, "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180");
        var projectPath = Path.Combine(directory, "HomeAura_TwoFloor_ArchitectureBaseline_D180.homeaura.json");
        var packagePath = Path.Combine(proposals, "packages", "HA_TWO_FLOOR_ARCHITECTURE_BASELINE_180.zip");

        Equal(D178Sha, Sha(d178Path), "D178 source hash");
        Equal(D153Sha, Sha(d153Path), "D153 source hash");
        Equal(D180ProjectSha, Sha(projectPath), "D180 project hash");
        Equal(D180PackageSha, Sha(packagePath), "D180 package hash");

        using var d178Document = JsonDocument.Parse(File.ReadAllText(d178Path));
        using var d153Document = JsonDocument.Parse(File.ReadAllText(d153Path));
        using var d180Document = JsonDocument.Parse(File.ReadAllText(projectPath));
        ValidateAppendOnlyComposition(
            d178Document.RootElement, d153Document.RootElement, d180Document.RootElement);

        var project = HomeAuraProject.FromJson(File.ReadAllText(projectPath));
        Check(project.Levels.Select(item => item.Id).SequenceEqual(["FLOOR_1", "ATTIC"]),
            "D180 level order changed.");
        Check(project.Rooms.Count(item => item.FloorId == "FLOOR_1") == 8 &&
              project.Rooms.Count(item => item.FloorId == "ATTIC") == 8,
            "D180 room count changed.");
        Check(project.Exclusions.Count(item => item.FloorId == "FLOOR_1") == 1 &&
              project.Exclusions.Count(item => item.FloorId == "ATTIC") == 1 &&
              project.Exclusions.Single(item => item.FloorId == "ATTIC").Id == "A-X-STAIR",
            "D180 stair exclusion changed.");

        var k2 = project.Collectors.Single(item => item.Id == "K2");
        Check(k2.FloorId == "FLOOR_1" && k2.ServedFloorId == "ATTIC" &&
              k2.MountingWallId == "FLOOR_1-W025" && k2.RotationDegrees == 180,
            "D180 K2 same-wall inverted placement changed.");
        Check(project.Circuits.All(item => item.CollectorId != "K2"),
            "D180 imported or invented a K2 route.");
        var roomsById = project.Rooms.ToDictionary(item => item.Id);
        Check(project.Circuits.All(item => item.RoomId is null || roomsById[item.RoomId].FloorId == "FLOOR_1"),
            "D180 assigned an inherited circuit to ATTIC.");

        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);
        var attic = diagnostics.CollectorServedFloorDetails.Single(item => item.CollectorId == "K2");
        Check(diagnostics.ServedFloorReferencesPass && attic.ServedFloorExists && attic.RoomCount == 8,
            "D180 did not materialize the verified ATTIC level and rooms.");
        Check(attic.HeatingBodyCount == 0 && attic.LoopCircuitCount == 0 && attic.AxisCircuitCount == 0,
            "D180 incorrectly materialized ATTIC heating geometry.");
        Check(!diagnostics.MaterializedHeatingRoutesPass && !diagnostics.InstallationCompletenessPass,
            "D180 incorrectly became installation-complete.");
        ValidateContract(directory);
        ValidatePackage(directory, packagePath);
    }

    private static void ValidateAppendOnlyComposition(
        JsonElement d178, JsonElement d153, JsonElement d180)
    {
        var appendOnlyProperties = new HashSet<string>(StringComparer.Ordinal)
            { "levels", "rooms", "exclusions" };
        foreach (var property in d178.EnumerateObject())
        {
            Check(d180.TryGetProperty(property.Name, out var current),
                $"D180 lost D178 property {property.Name}.");
            if (appendOnlyProperties.Contains(property.Name)) continue;
            Check(JsonElement.DeepEquals(property.Value, current),
                $"D180 changed preserved D178 property {property.Name}.");
        }
        Check(d180.EnumerateObject().Select(item => item.Name)
                .SequenceEqual(d178.EnumerateObject().Select(item => item.Name)),
            "D180 added an uncontracted top-level project property.");

        var d178Levels = d178.GetProperty("levels").EnumerateArray().ToArray();
        var d153Levels = d153.GetProperty("levels").EnumerateArray().ToArray();
        var d180Levels = d180.GetProperty("levels").EnumerateArray().ToArray();
        Check(d178Levels.Length == 1 && d153Levels.Length == 1 && d180Levels.Length == 2 &&
              JsonElement.DeepEquals(d178Levels[0], d180Levels[0]) &&
              JsonElement.DeepEquals(d153Levels[0], d180Levels[1]),
            "D180 level append changed.");

        ValidateAppendedArray(d178.GetProperty("rooms"), d153.GetProperty("rooms"),
            d180.GetProperty("rooms"), 8, "rooms");
        ValidateAppendedArray(d178.GetProperty("exclusions"), d153.GetProperty("exclusions"),
            d180.GetProperty("exclusions"), 1, "exclusions");
    }

    private static void ValidateAppendedArray(
        JsonElement baseline, JsonElement appended, JsonElement combined, int appendedCount, string label)
    {
        var first = baseline.EnumerateArray().ToArray();
        var second = appended.EnumerateArray().ToArray();
        var result = combined.EnumerateArray().ToArray();
        Check(second.Length == appendedCount && result.Length == first.Length + second.Length,
            $"D180 {label} count changed.");
        for (var index = 0; index < first.Length; index++)
            Check(JsonElement.DeepEquals(first[index], result[index]),
                $"D180 changed preserved {label}[{index}].");
        for (var index = 0; index < second.Length; index++)
            Check(JsonElement.DeepEquals(second[index], result[first.Length + index]),
                $"D180 changed appended {label}[{index}].");
    }

    private static void ValidateContract(string directory)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(directory, "two_floor_architecture_baseline_contract.json")));
        var contract = document.RootElement;
        Check(contract.GetProperty("status").GetString() ==
              "TWO_LEVEL_ARCHITECTURE_BASELINE_ONLY_NOT_INSTALLATION_READY",
            "D180 status changed.");
        var provenance = contract.GetProperty("source_provenance");
        Equal(D178Sha, provenance.GetProperty("official_D178_project").GetProperty("sha256").GetString(),
            "D180 D178 provenance");
        Equal(D153Sha, provenance.GetProperty("D153_attic_project").GetProperty("sha256").GetString(),
            "D180 D153 provenance");

        var architecture = contract.GetProperty("ATTIC_architecture");
        foreach (var field in new[] { "walls", "windows", "door_openings", "slab_holes_and_penetrations" })
            Equal("NOT_MATERIALIZED_UNVERIFIED", architecture.GetProperty(field).GetString(),
                $"D180 {field} boundary");
        Check(architecture.GetProperty("finish_face_room_count").GetInt32() == 8,
            "D180 ATTIC finish-face room count changed.");

        var k2 = contract.GetProperty("K2");
        foreach (var field in new[]
                 { "floor_heating_loops", "floor_service_routes", "interfloor_routes", "collector_connection_tails" })
            Equal("NOT_MATERIALIZED_UNVERIFIED", k2.GetProperty(field).GetString(),
                $"D180 K2 {field} boundary");
        Check(k2.GetProperty("complete_route_count").GetInt32() == 0 &&
              contract.GetProperty("collector_continuous_route_count").GetInt32() == 0 &&
              !contract.GetProperty("sleeves_added").GetBoolean() &&
              !contract.GetProperty("installation_ready").GetBoolean(),
            "D180 completion boundary changed.");
    }

    private static void ValidatePackage(string directory, string packagePath)
    {
        foreach (var name in new[]
                 {
                     "HomeAura_Floor1_D180_Clean.png",
                     "HomeAura_Attic_D180_Architecture_Clean.png",
                     "engineering_diagnostics.json",
                 })
            Check(new FileInfo(Path.Combine(directory, name)) is { Exists: true, Length: > 0 },
                $"D180 file {name} missing.");

        using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(directory, "artifact_manifest.json")));
        var manifestFiles = manifest.RootElement.GetProperty("files").EnumerateArray().ToArray();
        foreach (var item in manifestFiles)
        {
            var path = Path.Combine(directory, item.GetProperty("name").GetString()!);
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == item.GetProperty("sha256").GetString(),
                $"D180 manifest mismatch for {path}.");
        }

        using var archive = ZipFile.OpenRead(packagePath);
        Check(archive.Entries.Count == Directory.GetFiles(directory).Length,
            "D180 ZIP member count changed.");
        foreach (var entry in archive.Entries)
        {
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D180 ZIP byte parity failed for {entry.FullName}.");
        }
    }

    private static string Sha(string path) =>
        Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private static void Equal(string? expected, string? actual, string label)
    {
        if (expected != actual)
            throw new InvalidDataException($"{label}: expected {expected}, got {actual}.");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }
}
