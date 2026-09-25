# Building Heat Loss Core V1 — SP 60 transmission only

## Scope

`agent.building_heat_loss.calculate_room_transmission` is a pure Decimal
calculation over already-resolved, provenance-bearing inputs. It performs no
file access, project discovery, questionnaire work, climate lookup, UFH sizing,
routing, or engineering-kernel calls.

V1 returns `room_transmission_heat_loss_w`; this is not a complete room design
heating load. Ventilation, infiltration, warming of introduced materials and
equipment, and internal gains are separately marked not evaluated. The total
design heating load remains unresolved.

## Normative method identity

The method identity is SP 60.13330.2020, consolidated Amendments 1–6. The
official Rosstandart card for Amendment 6 records order 327/pr of 26 May 2026,
registration on 15 June 2026, and effective date 7 July 2026. Amendment 6
updates the climate reference to SP 131.13330.2025. The consolidated text was
checked for the Appendix A transmission method and internal-partition rule.

The narrow in-code method package records formula identities, units and source
references, not copyrighted standard text. Official document status comes from
Rosstandart. The consolidated text and its formula images are used as text
carriers, not represented as official-publisher copies.

- [Rosstandart: SP 60.13330.2020 Amendment 6](https://protect.gost.ru/sp/changesdetails/25d65837-dfb6-408b-948f-e7f254851ded)
- [SP 60.13330.2020 consolidated text, Appendix A.2–A.4](https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html)
- [A.2 formula image](https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_428224.png)
- [A.3 formula image](https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_681437.png)
- [A.4 formula image](https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i_/meganorm_746667.png)

Formula A.2 is `Q_tr,n = (t_v - t_n) * Σ(A_i * K_i)`, with
`K_i = 1 / R0_i_reduced`. Formula A.3 is
`Q_tr,n = (t_v - t_n) * [Σ(A_i * U_i) + Σ(L_j * ψ_j) + Σ(N_k * χ_k)]`.
The coefficient in A.2 is the heat-transfer coefficient `K_i`; no orientation
or exposure multiplier is added by this core. `U_i` is only the homogeneous
part of a fragment. `ψ` and `χ` remain explicit bridge terms.

## Input and method boundaries

Every boundary must identify its project/room linkage, geometric source and
digest. Area is accepted only with source provenance and normalized to 0.01 m²
using decimal half-up rounding, reflecting A.2 note 2. Construction U and each
design temperature likewise require paired provenance. No area, U-value,
temperature, thermal-bridge coefficient, or correction factor is supplied by a
software fallback.

For A.2, every opaque fragment and opening requires explicit role
`REDUCED_FRAGMENT`; the existing envelope resolver's
`HOMOGENEOUS_SECTION_CONDITIONAL_RESISTANCE` is not promoted to a reduced U.
`PLANAR_TRANSMISSION_ONLY` computes sourced planar `U*A*ΔT` terms, corresponding
to the planar part of A.3, and declares omitted bridge terms. `DETAILED_TRANSMISSION`
uses formula A.3 and requires a provenance-bearing complete bridge inventory;
an explicitly complete inventory with no bridges means zero listed ψ/χ terms.
Any room-level total in either mode also requires an explicit, provenance-bearing
complete boundary inventory. With an unresolved inventory, supplied boundaries
may produce a scoped subtotal, but the room transmission total is withheld.

Heat flow is signed: `ΔT = T_inside - T_opposite`. A warmer adjacent zone can
produce a negative value. For an internal partition, SP 60 A.2 note 1 says to
calculate transmission only when the absolute zone temperature difference is
greater than 4 °C. At 4 °C or below this core retains the boundary result and
marks it omitted under `SP60_INTERNAL_PARTITION_OMISSION_RULE`; it does not
delete the boundary from project data.

Ground-coupled boundaries never use ordinary `U*A*ΔT`; they return
`GROUND_HEAT_LOSS_MODEL_REQUIRED`. Unheated adjacent spaces, ventilated voids,
and other semantic categories need an explicit opposite-side temperature or a
future applicable method. Outdoor temperature may be supplied only as a
resolved climate result. ACH is deliberately absent from the input contract.

## Openings and no-double-counting

An opaque parent boundary carries gross area. Each window/door/other opening is
a distinct child fragment with its own sourced area and U-value. The core
subtracts the rounded opening areas from the opaque parent's area, then counts
each opening's own `U*A*ΔT` contribution once. Duplicate IDs, missing parents,
opening area above gross area, or negative net area fail closed.

## Application adapter

`ProjectTransmissionSource` and `build_building_heat_loss_input` accept
already-resolved in-memory values only. They bind the project's indoor design
temperature where sourced and the SP131 climate-resolver result only to outdoor
boundaries. They do not promote `OutdoorTemperatureC`, supply-air temperature,
heat-loss exports, or ACH. A project adapter must first provide each boundary's
authoritative area/construction and geometry references; a room polygon alone
does not establish wall areas or construction U-values.

## Result semantics

`PLANAR_ONLY` is a transmission-only subtotal. It does not claim
`COMPLETE_ROOM_HEAT_LOSS`. Detailed mode may return `COMPLETE_DETAILED` only for
the A.3 terms represented in its input and complete sourced bridge and
room-boundary inventories.
Ground or missing boundary inputs suppress the room total. Ventilation,
infiltration and internal gains are never mixed into transmission; the total
design heating load remains `None`.

## Test-only fixtures

Regression fixtures use `test_only` provenance and never load Test_01 values or
persist project changes. Test_01 is readiness-audited separately; no real room
heat-loss, UFH sizing, routing, retry or shadow-validation operation is part of
this block.
