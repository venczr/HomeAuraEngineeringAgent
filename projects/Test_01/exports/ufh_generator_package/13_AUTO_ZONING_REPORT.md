# AUTO zoning integration — kitchen / living room №3

The Test_01 editor now uses `AUTO` by default for the selected room. It calls `/api/floor-heating/zone-preview`, which invokes the existing zone generator and endpoint-access checks. The editor no longer sends `requested_circuit_count: 1` for AUTO.

For room №3 the source polygon is preserved and split into three exact horizontal bands. Each band produces one continuous route:

- `zone-3-1`: 63.088 m
- `zone-3-2`: 63.088 m
- `zone-3-3`: 63.088 m

All three routes have independent endpoints, pass geometry/topology/bend checks, and have geometric access to their own room boundary. The route IDs remain stable in the editor state. `MANIFOLD_CONNECTED` remains `UNVERIFIED`; no wall, door, corridor, riser, or collector path is invented. Transit length is therefore `UNVERIFIED`, and the 90 m project limit is reported for internal route length only until transit is confirmed.

With a 50 m limit, the same geometry is rejected because no candidate satisfies the limit. This confirms that changing the limit changes the AUTO result rather than preserving the previous route.
