# UFH envelope operating-condition resolver v1

## Normative source package

The package pins SP 50.13330.2024, approved by Minstroy order 327/pr on 2024-05-15 and effective 2024-06-16. Rosstandart's SP card is used only for document identity/status. The compact Table 1/Table 2 transcription is marked `PROJECT_APPROVED_NORMATIVE_EXTRACT`, cross-checked against the Garant and Mooml published text carriers and the GOSTCheck Table 2 transcription. No full standard text is stored.

Table 1 interval semantics are encoded as data: temperature bands are `t <= 12`, `12 < t <= 24`, and `t > 24`; RH thresholds use the standard's “до” (inclusive) and “свыше” (strictly greater) wording. In the first temperature band the source has no separate wet regime: RH above 75% remains the humid regime. In the other two bands wet starts strictly above 75% and 60%, respectively.

Table 2 rows are stored per room regime and moisture zone. Table 2 groups “влажный или мокрый” together, both mapping to B in all three zones. It applies to material-property selection for outer envelope constructions; interior scope returns not-applicable.

## Appendix A limitation

Appendix A is published as a Russia moisture-zone map (zones 1 dry, 2 normal, 3 humid), not as a verified locality lookup dataset. This implementation does not infer zone from SP 131 locality, temperature, region name, or visual approximation. Until a reproducible authoritative geospatial mapping is available, a zone must arrive as a provenance-bearing `ConstructionMoistureZoneInput` referencing an approved project/normative source. Otherwise the resolver reports `MOISTURE_ZONE_SOURCE_REQUIRED` / `APPENDIX_A_LOCALITY_MAPPING_NOT_AUTOMATED`.

## Inputs and behavior

The resolver requires sourced indoor design temperature and design RH, plus a construction moisture zone and explicit exterior-envelope scope. It derives DRY/NORMAL/HUMID/WET from Table 1 and A/B from Table 2. It never selects B as a fallback. The common resolver contract writes the semantic A/B result to `envelope_constructions.operating_condition`; no numeric temperature, material property, heat loss, or sizing result is created. Dependency identity uses the indoor setpoint value/source field, RH answer, zone evidence, scope, and normative dataset—not the unrelated whole project file revision or outdoor design temperature—so an unrelated climate-temperature edit does not stale A/B.

The material bridge `apply_condition_to_material_request` passes the resolved A/B plus source reference, table provenance, authority class, and dependency digest to the existing material-property resolver. Consequently only that resolver selects Appendix M lambda_A or lambda_B. The SP 345 insulation Appendix D/E route remains separate and unresolved here.

## Source references

- Official identity/status: https://protect.gost.ru/sp/details/5081dae9-9ee9-455f-80e8-d093d495361c
- Published text extract: https://base.garant.ru/409274974/
- Published text extract: https://mooml.com/d/normativno-pravovye-dokumenty/proektirovanie-inzhenernye-izyskaniya/55765/
- Table 1 and Table 2 cross-check: https://gostcheck.ru/sp/sp-50-13330-2024/table/sp-50-13330-2024-table-1
- Table 2 cross-check: https://gostcheck.ru/sp/sp-50-13330-2024/table/sp-50-13330-2024-table-2
- Appendix A rendered map evidence: https://storage.consultant.ru/ondb/attachments/202407/19/iddoc_283336_idnews_54381_SP-50_zCc.pdf
