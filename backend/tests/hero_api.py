"""The P1 hero scenario as raw API calls (API_SPEC §13). Used by integration and scenario tests."""

from typing import Any

import httpx

HERO_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": "EVT-P1-FD",
        "customer_ref": "CUST-0007",
        "event_type": "FD_CLOSED",
        "occurred_at": "2026-10-01T10:05:00+05:30",
        "account_ref": "XXXXXX7710",
        "amount_paise": 350000000,
        "payload": {"maturity_date": "2027-04-01", "proceeds_to_account": "XXXXXX2201"},
    },
    {
        "event_id": "EVT-P1-POOL-1",
        "customer_ref": "CUST-0007",
        "event_type": "INTERNAL_TRANSFER_IN",
        "occurred_at": "2026-10-02T11:00:00+05:30",
        "account_ref": "XXXXXX2201",
        "amount_paise": 60000000,
        "payload": {"from_account": "XXXXXX3302", "to_account": "XXXXXX2201"},
    },
    {
        "event_id": "EVT-P1-POOL-2",
        "customer_ref": "CUST-0007",
        "event_type": "INTERNAL_TRANSFER_IN",
        "occurred_at": "2026-10-02T11:30:00+05:30",
        "account_ref": "XXXXXX2201",
        "amount_paise": 50000000,
        "payload": {"from_account": "XXXXXX4403", "to_account": "XXXXXX2201"},
    },
]

HERO_CALL_DAY2 = {
    "customer_ref": "CUST-0007",
    "call_type": "VIDEO",
    "caller_known": False,
    "duration_min": 190,
    "ended_at": None,
    "observed_at": "2026-10-02T18:40:00+05:30",
}
HERO_CALL_DAY3_MORNING = {
    **HERO_CALL_DAY2,
    "duration_min": 185,
    "observed_at": "2026-10-03T09:05:00+05:30",
}
HERO_PAYEE = {
    "event_id": "EVT-P1-PAYEE",
    "customer_ref": "CUST-0007",
    "event_type": "PAYEE_ADDED",
    "occurred_at": "2026-10-03T09:12:00+05:30",
    "payload": {
        "payee_ref": "PAY-0007-03",
        "display_name": "Verification Account",
        "bank_name": "Example Bank",
        "ifsc": "EXMP0001234",
        "masked_account": "XXXXXX4821",
        "channel": "APP",
        "linked_msisdn": "+919800000193",
    },
}
HERO_CALL_DAY3 = {**HERO_CALL_DAY2, "duration_min": 315, "observed_at": "2026-10-03T11:15:00+05:30"}
HERO_TRANSFER = {
    "transfer_ref": "TRF-P1-0001",
    "customer_ref": "CUST-0007",
    "from_account": "XXXXXX2201",
    "payee_ref": "PAY-0007-03",
    "amount_paise": 460000000,
    "rail": "RTGS",
    "channel": "BRANCH",
    "initiated_at": "2026-10-03T11:20:00+05:30",
    "scenario_label": "P1",
}


async def replay_hero_until_transfer(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> list[int]:
    """Posts the P1 events and signals; returns the watch score after each stage step."""
    scores = []
    for event in HERO_EVENTS:
        r = await client.post("/api/v1/events", json=event, headers=headers)
        assert r.status_code == 202, r.text
        scores.append(r.json()["episode"]["watch_score"])
    for signal in (HERO_CALL_DAY2, HERO_CALL_DAY3_MORNING):
        r = await client.post("/api/v1/signals/call", json=signal, headers=headers)
        assert r.status_code == 202, r.text
        scores.append(r.json()["episode"]["watch_score"])
    r = await client.post("/api/v1/events", json=HERO_PAYEE, headers=headers)
    assert r.status_code == 202, r.text
    scores.append(r.json()["episode"]["watch_score"])
    r = await client.post("/api/v1/signals/call", json=HERO_CALL_DAY3, headers=headers)
    assert r.status_code == 202, r.text
    return scores
