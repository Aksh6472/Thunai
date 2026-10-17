"""T-027: call freshness and bands, teller cap, FRI mapping (AI_DESIGN §6.1)."""

from datetime import timedelta

from app.domain.enums import CallType, FriRating, TellerItem
from app.domain.models import CallSignal
from app.domain.signals import call_reason, fri_reason, is_call_fresh, teller_reasons
from tests.factories import cfg, ist


def _call(duration: int, *, known: bool = False, ended_min_ago: int | None = None) -> CallSignal:
    at = ist(2, 18, 40)
    ended = at - timedelta(minutes=ended_min_ago) if ended_min_ago is not None else None
    return CallSignal(
        call_type=CallType.VIDEO,
        caller_known=known,
        duration_min=duration,
        ended_at=ended,
        observed_at=at,
    )


def test_call_duration_bands() -> None:
    at = ist(2, 18, 40)
    assert call_reason(_call(59), at, cfg()) is None
    assert call_reason(_call(60), at, cfg()).points == 8  # type: ignore[union-attr]
    assert call_reason(_call(179), at, cfg()).points == 8  # type: ignore[union-attr]
    assert call_reason(_call(180), at, cfg()).points == 15  # type: ignore[union-attr]


def test_known_caller_never_counts() -> None:
    assert call_reason(_call(300, known=True), ist(2, 18, 40), cfg()) is None


def test_call_ended_more_than_30_minutes_ago_is_ignored() -> None:
    at = ist(2, 18, 40)
    assert is_call_fresh(_call(200, ended_min_ago=30), at, cfg())
    assert not is_call_fresh(_call(200, ended_min_ago=31), at, cfg())


def test_active_call_observation_goes_stale() -> None:
    call = _call(200)
    assert is_call_fresh(call, ist(2, 19, 10), cfg())
    assert not is_call_fresh(call, ist(2, 19, 11), cfg())


def test_future_observation_is_not_fresh() -> None:
    assert not is_call_fresh(_call(200), ist(2, 18, 0), cfg())


def test_call_reason_is_tagged_simulated() -> None:
    reason = call_reason(_call(200), ist(2, 18, 40), cfg())
    assert reason is not None and reason.evidence["source"] == "SIMULATED"


def test_teller_items_sum_below_cap() -> None:
    drafts = teller_reasons((TellerItem.ON_CALL, TellerItem.MENTIONS_AUTHORITY), cfg())
    assert sum(d.points for d in drafts) == 23


def test_teller_points_are_capped_at_30_and_still_sum_exactly() -> None:
    drafts = teller_reasons(tuple(TellerItem), cfg())
    assert sum(d.points for d in drafts) == 30
    assert len(drafts) == 4  # every observation stays visible to staff
    assert any(d.evidence.get("capped") for d in drafts)


def test_duplicate_teller_items_count_once() -> None:
    drafts = teller_reasons((TellerItem.DISTRESSED, TellerItem.DISTRESSED), cfg())
    assert [d.points for d in drafts] == [8]


def test_fri_mapping() -> None:
    assert fri_reason(FriRating.MEDIUM, False, None, cfg()).points == 10  # type: ignore[union-attr]
    assert fri_reason(FriRating.HIGH, False, None, cfg()).points == 20  # type: ignore[union-attr]
    assert fri_reason(FriRating.VERY_HIGH, False, None, cfg()).points == 30  # type: ignore[union-attr]


def test_missing_fri_adds_nothing() -> None:
    assert fri_reason(None, False, None, cfg()) is None


def test_fri_unavailable_is_an_info_reason() -> None:
    reason = fri_reason(None, True, None, cfg())
    assert reason is not None and (reason.code, reason.points) == ("FRI_UNAVAILABLE", 0)
