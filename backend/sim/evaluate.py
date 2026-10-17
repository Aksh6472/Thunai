"""Evaluation harness (FR-18, T-030, AI_DESIGN §7). Synthetic data only.

    uv run python -m sim.evaluate --seeds 100-299 --out ../reports/eval/

Runs every scenario family per seed through the API at infinite speed (httpx ASGITransport:
HTTP semantics, no network) against the test database, then writes Markdown and JSON reports.
Tune only on seeds 0–99; report on 100–299 (AI_DESIGN §7.2). P6 and N5 are held out.
"""

import argparse
import asyncio
import json
import math
import random
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from alembic import command
from alembic.config import Config

from app.core.settings import BACKEND_DIR, Settings, load_settings
from app.main import create_app
from sim import metrics
from sim.client import SimClient
from sim.generator import BASE, GeneratedCustomer, generate
from sim.metrics import Record
from sim.plan import plan_scenario
from sim.replay import run_steps
from sim.scenarios.schema import Scenario, load_all
from sim.seed import seed_database_url

DISCLAIMER = (
    "Synthetic data generated from public case patterns. Not evidence of real-world performance."
)


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            seeds.extend(range(lo, hi + 1))
        else:
            seeds.append(int(part))
    return seeds


def eval_settings() -> Settings:
    base = load_settings()
    url = base.test_database_url or base.database_url
    return load_settings(
        env="test", demo_mode=True, database_url=url, notifier="console", log_level="ERROR"
    )


def migrate(settings: Settings) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["url"] = settings.database_url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")


def _record(
    seed: int,
    scenario: Scenario | None,
    body: dict[str, Any],
    *,
    target: bool,
    first: bool,
    amount: int,
    ms: float,
) -> Record:
    return Record(
        seed=seed,
        family=scenario.id if scenario else "BG",
        label=scenario.label if scenario else "genuine",
        target=target,
        amount_paise=amount,
        decision=body["decision"],
        tier=body["tier"],
        hold_status=_initial_hold_status(body),
        reasons=body.get("reasons", []),
        raw_score=body.get("raw_score", 0),
        first_target=first,
        latency_ms=ms,
    )


def _initial_hold_status(body: dict[str, Any]) -> str | None:
    """Policy (AI_DESIGN §6.3): VERY_HIGH or no active contact starts with an officer."""
    if body["decision"] != "HOLD":
        return None
    if body["tier"] == "VERY_HIGH" or "NO_ACTIVE_TRUSTED_CONTACT" in body.get(
        "overrides_applied", []
    ):
        return "AWAITING_OFFICER"
    return "AWAITING_CONTACT"


async def run_seed(
    app: Any, settings: Settings, seed: int, scenarios: dict[str, Scenario], background: bool
) -> list[Record]:
    seed_database_url(settings.database_url, settings, seed)
    records: list[Record] = []
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://eval/api/v1", timeout=60
    ) as http:
        client = SimClient(http, settings.service_api_key)
        teller = ("teller.priya", settings.seed_password or "")
        for scenario in scenarios.values():
            steps = plan_scenario(scenario, seed)
            started = time.perf_counter()
            results = await run_steps(client, steps, speed=math.inf, teller_login=teller)
            elapsed = (time.perf_counter() - started) * 1000 / max(1, len(results))
            seen_target = False
            for r in results:
                if r.step.kind != "transfer":
                    continue
                first = r.step.target and not seen_target
                seen_target = seen_target or r.step.target
                records.append(
                    _record(
                        seed,
                        scenario,
                        r.body,
                        target=r.step.target,
                        first=first,
                        amount=r.step.body["amount_paise"],
                        ms=elapsed,
                    )
                )
        if background:
            records += await _background(client, seed, scenarios)
    return records


async def _background(client: SimClient, seed: int, scenarios: dict[str, Scenario]) -> list[Record]:
    """One routine transfer per background customer, to an established payee (genuine)."""
    rng = random.Random(f"{seed}:background")
    taken = {s.customer.ref for s in scenarios.values()}
    records = []
    population: list[GeneratedCustomer] = generate(seed, scenarios)
    for g in population:
        spec = g.spec
        if spec.ref in taken or not spec.payees:
            continue
        payee = rng.choice(spec.payees)
        account = next(a for a in spec.accounts if a.type in ("SAVINGS", "CURRENT"))
        amount = max(100_000, round(spec.median_outbound_rupees * rng.uniform(0.3, 2.5)) * 100)
        amount = min(amount, account.balance_rupees * 100)
        if amount <= 0:
            continue
        when = BASE.replace(hour=12)  # day 1, noon IST
        await client.set_clock(when, 0.0, "BG")
        started = time.perf_counter()
        r = await client.post(
            "/transfers/assess",
            {
                "transfer_ref": f"BG-{spec.ref}-S{seed}",
                "customer_ref": spec.ref,
                "from_account": account.masked,
                "payee_ref": payee.ref,
                "amount_paise": amount,
                "rail": "NEFT",
                "channel": "NETBANKING",
                "initiated_at": when.isoformat(),
            },
        )
        ms = (time.perf_counter() - started) * 1000
        if r.status_code == 200:
            records.append(
                _record(seed, None, r.json(), target=False, first=False, amount=amount, ms=ms)
            )
    return records


def git_commit() -> str:
    """Short SHA of HEAD for the report (a fixed, read-only git command)."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def summarise(
    records: list[Record], seeds: list[int], config_version: str, commit: str, held_out: list[str]
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "disclaimer": DISCLAIMER,
        "config_version": config_version,
        "git_commit": commit,
        "seeds": f"{seeds[0]}-{seeds[-1]}"
        if seeds == list(range(seeds[0], seeds[-1] + 1))
        else seeds,
        "n_seeds": len(seeds),
        "held_out_families": held_out,
        "metrics": {
            "interception": metrics.interception(records).as_dict(),
            "amount_protected": metrics.amount_protected(records),
            "false_hold": metrics.false_hold(records).as_dict(),
            "genuine_warning": metrics.genuine_warning(records).as_dict(),
            "explanation_coverage": metrics.explanation_coverage(records).as_dict(),
            "modelled_added_delay_min": metrics.modelled_delay_minutes(records, seed=seeds[0]),
            "in_process_assessment_latency": metrics.latency(records),
        },
        "per_family": metrics.per_family(records),
        "tier_confusion": metrics.tier_confusion(records),
        "reason_frequency": metrics.reason_frequency(records),
        "n_records": len(records),
    }


def pct(rate: dict[str, Any]) -> str:
    low, high = rate["ci95"]
    return f"{rate['rate'] * 100:.1f}% ({rate['k']}/{rate['n']}; 95% CI {low * 100:.1f}–{high * 100:.1f}%)"


def to_markdown(s: dict[str, Any]) -> str:
    m = s["metrics"]
    delay = m["modelled_added_delay_min"]
    lines = [
        "# Thunai evaluation report (synthetic)",
        "",
        f"> **{s['disclaimer']}**",
        "",
        f"- Generated: {s['generated_at']}",
        f"- Scoring config: `{s['config_version']}` · git `{s['git_commit']}`",
        f"- Seeds: {s['seeds']} ({s['n_seeds']} seeds; tuning seeds 0–99 were never used here)",
        f"- Held-out families (never used for tuning): {', '.join(s['held_out_families'])}",
        f"- Records: {s['n_records']} assessed transfers",
        "",
        "## Headline metrics (PRD §9)",
        "",
        "| Metric | Result | Target |",
        "|---|---|---|",
        f"| Coercion interception rate (first scammer transfer HELD) | {pct(m['interception'])} | ≥ 90% |",
        f"| Amount-weighted protection | {m['amount_protected']['share'] * 100:.1f}% of rupees attempted | reported |",
        f"| False hold rate (genuine ≥ ₹2 L held) | {pct(m['false_hold'])} | ≤ 5% overall |",
        f"| Genuine warning rate (genuine ≥ ₹2 L warned) | {pct(m['genuine_warning'])} | ≤ 20% desired |",
        f"| Added delay for genuine held transfers (**modelled**, AI_DESIGN §8) | median {delay['median']} min, p90 {delay['p90']} min (n={delay['n']}) | median ≤ 15 min |",
        f"| Explanation coverage (WARN/HOLD with reasons that sum to the score) | {pct(m['explanation_coverage'])} | 100% |",
        "",
        "The delay is a model, not a measurement: contact response log-normal (median 8 min, p90 25 min), "
        "15% never respond and go to an officer after the 240 min cooling-off; holds that start with an officer "
        "are counted at 240 min.",
        "",
        "## Per family",
        "",
        "| Family | Label | n | ALLOW | WARN | HOLD | Rate |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in s["per_family"]:
        metric = row.get("interception") or row.get("false_hold")
        name = "interception" if "interception" in row else "false hold (≥ ₹2 L)"
        held = " (held out)" if row["family"] in s["held_out_families"] else ""
        lines.append(
            f"| {row['family']}{held} | {row['label']} | {row['n']} | {row['ALLOW']} | {row['WARN']} | {row['HOLD']} | "
            f"{name} {pct(metric) if metric['n'] else 'n/a'} |"
        )
    lines += [
        "",
        "## Tier by label",
        "",
        "| Label | LOW | MEDIUM | HIGH | VERY_HIGH |",
        "|---|---|---|---|---|",
    ]
    for label, row in s["tier_confusion"].items():
        lines.append(
            f"| {label} | {row['LOW']} | {row['MEDIUM']} | {row['HIGH']} | {row['VERY_HIGH']} |"
        )
    lines += [
        "",
        "## Reason frequency (WARN/HOLD decisions)",
        "",
        "| Reason | Count |",
        "|---|---|",
    ]
    lines += [f"| {code} | {count} |" for code, count in s["reason_frequency"]]
    lat = m["in_process_assessment_latency"]
    lines += [
        "",
        "## Notes",
        "",
        f"- In-process timing per request (ASGITransport, includes DB work, not a network benchmark): p50 {lat.get('p50_ms')} ms, p95 {lat.get('p95_ms')} ms. NFR-01 is measured separately by `sim/bench.py`.",
        "- BG = one routine transfer per background customer to an established payee (genuine).",
        "- Numbers may only be quoted with the synthetic label and this report as the source (CLAUDE.md §15).",
        "",
    ]
    return "\n".join(lines)


async def evaluate(seeds: list[int], out_dir: Path, *, background: bool = True) -> dict[str, Any]:
    settings = eval_settings()
    migrate(settings)
    app = create_app(settings)
    scenarios = load_all()
    records: list[Record] = []
    started = time.perf_counter()
    for i, seed in enumerate(seeds):
        records += await run_seed(app, settings, seed, scenarios, background)
        if (i + 1) % 20 == 0 or i + 1 == len(seeds):
            print(f"  {i + 1}/{len(seeds)} seeds · {time.perf_counter() - started:.0f}s")  # noqa: T201
    commit = git_commit()
    summary = summarise(
        records,
        seeds,
        app.state.scoring_config.config_version,
        commit,
        [s.id for s in scenarios.values() if s.held_out],
    )
    summary["runtime_seconds"] = round(time.perf_counter() - started, 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"{stamp}.md").write_text(to_markdown(summary), encoding="utf-8")
    (out_dir / f"{stamp}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    summary["files"] = [str(out_dir / f"{stamp}.md"), str(out_dir / f"{stamp}.json")]
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the synthetic evaluation (FR-18).")
    parser.add_argument("--seeds", default="100-299")
    parser.add_argument("--out", default=str(BACKEND_DIR.parent / "reports" / "eval"))
    parser.add_argument("--no-background", action="store_true")
    args = parser.parse_args()
    seeds = parse_seeds(args.seeds)
    summary = asyncio.run(evaluate(seeds, Path(args.out), background=not args.no_background))
    m = summary["metrics"]
    print(  # noqa: T201
        f"Interception {pct(m['interception'])} · false hold {pct(m['false_hold'])} · "
        f"{summary['runtime_seconds']}s → {summary['files'][0]}"
    )


if __name__ == "__main__":
    main()
