"""Emerging movers detector configuration — thresholds, weights, and presets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class MoversConfig:
    """Configuration for the emerging movers detector."""

    # OI Delta thresholds
    oi_delta_immediate_pct: float = 15.0
    oi_delta_breakout_pct: float = 8.0
    oi_baseline_window: int = 6

    # Volume Surge thresholds
    volume_surge_ratio: float = 3.0
    volume_surge_immediate: float = 5.0
    volume_min_24h: float = 500_000.0

    # Funding Shift thresholds
    funding_flip_threshold: float = 0.0002
    funding_acceleration_pct: float = 50.0

    # Price Momentum thresholds
    breakout_lookback_bars: int = 24
    breakout_exceed_pct: float = 1.5

    # Quality filters
    erratic_max_reversals: int = 5
    erratic_window: int = 10
    min_scans_for_signal: int = 2

    # Signal confidence weights
    signal_weights: Dict[str, float] = field(default_factory=lambda: {
        "IMMEDIATE_MOVER": 100.0,
        "VOLUME_SURGE": 70.0,
        "OI_BREAKOUT": 60.0,
        "FUNDING_FLIP": 50.0,
    })

    # History
    scan_history_size: int = 30

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "MoversConfig":
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def from_yaml(cls, path: str) -> "MoversConfig":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


MOVERS_PRESETS: Dict[str, MoversConfig] = {
    "default": MoversConfig(),
    "sensitive": MoversConfig(
        oi_delta_immediate_pct=10.0,
        oi_delta_breakout_pct=5.0,
        volume_surge_ratio=2.0,
        volume_min_24h=200_000.0,
    ),
}
