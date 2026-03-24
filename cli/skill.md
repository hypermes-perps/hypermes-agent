# YEX Trader Skill

Autonomous Hyperliquid trading via the agent-cli. Direct HL API execution with deterministic and LLM-powered strategies.

## Setup

```bash
cd ~/agent-cli
export HL_PRIVATE_KEY=0x...          # Required for live trading
export ANTHROPIC_API_KEY=sk-ant-...  # Required for claude_agent strategy
```

## Commands

### Start autonomous trading
```bash
cd ~/agent-cli && python3 -m cli.main run <strategy> [options]
```
Options: `--instrument/-i`, `--tick/-t` (seconds), `--config/-c` (YAML), `--mainnet`, `--dry-run`, `--mock`, `--max-ticks`, `--resume/--fresh`, `--model` (LLM override)

### Check status
```bash
cd ~/agent-cli && python3 -m cli.main status [--watch] [--interval 5]
```

### Place a single order
```bash
cd ~/agent-cli && python3 -m cli.main trade <instrument> <side> <size>
```

### Account info
```bash
cd ~/agent-cli && python3 -m cli.main account [--mainnet]
```

### List strategies
```bash
cd ~/agent-cli && python3 -m cli.main strategies
```

## Available Strategies

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

## Recommended Workflow

1. Check account: `python3 -m cli.main account`
2. Validate with mock: `python3 -m cli.main run avellaneda_mm --mock --max-ticks 5`
3. Dry run: `python3 -m cli.main run avellaneda_mm --dry-run --max-ticks 10`
4. Live (testnet): `python3 -m cli.main run avellaneda_mm -i ETH-PERP --tick 10`
5. Monitor: `python3 -m cli.main status --watch`

## LLM Agent

```bash
python3 -m cli.main run claude_agent --mock --max-ticks 5 --tick 15
python3 -m cli.main run claude_agent -i VXX-USDYP --tick 30 --model claude-sonnet-4-20250514
```
