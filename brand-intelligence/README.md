# PVF Brand Intelligence

> **Brand Listener, evolved.** Same social listening power — now with a transparent memory that can explain *why* your brand score moved, *why* certain topics are being chased this week, and *why* an alert fired.

Built on the [Plastic Vector Fields](https://www.sciencedirect.com/science/article/pii/S0167278926001247) framework (Loughborough University, 2026). A direct evolution of [NinjaDS/brand-listener](https://github.com/NinjaDS/brand-listener).

---

## The Gap in Current Brand Listener

Brand Listener already does something clever: it blends themes from last week's report into this week's search (Karpathy-inspired adaptive queries). But there are three things it can't currently explain:

| Question | Current Answer | PVF Answer |
|---|---|---|
| Why did brand score drop 12 points? | "Sentiment decreased" | "Topic 'delivery complaints' reinforced from 0.21→0.74 over 3 weeks; 'award win' pattern decayed to 0.08" |
| Why are we focusing on this search query this week? | Blended from last report (opaque) | Explicit memory trace: which patterns drove query selection, and at what strength |
| Why did the alert fire? | Threshold crossed | Full signal path: which sources fed which patterns, which pattern crossed the threshold |

The adaptive learning in brand-listener is real — but it's a black box. PVF makes it a glass box.

---

## What Changes

### 1. Plastic Brand Memory (replaces static weekly state)

Instead of storing "last week's themes" as a flat list, the system maintains a living memory of brand signal patterns — each with a strength that evolves over time.

```
brand_memory["delivery complaints"]   = 0.74  ← reinforced 3 weeks running
brand_memory["award recognition"]     = 0.08  ← fading, appeared once
brand_memory["pricing concerns"]      = 0.45  ← stable, moderate signal
brand_memory["innovation leadership"] = 0.62  ← growing
```

New signals **reinforce** existing patterns. Old signals that stop appearing **decay** — mirroring how human memory works. Nothing is overwritten; it fades gracefully.

### 2. Traceable Adaptive Search

The current adaptive search picks up "emerging themes" opaquely. PVF makes query generation a traceable step:

```
Trace: adaptive_query_generation
  · 'delivery complaints' (strength 0.74) → promoted to primary query focus
  · 'innovation leadership' (strength 0.62, ↑ from 0.41) → included as secondary
  · 'award recognition' (strength 0.08) → dropped below threshold (0.10), excluded
  · Generated query: "Curlsmith delivery complaints OR innovation"
```

Every week, you know exactly *why* the search went where it went.

### 3. Explainable Sentiment Scoring

Current Brand Listener returns a sentiment score. PVF returns a score *plus* a memory-backed reasoning chain:

```json
{
  "brand": "Curlsmith",
  "week": "2026-W18",
  "score": 42,
  "score_delta": -11,
  "reasoning": [
    "Pattern 'delivery complaints' reinforced: 8 new mentions (Reddit x5, LinkedIn x3)",
    "Pattern 'product quality' stable at 0.51 — no significant change",
    "Pattern 'influencer collab' decayed: 0.34 → 0.28, no new mentions this week",
    "Score delta driven primarily by 'delivery complaints' reinforcement (+0.53 weighted impact)"
  ],
  "memory_snapshot": { ... }
}
```

### 4. Transparent Alert Engine

Alerts today fire when a threshold is crossed — but the reason is often unclear. PVF alert payloads include the full signal path:

```
ALERT: Curlsmith sentiment dropped >10 points

Signal path:
  Reddit (22 mentions) → sentiment: 0.31 → fed 'delivery complaints' pattern
  LinkedIn (6 mentions) → sentiment: 0.29 → reinforced 'price increase' pattern
  Memory: 'delivery complaints' crossed alert threshold (0.70) for first time
  Triggered by: week-over-week pattern acceleration (0.45 → 0.74)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PVF Brand Intelligence                        │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Data Layer (unchanged)                  │  │
│  │  Reddit · LinkedIn · News RSS · Meta · TikTok · HN         │  │
│  └───────────────────────┬───────────────────────────────────┘  │
│                           │ raw mentions                         │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │              Signal Extractor (Claude via Bedrock)         │  │
│  │   Topics · Sentiment · Named Entities · Urgency Score      │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │ structured signals                   │
│  ┌────────────────────────▼──────────────────────────────────┐  │
│  │              Plastic Brand Memory (PVF core)               │  │
│  │   Reinforcement · Decay · Pattern Strength · Trace Log     │  │
│  └──────────┬────────────────────────┬───────────────────────┘  │
│             │                        │                           │
│  ┌──────────▼──────────┐  ┌─────────▼──────────────────────┐   │
│  │  Adaptive Query     │  │   Scoring & Alert Engine        │   │
│  │  Generator          │  │   (with full reasoning trace)   │   │
│  │  (traceable picks)  │  └─────────────────────────────────┘   │
│  └─────────────────────┘                                        │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                     Report Builder                         │  │
│  │   Score · Delta · Reasoning Chain · Memory Snapshot        │  │
│  │   + existing HTML report format                            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Module: `pvf_brand_memory.py`

See [`pvf_brand_memory.py`](./pvf_brand_memory.py) for the full implementation.

Key API:

```python
from pvf_brand_memory import PlasticBrandMemory

memory = PlasticBrandMemory(brand="Curlsmith")

# Feed this week's signals in
trace = memory.update(signals={
    "delivery complaints": 0.85,
    "product quality": 0.60,
    "influencer collab": 0.20,
})

# Get traceable adaptive query topics
query_topics, query_trace = memory.suggest_query_topics(top_n=3)

# Get explainable brand score
score, score_trace = memory.compute_brand_score()

# Check if any alert thresholds crossed
alerts = memory.check_alerts(threshold=0.70)

# Persist memory across runs
memory.save("memory/curlsmith.json")
memory.load("memory/curlsmith.json")
```

---

## Integration with Brand Listener

This is designed as a **drop-in enhancement**, not a replacement. The existing scraping, Claude sentiment analysis, HTML reporting, and email delivery all stay the same. PVF wraps around the scoring and adaptive search layers:

```python
# In brand_listener.py — current flow:
mentions = scrape_all_sources(brand)
sentiment = claude_sentiment(mentions)
report = build_report(sentiment)

# PVF-enhanced flow:
mentions = scrape_all_sources(brand)
signals = claude_extract_signals(mentions)       # structured topics + strengths
trace = brand_memory.update(signals)             # PVF: reinforce/decay memory
query_topics, _ = brand_memory.suggest_query_topics()  # traceable next queries
score, reasoning = brand_memory.compute_brand_score()  # explainable score
alerts = brand_memory.check_alerts()            # signal-path alerts
report = build_report(score, reasoning, alerts, trace)  # enriched report
```

---

## What the Report Gains

**Before (current Brand Listener report):**
> Brand sentiment: 42/100 (↓11 from last week). Alert: sentiment drop detected.

**After (PVF-enhanced report):**
> Brand sentiment: 42/100 (↓11 from last week).
>
> **Why it dropped:** The 'delivery complaints' signal has been reinforcing for 3 consecutive weeks (0.21 → 0.46 → 0.74). This week it crossed the alert threshold. The 'innovation leadership' pattern is growing (0.41 → 0.62) but not yet strong enough to offset it.
>
> **This week's search focus:** Prioritising 'delivery complaints' and 'pricing concerns' — both accelerating. Dropping 'award recognition' (strength 0.08, faded).
>
> **Memory state:** [full pattern snapshot attached]

---

## References

- [NinjaDS/brand-listener](https://github.com/NinjaDS/brand-listener) — the base tool this enhances
- Janson & Balanov (2026). *Designing explainable cognitive systems and explaining neural networks with plastic dynamical systems.* Physica D: Nonlinear Phenomena.
- [Loughborough University Press Release](https://www.lboro.ac.uk/news-events/news/2026/april/blueprint-transparent-artificial-intelligence/)

---

*Concept: May 2026 | NinjaDS*
