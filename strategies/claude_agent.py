"""Claude-powered LLM trading agent.

Uses Claude API with structured tool_use to make trading decisions each tick.
The LLM receives market data, position state, and risk context, then decides
to place orders or hold.

Usage:
    hl run claude_agent --mock --max-ticks 5 --tick 15
    hl run claude_agent -i ETH-PERP --tick 15
    hl run claude_agent -i VXX-USDYP --tick 30 --model claude-sonnet-4-20250514
"""
from __future__ import annotations

import logging
import os
import time
from collections import deque
from typing import Any, Dict, List, Optional

from common.models import MarketSnapshot, StrategyDecision
from sdk.strategy_sdk.base import BaseStrategy, StrategyContext

log = logging.getLogger("claude_agent")

# ---------------------------------------------------------------------------
# System prompt — defines the agent's trading persona
# ---------------------------------------------------------------------------

DEFAULT_SYSTEM_PROMPT = """\
You are an autonomous trading agent operating on Hyperliquid.

Each tick you receive a market data snapshot and your current position state.
You must decide whether to place an order or hold.

Rules:
- You manage a single instrument position
- You receive: price data (mid, bid, ask, spread, funding), your position \
(qty, entry price, unrealized PnL, realized PnL), risk state, and recent history
- You MUST use exactly one tool call: either place_order or hold
- Consider: price trend, spread width, funding rate, your inventory, drawdown
- Be conservative: use small sizes, tight risk management
- If reduce_only is true, you may ONLY reduce your current position \
(sell if long, buy if short)
- If safe_mode is true, you MUST hold — no orders allowed
- Keep reasoning brief (1-2 sentences)
"""

# ---------------------------------------------------------------------------
# Tool definitions for Claude tool_use
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "place_order",
        "description": "Place a limit order on the exchange. "
        "The order will be IOC (immediate-or-cancel).",
        "input_schema": {
            "type": "object",
            "properties": {
                "side": {
                    "type": "string",
                    "enum": ["buy", "sell"],
                    "description": "Order side",
                },
                "size": {
                    "type": "number",
                    "description": "Order size in base asset units",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price in USD",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Brief reasoning for this trade",
                },
            },
            "required": ["side", "size", "price", "reasoning"],
        },
    },
    {
        "name": "hold",
        "description": "Do nothing this tick — place no orders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reasoning": {
                    "type": "string",
                    "description": "Why you are holding this tick",
                },
            },
            "required": ["reasoning"],
        },
    },
]

# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------


class ClaudeStrategy(BaseStrategy):
    """LLM-powered trading strategy using Claude API with tool_use."""

    def __init__(
        self,
        strategy_id: str = "claude_agent",
        model: str = "claude-haiku-4-5-20251001",
        base_size: float = 0.5,
        max_position: float = 5.0,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_tokens: int = 256,
        price_history_len: int = 20,
        fill_history_len: int = 10,
    ):
        super().__init__(strategy_id=strategy_id)
        self.model = model
        self.base_size = base_size
        self.max_position = max_position
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens

        # Rolling history buffers
        self._price_history: deque = deque(maxlen=price_history_len)
        self._fill_history: deque = deque(maxlen=fill_history_len)

        # Token usage tracking
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._api_calls = 0

        # Lazy-init the client (requires ANTHROPIC_API_KEY)
        self._client = None

    def _get_client(self):
        """Lazy-initialize the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                raise ImportError(
                    "anthropic package required for claude_agent strategy. "
                    "Install with: pip3 install anthropic"
                )

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is required "
                    "for claude_agent strategy"
                )
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    # ------------------------------------------------------------------
    # Build prompt
    # ------------------------------------------------------------------

    def _build_user_message(
        self,
        snapshot: MarketSnapshot,
        context: Optional[StrategyContext],
    ) -> str:
        """Build the user message with market data and position context."""
        parts = []

        # Market data
        parts.append(f"=== MARKET DATA (Tick {context.round_number if context else '?'}) ===")
        parts.append(f"Instrument: {snapshot.instrument}")
        parts.append(f"Mid: {snapshot.mid_price:.4f}")
        parts.append(f"Bid: {snapshot.bid:.4f}  Ask: {snapshot.ask:.4f}")
        parts.append(f"Spread: {snapshot.spread_bps:.1f} bps")
        parts.append(f"Funding rate: {snapshot.funding_rate:.6f}")
        parts.append(f"Open interest: {snapshot.open_interest:.0f}")
        parts.append(f"24h volume: {snapshot.volume_24h:.0f}")
        parts.append("")

        # Position state
        if context:
            parts.append("=== YOUR POSITION ===")
            parts.append(f"Qty: {context.position_qty:+.4f}")
            parts.append(f"Notional: ${context.position_notional:.2f}")
            parts.append(f"Unrealized PnL: ${context.unrealized_pnl:+.2f}")
            parts.append(f"Realized PnL: ${context.realized_pnl:+.2f}")
            parts.append("")

            # Risk state
            parts.append("=== RISK STATE ===")
            dd_pct = context.meta.get("drawdown_pct", 0.0) * 100
            parts.append(f"Reduce only: {context.reduce_only}")
            parts.append(f"Safe mode: {context.safe_mode}")
            parts.append(f"Drawdown: {dd_pct:.2f}%")
            parts.append("")

        # Price history
        if self._price_history:
            parts.append("=== RECENT PRICES (newest first) ===")
            for mid, ts in reversed(self._price_history):
                parts.append(f"  {mid:.4f}")
            parts.append("")

        # Recent fills
        if self._fill_history:
            parts.append("=== RECENT FILLS ===")
            for fill in reversed(list(self._fill_history)):
                parts.append(
                    f"  {fill['side'].upper()} {fill['size']:.4f} "
                    f"@ {fill['price']:.4f}"
                )
            parts.append("")

        # Constraints
        parts.append(f"=== CONSTRAINTS ===")
        parts.append(f"Max order size: {self.base_size}")
        parts.append(f"Max position: {self.max_position}")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Parse response
    # ------------------------------------------------------------------

    def _parse_response(
        self, response, snapshot: MarketSnapshot
    ) -> List[StrategyDecision]:
        """Parse Claude's tool_use response into StrategyDecisions."""
        decisions = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "place_order":
                inp = block.input
                side = inp.get("side", "")
                size = float(inp.get("size", 0))
                price = float(inp.get("price", 0))
                reasoning = inp.get("reasoning", "")

                if side not in ("buy", "sell") or size <= 0 or price <= 0:
                    log.warning("Invalid order from LLM: side=%s size=%s price=%s",
                                side, size, price)
                    continue

                # Clamp size to base_size
                size = min(size, self.base_size)

                decisions.append(StrategyDecision(
                    action="place_order",
                    instrument=snapshot.instrument,
                    side=side,
                    size=size,
                    limit_price=round(price, 2),
                    meta={
                        "signal": "claude_agent",
                        "reasoning": reasoning,
                        "model": self.model,
                    },
                ))
                log.info("LLM decision: %s %.4f @ %.2f — %s",
                         side.upper(), size, price, reasoning)

            elif block.name == "hold":
                reasoning = block.input.get("reasoning", "")
                log.info("LLM decision: HOLD — %s", reasoning)

        return decisions

    # ------------------------------------------------------------------
    # Core tick
    # ------------------------------------------------------------------

    def on_tick(
        self,
        snapshot: MarketSnapshot,
        context: Optional[StrategyContext] = None,
    ) -> List[StrategyDecision]:
        """Call Claude API with market data, return trading decisions."""
        if snapshot.mid_price <= 0:
            return []

        # Safe mode = must hold
        if context and context.safe_mode:
            log.info("Safe mode active, holding")
            return []

        # Update price history
        self._price_history.append((snapshot.mid_price, snapshot.timestamp_ms))

        # Build the prompt
        user_msg = self._build_user_message(snapshot, context)

        try:
            client = self._get_client()
            t0 = time.time()

            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=self.system_prompt,
                tools=TOOLS,
                tool_choice={"type": "any"},
                messages=[{"role": "user", "content": user_msg}],
            )

            elapsed_ms = (time.time() - t0) * 1000
            self._api_calls += 1
            self._total_input_tokens += response.usage.input_tokens
            self._total_output_tokens += response.usage.output_tokens

            log.info(
                "Claude API: %dms, %d in / %d out tokens (cumulative: %d calls, %d in, %d out)",
                elapsed_ms,
                response.usage.input_tokens,
                response.usage.output_tokens,
                self._api_calls,
                self._total_input_tokens,
                self._total_output_tokens,
            )

            decisions = self._parse_response(response, snapshot)

            # Record fills in history (for next tick's context)
            for d in decisions:
                if d.action == "place_order":
                    self._fill_history.append({
                        "side": d.side,
                        "size": d.size,
                        "price": d.limit_price,
                    })

            return decisions

        except Exception as e:
            log.error("Claude API call failed: %s", e)
            return []
