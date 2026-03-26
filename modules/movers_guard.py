"""MoversGuard — bridge between pure engine, persistence, and logging."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from modules.movers_config import MoversConfig
from modules.movers_engine import EmergingMoversEngine
from modules.movers_state import MoversHistoryStore, MoverScanResult

log = logging.getLogger("movers_guard")


class MoversGuard:
    """Owns engine + history store + logging."""

    def __init__(
        self,
        config: Optional[MoversConfig] = None,
        history_store: Optional[MoversHistoryStore] = None,
    ):
        self.config = config or MoversConfig()
        self.engine = EmergingMoversEngine(self.config)
        self.history = history_store or MoversHistoryStore(
            max_size=self.config.scan_history_size,
        )
        self.last_result: Optional[MoverScanResult] = None

    def scan(
        self,
        all_markets: list,
        asset_candles: Dict[str, Dict[str, List[Dict]]],
    ) -> MoverScanResult:
        """Run scan, persist results, log summary."""
        scan_history = self.history.get_history()

        result = self.engine.scan(
            all_markets=all_markets,
            asset_candles=asset_candles,
            scan_history=scan_history,
        )

        self.history.save_scan(result)
        self.last_result = result

        stats = result.stats
        log.info(
            "Movers scan: %d assets → %d qualifying → %d signals (history=%d)",
            stats.get("total_assets", 0),
            stats.get("qualifying", 0),
            stats.get("signals_detected", 0),
            stats.get("history_depth", 0),
        )

        for sig in result.signals[:5]:
            erratic_flag = " [ERRATIC]" if sig.is_erratic else ""
            log.info(
                "  %s %s %s conf=%.0f OI=%+.1f%% vol=%.1fx fund=%+.6f%s",
                sig.signal_type, sig.direction, sig.asset,
                sig.confidence, sig.oi_delta_pct,
                sig.volume_surge_ratio, sig.funding_shift, erratic_flag,
            )

        return result
