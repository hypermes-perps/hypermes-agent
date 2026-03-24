"""hl account — show HL account state."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer


def account_cmd(
    mainnet: bool = typer.Option(
        False, "--mainnet",
        help="Use mainnet (default: testnet)",
    ),
):
    """Show Hyperliquid account state (margin, balance)."""
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    logging.basicConfig(level=logging.WARNING)

    from cli.config import TradingConfig
    from cli.display import account_table
    from cli.hl_adapter import DirectHLProxy
    from parent.hl_proxy import HLProxy

    cfg = TradingConfig()
    private_key = cfg.get_private_key()

    raw_hl = HLProxy(private_key=private_key, testnet=not mainnet)
    hl = DirectHLProxy(raw_hl)
    state = hl.get_account_state()

    if not state:
        typer.echo("Failed to fetch account state", err=True)
        raise typer.Exit(1)

    typer.echo(account_table(state))
