# UFH Envelope Construction Resolver V1

## Scope

This block records sourced envelope assemblies in the existing questionnaire → resolver → authoring flow. It separates room geometry, the semantic boundary condition, the physical assembly, sourced material properties, and calculated resistance/U-value. It does not run room heat-loss, UFH sizing, routing, hydraulics, or shadow validation.

The authoring target is `envelope_constructions.selected`. It is an authoring record, not a numeric thermal boundary or a claim that the room heat-loss profile is complete. Existing boundary-condition semantics remain separate. Numeric wall/floor/ceiling U-value fields stay unresolved unless a supported, provenance-bearing U-value is supplied.

## Inputs and source policy

The existing `envelope` question is reused with source/method choices: `PROJECT_ASSEMBLY`, `CATALOG_SYSTEM`, `LAYERED_CUSTOM_ASSEMBLY`, `EXPLICIT_U_VALUE_WITH_PROVENANCE`, and `UNKNOWN`. The existing conditional `envelope.source` question now accepts a typed object. For a layered assembly it carries ordered records with assembly ID, boundary kind, material/product ID, canonical thickness in metres, optional conductivity in `W/(m*K)`, and field-level provenance.

Project assembly and catalog selection do not manufacture a record: until a project assembly adapter/catalog is available, they return `SOURCE_UNAVAILABLE`. `UNKNOWN` remains unresolved. Windows and doors accept directly sourced project/manufacturer U-values only; V1 rejects generic glazing-layer inference. A missing λ remains missing even when a material name is known.

Each physical λ or explicit U requires provenance with source reference, source field, units, transformation, and source/confirmation metadata. Test-only sources are rejected by the production resolver handoff. The envelope decision itself is recorded as a user-confirmed decision; per-property provenance remains inside the serialized typed assembly bundle.

## Calculations

For an opaque layered assembly with all positive, sourced layer properties, V1 calculates using `Decimal`:

`R_layers = Σ(thickness_m / lambda_w_mk)`

If a valid, provenance-bearing surface-resistance method is supplied, it can additionally calculate `R_total = R_si + R_layers + R_se` and `U = 1 / R_total`. No surface values or method are bundled as defaults. With no method, the result retains `R_layers`, leaves `R_total` and `U` null, and reports `NORMATIVE_SURFACE_RESISTANCE_SOURCE_REQUIRED`.

An explicit U-value is accepted only with provenance. If an explicit and calculated U are both available, V1 uses declared software comparison policy `EXACT_DECIMAL_MATCH_V1` (zero tolerance): equality passes; any disagreement returns `SOURCE_VALUE_CONFLICT`, with no chosen U. A later project-approved comparison tolerance must be separately versioned; it is not inferred here.

Thermal bridges are never folded into U; external opaque assemblies retain `THERMAL_BRIDGES_REMAIN_SEPARATE`. Ground-coupled heat transfer, adjacent-zone ΔT and whole-room transmission are outside this module.

## Normative source audit

The official Rosstandart registry currently marks `SP 50.13330.2024, Тепловая защита зданий` as active, approved by Ministry of Construction order `327/пр` dated `2024-05-15`, effective `2024-06-16`, replacing `SP 50.13330.2012` ([official Rosstandart record](https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c)). A published copy identifies internal surface coefficients in Table 4 and external surface coefficients in Table 6 ([published text extract](https://nav.tn.ru/cloud/iblock/290/290dfb2330a62dde8969a39056b6e1fe/SP_50.13330.2024.pdf)).

This validates document identity/status and locates the relevant methodology, but the repository contains no approved, revision-pinned structured extract/source package for the required assembly-specific surface-resistance method. Consequently no SP values are embedded or used for production binding. Layer resistance is still useful and available; total resistance/U reports `NORMATIVE_SOURCE_REQUIRED`. The cited published copy is a text carrier, not itself designated an official publisher.

## Test_01 source audit

`projects/Test_01/exports/rooms/rooms.json` and its history provide room extraction values/identity, but no assembly layer records, λ, certified U, construction type binding, or opening thermal values. The companion IFC room export contains the room-space geometry path; inspection found no `IfcMaterial`, `IfcRelAssociatesMaterial`, material property sets, `IfcWall`, `IfcSlab`, `IfcRoof`, `IfcWindow` or `IfcDoor` source records. No visualization route/export is treated as a construction authority. Therefore Test_01 gains no construction values and remains incomplete.

## Dependency and invalidation

The construction request depends on the `envelope` method choice, structured source answer, project revision and normative profile. It excludes climate and boundary semantic answers: changing climate does not invalidate assembly R/U; changing a boundary category does not invalidate an unchanged assembly. Layer thickness/property provenance changes the assembly digest. A changed normative profile changes the resolver request dependency digest. Source revisions are carried by the source question and physical-property provenance.

`BELOW`/`ABOVE` semantic boundary resolution remains independent. Knowing a wall/slab assembly does not complete its adjacent temperature difference; knowing `GROUND` does not make `U × (Ti − To)` a ground-loss model.

## Validation

Tests use clearly synthetic, in-memory assemblies and do not write Test_01 files. They cover layer resistance, missing λ, missing surface method, explicit U provenance, conflict behavior, opening rejection, ground separation, thermal-bridge separation, digest invalidation, authoring handoff, and incomplete-profile status. No heat-loss or UFH calculation is invoked.
