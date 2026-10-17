"""SQLAlchemy ORM models. Import from here so Alembic sees every table."""

from app.models.activity import (
    AccountEvent,
    CustomerBaseline,
    RiskAssessment,
    RiskEpisode,
    Signal,
    Transfer,
)
from app.models.base import Base
from app.models.cases import AuditLog, ContactRequest, FraudReport, FriMockRating, Hold, SimState
from app.models.people import Account, Consent, Customer, Payee, StaffUser, TrustedContact

__all__ = [
    "Account",
    "AccountEvent",
    "AuditLog",
    "Base",
    "Consent",
    "ContactRequest",
    "Customer",
    "CustomerBaseline",
    "FraudReport",
    "FriMockRating",
    "Hold",
    "Payee",
    "RiskAssessment",
    "RiskEpisode",
    "Signal",
    "SimState",
    "StaffUser",
    "Transfer",
    "TrustedContact",
]
