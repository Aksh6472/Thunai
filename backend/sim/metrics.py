"""Evaluation metrics (PRD §9, AI_DESIGN §7.3, §8). Pure functions over decision records."""

import math
import random
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

HIGH_VALUE_PAISE = 20_000_000  # ₹2,00,000: "genuine high-value transfer" (PRD §9)
CONTACT_MEDIAN_MIN = 8.0  # AI_DESIGN §8 (assumption A-05, modelled, not measured)
CONTACT_P90_MIN = 25.0
CONTACT_NO_RESPONSE = 0.15
COOLING_OFF_MIN = 240.0
Z90 = 1.2815515655446004


@dataclass(frozen=True)
class Record:
    """One assessed transfer in the evaluation."""

    seed: int
    family: str  # P1..P7, N1..N6, or BG (background routine transfer)
    label: str  # coercion | genuine
    target: bool  # a transfer to the scammer's payee
    amount_paise: int
    decision: str
    tier: str
    hold_status: str | None
    reasons: list[dict[str, Any]] = field(default_factory=list)
    raw_score: int = 0
    first_target: bool = False
    latency_ms: float = 0.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class Rate:
    k: int
    n: int

    @property
    def value(self) -> float:
        return self.k / self.n if self.n else 0.0

    @property
    def ci(self) -> tuple[float, float]:
        return wilson(self.k, self.n)

    def as_dict(self) -> dict[str, Any]:
        low, high = self.ci
        return {
            "k": self.k,
            "n": self.n,
            "rate": round(self.value, 4),
            "ci95": [round(low, 4), round(high, 4)],
        }


def interception(records: list[Record]) -> Rate:
    firsts = [r for r in records if r.label == "coercion" and r.first_target]
    return Rate(sum(r.decision == "HOLD" for r in firsts), len(firsts))


def amount_protected(records: list[Record]) -> dict[str, Any]:
    targets = [r for r in records if r.label == "coercion" and r.target]
    held = sum(r.amount_paise for r in targets if r.decision == "HOLD")
    total = sum(r.amount_paise for r in targets)
    return {
        "held_paise": held,
        "attempted_paise": total,
        "share": round(held / total, 4) if total else 0.0,
    }


def genuine_high_value(records: list[Record]) -> list[Record]:
    return [r for r in records if r.label == "genuine" and r.amount_paise >= HIGH_VALUE_PAISE]


def false_hold(records: list[Record]) -> Rate:
    genuine = genuine_high_value(records)
    return Rate(sum(r.decision == "HOLD" for r in genuine), len(genuine))


def genuine_warning(records: list[Record]) -> Rate:
    genuine = genuine_high_value(records)
    return Rate(sum(r.decision == "WARN" for r in genuine), len(genuine))


def explanation_coverage(records: list[Record]) -> Rate:
    flagged = [r for r in records if r.decision in ("WARN", "HOLD")]
    ok = sum(
        any(x["points"] for x in r.reasons) and sum(x["points"] for x in r.reasons) == r.raw_score
        for r in flagged
    )
    return Rate(ok, len(flagged))


def modelled_delay_minutes(records: list[Record], seed: int = 0) -> dict[str, Any]:
    """Hold-to-release time for genuine held transfers under the AI_DESIGN §8 assumptions.

    HIGH + active contact: log-normal response (median 8, p90 25 min); 15% never respond and go to
    an officer at the end of cooling-off (240 min). Holds that start with an officer (VERY_HIGH, or
    no active contact) are modelled as released at the end of cooling-off (240 min).
    """
    rng = random.Random(f"delay:{seed}")
    sigma = (math.log(CONTACT_P90_MIN) - math.log(CONTACT_MEDIAN_MIN)) / Z90
    delays = []
    for r in records:
        if r.label != "genuine" or r.decision != "HOLD":
            continue
        if r.hold_status == "AWAITING_CONTACT" and rng.random() >= CONTACT_NO_RESPONSE:
            delays.append(rng.lognormvariate(math.log(CONTACT_MEDIAN_MIN), sigma))
        else:
            delays.append(COOLING_OFF_MIN)
    if not delays:
        return {"n": 0, "median": None, "p90": None}
    ordered = sorted(delays)
    return {
        "n": len(ordered),
        "median": round(statistics.median(ordered), 1),
        "p90": round(ordered[min(len(ordered) - 1, int(0.9 * len(ordered)))], 1),
    }


def per_family(records: list[Record]) -> list[dict[str, Any]]:
    by_family: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        if r.label == "genuine" or r.first_target:
            by_family[r.family].append(r)
    rows = []
    for family in sorted(by_family, key=lambda f: (f[0] != "P", f)):
        rs = by_family[family]
        counts = Counter(r.decision for r in rs)
        label = rs[0].label
        if label == "coercion":
            metric = Rate(counts["HOLD"], len(rs))
            metric_name = "interception"
        else:
            hv = [r for r in rs if r.amount_paise >= HIGH_VALUE_PAISE]
            metric = Rate(sum(r.decision == "HOLD" for r in hv), len(hv))
            metric_name = "false_hold"
        rows.append(
            {
                "family": family,
                "label": label,
                "n": len(rs),
                "ALLOW": counts["ALLOW"],
                "WARN": counts["WARN"],
                "HOLD": counts["HOLD"],
                metric_name: metric.as_dict(),
            }
        )
    return rows


def tier_confusion(records: list[Record]) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {
        label: dict.fromkeys(("LOW", "MEDIUM", "HIGH", "VERY_HIGH"), 0)
        for label in ("coercion", "genuine")
    }
    for r in records:
        if r.label == "genuine" or r.first_target:
            table[r.label][r.tier] += 1
    return table


def reason_frequency(records: list[Record]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for r in records:
        if r.decision in ("WARN", "HOLD"):
            counts.update(x["code"] for x in r.reasons if x["points"])
    return counts.most_common()


def latency(records: list[Record]) -> dict[str, float]:
    values = sorted(r.latency_ms for r in records)
    if not values:
        return {}
    return {
        "p50_ms": round(statistics.median(values), 1),
        "p95_ms": round(values[min(len(values) - 1, int(0.95 * len(values)))], 1),
        "max_ms": round(values[-1], 1),
    }
