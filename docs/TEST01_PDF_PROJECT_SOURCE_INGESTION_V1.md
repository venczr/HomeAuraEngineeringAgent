# TEST01_PDF_PROJECT_SOURCE_INGESTION_V1

## Ingested sources

The two user-designated ChatGPT Library files are archived unchanged under
`projects/Test_01/engineering/source_documents/`. Their original library
names, byte lengths, `%PDF-` signatures, page metadata, SHA-256 values and
visual observations are recorded in
`projects/Test_01/engineering/test01_pdf_project_source_ingestion_v1.json`.
The manifest loader verifies both file hashes and its own deterministic digest
before exposing the package to the Test_01 source inventory.

| Document | Page title | Sheet | Scale | Date | Bytes | SHA-256 |
| --- | --- | ---: | ---: | --- | ---: | --- |
| `План 1 этажа с отметками.pdf` | План 1 этажа | 1 | 1:100 | 09.12.2024 | 441606 | `40f396cbb4f7fb6d1dafc198ce81492999a34f66c2f96d113ca8d33360586b25` |
| `План мансарды с отметками.pdf` | План мансарды | 2 | 1:100 | 09.12.2024 | 379741 | `b66d169ed5b1fdeff12b817fc887226376740a34592c777ee3fe5aa40967075d` |

Both are one-page A4 portrait image-only PDFs. Text extraction returned no
selectable page text; title-block values and the visible plan features were
reviewed from rendered pages. The title block declares the site as:

> Российская Федерация, Ленинградская область, Ломоносовский муниципальный
> район, Низинское сельское поселение, дер. Узигонты.

This is retained as a project-document location observation, not a climate
dataset locality binding. The available SP131 resolver must still establish a
normative row for the exact locality; no temperature or wind is inferred.

## Binding limits

The plans depict architectural room divisions, room labels, dimensions and
opening-like symbols. They do not expose `101DAA3` or room code `101`, and no
reviewed drawing coordinate transform links a depicted room/opening to the
authoritative IFC room boundary. Consequently:

- no room-use label is assigned to Room 101 based on name or area similarity;
- no thermal-boundary type, boundary area, opening inventory, construction,
  U-value, material property, or height is promoted;
- apparent opening symbols do not prove a complete opening schedule or prove
  that a particular opening belongs to Room 101;
- no SP60 calculation, UFH sizing, routing, or shadow validation is run.

The intake/source-binding audit can show the PDF source observations and hashes
while preserving the existing unresolved engineering gaps. Original project
DWG/MRD/rooms/IFC sources remain read-only.

The interactive intake now includes the declared plan location as visible
question context. It remains `OBSERVED_NOT_BOUND` until the existing climate
resolver can resolve an exact supported normative locality; it never supplies
an outdoor temperature by itself.
