"""Hyperliquid API proxy — market data + order placement.

MockHLProxy for development; HLProxy for real HL testnet/mainnet.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from common.models import MarketSnapshot

log = logging.getLogger("hl_proxy")

ZERO = Decimal("0")


@dataclass
class HLFill:
    """A fill received from Hyperliquid."""
    oid: str
    instrument: str
    side: str
    price: Decimal
    quantity: Decimal
    timestamp_ms: int
    fee: Decimal = ZERO


class MockHLProxy:
    """Fake HL proxy for local development — simulates market data and fills."""

    def __init__(self, base_price: float = 2500.0, spread_bps: float = 2.0):
        self.base_price = base_price
        self.spread_bps = spread_bps
        self.placed_orders: List[Dict] = []
        self.fills: List[HLFill] = []
        self._tick = 0

    def get_snapshot(self, instrument: str = "ETH-PERP") -> MarketSnapshot:
        """Generate a mock market data snapshot."""
        import random
        drift = random.uniform(-5, 5)
        mid = self.base_price + drift
        half_spread = mid * (self.spread_bps / 10000 / 2)

        self._tick += 1
        return MarketSnapshot(
            instrument=instrument,
            mid_price=round(mid, 2),
            bid=round(mid - half_spread, 2),
            ask=round(mid + half_spread, 2),
            spread_bps=round(self.spread_bps, 2),
            timestamp_ms=int(time.time() * 1000),
            volume_24h=round(random.uniform(1e6, 5e6), 0),
            funding_rate=round(random.uniform(-0.001, 0.001), 6),
            open_interest=round(random.uniform(1e5, 5e5), 0),
        )

    def place_orders_from_clearing(self, fills: List[Dict]) -> List[Dict]:
        """Convert clearing fills into HL orders.

        In mock mode, just records them and generates fake fills.
        Returns list of placed order records.
        """
        placed = []
        for f in fills:
            qty = Decimal(str(f.get("quantity_filled", "0")))
            if qty <= ZERO:
                continue

            order = {
                "instrument": f["instrument"],
                "side": f["side"],
                "price": str(f["fill_price"]),
                "quantity": str(qty),
                "agent_id": f["agent_id"],
                "type": "limit",
                "time_in_force": "IOC",
                "timestamp_ms": int(time.time() * 1000),
            }
            placed.append(order)
            self.placed_orders.append(order)

            # In mock mode, all orders are immediately filled
            self.fills.append(HLFill(
                oid=f"mock-{len(self.fills)}",
                instrument=f["instrument"],
                side=f["side"],
                price=Decimal(str(f["fill_price"])),
                quantity=qty,
                timestamp_ms=int(time.time() * 1000),
            ))

        log.info("Placed %d orders (%d cumulative fills)", len(placed), len(self.fills))
        return placed

    def get_fills(self, since_ms: int = 0) -> List[HLFill]:
        """Get fills since a given timestamp."""
        return [f for f in self.fills if f.timestamp_ms >= since_ms]


class HLProxy:
    """Real Hyperliquid proxy using hyperliquid-python-sdk.

    Requires:
      - HL_PRIVATE_KEY env var (for signing orders)
      - HL_API_URL env var (defaults to testnet)
    """

    def __init__(self, private_key: Optional[str] = None, testnet: bool = True):
        import os
        self.private_key = private_key or os.environ.get("HL_PRIVATE_KEY", "")
        self.testnet = testnet
        self._info = None
        self._exchange = None
        self._address = None
        self.placed_orders: List[Dict] = []
        self.fills: List[HLFill] = []

    def _ensure_client(self):
        if self._info is not None:
            return
        from eth_account import Account
        from hyperliquid.info import Info
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils import constants

        base_url = constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
        self._info = Info(base_url, skip_ws=True)

        account = Account.from_key(self.private_key)
        self._address = account.address
        self._exchange = Exchange(account, base_url)
        log.info("HL client initialized: %s (testnet=%s)", self._address, self.testnet)

        # Set max leverage for all assets we trade
        for coin in ["ETH"]:
            try:
                self._exchange.update_leverage(25, coin, is_cross=True)
                log.info("Set %s leverage to 25x cross", coin)
            except Exception as e:
                log.warning("Failed to set %s leverage: %s", coin, e)

    @staticmethod
    def _hl_coin(instrument: str) -> str:
        """Convert internal instrument name to HL coin name (ETH-PERP → ETH)."""
        return instrument.replace("-PERP", "").replace("-perp", "")

    def get_snapshot(self, instrument: str = "ETH-PERP") -> MarketSnapshot:
        """Get real market data from HL."""
        self._ensure_client()
        try:
            coin = self._hl_coin(instrument)
            book = self._info.l2_snapshot(coin)
            bids = book.get("levels", [[]])[0] if book.get("levels") else []
            asks = book.get("levels", [[], []])[1] if len(book.get("levels", [])) > 1 else []

            best_bid = float(bids[0]["px"]) if bids else 0.0
            best_ask = float(asks[0]["px"]) if asks else 0.0
            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
            spread = ((best_ask - best_bid) / mid * 10000) if mid > 0 else 0.0

            return MarketSnapshot(
                instrument=instrument,
                mid_price=round(mid, 2),
                bid=round(best_bid, 2),
                ask=round(best_ask, 2),
                spread_bps=round(spread, 2),
                timestamp_ms=int(time.time() * 1000),
            )
        except Exception as e:
            log.error("Failed to get HL snapshot: %s", e)
            return MarketSnapshot(instrument=instrument)

    def place_orders_from_clearing(self, fills: List[Dict]) -> List[Dict]:
        """Place real orders on HL from clearing fills.

        Uses market-crossing IOC prices to guarantee execution:
        buys at ask + 0.5% slippage, sells at bid - 0.5% slippage.
        """
        self._ensure_client()
        placed = []

        # Get current orderbook for market-crossing prices
        ob_cache: Dict[str, Dict[str, float]] = {}
        for f in fills:
            inst = f["instrument"]
            if inst not in ob_cache:
                try:
                    snap = self.get_snapshot(inst)
                    ob_cache[inst] = {"bid": float(snap.bid), "ask": float(snap.ask)}
                except Exception:
                    ob_cache[inst] = {"bid": 0.0, "ask": 0.0}

        for f in fills:
            qty = Decimal(str(f.get("quantity_filled", "0")))
            if qty <= ZERO:
                continue

            is_buy = f["side"] == "buy"
            sz = float(qty)
            inst = f["instrument"]
            ob = ob_cache.get(inst, {"bid": 0.0, "ask": 0.0})

            # Use aggressive market-crossing price (0.5% slippage)
            if is_buy:
                price = round(ob["ask"] * 1.005, 1)  # above ask
            else:
                price = round(ob["bid"] * 0.995, 1)  # below bid

            if price <= 0:
                price = float(f["fill_price"])  # fallback to clearing price

            try:
                coin = self._hl_coin(inst)
                result = self._exchange.order(
                    coin,
                    is_buy,
                    sz,
                    price,
                    {"limit": {"tif": "Ioc"}},
                )

                # Handle top-level error
                if result.get("status") == "err":
                    log.warning("HL order rejected: %s %s %s @ %s — %s",
                                f["side"], sz, f["instrument"], price, result.get("response"))
                    continue

                # Parse successful response
                resp = result.get("response", {})
                if not isinstance(resp, dict):
                    log.warning("HL unexpected response: %s", resp)
                    continue

                statuses = resp.get("data", {}).get("statuses", [])
                status = statuses[0] if statuses else {}

                if isinstance(status, str):
                    log.warning("HL order status string: %s", status)
                elif "filled" in status:
                    filled_info = status["filled"]
                    self.fills.append(HLFill(
                        oid=filled_info.get("oid", ""),
                        instrument=f["instrument"],
                        side=f["side"],
                        price=Decimal(str(filled_info.get("avgPx", price))),
                        quantity=Decimal(str(filled_info.get("totalSz", sz))),
                        timestamp_ms=int(time.time() * 1000),
                    ))
                    log.info("HL filled: %s %s %s @ %s",
                             f["side"], filled_info.get("totalSz", sz),
                             f["instrument"], filled_info.get("avgPx", price))
                elif "resting" in status:
                    log.info("HL resting: %s %s %s @ %s", f["side"], sz, f["instrument"], price)
                elif "error" in status:
                    log.info("HL no fill: %s %s %s @ %s — %s",
                             f["side"], sz, f["instrument"], price, status["error"])
                else:
                    log.warning("HL order status: %s", status)

                placed.append(f)
                self.placed_orders.append(f)
            except Exception as e:
                log.error("HL order failed: %s %s %s @ %s — %s",
                          f["side"], sz, f["instrument"], price, e)

        log.info("Placed %d/%d orders on HL", len(placed),
                 sum(1 for f in fills if Decimal(str(f.get("quantity_filled", "0"))) > ZERO))
        return placed

    def get_fills(self, since_ms: int = 0) -> List[HLFill]:
        """Get fills from HL user state."""
        if self._info and self._address:
            try:
                user_fills = self._info.user_fills(self._address)
                for uf in user_fills:
                    ts = int(uf.get("time", 0))
                    if ts >= since_ms:
                        self.fills.append(HLFill(
                            oid=uf.get("oid", ""),
                            instrument=uf.get("coin", ""),
                            side=uf.get("side", "").lower(),
                            price=Decimal(str(uf.get("px", "0"))),
                            quantity=Decimal(str(uf.get("sz", "0"))),
                            timestamp_ms=ts,
                            fee=Decimal(str(uf.get("fee", "0"))),
                        ))
            except Exception as e:
                log.error("Failed to fetch HL fills: %s", e)
        return [f for f in self.fills if f.timestamp_ms >= since_ms]
