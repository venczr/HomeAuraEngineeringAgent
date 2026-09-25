# HomeAura D170 — correction from owner markup

Source feedback: the D169 floor image had large uncovered zones, heating bodies visually inside wall thickness, no visible three-pass 100 mm exterior band, and an unused narrow hall strip suitable for a serpentine continuation.

Implemented:

- `ManualCircuit` now records `room_id`, `heating_body_start_index`, and `heating_body_end_index`.
- The native analyzer distinguishes heating-body wall intrusion from allowed transit wall crossings.
- Heating-body engineering acceptance requires containment in the assigned heated room and zero wall-solid intrusion.
- The renderer draws declared service/transit portions dashed and heating bodies solid.
- Floor 1 was repartitioned into 14 bodies: 2 north bedroom, 2 west bedroom, 1 bathroom, 1 shower, 2 boiler room, 4 kitchen/living, 1 entrance, 1 long hall circuit.
- Exterior-wall axes use three passes at 100 mm pitch followed by the 200 mm field.
- Bathroom and shower bodies are separated by the 100 mm partition; only future transit geometry may cross it.
- The owner-marked narrow hall void has one natural U-shaped serpentine continuation.

Validation:

- body count: 14
- body wall intrusions: 0
- bodies outside assigned rooms: 0
- body exclusion hits: 0
- inter-body contacts: 0
- exact exterior 3x100 records: PASS
- native test suite: 29/29 PASS
- body-only round-100 proximity diagnostic: 69.14%; not a thermal/full-coverage claim

Artifact: `HA_TWO_FLOOR_FLOOR1_USER_MARKUP_CORRECTION_170`.

Remaining bounded work: materialize the 28 individual K1 service legs as explicit transit sections. Wall crossings are permitted only in those transit sections; they must remain visually and machine-semantically distinct from heating bodies.
