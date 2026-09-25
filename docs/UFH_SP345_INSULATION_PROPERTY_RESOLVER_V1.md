# SP345 insulation resolution — dated-reference and layer-formula update

## Normative decision

The consolidated SP 345.1325800.2017 note in clause 2 distinguishes undated from dated references. For a replaced **dated** reference, it recommends using the version bearing the specified approval year. The insulation provisions cite SP 50.13330.2012 Appendix T; Amendment 2 updates that citation to SP 50.13330.2012 with Amendments 1 and 2. The dated dependency is therefore retained as `SP50_2012_APPENDIX_T_AMENDMENTS_1_2`; SP 50.13330.2024 Appendix M is not substituted.

Official document identity/status is separate from text carriers. Rosstandart identifies SP345 and Amendment 2, and the SP50.2012 card shows its replacement by SP50.2024. The structured Appendix-T subset is classified `PROJECT_APPROVED_NORMATIVE_EXTRACT`, not as an official publisher record.

The package contains only Table T.1 insulation rows 1–8 used by the existing SP50 insulation subset. It preserves the printed description, density range, lambda0, wA/wB, lambdaA/lambdaB, table row, revision and per-record digest. The verified 2012 consolidated Amendment-1+2 rows in the selected subset match the selected SP50.2024 rows; this does not change dated-reference ownership. Earlier unamended 2012 rows do differ from 2024 and remain in a separate historical audit object, never used for resolver binding.

## Formula 5.1a and gamma

The equation image for SP345 clause 5.2 formula (5.1a) was inspected. It places the layer operating coefficient as a multiplier of the layer resistance:

`R_s = (delta_s / lambda_s) * gamma_s^(у.э.)`

Here delta is thickness (m), lambda is the design conductivity for A or B, and gamma is dimensionless. The generic non-insulation path remains `d/lambda`; only a layer resolved as the SP345 insulation path uses the specialized formula.

The linked equation-image carrier used for visual verification has SHA-256 `628bd41eeea68aa6c7238dc15d45358f1cd9e1b192e65351617fd5ed1e3a6dbe`.

Gamma precedence is explicit: project/test result, applicable Appendix-E method result, then the clause 5.2 absence-of-data fallback `gamma=1`. The fallback carries clause and source provenance and is not a software default. Roofs, SFTK, layered masonry, mineral-wool NFS, and polymer buried/ground-contact scopes require the applicable Appendix-E/test result; the fallback is not used to bypass them. Appendix E’s approximations that require a 50-year effective service-life condition are not automatically assigned.

The SP345 A/B operating condition remains a different concept from gamma. Existing A/B is consumed as an input; this module does not recompute it.

## Lambda routes

For the selected exact Table T.1 records, the resolver computes both direct referenced lambda and Appendix-D lambda using the sourced Table-T lambda0/w values and the SP345 Table D.1 eta record. When the values differ because the tabulated value is rounded, both are returned with an exact delta and no invented tolerance. The caller must explicitly select `DIRECT_REFERENCE` or `APPENDIX_D_CALCULATED`; no silent route selection occurs.

The Appendix-D percent calculation is `lambda0 * (1 + eta * w)` where eta is `1/%` and w is `%`; there is no additional division by 100. For calculated mode, lambda0 and moisture values come from the dated Appendix-T package. Test-only lambda0 values remain non-bindable.

## Appendix E boundaries

E.2 applies methods based on GOST R 57418 (mineral wool) or GOST R 58950 (polymer) to roof, SFTK and layered masonry scopes; its text permits an approximate 0.9 for an effective service life of 50 years. E.3 covers mineral wool in ventilated façade systems and cites GOST R 56732, with a 0.95 approximation under its 50-year condition. E.4 covers polymer insulation in buried/ground-contact constructions and cites GOST R 58950, with a 0.9 approximation under the specified condition. This block does not infer those conditions or produce an Appendix-E result. Ground heat-loss remains unresolved independently.

## Sources

- Official [Rosstandart SP345 card](https://protect.gost.ru/sp/details/c020552a-f741-47c3-a588-491af35f8b88) and [Amendment 2 card](https://protect.gost.ru/sp/changesdetails/cbf2eee3-4a10-4f6e-9977-69f335e914fd).
- Consolidated text carrier: [SP345, revised 23.12.2022](https://meganorm.ru/mega_doc/norm/metodika/0/sp_345_1325800_2017_svod_pravil_zdaniya_zhilye_i.html); equation image at `.../meganorm_521077.png` linked from clause 5.2.
- Official [SP50.2012 status card](https://protect.gost.ru/sp/details/1e4f6a14-4010-46ef-a0c3-76189b93fa01).
- Independent Table T.1 carriers: [Buildingbook consolidated text](https://buildingbook.ru/sp-50-13330-2012.html), [Kritery PDF](https://kritery.ru/storage/files/5.EE/35-%D0%A1%D0%9F_50.13330.2012.pdf), and [Amendment 2 text carrier](https://nav.tn.ru/upload/directions/SNiP-23-02-2003.-Teplovaya-zaschita-zdanii.pdf).

No complete normative document is embedded in the repository; only the narrow structured table subset and source references/digests are represented.
