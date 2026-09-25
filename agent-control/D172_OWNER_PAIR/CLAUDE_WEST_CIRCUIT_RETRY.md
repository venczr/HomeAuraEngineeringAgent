NO TOOLS. Do not read files. Solve from this prompt and output one compact JSON object in your first response, under 3000 characters.

Draw one body-only 100-mm-grid PE-X16 counterflow circuit in bbox `[47,58,65,85]`. North inner face is y57, west inner face x46. Required long exterior axes: y58/y59/y60 and x47/x48/x49. All points inside bbox. East sibling stays x>=67. Orthogonal, continuous, simple, no duplicate edge, no arbitrary padding. Field pitch 200 mm, inward frames 400 mm with interleaved return. Compact asymmetric owner-style centre. Aim body 33-35m. Estimated full = body + Manhattan distances of both endpoints to K1(134,63), target 51-53m. Improve current worst-distance300mm and coverage92.3%; hard max distance200mm.

Current baseline to improve (do not copy unchanged): `[[47,85],[47,58],[65,58],[65,59],[48,59],[48,85],[49,85],[49,60],[65,60],[65,62],[51,62],[51,85],[65,85],[65,66],[55,66],[55,81],[61,81],[61,79],[57,79],[57,68],[63,68],[63,83],[53,83],[53,64],[63,64]]`.

Return only:
`{"status":"CANDIDATE"|"NO_FEASIBLE_CANDIDATE","provider":"CLAUDE","ordered_body_points_grid":[[x,y],...],"centre_indices":[start,end],"claimed_body_length_mm":0,"blocking_constraints":[]}`
