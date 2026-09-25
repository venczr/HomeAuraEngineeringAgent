using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using HomeAura.NativeEditor;

internal static class AtticVerifiedPhysicalInputGate186Validation
{
    private const string ArtifactId = "HA_TWO_FLOOR_ATTIC_VERIFIED_PHYSICAL_INPUT_GATE_186";
    private const string SourceArtifactId = "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185";
    private const string SourceProjectSha = "558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4";
    private const string SourceContractSha = "4C794B3F632C00DF790F743FECBA488DA378C69A5CBED988A34EB3DF4B4CC726";
    private const string SourceDiagnosticsSha = "FBC6BEDDECE6828102D4AAAA951B0FB20CAE7E13AE845391667CCCFC377A43B9";
    private const string SourceManifestSha = "0D4EDA2C54B63D3D7DE69F67D4310CBBEB14C11CA7687814CF7D9EAF6DA57347";
    private const string SourcePackageSha = "A2B1F9D5DE8171B0546D00CBDA29F9902EB47AC276F27616942FACD00E58DB99";
    private const string AcceptedScaffoldPackageSha =
        "B370CB555EEEC2E7041D9C0B4AA5E80D4CD048A67A30023CFCA863CCE5F85ED3";
    private const string PublicationAuditReceiptSha =
        "53D7DE82A5D31DEAB614FFF205C616187831C01530D0DA565C245E9E1A65CBDA";
    private const string OfficialPublicationState = "OFFICIAL_EVIDENCE_ONLY_PHYSICAL_INPUT_GATE_D186";
    private const string StageOverrideEnvironment = "HOMEAURA_D186_OFFICIAL_STAGE";
    private const string ProgramPath = "homeaura-native-editor-tests/Program.cs";
    private const string ValidatorPath =
        "homeaura-native-editor-tests/AtticVerifiedPhysicalInputGate186Validation.cs";
    private const string CurrentProgramSha =
        "0F27CFB69D55E5AAB964FC9572EA5A2C85572CF7461DAA5AE10DEC99EFB2BFCD";
    private const string BlockedReason =
        "BLOCKED_VERIFIED_ATTIC_ARCHITECTURE_AND_INTERFLOOR_OPENING_INPUTS";

    private static readonly IReadOnlyDictionary<string, string> AcceptedSchema11ImplementationHashes =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["homeaura-native-editor/ProjectModel.cs"] =
                "0667BC7D39EBF9CB399CDBFB0114B228BA21D1DB0795F513633B08C38D6FD294",
            ["homeaura-native-editor/CircuitAnalyzer.cs"] =
                "084C3D8CB72D4F4A1150B2C663EA30E6F971320336BDD7E0EE3262CE8EF1908E",
            ["homeaura-native-editor/EditorCanvas.cs"] =
                "DF37729621BFA4406EEC12F751895F10DFE3C15428D5DCC4795331A88E5AE863",
            ["homeaura-native-editor/MainForm.cs"] =
                "C0FF02B661F322F1D2D7D0B7F91EB0C2AD4AEFCB57441BF12DDE4C54044D423A",
            ["homeaura-native-editor/OwnerStyleProposalGenerator.cs"] =
                "A4B863C543FB635163ECB3F678D95D22437EFB5B80B74A092873E5CDD24183D2",
            ["homeaura-native-editor/README.md"] =
                "0BA4C3F4D70FD3215EA269118C3C7726A9D6E608043A66080662DE2ECEBBEA6F",
            ["homeaura-native-editor-tests/PhysicalInputSchemaValidation.cs"] =
                "B32110561728D46F23C167ECA63813050DE88AB0174F06C6AD8C89EDA247BF0C",
            ["homeaura-native-editor-tests/PhysicalInputRendererValidation.cs"] =
                "FD8FEA3D28D325ACA4205AAC0798DC02EEC568A0C244F06C9AEEA871375889B7",
            ["homeaura-native-editor-tests/Program.cs"] =
                "6EE05E55746AA2F4031D111BAF94D25C1271AB262C327D264F78EC398DE867A0",
        };

    private static readonly IReadOnlyDictionary<string, string> CurrentSchema11ImplementationHashes =
        BuildCurrentImplementationHashes();

    private static readonly IReadOnlyDictionary<string, string> AcceptedScaffoldPayloadHashes =
        new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["README.md"] = "29EFC168207F52E97E25F78514D8AB6F083A7E65149468918B6734DB48C5D27E",
            ["artifact_manifest.json"] = "32DA87F5ABBB0C905E5564830985A0CD09532B303BA0F60D0625B19AFF8AF019",
            ["attic_as_built_input_template.json"] =
                "493EC1560FC4CE77F305571911666E1C462778CCB4CF8B3AAC89483A569F7CBF",
            ["attic_verified_physical_input_gate.json"] =
                "19631431A7A53830F52B40ABF7CD535114B1BE7381B1305FBFF2BC0556B38313",
            ["status.json"] = "5BE1CC30095087EEA16B11870BE11040730A5ED8F242A3223A00EB35E6051F69",
        };

    private static readonly string[] ExpectedReasonCodes =
    [
        "UNSCOPED_ARCHITECTURE_OBJECTS",
        "VERIFIED_FLOOR_ARCHITECTURE_INCOMPLETE",
        "VERIFIED_INTERFLOOR_OPENING_INPUT_INCOMPLETE",
        "STRUCTURAL_DISPOSITION_INCOMPLETE",
        "MATERIALIZED_ROUTE_OPENING_BINDING_NOT_MODELED",
    ];

    public static void Run()
    {
        var root = FindRoot();
        var proposals = Path.Combine(root, "homeaura-native-editor", "examples", "proposals");
        var official = Path.Combine(proposals, ArtifactId);
        var scaffold = Path.Combine(root, "tmp", "D186_scaffold");
        var scaffoldPackage = Path.Combine(root, "tmp", $"{ArtifactId}_SCAFFOLD.zip");
        ValidateAcceptedScaffold(scaffold, scaffoldPackage);

        var stageOverride = Environment.GetEnvironmentVariable(StageOverrideEnvironment);
        var isStagedOfficial = !string.IsNullOrWhiteSpace(stageOverride);
        var expectedStage = Path.GetFullPath(Path.Combine(root, "tmp", "D186_official_stage"));
        var directory = isStagedOfficial ? Path.GetFullPath(stageOverride!) :
            Directory.Exists(official) ? official : scaffold;
        if (isStagedOfficial)
            Check(string.Equals(directory, expectedStage, StringComparison.OrdinalIgnoreCase),
                "D186 official stage override escaped the fixed tmp/D186_official_stage boundary.");
        var isOfficial = isStagedOfficial || string.Equals(directory, official, StringComparison.OrdinalIgnoreCase);
        var package = isStagedOfficial
            ? Path.Combine(root, "tmp", $"{ArtifactId}_OFFICIAL_STAGE.zip")
            : isOfficial
                ? Path.Combine(proposals, "packages", $"{ArtifactId}.zip")
                : scaffoldPackage;
        var sourceDirectory = Path.Combine(proposals, SourceArtifactId);
        var sourceProject = Path.Combine(sourceDirectory,
            "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json");
        var sourceContract = Path.Combine(sourceDirectory, "floor1_c12_bounded_terminal_contract.json");
        var sourceDiagnostics = Path.Combine(sourceDirectory, "engineering_diagnostics.json");
        var sourceManifest = Path.Combine(sourceDirectory, "artifact_manifest.json");
        var sourcePackage = Path.Combine(proposals, "packages", $"{SourceArtifactId}.zip");
        var gatePath = Path.Combine(directory, "attic_verified_physical_input_gate.json");
        var templatePath = Path.Combine(directory, "attic_as_built_input_template.json");
        var statusPath = Path.Combine(directory, "status.json");
        var manifestPath = Path.Combine(directory, "artifact_manifest.json");

        Check(Directory.Exists(directory), "D186 payload directory is absent.");
        Check(File.Exists(package), "D186 deterministic ZIP is absent.");
        foreach (var path in new[] { gatePath, templatePath, statusPath, manifestPath,
                     Path.Combine(directory, "README.md") })
            Check(File.Exists(path), $"D186 payload member is absent: {path}");
        if (isOfficial)
            Check(File.Exists(Path.Combine(directory, "publication_audit_receipt.json")),
                "Official D186 publication audit receipt is absent.");

        Equal(SourceProjectSha, Sha(sourceProject), "official D185 project");
        Equal(SourceContractSha, Sha(sourceContract), "official D185 contract");
        Equal(SourceDiagnosticsSha, Sha(sourceDiagnostics), "official D185 diagnostics");
        Equal(SourceManifestSha, Sha(sourceManifest), "official D185 manifest");
        Equal(SourcePackageSha, Sha(sourcePackage), "official D185 package");
        ValidateOfficialD185(sourceContract);
        var readiness = ValidateSourceNativeTruth(sourceProject);
        ValidateImplementationBinding(root);
        ValidateGate(root, directory, gatePath, sourceProject, sourceContract, readiness, isOfficial);
        ValidateTemplate(templatePath);
        ValidateReadme(Path.Combine(directory, "README.md"), isOfficial);
        ValidateStatus(root, directory, statusPath, sourceProject, sourceContract, isOfficial);
        if (isOfficial)
            ValidatePublicationAuditReceipt(Path.Combine(directory, "publication_audit_receipt.json"));
        ValidateManifestAndPackage(root, directory, package, manifestPath, sourceProject, sourceContract,
            isOfficial);
        ValidateNoGeometryOrRender(directory, package);
        ValidateProgramRegistrationBoundary(root, isOfficial);
    }

    private static IReadOnlyDictionary<string, string> BuildCurrentImplementationHashes()
    {
        var current = new Dictionary<string, string>(AcceptedSchema11ImplementationHashes,
            StringComparer.Ordinal)
        {
            [ProgramPath] = CurrentProgramSha,
        };
        return current;
    }

    private static void ValidateAcceptedScaffold(string directory, string package)
    {
        Check(Directory.Exists(directory), "Accepted D186 scaffold directory is absent.");
        Equal(AcceptedScaffoldPackageSha, Sha(package), "accepted D186 scaffold package");
        var names = Directory.GetFiles(directory).Select(Path.GetFileName).Order().ToArray();
        Check(names.SequenceEqual(AcceptedScaffoldPayloadHashes.Keys.Order()),
            "Accepted D186 scaffold payload set changed.");
        foreach (var (name, expected) in AcceptedScaffoldPayloadHashes)
            Equal(expected, Sha(Path.Combine(directory, name)), $"accepted D186 scaffold payload {name}");
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.Select(item => item.FullName)
                  .SequenceEqual(AcceptedScaffoldPayloadHashes.Keys.Order()),
            "Accepted D186 scaffold ZIP order/member set changed.");
        foreach (var entry in archive.Entries)
        {
            Check(entry.LastWriteTime.Year == 1980 && entry.LastWriteTime.Month == 1 &&
                  entry.LastWriteTime.Day == 1 && entry.LastWriteTime.Hour == 0 &&
                  entry.LastWriteTime.Minute == 0 && entry.LastWriteTime.Second == 0,
                $"Accepted D186 scaffold ZIP timestamp changed: {entry.FullName}");
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"Accepted D186 scaffold ZIP parity changed: {entry.FullName}");
        }
    }

    private static void ValidateOfficialD185(string contractPath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(contractPath));
        var root = document.RootElement;
        Equal(SourceArtifactId, Text(root, "artifact_id"), "D185 artifact id");
        Equal("OFFICIAL_BOUNDED_TERMINAL_D185", Text(root, "publication_state"), "D185 publication state");
        Equal("OFFICIAL_BOUNDED_TERMINAL_D185", Text(root, "status"), "D185 status");
        Check(!root.GetProperty("publishable_as_installation_project").GetBoolean() &&
              !root.GetProperty("installation_truth").GetProperty("installation_ready").GetBoolean() &&
              root.GetProperty("installation_truth").GetProperty("structured_sleeve_geometry_count").GetInt32() == 0,
            "D185 official installation/sleeve boundary changed.");
    }

    private static PhysicalInputReadinessDetail ValidateSourceNativeTruth(string projectPath)
    {
        var raw = File.ReadAllText(projectPath);
        using var document = JsonDocument.Parse(raw);
        var root = document.RootElement;
        var project = HomeAuraProject.FromJson(raw);
        Equal("1.0", project.SchemaVersion, "D185 schema version");

        foreach (var absent in new[]
        {
            "shared_spatial_datum", "door_openings", "interfloor_openings",
            "floor_architecture_registry_verifications", "interfloor_opening_registry_verifications",
        })
            Check(!root.TryGetProperty(absent, out _), $"D185 unexpectedly has schema 1.1 member {absent}.");
        AssertNoNestedMembers(root, "levels",
            "shared_datum_id", "finished_floor_elevation_mm_shared_datum");
        AssertNoNestedMembers(root, "walls",
            "floor_id", "verified_finish_face_a_outline_mm", "verified_finish_face_b_outline_mm",
            "base_elevation_mm_shared_datum", "top_elevation_mm_shared_datum", "physical_verification");
        AssertNoNestedMembers(root, "windows",
            "floor_id", "verified_plan_outline_mm", "clear_width_mm",
            "sill_elevation_mm_shared_datum", "physical_verification");
        AssertNoNestedMembers(root, "floor_build_ups",
            "build_up_id", "layer_registry", "total_build_up_thickness_mm",
            "allowed_pipe_axis_elevation_mm_shared_datum", "allowed_pipe_axis_tolerance_mm",
            "physical_verification");

        Check(project.SharedSpatialDatum is null && project.DoorOpenings is null &&
              project.InterfloorOpenings is null && project.FloorArchitectureRegistryVerifications is null &&
              project.InterfloorOpeningRegistryVerifications is null,
            "D185 deserialization materialized absent schema 1.1 values.");
        Check(project.Levels.All(item => item.SharedDatumId is null &&
                                       item.FinishedFloorElevationMmSharedDatum is null),
            "D185 levels acquired physical datum values.");
        Equal(33, project.Walls.Count, "D185 legacy wall count");
        Equal(8, project.Windows.Count, "D185 legacy window count");
        Check(project.Walls.All(item => item.FloorId is null && item.VerifiedFinishFaceAOutlineMm is null &&
                                      item.VerifiedFinishFaceBOutlineMm is null && item.PhysicalVerification is null) &&
              project.Windows.All(item => item.FloorId is null && item.VerifiedPlanOutlineMm is null &&
                                        item.PhysicalVerification is null),
            "D185 legacy walls/windows acquired typed physical values.");
        Check(project.FloorBuildUps.All(item => item.BuildUpId is null && item.LayerRegistry is null &&
                                              item.TotalBuildUpThicknessMm is null &&
                                              item.AllowedPipeAxisElevationMmSharedDatum is null &&
                                              item.PhysicalVerification is null),
            "D185 legacy floor build-up acquired typed physical values.");

        var atticRoomIds = project.Rooms.Where(item => item.FloorId == "ATTIC")
            .Select(item => item.Id).Order().ToArray();
        Check(atticRoomIds.SequenceEqual(new[]
            { "A-R09", "A-R10", "A-R11", "A-R12", "A-R13", "A-R14", "A-R15", "A-R16" }),
            "D185 no longer has exactly eight frozen ATTIC finish-face rooms.");
        Check(project.Exclusions.Where(item => item.FloorId == "ATTIC").Select(item => item.Id)
                  .SequenceEqual(new[] { "A-X-STAIR" }),
            "D185 no longer has exactly one A-X-STAIR exclusion.");
        var k2 = project.Collectors.Single(item => item.Id == "K2");
        Check(k2.FloorId == "FLOOR_1" && k2.ServedFloorId == "ATTIC",
            "D185 K2 cross-floor applicability changed.");
        Equal(0, project.ServiceZones.Count(item => item.FloorId == "ATTIC"), "ATTIC service zones");
        Equal(0, project.FloorBuildUps.Count(item => item.FloorId == "ATTIC"), "ATTIC floor build-ups");
        Equal(0, project.Circuits.Count(item => item.CollectorId == "K2"), "K2 routes");

        var readiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(project);
        Check(readiness.Applicable && !readiness.ArchitectureFloorScopePass,
            "D185 direct physical input applicability/scope changed.");
        Equal(33, readiness.UnscopedWallIds.Count, "D185 unscoped walls");
        Equal(8, readiness.UnscopedWindowIds.Count, "D185 unscoped windows");
        Check(readiness.FloorDetails.Count == 2 &&
              readiness.FloorDetails.All(item => item.RequiredByCrossFloorSystem && !item.Pass),
            "D185 required physical floor details changed.");
        Check(readiness.InterfloorOpeningDetails is
              [{ FromFloorId: "FLOOR_1", ToFloorId: "ATTIC", OpeningCount: 0,
                  RegistryDeclarationPass: false, PairedFaceGeometryPass: false,
                  StructuralDispositionPass: false, RoutingInputPass: false }],
            "D185 opening-pair readiness changed.");
        Check(readiness.CrossFloorCollectorDetails is
              [{ CollectorId: "K2", FloorReferencesPass: true, VerifiedOpeningInputPass: false,
                  MaterializedRouteOpeningBindingPass: false }],
            "D185 K2 physical readiness detail changed.");
        Check(!readiness.VerifiedArchitectureInputPass && !readiness.VerifiedInterfloorOpeningInputPass &&
              !readiness.RoutingInputReadinessPass && !readiness.StructuralDispositionPass &&
              !readiness.RouteOpeningBindingPass && !readiness.InstallationInputReadinessPass,
            "D185 direct physical readiness was incorrectly released.");
        Check(readiness.ReasonCodes.SequenceEqual(ExpectedReasonCodes),
            $"D185 physical reason codes changed: {string.Join(',', readiness.ReasonCodes)}");

        var diagnostics = CircuitAnalyzer.AnalyzeProject(project);
        Check(diagnostics.PhysicalInputReadiness is null &&
              diagnostics.PhysicalInstallationCompletenessPass is null,
            "Schema 1.0 D185 exposed schema 1.1 diagnostics fields.");
        return readiness;
    }

    private static void ValidateImplementationBinding(string root)
    {
        foreach (var (relative, expected) in CurrentSchema11ImplementationHashes)
            Equal(expected, Sha(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar))),
                $"schema 1.1 implementation hash {relative}");
    }

    private static void ValidateGate(string repositoryRoot, string directory, string path,
        string sourceProject, string sourceContract,
        PhysicalInputReadinessDetail readiness, bool isOfficial)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        Equal(ArtifactId, Text(root, "artifact_id"), "D186 artifact id");
        Equal(BlockedReason, Text(root, "status"), "D186 gate status");
        Equal(BlockedReason, Text(root, "blocked_reason"), "D186 blocked reason");
        Equal(BlockedReason, Text(root, "result"), "D186 result");
        Equal("EVIDENCE_ONLY_NO_HOMEAURA_GEOMETRY", Text(root, "scope"), "D186 scope");
        Equal(isOfficial ? OfficialPublicationState : "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL",
            Text(root, "publication_state"), "D186 publication state");
        Equal(CanonicalDigest(root, "gate_digest"), Text(root, "gate_digest"), "D186 gate digest");
        Check(!root.TryGetProperty("native_schema_gap_report", out _),
            "D186 retained the obsolete native-schema-missing report.");

        var sources = root.GetProperty("source_records").EnumerateArray()
            .ToDictionary(item => Text(item, "source_key"), item => item.Clone());
        Equal(SourceProjectSha, Text(sources["D185_PROJECT"], "sha256"), "D186 D185 project source");
        Equal(SourceContractSha, Text(sources["D185_CONTRACT"], "sha256"), "D186 D185 contract source");
        Equal(SourceDiagnosticsSha, Text(sources["D185_DIAGNOSTICS"], "sha256"),
            "D186 D185 exact diagnostics source");
        Equal(SourceManifestSha, Text(sources["D185_MANIFEST"], "sha256"),
            "D186 D185 manifest source");
        Equal(SourcePackageSha, Text(sources["D185_PACKAGE"], "sha256"),
            "D186 D185 package source");
        Check(Text(sources["D185_PROJECT"], "classification").EndsWith("SCHEMA_1_0", StringComparison.Ordinal),
            "D186 source schema classification changed.");
        Equal("NON_AUTHORITATIVE_WALL_DOMAIN_CANDIDATES", Text(sources["D181"], "classification"),
            "D181 evidence class");
        Equal("NON_AUTHORITATIVE_EVIDENCE", Text(sources["D137"], "classification"), "D137 evidence class");
        Equal("NON_AUTHORITATIVE_EVIDENCE", Text(sources["D166"], "classification"), "D166 evidence class");

        var capability = root.GetProperty("native_schema_11_capability_binding");
        Check(capability.GetProperty("implemented").GetBoolean() &&
              capability.GetProperty("typed_shared_datum_architecture_opening_build_up_and_registry_input").GetBoolean() &&
              capability.GetProperty("physical_input_readiness_analyzer").GetBoolean() &&
              capability.GetProperty("active_floor_physical_renderer").GetBoolean() &&
              capability.GetProperty("owner_style_transform_rejects_schema_11").GetBoolean() &&
              !capability.GetProperty("segment_to_opening_route_binding_modeled").GetBoolean(),
            "D186 schema 1.1 capability boundary changed.");
        Equal(9, capability.GetProperty("runtime_test_doc_surface_file_count").GetInt32(),
            "D186 runtime/test/doc surface file count");
        var implementationArray = capability.GetProperty("implementation_files");
        var boundFiles = implementationArray.EnumerateArray()
            .ToDictionary(item => Text(item, "path"), item => Text(item, "sha256"), StringComparer.Ordinal);
        Check(boundFiles.Count == AcceptedSchema11ImplementationHashes.Count &&
              AcceptedSchema11ImplementationHashes.All(item =>
                  boundFiles.GetValueOrDefault(item.Key) == item.Value),
            "D186 accepted-scaffold schema 1.1 implementation binding changed.");
        var acceptance = capability.GetProperty("acceptance_evidence_binding");
        Equal(CanonicalDigest(implementationArray, "__none__"), Text(acceptance, "surface_binding_digest"),
            "D186 surface binding digest");
        Equal("PASS_0_WARNINGS_0_ERRORS", Text(acceptance, "release_build_result"),
            "D186 Release build claim");
        Equal("RESULT_56_OF_56_PASSED", Text(acceptance, "registered_suite_result"),
            "D186 registered suite claim");
        Equal("homeaura-native-editor-tests/Program.cs", Text(acceptance, "registered_suite_program_path"),
            "D186 registered suite program path");
        Equal(AcceptedSchema11ImplementationHashes[ProgramPath],
            Text(acceptance, "registered_suite_program_sha256"), "D186 registered suite program hash");
        Equal(SourceDiagnosticsSha, Text(acceptance, "D185_diagnostics_exact_sha256"),
            "D186 exact diagnostics acceptance hash");
        Equal(SourceManifestSha, Text(acceptance, "D185_manifest_sha256"),
            "D186 acceptance manifest hash");
        Equal(SourcePackageSha, Text(acceptance, "D185_package_sha256"),
            "D186 acceptance package hash");
        Check(capability.GetProperty("schema11_final_GO_received").GetBoolean() &&
              capability.GetProperty("independent_D186_package_reviewer_GO_required_before_official_freeze").GetBoolean(),
            "D186 final schema/package review boundary changed.");

        var state = root.GetProperty("verified_current_native_state");
        Equal("1.0", Text(state, "source_project_schema_version"), "D186 source project schema");
        Equal(33, state.GetProperty("source_project_legacy_wall_count").GetInt32(), "legacy walls");
        Equal(8, state.GetProperty("source_project_legacy_window_count").GetInt32(), "legacy windows");
        Equal(33, state.GetProperty("unscoped_wall_count").GetInt32(), "unscoped walls");
        Equal(8, state.GetProperty("unscoped_window_count").GetInt32(), "unscoped windows");
        Check(!state.GetProperty("schema_11_typed_values_present").GetBoolean() &&
              state.GetProperty("shared_spatial_datum").ValueKind == JsonValueKind.Null &&
              state.GetProperty("door_openings").GetArrayLength() == 0 &&
              state.GetProperty("interfloor_openings").GetArrayLength() == 0,
            "D186 invented schema 1.1 values in D185.");

        var expected = root.GetProperty("direct_physical_input_readiness_expected_from_D185");
        Check(expected.GetProperty("applicable").GetBoolean() == readiness.Applicable &&
              expected.GetProperty("architecture_floor_scope_pass").GetBoolean() == readiness.ArchitectureFloorScopePass &&
              expected.GetProperty("unscoped_wall_count").GetInt32() == readiness.UnscopedWallIds.Count &&
              expected.GetProperty("unscoped_window_count").GetInt32() == readiness.UnscopedWindowIds.Count &&
              expected.GetProperty("verified_architecture_input_pass").GetBoolean() == readiness.VerifiedArchitectureInputPass &&
              expected.GetProperty("verified_interfloor_opening_input_pass").GetBoolean() == readiness.VerifiedInterfloorOpeningInputPass &&
              expected.GetProperty("routing_input_readiness_pass").GetBoolean() == readiness.RoutingInputReadinessPass &&
              expected.GetProperty("structural_disposition_pass").GetBoolean() == readiness.StructuralDispositionPass &&
              expected.GetProperty("route_opening_binding_pass").GetBoolean() == readiness.RouteOpeningBindingPass &&
              expected.GetProperty("installation_input_readiness_pass").GetBoolean() == readiness.InstallationInputReadinessPass,
            "D186 gate does not match the live physical analyzer.");
        Check(expected.GetProperty("reason_codes").EnumerateArray().Select(item => item.GetString())
                  .SequenceEqual(readiness.ReasonCodes),
            "D186 gate reason codes do not match the live physical analyzer.");

        var required = root.GetProperty("required_verified_input");
        Check(Text(required, "truthful_floor_scope_for_all_33_walls_and_8_windows") == "REQUIRED" &&
              Text(required, "segment_to_opening_binding") == "NOT_MODELED_IN_SCHEMA_1_1",
            "D186 omitted a required input or the native route-binding limit.");
        var release = root.GetProperty("release_boundary");
        foreach (var property in new[]
        {
            "verified_architecture_input_pass", "verified_interfloor_opening_input_pass",
            "routing_input_readiness_pass", "structural_disposition_pass", "route_opening_binding_pass",
            "installation_input_readiness_pass", "physical_installation_completeness_pass",
            "owner_style_route_release", "K2_route_release", "installation_ready", "install",
        })
            Check(!release.GetProperty(property).GetBoolean(), $"D186 incorrectly released {property}.");
        if (isOfficial)
        {
            Check(release.GetProperty("official_D186_freeze_allowed").GetBoolean() &&
                  release.GetProperty("independent_D186_package_reviewer_GO_received").GetBoolean() &&
                  !release.GetProperty("root_review_required").GetBoolean(),
                "Official D186 reviewer/root/freeze publication state changed.");
            ValidateOfficialPublicationBindings(repositoryRoot, directory, root);
        }
        else
            Check(!release.GetProperty("official_D186_freeze_allowed").GetBoolean() &&
                  !release.GetProperty("independent_D186_package_reviewer_GO_received").GetBoolean() &&
                  release.GetProperty("root_review_required").GetBoolean() &&
                  !root.TryGetProperty("official_publication", out _) &&
                  !root.TryGetProperty("current_official_validation_binding", out _),
                "D186 scaffold lost its prepublication guard.");

        var materialization = root.GetProperty("materialization_boundary");
        foreach (var count in new[]
        {
            "added_geometry_count", "homeaura_file_count_in_D186", "render_file_count_in_D186",
            "walls_added", "windows_added", "doors_added", "holes_or_penetrations_added",
            "service_zones_added", "floor_build_ups_added", "K2_routes_added",
        })
            Equal(0, materialization.GetProperty(count).GetInt32(), count);
        Check(!materialization.GetProperty("homeaura_geometry_created_or_changed").GetBoolean() &&
              !materialization.GetProperty("sleeves_added").GetBoolean(),
            "D186 invented geometry or sleeves.");
        Equal(Sha(sourceProject), SourceProjectSha, "D186 immutable source project");
    }

    private static void ValidateOfficialPublicationBindings(string repositoryRoot, string directory,
        JsonElement root)
    {
        ValidateAcceptedScaffoldBinding(root.GetProperty("accepted_scaffold_validation_binding"),
            root.GetProperty("native_schema_11_capability_binding"));
        ValidateOfficialPublicationSummary(root.GetProperty("official_publication"));
        ValidateCurrentOfficialBinding(repositoryRoot,
            root.GetProperty("current_official_validation_binding"));
        Equal(PublicationAuditReceiptSha,
            Sha(Path.Combine(directory, "publication_audit_receipt.json")),
            "official D186 copied audit receipt");
    }

    private static void ValidateAcceptedScaffoldBinding(JsonElement binding, JsonElement historicalCapability)
    {
        Equal(AcceptedScaffoldPackageSha, Text(binding, "accepted_scaffold_package_sha256"),
            "accepted scaffold binding package");
        var payloads = binding.GetProperty("accepted_scaffold_payload_sha256").EnumerateObject()
            .ToDictionary(item => item.Name, item => item.Value.GetString() ?? "", StringComparer.Ordinal);
        Check(payloads.Count == AcceptedScaffoldPayloadHashes.Count &&
              AcceptedScaffoldPayloadHashes.All(item => payloads.GetValueOrDefault(item.Key) == item.Value),
            "Accepted scaffold payload binding changed.");
        Equal(CanonicalDigest(historicalCapability, "__none__"),
            Text(binding, "historical_native_schema_11_capability_binding_digest"),
            "historical accepted capability digest");
        Equal("RESULT_56_OF_56_PASSED", Text(binding, "historical_registered_suite_result"),
            "historical accepted suite result");
        Equal(AcceptedSchema11ImplementationHashes[ProgramPath],
            Text(binding, "historical_registered_suite_program_sha256"),
            "historical accepted Program hash");
    }

    private static void ValidateOfficialPublicationSummary(JsonElement publication)
    {
        Equal(OfficialPublicationState, Text(publication, "publication_state"),
            "official D186 publication summary state");
        Equal(AcceptedScaffoldPackageSha, Text(publication, "accepted_scaffold_package_sha256"),
            "official D186 accepted scaffold package");
        Equal("publication_audit_receipt.json", Text(publication, "audit_receipt_path"),
            "official D186 audit receipt path");
        Equal(PublicationAuditReceiptSha, Text(publication, "audit_receipt_sha256"),
            "official D186 audit receipt hash");
        Equal(2, publication.GetProperty("required_formal_GO_count").GetInt32(),
            "official D186 required GO count");
        Equal(2, publication.GetProperty("received_formal_GO_count").GetInt32(),
            "official D186 received GO count");
        Check(publication.GetProperty("explicit_root_GO").GetBoolean() &&
              publication.GetProperty("independent_reviewer_GO_received").GetBoolean() &&
              publication.GetProperty("official_freeze_allowed").GetBoolean() &&
              !publication.GetProperty("root_review_required").GetBoolean() &&
              !publication.GetProperty("physical_release_allowed").GetBoolean() &&
              !publication.GetProperty("installation_allowed").GetBoolean(),
            "Official D186 audit/root/publication boundary changed.");
        ValidateFormalGoRecords(publication.GetProperty("formal_GO_records"));
    }

    private static void ValidateFormalGoRecords(JsonElement recordsElement)
    {
        var records = recordsElement.EnumerateArray().ToArray();
        Equal(2, records.Length, "D186 formal GO record count");
        var expected = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["d186_semantic_audit"] = "/root/d186_semantic_audit",
            ["d186_package_audit"] = "/root/d186_package_audit",
        };
        var actualIds = records.Select(item => Text(item, "auditor_id")).ToArray();
        Check(actualIds.Distinct(StringComparer.Ordinal).Count() == 2 &&
              actualIds.Order().SequenceEqual(expected.Keys.Order()),
            "D186 formal GO auditor identities are not exact and unique.");
        foreach (var record in records)
        {
            var auditor = Text(record, "auditor_id");
            Equal(expected[auditor], Text(record, "canonical_agent_path"), $"{auditor} canonical path");
            Equal("FORMAL GO", Text(record, "verdict"), $"{auditor} verdict");
            Equal(AcceptedScaffoldPackageSha,
                Text(record, "accepted_scaffold_package_sha256"), $"{auditor} package binding");
            Check(Text(record, "go_record_id").StartsWith($"{auditor}_FORMAL_GO_", StringComparison.Ordinal),
                $"{auditor} unique GO record id changed.");
        }
    }

    private static void ValidateCurrentOfficialBinding(string repositoryRoot, JsonElement binding)
    {
        Equal(9, binding.GetProperty("runtime_test_doc_surface_file_count").GetInt32(),
            "current official surface file count");
        var implementationArray = binding.GetProperty("implementation_files");
        var files = implementationArray.EnumerateArray()
            .ToDictionary(item => Text(item, "path"), item => Text(item, "sha256"), StringComparer.Ordinal);
        Check(files.Count == CurrentSchema11ImplementationHashes.Count &&
              CurrentSchema11ImplementationHashes.All(item => files.GetValueOrDefault(item.Key) == item.Value),
            "Current official runtime/test/doc binding changed.");
        Equal(CanonicalDigest(implementationArray, "__none__"), Text(binding, "surface_binding_digest"),
            "current official surface digest");
        Equal(Schema11SurfaceDigest(CurrentSchema11ImplementationHashes),
            Text(binding, "surface_binding_digest"), "exact current official surface digest");
        Equal("PASS_0_WARNINGS_0_ERRORS", Text(binding, "release_build_result"),
            "current official Release result");
        Equal("RESULT_57_OF_57_PASSED", Text(binding, "registered_suite_result"),
            "current official registered suite result");
        Equal(ProgramPath, Text(binding, "registered_suite_program_path"),
            "current official Program path");
        Equal(CurrentProgramSha, Text(binding, "registered_suite_program_sha256"),
            "current official Program hash");
        Equal(ValidatorPath, Text(binding, "direct_validator_path"), "current official validator path");
        Equal(Sha(Path.Combine(repositoryRoot, ValidatorPath.Replace('/', Path.DirectorySeparatorChar))),
            Text(binding, "direct_validator_sha256"), "current official validator hash");
        Equal("PASS", Text(binding, "direct_D186_validator_result"),
            "current official direct validator result");
        Equal(AcceptedScaffoldPackageSha, Text(binding, "accepted_scaffold_package_sha256"),
            "current official accepted scaffold hash");
        Equal(PublicationAuditReceiptSha, Text(binding, "publication_audit_receipt_sha256"),
            "current official audit receipt hash");
        foreach (var forbidden in new[]
        {
            "official_manifest_sha256", "official_package_sha256", "official_publisher_expected_sha256",
        })
            Check(!binding.TryGetProperty(forbidden, out _),
                $"Current official binding introduced a reverse/future hash: {forbidden}.");
    }

    private static void ValidatePublicationAuditReceipt(string path)
    {
        Equal(PublicationAuditReceiptSha, Sha(path), "D186 publication audit receipt");
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var receipt = document.RootElement;
        Equal(ArtifactId, Text(receipt, "artifact_id"), "D186 receipt artifact id");
        Equal(AcceptedScaffoldPackageSha, Text(receipt, "accepted_scaffold_package_sha256"),
            "D186 receipt accepted scaffold package");
        Equal(2, receipt.GetProperty("required_formal_GO_count").GetInt32(),
            "D186 receipt required GO count");
        Equal(2, receipt.GetProperty("received_formal_GO_count").GetInt32(),
            "D186 receipt received GO count");
        Check(receipt.GetProperty("unique_auditor_ids").GetBoolean() &&
              receipt.GetProperty("all_GO_records_bind_same_accepted_scaffold_sha256").GetBoolean() &&
              receipt.GetProperty("explicit_root_GO").GetBoolean(),
            "D186 receipt lacks exact independent/root GO proof.");
        Equal(OfficialPublicationState, Text(receipt, "publication_state_authorized"),
            "D186 receipt authorized publication state");
        Equal(BlockedReason, Text(receipt, "result_remains"), "D186 receipt blocked result");
        var payloads = receipt.GetProperty("accepted_scaffold_payload_sha256").EnumerateObject()
            .ToDictionary(item => item.Name, item => item.Value.GetString() ?? "", StringComparer.Ordinal);
        Check(payloads.Count == AcceptedScaffoldPayloadHashes.Count &&
              AcceptedScaffoldPayloadHashes.All(item => payloads.GetValueOrDefault(item.Key) == item.Value),
            "D186 receipt accepted payload binding changed.");
        ValidateFormalGoRecords(receipt.GetProperty("formal_GO_records"));
        AssertStrings(receipt, "excluded_claims", "HOMEAURA_GEOMETRY", "K2_OR_OWNER_STYLE_ROUTES",
            "SLEEVES", "PNG_OR_PDF_RENDERS", "INSTALL", "INSTALLATION_READY",
            "PHYSICAL_RELEASE_PASS");
    }

    private static void ValidateTemplate(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        Equal(ArtifactId, Text(root, "artifact_id"), "D186 template artifact id");
        Equal("homeaura.attic.as_built_schema11_input_template.v3", Text(root, "schema"),
            "D186 template schema");
        Equal("1.1", Text(root, "target_native_schema_version"), "D186 template target schema");
        Equal("EMPTY_UNVERIFIED_OWNER_SITE_INPUT_TEMPLATE", Text(root, "template_status"),
            "D186 template status");
        Check(!root.GetProperty("template_is_directly_loadable_homeaura_project").GetBoolean(),
            "D186 evidence template claims to be a project.");
        Equal(CanonicalDigest(root, "template_digest"), Text(root, "template_digest"), "D186 template digest");
        Check(!ContainsNumber(root), "D186 empty input template contains a numeric placeholder.");
        Check(!ContainsPartiallyPopulatedPoint(root),
            "D186 template contains a PointMm/Point3Mm with missing, null, or nonnumeric components.");

        foreach (var stale in new[]
        {
            "verified_plan_bbox_mm", "face_id", "verified_center_point_3d_shared_datum_mm",
            "verified_plan_center_point_mm", "verified_center_elevation_mm_shared_datum",
            "nonrect_clear_outline_mm", "measurement_evidence",
            "verified_clear_centerline_between_faces_3d_shared_datum_mm",
            "verified_clear_axis_vector_shared_datum", "verified_clear_axis_orientation", "thresholds",
        })
            Check(!ContainsProperty(root, stale), $"D186 template retained stale non-native field {stale}.");

        var enums = root.GetProperty("native_enum_contract");
        AssertStrings(enums, "clear_axis_definition_method",
            "FACE_CENTERS", "CENTERLINE_POLYLINE", "VECTOR_AND_ORIENTATION");
        AssertStrings(enums, "clear_axis_direction", "FROM_TO", "TO_FROM");
        AssertStrings(enums, "shape_type", "CIRCULAR", "RECTANGULAR", "NONRECTANGULAR");
        AssertStrings(enums, "threshold_disposition", "NONE", "FLUSH", "RAISED");
        Check(!File.ReadAllText(path).Contains("CENTERLINE_BETWEEN_FACE_CENTERS", StringComparison.Ordinal) &&
              !File.ReadAllText(path).Contains("AXIS_VECTOR_AND_ORIENTATION", StringComparison.Ordinal),
            "D186 template retained obsolete axis enum names.");

        Check(!root.TryGetProperty("native_record_shapes", out _),
            "D186 template retained ambiguous partially populated DTO shapes.");
        var encoding = root.GetProperty("encoding_contract");
        Check(!ContainsProperty(root, "unknown_collection") &&
              Text(encoding, "unknown_nullable_scalar_or_object") == "null_or_omitted" &&
              Text(encoding, "unknown_optional_outline") ==
              "null_or_omitted_except_StructuralDisposition.approved_clear_outline_mm_on_existing_UNREVIEWED_record" &&
              Text(encoding, "unknown_layer_registry") == "null_or_omitted" &&
              Text(encoding, "present_empty_submission_registry_or_declaration") == "empty_array" &&
              Text(encoding, "StructuralDisposition_unknown_whole_record") == "null_or_omitted" &&
              Text(encoding, "StructuralDisposition_UNREVIEWED_approved_clear_outline_mm") ==
              "omitted_or_empty_array_never_explicit_null" &&
              Text(encoding, "StructuralDisposition_approved_status_approved_clear_outline_mm") ==
              "nonempty_simple_polygon" &&
              Text(encoding, "empty_array_allowed_only_for") ==
              "present_empty_submission_registry_or_declaration_or_UNREVIEWED_approved_clear_outline_mm" &&
              encoding.GetProperty("no_global_unknown_collection_default").GetBoolean() &&
              encoding.GetProperty("partially_populated_PointMm_or_Point3Mm_forbidden").GetBoolean() &&
              encoding.GetProperty("zero_is_never_an_unknown_numeric_sentinel").GetBoolean() &&
              encoding.GetProperty("records_must_describe_measured_reality_not_candidate_geometry").GetBoolean(),
            "D186 per-field null/empty/no-sentinel encoding contract changed.");

        var catalog = root.GetProperty("native_field_catalog");
        AssertCatalog<PointMm>(catalog, "PointMm");
        AssertCatalog<Point3Mm>(catalog, "Point3Mm");
        AssertCatalog<PhysicalVerification>(catalog, "PhysicalVerification");
        AssertCatalog<DatumControlPoint>(catalog, "DatumControlPoint");
        AssertCatalog<SharedSpatialDatum>(catalog, "SharedSpatialDatum");
        AssertCatalog<FloorLevel>(catalog, "FloorLevel");
        AssertCatalog<WallSegment>(catalog, "WallSegment");
        AssertCatalog<WindowOpening>(catalog, "WindowOpening");
        AssertCatalog<DoorOpening>(catalog, "DoorOpening");
        AssertCatalog<InterfloorOpeningFace>(catalog, "InterfloorOpeningFace");
        AssertCatalog<StructuralDisposition>(catalog, "StructuralDisposition",
            "null_or_omitted_while_unknown; when_present_status_controls_approved_clear_outline_mm_encoding");
        AssertCatalog<InterfloorOpening>(catalog, "InterfloorOpening");
        AssertCatalog<FloorLayer>(catalog, "FloorLayer");
        AssertCatalog<FloorBuildUp>(catalog, "FloorBuildUp");
        AssertCatalog<FloorArchitectureRegistryVerification>(catalog, "FloorArchitectureRegistryVerification");
        AssertCatalog<InterfloorOpeningRegistryVerification>(catalog,
            "InterfloorOpeningRegistryVerification");

        var point3Rules = catalog.GetProperty("Point3Mm")
            .GetProperty("per_field_unknown_or_population_rules");
        Equal("null_or_omitted_when_unknown; when present x_mm/y_mm/z_mm are all finite numeric values",
            Text(point3Rules, "object"), "Point3 population rule");
        var wallRules = catalog.GetProperty("WallSegment")
            .GetProperty("per_field_unknown_or_population_rules");
        Equal("null_or_omitted_when_unknown; measured_nonempty_array_when_present",
            Text(wallRules, "verified_finish_face_a_outline_mm"), "wall face A outline rule");
        Equal("null_or_omitted_when_unknown; measured_nonempty_array_when_present",
            Text(wallRules, "verified_finish_face_b_outline_mm"), "wall face B outline rule");
        foreach (var name in new[] { "WindowOpening", "DoorOpening", "InterfloorOpeningFace" })
            Check(Text(catalog.GetProperty(name).GetProperty("per_field_unknown_or_population_rules"),
                           "verified_plan_outline_mm").StartsWith("null_or_omitted_when_unknown;", StringComparison.Ordinal),
                $"{name} optional outline null rule changed.");
        Equal("whole_disposition_unknown=null_or_omitted; UNREVIEWED_record=omitted_or_empty_array_never_null; EXISTING_OPENING_ACCEPTED_or_NEW_OPENING_APPROVED=nonempty_simple_polygon",
            Text(catalog.GetProperty("StructuralDisposition")
                .GetProperty("per_field_unknown_or_population_rules"), "approved_clear_outline_mm"),
            "structural disposition/outline state rule");
        Equal("null_or_omitted_while_unknown; when_present_follow_StructuralDisposition_state_contract",
            Text(catalog.GetProperty("InterfloorOpening")
                .GetProperty("per_field_unknown_or_population_rules"), "structural_disposition"),
            "interfloor opening structural-disposition field rule");
        Equal("null_or_omitted_when_unknown; nonempty_array_when_verified",
            Text(catalog.GetProperty("FloorBuildUp")
                .GetProperty("per_field_unknown_or_population_rules"), "layer_registry"),
            "layer registry null rule");

        var representationFields = new[]
        {
            "centerline_mm_shared_datum", "clear_axis_vector",
            "clear_axis_azimuth_degrees_shared_datum",
            "clear_axis_inclination_degrees_shared_datum",
            "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
        };
        var skeletons = root.GetProperty("axis_method_skeletons");
        AssertAxisSkeleton(skeletons, "FACE_CENTERS",
            ["from_floor_face.center_mm_shared_datum", "to_floor_face.center_mm_shared_datum"],
            representationFields);
        AssertAxisSkeleton(skeletons, "CENTERLINE_POLYLINE",
            ["centerline_mm_shared_datum"],
            ["clear_axis_vector", "clear_axis_azimuth_degrees_shared_datum",
             "clear_axis_inclination_degrees_shared_datum",
             "clear_axis_orientation_tolerance_degrees", "clear_axis_direction"]);
        AssertAxisSkeleton(skeletons, "VECTOR_AND_ORIENTATION",
            ["clear_axis_vector", "clear_axis_azimuth_degrees_shared_datum",
             "clear_axis_inclination_degrees_shared_datum",
             "clear_axis_orientation_tolerance_degrees", "clear_axis_direction"],
            ["centerline_mm_shared_datum"]);
        var structuralSkeletons = root.GetProperty("structural_disposition_state_skeletons");
        var unknownStructural = structuralSkeletons.GetProperty("UNKNOWN");
        Check(unknownStructural.GetProperty("structural_disposition").ValueKind == JsonValueKind.Null &&
              unknownStructural.GetProperty("whole_field_may_be_omitted").GetBoolean(),
            "D186 unknown StructuralDisposition skeleton must be null or omitted.");
        var unreviewedStructural = structuralSkeletons.GetProperty("UNREVIEWED_RECORD");
        var unreviewedRecord = unreviewedStructural.GetProperty("structural_disposition");
        Check(Text(unreviewedRecord, "status") == "UNREVIEWED" &&
              unreviewedRecord.GetProperty("approved_clear_outline_mm").ValueKind == JsonValueKind.Array &&
              unreviewedRecord.GetProperty("approved_clear_outline_mm").GetArrayLength() == 0 &&
              Text(unreviewedStructural, "approved_clear_outline_mm_encoding") ==
              "shown_as_present_empty_array; property_may_instead_be_omitted; explicit_null_forbidden" &&
              !ContainsExplicitNullProperty(root, "approved_clear_outline_mm"),
            "D186 UNREVIEWED StructuralDisposition skeleton permits an explicit null outline.");
        var approvedStructural = structuralSkeletons.GetProperty("APPROVED_RECORD");
        AssertStrings(approvedStructural, "allowed_statuses",
            "EXISTING_OPENING_ACCEPTED", "NEW_OPENING_APPROVED");
        Equal("required_nonempty_simple_polygon",
            Text(approvedStructural, "approved_clear_outline_mm_encoding"),
            "approved StructuralDisposition outline skeleton");

        var inputs = root.GetProperty("empty_input_records");
        Check(inputs.GetProperty("shared_spatial_datum").ValueKind == JsonValueKind.Null,
            "D186 template invented a shared datum.");
        var emptyInputCollections = new[]
        {
            "level_physical_input_records", "walls", "windows", "door_openings", "floor_build_ups",
            "floor_architecture_registry_verifications", "interfloor_openings",
            "interfloor_opening_registry_verifications",
        };
        foreach (var collection in emptyInputCollections)
            Equal(0, inputs.GetProperty(collection).GetArrayLength(), $"empty {collection}");
        var emptyArrayPaths = new List<string>();
        CollectEmptyArrayPaths(root, "$", emptyArrayPaths);
        var expectedEmptyArrayPaths = emptyInputCollections
            .Select(name => $"$.empty_input_records.{name}")
            .Append("$.structural_disposition_state_skeletons.UNREVIEWED_RECORD.structural_disposition.approved_clear_outline_mm")
            .Order(StringComparer.Ordinal).ToArray();
        Check(emptyArrayPaths.Order(StringComparer.Ordinal).SequenceEqual(expectedEmptyArrayPaths),
            $"D186 [] is not limited to present empty registries/declarations or the exact UNREVIEWED structural-outline exception: {string.Join(',', emptyArrayPaths)}");

        AssertExactStrings(root, "physical_verification_semantics",
            "Routing readiness accepts only INDEPENDENTLY_VERIFIED records with measurement_source_type, measured_by, yyyy-MM-dd measurement_date, positive survey_tolerance_mm, and source_document_id OR a nonempty source_document_paths array.",
            "photo_evidence_paths and independent_verification_record_ids are nonempty for independently verified records; every evidence array contains no blank element.",
            "A verified shared datum requires nonempty coordinate/horizontal/vertical references, a resolvable horizontal-origin control-point id, and at least one finite control point on every bound floor.");
        AssertExactStrings(root, "opening_shape_and_axis_semantics",
            "CIRCULAR requires clear_diameter_mm, forbids width/length, and requires at least eight distinct measured points on each declared circle; each axis-aligned X/Y face extent equals the diameter within survey tolerance.",
            "RECTANGULAR requires clear_width_mm and clear_length_mm, forbids diameter, and each face is exactly the four axis-aligned bbox corners; width is maxX-minX and length is maxY-minY with no swapped or rotated interpretation.",
            "NONRECTANGULAR forbids diameter/width/length; its two verified_plan_outline_mm face polygons are the complete shape records.",
            "center_mm_shared_datum is the only face-center representation: bbox midpoint for CIRCULAR/RECTANGULAR and polygon centroid for NONRECTANGULAR, within survey tolerance.",
            "FACE_CENTERS forbids centerline and every vector/orientation field; clear_depth_mm is the Euclidean 3D distance between face centers.",
            "CENTERLINE_POLYLINE requires centerline_mm_shared_datum endpoints at the face centers, forbids every vector/orientation field, and clear_depth_mm is the sum of its nonzero 3D segment lengths.",
            "VECTOR_AND_ORIENTATION forbids centerline, requires nonzero clear_axis_vector plus numeric azimuth, inclination, declared angular tolerance, and FROM_TO/TO_FROM direction; clear_depth_mm remains the 3D face-center distance rather than vector magnitude.",
            "clear_bottom/top elevations equal the minimum/maximum face-center Z values within survey tolerance; their vertical span cannot exceed clear_depth_mm.",
            "Every CENTERLINE_POLYLINE point has finite numeric XYZ, XY inside the project canvas, and Z inside the declared clear_bottom/top interval within survey tolerance.",
            "Each face elevation min/max range lies inside the declared clear_bottom/top interval, and center_mm_shared_datum.Z lies inside its own face range within survey tolerance.",
            "For VECTOR_AND_ORIENTATION, vector-derived azimuth and inclination agree with declared numeric angles within clear_axis_orientation_tolerance_degrees.",
            "For VECTOR_AND_ORIENTATION, clear_axis_vector is collinear/aligned with the from-face-to-to-face center displacement within clear_axis_orientation_tolerance_degrees, and clear_axis_direction agrees with the sign of their dot product.");
        AssertExactStrings(root, "architecture_and_floor_semantics",
            "All 33 legacy walls and 8 legacy windows must receive truthful floor scope before the cross-floor architecture scope gate can pass; filename/id prefixes are not floor attribution.",
            "Each verified wall is a nonzero orthogonal centerline with two measured collinear finish-face spans symmetric about it, separated by thickness_mm, plus base/top shared-datum elevations.",
            "Every verified polygon is nondegenerate, has nonzero area, is simple, and has no self-intersection.",
            "Each verified window/door references a verified wall on the same floor; start/end, clear width, four-corner wall-body outline, heights, sill/threshold elevation, and evidence agree within survey tolerance.",
            "A window vertical interval [sill_elevation_mm_shared_datum, sill_elevation_mm_shared_datum + opening_height_mm] lies fully inside its parent wall [base_elevation_mm_shared_datum, top_elevation_mm_shared_datum] within survey tolerance.",
            "Door NONE requires threshold_height_mm null_or_zero and threshold_elevation_mm_shared_datum null; resolved_bottom is floor FFL. FLUSH requires height null_or_zero and threshold elevation equal to FFL within tolerance; resolved_bottom is threshold elevation. RAISED requires positive height and threshold elevation equal to FFL plus height within tolerance; resolved_bottom is threshold elevation.",
            "A door vertical interval [resolved_bottom, resolved_bottom + clear_height_mm] lies fully inside its parent wall [base_elevation_mm_shared_datum, top_elevation_mm_shared_datum] within survey tolerance.",
            "Door thresholds are fields of DoorOpening; schema 1.1 has no standalone threshold collection.",
            "Floor total_build_up_thickness_mm equals both the layer_registry sum and installed_insulation_mm plus remaining_height_mm; the allowed pipe-axis elevation plus/minus tolerance lies inside [FFL-total, FFL].",
            "Exactly one independently verified FloorBuildUp exists for each required physical floor.",
            "Complete, independently verified floor and interfloor population declarations are required; an exclusion or out-of-plane length is never proof of an opening.");
        var structural = root.GetProperty("structural_disposition_boundary");
        Check(!structural.GetProperty("required_for_empty_evidence_gate").GetBoolean() &&
              structural.GetProperty("required_before_installation_input_readiness").GetBoolean() &&
              structural.GetProperty("approved_status_requires_record_authority_date_document_and_outline_covering_both_faces").GetBoolean() &&
              structural.GetProperty("unknown_structural_disposition_is_null_or_omitted").GetBoolean() &&
              structural.GetProperty("UNREVIEWED_record_approved_clear_outline_is_omitted_or_empty_array_never_null").GetBoolean() &&
              structural.GetProperty("approved_status_requires_nonempty_simple_approved_clear_outline").GetBoolean() &&
              structural.GetProperty("approved_outline_is_nondegenerate_simple_and_contains_both_full_face_polygon_areas").GetBoolean() &&
              structural.GetProperty("approved_outline_contains_the_full_projected_axis_not_only_axis_vertices").GetBoolean(),
            "D186 structural outline/full-area/full-axis contract changed.");
        Check(!root.GetProperty("native_capability_limit")
                   .GetProperty("segment_to_opening_route_binding_modeled").GetBoolean() &&
              !root.GetProperty("native_capability_limit")
                   .GetProperty("physical_installation_completeness_can_pass_for_cross_floor_D185_upgrade").GetBoolean(),
            "D186 template overstated schema 1.1 installation capability.");
        Check(!root.GetProperty("template_populated").GetBoolean() &&
              !root.GetProperty("owner_style_route_release").GetBoolean() &&
              !root.GetProperty("installation_ready").GetBoolean(),
            "D186 empty template incorrectly released routes or installation.");
    }

    private static void ValidateReadme(string path, bool isOfficial)
    {
        var readme = File.ReadAllText(path);
        Check(readme.Contains("неизвестный StructuralDisposition целиком null/omitted", StringComparison.Ordinal) &&
              readme.Contains("UNREVIEWED, approved_clear_outline_mm только omitted или [], никогда null",
                  StringComparison.Ordinal) &&
              readme.Contains("approved status требует непустой простой polygon", StringComparison.Ordinal) &&
              readme.Contains("коллинеарность вектора смещению центров граней", StringComparison.Ordinal) &&
              readme.Contains("clear_axis_orientation_tolerance_degrees", StringComparison.Ordinal),
            "D186 README omits the exact structural state or vector/face-center alignment contract.");
        if (isOfficial)
            Check(readme.Contains(OfficialPublicationState, StringComparison.Ordinal) &&
                  readme.Contains(AcceptedScaffoldPackageSha, StringComparison.Ordinal) &&
                  readme.Contains("d186_semantic_audit", StringComparison.Ordinal) &&
                  readme.Contains("d186_package_audit", StringComparison.Ordinal) &&
                  readme.Contains("RESULT_57_OF_57_PASSED", StringComparison.Ordinal) &&
                  readme.Contains("explicit root GO", StringComparison.OrdinalIgnoreCase) &&
                  readme.Contains("no geometry, routes, sleeves, `.homeaura`, renders or installation claim",
                      StringComparison.Ordinal),
                "Official D186 README omits the exact audit/current-validation/excluded-claim publication state.");
    }

    private static void ValidateStatus(string repositoryRoot, string directory, string path,
        string sourceProject, string sourceContract, bool isOfficial)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var root = document.RootElement;
        Equal(ArtifactId, Text(root, "artifact_id"), "D186 status artifact id");
        Equal(BlockedReason, Text(root, "result"), "D186 status result");
        Equal(BlockedReason, Text(root, "blocked_reason"), "D186 status blocker");
        Equal("1.0", Text(root, "source_project_schema_version"), "D186 status source schema");
        Equal(SourceProjectSha, Text(root, "source_project_sha256"), "D186 status project source");
        Equal(SourceContractSha, Text(root, "source_contract_sha256"), "D186 status contract source");
        Equal(SourceDiagnosticsSha, Text(root, "source_diagnostics_sha256"),
            "D186 status diagnostics source");
        Equal(SourceManifestSha, Text(root, "source_manifest_sha256"), "D186 status manifest source");
        Equal(SourcePackageSha, Text(root, "source_package_sha256"), "D186 status package source");
        Equal(9, root.GetProperty("runtime_test_doc_surface_file_count").GetInt32(),
            "D186 status surface file count");
        Equal(Schema11SurfaceDigest(AcceptedSchema11ImplementationHashes),
            Text(root, "implementation_binding_digest"), "D186 historical status surface digest");
        Equal("PASS_0_WARNINGS_0_ERRORS", Text(root, "release_build_result"),
            "D186 status Release build claim");
        Equal("RESULT_56_OF_56_PASSED", Text(root, "registered_suite_result"),
            "D186 status registered suite claim");
        Equal("homeaura-native-editor-tests/Program.cs", Text(root, "registered_suite_program_path"),
            "D186 status registered suite program path");
        Equal(AcceptedSchema11ImplementationHashes[ProgramPath],
            Text(root, "registered_suite_program_sha256"), "D186 status registered suite program hash");
        Check(root.GetProperty("native_schema_11_implemented").GetBoolean() &&
              root.GetProperty("schema11_final_GO_received").GetBoolean() &&
              root.GetProperty("direct_D185_physical_input_applicable").GetBoolean() &&
              !root.GetProperty("direct_D185_verified_architecture_pass").GetBoolean() &&
              !root.GetProperty("direct_D185_verified_interfloor_opening_pass").GetBoolean() &&
              !root.GetProperty("direct_D185_route_opening_binding_pass").GetBoolean() &&
              !root.GetProperty("direct_D185_installation_input_pass").GetBoolean() &&
              root.GetProperty("evidence_only").GetBoolean() &&
              root.GetProperty("added_geometry_count").GetInt32() == 0 &&
              root.GetProperty("homeaura_file_count").GetInt32() == 0 &&
              root.GetProperty("render_file_count").GetInt32() == 0 &&
              !root.GetProperty("sleeves_added").GetBoolean() &&
              !root.GetProperty("owner_style_route_release").GetBoolean() &&
              !root.GetProperty("K2_route_release").GetBoolean() &&
              !root.GetProperty("install").GetBoolean() &&
              !root.GetProperty("installation_ready").GetBoolean() &&
              !root.GetProperty("template_populated").GetBoolean(),
            "D186 status crossed its evidence-only boundary.");
        if (isOfficial)
        {
            Check(Text(root, "publication_state") == OfficialPublicationState &&
                  !root.GetProperty("publishable").GetBoolean() &&
                  root.GetProperty("official_files_modified").GetBoolean() &&
                  !root.GetProperty("root_review_required").GetBoolean() &&
                  root.GetProperty("independent_D186_package_reviewer_GO_received").GetBoolean() &&
                  root.GetProperty("official_D186_freeze_allowed").GetBoolean(),
                "Official D186 status lost its evidence-only publication guard.");
            ValidateAcceptedScaffoldBinding(root.GetProperty("accepted_scaffold_validation_binding"),
                root.GetProperty("historical_native_schema_11_capability_binding"));
            ValidateOfficialPublicationSummary(root.GetProperty("official_publication"));
            ValidateCurrentOfficialBinding(repositoryRoot,
                root.GetProperty("current_official_validation_binding"));
            Equal(PublicationAuditReceiptSha,
                Sha(Path.Combine(directory, "publication_audit_receipt.json")),
                "official status receipt parity");
        }
        else
            Check(Text(root, "publication_state") == "SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL" &&
                  !root.GetProperty("publishable").GetBoolean() &&
                  !root.GetProperty("official_files_modified").GetBoolean() &&
                  root.GetProperty("root_review_required").GetBoolean() &&
                  !root.GetProperty("independent_D186_package_reviewer_GO_received").GetBoolean() &&
                  !root.GetProperty("official_D186_freeze_allowed").GetBoolean(),
                "D186 scaffold status lost its publication guard.");
        Equal(SourceProjectSha, Sha(sourceProject), "D186 status immutable D185 project");
        Equal(SourceContractSha, Sha(sourceContract), "D186 status immutable D185 contract");
    }

    private static void ValidateManifestAndPackage(string root, string directory, string package,
        string manifestPath, string sourceProject, string sourceContract, bool isOfficial)
    {
        if (isOfficial)
        {
            ValidateOfficialManifestAndPackage(root, directory, package, manifestPath);
            return;
        }
        using var document = JsonDocument.Parse(File.ReadAllText(manifestPath));
        var manifest = document.RootElement;
        Equal(ArtifactId, Text(manifest, "artifact_id"), "D186 manifest artifact id");
        Check(manifest.GetProperty("append_only").GetBoolean() &&
              manifest.GetProperty("evidence_only").GetBoolean() &&
              manifest.GetProperty("homeaura_file_count").GetInt32() == 0 &&
              manifest.GetProperty("render_file_count").GetInt32() == 0,
            "D186 manifest crossed its evidence-only boundary.");
        Equal("SCAFFOLD_REVIEW_REQUIRED_NOT_OFFICIAL", Text(manifest, "publication_state"),
            "D186 manifest publication state");
        Equal(SourceProjectSha, Text(manifest, "source_project_sha256"), "manifest D185 project");
        Equal(SourceContractSha, Text(manifest, "source_contract_sha256"), "manifest D185 contract");
        Equal(SourceDiagnosticsSha, Text(manifest, "source_diagnostics_sha256"),
            "manifest D185 diagnostics");
        Equal(SourceManifestSha, Text(manifest, "source_manifest_sha256"), "manifest D185 manifest");
        Equal(SourcePackageSha, Text(manifest, "source_package_sha256"), "manifest D185 package");
        var generator = manifest.GetProperty("deterministic_generator");
        var generatorPath = Path.Combine(root, Text(generator, "path").Replace('/', Path.DirectorySeparatorChar));
        Equal(Sha(generatorPath), Text(generator, "sha256"), "D186 generator hash");

        var implementationFiles = manifest.GetProperty("schema11_implementation_files").EnumerateArray()
            .ToDictionary(item => Text(item, "path"), item => Text(item, "sha256"), StringComparer.Ordinal);
        Equal(9, manifest.GetProperty("runtime_test_doc_surface_file_count").GetInt32(),
            "D186 manifest surface file count");
        Check(implementationFiles.Count == 9 &&
              AcceptedSchema11ImplementationHashes.All(item =>
                  implementationFiles.GetValueOrDefault(item.Key) == item.Value),
            "D186 manifest schema 1.1 binding changed.");
        var implementationArray = manifest.GetProperty("schema11_implementation_files");
        var acceptance = manifest.GetProperty("acceptance_evidence_binding");
        Equal(CanonicalDigest(implementationArray, "__none__"), Text(acceptance, "surface_binding_digest"),
            "D186 manifest surface binding digest");
        Equal(Schema11SurfaceDigest(AcceptedSchema11ImplementationHashes),
            Text(acceptance, "surface_binding_digest"),
            "D186 manifest exact surface binding digest");
        Equal("PASS_0_WARNINGS_0_ERRORS", Text(acceptance, "release_build_result"),
            "D186 manifest Release build claim");
        Equal("RESULT_56_OF_56_PASSED", Text(acceptance, "registered_suite_result"),
            "D186 manifest registered suite claim");
        Equal("homeaura-native-editor-tests/Program.cs", Text(acceptance, "registered_suite_program_path"),
            "D186 manifest registered suite program path");
        Equal(AcceptedSchema11ImplementationHashes[ProgramPath],
            Text(acceptance, "registered_suite_program_sha256"),
            "D186 manifest registered suite program hash");
        Equal(SourceDiagnosticsSha, Text(acceptance, "D185_diagnostics_exact_sha256"),
            "D186 manifest exact diagnostics acceptance hash");
        Equal(SourceManifestSha, Text(acceptance, "D185_manifest_sha256"),
            "D186 manifest D185 manifest acceptance hash");
        Equal(SourcePackageSha, Text(acceptance, "D185_package_sha256"),
            "D186 manifest D185 package acceptance hash");

        var expectedPayloadNames = new[]
        {
            "README.md", "attic_as_built_input_template.json",
            "attic_verified_physical_input_gate.json", "status.json",
        };
        var manifestNames = manifest.GetProperty("files").EnumerateArray()
            .Select(item => Text(item, "name")).Order().ToArray();
        Check(manifestNames.SequenceEqual(expectedPayloadNames.Order()), "D186 manifest payload set changed.");
        foreach (var item in manifest.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, Text(item, "name"));
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == Text(item, "sha256"), $"D186 manifest parity failed: {path}");
        }

        var directoryNames = Directory.GetFiles(directory).Select(Path.GetFileName).Order().ToArray();
        var expectedDirectoryNames = expectedPayloadNames.Append("artifact_manifest.json").Order().ToArray();
        Check(directoryNames.SequenceEqual(expectedDirectoryNames), "D186 directory member set changed.");
        using var archive = ZipFile.OpenRead(package);
        var zipNames = archive.Entries.Select(item => item.FullName).ToArray();
        Check(zipNames.SequenceEqual(expectedDirectoryNames), "D186 ZIP member order/set is not deterministic.");
        foreach (var entry in archive.Entries)
        {
            Check(entry.LastWriteTime.Year == 1980 && entry.LastWriteTime.Month == 1 &&
                  entry.LastWriteTime.Day == 1 && entry.LastWriteTime.Hour == 0 &&
                  entry.LastWriteTime.Minute == 0 && entry.LastWriteTime.Second == 0,
                $"D186 ZIP timestamp changed: {entry.FullName}");
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"D186 ZIP byte parity failed: {entry.FullName}");
        }
    }

    private static void ValidateOfficialManifestAndPackage(string root, string directory, string package,
        string manifestPath)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(manifestPath));
        var manifest = document.RootElement;
        Equal(ArtifactId, Text(manifest, "artifact_id"), "official D186 manifest artifact id");
        Equal(OfficialPublicationState, Text(manifest, "publication_state"),
            "official D186 manifest publication state");
        Equal(BlockedReason, Text(manifest, "result"), "official D186 manifest result");
        Equal(BlockedReason, Text(manifest, "blocked_reason"), "official D186 manifest blocker");
        Check(manifest.GetProperty("append_only").GetBoolean() &&
              manifest.GetProperty("evidence_only").GetBoolean() &&
              !manifest.GetProperty("publishable").GetBoolean() &&
              !manifest.GetProperty("installation_ready").GetBoolean() &&
              !manifest.GetProperty("install").GetBoolean() &&
              manifest.GetProperty("homeaura_file_count").GetInt32() == 0 &&
              manifest.GetProperty("render_file_count").GetInt32() == 0 &&
              manifest.GetProperty("geometry_file_count").GetInt32() == 0 &&
              manifest.GetProperty("route_file_count").GetInt32() == 0 &&
              manifest.GetProperty("sleeve_file_count").GetInt32() == 0,
            "Official D186 manifest crossed its evidence-only boundary.");
        Equal(SourceProjectSha, Text(manifest, "source_project_sha256"), "official manifest D185 project");
        Equal(SourceContractSha, Text(manifest, "source_contract_sha256"), "official manifest D185 contract");
        Equal(SourceDiagnosticsSha, Text(manifest, "source_diagnostics_sha256"),
            "official manifest D185 diagnostics");
        Equal(SourceManifestSha, Text(manifest, "source_manifest_sha256"),
            "official manifest D185 manifest");
        Equal(SourcePackageSha, Text(manifest, "source_package_sha256"), "official manifest D185 package");
        Check(!ContainsProperty(manifest, "official_package_sha256") &&
              !ContainsProperty(manifest, "official_manifest_sha256") &&
              !ContainsProperty(manifest, "manifest_self_sha256"),
            "Official D186 manifest introduced a ZIP/manifest reverse self-hash.");

        var publisher = manifest.GetProperty("official_publisher");
        var publisherPath = Text(publisher, "path");
        Equal("homeaura-native-editor-generate/publish_attic_verified_physical_input_gate_186.py",
            publisherPath, "official D186 publisher path");
        Equal(Sha(Path.Combine(root, publisherPath.Replace('/', Path.DirectorySeparatorChar))),
            Text(publisher, "sha256"), "official D186 dynamic publisher hash");
        var validator = manifest.GetProperty("official_validator");
        Equal(ValidatorPath, Text(validator, "path"), "official D186 validator path");
        Equal(Sha(Path.Combine(root, ValidatorPath.Replace('/', Path.DirectorySeparatorChar))),
            Text(validator, "sha256"), "official D186 validator hash");
        var program = manifest.GetProperty("registered_suite_program");
        Equal(ProgramPath, Text(program, "path"), "official D186 Program path");
        Equal(CurrentProgramSha, Text(program, "sha256"), "official D186 Program hash");

        var receipt = manifest.GetProperty("publication_audit_receipt");
        Equal("publication_audit_receipt.json", Text(receipt, "path"),
            "official manifest audit receipt path");
        Equal(PublicationAuditReceiptSha, Text(receipt, "sha256"),
            "official manifest audit receipt hash");
        ValidateAcceptedScaffoldBinding(manifest.GetProperty("accepted_scaffold_validation_binding"),
            manifest.GetProperty("historical_native_schema_11_capability_binding"));
        ValidateOfficialPublicationSummary(manifest.GetProperty("official_publication"));
        ValidateCurrentOfficialBinding(root, manifest.GetProperty("current_official_validation_binding"));

        var guard = manifest.GetProperty("publication_guard");
        Check(!guard.GetProperty("active").GetBoolean() &&
              guard.GetProperty("evidence_only_official_publication_allowed").GetBoolean() &&
              guard.GetProperty("independent_reviewer_GO_received").GetBoolean() &&
              guard.GetProperty("explicit_root_GO_received").GetBoolean() &&
              guard.GetProperty("official_freeze_allowed").GetBoolean() &&
              !guard.GetProperty("root_review_required").GetBoolean() &&
              !guard.GetProperty("physical_release_allowed").GetBoolean() &&
              !guard.GetProperty("installation_allowed").GetBoolean(),
            "Official D186 manifest publication guard changed.");

        var expectedPayloadNames = new[]
        {
            "README.md", "attic_as_built_input_template.json",
            "attic_verified_physical_input_gate.json", "publication_audit_receipt.json", "status.json",
        };
        var manifestNames = manifest.GetProperty("files").EnumerateArray()
            .Select(item => Text(item, "name")).Order().ToArray();
        Check(manifestNames.SequenceEqual(expectedPayloadNames.Order()),
            "Official D186 manifest payload/self-manifest convention changed.");
        foreach (var item in manifest.GetProperty("files").EnumerateArray())
        {
            var path = Path.Combine(directory, Text(item, "name"));
            Check(File.Exists(path) && new FileInfo(path).Length == item.GetProperty("bytes").GetInt64() &&
                  Sha(path) == Text(item, "sha256"), $"Official D186 manifest parity failed: {path}");
        }

        var directoryNames = Directory.GetFiles(directory).Select(Path.GetFileName).Order().ToArray();
        var expectedDirectoryNames = expectedPayloadNames.Append("artifact_manifest.json").Order().ToArray();
        Check(directoryNames.SequenceEqual(expectedDirectoryNames),
            "Official D186 directory member set changed.");
        using var archive = ZipFile.OpenRead(package);
        var zipNames = archive.Entries.Select(item => item.FullName).ToArray();
        Check(zipNames.SequenceEqual(expectedDirectoryNames),
            "Official D186 ZIP member order/set is not deterministic.");
        foreach (var entry in archive.Entries)
        {
            Check(entry.LastWriteTime.Year == 1980 && entry.LastWriteTime.Month == 1 &&
                  entry.LastWriteTime.Day == 1 && entry.LastWriteTime.Hour == 0 &&
                  entry.LastWriteTime.Minute == 0 && entry.LastWriteTime.Second == 0,
                $"Official D186 ZIP timestamp changed: {entry.FullName}");
            using var stream = entry.Open();
            using var memory = new MemoryStream();
            stream.CopyTo(memory);
            Check(memory.ToArray().SequenceEqual(File.ReadAllBytes(Path.Combine(directory, entry.FullName))),
                $"Official D186 ZIP byte parity failed: {entry.FullName}");
        }
    }

    private static void ValidateNoGeometryOrRender(string directory, string package)
    {
        static bool Forbidden(string path) =>
            path.EndsWith(".homeaura.json", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".png", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".pdf", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".svg", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".webp", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".dwg", StringComparison.OrdinalIgnoreCase) ||
            path.EndsWith(".dxf", StringComparison.OrdinalIgnoreCase);
        Check(Directory.GetFiles(directory).All(path => !Forbidden(path)),
            "D186 contains a project or geometry render.");
        using var archive = ZipFile.OpenRead(package);
        Check(archive.Entries.All(item => !Forbidden(item.FullName)),
            "D186 ZIP contains a project or geometry render.");
    }

    private static void ValidateProgramRegistrationBoundary(string root, bool isOfficial)
    {
        var program = File.ReadAllText(Path.Combine(root, "homeaura-native-editor-tests", "Program.cs"));
        const string registration = "AtticVerifiedPhysicalInputGate186Validation.Run";
        var registrationCount = program.Split(registration, StringSplitOptions.None).Length - 1;
        Equal(isOfficial ? 1 : 0, registrationCount,
            isOfficial
                ? "official D186 exact Program registration count"
                : "prepublication D186 Program registration count");
    }

    private static void AssertNoNestedMembers(JsonElement root, string collection, params string[] names)
    {
        foreach (var item in root.GetProperty(collection).EnumerateArray())
            foreach (var name in names)
                Check(!item.TryGetProperty(name, out _), $"D185 {collection} contains schema 1.1 member {name}.");
    }

    private static void AssertCatalog<T>(JsonElement catalog, string name,
        string wholeRecordRule = "null_or_omitted_until_all_required_populated_fields_are_measured")
    {
        var expected = typeof(T).GetProperties(BindingFlags.Instance | BindingFlags.Public)
            .Select(property => property.GetCustomAttribute<JsonPropertyNameAttribute>()?.Name ??
                                JsonNamingPolicy.SnakeCaseLower.ConvertName(property.Name))
            .Order(StringComparer.Ordinal).ToArray();
        var entry = catalog.GetProperty(name);
        var actual = entry.GetProperty("json_fields").EnumerateArray()
            .Select(item => item.GetString() ?? "").Order(StringComparer.Ordinal).ToArray();
        Check(actual.SequenceEqual(expected),
            $"D186 {name} field catalog differs from native DTO: expected {string.Join(',', expected)}; actual {string.Join(',', actual)}");
        Check(entry.GetProperty("unknown_whole_record").ValueKind == JsonValueKind.Null &&
              Text(entry, "whole_record_rule") == wholeRecordRule,
            $"D186 {name} whole-record null rule changed.");
    }

    private static void AssertAxisSkeleton(JsonElement skeletons, string method,
        string[] required, string[] unused)
    {
        var skeleton = skeletons.GetProperty(method);
        Equal(method, Text(skeleton, "clear_axis_definition_method"), $"{method} skeleton method");
        var values = skeleton.GetProperty("unpopulated_representation_values");
        var expectedRepresentationFields = new[]
        {
            "centerline_mm_shared_datum", "clear_axis_vector",
            "clear_axis_azimuth_degrees_shared_datum",
            "clear_axis_inclination_degrees_shared_datum",
            "clear_axis_orientation_tolerance_degrees", "clear_axis_direction",
        };
        Check(values.EnumerateObject().Select(item => item.Name)
                  .SequenceEqual(expectedRepresentationFields) &&
              values.EnumerateObject().All(item => item.Value.ValueKind == JsonValueKind.Null),
            $"D186 {method} unpopulated representation must use only exact null axis fields.");
        Check(skeleton.GetProperty("required_when_independently_verified").EnumerateArray()
                  .Select(item => item.GetString() ?? "").SequenceEqual(required),
            $"D186 {method} required axis fields changed.");
        Check(skeleton.GetProperty("unused_nullable_fields_must_remain_null_or_be_omitted").EnumerateArray()
                  .Select(item => item.GetString() ?? "").SequenceEqual(unused),
            $"D186 {method} unused nullable axis fields changed.");
        Check(skeleton.GetProperty(
                  "required_null_placeholders_must_be_replaced_by_fully_numeric_values_before_submission")
                  .GetBoolean() &&
              Text(skeleton, "non_axis_structural_disposition_rule_reference") ==
              "$.structural_disposition_state_skeletons",
            $"D186 {method} numeric replacement guard changed.");
    }

    private static void AssertExactStrings(JsonElement parent, string property, params string[] expected)
    {
        var actual = parent.GetProperty(property).EnumerateArray()
            .Select(item => item.GetString() ?? "").ToArray();
        Check(actual.SequenceEqual(expected),
            $"D186 {property} contract changed: {string.Join(" | ", actual)}");
    }

    private static void AssertStrings(JsonElement parent, string property, params string[] expected)
    {
        var actual = parent.GetProperty(property).EnumerateArray().Select(item => item.GetString()).ToArray();
        Check(actual.SequenceEqual(expected),
            $"D186 enum {property} differs: {string.Join(',', actual)}");
    }

    private static bool ContainsProperty(JsonElement value, string propertyName)
    {
        return value.ValueKind switch
        {
            JsonValueKind.Object => value.EnumerateObject().Any(item =>
                item.NameEquals(propertyName) || ContainsProperty(item.Value, propertyName)),
            JsonValueKind.Array => value.EnumerateArray().Any(item => ContainsProperty(item, propertyName)),
            _ => false,
        };
    }

    private static bool ContainsExplicitNullProperty(JsonElement value, string propertyName)
    {
        return value.ValueKind switch
        {
            JsonValueKind.Object => value.EnumerateObject().Any(item =>
                item.NameEquals(propertyName) && item.Value.ValueKind == JsonValueKind.Null ||
                ContainsExplicitNullProperty(item.Value, propertyName)),
            JsonValueKind.Array => value.EnumerateArray().Any(item =>
                ContainsExplicitNullProperty(item, propertyName)),
            _ => false,
        };
    }

    private static bool ContainsNumber(JsonElement value)
    {
        return value.ValueKind switch
        {
            JsonValueKind.Number => true,
            JsonValueKind.Object => value.EnumerateObject().Any(item => ContainsNumber(item.Value)),
            JsonValueKind.Array => value.EnumerateArray().Any(ContainsNumber),
            _ => false,
        };
    }

    private static bool ContainsPartiallyPopulatedPoint(JsonElement value)
    {
        if (value.ValueKind == JsonValueKind.Object)
        {
            var pointProperties = value.EnumerateObject()
                .Where(item => item.Name is "x_mm" or "y_mm" or "z_mm")
                .ToDictionary(item => item.Name, item => item.Value, StringComparer.Ordinal);
            if (pointProperties.Count > 0 &&
                (!pointProperties.TryGetValue("x_mm", out var x) || x.ValueKind != JsonValueKind.Number ||
                 !pointProperties.TryGetValue("y_mm", out var y) || y.ValueKind != JsonValueKind.Number ||
                 !pointProperties.TryGetValue("z_mm", out var z) || z.ValueKind != JsonValueKind.Number))
                return true;
            return value.EnumerateObject().Any(item => ContainsPartiallyPopulatedPoint(item.Value));
        }
        return value.ValueKind == JsonValueKind.Array &&
               value.EnumerateArray().Any(ContainsPartiallyPopulatedPoint);
    }

    private static void CollectEmptyArrayPaths(JsonElement value, string path, ICollection<string> result)
    {
        if (value.ValueKind == JsonValueKind.Array)
        {
            if (value.GetArrayLength() == 0)
                result.Add(path);
            var index = 0;
            foreach (var item in value.EnumerateArray())
                CollectEmptyArrayPaths(item, $"{path}[{index++}]", result);
            return;
        }
        if (value.ValueKind == JsonValueKind.Object)
            foreach (var property in value.EnumerateObject())
                CollectEmptyArrayPaths(property.Value, $"{path}.{property.Name}", result);
    }

    private static string Schema11SurfaceDigest(IReadOnlyDictionary<string, string> hashes)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartArray();
            foreach (var item in hashes)
            {
                writer.WriteStartObject();
                writer.WriteString("path", item.Key);
                writer.WriteString("sha256", item.Value);
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
        }
        using var document = JsonDocument.Parse(stream.ToArray());
        return CanonicalDigest(document.RootElement, "__none__");
    }

    private static string CanonicalDigest(JsonElement root, string excludedTopLevelProperty)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream, new JsonWriterOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            Indented = false,
        }))
            WriteCanonical(writer, root, excludedTopLevelProperty, true);
        return Convert.ToHexString(SHA256.HashData(stream.ToArray()));
    }

    private static void WriteCanonical(Utf8JsonWriter writer, JsonElement value,
        string excludedTopLevelProperty, bool topLevel)
    {
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var property in value.EnumerateObject().OrderBy(item => item.Name, StringComparer.Ordinal))
                {
                    if (topLevel && property.Name == excludedTopLevelProperty) continue;
                    writer.WritePropertyName(property.Name);
                    WriteCanonical(writer, property.Value, excludedTopLevelProperty, false);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in value.EnumerateArray())
                    WriteCanonical(writer, item, excludedTopLevelProperty, false);
                writer.WriteEndArray();
                break;
            case JsonValueKind.String:
                writer.WriteStringValue(value.GetString());
                break;
            case JsonValueKind.Number:
                writer.WriteRawValue(value.GetRawText(), skipInputValidation: true);
                break;
            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;
            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                writer.WriteNullValue();
                break;
            default:
                throw new InvalidDataException($"Unsupported JSON kind {value.ValueKind}.");
        }
    }

    private static string FindRoot()
    {
        foreach (var start in new[] { Environment.CurrentDirectory, AppContext.BaseDirectory }.Distinct())
        {
            var current = new DirectoryInfo(start);
            while (current is not null)
            {
                if (Directory.Exists(Path.Combine(current.FullName, "homeaura-native-editor")) &&
                    Directory.Exists(Path.Combine(current.FullName, "homeaura-native-editor-tests")))
                    return current.FullName;
                current = current.Parent;
            }
        }
        throw new DirectoryNotFoundException("HomeAura repository root not found.");
    }

    private static string Text(JsonElement value, string name) =>
        value.GetProperty(name).GetString() ?? throw new InvalidDataException($"{name} is null.");

    private static string Sha(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private static void Equal<T>(T expected, T actual, string label)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new InvalidDataException($"{label}: expected {expected}, actual {actual}");
    }

    private static void Check(bool value, string message)
    {
        if (!value) throw new InvalidDataException(message);
    }
}
