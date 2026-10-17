"""Assessment latency check (NFR-01, T-046): p95 ≤ 300 ms for POST /transfers/assess.

    uv run python -m sim.bench --n 500 --concurrency 10

Runs against a live server (uvicorn, 1 worker) seeded with seed 42: background customers send
routine transfers to established payees. Real HTTP over localhost.
"""

import argparse
import asyncio
import random
import statistics
import time
import uuid

import httpx

from app.core.settings import get_settings
from sim.generator import BASE, generate
from sim.scenarios.schema import load_all


def _requests(n: int) -> list[dict[str, object]]:
    scenarios = load_all()
    taken = {s.customer.ref for s in scenarios.values()}
    customers = [
        g.spec for g in generate(42, scenarios) if g.spec.ref not in taken and g.spec.payees
    ]
    rng = random.Random(7)
    run = uuid.uuid4().hex[:6]
    out = []
    for i in range(n):
        spec = rng.choice(customers)
        account = next(a for a in spec.accounts if a.type in ("SAVINGS", "CURRENT"))
        out.append(
            {
                "transfer_ref": f"BENCH-{run}-{i:04d}",
                "customer_ref": spec.ref,
                "from_account": account.masked,
                "payee_ref": rng.choice(spec.payees).ref,
                "amount_paise": max(
                    100_000, round(spec.median_outbound_rupees * rng.uniform(0.3, 2)) * 100
                ),
                "rail": "NEFT",
                "channel": "NETBANKING",
                "initiated_at": BASE.replace(hour=12).isoformat(),
            }
        )
    return out


async def bench(
    base_url: str, service_key: str, n: int, concurrency: int
) -> dict[str, float | int]:
    bodies = _requests(n)
    timings: list[float] = []
    errors = 0
    semaphore = asyncio.Semaphore(concurrency)
    headers = {"X-Thunai-Service-Key": service_key}
    async with httpx.AsyncClient(base_url=base_url, timeout=30, headers=headers) as client:
        await client.post("/transfers/assess", json=bodies[0])  # warm-up, not timed

        async def one(body: dict[str, object]) -> None:
            nonlocal errors
            async with semaphore:
                started = time.perf_counter()
                r = await client.post("/transfers/assess", json=body)
                timings.append((time.perf_counter() - started) * 1000)
                if r.status_code != 200:
                    errors += 1

        await asyncio.gather(*(one(b) for b in bodies[1:]))
    timings.sort()
    return {
        "n": len(timings),
        "concurrency": concurrency,
        "errors": errors,
        "p50_ms": round(statistics.median(timings), 1),
        "p95_ms": round(timings[int(0.95 * (len(timings) - 1))], 1),
        "max_ms": round(timings[-1], 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Assessment latency benchmark (NFR-01).")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()
    settings = get_settings()
    result = asyncio.run(
        bench(
            args.base_url or settings.api_base_url,
            settings.service_api_key,
            args.n,
            args.concurrency,
        )
    )
    verdict = "PASS" if result["p95_ms"] <= 300 and not result["errors"] else "FAIL"
    summary = (
        f"{result['n']} assessments, concurrency {result['concurrency']}: "
        f"p50 {result['p50_ms']} ms, p95 {result['p95_ms']} ms, max {result['max_ms']} ms, "
        f"errors {result['errors']} → NFR-01 {verdict}"
    )
    print(summary)  # noqa: T201


if __name__ == "__main__":
    main()
