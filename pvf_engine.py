"""
Transparent AI Platform — Plastic Vector Fields (PVF)
Proof-of-Concept Skeleton

This module provides a minimal skeleton illustrating the core PVF design principles:
  1. Every learning/inference step produces a structured trace
  2. Memory is updated non-destructively (no catastrophic forgetting)
  3. Decisions are explainable by construction

NOTE: This is a conceptual scaffold, not a production PVF implementation.
The mathematical foundation is from Janson & Balanov (2026), Physica D.
"""

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Trace record — every decision leaves one of these
# ---------------------------------------------------------------------------

@dataclass
class TraceRecord:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    input_features: dict = field(default_factory=dict)
    memory_state_snapshot: dict = field(default_factory=dict)
    active_field_weights: dict = field(default_factory=dict)
    decision: Any = None
    confidence: float = 0.0
    reasoning_steps: list = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ---------------------------------------------------------------------------
# Plastic Memory — non-destructive, continuously updated
# ---------------------------------------------------------------------------

class PlasticMemory:
    """
    Simplified model of a plastic vector field memory store.
    
    Key property: new information strengthens or releases existing patterns
    rather than overwriting them — avoiding catastrophic forgetting.
    """

    def __init__(self, decay_rate: float = 0.05, reinforce_rate: float = 0.2):
        self.patterns: dict[str, float] = {}  # pattern_key -> strength
        self.decay_rate = decay_rate
        self.reinforce_rate = reinforce_rate

    def update(self, pattern_key: str, signal_strength: float) -> str:
        """
        Update memory for a pattern.
        - If pattern is new: initialise at signal_strength
        - If pattern exists: reinforce proportionally (not overwrite)
        - Existing unrelated patterns decay slightly (selective forgetting)
        Returns a human-readable trace of what changed.
        """
        trace_steps = []

        # Decay all existing patterns slightly (selective forgetting)
        for key in list(self.patterns.keys()):
            if key != pattern_key:
                before = self.patterns[key]
                self.patterns[key] = max(0.0, self.patterns[key] - self.decay_rate)
                if self.patterns[key] == 0.0:
                    del self.patterns[key]
                    trace_steps.append(f"Released weak pattern '{key}' (was {before:.3f})")

        # Reinforce or initialise the target pattern
        if pattern_key in self.patterns:
            before = self.patterns[pattern_key]
            self.patterns[pattern_key] = min(1.0, self.patterns[pattern_key] + self.reinforce_rate * signal_strength)
            trace_steps.append(
                f"Reinforced '{pattern_key}': {before:.3f} → {self.patterns[pattern_key]:.3f}"
            )
        else:
            self.patterns[pattern_key] = signal_strength
            trace_steps.append(f"Initialised new pattern '{pattern_key}' at {signal_strength:.3f}")

        return " | ".join(trace_steps)

    def snapshot(self) -> dict:
        return dict(sorted(self.patterns.items(), key=lambda x: x[1], reverse=True))

    def recall(self, pattern_key: str) -> float:
        return self.patterns.get(pattern_key, 0.0)


# ---------------------------------------------------------------------------
# PVF Decision Engine — core inference loop with built-in trace
# ---------------------------------------------------------------------------

class PVFDecisionEngine:
    """
    Minimal PVF-inspired decision engine.
    
    Every call to .decide() returns both a decision and a full TraceRecord —
    the reasoning is not reconstructed after the fact; it is produced as the
    inference runs.
    """

    def __init__(self, domain: str):
        self.domain = domain
        self.memory = PlasticMemory()
        self.decision_log: list[TraceRecord] = []

    def decide(self, features: dict[str, float], learn: bool = True) -> TraceRecord:
        """
        Make a traceable decision from input features.
        
        Args:
            features: key-value input signals (e.g. {"credit_score": 0.72, "debt_ratio": 0.3})
            learn:    whether to update memory from this input
        
        Returns:
            TraceRecord with full reasoning chain
        """
        trace = TraceRecord(input_features=features)
        steps = []

        # Step 1 — Retrieve relevant memory patterns
        steps.append("Step 1: Retrieve memory patterns for input features")
        field_weights = {}
        for feature, value in features.items():
            memory_strength = self.memory.recall(feature)
            field_weights[feature] = value * (1.0 + memory_strength)
            steps.append(
                f"  · '{feature}': input={value:.3f}, memory_strength={memory_strength:.3f}, "
                f"effective_weight={field_weights[feature]:.3f}"
            )

        trace.active_field_weights = field_weights

        # Step 2 — Compute weighted signal
        steps.append("Step 2: Compute aggregate decision signal")
        total_weight = sum(field_weights.values())
        n = len(field_weights)
        signal = total_weight / n if n > 0 else 0.0
        steps.append(f"  · Aggregate signal: {signal:.4f} (mean of {n} weighted features)")

        # Step 3 — Map signal to decision (domain-agnostic threshold example)
        steps.append("Step 3: Map signal to decision via threshold")
        if signal >= 0.65:
            decision = "APPROVE"
            confidence = min(1.0, signal)
        elif signal >= 0.40:
            decision = "REVIEW"
            confidence = signal
        else:
            decision = "DECLINE"
            confidence = 1.0 - signal

        steps.append(f"  · Signal {signal:.4f} → decision='{decision}', confidence={confidence:.4f}")

        trace.decision = decision
        trace.confidence = round(confidence, 4)

        # Step 4 — Update memory (continuous learning, non-destructive)
        if learn:
            steps.append("Step 4: Update plastic memory (continuous learning)")
            for feature, value in features.items():
                update_trace = self.memory.update(feature, value)
                steps.append(f"  · {update_trace}")
        else:
            steps.append("Step 4: Memory update skipped (learn=False)")

        trace.reasoning_steps = steps
        trace.memory_state_snapshot = self.memory.snapshot()

        self.decision_log.append(trace)
        return trace

    def audit_export(self, last_n: int = 10) -> list[dict]:
        """Export the last N decisions as structured dicts for audit/reporting."""
        return [asdict(t) for t in self.decision_log[-last_n:]]


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== PVF Decision Engine — Credit Scoring Demo ===\n")

    engine = PVFDecisionEngine(domain="credit_scoring")

    applications = [
        {"credit_score": 0.80, "debt_ratio": 0.20, "employment_stability": 0.90},
        {"credit_score": 0.45, "debt_ratio": 0.60, "employment_stability": 0.50},
        {"credit_score": 0.70, "debt_ratio": 0.35, "employment_stability": 0.75},
    ]

    for i, app in enumerate(applications, 1):
        print(f"--- Application {i} ---")
        result = engine.decide(app)
        print(f"Decision:    {result.decision}")
        print(f"Confidence:  {result.confidence}")
        print("\nReasoning trace:")
        for step in result.reasoning_steps:
            print(f"  {step}")
        print(f"\nMemory state after this decision:")
        for k, v in result.memory_state_snapshot.items():
            print(f"  {k}: {v:.4f}")
        print()

    print("=== Audit Export (last 3 decisions) ===")
    print(json.dumps(engine.audit_export(3), indent=2))
