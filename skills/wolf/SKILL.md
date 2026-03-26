---
name: WOLF Strategy
version: 1.0.0
description: Autonomous multi-slot trading orchestrator
author: YEX
dependencies:
  - modules/wolf_config.py
  - modules/wolf_state.py
  - modules/wolf_engine.py
  - modules/scanner_guard.py
  - modules/movers_guard.py
  - modules/dsl_guard.py
---

# WOLF Strategy

Autonomous multi-slot trading strategy that composes Scanner + Movers + DSL into a unified orchestrator.

## Architecture

WOLF runs a single tick loop (60s base) that:

1. **Every tick**: Fetch prices, update ROEs, check DSL guards, run movers, evaluate entry/exit
2. **Every 5 ticks** (5 min): Watchdog health check (verify positions match exchange)
3. **Every 15 ticks** (15 min): Run opportunity scanner, queue high-score setups

## Slot Management

- 2-3 concurrent positions (configurable)
- Each slot: EMPTY -> ACTIVE -> CLOSED (reset to EMPTY)
- No duplicate instruments across slots
- Max 2 same-direction positions

## Entry Priority

1. Movers IMMEDIATE_MOVER -> auto-enter
2. Scanner score > 170 -> queue entry
3. Movers other signals (confidence > 70) -> enter

## Exit Priority

1. DSL trailing stop CLOSE
2. Hard stop: ROE < -5%
3. Conviction collapse: signal gone + negative PnL for 30+ min
4. Stagnation: ROE stuck above 3% for 60+ min

## Risk Management

- Per-slot margin: total_budget / max_slots
- Daily loss limit: $500 (default)
- Daily loss trigger: close all positions immediately

## Usage

```bash
# Mock mode
hl wolf run --mock --max-ticks 10

# Live (testnet)
hl wolf run

# Live (mainnet)
hl wolf run --mainnet

# Check status
hl wolf status

# List presets
hl wolf presets
```

## Presets

- **default**: 3 slots, 10x leverage, $10K budget
- **conservative**: 2 slots, 5x leverage, higher thresholds
- **aggressive**: 3 slots, 15x leverage, lower thresholds
