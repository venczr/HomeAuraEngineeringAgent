# Ventilation and infiltration heat-loss V1

This module adds pure in-memory SP 60.13330.2020 air heat-loss components. It does not call sizing, UFH routing, or any UFH kernel. Formula and source-carrier digests are embedded in `agent/ventilation_infiltration_heat_loss.py`.

## Normative method package

The SP60 date identity is now shared from `agent/sp60_normative_method.py`. Amendment 6 was approved 2026-05-26, registered 2026-06-15, officially published 2026-07-07, and effective 2026-07-07. Rosstandart records these as distinct events; its page also states the order's rule “from date of publication”. The previous 2026-07-13 date in this document was incorrect. The consolidated text revision marker remains 2026-05-26 and is not conflated with the effective date. Rosstandart is the source for identity/status; MegaNorm is only a published text carrier.

Current consolidated SP 60 A.1 is visually verified as `Q^p = Σ_n(Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)`, with the checked formula image SHA-256 `9e5c640d05e33251943b2e55ed8769a4f10346822e2d71370a20b91f3dc71151`. Its explanatory text defines those same four terms. `Q_byt` is not an A.1 term (neither additive nor subtractive); no separate internal-gain “classification” is required to close the A.1 component set. The A.6 `Q_mts` term remains required or must be explicitly classified not applicable for a provenance-backed room/process scope; unknown applicability blocks completion.

## Ventilation

`RequiredVentilationAirflow` accepts one explicit source mode: direct project design airflow; normative cold-period design air-change rate plus authoritative volume; per-person requirement plus occupancy; or a sourced SP 60 7.4.1 calculation result. A generic project `AirExchangeRate` stays an audit-only observation and cannot be passed as normative design ACH without the required semantics and provenance. A.5 calculates the heating demand using the A.6 density method; no generic 1.2 kg/m³ value is used. Provenanced pressurization make-up airflow is added to the required airflow.

## Infiltration

Infiltration is a distinct A.7/A.8/A.9/A.10 path. Each element needs sourced area and air-permeability resistance; openings do not borrow thermal U-values. Windows/translucent elements use the source-pinned 2/3 exponent and entrance doors/gates/openings use 1/2. Other element categories require an explicit sourced exponent. The A.9/A.10 path requires design wind, building height, element height, height coefficient, aerodynamic model and a complete air-permeable inventory. Missing inputs yield typed `INCOMPLETE` results. The 0.8/−0.6 pair is available only for a sourced rectangular-building classification; other geometry requires an SP 20 aerodynamic model.

Balanced supply/exhaust uses the SP 60 permitted omission of `P_v`. Design-maintained positive pressure suppresses the infiltration term only with explicit make-up airflow provenance; that make-up remains included in `Q_vent`. No ACH infiltration shortcut exists. The current implementation models inward design infiltration; non-positive element pressure yields no inward mass flow, not an exfiltration heat-loss calculation.

## Aggregation and scope

`aggregate_sp60_a1_components` reports the known component subtotal separately from the complete A.1 total. `Q_mts` must be sourced or explicitly not applicable. The existing transmission result must be complete-detailed. Ventilation/infiltration remain unresolved until their own required sources are available. The Test_01 adapter bridge is in-memory only and preserves its room `AirExchangeRate` as unclassified; project file access remains outside the calculation functions.

This block does not implement transmission, room-heat-loss orchestration, material/equipment warming, wind climate data, SP 20 general aerodynamics, or real Test_01 air calculations. Test_01 receives a readiness audit only.

## References

- [Official Rosstandart document identity record](https://protect.gost.ru/sp/details/b00f766e-b861-4cc7-a448-c65906490262)
- [Official Rosstandart Amendment 6 record](https://protect.gost.ru/sp/changesdetails/25d65837-dfb6-408b-948f-e7f254851ded)
- [Consolidated SP 60 text carrier (not the official publisher)](https://meganorm.ru/mega_doc/norm_update_01082026/metodika/0/sp_60_13330_2020_svod_pravil_otoplenie_ventilyatsiya_i.html)
