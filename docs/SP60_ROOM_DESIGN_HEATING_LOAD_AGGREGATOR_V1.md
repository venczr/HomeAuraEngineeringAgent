# SP60 Room Design Heating Load Aggregator V1

## Normative identity

`agent/sp60_normative_method.py` is the single canonical SP 60.13330.2020 revision identity shared by the transmission method, ventilation/infiltration method and room A.1 aggregator. It records separately: base approval (2020-12-30), base effective date (2021-07-01), Amendment 6 approval (2026-05-26), Rosstandart registration (2026-06-15), official publication (2026-07-07), and effective date (2026-07-07). The last two agree with the order's publication-triggered entry rule. The consolidated text marker (2026-05-26) is not an effective date.

Rosstandart provides normative identity/status metadata. The current consolidated text carrier is used only for formula text/equation evidence, not represented as the official publisher.

## Formula A.1 and scope

The visually checked A.1 equation (equation image SHA-256 `9e5c640d05e33251943b2e55ed8769a4f10346822e2d71370a20b91f3dc71151`) is:

`Q_ов^p = Σ_n (Q_tr,n + Q_vent,n + Q_inf,n + Q_mts,n)`.

Thus the A.1 component set is exactly transmission, required ventilation-air heating, infiltration-air heating, and warming materials/equipment/vehicles brought into the room. The current equation and its definitions do not contain `Q_byt` (internal heat gains), so no gains are silently subtracted and no extra gains classification is needed to close A.1.

`Q_mts` is the heat required to warm materials, equipment and vehicles brought into the room, under SP60 A.6 (formula A.11). The source text describes incoming temperature treatment, mass, specific heat and first-hour absorption factors. This block does not calculate that industrial/process-specific term. It remains an explicit typed decision: a resolved value carries value provenance; `NOT_APPLICABLE` carries applicability provenance and an identified room/process scope; unknown/applicable-but-unresolved states block the total. There is no blanket residential zero or blanket “all residential rooms are not applicable” rule.

## Aggregation and UFH handoff

`aggregate_sp60_room_design_heating_load` composes the already calculated Q components only. It requires `COMPLETE_DETAILED` transmission, resolved ventilation and infiltration (including sourced design-pressurization suppression semantics), and resolved or explicitly not-applicable Q_mts. The Decimal total is emitted only when complete. Component result digests and canonical normative revision digest enter the result digest.

The A.1 arithmetic preserves the signed values produced by the component formulas; it never applies `abs()`. Positive total means heating demand, while a negative transmission component can represent heat transfer from a warmer adjacent zone. A complete non-positive total is still retained as an SP60 result but cannot be handed off as a positive UFH design load.

`build_ufh_design_heat_load_input` accepts only a complete positive SP60 result and emits a provenance-bearing `design_heat_load_w` for the existing `ThermalTask.required_heat_w` slot. `bind_design_heat_load_to_thermal_task` changes only that field on a supplied typed task context and does not invoke sizing, the kernel, coverage, routing, or retry. Legacy `UFHSizingRequest` still runs its own legacy heat-loss estimator; this block does not substitute the new SP60 result into that estimator or change its equations.

No Test_01 heat-loss result is calculated here. Test_01 readiness remains based on prior source/profile diagnostics: geometry/identity were previously bound, while envelope assemblies, opposite-side conditions, outdoor design locality, ventilation design airflow, infiltration inputs, and Q_mts applicability remain unproven. No synthetic input is persisted.
