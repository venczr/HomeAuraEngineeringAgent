# D172 Claude task — west circuit of the north bedroom

You are an independent read-only geometric designer. Return a candidate only; do not edit any file.

Read these authoritative local files:

- `homeaura-native-editor/examples/room-7000x3200-south-exterior.homeaura.json` — the owner's hand-drawn `ACCEPTED` style reference.
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171/HomeAura_Floor1_OwnerAcceptedAnalogue_D171.homeaura.json` — current whole-floor context.
- `homeaura-native-editor/examples/proposals/HA_TWO_FLOOR_FLOOR1_OWNER_ACCEPTED_ANALOGUE_171/floor1_owner_accepted_analogue_contract.json` — current metrics (claims are not automatically trusted).

Design exactly ONE heating body for `F1-R08` west territory. Coordinates are integer 100-mm grid units with project conversion `x_mm=3000+x*100`, `y_mm=3000+y*100`.

Hard geometric domain:

- territory closed bbox: `x=47..65`, `y=58..85`;
- exterior inner finish faces: west `x=46`, north `y=57`;
- exterior wall-parallel axes must be exactly `x=47,48,49` and `y=58,59,60`, followed by field axes at 200-mm pitch;
- the east candidate by Kimi is confined to `x=67..92`; keep every point `x<=65`, leaving a 200-mm centreline corridor;
- heating body only: no K1 transit, no collector port, no wall crossing, no sleeves;
- immutable exclusions and all other D171 bodies must not be touched.

Owner grammar:

- one continuous, simple, orthogonal polyline on the grid;
- PE-X 16; nominal bend radius R80. Avoid 100-mm decorative doglegs. The three 100-mm exterior axes are required, but connect them through the overall counterflow path rather than adding arbitrary padding;
- three exterior passes must each cover at least 90% of its unobstructed wall-parallel span and cover the window projection where applicable;
- inward same-direction frames step 400 mm; return/interleave runs between them, yielding 200-mm field pitch;
- compact asymmetric centre analogous to one of the two ACCEPTED centre closures. It must have 6–8 alternating segments, at least two 200-mm segments, bbox no larger than 700×700 mm, no rectangular central void;
- no self crossing, self touch, duplicate edge or zero segment;
- no useful territory sample may be more than 200 mm from the axis; prefer maximum <=150 mm and round-100-mm-buffer coverage >=97%;
- estimated complete length uses `body_length + Manhattan(K1=(134,63),start) + Manhattan(K1,end)`, all multiplied by 100 mm. Required 40–80 m; target 52–54 m. The paired east target is also 52–54 m; aim group spread <=2 m.

Current baseline to beat: body 31.1 m; direct service estimate 18.1 m; total 49.2 m; territory round-100 coverage 91.60%; worst sampled distance 300 mm.

Return exactly one JSON object and no Markdown:

```json
{
  "status": "CANDIDATE" | "NO_FEASIBLE_CANDIDATE",
  "provider": "CLAUDE",
  "circuit_id": "F1-D172-CLAUDE-WEST",
  "territory_bbox_grid": [47,58,65,85],
  "ordered_body_points_grid": [[47,58]],
  "centre": {"start_index":0,"end_index":0,"template":"A|B|ANALOGUE","rotation_deg":0,"mirrored":false},
  "exterior_passes": [
    {"side":"WEST","axis_levels_grid":[47,48,49]},
    {"side":"NORTH","axis_levels_grid":[58,59,60]}
  ],
  "claimed": {"body_length_mm":0,"estimated_service_length_mm":0,"estimated_complete_length_mm":0},
  "blocking_constraints": []
}
```

If requirements conflict, return `NO_FEASIBLE_CANDIDATE` honestly instead of weakening them.
