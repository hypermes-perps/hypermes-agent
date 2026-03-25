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
| `claude_agent` | LLM | Multi-model AI agent (Gemini/Claude/OpenAI) |

## Custom Strategies

You can write and run your own strategy without modifying the repo. Create a Python file that subclasses `BaseStrategy`:

```python
# my_strategies/momentum.py
from sdk.strategy_sdk.base import BaseStrategy, StrategyContext
from common.models import MarketSnapshot, StrategyDecision

class MomentumStrategy(BaseStrategy):
    def __init__(self, strategy_id="momentum", lookback=10, threshold=0.5, size=0.1, **kwargs):
        super().__init__(strategy_id=strategy_id)
        self.lookback = lookback
        self.threshold = threshold
        self.size = size
        self._prices = []

    def on_tick(self, snapshot, context=None):
        mid = snapshot.mid_price
        if mid <= 0:
            return []

        self._prices.append(mid)
        if len(self._prices) < self.lookback:
            return []  # not enough data yet

        # Simple momentum: compare current price to lookback price
        old = self._prices[-self.lookback]
        pct_change = (mid - old) / old * 100

        if pct_change > self.threshold:
            return [StrategyDecision(
                action="place_order",
                instrument=snapshot.instrument,
                side="buy",
                size=self.size,
                limit_price=round(snapshot.ask, 2),
            )]
        elif pct_change < -self.threshold:
            return [StrategyDecision(
                action="place_order",
                instrument=snapshot.instrument,
                side="sell",
                size=self.size,
                limit_price=round(snapshot.bid, 2),
            )]
        return []
```

Run it by passing the full `module:ClassName` path:

```bash
hl run my_strategies.momentum:MomentumStrategy -i ETH-PERP --tick 10
```

### Strategy Interface

Every strategy receives two objects each tick:

| Object | Fields |
|--------|--------|
| `MarketSnapshot` | `mid_price`, `bid`, `ask`, `spread_bps`, `funding_rate`, `open_interest`, `volume_24h`, `timestamp_ms` |
| `StrategyContext` | `position_qty`, `position_notional`, `unrealized_pnl`, `realized_pnl`, `reduce_only`, `safe_mode`, `round_number`, `meta` |

Return a list of `StrategyDecision` objects:

```python
StrategyDecision(
    action="place_order",  # or "noop" to skip
    instrument="ETH-PERP",
    side="buy",            # or "sell"
    size=0.1,
    limit_price=2050.0,
    meta={"signal": "my_signal"},  # optional metadata
)
```

The engine handles everything else: risk checks, order execution, position tracking, PnL, and state persistence.

### Passing Parameters

Strategy constructor `**kwargs` come from the YAML config's `strategy_params` or the registry defaults:

```yaml
strategy: my_strategies.momentum:MomentumStrategy
strategy_params:
  lookback: 20
  threshold: 0.3
  size: 0.05
```

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

### Claim Testnet USDyP

To trade YEX markets on testnet, you need USDyP tokens. Claim them with:

```bash
curl --location 'https://api-temp.nunchi.trade/api/v1/yex/usdyp-claim' \
  --header 'x-network: testnet' \
  --header 'Content-Type: application/json' \
  --data '{"userAddress":"<YOUR_WALLET_ADDRESS>"}'
```

## LLM Agent (Multi-Model)

The `claude_agent` strategy uses structured tool/function calling to make trading decisions. It auto-detects the provider from the model name:

| Provider | Models | Env Variable |
|----------|--------|-------------|
| Google Gemini | `gemini-2.0-flash` (default), `gemini-2.5-pro` | `GEMINI_API_KEY` |
| Anthropic Claude | `claude-haiku-4-5-20251001`, `claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| OpenAI | `gpt-4o`, `gpt-4o-mini`, `o3-mini` | `OPENAI_API_KEY` |

```bash
# Gemini (default)
export GEMINI_API_KEY=...
hl run claude_agent -i ETH-PERP --tick 15

# Claude
export ANTHROPIC_API_KEY=sk-ant-...
hl run claude_agent -i ETH-PERP --tick 15 --model claude-haiku-4-5-20251001

# OpenAI
export OPENAI_API_KEY=sk-...
hl run claude_agent -i ETH-PERP --tick 15 --model gpt-4o
```

Each tick, the LLM receives market data, position state, and risk context, then calls `place_order` or `hold` via structured tool use. The engine applies risk checks on top — the LLM can't bypass position limits or drawdown controls.

## Install as a Claude Code Skill

```bash
# 1. Clone and install the CLI
git clone https://github.com/Nunchi-trade/agent-cli.git ~/agent-cli
cd ~/agent-cli && pip install -e .

# 2. Install the skill
mkdir -p ~/.claude/skills/yex-trader
cp ~/agent-cli/cli/skill.md ~/.claude/skills/yex-trader/SKILL.md
```

Claude Code will automatically discover it. Use `/yex-trader` or ask Claude to run trading strategies — it knows all the commands.

## Install as an OpenClaw Skill

```bash
# 1. Clone and install the CLI
git clone https://github.com/Nunchi-trade/agent-cli.git ~/agent-cli
cd ~/agent-cli && pip install -e .

# 2. Install the skill via ClawHub (if published)
clawhub install nunchi-trade/yex-trader

# Or manually copy the skill file
mkdir -p ~/.openclaw/workspace/skills/yex-trader
cp ~/agent-cli/cli/skill.md ~/.openclaw/workspace/skills/yex-trader/SKILL.md
```

The skill uses the [Agent Skills](https://agentskills.io) open standard — the same `SKILL.md` format works for both Claude Code and OpenClaw.

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
