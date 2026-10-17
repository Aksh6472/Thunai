"""EN/TA text for every reason code (FR-08). Staff-facing; customers see one generic line (ADR-013).

Kept as Python (not YAML) so the domain stays free of file I/O.
Tamil: DRAFT, PENDING NATIVE REVIEW (T-038, NFR-07). Wording avoids "fraud", "victim", "blocked".
"""

from collections.abc import Callable
from typing import Any

from app.domain.money import format_inr

TAMIL_REVIEWED_BY_NATIVE_SPEAKER = False

Evidence = dict[str, Any]
Renderer = Callable[[Evidence], tuple[str, str]]

STAGE_NAMES = {
    "S1_LIQUIDATION": ("FD broken early", "நிலை வைப்பு முன்கூட்டியே முடிப்பு"),
    "S2_POOLING": ("funds pooled", "நிதி ஒரே கணக்கில் சேர்ப்பு"),
    "S3_NEW_PAYEE": ("new payee", "புதிய பெறுநர்"),
    "S4_HIGH_VALUE": ("large transfer", "பெரிய பரிமாற்றம்"),
}

FRI_RATING_NAMES = {
    "MEDIUM": ("MEDIUM", "நடுத்தர ஆபத்து"),
    "HIGH": ("HIGH", "அதிக ஆபத்து"),
    "VERY_HIGH": ("VERY HIGH", "மிக அதிக ஆபத்து"),
}


def _age(hours: int) -> tuple[str, str]:
    if hours < 1:
        return "less than an hour", "ஒரு மணி நேரத்திற்கும் குறைவான நேரத்திற்கு"
    if hours < 48:
        return f"{hours} hours", f"{hours} மணி நேரத்திற்கு"
    days = hours // 24
    return f"{days} days", f"{days} நாட்களுக்கு"


def _fd(e: Evidence) -> tuple[str, str]:
    amount = format_inr(int(e.get("amount_paise") or 0)) if e.get("amount_paise") else ""
    what_en = f"Fixed deposit of {amount}" if amount else "A fixed deposit"
    what_ta = f"{amount} நிலை வைப்பு" if amount else "ஒரு நிலை வைப்பு"
    en, ta = f"{what_en} was closed before maturity.", f"{what_ta} முதிர்வுக்கு முன்பே முடிக்கப்பட்டது."
    if e.get("habitual"):
        en += " The customer has done this before, so it counts less."
        ta += " வாடிக்கையாளர் இதை முன்பும் செய்துள்ளார், எனவே குறைவாகக் கணக்கிடப்படுகிறது."
    return en, ta


def _pooled(e: Evidence) -> tuple[str, str]:
    amount = format_inr(int(e.get("amount_paise") or 0))
    hours = e.get("window_hours", 72)
    return (
        f"{amount} was moved into one account from the customer's other accounts within "
        f"{hours} hours.",
        f"{hours} மணி நேரத்திற்குள் வாடிக்கையாளரின் மற்ற கணக்குகளிலிருந்து {amount} ஒரே கணக்கில் சேர்க்கப்பட்டது.",
    )


def _new_payee(e: Evidence) -> tuple[str, str]:
    age_en, age_ta = _age(int(e.get("payee_age_minutes", 0)) // 60)
    return (
        f"Payee was added {age_en} before this transfer.",
        f"இந்த பரிமாற்றத்திற்கு {age_ta} முன்புதான் பெறுநர் சேர்க்கப்பட்டார்.",
    )


def _high_value(e: Evidence) -> tuple[str, str]:
    amount = format_inr(int(e["amount_paise"]))
    median = format_inr(int(e["median_outbound_paise"]))
    multiple = e["multiple_of_median"]
    return (
        f"{amount} is {multiple}× this customer's usual transfer ({median}).",
        f"{amount} என்பது இந்த வாடிக்கையாளரின் வழக்கமான பரிமாற்றத்தின் ({median}) {multiple} மடங்கு.",
    )


def _drain(e: Evidence) -> tuple[str, str]:
    pct = e["percent_of_balance"]
    return (
        f"This transfer would take {pct}% of the account balance.",
        f"இந்தப் பரிமாற்றம் கணக்கு இருப்பில் {pct}% ஐ எடுத்துவிடும்.",
    )


def _sequence(e: Evidence) -> tuple[str, str]:
    stages = e.get("stages", [])
    en_steps = " → ".join(STAGE_NAMES[s][0] for s in stages)
    ta_steps = " → ".join(STAGE_NAMES[s][1] for s in stages)
    n = e.get("count", len(stages))
    return (
        f"{n} warning steps happened in order: {en_steps}.",
        f"{n} எச்சரிக்கை படிகள் வரிசையாக நடந்தன: {ta_steps}.",
    )


def _fri(e: Evidence) -> tuple[str, str]:
    en_name, ta_name = FRI_RATING_NAMES[e["rating"]]
    return (
        f"The payee's linked mobile number is rated {en_name} risk by DoT FRI (simulated).",
        f"பெறுநரின் இணைக்கப்பட்ட மொபைல் எண் DoT FRI-யால் {ta_name} என மதிப்பிடப்பட்டுள்ளது "
        "(உருவகப்படுத்தப்பட்டது).",
    )


def _fri_unavailable(_: Evidence) -> tuple[str, str]:
    return (
        "The FRI rating could not be checked in time (no points added).",
        "FRI மதிப்பீட்டை நேரத்தில் சரிபார்க்க முடியவில்லை (புள்ளிகள் சேர்க்கப்படவில்லை).",
    )


def _call(e: Evidence) -> tuple[str, str]:
    minutes = e["duration_min"]
    video = e.get("call_type") == "VIDEO"
    kind_en, kind_ta = ("video", "வீடியோ") if video else ("voice", "குரல்")
    return (
        f"On a {kind_en} call with an unknown caller for {minutes} minutes "
        "(consented flag, simulated).",
        f"தெரியாத நபருடன் {minutes} நிமிடங்களாக {kind_ta} அழைப்பில் உள்ளார் (ஒப்புதலுடன், உருவகப்படுத்தப்பட்டது).",
    )


def _teller(en: str, ta: str) -> Renderer:
    def render(e: Evidence) -> tuple[str, str]:
        if e.get("capped"):
            return (
                f"{en} (teller total capped at 30).",
                f"{ta} (காசாளர் புள்ளிகள் 30 வரை மட்டும்).",
            )
        return f"{en}.", f"{ta}."

    return render


def _contact_changed(e: Evidence) -> tuple[str, str]:
    age_en, age_ta = _age(int(e.get("changed_hours_ago", 0)))
    return (
        f"The trusted contact was added or changed {age_en} ago.",
        f"நம்பகமான தொடர்பு {age_ta} முன்பு சேர்க்கப்பட்டது அல்லது மாற்றப்பட்டது.",
    )


def _established(e: Evidence) -> tuple[str, str]:
    days, count = e["payee_age_days"], e["prior_successful_transfers"]
    return (
        f"Established payee: added {days} days ago, with {count} earlier successful transfers.",
        f"நிறுவப்பட்ட பெறுநர்: {days} நாட்களுக்கு முன்பு சேர்க்கப்பட்டார், இதற்கு முன் {count} "
        "வெற்றிகரமான பரிமாற்றங்கள்.",
    )


def _regular(e: Evidence) -> tuple[str, str]:
    amount = format_inr(int(e["recurring_amount_paise"]))
    return (
        f"The amount matches this payee's regular payment ({amount}).",
        f"தொகை இந்தப் பெறுநருக்கான வழக்கமான கொடுப்பனவுடன் ({amount}) பொருந்துகிறது.",
    )


def _low_confidence(e: Evidence) -> tuple[str, str]:
    days, count = e.get("history_days", 0), e.get("qualifying_transfer_count", 0)
    return (
        f"Limited history ({days} days, {count} transfers): the usual amount is estimated.",
        f"வரலாறு குறைவு ({days} நாட்கள், {count} பரிமாற்றங்கள்): வழக்கமான தொகை மதிப்பிடப்பட்டது.",
    )


RENDERERS: dict[str, Renderer] = {
    "FD_PREMATURE_CLOSURE": _fd,
    "FUNDS_POOLED": _pooled,
    "NEW_PAYEE": _new_payee,
    "HIGH_VALUE_TO_PAYEE": _high_value,
    "BALANCE_DRAIN": _drain,
    "STAGE_SEQUENCE": _sequence,
    "FRI_RISK": _fri,
    "FRI_UNAVAILABLE": _fri_unavailable,
    "LONG_CALL_UNKNOWN": _call,
    "TELLER_ON_CALL": _teller(
        "Teller: the customer is on a phone or video call while transacting",
        "காசாளர்: பரிவர்த்தனையின் போது வாடிக்கையாளர் தொலைபேசி அல்லது வீடியோ அழைப்பில் உள்ளார்",
    ),
    "TELLER_DISTRESSED": _teller(
        "Teller: the customer appears anxious, frightened or confused",
        "காசாளர்: வாடிக்கையாளர் பதற்றமாக, பயமாக அல்லது குழப்பமாக காணப்படுகிறார்",
    ),
    "TELLER_FOLLOWING_INSTRUCTIONS": _teller(
        "Teller: the customer appears to be following someone else's instructions",
        "காசாளர்: வாடிக்கையாளர் வேறொருவரின் அறிவுறுத்தல்களைப் பின்பற்றுவதாகத் தெரிகிறது",
    ),
    "TELLER_MENTIONS_AUTHORITY": _teller(
        "Teller: the customer mentions police, CBI, ED, customs, a court or an 'arrest'",
        "காசாளர்: வாடிக்கையாளர் காவல்துறை, சிபிஐ, அமலாக்கத்துறை, சுங்கம், நீதிமன்றம் அல்லது 'கைது' "
        "பற்றிக் குறிப்பிடுகிறார்",
    ),
    "TRUSTED_CONTACT_RECENTLY_CHANGED": _contact_changed,
    "ESTABLISHED_PAYEE": _established,
    "MATCHES_REGULAR_PATTERN": _regular,
    "BASELINE_LOW_CONFIDENCE": _low_confidence,
}


def render(code: str, evidence: Evidence) -> tuple[str, str]:
    return RENDERERS[code](evidence)
