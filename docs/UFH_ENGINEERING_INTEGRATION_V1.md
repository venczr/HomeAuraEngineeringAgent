# UFH_ENGINEERING_INTEGRATION_V1

Opt-in Python integration of existing heat-loss/sizing, actual coverage/routes and
UFH_ENGINEERING_KERNEL_V1. No geometry, routing policy, API or AutoCAD changes.

## Architecture and entry points

    UFHSizingRequest
      -> size_ufh_requirement_and_coverage(request)
         -> existing HeatLossEstimator + existing solve_floor_heating_coverage
         -> (UFHRequirement, FloorHeatingCoveragePlan)
      -> assess_ufh_candidates(sizing, coverage, explicit_inputs)
         -> map_candidates
         -> existing kernel thermal, flow, hydraulics, pressure functions
         -> existing kernel balance_circuits when control is supplied
      -> IntegrationAssessment

`size_ufh_requirement_with_engineering(request, inputs)` provides this entire path
in one opt-in call. It invokes legacy sizing/coverage exactly once and returns
`SizingEngineeringResult(sizing, coverage, engineering)`. There is no retry or
rerouting. Existing `size_ufh_requirement(request)` delegates to the shared function
and returns only its original UFHRequirement, unchanged in shape/content/digest.
No engineering import was added to the sizing module or existing API paths.

`assess_ufh_candidates` also accepts an already computed sizing/coverage pair.
It checks matching project, room, plan ID/digest, route IDs and counts; it does not
generate geometry. These are trusted repository objects, not signed external
artifacts. The digest is deterministic identity, not tamper-proof authentication.

## Actual candidate source and heat allocation

- Identity: `FloorHeatingCoveragePlan.circuit_routes[].id`.
- Length: `CircuitRoute.length_mm`, checked against the actual orthogonal
  polyline length, route validation length and coverage zone generated length.
- Area: matching `FloorHeatingCoverageZone.estimated_coverage_mm2`, by circuit ID.
- Room heat: `UFHRequirement.required_heat_w`, from existing heat-loss/sizing.

The existing planner explicitly labels coverage as a length-times-spacing estimate,
not a geometric union. Its plan status remains `partial`; this does not contradict
valid individual routes or `UFHRequirement.coverage_status == accepted` under the
existing MVP checks. Integration never promotes this estimate to full coverage.

The caller must explicitly select `area_basis=ACKNOWLEDGED_COVERAGE_ESTIMATE`:

    A_j = existing zone estimated_coverage_mm2 / 1000000
    Q_j = Q_room_required * A_j / sum(A_j)
    q_j = kernel.required_heat_flux(Q_j, A_j)

Thus all circuits in the uniform room allocation have the same flux, namely
Q_room/sum(estimated served areas), not Q_room/gross room area unless those areas
coincide. Unequal areas receive unequal heat; no automatic equal division is used.
Allocation preserves the room load within ordinary floating-point tolerance.

Every assessment records `COVERAGE_ESTIMATE_USED_FOR_HEAT_ALLOCATION` and each
candidate records `area_is_estimate=True`. `EXACT_SERVED_AREA_REQUIRED`, missing or
zero areas, unmatched zones or inconsistent totals fail closed with
`CIRCUIT_HEAT_ALLOCATION_UNAVAILABLE`. No exact area is invented and no geometry
algorithm is changed to obtain it.

## Explicit assumptions and kernel calls

`UFHEngineeringIntegrationInputs` requires K_H, surface flux limit, indoor/lower
boundary temperatures, R_o/R_u, temperature mode, sigma OR supply, and c_W.
The existing kernel prescribes 4190 J/(kg K); another supplied c_W is rejected,
not ignored. The wrapper checks indoor/lower temperatures against the heat-loss
request. Callers of the lower-level assessment function must supply the linked
thermal assumptions themselves because UFHRequirement does not retain temperatures.

`common_circuit` explicitly applies the same pipe/fluid/loss inputs to each circuit
in the room: inside diameter, product roughness, density, viscosity, SG, three
embedded loss additions, an explicit fixed-manifold loss tuple, optional manufacturer
pressure limit and optional control characteristic. An empty loss tuple and zero
loss additions must be supplied explicitly. Heterogeneous products per circuit are
not selected or inferred by this V1 interface.

All engineering mathematics calls the existing kernel: `required_heat_flux`,
`solve_thermal`, `design_mass_flow`, `pipe_hydraulics`, `circuit_pressure`,
mass-flow conversions and `balance_circuits`. No LMTD, Formula 13, Churchill,
Darcy, Kv or LOW/HIGH equations are copied into the adapter.

The kernel's top-level `evaluate` requires a control characteristic. Optional-control
integration therefore orchestrates its existing public pure functions directly.
The pressure function consumes only `embedded_losses`, `fixed_manifold_losses` and
`manufacturer_max_circuit_pressure_pa`; CommonCircuitInputs supplies those same
validated attributes. No placeholder valve, fabricated Kv or unvalidated CircuitTask
is constructed. Fixed/control component overlap is rejected when control is given.

Without control, thermal/hydraulic results remain available and balance is `None`,
with `BALANCEABILITY_NOT_EVALUATED_NO_CHARACTERISTIC`. An individual ACCEPTED result
does not certify unassessed balanceability. With control, all accepted branches
are passed together to the existing LOW/HIGH solver, including a single branch.

## Units and result layout

`mm_to_m` is the sole length conversion (1000 mm/m). `mm2_to_m2` is the sole area
conversion (1000000 mm²/m²). Both accept only nonnegative integer geometry values;
candidate length/area must subsequently be positive. Fluid/pipe/thermal engineering
inputs already use SI. Kernel conversions provide kg/s to kg/h and Pa to mbar.

The 80000 mm -> 80.0 m boundary is tested through `pipe_for_route` and the actual
hydraulic function. This isolated unit fixture is not falsely presented as a new
accepted 80-m geometric route; whole-plan admission rejects inconsistent length
evidence. End-to-end fixtures use unmodified routes from the existing planner.

| Required information | Per-circuit output path |
|---|---|
| ID, actual length, estimated served area, allocated heat, flux | `candidate` |
| Supply, return, sigma, root diagnostics | `thermal` |
| Design flow in kg/h | `mass_flow_kg_h` |
| Velocity, Re, Darcy factor, pipe Pa/mbar | `hydraulics` |
| EN circuit pressure, fixed manifold pressure, EN/manufacturer checks | `pressure` |
| Natural branch pressure | `natural_branch_pressure_pa` |
| Thermal/hydraulic/engineering status, recommendation | Explicit status fields |
| Root causes | `diagnostics` |

Room output contains project/room/sizing/coverage identities, policy acceptance,
per-circuit assessments, total design flow, highest natural branch pressure,
optional balance result, overall status, recommendation, diagnostics and SHA-256.
Totals are `None` if any branch lacks the required calculation; partial sums are
not labelled complete design totals. Circuits and digest collections are ordered
deterministically. Digest covers source sizing/coverage content, inputs and result.

## Failure and recommendation semantics

Geometry acceptance and engineering acceptance are independent. Example:
`routing_accepted_legacy_policy=True`,
`engineering_status=REJECTED_CIRCUIT_PRESSURE`, `recommendation=SPLIT_REQUIRED`.
The original pressure diagnostic and per-circuit status remain available.

EN or manufacturer circuit overpressure may warrant splitting/redesign and emits
that recommendation; it does not assert that splitting will solve every fixed loss.
No geometry changes result. A balanceability range conflict is preserved as a
kernel failure, but V1 does not assume that splitting can fix that characteristic.
Published/recommended domain failures retain their kernel source semantics.

Thermal rejection takes priority. Surface failure does not trigger hydraulic
optimization or a split-only remedy. No thermal failure is overwritten by hydraulic
success. Existing sizing coverage failure also cannot be promoted into overall
ACCEPTED. Invalid candidate linkage/geometry evidence fails closed before engineering.

## Verified integration cases

Synthetic engineering properties are explicit test inputs, not product defaults.
The common test control interval is Kv=[0.1,1.5], SG=1.0, rho=990.22, mu=0.000594,
ID=0.012 m, epsilon=0. Surface limits and sigma are explicitly varied.

| Case | Actual route length(s) | Outcome |
|---|---|---|
| One circuit, sigma=5 K | 44.1 m | Routing/sizing accepted; engineering ACCEPTED |
| Same candidate, sigma=0.5 K | 44.1 m | Routing unchanged; EN pressure failure; SPLIT_REQUIRED |
| Same candidate, surface maximum=40 W/m² | 44.1 m | Surface rejection; no split recommendation |
| Two unequal-area circuits, sigma=5 K | 42.5 / 41.7 m | Accepted; LOW/HIGH overlap |

One-circuit load=421 W, estimated area=7.47 m², design flow=95.868258 kg/h,
natural/embedded pressure=3957.696718 Pa. At sigma=0.5 K the design flow becomes
958.682578 kg/h and pressure=216171.646238 Pa, without changing a route vertex.
Surface failure is 421/7.47=56.358768 W/m² > explicit limit 40 W/m².

Two-circuit areas=7.23/7.17 m², heat allocations=362.002083/358.997917 W,
flows=83.958591/83.261839 kg/h, total=167.220430 kg/h. Natural pressures are
3047.801148/2948.644684 Pa. Kernel feasible manifold interval is
[3367.311088,73650.141653] Pa. This is not pump selection.

Required acceptance commands (existing repository .venv):

    python -m pytest -q tests/test_ufh_candidate_adapter.py
    python -m pytest -q tests/test_ufh_engineering_integration.py
    python -m pytest -q tests/test_ufh_engineering_kernel.py
    python -m pytest -q tests -k floor_heating

Results: 24 passed, 11 passed, 46 passed, 100 passed respectively. Tests additionally
check unequal allocation, one routing invocation, byte-stable legacy outputs,
optional control, manufacturer separation, manifold rejection diagnostics, missing
inputs, invalid candidate identities/areas, unit conversion and no input mutation.
Bytecode/cache writes disabled via PYTHONDONTWRITEBYTECODE=1 and
PYTEST_ADDOPTS=-p no:cacheprovider. No unrelated remediation.

## Protected boundary and next block

Before implementation, SHA-256 was recorded for 224 existing source/test/doc files
including floor-heating, kernel, project/domain and AutoCAD source. Only the
authorized sizing module changes: its existing body now exposes the computed plan
through an additional function, while the old function returns the original result.
No existing output model was changed. New files are this document, the adapter
and its two test files. Final comparison: 223 existing files unchanged, exactly
one authorized existing file changed, and exactly four allowed files created.
Sizing SHA-256 before: `7e4015866c1297a9f0242abc723172d8c2860fe36c6b566fa4466349deff6623`;
after: `f1277bb71c154dbaf2c0d26d19ba229bc1f101490ba6c8a118dfadfd15c1fafe`.

Selected protected preflight SHA-256 values (unchanged after implementation):

| File | SHA-256 |
|---|---|
| agent/floor_heating_engine.py | 19d46ef12170645524d0792fa0eed23a50e88915a18d20cfb5149de1c2005326 |
| agent/floor_heating_coverage.py | 30499e8a94a249cebbd308a2297b03be23b17a3413db301b490747dd3aca1452 |
| agent/floor_heating_models.py | 836b326b7afabd2afe87acff93f7fefc4df2502222edcc174a6b7d6eca3b021e |
| agent/ufh_engineering_kernel.py | 56c3d342202005f1948c098d03af0cef61d3075ee59993940a95f5923eb346c2 |
| agent/ufh_engineering_models.py | 4c7e0aeb4efb411e67a97f89fed521a5e2deb327eeb9aff161bee8110fe2dfa4 |
| agent/project_models.py | a38a10d0ee469bcece5a5a3b01c71e71ec076e789ad3389b28af4ca0985965aa |
| agent/domain_models.py | efc0b3e5ed54c8a2e2d90bbd59c9405f4fe2b19c26d48519da97747f7afe28b2 |

The existing 40000–80000 mm check remains **LEGACY_MVP_ROUTING_POLICY**, not a
universal physical pipe-length limit. Integration does not expand router acceptance
to 100+ m. Geometry algorithms, collector placement, clipping, C#/AutoCAD/DWG,
project/domain contracts, services, credentials, provider calls and Git history
are untouched. No commits/push. No automatic diameter, pump, mixing-unit or catalog
selection, real curve interpolation, geometry splitting or retry loop.

Next recommended bounded block: **UFH_AUTOMATIC_SPLIT_AND_RETRY_V1**.
It would consume recommendations as explicit feedback after separate authorization.
It is not implemented here; published-domain or thermal surface failures must not
be treated as unconditional instructions to split.
