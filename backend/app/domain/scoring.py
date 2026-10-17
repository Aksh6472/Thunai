"""Transfer scoring (AI_DESIGN §6). Deterministic, additive, explained. Pure.

score = clamp(sum(reason points), 0, 100). The reasons always sum exactly to raw_score.
"""

from app.domain.config import ScoringConfig
from app.domain.enums import BaselineConfidence, Stage
from app.domain.models import Assessment, AssessmentInput, Reason, StageEvent
from app.domain.policy import decide
from app.domain.reasons import render_reasons
from app.domain.signals import (
    ReasonDraft,
    call_reason,
    contact_changed_reason,
    fri_reason,
    teller_reasons,
)
from app.domain.stage_reasons import fd_reason, pooled_reason, sequence_reason
from app.domain.stages import is_high_value


class ScoringInvariantError(RuntimeError):
    """The reasons do not add up to the score. Never expected; fails the assessment closed."""


def _payee_age_minutes(inp: AssessmentInput) -> int:
    delta = inp.transfer.initiated_at - inp.transfer.payee.added_at
    return max(0, int(delta.total_seconds() // 60))


def _new_payee_reason(inp: AssessmentInput, cfg: ScoringConfig) -> ReasonDraft | None:
    # ADR-020: payee age is compared in whole hours (128 min counts as 2 h).
    age_minutes = _payee_age_minutes(inp)
    for band in cfg.points.new_payee:
        if age_minutes // 60 <= band.max_age_hours:
            return ReasonDraft(
                "NEW_PAYEE",
                band.points,
                Stage.S3_NEW_PAYEE.value,
                {"payee_age_minutes": age_minutes, "payee_ref": inp.transfer.payee.payee_ref},
            )
    return None


def _dampener_reasons(inp: AssessmentInput, cfg: ScoringConfig) -> list[ReasonDraft]:
    """Negative points only on positive evidence of an established relationship (§9)."""
    payee, amount = inp.transfer.payee, inp.transfer.amount_paise
    age_minutes = _payee_age_minutes(inp)
    drafts: list[ReasonDraft] = []
    established = cfg.points.established_payee
    if (
        age_minutes >= established.min_payee_age_days * 24 * 60
        and payee.prior_successful_transfers >= established.min_prior_successful_transfers
    ):
        drafts.append(
            ReasonDraft(
                "ESTABLISHED_PAYEE",
                established.points,
                evidence={
                    "payee_age_days": age_minutes // (24 * 60),
                    "prior_successful_transfers": payee.prior_successful_transfers,
                },
            )
        )
    regular = cfg.points.matches_regular_pattern
    recurring = payee.recurring_amount_paise
    if recurring and amount <= regular.max_multiple_of_recurring * recurring:
        drafts.append(
            ReasonDraft(
                "MATCHES_REGULAR_PATTERN",
                regular.points,
                evidence={"recurring_amount_paise": recurring},
            )
        )
    return drafts


def _amount_reasons(inp: AssessmentInput, cfg: ScoringConfig) -> list[ReasonDraft]:
    amount, median = inp.transfer.amount_paise, inp.baseline.median_outbound_paise
    drafts: list[ReasonDraft] = []
    high_value = cfg.points.high_value_to_payee
    multiple = amount // median
    if amount >= high_value.min_amount_paise:
        points = 0
        for band in high_value.bands:
            if multiple >= band.min_multiple:
                points = band.points
        if points:
            drafts.append(
                ReasonDraft(
                    "HIGH_VALUE_TO_PAYEE",
                    points,
                    Stage.S4_HIGH_VALUE.value,
                    {
                        "amount_paise": amount,
                        "multiple_of_median": multiple,
                        "median_outbound_paise": median,
                        "baseline_confidence": inp.baseline.confidence.value,
                    },
                )
            )

    balance = inp.transfer.source_account_balance_paise
    drain = cfg.points.balance_drain
    if balance <= 0 or amount >= drain.min_fraction_of_balance * balance:
        percent = 100 if balance <= 0 else min(100, round(amount * 100 / balance))
        drafts.append(
            ReasonDraft("BALANCE_DRAIN", drain.points, evidence={"percent_of_balance": percent})
        )
    return drafts


def score_reasons(inp: AssessmentInput, cfg: ScoringConfig) -> tuple[tuple[Reason, ...], bool]:
    """All reasons for a transfer, and whether the transfer itself is an S4 stage."""
    is_s4 = is_high_value(inp.transfer.amount_paise, inp.baseline, cfg)
    stages = inp.episode_stages
    if is_s4:
        stages = (
            *stages,
            StageEvent(
                stage=Stage.S4_HIGH_VALUE,
                event_id=inp.transfer.transfer_ref,
                occurred_at=inp.transfer.initiated_at,
                amount_paise=inp.transfer.amount_paise,
                payee_id=inp.transfer.payee.payee_id,
            ),
        )
    signals = inp.signals
    drafts: list[ReasonDraft | None] = [
        fd_reason(stages, inp.baseline, cfg),
        pooled_reason(stages, cfg),
        _new_payee_reason(inp, cfg),
        *_amount_reasons(inp, cfg),
        sequence_reason(stages, cfg),
        fri_reason(
            signals.fri_rating, signals.fri_unavailable, signals.fri_linked_msisdn_last4, cfg
        ),
        call_reason(signals.call, inp.now, cfg),
        *teller_reasons(signals.teller_items, cfg),
        contact_changed_reason(signals.trusted_contact_changed_at, inp.now, cfg),
        *_dampener_reasons(inp, cfg),
    ]
    if inp.baseline.confidence is BaselineConfidence.LOW:
        drafts.append(
            ReasonDraft(
                "BASELINE_LOW_CONFIDENCE",
                0,
                evidence={
                    "history_days": inp.baseline.history_days,
                    "qualifying_transfer_count": inp.baseline.qualifying_transfer_count,
                },
            )
        )
    return render_reasons([d for d in drafts if d is not None]), is_s4


def assess(inp: AssessmentInput, cfg: ScoringConfig) -> Assessment:
    reasons, is_s4 = score_reasons(inp, cfg)
    raw = sum(r.points for r in reasons)
    score = max(0, min(100, raw))
    tier = cfg.tiers.tier_for(score)
    policy = decide(
        tier,
        inp.transfer.amount_paise,
        inp.signals.fri_rating,
        inp.has_active_trusted_contact,
        cfg,
    )
    assessment = Assessment(
        raw_score=raw,
        score=score,
        tier=policy.tier,
        decision=policy.decision,
        overrides_applied=policy.overrides,
        initial_hold_status=policy.initial_hold_status,
        reasons=reasons,
        config_version=cfg.config_version,
        is_s4=is_s4,
    )
    _check_invariants(assessment)
    return assessment


def _check_invariants(assessment: Assessment) -> None:
    if sum(r.points for r in assessment.reasons) != assessment.raw_score:
        raise ScoringInvariantError("reason points do not sum to raw_score")
    if assessment.decision.value != "ALLOW" and not any(r.points for r in assessment.reasons):
        raise ScoringInvariantError("a WARN/HOLD decision has no non-zero reason")
