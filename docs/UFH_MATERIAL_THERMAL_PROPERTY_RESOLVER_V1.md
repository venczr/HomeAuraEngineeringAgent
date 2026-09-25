# UFH material thermal-property resolver V1

## Scope and normative ownership

This is a version-pinned, deliberately partial source package and resolver. SP 50.13330.2024 is active, approved by Minstroy order 327/pr dated 2024-05-15 and effective 2024-06-16. Its clause 5.4 routes design conductivity for insulation to SP 345.1325800.2017 Appendix D, while other materials use SP 50 Appendix M. The official Rosstandart records establish document identity/status, not extracted cell values: [SP 50 record](https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c), [SP 345 record](https://protect.gost.ru/sp/details/c020552a-f741-47c3-a588-491af35f8b88).

Table M.1 is treated as 246 numbered rows; this package carries 13 selected rows (5.28%). The structured values are `PROJECT_APPROVED_NORMATIVE_EXTRACT`, not `NORMATIVE_AUTHORITATIVE`: the Rosstandart metadata is the identity authority, while published text copies are carriers for the exact table cells. Row values for the included gypsum, concrete and mortar records were checked against independent published copies; insulation rows are retained for exact identity/context only and cannot yield a design lambda through this SP 50 provider. The source URLs and row references are stored with each record. The full standard is not copied.

## Insulation and SP 345 boundary

SP 345 Appendix D defines the A/B conductivity method for insulation using dry conductivity, quality factor and A/B moisture; Appendix E covers construction-dependent operating-condition coefficients. Current amendment text still points moisture values back to Appendix T of SP 50.13330.2012, so migration/current applicability of that dependency needs a separately approved resolution. SP 50 clause 5.4 also applies an insulation-layer operating coefficient in the envelope resistance calculation. V1 therefore returns `SP345_SOURCE_REQUIRED` for Table M.1 insulation rows and never treats their Table M.1 lambda columns as the production design lambda. No Appendix D/E coefficient calculation or insulation-layer resistance is claimed here. References: [SP 345 consolidated text](https://meganorm.ru/mega_doc/norm/metodika/0/sp_345_1325800_2017_svod_pravil_zdaniya_zhilye_i.html), [Change 1](https://protect.gost.ru/sp/changesdetails/a4b65c2b-82c0-40cf-a463-083c0561be01), [Change 2](https://protect.gost.ru/sp/changesdetails/cbf2eee3-4a10-4f6e-9977-69f335e914fd). The older Appendix T references are a limitation/blocker, not silently migrated data.

## Typed behavior

`MaterialThermalPropertyRecord` preserves row number, exact source description, density discriminator, dry `lambda_0`, moisture and `lambda_A`/`lambda_B` separately, route, authority, source references and deterministic row digest. Density variants remain distinct. Matching accepts an exact row ID, a family label, or registered exact aliases; ambiguous labels return candidate IDs, never a guessed row. There is no fuzzy matching or nearest-density rule.

`MaterialResolutionRequest.operating_condition` is explicit A/B/UNRESOLVED and records its provenance. Identifying a non-insulation row with unresolved A/B returns `RECORD_RESOLVED` plus `OPERATING_CONDITION_REQUIRED`; it does not set `design_lambda_w_mk`. Selecting A or B without condition provenance also fails closed. There is no dry-lambda fallback, A/B average, or safety-side selection. A resolved layer is created only from a `RESOLVED` result and carries the record ID, condition, property provenance and dependency digest.

Explicit project/manufacturer/normative property claims require a matching source/authority class, positive lambda, canonical/equivalent units and source references. Conflicting claims return `SOURCE_VALUE_CONFLICT`. Test-only claims/conditions cannot pass through the production envelope handoff.

The existing envelope submission path accepts per-layer `material_query` inside the structured construction decision. It resolves properties, then uses the existing `ConstructionLayer`, `calculate_bundle`, SP 50 surface-resistance resolver and normal `ResolverResult` authoring handoff. Resolver enrichment deep-copies the submitted decision so its dependency digest remains valid. It computes the existing homogeneous-section conditional resistance only where applicable; it is not full reduced envelope resistance and leaves thermal bridges separate. No room heat-loss or UFH generation path is called.

## Test_01 source audit

The checked production-derived source `projects/Test_01/exports/rooms/rooms.json` contains room identity, geometry/areas, temperatures/airflows and existing heat-loss observations, but no material layers, material/product IDs, density, lambda or construction U-values. Test-only and visualization exports are not material-property sources. No materials were inferred from thickness, appearance, name or geometry; no Test_01 file was edited and no Test_01 heat-loss, sizing, routing or shadow calculation was run.

## Limits / next dependency

Production-ready coverage is the 13 exact selected rows only. In particular, insulation remains unresolved until a revision/current-applicability-verified SP 345 source package and its A/B/operating-coefficient dependencies are implemented. `RU_CURRENT` is not used to silently choose a material row or A/B condition. The next bounded block should be `UFH_SP345_INSULATION_PROPERTY_SOURCE_AND_OPERATING_COEFFICIENT_RESOLVER_V1`, including explicit resolution of the amended Appendix D/E and legacy Appendix T references before any insulation lambda is bound.
