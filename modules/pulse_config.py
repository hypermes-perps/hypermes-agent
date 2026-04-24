"""Pulse detector configuration — thresholds, weights, and presets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PulseConfig:
    """Configuration for the Pulse detector."""

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
        # 5-tier taxonomy
        "FIRST_JUMP": 100.0,
        "CONTRIB_EXPLOSION": 95.0,
        "NEW_ENTRY_DEEP": 65.0,
        "DEEP_CLIMBER": 55.0,
    })

    # --- Signal taxonomy (5-tier) thresholds ---
    # Tier 2: CONTRIB_EXPLOSION — simultaneous extreme OI + volume
    contrib_explosion_oi_pct: float = 15.0
    contrib_explosion_vol_mult: float = 5.0

    # Tier 4: NEW_ENTRY_DEEP — OI grows but volume stays low (limit-order accumulation)
    new_entry_deep_oi_pct: float = 8.0
    new_entry_deep_max_vol_mult: float = 1.5

    # Tier 5: DEEP_CLIMBER — sustained OI climb over N scan windows
    deep_climber_min_windows: int = 3
    deep_climber_min_oi_pct: float = 5.0  # per window

    # Sector mapping for FIRST_JUMP detection (instrument → sector)
    sector_map: Dict[str, str] = field(default_factory=dict)

    # History
    scan_history_size: int = 30

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PulseConfig":
        valid = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in valid})

    @classmethod
    def from_yaml(cls, path: str) -> "PulseConfig":
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


PULSE_PRESETS: Dict[str, PulseConfig] = {
    "default": PulseConfig(),
    "sensitive": PulseConfig(
        oi_delta_immediate_pct=10.0,
        oi_delta_breakout_pct=5.0,
        volume_surge_ratio=2.0,
        volume_min_24h=200_000.0,
    ),
    # Tuned for 3-market yex testnet competition. Generates signals on
    # tiny moves so the agent rotates frequently and produces visible
    # PnL. Not safe for mainnet trading.
    "competition": PulseConfig(
        oi_delta_immediate_pct=3.0,    # was 15.0
        oi_delta_breakout_pct=1.5,     # was 8.0
        oi_baseline_window=3,          # was 6 — quicker baselines for short cohorts
        volume_surge_ratio=1.3,        # was 3.0
        volume_surge_immediate=2.0,    # was 5.0
        volume_min_24h=50_000.0,       # was 500_000
        funding_flip_threshold=0.0001, # was 0.0002
        breakout_exceed_pct=0.4,       # was 1.5
        min_scans_for_signal=1,        # was 2
        contrib_explosion_oi_pct=3.0,  # was 15.0
        contrib_explosion_vol_mult=1.5, # was 5.0
        new_entry_deep_oi_pct=1.5,     # was 8.0
        new_entry_deep_max_vol_mult=3.0, # was 1.5
        deep_climber_min_windows=2,    # was 3
        deep_climber_min_oi_pct=1.0,   # was 5.0
    ),
}
