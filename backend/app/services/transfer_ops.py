"""Transfer state changes, only through the transition table (CLAUDE.md §7)."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import InvalidStateTransition
from app.domain.config import ScoringConfig
from app.domain.enums import CancelledReason, TransferStatus
from app.domain.transitions import TransitionNotAllowed, next_transfer_status
from app.models import Account, Transfer
from app.services import baseline_service


def move(transfer: Transfer, target: TransferStatus) -> None:
    try:
        transfer.status = next_transfer_status(transfer.status, target)
    except TransitionNotAllowed:
        raise InvalidStateTransition(
            f"The transfer is already {transfer.status.value.lower()}."
        ) from None


def execute(session: Session, transfer: Transfer, now: datetime, cfg: ScoringConfig) -> None:
    """Simulated execution: debit the source account, then refresh the baseline."""
    move(transfer, TransferStatus.EXECUTED)
    transfer.executed_at = now
    account = session.get(Account, transfer.from_account_id)
    if account is not None:
        account.balance_paise = max(0, account.balance_paise - transfer.amount_paise)
    session.flush()
    baseline_service.refresh(session, transfer.customer_id, now, cfg)


def cancel(transfer: Transfer, reason: CancelledReason) -> None:
    move(transfer, TransferStatus.CANCELLED)
    transfer.cancelled_reason = reason
