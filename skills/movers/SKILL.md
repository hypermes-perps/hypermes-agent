---
name: emerging-movers
version: 1.0.0
description: Detects assets with sudden capital inflow via OI/volume/funding proxy signals
author: Nunchi Trade
tags: [movers, detector, smart-money, signals, hyperliquid]
---

# Emerging Movers Detector

Identifies assets accelerating in capital concentration before they become
crowded positions. Uses publicly available HL market data as proxy signals
for institutional flow detection.

## Signal Types

| Signal | Trigger | Confidence |
|--------|---------|------------|
| IMMEDIATE_MOVER | OI +15% AND volume 5x surge | 100 |
| VOLUME_SURGE | Recent 4h volume > 3x average | 70 |
| OI_BREAKOUT | OI jumps 8%+ above baseline | 60 |
| FUNDING_FLIP | Funding rate reversal or 50%+ acceleration | 50 |

## Direction Classification

Majority vote across available signals:
- Funding rate sign → directional bias
- Price breakout direction
- Volume surge + price momentum

## Quality Filters

1. Erratic detection (rank bouncing → filtered)
2. Minimum 24h volume ($500K default)
3. Minimum scan history for baseline (2 scans)

## Usage

```bash
hl movers once              # Single scan
hl movers run --tick 60     # Continuous (60s intervals)
hl movers once --json       # JSON output
hl movers once --mock       # Mock data
hl movers status            # Last scan results
hl movers presets           # List presets
```
