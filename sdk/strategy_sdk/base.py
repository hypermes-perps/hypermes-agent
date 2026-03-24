"""Base strategy interface — all strategies implement this."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common.models import MarketSnapshot, StrategyDecision


class StrategyContext(BaseModel):
    """Rich context passed to strategies each tick.

    Provides position, PnL, and risk state so strategies can make
    inventory-aware decisions.
    """
    snapshot: MarketSnapshot = Field(default_factory=MarketSnapshot)
    position_qty: float = 0.0          # net position in base asset
    position_notional: float = 0.0     # notional USD exposure
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    reduce_only: bool = False          # from risk manager
    safe_mode: bool = False
    round_number: int = 0
    meta: Dict[str, Any] = Field(default_factory=dict)


class BaseStrategy(ABC):
    def __init__(self, strategy_id: str = "unnamed"):
        self.strategy_id = strategy_id

    @abstractmethod
    def on_tick(self, snapshot: MarketSnapshot,
                context: Optional[StrategyContext] = None) -> List[StrategyDecision]:
        """Called each tick with current market data.

        Args:
            snapshot: Current market data snapshot.
            context: Optional rich context with position/risk info.
                     None for legacy/stateless mode.

        Return a list of StrategyDecisions (orders to submit this round).
        Return an empty list or [StrategyDecision(action="noop")] to skip.
        """
        ...
