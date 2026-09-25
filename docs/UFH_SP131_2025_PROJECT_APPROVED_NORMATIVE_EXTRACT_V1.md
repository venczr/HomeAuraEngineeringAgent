# UFH climate source package: SP 131.13330.2025

## Authority and scope

The structured subset in `standards-rag/climate/sp131_2025_table_5_1_extract.json` is a project-approved normative extract. It is not a copy of the standard and it does not classify either PDF host as the official publisher.

Layer A is the Rosstandart record for SP 131.13330.2025. It identifies the document as active, approved by order 470/pr on 2025-08-08, effective 2025-09-09, and replacing SP 131.13330.2020. That record establishes normative document identity/status, not climate table values. The official record was checked on 2026-09-15: [Rosstandart record](https://protect.gost.ru/sp/details/0634a74e-9f91-4571-82a8-b04c3a9b6c99).

Layer B uses two separately hosted published copies as text carriers:

- [Published SP copy hosted by kmdrus.ru](https://kmdrus.ru/uploads/sp/%D0%A1%D0%9F_131.13330.2025.pdf)
- [Published SP copy hosted by gpao.ru](https://www.gpao.ru/lib/u/file/Law_docs/SP-131.2025.pdf)

Both copies identify SP 131.13330.2025 and reproduce Table 5.1. The table header and all six selected locality rows were compared in both copies on 2026-09-15. The copies agree on the four relevant ordered data columns and row values. They remain third-party text carriers; they are never labelled `NORMATIVE_AUTHORITATIVE`.

## Table extraction

The ordered four-column slice is:

1. coldest day, probability 0.98;
2. coldest day, probability 0.92;
3. coldest five-day period, probability 0.98;
4. coldest five-day period, probability 0.92.

The bound parameter is column 4 (zero-based index 3), Table 5.1, temperature of the coldest five-day period at probability 0.92, in °C. Each JSON record stores all four values so the target cannot be confused with the coldest-day columns or the 0.98 five-day column.

The six extracted locality records are:

| Table section | Locality | Four ordered values (°C) | Bound 0.92 coldest five-day value |
|---|---|---:|---:|
| Ленинградская область | Винницы | −39, −36, −35, −31 | −31 °C |
| Ленинградская область | Выборг | −32, −30, −30, −26 | −26 °C |
| Ленинградская область | Николаевское | −33, −29, −30, −26 | −26 °C |
| Ленинградская область | Новая Ладога | −35, −31, −32, −27 | −27 °C |
| Ленинградская область | Санкт-Петербург | −30, −27, −27, −23 | −23 °C |
| Ленинградская область | Тихвин | −39, −35, −34, −30 | −30 °C |

`region` records the table-section label, not an independent assertion that every listed place has that administrative status. No region-wide temperature is created; a region-only answer requires locality selection.

## Dataset integrity and limits

The dataset and every record have deterministic digests calculated from their normalized typed payload. The source PDFs were not copied into the repository, and no source-file SHA-256 was available from the reviewed online copies. The extract therefore records `source_file_sha256: null`; the dataset/extraction digest is not presented as a PDF hash. Resolver authoring provenance carries the normalized dataset digest (and labels it as such), so a changed record package changes the downstream profile provenance/digest.

The official record reviewed established document identity and current status. No amendment metadata was surfaced in that record during this acquisition; the package marks this as a recheck item on refresh rather than claiming that no future amendment can exist. The resolver is bound to `SP131_2025`. `RU_CURRENT` is an explicit profile alias currently mapped to `SP131_2025`; it is registry data, not a “latest edition” heuristic. A future edition must be added with its own dataset and mapping.

The resolver returns `PROJECT_APPROVED_NORMATIVE_EXTRACT`. This authority means the project owner approved this two-layer source policy and the exact records were cross-checked against two published copies while normative document status was verified separately. It does not elevate the third-party hosts to official status or weaken other authority checks.

If the two text carriers disagree, the resolver returns `AMBIGUOUS` / `SOURCE_AMBIGUOUS`. The authoring result binds only `design_conditions.outdoor_design_temperature_c`; `rooms.json` `OutdoorTemperatureC` is not consulted or promoted. Test_01 has no assigned climate locality and remains incomplete unless a real user/project answer is explicitly applied.

## Copyright handling

Only a small structured factual extract and source references are retained. The full standard is not embedded in source code or documentation. Source URLs, retrieval date, exact table/row/column identity, verification statement, and calculated digests provide audit traceability without mirroring the complete document.
