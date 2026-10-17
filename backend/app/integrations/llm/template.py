"""Template narrative for the report draft (FR-15). Deterministic; the LLM path falls back here.

Neutral wording: "beneficiary account", never "fraudster" (SECURITY §11.1).
"""

from typing import Any

from app.domain.money import format_inr


def render_narrative(facts: dict[str, Any]) -> str:
    tx = facts["transaction"]
    parts = [
        f"On {facts['initiated_at_display']}, the customer ({facts['customer_name']}) requested a "
        f"{tx['rail']} transfer of {format_inr(tx['amount_paise'])} from account "
        f"{tx['from_account_masked']} at the {facts['channel_display']} to a beneficiary account "
        f"{tx['beneficiary_account_masked']} at {tx['beneficiary_bank']} (IFSC "
        f"{tx['beneficiary_ifsc']}). The beneficiary had been added {facts['payee_age_display']} "
        "earlier."
    ]
    if facts["timeline"]:
        steps = "; ".join(f"{t['at_display']}: {t['what']}" for t in facts["timeline"])
        parts.append(f"Account activity before the request: {steps}.")
    parts.append(
        f"The transfer was paused for the customer's safety and its status is: {tx['status']}."
    )
    reported = facts.get("customer_reported") or {}
    if reported.get("claimed_agency"):
        parts.append(
            f"The customer said the caller claimed to be from {reported['claimed_agency']}."
        )
    if reported.get("platform"):
        parts.append(f"Contact was made through {reported['platform']}.")
    if reported.get("scammer_numbers_given_by_customer"):
        numbers = ", ".join(reported["scammer_numbers_given_by_customer"])
        parts.append(f"Numbers the customer said were used to contact them: {numbers}.")
    parts.append("This draft was prepared from bank records for review by the branch officer.")
    return " ".join(parts)
