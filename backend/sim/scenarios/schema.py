"""Scenario family schema and loader (FR-01, AI_DESIGN §7.1, T-023).

A family describes one fictional customer's starting state and a timed list of steps.
Seed 42 replays the steps exactly (the demo and golden expectations). Other seeds randomise
amounts, gaps and history length within `randomise` (AI_DESIGN §7.2).
Narrative details (age, occupation) live only in `narrative` and are never sent to the API.
"""

from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

SCENARIO_DIR = Path(__file__).resolve().parent
GOLDEN_SEED = 42


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AccountSpec(_Model):
    masked: str = Field(pattern=r"^XXXXXX\d{4}$")
    type: Literal["SAVINGS", "CURRENT", "FD", "RD"] = "SAVINGS"
    balance_rupees: int = Field(ge=0)
    maturity: date | None = None


class PayeeHistorySpec(_Model):
    ref: str
    name: str
    age_days: float = Field(gt=0)
    transfers: int = Field(ge=0, default=0)
    amount_rupees: int = Field(ge=0, default=0)
    ifsc: str = "EXMP0001234"
    masked_account: str = "XXXXXX9001"


class ContactSpec(_Model):
    name: str
    relationship: str
    language: Literal["en", "ta"] = "en"
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    age_days: float = 400


class CustomerSpec(_Model):
    ref: str = Field(pattern=r"^CUST-\d{4}$")
    display_name: str
    language: Literal["en", "ta"] = "en"
    login: str | None = None
    narrative: str = ""
    median_outbound_rupees: int = Field(gt=0)
    history_days: int = Field(ge=1, default=180)
    premature_fd_closures: int = Field(ge=0, default=0)
    accounts: list[AccountSpec]
    payees: list[PayeeHistorySpec] = Field(default_factory=list)
    trusted_contact: ContactSpec | None = None
    consents: list[Literal["CALL_SIGNAL", "TRUSTED_CONTACT_SHARING"]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _names_are_fictional(self) -> "CustomerSpec":
        if "(fictional)" not in self.display_name:
            raise ValueError(f"{self.ref}: display_name must carry the '(fictional)' suffix")
        return self


class FriSpec(_Model):
    msisdn: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    rating: Literal["MEDIUM", "HIGH", "VERY_HIGH"]


class _Step(_Model):
    day: int = Field(ge=1, le=30)
    time: str = Field(pattern=r"^\d{2}:\d{2}$")


class EventStep(_Step):
    kind: Literal["event"]
    type: Literal[
        "FD_CLOSED",
        "INTERNAL_TRANSFER_IN",
        "PAYEE_ADDED",
        "TRUSTED_CONTACT_CHANGED",
        "ROUTINE_DEBIT",
        "ROUTINE_CREDIT",
    ]
    account: str | None = None
    amount_rupees: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    scale_amount: bool = True


class CallStep(_Step):
    kind: Literal["call"]
    call_type: Literal["VOICE", "VIDEO"] = "VIDEO"
    caller_known: bool = False
    duration_min: int = Field(ge=0, le=1440)
    ended: bool = False


class TransferStep(_Step):
    kind: Literal["transfer"]
    ref: str
    from_account: str
    payee: str
    amount_rupees: int = Field(gt=0)
    rail: Literal["RTGS", "NEFT", "IMPS", "UPI"] = "RTGS"
    channel: Literal["APP", "BRANCH", "NETBANKING"] = "BRANCH"
    target: bool = False  # a transfer to the scammer's payee (coercion families)
    on_warn: Literal["CONTINUE", "CANCEL", "NONE"] = "NONE"


class TellerStep(_Step):
    kind: Literal["teller"]
    transfer_ref: str
    items: list[Literal["ON_CALL", "DISTRESSED", "FOLLOWING_INSTRUCTIONS", "MENTIONS_AUTHORITY"]]
    customer_said: str | None = None


Step = Annotated[EventStep | CallStep | TransferStep | TellerStep, Field(discriminator="kind")]


class Expected(_Model):
    decision: Literal["ALLOW", "WARN", "HOLD"]
    tier: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] | None = None
    after_teller: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] | None = None


class Randomise(_Model):
    amount_scale: tuple[float, float] = (0.3, 3.0)
    gap_scale: tuple[float, float] = (0.5, 1.5)
    history_days: tuple[int, int] = (20, 365)


class Scenario(_Model):
    id: str = Field(pattern=r"^[PN]\d$")
    title: str
    label: Literal["coercion", "genuine"]
    grounding: str
    description: str
    held_out: bool = False
    customer: CustomerSpec
    fri: list[FriSpec] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1)
    expected: Expected
    randomise: Randomise = Randomise()

    @model_validator(mode="after")
    def _consistent(self) -> "Scenario":
        accounts = {a.masked for a in self.customer.accounts}
        transfers = [s for s in self.steps if isinstance(s, TransferStep)]
        if not transfers:
            raise ValueError(f"{self.id}: needs at least one transfer step")
        for step in transfers:
            if step.from_account not in accounts:
                raise ValueError(f"{self.id}: unknown account {step.from_account}")
        if self.label == "coercion" and not any(t.target for t in transfers):
            raise ValueError(f"{self.id}: a coercion family needs a target transfer")
        order = [(s.day, s.time) for s in self.steps]
        if order != sorted(order):
            raise ValueError(f"{self.id}: steps must be in time order")
        return self


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_all(directory: Path = SCENARIO_DIR) -> dict[str, Scenario]:
    scenarios = {}
    for path in sorted(directory.glob("*.yaml")):
        scenario = load_scenario(path)
        if scenario.id in scenarios:
            raise ValueError(f"duplicate scenario id {scenario.id}")
        scenarios[scenario.id] = scenario
    refs = [s.customer.ref for s in scenarios.values()]
    if len(refs) != len(set(refs)):
        raise ValueError("each scenario needs its own customer")
    return scenarios
