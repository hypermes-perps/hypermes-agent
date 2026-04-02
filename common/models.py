"""Shared Pydantic models for the trading system."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    instrument: str = "ETH-PERP"
    mid_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread_bps: float = 0.0
    timestamp_ms: int = 0
    volume_24h: float = 0.0
    funding_rate: float = 0.0
    open_interest: float = 0.0


class VerifyResult(BaseModel):
    ok: bool
    checks: Dict[str, bool] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


class StrategyDecision(BaseModel):
    action: str = "noop"  # "place_order" or "noop"
    instrument: str = "ETH-PERP"
    side: str = ""        # "buy" or "sell"
    size: float = 0.0
    limit_price: float = 0.0
    meta: Dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    """Individual decision — matches KorAI MVP Listing 1 inner 'decision' object."""
    decision_id: str
    strategy_id: str = ""
    action: str = "limit_order"  # quote | limit_order | hedge
    instrument: str = "ETH"
    side: Optional[str] = None   # buy | sell | null
    size: float = 0.0
    limit_price: float = 0.0
    timestamp_ms: int = 0
