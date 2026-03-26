"""hl movers — emerging movers detection commands."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import typer

movers_app = typer.Typer(no_args_is_help=True)


@movers_app.command("run")
def movers_run(
    tick: float = typer.Option(60.0, "--tick", "-t", help="Seconds between scans"),
    min_volume: float = typer.Option(500_000.0, "--min-volume"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mock: bool = typer.Option(False, "--mock"),
    mainnet: bool = typer.Option(False, "--mainnet"),
    json_output: bool = typer.Option(False, "--json"),
    max_scans: int = typer.Option(0, "--max-scans"),
    data_dir: str = typer.Option("data/movers", "--data-dir"),
):
    """Start continuous emerging movers detection."""
    _run_movers(tick=tick, min_volume=min_volume, preset=preset, config=config,
                mock=mock, mainnet=mainnet, json_output=json_output,
                max_scans=max_scans, data_dir=data_dir)


@movers_app.command("once")
def movers_once(
    min_volume: float = typer.Option(500_000.0, "--min-volume"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    mock: bool = typer.Option(False, "--mock"),
    mainnet: bool = typer.Option(False, "--mainnet"),
    json_output: bool = typer.Option(False, "--json"),
    data_dir: str = typer.Option("data/movers", "--data-dir"),
):
    """Run a single movers scan and exit."""
    _run_movers(tick=0, min_volume=min_volume, preset=preset, config=config,
                mock=mock, mainnet=mainnet, json_output=json_output,
                max_scans=1, data_dir=data_dir, single=True)


@movers_app.command("status")
def movers_status(data_dir: str = typer.Option("data/movers", "--data-dir")):
    """Show last movers scan results."""
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from modules.movers_state import MoversHistoryStore, MoverScanResult
    import time as _time

    store = MoversHistoryStore(path=f"{data_dir}/scan-history.json")
    history = store.get_history()

    if not history:
        typer.echo("No movers scan history found.")
        raise typer.Exit()

    last = MoverScanResult.from_dict(history[-1])
    age = (_time.time() * 1000 - last.scan_time_ms) / 1000

    typer.echo(f"Last scan: {age:.0f}s ago  |  Signals: {len(last.signals)}")
    if last.signals:
        for i, sig in enumerate(last.signals[:10], 1):
            typer.echo(f"  {i}. {sig.signal_type} {sig.direction} {sig.asset} "
                       f"conf={sig.confidence:.0f}")
    else:
        typer.echo("  No signals detected.")


@movers_app.command("presets")
def movers_presets():
    """List available movers presets."""
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from modules.movers_config import MOVERS_PRESETS

    for name, cfg in MOVERS_PRESETS.items():
        typer.echo(f"\n{name}:")
        typer.echo(f"  volume_min_24h: ${cfg.volume_min_24h:,.0f}")
        typer.echo(f"  oi_delta_immediate: {cfg.oi_delta_immediate_pct}%")
        typer.echo(f"  oi_delta_breakout: {cfg.oi_delta_breakout_pct}%")
        typer.echo(f"  volume_surge_ratio: {cfg.volume_surge_ratio}x")


def _run_movers(tick, min_volume, preset, config, mock, mainnet,
                json_output, max_scans, data_dir, single=False):
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from modules.movers_config import MoversConfig, MOVERS_PRESETS

    if config:
        cfg = MoversConfig.from_yaml(str(config))
    elif preset and preset in MOVERS_PRESETS:
        cfg = MoversConfig.from_dict(MOVERS_PRESETS[preset].to_dict())
    else:
        cfg = MoversConfig()

    cfg.volume_min_24h = min_volume

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)-14s %(levelname)-5s %(message)s",
        datefmt="%H:%M:%S",
    )

    if mock:
        from cli.hl_adapter import DirectMockProxy
        hl = DirectMockProxy()
        typer.echo("Mode: MOCK")
    else:
        from cli.hl_adapter import DirectHLProxy
        from parent.hl_proxy import HLProxy
        import os
        private_key = os.environ.get("HL_PRIVATE_KEY", "")
        if not private_key:
            typer.echo("Error: HL_PRIVATE_KEY not set", err=True)
            raise typer.Exit(1)
        raw_hl = HLProxy(private_key=private_key, testnet=not mainnet)
        hl = DirectHLProxy(raw_hl)
        typer.echo(f"Mode: LIVE ({'mainnet' if mainnet else 'testnet'})")

    typer.echo(f"Min Vol: ${cfg.volume_min_24h:,.0f}  |  "
               f"OI threshold: {cfg.oi_delta_breakout_pct}%")

    from skills.movers.scripts.standalone_runner import MoversRunner

    runner = MoversRunner(hl=hl, config=cfg, tick_interval=tick,
                          json_output=json_output, data_dir=data_dir)

    if single:
        runner.run_once()
    else:
        runner.run(max_scans=max_scans)
