from __future__ import annotations

import re

from ragdoll.api.shared_schemas import Citation, SourceTier
from ragdoll.platform.db.models import CorrectionRecord


def correction_citation(correction: CorrectionRecord, *, source_tier: SourceTier) -> Citation:
    return Citation(
        document_id=correction.document_id,
        entity_id=correction.entity_id,
        locator=correction.locator_text,
        source_tier=source_tier,
    )


def correction_matches_query(correction: CorrectionRecord, query_text: str) -> bool:
    tokens = [token for token in re.findall(r"[a-z0-9]+", query_text.lower()) if token]
    if not tokens:
        return True
    haystack = " ".join(
        filter(
            None,
            [
                correction.proposed_value,
                correction.rationale,
                correction.locator_text,
            ],
        )
    ).lower()
    return any(token in haystack for token in tokens)
