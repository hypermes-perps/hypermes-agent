---
name: opportunity-scanner
version: 1.0.0
description: Screens all Hyperliquid perps and surfaces top trading setups
author: Nunchi Trade
tags: [scanner, screener, technicals, opportunities, hyperliquid]
---

# Opportunity Scanner

Screens all Hyperliquid perpetual markets through a 4-stage funnel to surface
the highest-conviction trading setups.

## Architecture

```
Stage 0: BTC Macro Context (EMA 5/13 on 4h, 1h momentum)
Stage 1: Bulk Screen (~500 assets → ~70 by volume)
Stage 2: Top-N Selection (by composite liquidity score)
Stage 3: Deep Dive (multi-TF technicals + 3-pillar scoring)
Stage 4: Momentum + Final Ranking
```

## 3-Pillar Scoring (0-400 scale)

| Pillar | Weight | Signals |
|--------|--------|---------|
| Market Structure | 35% | Volume tiers, surge, OI, OI/Vol health |
| Technicals | 40% | 4h trend, hourly trend, RSI, patterns, volume |
| Funding | 25% | Neutral (+40), favorable, unfavorable penalties |

## Hard Disqualifiers

1. Counter-trend on hourly structure
2. Extreme RSI (>80 for LONG, <20 for SHORT)
3. Strong 4h counter-trend (strength > 50)
4. Volume dying on both timeframes
5. Heavy unfavorable funding (>50% annualized)
6. BTC macro headwind (modifier < -30)

## Usage

### CLI
```bash
hl scanner once              # Single scan
hl scanner run --tick 900    # Continuous (15 min intervals)
hl scanner once --json       # JSON output
hl scanner once --mock       # With mock data (no HL connection)
hl scanner status            # Show last scan results
hl scanner presets            # List presets
```

### Standalone
```python
from skills.scanner.scripts.standalone_runner import ScannerRunner
from cli.hl_adapter import DirectHLProxy

runner = ScannerRunner(hl=hl, tick_interval=900)
runner.run()
```

## Configuration

Via YAML config or CLI flags:
- `--min-volume`: Minimum 24h volume to qualify (default: $500K)
- `--top-n`: Assets to deep dive (default: 20)
- `--preset`: "default" or "aggressive"
- `--score-threshold`: Minimum final score (default: 150)
