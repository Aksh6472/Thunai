"""T-019: dashboard summary, alert queue, customers, query budget (≤ 5 per request)."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.domain.enums import Role
from app.repositories import customers
from tests.db_factories import hero_world
from tests.hero_api import HERO_EVENTS
from tests.scenario_helpers import hero_hold, staff_headers, wedding_hold

pytestmark = pytest.mark.anyio


@contextmanager
def count_queries(db: Session) -> Iterator[list[str]]:
    statements: list[str] = []
    engine = db.get_bind().engine

    def before(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        if not statement.lstrip().upper().startswith(("SAVEPOINT", "RELEASE", "ROLLBACK")):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", before)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", before)


async def test_summary(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    await wedding_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    s = (await client.get("/api/v1/dashboard/summary", headers=officer)).json()
    assert (s["active_holds"], s["awaiting_officer"], s["awaiting_contact"]) == (2, 1, 1)
    assert s["amount_on_hold_paise"] == 460000000 + 80000000
    assert s["data_label"] == "SYNTHETIC"


async def test_alerts_sorted_by_urgency_and_include_watchlist(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await wedding_hold(client, db, test_settings, service_headers)
    await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    items = (await client.get("/api/v1/alerts", headers=officer)).json()["items"]
    kinds = [(i["kind"], i["tier"]) for i in items]
    assert kinds[0] == ("HOLD", "VERY_HIGH")
    assert ("HOLD", "HIGH") in kinds
    assert any(k == "WATCH" for k, _ in kinds)
    watch_only = (await client.get("/api/v1/alerts?kind=WATCH", headers=officer)).json()["items"]
    assert all(i["kind"] == "WATCH" for i in watch_only)


async def test_alert_pagination_is_stable(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await wedding_hold(client, db, test_settings, service_headers)
    await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    full = [i["id"] for i in (await client.get("/api/v1/alerts", headers=officer)).json()["items"]]
    paged, cursor = [], None
    while True:
        url = "/api/v1/alerts?limit=1" + (f"&cursor={cursor}" if cursor else "")
        page = (await client.get(url, headers=officer)).json()
        paged += [i["id"] for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert paged == full


async def test_watchlist_without_transfer(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    hero_world(db, test_settings)
    for e in HERO_EVENTS:
        await client.post("/api/v1/events", json=e, headers=service_headers)
    from tests.hero_api import HERO_CALL_DAY2

    await client.post("/api/v1/signals/call", json=HERO_CALL_DAY2, headers=service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    items = (await client.get("/api/v1/alerts", headers=officer)).json()["items"]
    assert [(i["kind"], i["tier"], i["watch_score"]) for i in items] == [("WATCH", "MEDIUM", 40)]


async def test_customer_search_risk_and_timeline(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    found = (await client.get("/api/v1/customers?search=kamala", headers=officer)).json()["items"]
    assert [c["external_ref"] for c in found] == ["CUST-0007"]
    cid = found[0]["id"]
    risk = (await client.get(f"/api/v1/customers/{cid}/risk", headers=officer)).json()
    assert risk["baseline"]["median_outbound_paise"] == 4000000
    assert risk["recent_assessments"][0]["tier"] == "VERY_HIGH"
    assert risk["trusted_contact"]["active"] is True
    timeline = (
        await client.get(f"/api/v1/customers/{cid}/timeline?days=14", headers=officer)
    ).json()
    kinds = {t["kind"] for t in timeline}
    assert {"EVENT", "SIGNAL", "ASSESSMENT"} <= kinds
    assert timeline == sorted(timeline, key=lambda t: t["at"])


async def test_teller_cannot_read_summary_but_can_read_alerts(
    client: httpx.AsyncClient, db: Session, test_settings: Settings
) -> None:
    teller = staff_headers(db, test_settings, "teller.priya", Role.TELLER)
    assert (await client.get("/api/v1/dashboard/summary", headers=teller)).status_code == 403
    assert (await client.get("/api/v1/alerts", headers=teller)).status_code == 200


async def test_other_branch_customer_is_404(
    client: httpx.AsyncClient, db: Session, test_settings: Settings, service_headers: dict[str, str]
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    customer = customers.by_ref(db, "CUST-0007")
    assert customer is not None
    other = staff_headers(db, test_settings, "officer.blr", Role.OFFICER, branch="BLR001")
    assert (
        await client.get(f"/api/v1/customers/{customer.id}/risk", headers=other)
    ).status_code == 404


@pytest.mark.parametrize(
    "path", ["/api/v1/holds", "/api/v1/alerts", "/api/v1/dashboard/summary", "/api/v1/teller/queue"]
)
async def test_read_endpoints_stay_within_five_queries(
    client: httpx.AsyncClient,
    db: Session,
    test_settings: Settings,
    service_headers: dict[str, str],
    path: str,
) -> None:
    await hero_hold(client, db, test_settings, service_headers)
    await wedding_hold(client, db, test_settings, service_headers)
    officer = staff_headers(db, test_settings, "officer.rao", Role.OFFICER)
    with count_queries(db) as statements:
        assert (await client.get(path, headers=officer)).status_code == 200
    assert len(statements) <= 5, statements
