"""
pvf_brand_memory.py — Plastic Vector Field memory layer for Brand Intelligence

Drop-in enhancement for NinjaDS/brand-listener.
Replaces opaque adaptive learning with a transparent, traceable brand memory.

Every update, query suggestion, score, and alert includes a full reasoning trace
so you always know WHY the brand score moved, WHY you're searching for X this week,
and WHY an alert fired.

Based on: Janson & Balanov (2026), Physica D: Nonlinear Phenomena
          https://www.sciencedirect.com/science/article/pii/S0167278926001247
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MemoryUpdateTrace:
    """Full trace produced by a single memory update cycle."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    week_label: str = ""
    brand: str = ""
    input_signals: dict = field(default_factory=dict)
    reinforcements: list = field(default_factory=list)
    decays: list = field(default_factory=list)
    releases: list = field(default_factory=list)
    new_patterns: list = field(default_factory=list)
    memory_before: dict = field(default_factory=dict)
    memory_after: dict = field(default_factory=dict)

    def summary(self) -> str:
        lines = [f"Memory update — {self.brand} ({self.week_label})"]
        if self.new_patterns:
            lines.append(f"  New patterns: {', '.join(self.new_patterns)}")
        if self.reinforcements:
            lines += [f"  ↑ {r}" for r in self.reinforcements]
        if self.decays:
            lines += [f"  ↓ {d}" for d in self.decays]
        if self.releases:
            lines += [f"  ✗ Released: {', '.join(self.releases)}"]
        return "\n".join(lines)


@dataclass
class BrandScoreTrace:
    """Traceable brand score computation."""
    score: float = 0.0
    score_label: str = ""
    delta: float = 0.0
    previous_score: float = 0.0
    reasoning: list = field(default_factory=list)
    dominant_positive: list = field(default_factory=list)
    dominant_negative: list = field(default_factory=list)


@dataclass
class QuerySuggestionTrace:
    """Traceable adaptive search query generation."""
    topics: list = field(default_factory=list)
    reasoning: list = field(default_factory=list)
    excluded: list = field(default_factory=list)


@dataclass
class AlertTrace:
    """Alert with full signal path."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand: str = ""
    pattern: str = ""
    strength: float = 0.0
    threshold: float = 0.0
    direction: str = ""   # "negative" or "positive"
    signal_path: list = field(default_factory=list)
    fired_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Sentiment polarity — which topics are typically negative signals for brands
# (extend or configure per domain)
# ---------------------------------------------------------------------------

NEGATIVE_SIGNAL_KEYWORDS = {
    "complaint", "complaints", "delay", "delays", "issue", "issues",
    "problem", "problems", "error", "errors", "fail", "failure", "refund",
    "scam", "fraud", "lawsuit", "recall", "crisis", "scandal",
    "overpriced", "expensive", "rip-off", "terrible", "awful", "worst",
    "disappointing", "broken", "defect",
}

def _is_negative(pattern_key: str) -> bool:
    key_lower = pattern_key.lower()
    return any(kw in key_lower for kw in NEGATIVE_SIGNAL_KEYWORDS)


# ---------------------------------------------------------------------------
# Plastic Brand Memory
# ---------------------------------------------------------------------------

class PlasticBrandMemory:
    """
    Transparent, continuously-learning brand signal memory.

    Replaces the opaque weekly state in brand-listener with a PVF-inspired
    memory store where every learning step is traceable.

    Key properties:
    - New signals REINFORCE existing patterns (non-destructive)
    - Stale signals DECAY naturally over time (no abrupt forgetting)
    - Very weak patterns are RELEASED cleanly (no ghost signals)
    - Every update, query, score, and alert carries a full reasoning trace
    """

    def __init__(
        self,
        brand: str,
        reinforce_rate: float = 0.25,
        decay_rate: float = 0.08,
        release_threshold: float = 0.05,
        alert_threshold: float = 0.70,
    ):
        self.brand = brand
        self.reinforce_rate = reinforce_rate
        self.decay_rate = decay_rate
        self.release_threshold = release_threshold
        self.alert_threshold = alert_threshold

        self.patterns: dict[str, float] = {}
        self.history: list[MemoryUpdateTrace] = []
        self.score_history: list[float] = []
        self.week_counter: int = 0

    # ------------------------------------------------------------------
    # Core: update memory from this week's signals
    # ------------------------------------------------------------------

    def update(self, signals: dict[str, float], week_label: str = "") -> MemoryUpdateTrace:
        """
        Feed this week's extracted brand signals into memory.

        Args:
            signals: dict of {topic/pattern: signal_strength (0.0–1.0)}
                     e.g. {"delivery complaints": 0.85, "product quality": 0.60}
            week_label: human-readable week identifier (e.g. "2026-W18")

        Returns:
            MemoryUpdateTrace — full record of what changed and why
        """
        self.week_counter += 1
        week_label = week_label or f"Week-{self.week_counter}"

        trace = MemoryUpdateTrace(
            brand=self.brand,
            week_label=week_label,
            input_signals=dict(signals),
            memory_before=dict(self.patterns),
        )

        # Step 1 — Decay all existing patterns not in this week's signals
        for pattern in list(self.patterns.keys()):
            if pattern not in signals:
                before = self.patterns[pattern]
                self.patterns[pattern] = max(0.0, before - self.decay_rate)
                if self.patterns[pattern] <= self.release_threshold:
                    del self.patterns[pattern]
                    trace.releases.append(f"'{pattern}' (was {before:.3f}, decayed to threshold)")
                else:
                    trace.decays.append(
                        f"'{pattern}': {before:.3f} → {self.patterns[pattern]:.3f} (no signal this week)"
                    )

        # Step 2 — Reinforce or initialise patterns from this week's signals
        for pattern, signal in signals.items():
            if pattern in self.patterns:
                before = self.patterns[pattern]
                self.patterns[pattern] = min(1.0, before + self.reinforce_rate * signal)
                trace.reinforcements.append(
                    f"'{pattern}': {before:.3f} → {self.patterns[pattern]:.3f} "
                    f"(signal={signal:.3f}, reinforced)"
                )
            else:
                self.patterns[pattern] = signal
                trace.new_patterns.append(pattern)
                trace.reinforcements.append(
                    f"'{pattern}': initialised at {signal:.3f} (new pattern)"
                )

        trace.memory_after = dict(self.patterns)
        self.history.append(trace)
        return trace

    # ------------------------------------------------------------------
    # Explainable brand score
    # ------------------------------------------------------------------

    def compute_brand_score(self) -> tuple[float, BrandScoreTrace]:
        """
        Compute a 0–100 brand health score with full reasoning.

        Positive patterns push the score up; negative patterns pull it down.
        The reasoning trace explains each contributor.
        """
        if not self.patterns:
            trace = BrandScoreTrace(score=50.0, score_label="Neutral", reasoning=["No patterns in memory yet"])
            return 50.0, trace

        positive, negative = [], []
        reasoning = []

        for pattern, strength in sorted(self.patterns.items(), key=lambda x: x[1], reverse=True):
            if _is_negative(pattern):
                negative.append((pattern, strength))
                reasoning.append(
                    f"  ↓ '{pattern}' (strength {strength:.3f}) — negative signal, pulls score down"
                )
            else:
                positive.append((pattern, strength))
                reasoning.append(
                    f"  ↑ '{pattern}' (strength {strength:.3f}) — positive signal, lifts score"
                )

        pos_total = sum(s for _, s in positive)
        neg_total = sum(s for _, s in negative)
        n = len(self.patterns)

        raw = (pos_total - neg_total) / n if n > 0 else 0.0
        score = round(max(0.0, min(100.0, 50.0 + raw * 50.0)), 1)

        # Compute delta vs last score
        previous = self.score_history[-1] if self.score_history else score
        delta = round(score - previous, 1)
        self.score_history.append(score)

        label = (
            "Strong" if score >= 70 else
            "Healthy" if score >= 55 else
            "Neutral" if score >= 45 else
            "At Risk" if score >= 30 else
            "Critical"
        )

        trace = BrandScoreTrace(
            score=score,
            score_label=label,
            delta=delta,
            previous_score=previous,
            reasoning=reasoning,
            dominant_positive=[p for p, _ in positive[:3]],
            dominant_negative=[p for p, _ in negative[:3]],
        )

        return score, trace

    # ------------------------------------------------------------------
    # Traceable adaptive query suggestion
    # ------------------------------------------------------------------

    def suggest_query_topics(self, top_n: int = 3, min_strength: float = 0.10) -> tuple[list[str], QuerySuggestionTrace]:
        """
        Suggest which topics to focus search queries on this week.

        Replaces the opaque "blend from last week's report" logic in brand-listener
        with a transparent, strength-ranked selection.
        """
        trace = QuerySuggestionTrace()

        if not self.patterns:
            trace.reasoning.append("Memory empty — using brand name only")
            return [], trace

        # Sort by strength descending
        ranked = sorted(self.patterns.items(), key=lambda x: x[1], reverse=True)

        selected, excluded = [], []
        for pattern, strength in ranked:
            if strength < min_strength:
                excluded.append(f"'{pattern}' (strength {strength:.3f} below threshold {min_strength})")
            elif len(selected) < top_n:
                selected.append(pattern)
                trace.reasoning.append(
                    f"  Selected '{pattern}' (strength {strength:.3f}) — "
                    f"{'accelerating' if strength > 0.60 else 'notable signal'}"
                )
            else:
                excluded.append(f"'{pattern}' (strength {strength:.3f}, top {top_n} already filled)")

        trace.topics = selected
        trace.excluded = excluded

        if excluded:
            trace.reasoning.append(f"  Excluded: {'; '.join(excluded)}")

        return selected, trace

    # ------------------------------------------------------------------
    # Transparent alerts
    # ------------------------------------------------------------------

    def check_alerts(self, threshold: float = None) -> list[AlertTrace]:
        """
        Check for patterns that have crossed the alert threshold.
        Returns alerts with full signal paths (not just "threshold crossed").
        """
        threshold = threshold or self.alert_threshold
        alerts = []

        for pattern, strength in self.patterns.items():
            if strength >= threshold:
                direction = "negative" if _is_negative(pattern) else "positive"
                signal_path = [
                    f"Pattern '{pattern}' reached strength {strength:.3f}",
                    f"Threshold: {threshold} | Direction: {direction}",
                ]

                # Add history context if available
                if self.history:
                    last = self.history[-1]
                    matching = [r for r in last.reinforcements if f"'{pattern}'" in r]
                    if matching:
                        signal_path.append(f"This week: {matching[0]}")

                alerts.append(AlertTrace(
                    brand=self.brand,
                    pattern=pattern,
                    strength=strength,
                    threshold=threshold,
                    direction=direction,
                    signal_path=signal_path,
                ))

        return alerts

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        data = {
            "brand": self.brand,
            "week_counter": self.week_counter,
            "patterns": self.patterns,
            "score_history": self.score_history,
            "config": {
                "reinforce_rate": self.reinforce_rate,
                "decay_rate": self.decay_rate,
                "release_threshold": self.release_threshold,
                "alert_threshold": self.alert_threshold,
            },
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        self.patterns = data.get("patterns", {})
        self.score_history = data.get("score_history", [])
        self.week_counter = data.get("week_counter", 0)


# ---------------------------------------------------------------------------
# Demo: 4-week brand monitoring scenario
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("PVF Brand Intelligence — Curlsmith 4-Week Demo")
    print("=" * 60)

    memory = PlasticBrandMemory(brand="Curlsmith", alert_threshold=0.70)

    weekly_signals = [
        {
            "week": "2026-W15",
            "signals": {
                "product quality": 0.80,
                "influencer collab": 0.70,
                "delivery complaints": 0.20,
                "pricing concerns": 0.30,
            }
        },
        {
            "week": "2026-W16",
            "signals": {
                "product quality": 0.75,
                "delivery complaints": 0.55,
                "pricing concerns": 0.40,
                "new product launch": 0.60,
            }
        },
        {
            "week": "2026-W17",
            "signals": {
                "delivery complaints": 0.80,
                "pricing concerns": 0.65,
                "product quality": 0.50,
                "customer service issues": 0.45,
            }
        },
        {
            "week": "2026-W18",
            "signals": {
                "delivery complaints": 0.90,
                "customer service issues": 0.70,
                "pricing concerns": 0.60,
                "product quality": 0.45,
            }
        },
    ]

    for entry in weekly_signals:
        print(f"\n{'─' * 50}")
        print(f"📅 {entry['week']}")
        print(f"{'─' * 50}")

        # Update memory
        update_trace = memory.update(entry["signals"], week_label=entry["week"])
        print(update_trace.summary())

        # Score
        score, score_trace = memory.compute_brand_score()
        delta_str = f"({'↑' if score_trace.delta >= 0 else '↓'}{abs(score_trace.delta)})" if score_trace.delta != 0 else ""
        print(f"\n📊 Brand Score: {score}/100 [{score_trace.score_label}] {delta_str}")
        print("Reasoning:")
        for r in score_trace.reasoning:
            print(r)

        # Query suggestions
        topics, query_trace = memory.suggest_query_topics(top_n=2)
        print(f"\n🔍 Adaptive Search Focus:")
        for r in query_trace.reasoning:
            print(r)

        # Alerts
        alerts = memory.check_alerts()
        if alerts:
            print(f"\n🚨 Alerts ({len(alerts)}):")
            for alert in alerts:
                print(f"  [{alert.direction.upper()}] '{alert.pattern}' at {alert.strength:.3f}")
                for step in alert.signal_path:
                    print(f"    · {step}")

    print(f"\n{'=' * 60}")
    print("Final memory state:")
    for pattern, strength in sorted(memory.patterns.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(strength * 20)
        print(f"  {pattern:<30} {bar} {strength:.3f}")
