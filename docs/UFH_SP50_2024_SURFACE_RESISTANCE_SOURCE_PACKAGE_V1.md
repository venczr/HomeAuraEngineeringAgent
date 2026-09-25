# UFH SP 50.13330.2024 surface resistance source package V1

## Normative identity and extract authority

Rosstandart identifies **SP 50.13330.2024, “Тепловая защита зданий”** as active, approved by Minstroy order 327/пр dated 2024-05-15, effective 2024-06-16, replacing SP 50.13330.2012. The official registry page is the identity/status authority: https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c

The table cells are carried by published copies, not by the Rosstandart metadata page. Table 4 was cross-checked against Garant and the published KMD PDF; Table 6 against Garant and the TN published PDF, with Consultant-hosted/RSO copies as additional checks. These carriers are not labelled as official publishers and the resulting record authority is `PROJECT_APPROVED_NORMATIVE_EXTRACT`. Only the selected structured rows and trace metadata are embedded; the standard itself is not reproduced.

The version-pinned in-code dataset is `SP50_2024_SURFACE_HEAT_TRANSFER_V1`. Its dataset and record digests cover the normalized structured records and provenance envelope. Official status was checked and the extract cross-check recorded on 2026-09-15. No source-file byte digest was available from the browser evidence; the package therefore records URLs and its own normalized extract digests rather than claiming a downloaded-source hash.

## Extracted rows

Table 4, internal winter surface coefficient αв, W/(m²·K):

| Row | Applicability | αв |
|---|---|---:|
| 1 | Walls, floors, smooth ceilings; ribbed ceilings only at h/a ≤ 0.3 | 8.7 |
| 2 | Ribbed ceilings at h/a > 0.3 | 7.6 |
| 3 | Windows | 8.0 |
| 4 | Rooflights | 9.9 |

Table 6, external winter surface coefficient αн, W/(m²·K):

| Row | Applicability | αн |
|---|---|---:|
| 1 | Exterior walls, coverings, overpasses, floors above cold crawlspaces without enclosure walls — Northern construction-climatic zone | 23 |
| 2 | Floors above cold basements communicating with outdoor air, cold crawlspaces with enclosure walls, and cold floors — Northern construction-climatic zone | 17 |
| 3 | Attic floors; floors above unheated basements with wall openings; exterior walls with an outdoor-ventilated air layer | 12 |
| 4 | Floors above unheated basements and technical crawlspaces not ventilated by outdoor air | 6 |

These are row-specific values, not a universal exterior coefficient. Rows 1 and 2 require both explicit Northern-zone confirmation and a source reference/field for that zone classification. Row 3’s ventilated exterior-wall case retains a methodology-scope diagnostic and is not automatically admitted to the homogeneous-layer U calculation. Row 3 attic-floor/basement-opening cases remain distinct. Ground is never mapped to Table 6: `GROUND_BOUNDARY_MODEL_REQUIRED`.

## Resolution and calculation scope

Call `resolve_surface_resistances(SurfaceApplicability(...))` with explicit Table 4 and Table 6 categories. Ribbed ceilings additionally require the actual h/a ratio and the selected high-ratio category. Missing or contradictory applicability fails closed. A coarse `OUTDOOR_AIR` semantic boundary is insufficient to select an external row.

The dataset stores α as the normative primary value. The resolver derives `R_si = 1/α_i` and `R_se = 1/α_e`, preserving the selected row IDs and record digest under `DERIVED_FROM_NORMATIVE_COEFFICIENT`. The resulting `SurfaceResistanceMethod` can be passed to the existing envelope bundle calculation, which evaluates `R_total = R_si + Σ(d/λ) + R_se` and `U = 1/R_total` with Decimal arithmetic.

This U is labelled `HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE`; it is not the full reduced resistance of a nonuniform building envelope. Thermal bridges remain separate. The existing exact explicit-U comparison policy remains unchanged. Windows/rooflights do not gain a glazing-layer U calculation; they still need a supported project/manufacturer/dedicated-method U source.

Changing the selected coefficient row or dataset revision changes the method and assembly dependency digest. Layer changes alter the assembly total/U digest but do not change selected coefficient records. Climate location is not an input to this coefficient resolver.

## Test_01 audit and execution boundary

Test_01 construction-source findings are unchanged: its room export has no authoritative assembly/layer/property/U-value binding, and its prior IFC room source did not establish construction material associations. No SP50 values are assigned to Test_01. Tests use synthetic sourced layers only. No heat loss, sizing, routing, engineering kernel, or shadow validation runs in this block.
