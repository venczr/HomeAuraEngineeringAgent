using System.Text.Json;
using System.Text.Json.Nodes;
using HomeAura.NativeEditor;

internal static class PhysicalInputSchemaValidation
{
    private static readonly string[] Schema11TopLevelKeys =
    [
        "shared_spatial_datum",
        "door_openings",
        "interfloor_openings",
        "floor_architecture_registry_verifications",
        "interfloor_opening_registry_verifications",
    ];

    public static void Run()
    {
        ValidateLegacy10RoundTripAndKeyAbsence();
        ValidateSchema10RejectsSchema11Members();
        ValidateD185ReadinessTruthWithoutChangingLegacyDiagnostics();
        ValidateCompleteSchema11PhysicalInput();
        ValidateSchema11ReferencesAndVerificationEvidence();
        ValidateOpeningShapeAndAxisVariants();
        ValidateVerifiedZeroRegistriesAndConservativeFloorIsolation();
        ValidateOwnerStyleGeneratorRejectsSchema11();
    }

    private static void ValidateLegacy10RoundTripAndKeyAbsence()
    {
        var legacyJson = File.ReadAllText(D185ProjectPath());
        using (var source = JsonDocument.Parse(legacyJson))
        {
            Equal("1.0", source.RootElement.GetProperty("schema_version").GetString(), "D185 schema");
            AssertPropertiesAbsent(source.RootElement, Schema11TopLevelKeys, "legacy top level");
            AssertArrayItemPropertiesAbsent(source.RootElement, "levels",
                ["shared_datum_id", "finished_floor_elevation_mm_shared_datum"]);
            AssertArrayItemPropertiesAbsent(source.RootElement, "walls",
            [
                "floor_id", "verified_finish_face_a_outline_mm", "verified_finish_face_b_outline_mm",
                "base_elevation_mm_shared_datum", "top_elevation_mm_shared_datum", "physical_verification",
            ]);
            AssertArrayItemPropertiesAbsent(source.RootElement, "windows",
            [
                "floor_id", "verified_plan_outline_mm", "clear_width_mm",
                "sill_elevation_mm_shared_datum", "physical_verification",
            ]);
            AssertArrayItemPropertiesAbsent(source.RootElement, "floor_build_ups",
            [
                "build_up_id", "layer_registry", "total_build_up_thickness_mm",
                "allowed_pipe_axis_elevation_mm_shared_datum", "allowed_pipe_axis_tolerance_mm",
                "physical_verification",
            ]);
        }

        var legacy = HomeAuraProject.FromJson(legacyJson);
        Check(legacy.SharedSpatialDatum is null && legacy.DoorOpenings is null && legacy.InterfloorOpenings is null &&
              legacy.FloorArchitectureRegistryVerifications is null &&
              legacy.InterfloorOpeningRegistryVerifications is null,
            "Legacy 1.0 deserialization materialized schema 1.1 collections.");

        var roundTripJson = legacy.ToJson();
        using (var roundTrip = JsonDocument.Parse(roundTripJson))
            AssertPropertiesAbsent(roundTrip.RootElement, Schema11TopLevelKeys, "legacy round-trip top level");
        Check(JsonNode.DeepEquals(JsonNode.Parse(legacyJson), JsonNode.Parse(roundTripJson)),
            "D185 schema 1.0 semantic round-trip changed a legacy property.");
        Equal(legacyJson.Contains("\"schema_version\": \"1.0\"", StringComparison.Ordinal), true,
            "D185 source schema marker");
        Equal("1.0", HomeAuraProject.FromJson(roundTripJson).SchemaVersion, "legacy round-trip schema");

        var diagnostics = CircuitAnalyzer.AnalyzeProject(legacy);
        Check(diagnostics.PhysicalInputReadiness is null && diagnostics.PhysicalInstallationCompletenessPass is null,
            "Schema 1.0 diagnostics exposed schema 1.1 physical readiness fields.");
        using var diagnosticsJson = JsonDocument.Parse(JsonSerializer.Serialize(diagnostics, HomeAuraProject.JsonOptions));
        AssertPropertiesAbsent(diagnosticsJson.RootElement,
            ["physical_input_readiness", "physical_installation_completeness_pass"], "legacy diagnostics");
    }

    private static void ValidateSchema10RejectsSchema11Members()
    {
        var legacyJson = File.ReadAllText(D185ProjectPath());
        var topLevel = JsonNode.Parse(legacyJson)!.AsObject();
        topLevel["door_openings"] = new JsonArray();
        Throws<InvalidDataException>(() => HomeAuraProject.FromJson(topLevel.ToJsonString()),
            "schema 1.0 raw top-level schema 1.1 key");

        var nested = JsonNode.Parse(legacyJson)!.AsObject();
        nested["walls"]!.AsArray()[0]!.AsObject()["floor_id"] = "FLOOR_1";
        Throws<InvalidDataException>(() => HomeAuraProject.FromJson(nested.ToJsonString()),
            "schema 1.0 raw nested schema 1.1 key");

        var missingSchema = JsonNode.Parse(legacyJson)!.AsObject();
        missingSchema.Remove("schema_version");
        missingSchema["interfloor_openings"] = new JsonArray();
        Throws<InvalidDataException>(() => HomeAuraProject.FromJson(missingSchema.ToJsonString()),
            "missing schema_version with schema 1.1 key");

        var programmatic = HomeAuraProject.FromJson(legacyJson);
        programmatic.InterfloorOpenings = [];
        Throws<InvalidDataException>(programmatic.ValidateContract,
            "schema 1.0 programmatic empty schema 1.1 collection");
    }

    private static void ValidateD185ReadinessTruthWithoutChangingLegacyDiagnostics()
    {
        var project = HomeAuraProject.FromJson(File.ReadAllText(D185ProjectPath()));
        var readiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(project);
        Check(readiness.Applicable, "D185 physical readiness should be applicable to its cross-floor collector.");
        Equal(33, readiness.UnscopedWallIds.Count, "D185 unscoped wall count");
        Equal(8, readiness.UnscopedWindowIds.Count, "D185 unscoped window count");
        SequenceEqual(["ATTIC", "FLOOR_1"], readiness.FloorDetails.Select(item => item.FloorId).Order());
        Check(readiness.FloorDetails.All(item => item.RequiredByCrossFloorSystem),
            "Both D185 floors must be required by its cross-floor system.");
        Check(!readiness.ArchitectureFloorScopePass && !readiness.VerifiedArchitectureInputPass &&
              !readiness.VerifiedInterfloorOpeningInputPass && !readiness.RoutingInputReadinessPass &&
              !readiness.StructuralDispositionPass && !readiness.RouteOpeningBindingPass &&
              !readiness.InstallationInputReadinessPass,
            "D185 legacy geometry was incorrectly promoted to verified physical input.");
        Equal(1, readiness.CrossFloorCollectorDetails.Count, "D185 cross-floor collector detail count");
        Equal("K2", readiness.CrossFloorCollectorDetails[0].CollectorId, "D185 cross-floor collector");
        Check(readiness.ReasonCodes.Contains("UNSCOPED_ARCHITECTURE_OBJECTS") &&
              readiness.ReasonCodes.Contains("VERIFIED_FLOOR_ARCHITECTURE_INCOMPLETE") &&
              readiness.ReasonCodes.Contains("VERIFIED_INTERFLOOR_OPENING_INPUT_INCOMPLETE") &&
              readiness.ReasonCodes.Contains("STRUCTURAL_DISPOSITION_INCOMPLETE") &&
              readiness.ReasonCodes.Contains("MATERIALIZED_ROUTE_OPENING_BINDING_NOT_MODELED"),
            "D185 physical-input blockers are incomplete.");
    }

    private static void ValidateCompleteSchema11PhysicalInput()
    {
        var project = CompleteSchema11Fixture();
        project.ValidateContract();

        var json = project.ToJson();
        using (var document = JsonDocument.Parse(json))
        {
            Equal("1.1", document.RootElement.GetProperty("schema_version").GetString(), "physical fixture schema");
            foreach (var key in Schema11TopLevelKeys)
                Check(document.RootElement.TryGetProperty(key, out _), $"Schema 1.1 round-trip omitted {key}.");
        }
        var restored = HomeAuraProject.FromJson(json);
        Equal("DATUM-01", restored.SharedSpatialDatum?.Id, "shared datum round-trip");
        Equal(2, restored.DoorOpenings?.Count, "door round-trip");
        Equal("RECTANGULAR", restored.InterfloorOpenings?.Single().ShapeType, "opening shape round-trip");

        var readiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(restored);
        Check(readiness.Applicable && readiness.ArchitectureFloorScopePass,
            "Complete 1.1 fixture did not enter scoped physical readiness.");
        Check(readiness.FloorDetails.Count == 2 && readiness.FloorDetails.All(item => item.Pass),
            "Complete 1.1 floor inputs did not pass independently per floor.");
        Check(readiness.VerifiedArchitectureInputPass && readiness.VerifiedInterfloorOpeningInputPass &&
              readiness.RoutingInputReadinessPass && readiness.StructuralDispositionPass &&
              readiness.InstallationInputReadinessPass,
            "Complete 1.1 physical input failed a readiness gate.");
        Check(!readiness.RouteOpeningBindingPass,
            "Schema 1.1 must not invent a segment-to-opening route binding.");
        SequenceEqual(["MATERIALIZED_ROUTE_OPENING_BINDING_NOT_MODELED"], readiness.ReasonCodes);

        var opening = readiness.InterfloorOpeningDetails.Single();
        Check(opening.RegistryDeclarationPass && opening.PairedFaceGeometryPass &&
              opening.StructuralDispositionPass && opening.RoutingInputPass,
            "Complete 1.1 opening readiness is incomplete.");
        Equal(1, opening.OpeningCount, "physical opening count");
        Equal(1, opening.IndependentlyVerifiedOpeningCount, "verified physical opening count");

        var diagnostics = CircuitAnalyzer.AnalyzeProject(restored);
        Check(diagnostics.PhysicalInputReadiness is not null,
            "Schema 1.1 project diagnostics omitted physical readiness.");
        Equal(false, diagnostics.PhysicalInstallationCompletenessPass, "route-binding-aware installation result");
        using var diagnosticsJson = JsonDocument.Parse(JsonSerializer.Serialize(diagnostics, HomeAuraProject.JsonOptions));
        Check(diagnosticsJson.RootElement.TryGetProperty("physical_input_readiness", out _) &&
              diagnosticsJson.RootElement.TryGetProperty("physical_installation_completeness_pass", out _),
            "Schema 1.1 diagnostics JSON omitted physical readiness fields.");
    }

    private static void ValidateSchema11ReferencesAndVerificationEvidence()
    {
        var missingDatum = Clone(CompleteSchema11Fixture());
        missingDatum.Levels[0].SharedDatumId = "MISSING-DATUM";
        Throws<InvalidDataException>(missingDatum.ValidateContract, "missing shared datum reference");

        var wrongWallFloor = Clone(CompleteSchema11Fixture());
        wrongWallFloor.DoorOpenings![0].FloorId = "ATTIC";
        Throws<InvalidDataException>(wrongWallFloor.ValidateContract, "door-to-wall floor mismatch");

        var unscopedWindowWall = Clone(CompleteSchema11Fixture());
        unscopedWindowWall.Walls.Single(item => item.Id == "W-FLOOR-1").FloorId = null;
        Throws<InvalidDataException>(unscopedWindowWall.ValidateContract,
            "explicit window assigned to an unscoped wall");

        var crossFloorWindowWall = Clone(CompleteSchema11Fixture());
        crossFloorWindowWall.Windows.Single(item => item.Id == "WIN-FLOOR-1").FloorId = "ATTIC";
        Throws<InvalidDataException>(crossFloorWindowWall.ValidateContract,
            "explicit window-to-wall floor mismatch");

        var wrongOpeningFace = Clone(CompleteSchema11Fixture());
        wrongOpeningFace.InterfloorOpenings![0].ToFloorFace.FloorId = "FLOOR_1";
        Throws<InvalidDataException>(wrongOpeningFace.ValidateContract, "opening face floor mismatch");

        var wrongRegistryDatum = Clone(CompleteSchema11Fixture());
        wrongRegistryDatum.InterfloorOpeningRegistryVerifications![0].SharedDatumId = "MISSING-DATUM";
        Throws<InvalidDataException>(wrongRegistryDatum.ValidateContract, "opening registry datum mismatch");

        var missingIndependentEvidence = Clone(CompleteSchema11Fixture());
        missingIndependentEvidence.Walls[0].PhysicalVerification!.PhotoEvidencePaths.Clear();
        Throws<InvalidDataException>(missingIndependentEvidence.ValidateContract,
            "independent verification without photo evidence");

        var missingPerFloorDatumControl = Clone(CompleteSchema11Fixture());
        missingPerFloorDatumControl.SharedSpatialDatum!.ControlPoints.RemoveAll(item => item.FloorId == "ATTIC");
        Throws<InvalidDataException>(missingPerFloorDatumControl.ValidateContract,
            "independently verified datum has no ATTIC control evidence");
        var missingControlReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(missingPerFloorDatumControl);
        Check(!missingControlReadiness.VerifiedArchitectureInputPass &&
              missingControlReadiness.ReasonCodes.Contains("SCHEMA_1_1_CONTRACT_INVALID"),
            "Missing per-floor datum control evidence passed defensive readiness.");

        var globalIdentityCollision = Clone(CompleteSchema11Fixture());
        globalIdentityCollision.SharedSpatialDatum!.ControlPoints[0].Id = "W-FLOOR-1";
        Throws<InvalidDataException>(globalIdentityCollision.ValidateContract,
            "schema 1.1 identifier collides with legacy object id");

        var raisedWithoutElevation = Clone(CompleteSchema11Fixture());
        var raisedDoor = raisedWithoutElevation.DoorOpenings!.Single(item => item.FloorId == "FLOOR_1");
        raisedDoor.ThresholdDisposition = "RAISED";
        raisedDoor.ThresholdHeightMm = 20;
        raisedDoor.ThresholdElevationMmSharedDatum = null;
        Throws<InvalidDataException>(raisedWithoutElevation.ValidateContract,
            "raised threshold without a shared-datum elevation");

        var duplicateLayerIdentity = Clone(CompleteSchema11Fixture());
        duplicateLayerIdentity.FloorBuildUps[0].LayerRegistry![0].Id = "W-FLOOR-1";
        Throws<InvalidDataException>(duplicateLayerIdentity.ValidateContract,
            "floor-layer identifier collides globally");

        var missingRoomFloor = Clone(CompleteSchema11Fixture());
        missingRoomFloor.Rooms.Add(new RoomZone
        {
            Id = "ROOM-MISSING", FloorId = "MISSING", Outline = Rectangle(0, 0, 500, 500),
            LabelPosition = new(100, 100),
        });
        Throws<InvalidDataException>(missingRoomFloor.ValidateContract, "schema 1.1 room floor is missing");

        var missingExclusionFloor = Clone(CompleteSchema11Fixture());
        missingExclusionFloor.Exclusions.Add(new ExclusionZone
        {
            Id = "EX-MISSING", FloorId = "MISSING", Outline = Rectangle(0, 0, 500, 500),
        });
        Throws<InvalidDataException>(missingExclusionFloor.ValidateContract, "schema 1.1 exclusion floor is missing");

        var missingServiceFloor = Clone(CompleteSchema11Fixture());
        missingServiceFloor.ServiceZones.Add(new ServiceZone
        {
            Id = "SZ-MISSING", FloorId = "MISSING", Outline = Rectangle(0, 0, 500, 500),
        });
        Throws<InvalidDataException>(missingServiceFloor.ValidateContract, "schema 1.1 service-zone floor is missing");

        var inconsistentBuildUp = Clone(CompleteSchema11Fixture());
        inconsistentBuildUp.FloorBuildUps[0].TotalBuildUpThicknessMm = 169;
        Throws<InvalidDataException>(inconsistentBuildUp.ValidateContract,
            "build-up total contradicts layers and migration summary");

        var unnamedBuildUp = Clone(CompleteSchema11Fixture());
        unnamedBuildUp.FloorBuildUps[0].BuildUpId = null;
        unnamedBuildUp.ValidateContract();
        Check(!CircuitAnalyzer.AnalyzePhysicalInputReadiness(unnamedBuildUp).FloorDetails
                .Single(item => item.FloorId == "FLOOR_1").FloorBuildUpAndPipeAxisPass,
            "A populated floor build-up without build_up_id passed readiness.");

        var remoteWindowOutline = Clone(CompleteSchema11Fixture());
        remoteWindowOutline.Windows.Single(item => item.FloorId == "ATTIC").VerifiedPlanOutlineMm =
            Rectangle(4000, 4000, 20, 20);
        Throws<InvalidDataException>(remoteWindowOutline.ValidateContract,
            "verified window outline is remote from its wall opening");

        var remoteDoorOutline = Clone(CompleteSchema11Fixture());
        remoteDoorOutline.DoorOpenings!.Single(item => item.FloorId == "ATTIC").VerifiedPlanOutlineMm =
            Rectangle(4000, 4000, 20, 20);
        Throws<InvalidDataException>(remoteDoorOutline.ValidateContract,
            "verified door outline is remote from its wall opening");

        var overheightWindow = Clone(CompleteSchema11Fixture());
        overheightWindow.Windows.Single(item => item.FloorId == "ATTIC").OpeningHeightMm = 5000;
        Throws<InvalidDataException>(overheightWindow.ValidateContract,
            "verified window vertical opening exceeds its parent wall");
        var overheightWindowReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(overheightWindow);
        Check(!overheightWindowReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").WindowRegistryPass &&
              !overheightWindowReadiness.VerifiedArchitectureInputPass &&
              !overheightWindowReadiness.InstallationInputReadinessPass,
            "live readiness accepted a window whose vertical opening exceeds its wall");

        var overheightDoor = Clone(CompleteSchema11Fixture());
        overheightDoor.DoorOpenings!.Single(item => item.FloorId == "ATTIC").ClearHeightMm = 5000;
        Throws<InvalidDataException>(overheightDoor.ValidateContract,
            "verified door vertical opening exceeds its parent wall");
        var overheightDoorReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(overheightDoor);
        Check(!overheightDoorReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").DoorAndThresholdRegistryPass &&
              !overheightDoorReadiness.VerifiedArchitectureInputPass &&
              !overheightDoorReadiness.InstallationInputReadinessPass,
            "live readiness accepted a door whose vertical opening exceeds its wall");

        var outOfEnvelopeAxis = Clone(CompleteSchema11Fixture());
        outOfEnvelopeAxis.FloorBuildUps[0].AllowedPipeAxisElevationMmSharedDatum = 171;
        Throws<InvalidDataException>(outOfEnvelopeAxis.ValidateContract,
            "pipe-axis tolerance is outside the floor build-up envelope");

        var emptyStructuralEnvelope = Clone(CompleteSchema11Fixture());
        emptyStructuralEnvelope.InterfloorOpenings!.Single().StructuralDisposition!.ApprovedClearOutlineMm.Clear();
        Throws<InvalidDataException>(emptyStructuralEnvelope.ValidateContract,
            "approved structural disposition without a clear envelope");

        var undersizedStructuralEnvelope = Clone(CompleteSchema11Fixture());
        undersizedStructuralEnvelope.InterfloorOpenings!.Single().StructuralDisposition!.ApprovedClearOutlineMm =
            Rectangle(1050, 1550, 100, 300);
        Throws<InvalidDataException>(undersizedStructuralEnvelope.ValidateContract,
            "approved structural envelope does not contain both opening faces");

        var concaveStructuralEnvelope = Clone(CompleteSchema11Fixture());
        concaveStructuralEnvelope.InterfloorOpenings!.Single().StructuralDisposition!.ApprovedClearOutlineMm =
        [
            new(900, 1400), new(1300, 1400), new(1300, 2000), new(1125, 2000),
            new(1125, 1700), new(1075, 1700), new(1075, 2000), new(900, 2000),
        ];
        Throws<InvalidDataException>(concaveStructuralEnvelope.ValidateContract,
            "concave approved envelope whose notch cuts an opening face edge");
        var concaveReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(concaveStructuralEnvelope);
        Check(!concaveReadiness.StructuralDispositionPass && !concaveReadiness.InstallationInputReadinessPass,
            "live readiness must reject a concave structural envelope that excludes opening area");

        var faceCentersCrossStructuralNotch = Clone(CompleteSchema11Fixture());
        var notchOpening = faceCentersCrossStructuralNotch.InterfloorOpenings!.Single();
        notchOpening.ToFloorFace.VerifiedPlanOutlineMm = Rectangle(1800, 1500, 200, 400);
        notchOpening.ToFloorFace.CenterMmSharedDatum = new Point3Mm(1900, 1700, 3100);
        notchOpening.ClearDepthMm = 825;
        notchOpening.StructuralDisposition!.ApprovedClearOutlineMm =
        [
            new(900, 1400), new(2100, 1400), new(2100, 2000), new(1700, 2000),
            new(1700, 1600), new(1300, 1600), new(1300, 2000), new(900, 2000),
        ];
        Throws<InvalidDataException>(faceCentersCrossStructuralNotch.ValidateContract,
            "straight face-centers axis crosses a notch outside the approved structural outline");
        var notchedAxisReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(faceCentersCrossStructuralNotch);
        Check(!notchedAxisReadiness.StructuralDispositionPass && !notchedAxisReadiness.InstallationInputReadinessPass,
            "live readiness accepted a straight opening axis across a structural notch");

        var selfCrossingStructuralEnvelope = Clone(CompleteSchema11Fixture());
        selfCrossingStructuralEnvelope.InterfloorOpenings!.Single().StructuralDisposition!.ApprovedClearOutlineMm =
        [new(900, 1400), new(1300, 2000), new(900, 2000), new(1300, 1400)];
        Throws<InvalidDataException>(selfCrossingStructuralEnvelope.ValidateContract,
            "self-crossing approved structural envelope");

        var merelyMeasured = Clone(CompleteSchema11Fixture());
        merelyMeasured.Walls.Single(item => item.FloorId == "ATTIC").PhysicalVerification!.Status = "MEASURED";
        merelyMeasured.ValidateContract();
        var readiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(merelyMeasured);
        Check(readiness.FloorDetails.Single(item => item.FloorId == "FLOOR_1").Pass,
            "A measured ATTIC object contaminated FLOOR_1 readiness.");
        Check(!readiness.FloorDetails.Single(item => item.FloorId == "ATTIC").Pass &&
              !readiness.VerifiedArchitectureInputPass,
            "MEASURED input was promoted to independently verified architecture.");
    }

    private static void ValidateOpeningShapeAndAxisVariants()
    {
        var circular = Clone(CompleteSchema11Fixture());
        var circularOpening = circular.InterfloorOpenings!.Single();
        circularOpening.ShapeType = "CIRCULAR";
        circularOpening.ClearDiameterMm = 200;
        circularOpening.ClearWidthMm = null;
        circularOpening.ClearLengthMm = null;
        circularOpening.FromFloorFace.VerifiedPlanOutlineMm = Circle(1100, 1700, 100);
        circularOpening.ToFloorFace.VerifiedPlanOutlineMm = Circle(1100, 1700, 100);
        circular.ValidateContract();

        var squareCircle = Clone(circular);
        squareCircle.InterfloorOpenings!.Single().ToFloorFace.VerifiedPlanOutlineMm = Rectangle(1000, 1600, 200, 200);
        Throws<InvalidDataException>(squareCircle.ValidateContract, "CIRCULAR face cannot be a square bbox");

        var offCenter = Clone(CompleteSchema11Fixture());
        offCenter.InterfloorOpenings!.Single().ToFloorFace.CenterMmSharedDatum = new Point3Mm(1000, 1700, 3100);
        Throws<InvalidDataException>(offCenter.ValidateContract, "verified face center must match outline center");

        var rotatedRectangle = Clone(CompleteSchema11Fixture());
        rotatedRectangle.InterfloorOpenings!.Single().ToFloorFace.VerifiedPlanOutlineMm =
            Rectangle(900, 1600, 400, 200);
        Throws<InvalidDataException>(rotatedRectangle.ValidateContract,
            "rectangular face cannot twist 90 degrees without orientation metadata");

        var triangularRectangle = Clone(CompleteSchema11Fixture());
        triangularRectangle.InterfloorOpenings!.Single().ToFloorFace.VerifiedPlanOutlineMm =
        [
            new PointMm(1000, 1500), new PointMm(1200, 1500), new PointMm(1200, 1900),
        ];
        Throws<InvalidDataException>(triangularRectangle.ValidateContract,
            "RECTANGULAR face must be an actual axis-aligned rectangle");

        var nonRectangular = Clone(CompleteSchema11Fixture());
        var nonRectangularOpening = nonRectangular.InterfloorOpenings!.Single();
        nonRectangularOpening.ShapeType = "NONRECTANGULAR";
        nonRectangularOpening.ClearDiameterMm = null;
        nonRectangularOpening.ClearWidthMm = null;
        nonRectangularOpening.ClearLengthMm = null;
        nonRectangular.ValidateContract();

        var centerline = Clone(CompleteSchema11Fixture());
        var centerlineOpening = centerline.InterfloorOpenings!.Single();
        centerlineOpening.ClearAxisDefinitionMethod = "CENTERLINE_POLYLINE";
        centerlineOpening.CenterlineMmSharedDatum =
        [
            Clone(centerlineOpening.FromFloorFace.CenterMmSharedDatum!),
            Clone(centerlineOpening.ToFloorFace.CenterMmSharedDatum!),
        ];
        centerline.ValidateContract();

        var centerlineOutsideVerticalEnvelope = Clone(centerline);
        var outsideCenterlineOpening = centerlineOutsideVerticalEnvelope.InterfloorOpenings!.Single();
        outsideCenterlineOpening.CenterlineMmSharedDatum =
        [
            Clone(outsideCenterlineOpening.FromFloorFace.CenterMmSharedDatum!),
            new Point3Mm(1100, 1700, 5000),
            Clone(outsideCenterlineOpening.ToFloorFace.CenterMmSharedDatum!),
        ];
        outsideCenterlineOpening.ClearDepthMm = 4000;
        Throws<InvalidDataException>(centerlineOutsideVerticalEnvelope.ValidateContract,
            "centerline intermediate point escapes declared opening elevation envelope");
        var outsideCenterlineReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(centerlineOutsideVerticalEnvelope);
        Check(!outsideCenterlineReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !outsideCenterlineReadiness.VerifiedInterfloorOpeningInputPass &&
              !outsideCenterlineReadiness.InstallationInputReadinessPass,
            "live readiness accepted a centerline outside the opening elevation envelope");

        var centerlineOutsideApprovedEnvelope = Clone(centerline);
        var outsideApprovedOpening = centerlineOutsideApprovedEnvelope.InterfloorOpenings!.Single();
        outsideApprovedOpening.CenterlineMmSharedDatum =
        [
            Clone(outsideApprovedOpening.FromFloorFace.CenterMmSharedDatum!),
            new Point3Mm(2000, 1700, 3000),
            Clone(outsideApprovedOpening.ToFloorFace.CenterMmSharedDatum!),
        ];
        outsideApprovedOpening.ClearDepthMm = 1811;
        Throws<InvalidDataException>(centerlineOutsideApprovedEnvelope.ValidateContract,
            "centerline projected segments escape the approved structural outline");
        var outsideApprovedReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(centerlineOutsideApprovedEnvelope);
        Check(!outsideApprovedReadiness.StructuralDispositionPass &&
              !outsideApprovedReadiness.InstallationInputReadinessPass,
            "live readiness accepted a centerline outside the approved structural outline");

        var centerlineOutsideCanvas = Clone(centerline);
        var outsideCanvasOpening = centerlineOutsideCanvas.InterfloorOpenings!.Single();
        outsideCanvasOpening.CenterlineMmSharedDatum =
        [
            Clone(outsideCanvasOpening.FromFloorFace.CenterMmSharedDatum!),
            new Point3Mm(6000, 1700, 3000),
            Clone(outsideCanvasOpening.ToFloorFace.CenterMmSharedDatum!),
        ];
        outsideCanvasOpening.ClearDepthMm = 9802;
        Throws<InvalidDataException>(centerlineOutsideCanvas.ValidateContract,
            "centerline intermediate point escapes the project canvas");
        var outsideCanvasReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(centerlineOutsideCanvas);
        Check(!outsideCanvasReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !outsideCanvasReadiness.VerifiedInterfloorOpeningInputPass &&
              !outsideCanvasReadiness.InstallationInputReadinessPass,
            "live readiness accepted a centerline outside the project canvas");

        var vector = Clone(CompleteSchema11Fixture());
        var vectorOpening = vector.InterfloorOpenings!.Single();
        vectorOpening.ClearAxisDefinitionMethod = "VECTOR_AND_ORIENTATION";
        vectorOpening.ClearAxisVector = new Point3Mm(0, 0, 1);
        vectorOpening.ClearAxisDirection = "FROM_TO";
        vectorOpening.ClearAxisAzimuthDegreesSharedDatum = 0;
        vectorOpening.ClearAxisInclinationDegreesSharedDatum = 90;
        vectorOpening.ClearAxisOrientationToleranceDegrees = 1;
        vector.ValidateContract();

        var fakeNonRectangularSize = Clone(nonRectangular);
        fakeNonRectangularSize.InterfloorOpenings!.Single().ClearWidthMm = 200;
        Throws<InvalidDataException>(fakeNonRectangularSize.ValidateContract,
            "NONRECTANGULAR scalar cross-section dimension");

        var openCenterline = Clone(centerline);
        openCenterline.InterfloorOpenings!.Single().CenterlineMmSharedDatum![^1] = new Point3Mm(1010, 1700, 3100);
        Throws<InvalidDataException>(openCenterline.ValidateContract, "centerline not closed on face center");

        var contradictoryCenterline = Clone(centerline);
        contradictoryCenterline.InterfloorOpenings!.Single().ClearAxisVector = new Point3Mm(0, 0, 1);
        Throws<InvalidDataException>(contradictoryCenterline.ValidateContract,
            "centerline method contains an unused vector representation");

        var reversedVector = Clone(vector);
        reversedVector.InterfloorOpenings!.Single().ClearAxisDirection = "TO_FROM";
        Throws<InvalidDataException>(reversedVector.ValidateContract, "vector direction contradicts face centers");

        var zeroVector = Clone(vector);
        zeroVector.InterfloorOpenings!.Single().ClearAxisVector = new Point3Mm(0, 0, 0);
        Throws<InvalidDataException>(zeroVector.ValidateContract, "zero clear-axis vector");

        var outsideDeclaredAngleTolerance = Clone(vector);
        outsideDeclaredAngleTolerance.InterfloorOpenings!.Single().ClearAxisVector = new Point3Mm(0.1, 0, 1);
        Throws<InvalidDataException>(outsideDeclaredAngleTolerance.ValidateContract,
            "vector-to-centers alignment exceeds declared angular tolerance");

        var inconsistentElevationSpan = Clone(CompleteSchema11Fixture());
        inconsistentElevationSpan.InterfloorOpenings!.Single().ClearTopElevationMmSharedDatum = 3200;
        Throws<InvalidDataException>(inconsistentElevationSpan.ValidateContract,
            "opening elevation span contradicts clear depth and face centers");

        var faceElevationOutsideEnvelope = Clone(CompleteSchema11Fixture());
        var outsideFaceElevationOpening = faceElevationOutsideEnvelope.InterfloorOpenings!.Single();
        outsideFaceElevationOpening.FromFloorFace.FaceElevationMinMmSharedDatum = 0;
        outsideFaceElevationOpening.FromFloorFace.FaceElevationMaxMmSharedDatum = 4000;
        outsideFaceElevationOpening.ToFloorFace.FaceElevationMinMmSharedDatum = 0;
        outsideFaceElevationOpening.ToFloorFace.FaceElevationMaxMmSharedDatum = 4000;
        Throws<InvalidDataException>(faceElevationOutsideEnvelope.ValidateContract,
            "face elevation ranges escape the declared opening elevation envelope");
        var outsideFaceElevationReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(faceElevationOutsideEnvelope);
        Check(!outsideFaceElevationReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !outsideFaceElevationReadiness.VerifiedInterfloorOpeningInputPass &&
              !outsideFaceElevationReadiness.InstallationInputReadinessPass,
            "live readiness accepted face elevation ranges outside the opening envelope");

        var incompleteUnverified = Clone(CompleteSchema11Fixture());
        var unverifiedOpening = incompleteUnverified.InterfloorOpenings!.Single();
        unverifiedOpening.PhysicalVerification = new PhysicalVerification { Status = "UNVERIFIED" };
        unverifiedOpening.ShapeType = null;
        unverifiedOpening.ClearWidthMm = null;
        unverifiedOpening.ClearLengthMm = null;
        unverifiedOpening.ClearDepthMm = null;
        unverifiedOpening.ClearBottomElevationMmSharedDatum = null;
        unverifiedOpening.ClearTopElevationMmSharedDatum = null;
        unverifiedOpening.ClearAxisDefinitionMethod = null;
        unverifiedOpening.FromFloorFace.VerifiedPlanOutlineMm = [];
        unverifiedOpening.ToFloorFace.VerifiedPlanOutlineMm = [];
        unverifiedOpening.FromFloorFace.CenterMmSharedDatum = null;
        unverifiedOpening.ToFloorFace.CenterMmSharedDatum = null;
        unverifiedOpening.FromFloorFace.FaceElevationMinMmSharedDatum = null;
        unverifiedOpening.FromFloorFace.FaceElevationMaxMmSharedDatum = null;
        unverifiedOpening.ToFloorFace.FaceElevationMinMmSharedDatum = null;
        unverifiedOpening.ToFloorFace.FaceElevationMaxMmSharedDatum = null;
        unverifiedOpening.StructuralDisposition = new StructuralDisposition { Status = "UNREVIEWED" };
        incompleteUnverified.ValidateContract();
        var incompleteReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(incompleteUnverified);
        Check(!incompleteReadiness.VerifiedInterfloorOpeningInputPass &&
              !incompleteReadiness.RoutingInputReadinessPass,
            "An intentionally incomplete UNVERIFIED opening passed readiness.");

        var mismatchedRectangle = Clone(CompleteSchema11Fixture());
        mismatchedRectangle.InterfloorOpenings!.Single().ClearWidthMm = 250;
        Throws<InvalidDataException>(mismatchedRectangle.ValidateContract,
            "rectangular dimensions disagree with verified outlines");

        var mismatchedFaceRectangle = Clone(CompleteSchema11Fixture());
        mismatchedFaceRectangle.InterfloorOpenings!.Single().ToFloorFace.VerifiedPlanOutlineMm =
            Rectangle(1000, 1550, 200, 300);
        Throws<InvalidDataException>(mismatchedFaceRectangle.ValidateContract,
            "one rectangular face disagrees with declared dimensions");
    }

    private static void ValidateVerifiedZeroRegistriesAndConservativeFloorIsolation()
    {
        var verifiedZero = Clone(CompleteSchema11Fixture());
        verifiedZero.Windows.RemoveAll(item => item.FloorId == "ATTIC");
        verifiedZero.DoorOpenings!.RemoveAll(item => item.FloorId == "ATTIC");
        verifiedZero.ValidateContract();
        var zeroReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(verifiedZero);
        var zeroFloor = zeroReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC");
        Equal(0, zeroFloor.ExplicitWindowCount, "verified-zero ATTIC windows");
        Equal(0, zeroFloor.ExplicitDoorCount, "verified-zero ATTIC doors");
        Check(zeroFloor.RegistryDeclarationPass && zeroFloor.WindowRegistryPass &&
              zeroFloor.DoorAndThresholdRegistryPass && zeroFloor.Pass,
            "Independently verified complete zero-population window/door registries did not pass.");

        var zeroWalls = Clone(verifiedZero);
        zeroWalls.Walls.RemoveAll(item => item.FloorId == "ATTIC");
        zeroWalls.ValidateContract();
        var zeroWallReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(zeroWalls);
        var zeroWallFloor = zeroWallReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC");
        Check(zeroWallFloor.RegistryDeclarationPass && zeroWallFloor.ExplicitWallCount == 0 &&
              !zeroWallFloor.WallGeometryPass && !zeroWallFloor.Pass,
            "A declaration alone laundered a required floor with no explicit wall geometry.");

        var unscoped = Clone(CompleteSchema11Fixture());
        var unscopedWall = VerifiedWall("W-UNSCOPED", "FLOOR_1", 4000, 0, 3000);
        unscopedWall.FloorId = null;
        unscoped.Walls.Add(unscopedWall);
        unscoped.ValidateContract();
        var unscopedReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(unscoped);
        Check(!unscopedReadiness.ArchitectureFloorScopePass &&
              unscopedReadiness.UnscopedWallIds.SequenceEqual(["W-UNSCOPED"], StringComparer.Ordinal) &&
              unscopedReadiness.FloorDetails.Single(item => item.FloorId == "FLOOR_1").ExplicitWallCount == 1 &&
              unscopedReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").ExplicitWallCount == 1,
            "Unscoped architecture was silently assigned to a floor.");

        var invalidWallFaces = Clone(CompleteSchema11Fixture());
        var atticWall = invalidWallFaces.Walls.Single(item => item.FloorId == "ATTIC");
        atticWall.VerifiedFinishFaceBOutlineMm = [new(500, 3150), new(2500, 3150)];
        invalidWallFaces.ValidateContract();
        var invalidWallReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(invalidWallFaces);
        Check(!invalidWallReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").WallGeometryPass &&
              invalidWallReadiness.FloorDetails.Single(item => item.FloorId == "FLOOR_1").WallGeometryPass,
            "Invalid face-to-face wall thickness was not isolated to its floor.");

        var diagonalWall = Clone(CompleteSchema11Fixture());
        var diagonal = diagonalWall.Walls.Single(item => item.FloorId == "FLOOR_1");
        diagonal.Start = new PointMm(500, 500);
        diagonal.End = new PointMm(2500, 2500);
        diagonal.VerifiedFinishFaceAOutlineMm = [new(571, 429), new(2571, 2429)];
        diagonal.VerifiedFinishFaceBOutlineMm = [new(429, 571), new(2429, 2571)];
        var diagonalReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(diagonalWall);
        Check(!diagonalReadiness.FloorDetails.Single(item => item.FloorId == "FLOOR_1").WallGeometryPass &&
              diagonalReadiness.ReasonCodes.Contains("UNSUPPORTED_WALL_GEOMETRY"),
            "Unsupported diagonal wall geometry passed the orthogonal routing-readiness gate.");

        var invalidInMemoryOpening = Clone(CompleteSchema11Fixture());
        invalidInMemoryOpening.InterfloorOpenings!.Single().ToFloorFace.VerifiedPlanOutlineMm =
        [
            new PointMm(1000, 1500), new PointMm(1200, 1500), new PointMm(1200, 1900),
        ];
        var invalidInMemoryReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(invalidInMemoryOpening);
        Check(!invalidInMemoryReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !invalidInMemoryReadiness.VerifiedInterfloorOpeningInputPass &&
              !invalidInMemoryReadiness.RoutingInputReadinessPass,
            "Analyzer promoted an unsaved invalid opening that ValidateContract would reject.");

        var invalidInMemoryDatum = Clone(CompleteSchema11Fixture());
        invalidInMemoryDatum.InterfloorOpenings!.Single().SharedDatumId = "MISSING-DATUM";
        var invalidDatumReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(invalidInMemoryDatum);
        Check(!invalidDatumReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !invalidDatumReadiness.RoutingInputReadinessPass,
            "Analyzer promoted an opening whose shared datum reference is missing.");

        var invalidInMemoryFaceFloor = Clone(CompleteSchema11Fixture());
        invalidInMemoryFaceFloor.InterfloorOpenings!.Single().ToFloorFace.FloorId = "FLOOR_1";
        var invalidFaceFloorReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(invalidInMemoryFaceFloor);
        Check(!invalidFaceFloorReadiness.InterfloorOpeningDetails.Single().PairedFaceGeometryPass &&
              !invalidFaceFloorReadiness.RoutingInputReadinessPass,
            "Analyzer promoted an opening face assigned to the wrong floor.");

        var incompleteWindow = Clone(CompleteSchema11Fixture());
        var atticWindow = incompleteWindow.Windows.Single(item => item.FloorId == "ATTIC");
        atticWindow.ClearWidthMm = null;
        atticWindow.VerifiedPlanOutlineMm = null;
        atticWindow.SillElevationMmSharedDatum = null;
        incompleteWindow.ValidateContract();
        var incompleteWindowReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(incompleteWindow);
        Check(!incompleteWindowReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").WindowRegistryPass,
            "Readiness accepted a verified window without clear width and shared-datum sill elevation.");

        var incompleteDoor = Clone(CompleteSchema11Fixture());
        incompleteDoor.DoorOpenings!.Single(item => item.FloorId == "ATTIC").ClearHeightMm = null;
        incompleteDoor.ValidateContract();
        var incompleteDoorReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(incompleteDoor);
        Check(!incompleteDoorReadiness.FloorDetails.Single(item => item.FloorId == "ATTIC").DoorAndThresholdRegistryPass,
            "Readiness accepted a verified door without a clear height.");

        var missingServedFloor = Clone(CompleteSchema11Fixture());
        missingServedFloor.Collectors.Single().ServedFloorId = "MISSING-FLOOR";
        Throws<InvalidDataException>(missingServedFloor.ValidateContract,
            "collector served-floor reference is missing");
        // The analyzer remains conservative for an unvalidated/imported in-memory object: malformed
        // references must not disable applicability or disappear from the diagnostic reason set.
        var missingServedReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(missingServedFloor);
        Check(missingServedReadiness.Applicable &&
              !missingServedReadiness.CrossFloorCollectorDetails.Single().FloorReferencesPass &&
              !missingServedReadiness.VerifiedArchitectureInputPass &&
              missingServedReadiness.ReasonCodes.Contains("CROSS_FLOOR_REFERENCE_MISSING"),
            "A missing served floor disabled applicability or escaped the readiness reasons.");

        var ambiguousCollector = Clone(CompleteSchema11Fixture());
        ambiguousCollector.Collectors.Single().FloorId = null;
        ambiguousCollector.Collectors.Single().ServedFloorId = null;
        ambiguousCollector.ValidateContract();
        var ambiguousReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(ambiguousCollector);
        var ambiguousDiagnostics = CircuitAnalyzer.AnalyzeProject(ambiguousCollector);
        Check(ambiguousReadiness.Applicable && !ambiguousReadiness.CrossFloorCollectorDetails.Single().FloorReferencesPass &&
              !ambiguousReadiness.StructuralDispositionPass &&
              ambiguousReadiness.ReasonCodes.Contains("CROSS_FLOOR_REFERENCE_MISSING") &&
              ambiguousReadiness.ReasonCodes.Contains("STRUCTURAL_DISPOSITION_INCOMPLETE") &&
              ambiguousDiagnostics.PhysicalInstallationCompletenessPass == false,
            "A schema 1.1 multi-floor collector with no floor topology escaped the physical installation gate.");

        var invalidNonApplicable = Clone(CompleteSchema11Fixture());
        invalidNonApplicable.Collectors.Clear();
        invalidNonApplicable.Windows.Single(item => item.FloorId == "ATTIC").FloorId = "MISSING-FLOOR";
        var invalidNonApplicableReadiness = CircuitAnalyzer.AnalyzePhysicalInputReadiness(invalidNonApplicable);
        var invalidNonApplicableDiagnostics = CircuitAnalyzer.AnalyzeProject(invalidNonApplicable);
        Check(!invalidNonApplicableReadiness.Applicable &&
              !invalidNonApplicableReadiness.VerifiedArchitectureInputPass &&
              !invalidNonApplicableReadiness.VerifiedInterfloorOpeningInputPass &&
              !invalidNonApplicableReadiness.StructuralDispositionPass &&
              !invalidNonApplicableReadiness.RoutingInputReadinessPass &&
              !invalidNonApplicableReadiness.InstallationInputReadinessPass &&
              !invalidNonApplicableReadiness.RouteOpeningBindingPass &&
              invalidNonApplicableReadiness.ReasonCodes.Contains("SCHEMA_1_1_CONTRACT_INVALID") &&
              invalidNonApplicableDiagnostics.PhysicalInstallationCompletenessPass == false,
            "An invalid non-applicable schema 1.1 project escaped through vacuous physical gates.");
    }

    private static void ValidateOwnerStyleGeneratorRejectsSchema11()
    {
        var project = CompleteSchema11Fixture();
        project.Training.Label = "ACCEPTED";
        Throws<InvalidOperationException>(() => OwnerStyleProposalGenerator.RotateAcceptedExampleCounterClockwise(project),
            "owner-style transform on schema 1.1 physical input");
    }

    private static HomeAuraProject CompleteSchema11Fixture()
    {
        var project = new HomeAuraProject
        {
            SchemaVersion = "1.1",
            CanvasWidthMm = 5000,
            CanvasHeightMm = 5000,
            GridSpacingMm = 100,
            Levels =
            [
                new FloorLevel
                {
                    Id = "FLOOR_1", Name = "Floor 1", Origin = new(0, 0),
                    Outline = Rectangle(0, 0, 5000, 2500), LabelPosition = new(200, 200),
                    SharedDatumId = "DATUM-01", FinishedFloorElevationMmSharedDatum = 170,
                },
                new FloorLevel
                {
                    Id = "ATTIC", Name = "Attic", Origin = new(0, 2500),
                    Outline = Rectangle(0, 2500, 5000, 2500), LabelPosition = new(200, 2700),
                    SharedDatumId = "DATUM-01", FinishedFloorElevationMmSharedDatum = 3170,
                },
            ],
            Walls =
            [
                VerifiedWall("W-FLOOR-1", "FLOOR_1", 1000, 0, 3000),
                VerifiedWall("W-ATTIC", "ATTIC", 3000, 3000, 6000),
            ],
            Windows =
            [
                VerifiedWindow("WIN-FLOOR-1", "FLOOR_1", "W-FLOOR-1", 600, 1000, 1000, 1070),
                VerifiedWindow("WIN-ATTIC", "ATTIC", "W-ATTIC", 600, 1000, 3000, 4070),
            ],
            DoorOpenings =
            [
                VerifiedDoor("DOOR-FLOOR-1", "FLOOR_1", "W-FLOOR-1", 1200, 2000, 1000, 170),
                VerifiedDoor("DOOR-ATTIC", "ATTIC", "W-ATTIC", 1200, 2000, 3000, 3170),
            ],
            FloorBuildUps =
            [
                VerifiedBuildUp("BUILDUP-FLOOR-1", "FLOOR_1", 108),
                VerifiedBuildUp("BUILDUP-ATTIC", "ATTIC", 3108),
            ],
            SharedSpatialDatum = new SharedSpatialDatum
            {
                Id = "DATUM-01",
                CoordinateReferenceDescription = "Verified common as-built coordinate frame",
                HorizontalOriginReference = "CP-FLOOR-1",
                VerticalZeroReference = "Finished floor FLOOR_1 = 0 mm",
                FloorIdsBoundToDatum = ["FLOOR_1", "ATTIC"],
                ControlPoints =
                [
                    new DatumControlPoint
                    {
                        Id = "CP-FLOOR-1", FloorId = "FLOOR_1", PositionMm = new(0, 0, 0),
                        ReferenceDescription = "Surveyed origin on FLOOR_1",
                    },
                    new DatumControlPoint
                    {
                        Id = "CP-ATTIC", FloorId = "ATTIC", PositionMm = new(0, 2500, 3170),
                        ReferenceDescription = "Surveyed ATTIC control point",
                    },
                ],
                PhysicalVerification = Verified("DATUM-01"),
            },
            FloorArchitectureRegistryVerifications =
            [
                CompleteFloorRegistry("FLOOR_1"),
                CompleteFloorRegistry("ATTIC"),
            ],
            InterfloorOpeningRegistryVerifications =
            [
                new InterfloorOpeningRegistryVerification
                {
                    FromFloorId = "FLOOR_1", ToFloorId = "ATTIC", SharedDatumId = "DATUM-01",
                    PopulationComplete = true, PhysicalVerification = Verified("OPENING-REGISTRY"),
                },
            ],
            InterfloorOpenings = [VerifiedRectangularOpening()],
            Collectors =
            [
                new Collector
                {
                    Id = "K-CROSS", Position = new(3000, 1000), FloorId = "FLOOR_1",
                    ServedFloorId = "ATTIC", Ports = 2,
                },
            ],
        };
        project.ValidateContract();
        return project;
    }

    private static WallSegment VerifiedWall(string id, string floorId, int y, int baseElevation, int topElevation) => new()
    {
        Id = id,
        FloorId = floorId,
        Start = new(500, y),
        End = new(2500, y),
        ThicknessMm = 200,
        WallType = "EXTERIOR",
        VerifiedFinishFaceAOutlineMm = [new(500, y - 100), new(2500, y - 100)],
        VerifiedFinishFaceBOutlineMm = [new(500, y + 100), new(2500, y + 100)],
        BaseElevationMmSharedDatum = baseElevation,
        TopElevationMmSharedDatum = topElevation,
        PhysicalVerification = Verified(id),
    };

    private static WindowOpening VerifiedWindow(
        string id, string floorId, string wallId, int fromX, int toX, int y, int sillElevation) => new()
    {
        Id = id,
        FloorId = floorId,
        WallId = wallId,
        Start = new(fromX, y),
        End = new(toX, y),
        SillHeightMm = 900,
        OpeningHeightMm = 1200,
        VerifiedPlanOutlineMm = Rectangle(fromX, y - 100, toX - fromX, 200),
        ClearWidthMm = toX - fromX,
        SillElevationMmSharedDatum = sillElevation,
        PhysicalVerification = Verified(id),
    };

    private static DoorOpening VerifiedDoor(
        string id, string floorId, string wallId, int fromX, int toX, int y, int thresholdElevation) => new()
    {
        Id = id,
        FloorId = floorId,
        WallId = wallId,
        Start = new(fromX, y),
        End = new(toX, y),
        VerifiedPlanOutlineMm = Rectangle(fromX, y - 100, toX - fromX, 200),
        ClearWidthMm = toX - fromX,
        ClearHeightMm = 2100,
        ThresholdDisposition = "FLUSH",
        ThresholdHeightMm = 0,
        ThresholdElevationMmSharedDatum = thresholdElevation,
        PhysicalVerification = Verified(id),
    };

    private static FloorBuildUp VerifiedBuildUp(string id, string floorId, int pipeAxisElevation) => new()
    {
        FloorId = floorId,
        InstalledInsulationMm = 100,
        RemainingHeightMm = 70,
        BuildUpId = id,
        LayerRegistry =
        [
            new FloorLayer { Id = $"{id}-INSULATION", Material = "Insulation", ThicknessMm = 100 },
            new FloorLayer { Id = $"{id}-SCREED", Material = "Screed", ThicknessMm = 70 },
        ],
        TotalBuildUpThicknessMm = 170,
        AllowedPipeAxisElevationMmSharedDatum = pipeAxisElevation,
        AllowedPipeAxisToleranceMm = 2,
        PhysicalVerification = Verified(id),
    };

    private static FloorArchitectureRegistryVerification CompleteFloorRegistry(string floorId) => new()
    {
        FloorId = floorId,
        SharedDatumId = "DATUM-01",
        WallsComplete = true,
        WindowsComplete = true,
        DoorsAndThresholdsComplete = true,
        FloorBuildUpComplete = true,
        AllowedPipeAxisComplete = true,
        PhysicalVerification = Verified($"ARCH-{floorId}"),
    };

    private static InterfloorOpening VerifiedRectangularOpening() => new()
    {
        Id = "OPENING-01",
        OpeningType = "CORE_PENETRATION",
        ShapeType = "RECTANGULAR",
        FromFloorId = "FLOOR_1",
        ToFloorId = "ATTIC",
        SharedDatumId = "DATUM-01",
        FromFloorFace = new InterfloorOpeningFace
        {
            FloorId = "FLOOR_1",
            VerifiedPlanOutlineMm = Rectangle(1000, 1500, 200, 400),
            CenterMmSharedDatum = new Point3Mm(1100, 1700, 2900),
            FaceElevationMinMmSharedDatum = 2899,
            FaceElevationMaxMmSharedDatum = 2901,
        },
        ToFloorFace = new InterfloorOpeningFace
        {
            FloorId = "ATTIC",
            VerifiedPlanOutlineMm = Rectangle(1000, 1500, 200, 400),
            CenterMmSharedDatum = new Point3Mm(1100, 1700, 3100),
            FaceElevationMinMmSharedDatum = 3099,
            FaceElevationMaxMmSharedDatum = 3101,
        },
        ClearDepthMm = 200,
        ClearWidthMm = 200,
        ClearLengthMm = 400,
        ClearBottomElevationMmSharedDatum = 2900,
        ClearTopElevationMmSharedDatum = 3100,
        ClearAxisDefinitionMethod = "FACE_CENTERS",
        PhysicalVerification = Verified("OPENING-01"),
        StructuralDisposition = new StructuralDisposition
        {
            Status = "EXISTING_OPENING_ACCEPTED",
            RecordId = "STRUCT-OPENING-01",
            AuthorityName = "Independent structural engineer",
            AuthorityDocumentId = "STRUCT-DOC-01",
            AuthorityDocumentPaths = ["evidence/STRUCT-DOC-01.pdf"],
            ApprovedClearOutlineMm = Rectangle(1000, 1500, 200, 400),
            ApprovalDate = "2026-08-20",
        },
    };

    private static PhysicalVerification Verified(string owner) => new()
    {
        Status = "INDEPENDENTLY_VERIFIED",
        MeasurementSourceType = "AS_BUILT_SURVEY",
        SourceDocumentId = $"SOURCE-{owner}",
        SourceDocumentPaths = [$"evidence/{owner}.pdf"],
        PhotoEvidencePaths = [$"evidence/{owner}.jpg"],
        MeasuredBy = "Independent surveyor",
        MeasurementDate = "2026-08-20",
        SurveyToleranceMm = 1,
        IndependentVerificationRecordIds = [$"VERIFY-{owner}"],
    };

    private static List<PointMm> Rectangle(int x, int y, int width, int height) =>
    [
        new(x, y),
        new(x + width, y),
        new(x + width, y + height),
        new(x, y + height),
    ];

    private static List<PointMm> Circle(int centerX, int centerY, int radius) =>
    [
        new(centerX + radius, centerY), new(centerX + 71, centerY + 71),
        new(centerX, centerY + radius), new(centerX - 71, centerY + 71),
        new(centerX - radius, centerY), new(centerX - 71, centerY - 71),
        new(centerX, centerY - radius), new(centerX + 71, centerY - 71),
    ];

    private static HomeAuraProject Clone(HomeAuraProject project) => project.DeepClone();

    private static Point3Mm Clone(Point3Mm point) => new(point.X, point.Y, point.Z);

    private static string D185ProjectPath()
    {
        var root = FindRoot();
        return Path.Combine(root, "homeaura-native-editor", "examples", "proposals",
            "HA_TWO_FLOOR_C12_BOUNDED_TERMINAL_185",
            "HomeAura_TwoFloor_C12BoundedTerminal_D185.homeaura.json");
    }

    private static string FindRoot()
    {
        foreach (var start in new[] { AppContext.BaseDirectory, Directory.GetCurrentDirectory() }.Distinct(StringComparer.OrdinalIgnoreCase))
            for (var directory = new DirectoryInfo(start); directory is not null; directory = directory.Parent)
                if (Directory.Exists(Path.Combine(directory.FullName, "homeaura-native-editor")) &&
                    Directory.Exists(Path.Combine(directory.FullName, "homeaura-native-editor-tests")))
                    return directory.FullName;
        throw new DirectoryNotFoundException("HomeAura repository root was not found.");
    }

    private static void AssertArrayItemPropertiesAbsent(JsonElement root, string arrayName, string[] names)
    {
        foreach (var item in root.GetProperty(arrayName).EnumerateArray())
            AssertPropertiesAbsent(item, names, $"legacy {arrayName} item");
    }

    private static void AssertPropertiesAbsent(JsonElement element, IEnumerable<string> names, string owner)
    {
        foreach (var name in names)
            Check(!element.TryGetProperty(name, out _), $"{owner} unexpectedly contains {name}.");
    }

    private static void Throws<TException>(Action action, string label) where TException : Exception
    {
        try { action(); }
        catch (TException) { return; }
        throw new InvalidOperationException($"Expected {typeof(TException).Name}: {label}.");
    }

    private static void Equal<T>(T expected, T actual, string label)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
            throw new InvalidOperationException($"{label}: expected {expected}, actual {actual}.");
    }

    private static void SequenceEqual<T>(IEnumerable<T> expected, IEnumerable<T> actual)
    {
        var expectedArray = expected.ToArray();
        var actualArray = actual.ToArray();
        if (!expectedArray.SequenceEqual(actualArray))
            throw new InvalidOperationException(
                $"Sequence mismatch: expected [{string.Join(", ", expectedArray)}], actual [{string.Join(", ", actualArray)}].");
    }

    private static void Check(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
