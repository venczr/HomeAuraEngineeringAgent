# Semantic face planar graph ? 2026-09-17

## Reconstruction evidence
96 raster wall candidates assemble into 61 source-linked collinear chains and 14 sustained gaps. Short dimension/text interruptions remain excluded. Gaps now distinguish exterior WINDOW_CANDIDATE, exactly-two-room OPEN_PASSAGE_CANDIDATE and UNKNOWN_OPENING.

A deterministic planar polygonization experiment was run over noded wall centerlines, reviewed outer contours and virtual sustained-gap closure. It does not yet produce a complete subdivision: floor 1 yields only 3 faces and attic 8 faces because raster walls are represented by parallel faces and missing junction closures. This is recorded as algorithm evidence, not promoted geometry.

Rooms 2 and 9 each lie in a uniquely containing polygonized component, but those components also contain neighboring labels or unsupported residual space. Therefore neither face is semantically unique. Area labels were not used for selection. Routing remains 14/16.

## Engineering intake
Added typed whole-building intake supporting KNOWN_U_VALUE or LAYER_ASSEMBLY for envelope inputs, allowing existing SP50/SP345 resolvers to calculate properties when users know construction layers. Openings, room height, winter air basis and climate binding remain explicit typed fields.

## Climate
The existing SP131 resolver uses exact locality matching. Its approved extract contains no ???????? record/alias. Status is NORMATIVE_LOCALITY_BINDING_REQUIRED; no nearest-city substitution is made.

## Tests
46 targeted topology, routing, climate, intake and SP60 binding tests passed. Compile and whitespace checks passed.
