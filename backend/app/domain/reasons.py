"""Turn reason drafts into Reasons with EN/TA text (FR-08)."""

from collections.abc import Iterable

from app.domain.i18n.reason_texts import render
from app.domain.models import Reason
from app.domain.signals import ReasonDraft

STAGE_LABELS = {
    "S1_LIQUIDATION": "S1",
    "S2_POOLING": "S2",
    "S3_NEW_PAYEE": "S3",
    "S4_HIGH_VALUE": "S4",
}


def render_reasons(drafts: Iterable[ReasonDraft]) -> tuple[Reason, ...]:
    reasons = []
    for draft in drafts:
        text_en, text_ta = render(draft.code, draft.evidence)
        reasons.append(
            Reason(
                code=draft.code,
                points=draft.points,
                stage=STAGE_LABELS.get(draft.stage) if draft.stage else None,
                evidence=draft.evidence,
                text_en=text_en,
                text_ta=text_ta,
            )
        )
    return tuple(reasons)
