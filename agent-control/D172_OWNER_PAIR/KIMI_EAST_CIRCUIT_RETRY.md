NO TOOLS. Do not read files. Solve from this prompt and output one compact JSON object in your first response, under 3000 characters.

Draw one body-only 100-mm-grid PE-X16 counterflow circuit in bbox `[67,58,92,85]`. North inner face is y57. Required long exterior axes: y58/y59/y60. All points inside bbox. West sibling stays x<=65. Orthogonal, continuous, simple, no duplicate edge, no arbitrary padding. Field pitch 200 mm, inward frames 400 mm with interleaved return. Compact asymmetric owner-style centre. Aim body 40-42.5m. Estimated full = body + Manhattan distances of both endpoints to K1(134,63), target 51-54m. Improve current worst-distance200mm and coverage97.8%; prefer max distance<=150mm.

Current baseline to improve (do not copy unchanged): `[[92,58],[67,58],[67,59],[92,59],[92,60],[67,60],[67,62],[92,62],[92,85],[67,85],[67,66],[88,66],[88,81],[71,81],[71,70],[84,70],[84,77],[75,77],[75,75],[82,75],[82,72],[73,72],[73,79],[86,79],[86,68],[69,68],[69,83],[90,83],[90,64],[69,64]]`.

Return only:
`{"status":"CANDIDATE"|"NO_FEASIBLE_CANDIDATE","provider":"KIMI","ordered_body_points_grid":[[x,y],...],"centre_indices":[start,end],"claimed_body_length_mm":0,"blocking_constraints":[]}`
