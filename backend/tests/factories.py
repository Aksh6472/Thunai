"""Builders for engine inputs (TESTING.md §9). All data fictional.

The hero (P1), N1 and N4 match AI_DESIGN §6.4.
"""

from datetime import UTC, date, datetime, timedelta, timezone

from app.core.scoring_config import load_scoring_config
from app.domain.config import ScoringConfig
from app.domain.enums import (
    BaselineConfidence,
    CallType,
    Channel,
    EventType,
    FriRating,
    Rail,
    Stage,
    TellerItem,
)
from app.domain.models import (
    AssessmentInput,
    Baseline,
    CallSignal,
    EventFacts,
    PayeeFacts,
    Signals,
    StageEvent,
    TransferFacts,
)

IST = timezone(timedelta(hours=5, minutes=30))


def cfg() -> ScoringConfig:
    return load_scoring_config()


def ist(day: int, hh: int, mm: int = 0) -> datetime:
    """Hero calendar: day 1 = 1 Oct 2026, in IST."""
    return datetime(2026, 9, 30, hh, mm, tzinfo=IST) + timedelta(days=day)


def rupees(n: int) -> int:
    return n * 100


def baseline(
    median_rupees: int = 40_000,
    *,
    history_days: int = 180,
    count: int = 24,
    premature: int = 0,
    confidence: BaselineConfidence = BaselineConfidence.OK,
) -> Baseline:
    return Baseline(
        history_days=history_days,
        median_outbound_paise=rupees(median_rupees),
        p95_outbound_paise=rupees(median_rupees) * 3,
        qualifying_transfer_count=count,
        premature_fd_closures_365d=premature,
        confidence=confidence,
    )


def stage(
    kind: Stage, at: datetime, amount_rupees: int | None = None, event_id: str = ""
) -> StageEvent:
    return StageEvent(
        stage=kind,
        event_id=event_id or f"EVT-{kind.value}-{at:%d%H%M}",
        occurred_at=at,
        amount_paise=rupees(amount_rupees) if amount_rupees is not None else None,
    )


# ---------- Hero P1: R. Kamala (fictional), CUST-0007 ----------

HERO_FD = EventFacts(
    event_id="EVT-P1-FD",
    event_type=EventType.FD_CLOSED,
    occurred_at=ist(1, 10, 5),
    amount_paise=rupees(35_00_000),
    maturity_date=date(2027, 4, 1),
    to_account="XXXXXX2201",
)
HERO_POOL_1 = EventFacts(
    event_id="EVT-P1-POOL-1",
    event_type=EventType.INTERNAL_TRANSFER_IN,
    occurred_at=ist(2, 11, 0),
    amount_paise=rupees(6_00_000),
    to_account="XXXXXX2201",
)
HERO_POOL_2 = EventFacts(
    event_id="EVT-P1-POOL-2",
    event_type=EventType.INTERNAL_TRANSFER_IN,
    occurred_at=ist(2, 11, 30),
    amount_paise=rupees(5_00_000),
    to_account="XXXXXX2201",
)
HERO_PAYEE = EventFacts(
    event_id="EVT-P1-PAYEE",
    event_type=EventType.PAYEE_ADDED,
    occurred_at=ist(3, 9, 12),
    payee_id="PAY-0007-03",
)

HERO_STAGES = (
    stage(Stage.S1_LIQUIDATION, ist(1, 10, 5), 35_00_000, "EVT-P1-FD"),
    stage(Stage.S2_POOLING, ist(2, 11, 0), 6_00_000, "EVT-P1-POOL-1"),
    stage(Stage.S2_POOLING, ist(2, 11, 30), 11_00_000, "EVT-P1-POOL-2"),
    stage(Stage.S3_NEW_PAYEE, ist(3, 9, 12), None, "EVT-P1-PAYEE"),
)

HERO_CALL_DAY2 = CallSignal(
    call_type=CallType.VIDEO, caller_known=False, duration_min=190, observed_at=ist(2, 18, 40)
)
HERO_CALL_DAY3_MORNING = CallSignal(
    call_type=CallType.VIDEO, caller_known=False, duration_min=185, observed_at=ist(3, 9, 5)
)
HERO_CALL_DAY3 = CallSignal(
    call_type=CallType.VIDEO, caller_known=False, duration_min=315, observed_at=ist(3, 11, 15)
)


def hero_input(
    *,
    fri: FriRating | None = FriRating.HIGH,
    call: CallSignal | None = HERO_CALL_DAY3,
    teller: tuple[TellerItem, ...] = (),
    active_contact: bool = True,
) -> AssessmentInput:
    return AssessmentInput(
        customer_id="cust-0007",
        now=ist(3, 11, 20),
        baseline=baseline(40_000),
        episode_stages=HERO_STAGES,
        transfer=TransferFacts(
            transfer_ref="TRF-P1-0001",
            amount_paise=rupees(46_00_000),
            rail=Rail.RTGS,
            channel=Channel.BRANCH,
            initiated_at=ist(3, 11, 20),
            source_account_balance_paise=rupees(47_00_000),
            payee=PayeeFacts(
                payee_id="PAY-0007-03",
                payee_ref="PAY-0007-03",
                added_at=ist(3, 9, 12),
                prior_successful_transfers=0,
            ),
        ),
        signals=Signals(
            fri_rating=fri,
            fri_linked_msisdn_last4="0193" if fri else None,
            call=call,
            teller_items=teller,
        ),
        has_active_trusted_contact=active_contact,
    )


# ---------- N1: Mr. Iqbal (fictional), CUST-0012, property instalment ----------


def n1_input() -> AssessmentInput:
    t = datetime(2026, 10, 10, 11, 0, tzinfo=IST)
    return AssessmentInput(
        customer_id="cust-0012",
        now=t,
        baseline=baseline(5_00_000),
        episode_stages=(
            stage(Stage.S1_LIQUIDATION, t - timedelta(days=2), 30_00_000),
            stage(Stage.S2_POOLING, t - timedelta(days=1), 10_00_000),
        ),
        transfer=TransferFacts(
            transfer_ref="TRF-N1-0001",
            amount_paise=rupees(40_00_000),
            rail=Rail.RTGS,
            channel=Channel.NETBANKING,
            initiated_at=t,
            source_account_balance_paise=rupees(45_00_000),
            payee=PayeeFacts(
                payee_id="PAY-0012-01",
                payee_ref="PAY-0012-01",
                added_at=t - timedelta(days=730),
                prior_successful_transfers=8,
                recurring_amount_paise=rupees(5_00_000),
            ),
        ),
        has_active_trusted_contact=True,
    )


# ---------- N4: wedding, new jeweller payee ----------


def n4_input() -> AssessmentInput:
    t = datetime(2026, 11, 20, 12, 0, tzinfo=IST)
    return AssessmentInput(
        customer_id="cust-0021",
        now=t,
        baseline=baseline(60_000),
        episode_stages=(
            stage(Stage.S1_LIQUIDATION, t - timedelta(days=3), 6_00_000),
            stage(Stage.S2_POOLING, t - timedelta(days=2), 4_00_000),
            stage(Stage.S3_NEW_PAYEE, t - timedelta(hours=20)),
        ),
        transfer=TransferFacts(
            transfer_ref="TRF-N4-0001",
            amount_paise=rupees(8_00_000),
            rail=Rail.NEFT,
            channel=Channel.APP,
            initiated_at=t,
            source_account_balance_paise=rupees(15_00_000),
            payee=PayeeFacts(
                payee_id="PAY-0021-05",
                payee_ref="PAY-0021-05",
                added_at=t - timedelta(hours=20),
                prior_successful_transfers=0,
            ),
        ),
        has_active_trusted_contact=True,
    )


def to_utc(dt: datetime) -> datetime:
    return dt.astimezone(UTC)
