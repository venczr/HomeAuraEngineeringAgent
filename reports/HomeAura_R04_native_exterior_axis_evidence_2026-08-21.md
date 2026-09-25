# HomeAura R04 — native exterior-axis evidence

Date: 2026-08-21  
Scope: exact analyzer convention for C05/C06 scratch BODY planning; not an accepted finish-face survey.

## Frozen sources

- Official D185 project SHA-256: `558304DF7C9F774CF048F5C2F235F32986659100CFEA4078825534A2AA02FFF4`
- `CircuitAnalyzer.cs` SHA-256: `084C3D8CB72D4F4A1150B2C663EA30E6F971320336BDD7E0EE3262CE8EF1908E`
- R04 source outline: `(16200,8500) – (21300,8500) – (21300,11800) – (16200,11800)`
- Inferred clear rectangle used only for DRAFT analysis: `[16300,21100] × [8700,11700]`, area `14.4 m²`

## Native convention

`CircuitAnalyzer.TryGetInteriorNormal` at lines 3175–3199 probes from a wall centerline toward the room. `AnalyzeExteriorWallBands` at lines 1946–1951 then computes each lane coordinate as:

`wall centerline + interior normal × (wall thickness / 2 + lane index × 100 mm)`.

Therefore:

- W022 is horizontal at `y=8500`, thickness `400`; the room is north, so normal is `+Y`. Required BODY axes are exactly `y=8800`, `8900`, `9000`.
- W023 is vertical at `x=21300`, thickness `400`; the room is west, so normal is `−X`. Required BODY axes are exactly `x=21000`, `20900`, `20800`.

The opposite values `y=8800/8700/8600` or `x=21000/21100/21200` are not the native interior-band convention and must be rejected.

## Claim boundary

These coordinates resolve the software wall-face orientation only. They do not resolve the conflicting R04 authoritative area (`15.9 m²` declared, `14.4 m²` inferred, `16.83 m²` prior artifact), verified W024/W025/W026 gates, or exact Eurocone tails. Any generated C05/C06 BODY remains scratch `DRAFT|NO_GO`; SERVICE and FULL remain `NO_GO` until native diagnostics and physical input gates pass.
