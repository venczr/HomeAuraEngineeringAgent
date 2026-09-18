# UFH layout engineering basis

This record separates published manufacturer guidance from HomeAura preview policy. It is a layout basis for review, not a construction approval.

| SOURCE | RULE | SCOPE | AUTHORITY | HOW HOMEAURA USES IT |
|---|---|---|---|---|
| Uponor, *Radiant Floor Heating Installation Handbook* (official handbook link recorded in `reports/HomeAura_D163_layout_and_editor_2026-08-14.md`) | Locate the manifold where it remains accessible for service; connect loops to supply and return headers. | Manifold installation | MANUFACTURER_SPECIFIC_RULE | Model one accessible manifold station and unique supply/return ports; exact mounting wall remains source-dependent. |
| Uponor Vario S FM official product/manual record (`manufacturer-data/uponor_vario_s_fm_14_design_reference.json`) | Vario S FM is offered in 2–16 circuit sizes; loop connections use G3/4 Eurocone and the documented loop pitch is 50 mm. | Manifold product geometry | MANUFACTURER_SPECIFIC_RULE | Use module capacity and 50 mm port pitch only as a parameterized preview reference; never infer hydraulic approval. |
| Wavin / Uponor / REHAU installation guidance (manufacturer practice, cross-checked against the owner routing manual) | Bifilar/spiral layouts are suitable for regular areas; meander layouts remain useful for narrow or irregular areas. | Pattern selection | MANUFACTURER_SPECIFIC_RULE | AUTO evaluates spiral, meander, and hybrid candidates from geometry. It records the selected reason and does not claim thermal superiority. |
| HomeAura owner routing manual, sections 3, 5, 7, 10–13 (`reports/HomeAura_owner_floor_heating_routing_rules_for_all_helpers_2026-08-20.md`) | BODY is coverage; TRANSIT is connection only. No diagonal wall crossing; wall crossing requires a verified opening. Use explicit R80 bends, 16x2 mm pipe, 100/200 mm grid and 40–80 m project review band. | Current project geometry and review gates | PROJECT_POLICY | Enforce independent containment, explicit transit roles, bend/spacing metadata, and honest unresolved authority states. |
| HomeAura source-authority report (`reports/HomeAura_semantic_topology_boundary_evidence_2026-09-17.md` and related drawing reports) | Unknown openings and corridor paths are not construction-authorized. | Test_01 source model | PROJECT_POLICY | Generate preview paths only through explicit preview penetrations and mark them `REQUIRES_INSTALLER_CONFIRMATION`. |
| EN 1264 / manufacturer design practice | Circuit length depends on pipe diameter, spacing, flow, temperature drop, pressure loss and system design; no universal length is valid without those inputs. | Circuit sizing | AUTHORITATIVE_SOURCE_RULE | Expose `MAX_TOTAL_CIRCUIT_LENGTH_M` as configurable preview policy. Test_01 uses 90 m only as `PREVIEW_NON_AUTHORITATIVE_POLICY`. |
| Manufacturer installation guidance and owner manual | Transit pipes can affect adjacent floor temperature; insulation/protection is selected from project construction and manufacturer data. | Corridors and tails | MANUFACTURER_SPECIFIC_RULE | Track transit thermal effect as unresolved, distinguish insulated transit from BODY, and flag dense corridor bundles for review. |

## Explicit preview assumptions

- Default preview pipe: 16x2 mm; minimum bend radius: 80 mm; wall offset: 100 mm; field spacing: 200 mm. These values are project preview assumptions unless a source-authorized project profile overrides them.
- `MAX_TOTAL_CIRCUIT_LENGTH_M=90` is a resplitting trigger only. It is not a hydraulic compliance claim.
- A strategy is selected on geometry and installation proxies only. No room-level thermal score is produced until authoritative heat-loss inputs exist.
- Manifold and riser coordinates remain `MANIFOLD_GEOMETRY_PREVIEW` / `RISER_POSITION_PREVIEW` until source geometry or installer confirmation authorizes them.
