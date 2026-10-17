"""Every enum in the system. Values are identical to the DB CHECK values (DATABASE_SCHEMA §3)."""

from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "CUSTOMER"
    TELLER = "TELLER"
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"


STAFF_ROLES = (Role.TELLER, Role.OFFICER, Role.ADMIN)


class Language(StrEnum):
    EN = "en"
    TA = "ta"


class AccountType(StrEnum):
    SAVINGS = "SAVINGS"
    CURRENT = "CURRENT"
    FD = "FD"
    RD = "RD"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class Channel(StrEnum):
    APP = "APP"
    BRANCH = "BRANCH"
    NETBANKING = "NETBANKING"


class TrustedContactStatus(StrEnum):
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ConsentType(StrEnum):
    CALL_SIGNAL = "CALL_SIGNAL"
    TRUSTED_CONTACT_SHARING = "TRUSTED_CONTACT_SHARING"


class EventType(StrEnum):
    FD_CLOSED = "FD_CLOSED"
    INTERNAL_TRANSFER_IN = "INTERNAL_TRANSFER_IN"
    PAYEE_ADDED = "PAYEE_ADDED"
    TRUSTED_CONTACT_CHANGED = "TRUSTED_CONTACT_CHANGED"
    ROUTINE_DEBIT = "ROUTINE_DEBIT"
    ROUTINE_CREDIT = "ROUTINE_CREDIT"


class Stage(StrEnum):
    S1_LIQUIDATION = "S1_LIQUIDATION"
    S2_POOLING = "S2_POOLING"
    S3_NEW_PAYEE = "S3_NEW_PAYEE"
    S4_HIGH_VALUE = "S4_HIGH_VALUE"


EVENT_STAGES = (Stage.S1_LIQUIDATION, Stage.S2_POOLING, Stage.S3_NEW_PAYEE)
STAGE_ORDER = (Stage.S1_LIQUIDATION, Stage.S2_POOLING, Stage.S3_NEW_PAYEE, Stage.S4_HIGH_VALUE)


class Rail(StrEnum):
    RTGS = "RTGS"
    NEFT = "NEFT"
    IMPS = "IMPS"
    UPI = "UPI"


class TransferStatus(StrEnum):
    PENDING = "PENDING"
    WARNED = "WARNED"
    HELD = "HELD"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"


class CancelledReason(StrEnum):
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    OFFICER_CANCELLED = "OFFICER_CANCELLED"
    CONTACT_REPORTED_SCAM_OFFICER_CONFIRMED = "CONTACT_REPORTED_SCAM_OFFICER_CONFIRMED"


class BaselineConfidence(StrEnum):
    OK = "OK"
    LOW = "LOW"


class EpisodeStatus(StrEnum):
    OPEN = "OPEN"
    EXPIRED = "EXPIRED"
    CLOSED_BENIGN = "CLOSED_BENIGN"
    CLOSED_CONFIRMED_RISK = "CLOSED_CONFIRMED_RISK"


class SignalType(StrEnum):
    CALL_RISK = "CALL_RISK"
    TELLER_CHECKLIST = "TELLER_CHECKLIST"


class SignalSource(StrEnum):
    DEVICE_SIMULATED = "DEVICE_SIMULATED"
    TELLER = "TELLER"


class CallType(StrEnum):
    VOICE = "VOICE"
    VIDEO = "VIDEO"


class TellerItem(StrEnum):
    ON_CALL = "ON_CALL"
    DISTRESSED = "DISTRESSED"
    FOLLOWING_INSTRUCTIONS = "FOLLOWING_INSTRUCTIONS"
    MENTIONS_AUTHORITY = "MENTIONS_AUTHORITY"


class AssessmentTrigger(StrEnum):
    INITIAL = "INITIAL"
    TELLER_CHECKLIST = "TELLER_CHECKLIST"
    SIGNAL_UPDATE = "SIGNAL_UPDATE"


class Tier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


TIER_ORDER = (Tier.LOW, Tier.MEDIUM, Tier.HIGH, Tier.VERY_HIGH)


class Decision(StrEnum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    HOLD = "HOLD"


DECISION_ORDER = (Decision.ALLOW, Decision.WARN, Decision.HOLD)


class FriRating(StrEnum):
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class HoldTier(StrEnum):
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class HoldStatus(StrEnum):
    AWAITING_CONTACT = "AWAITING_CONTACT"
    AWAITING_OFFICER = "AWAITING_OFFICER"
    RELEASED = "RELEASED"
    CANCELLED = "CANCELLED"


class ContactResponse(StrEnum):
    CONFIRM_GENUINE = "CONFIRM_GENUINE"
    REPORT_SUSPICIOUS = "REPORT_SUSPICIOUS"
    CANNOT_REACH = "CANNOT_REACH"


class ResolvedByType(StrEnum):
    TRUSTED_CONTACT = "TRUSTED_CONTACT"
    OFFICER = "OFFICER"
    CUSTOMER = "CUSTOMER"


class DeliveryChannel(StrEnum):
    CONSOLE = "CONSOLE"
    SMS = "SMS"
    TELEGRAM = "TELEGRAM"


class DeliveryStatus(StrEnum):
    QUEUED = "QUEUED"
    SENT = "SENT"
    FAILED = "FAILED"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    FILED_EXTERNALLY = "FILED_EXTERNALLY"


class NarrativeSource(StrEnum):
    TEMPLATE = "TEMPLATE"
    LLM = "LLM"
    EDITED = "EDITED"


class ActorType(StrEnum):
    STAFF = "STAFF"
    CUSTOMER = "CUSTOMER"
    TRUSTED_CONTACT = "TRUSTED_CONTACT"
    SERVICE = "SERVICE"
    SYSTEM = "SYSTEM"


class OfficerDecision(StrEnum):
    RELEASE = "RELEASE"
    CANCEL_TRANSFER = "CANCEL_TRANSFER"
    KEEP_HOLDING = "KEEP_HOLDING"
