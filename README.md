# YEX Trader — Autonomous Hyperliquid Trading CLI

Autonomous trading agent for [Hyperliquid](https://hyperliquid.xyz) perps and [YEX](https://yex.trade) yield markets. Ships with 7 built-in strategies (market making, mean reversion, hedging) plus a Claude-powered LLM trading agent.

Works as a standalone CLI, a **Claude Code skill**, or an **OpenClaw AgentSkill**.

## Quick Start

```bash
git clone https://github.com/Nunchi-trade/agent-cli.git
cd agent-cli
pip install -e .

# Set your HL private key
export HL_PRIVATE_KEY=0x...

# Mock test (no connection needed)
hl run avellaneda_mm --mock --max-ticks 10

# Live testnet
hl run avellaneda_mm -i ETH-PERP --tick 10

# YEX market
hl run avellaneda_mm -i VXX-USDYP --tick 15
```

## Strategies

| Name | Type | Description |
|------|------|-------------|
| `simple_mm` | Market Making | Symmetric bid/ask quoting around mid |
| `avellaneda_mm` | Market Making | Inventory-aware Avellaneda-Stoikov model |
| `mean_reversion` | Statistical | Trade on SMA deviations |
| `hedge_agent` | Risk | Reduces excess exposure |
| `rfq_agent` | Liquidity | Block-size dark RFQ flow |
| `aggressive_taker` | Directional | Crosses spread with directional bias |
| `claude_agent` | LLM | Claude-powered AI trading agent |

## Commands

```bash
hl run <strategy> [options]   # Start autonomous trading
hl status [--watch]           # Show positions, PnL, risk
hl trade <inst> <side> <size> # Place a single order
hl account                    # Show HL account state
hl strategies                 # List all strategies
```

### Run Options

| Flag | Default | Description |
|------|---------|-------------|
| `-i, --instrument` | ETH-PERP | Trading instrument |
| `-t, --tick` | 10.0 | Seconds between ticks |
| `-c, --config` | — | YAML config file |
| `--mainnet` | false | Use mainnet (default: testnet) |
| `--dry-run` | false | Run without placing orders |
| `--mock` | false | Use mock market data |
| `--max-ticks` | 0 | Stop after N ticks (0 = forever) |
| `--resume/--fresh` | resume | Resume or start fresh |
| `--model` | — | LLM model override (claude_agent) |

## YEX Markets

[YEX](https://yex.trade) (Nunchi HIP-3) yield perpetuals on Hyperliquid:

| Instrument | HL Coin | Description |
|------------|---------|-------------|
| VXX-USDYP | yex:VXX | Volatility index yield perp |
| US3M-USDYP | yex:US3M | US 3M Treasury rate yield perp |

```bash
hl run avellaneda_mm -i VXX-USDYP --tick 15
hl run claude_agent -i US3M-USDYP --tick 30
```

## Claude Agent (LLM Strategy)

The `claude_agent` strategy uses Claude's tool_use API to make trading decisions each tick.

```bash
# Install LLM support
pip install -e ".[llm]"

export ANTHROPIC_API_KEY=sk-ant-...

# Default: Haiku (fast, cheap)
hl run claude_agent -i ETH-PERP --tick 15

# Upgrade to Sonnet
hl run claude_agent -i ETH-PERP --tick 15 --model claude-sonnet-4-20250514
```

Each tick, Claude receives market data, position state, and risk context, then decides to `place_order` or `hold` using structured tool calls.

## Use as a Claude Code Skill

Copy the skill into your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills/yex-trader
cp cli/skill.md ~/.claude/skills/yex-trader/SKILL.md
```

Then in Claude Code, the agent can run trading commands directly.

## Use as an OpenClaw AgentSkill

The OpenClaw skill config is at `cli/openclaw_skill.json`. Register it with your OpenClaw agent:

```json
{
  "name": "yex-trader",
  "actions": ["run_strategy", "check_status", "place_trade", "check_account", "list_strategies"]
}
```

## Configuration

Create a YAML config (see `cli/config_example.yaml`):

```yaml
strategy: avellaneda_mm
strategy_params:
  gamma: 0.1
  k: 1.5
  base_size: 0.5

instrument: ETH-PERP
tick_interval: 10.0

max_position_qty: 5.0
max_notional_usd: 15000
max_order_size: 2.0
max_daily_drawdown_pct: 2.5

mainnet: false
dry_run: false
```

```bash
hl run avellaneda_mm --config my_config.yaml
```

## Architecture

```
cli/           → CLI commands and trading engine
strategies/    → Trading strategy implementations
sdk/           → Strategy base class and loader
common/        → Shared data models
parent/        → HL API proxy, position tracking, risk management
```

The engine runs an autonomous tick loop:
1. Fetch market snapshot from HL
2. Pre-tick risk check (drawdown, leverage, position limits)
3. Run strategy with full context (position, PnL, risk state)
4. Filter orders through risk manager
5. Execute via IOC orders on Hyperliquid
6. Track fills, update positions, persist state

## License

MIT
