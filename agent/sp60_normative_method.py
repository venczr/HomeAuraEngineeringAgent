"""Canonical SP 60 revision identity shared by the building-physics cores.

This module contains revision/provenance metadata only. Formula-specific
method records remain owned by their respective SP60 calculation modules.
"""
from __future__ import annotations

import hashlib
import json


SP60_CANONICAL_REVISION = {
    "document_id": "SP 60.13330.2020",
    "title": "Отопление, вентиляция и кондиционирование воздуха",
    "status": "ACTIVE",
    "base_approval_order": "Минстрой России 921/пр",
    "base_approval_date": "2020-12-30",
    "base_effective_date": "2021-07-01",
    "consolidated_amendments": [1, 2, 3, 4, 5, 6],
    "consolidated_text_revision": "2026-05-26",
    "consolidated_text_effective_date": "2026-07-07",
    "amendment_6": {
        "approval_order": "Минстрой России 327/пр",
        "approval_date": "2026-05-26",
        "rosstandart_registration_date": "2026-06-15",
        "official_publication_date": "2026-07-07",
        "effective_date": "2026-07-07",
        "order_entry_rule": "from date of publication",
    },
    "official_identity_source": "https://protect.gost.ru/sp/details/b00f766e-b861-4cc7-a448-c65906490262",
    "official_amendment_6_source": "https://protect.gost.ru/sp/changesdetails/25d65837-dfb6-408b-948f-e7f254851ded",
    "official_identity_authority": "NORMATIVE_DOCUMENT_IDENTITY_AUTHORITY",
    "text_carrier_authority": "TEXT_CARRIER_ONLY",
}

SP60_CANONICAL_REVISION_DIGEST = hashlib.sha256(
    json.dumps(SP60_CANONICAL_REVISION, sort_keys=True, ensure_ascii=False,
               separators=(",", ":")).encode("utf-8")
).hexdigest()
