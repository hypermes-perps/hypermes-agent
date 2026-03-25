---
name: yex-trader
description: Autonomous Hyperliquid trading — run market making, mean reversion, and LLM-powered strategies on HL perps and YEX yield markets.
user-invocable: true
argument-hint: "<strategy> [options]"
allowed-tools:
  - Bash
metadata:
  openclaw:
    requires:
      env:
        - HL_PRIVATE_KEY
      bins:
        - python3
    primaryEnv: HL_PRIVATE_KEY
---

# YEX Trader

Autonomous Hyperliquid trading via the agent-cli. Runs deterministic and LLM-powered strategies against HL perps and YEX yield markets.

## Setup

The agent-cli must be cloned and installed:
```bash
cd ~/agent-cli && pip install -e .
```

Required environment variables:
- `HL_PRIVATE_KEY` — Hyperliquid private key (for live trading)
- `ANTHROPIC_API_KEY` — Anthropic API key (only for `claude_agent` strategy)

## Commands

### Start autonomous trading
```bash
cd ~/agent-cli && hl run <strategy> [options]
```
Options: `--instrument/-i`, `--tick/-t` (seconds), `--config/-c` (YAML), `--mainnet`, `--dry-run`, `--mock`, `--max-ticks`, `--resume/--fresh`, `--model` (LLM override)

### Check status
```bash
cd ~/agent-cli && hl status [--watch] [--interval 5]
```

### Place a single order
```bash
cd ~/agent-cli && hl trade <instrument> <side> <size>
```

### Account info
```bash
cd ~/agent-cli && hl account [--mainnet]
```

### List strategies
```bash
cd ~/agent-cli && hl strategies
```

## Strategies

| Name | Description |
|------|-------------|
| simple_mm | Symmetric bid/ask quoting |
| avellaneda_mm | Inventory-aware market maker (A-S model) |
| mean_reversion | Trade on SMA deviations |
| hedge_agent | Reduces excess exposure |
| rfq_agent | Block-size dark RFQ liquidity |
| aggressive_taker | Directional spread crossing |
| claude_agent | Claude-powered LLM trading agent |

## Instruments

- **Standard perps**: ETH-PERP
- **YEX markets**: VXX-USDYP (yex:VXX), US3M-USDYP (yex:US3M)

## Workflow

1. Check account: `hl account`
2. Mock test: `hl run avellaneda_mm --mock --max-ticks 5`
3. Dry run: `hl run avellaneda_mm --dry-run --max-ticks 10`
4. Live testnet: `hl run avellaneda_mm -i ETH-PERP --tick 10`
5. Monitor: `hl status --watch`

## LLM Agent

```bash
hl run claude_agent --mock --max-ticks 5 --tick 15
hl run claude_agent -i VXX-USDYP --tick 30 --model claude-sonnet-4-20250514
```
