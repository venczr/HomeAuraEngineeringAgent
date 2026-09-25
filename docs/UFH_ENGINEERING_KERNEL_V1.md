# UFH_ENGINEERING_KERNEL_V1

Isolated deterministic engineering kernel. No router, sizing, API or CAD integration.
The write boundary is exactly the two `agent/ufh_engineering_*.py` modules, their
focused test file and this document. No new dependency, network, randomness or I/O
inside the kernel.

## Preflight and conventions

Read `agent/floor_heating_sizing.py`, `agent/floor_heating_models.py`,
`agent/floor_heating_engine.py`, `agent/floor_heating_coverage.py` and their focused
model/sizing/engine/coverage tests. Existing models derive from `StrictProjectModel`
(Pydantic v2, extra fields forbidden, strict types, finite-number and strict JSON
validation). The new models reuse that base read-only, add `frozen=True`, and use
tuples for immutable collections. No project/domain contract is modified.

Existing sizing uses Decimal and ROUND_HALF_UP for integer watts, ROUND_CEILING
for area allocation. This separate kernel deliberately retains unrounded floats
for transcendental calculations; presentation rounding must not feed back into
engineering comparisons. Diagnostics use stable codes with separate messages.
The SHA-256 digest follows the existing sorted-key, compact UTF-8 JSON convention,
with `allow_nan=False`, and covers the entire request and calculated result except
the digest itself. Circuits are sorted by ID; interval ties select the first ID.
Same inputs/runtime produce identical results. Bitwise identity across different
platform math libraries is not promised.

## Public interface and units

`evaluate(EngineeringRequest)` handles one or more `CircuitTask` candidates.
Each requires explicit thermal task, fluid properties, pipe, embedded extra losses,
fixed manifold losses (possibly an explicitly empty tuple), and a control
characteristic with a declared Kv interval. Lower-level pure functions support
independent thermal, hydraulic and interval calculations.

| Quantity | Internal/input unit | Presentation/conversion |
|---|---|---|
| Pipe length, inside diameter, roughness | m | No implicit mm conversion |
| Heated area | m² | No implicit mm² conversion |
| Temperatures | °C | Differences in K |
| Heat/output coefficient | W; W/(m² K) | Flux W/m² |
| Thermal resistance | m² K/W | Explicit R_o, R_u |
| Mass flow | kg/s | `kg_s_to_kg_h`, `kg_h_to_kg_s`, 3600 s/h |
| Density, dynamic viscosity | kg/m³; Pa s | Explicit, no production defaults |
| Pressure | Pa | `pa_to_mbar`, `mbar_to_pa`, 100 Pa/mbar |
| Kv | m³/h at 1 bar and SG=1 | 100000 Pa/bar inside Kv functions |
| Specific gravity | Dimensionless | Explicit and independent of density |
| Specific heat | J/(kg K) | Formula 13 constant c_W=4190 prescribed for V1 |

`PipeCandidate.length_m` is the total actual candidate length, including heating
pipe and both transits. Darcy friction acts once over this entire length. Additional
bend/fitting losses are incremental losses, not another equivalent length counted
twice. Pipe product roughness is required; explicitly providing zero is a smooth
pipe declaration, not a silent fallback. A diameter is the inside diameter.

## Mathematics

1. `required_heat_flux`: q=Q/A. Strictly positive heat, area and K_H.
2. `solve_thermal`: reject q above the explicit surface limit before other solves.
   Required LMTD=q/K_H. `lmtd` uses (V-R)/ln((V-i)/(R-i)), not an arithmetic mean.
3. Return mode requires i < R < V and 0 < required LMTD < V-i. Equality at the
   upper bound requires sigma=0 and is rejected. Supply mode solves with explicit
   sigma>0 and R=V-sigma. Brackets use excess return temperature: [0,V-i] in return
   mode and [0,required LMTD] in supply mode. The zero endpoint is an analytical
   limit, not an operating temperature.
4. Deterministic bisection: at most 200 iterations, residual tolerance
   `1e-10 K + 1e-10 * required LMTD`. The reconstructed temperatures must close
   the equation too. `log1p` preserves accuracy near equal temperatures; exact
   equality in the public LMTD function uses its continuous limit. No Newton,
   silent clamp or extrapolation. No physical bracket and failed numerical
   closure have different diagnostics/statuses.
5. `design_mass_flow`: Formula 13, A*q/(sigma*4190) *
   [1+R_o/R_u+(i-u)/(q*R_u)]. Result is kg/s, including the declared downward heat
   contribution. R_o and R_u are explicit; construction-layer Formulas 14/15 are
   not inferred. Invalid/nonpositive resulting flow prevents hydraulic evaluation.
6. `pipe_hydraulics`: volume=m/rho, v=volume/(pi D²/4), Re=rho*v*D/mu.
   `churchill_friction` implements the prescribed exact all-regime Darcy equation.
   Large powers are evaluated with logarithms and log-sum-exp, algebraically
   equivalent to Churchill; no laminar/turbulent threshold or Haaland switch.
7. Darcy-Weisbach: dp=f*(L/D)*rho*v²/2. Returns Re, Darcy factor, velocity,
   total Pa/mbar, and Pa/m.
8. `kv_pressure_pa`: 100000*SG*(Q_m3h/Kv)². `required_kv` is the inverse equation.

All primitive functions reject invalid/nonfinite numerical arguments. Unrepresentable
finite-input arithmetic is never returned as NaN/Inf: the orchestration reports
`REJECTED_NUMERICAL_CALCULATION`. Invalid model inputs raise Pydantic validation
errors. Direct scalar functions may raise ValueError/ArithmeticError. Numeric
failure is not evidence of physical infeasibility.

## Pressure boundaries and balanceability

`en_circuit_pressure_pa` = total pipe friction + explicit continuous bends + pipe
fittings + other fixed pipe-path losses. Inclusive EN threshold: 35000 Pa.
The optional manufacturer maximum is checked independently against this same
embedded-circuit total. `manufacturer_pressure_ok=None` means no limit supplied.

Fixed manifold losses are stored separately. Natural branch loss is embedded
circuit loss plus fixed manifold losses; the adjustable characteristic is excluded.
No return valve or distributor loss is automatically added. Component IDs shared
between declared fixed manifold losses and `included_components` are rejected.
This is a minimal double-count check, not a component graph or product catalog.

At the design flow, valve minimum pressure corresponds to Kv_max, maximum to Kv_min:

    LOW_j = natural_j + valve_min_j
    HIGH_j = natural_j + valve_max_j
    LOW_GLOBAL = max(LOW_j)
    HIGH_GLOBAL = min(HIGH_j)

Balanceable within the declared characteristic iff LOW_GLOBAL <= HIGH_GLOBAL,
without widening the interval by tolerance. An empty feasible interval is `None`,
while both limiting numeric bounds and circuit IDs remain available. When feasible,
orchestration uses LOW_GLOBAL as a reproducible common branch operating point and
returns required Kv, combined manifold/control loss and complete branch loss.
This common differential pressure is not a pump-head selection.

## Source-domain semantics and statuses

Each characteristic records manufacturer, family, optional version, document
reference/revision, scope, included components, optional paired Kv/setting ranges,
limit type and source confidence. V1 calculations require Kv bounds; metadata-only
settings are not interpolated. Scope distinguishes single valve, supply path,
supply+return path and complete manifold path.

Outside a published/digitized domain yields `OUTSIDE_PUBLISHED_CHARACTERISTIC`,
not mechanical impossibility. For Kv below a published minimum the diagnostic is
`REQUIRED_KV_BELOW_PUBLISHED_MINIMUM_CHARACTERISTIC`. Physical impossibility stays
unknown (`None`), with `PHYSICAL_FEASIBILITY_UNKNOWN`. Recommended limits similarly
yield `OUTSIDE_RECOMMENDED_SETTING_RANGE`. Mechanical and manufacturer adjustment
range failures yield `REJECTED_BALANCEABILITY`; physical impossibility is asserted
only for explicitly mechanical limiting boundaries. Positive interval acceptance
is always conditional on the supplied characteristic, not proof of the whole system.

Thermal statuses include surface/output rejection, no physical root, and numerical
solver failure. Pressure rejection retains separate EN/manufacturer booleans and
diagnostics. EN overpressure also emits `SPLIT_REQUIRED` as a redesign signal;
splitting geometry is not implemented, and successful remediation is not guaranteed.
Multi-circuit primary rejection precedence is surface, thermal output, no thermal
root, numerical root, other numerical calculation, EN pressure, manufacturer pressure.
All per-circuit results remain available. Balance is calculated only after every
circuit passes; a missing balance result is not a positive balanceability claim.

## Regression evidence

Explicit water fixture: rho=990.22 kg/m³, mu=0.000594 Pa s, epsilon=0 m, ID=0.012 m.

| Mass flow kg/h | Re | dp/m Pa/m |
|---:|---:|---:|
| 60 | 2977.084607 | 39.185076614 |
| 100 | 4961.807678 | 96.394935843 |
| 200 | 9923.615357 | 315.439554756 |

Synthetic thermal supply/return: 31.818928635 / 26.818928635 °C, LMTD target
9.090909091 K; closure is tested. Formula 13 fixture: 97.088305489 kg/h.
Positive interval: [276.985850559, 394.546263971] mbar. Negative interval bounds:
LOW=276.985850559, HIGH=50.346641498 mbar; diagnostic
`CONTROL_VALVE_INSUFFICIENT_THROTTLING_RANGE`. LOW is limited by c6, HIGH by c1.

The requested interval anchors use explicit SG=1.0 (a synthetic approximation),
with volumetric conversion using rho=990.22. Using explicit SG=rho/1000=0.99022
instead gives LOW=276.842222940, positive HIGH=390.955573509 and negative
HIGH=50.122223344 mbar. Neither SG value is a hidden production default.

Anchor tests use 2e-9 relative tolerance for Churchill and 1e-8 mbar absolute
tolerance for intervals. Additional tests cover the 35000-Pa inclusive boundary,
100-m low/high-flow outcomes, thermal failure precedence, strict/immutable inputs,
overflow failure, component overlap, source semantics and deterministic digest.

Validation on the repository's existing `.venv` Python:

    python -m pytest -q tests/test_ufh_engineering_kernel.py
    python -m pytest -q tests -k floor_heating

Results: 46 new tests passed; 100 existing floor-heating tests passed. Bytecode
and pytest cache writing were disabled with `PYTHONDONTWRITEBYTECODE=1` and
`PYTEST_ADDOPTS=-p no:cacheprovider` to respect the bounded write scope.

## Protected baseline and limitations

Existing routing's 40000–80000 mm window is unchanged:
`LEGACY_MVP_ROUTING_POLICY`, not `UNIVERSAL_PHYSICAL_LOOP_LENGTH_LIMIT`.
The kernel does not inspect a length against 80 m. A 100-m candidate can pass or
fail depending on its design flow and resulting pressure.

No change to routing engine, coverage, sizing, AutoCAD/C#, renderers, DWG,
project/domain contracts, services, credentials, broker, TokenLedger or git history.
No commits/push. Existing user changes are preserved.

No pumps, mixing units, product catalogs, real manufacturer curve digitization,
header gradients, advanced manifold topology, bend-zeta/fitting libraries, automatic
diameter selection, optimization, geometric splitting or production integration.
Thermal tasks are evaluated as supplied; selection of a shared supply temperature
for all circuits is not a V1 optimizer. No normative construction or water-property
defaults are inferred. ACCEPTED means accepted under these declared mathematical
inputs and characteristic domains, not a complete installation certification.

Next recommended bounded block: **UFH_CANDIDATE_ADAPTER_V1** — an explicit,
separately authorized candidate-to-kernel adapter with unit/contract tests,
preserving the legacy router policy until separate integration acceptance.
