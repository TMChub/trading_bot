#!/usr/bin/env python3
"""
CLI entry point for the Binance Futures Testnet Trading Bot.

Usage examples:

  # Market BUY
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

  # Limit SELL
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 70000

  # Stop-Market BUY (bonus)
  python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 60000

  # Account info
  python cli.py account

  # Open orders
  python cli.py open-orders --symbol BTCUSDT
"""

from __future__ import annotations

import json
import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv

# ── make sure the project root is importable ──────────────────
sys.path.insert(0, os.path.dirname(__file__))

from bot.client import BinanceAPIError, BinanceNetworkError, BinanceClient
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order
from bot.validators import validate_all

# Load .env (if present) before anything reads env vars
load_dotenv()

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

DIVIDER = "─" * 60


def _print_section(title: str) -> None:
    click.echo(f"\n{DIVIDER}")
    click.echo(f"  {title}")
    click.echo(DIVIDER)


def _print_kv(label: str, value: object, colour: str = "white") -> None:
    click.echo(f"  {click.style(label + ':', bold=True):<22} {click.style(str(value), fg=colour)}")


def _print_order_request(params: dict) -> None:
    _print_section("ORDER REQUEST SUMMARY")
    _print_kv("Symbol",     params["symbol"])
    _print_kv("Side",       params["side"],       "cyan" if params["side"] == "BUY" else "magenta")
    _print_kv("Type",       params["order_type"])
    _print_kv("Quantity",   params["quantity"])
    if params.get("price"):
        _print_kv("Price",  params["price"])
    if params.get("stop_price"):
        _print_kv("Stop Price", params["stop_price"])


def _print_order_response(result: dict) -> None:
    _print_section("ORDER RESPONSE")
    _print_kv("Order ID",     result.get("orderId"),     "yellow")
    _print_kv("Status",       result.get("status"),      "green" if result.get("status") == "FILLED" else "yellow")
    _print_kv("Symbol",       result.get("symbol"))
    _print_kv("Side",         result.get("side"))
    _print_kv("Type",         result.get("type"))
    _print_kv("Orig Qty",     result.get("origQty"))
    _print_kv("Executed Qty", result.get("executedQty"))
    _print_kv("Avg Price",    result.get("avgPrice")  or "N/A")
    _print_kv("Limit Price",  result.get("price")     or "N/A")
    _print_kv("Stop Price",   result.get("stopPrice") or "N/A")
    _print_kv("Time In Force",result.get("timeInForce") or "N/A")
    _print_kv("Client OID",   result.get("clientOrderId"))


def _get_client(log_level: str) -> BinanceClient:
    """Build BinanceClient from environment variables."""
    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        click.echo(
            click.style(
                "\n✗ BINANCE_API_KEY and BINANCE_API_SECRET must be set "
                "in your environment or .env file.\n",
                fg="red", bold=True,
            )
        )
        sys.exit(1)

    setup_logging(log_level)
    return BinanceClient(api_key=api_key, api_secret=api_secret)


# ─────────────────────────────────────────────────────────────
# CLI definition
# ─────────────────────────────────────────────────────────────

@click.group()
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    show_default=True,
    help="Console log verbosity.",
)
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """
    \b
    ╔══════════════════════════════════════════╗
    ║  Binance Futures Testnet Trading Bot     ║
    ║  USDT-M Perpetuals                       ║
    ╚══════════════════════════════════════════╝

    All orders execute on the testnet environment.
    Set BINANCE_API_KEY and BINANCE_API_SECRET before running.
    """
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = log_level


# ── place ─────────────────────────────────────────────────────

@cli.command("place")
@click.option("--symbol",     required=True,  help="Trading pair, e.g. BTCUSDT.")
@click.option("--side",       required=True,  type=click.Choice(["BUY", "SELL"], case_sensitive=False), help="Order side.")
@click.option("--type",       "order_type",   required=True,
              type=click.Choice(["MARKET", "LIMIT", "STOP_MARKET"], case_sensitive=False),
              help="Order type.")
@click.option("--quantity",   required=True,  help="Order quantity (base asset).")
@click.option("--price",      default=None,   help="Limit price (required for LIMIT orders).")
@click.option("--stop-price", default=None,   help="Stop price (required for STOP_MARKET orders).")
@click.option("--tif",        default="GTC",  show_default=True,
              type=click.Choice(["GTC", "IOC", "FOK"], case_sensitive=False),
              help="Time-in-force for LIMIT orders.")
@click.pass_context
def place_cmd(
    ctx: click.Context,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str],
    stop_price: Optional[str],
    tif: str,
) -> None:
    """Place a MARKET, LIMIT, or STOP_MARKET order."""
    client = _get_client(ctx.obj["log_level"])
    logger = get_logger("cli")

    # ── Validate inputs ───────────────────────────────────────
    try:
        params = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        click.echo(click.style(f"\n✗ Validation error: {exc}\n", fg="red", bold=True))
        logger.error("Validation failed: %s", exc)
        sys.exit(1)

    _print_order_request(params)

    # ── Confirm ───────────────────────────────────────────────
    if not click.confirm(click.style("\n  Proceed with this order?", bold=True), default=True):
        click.echo("  Order cancelled by user.\n")
        sys.exit(0)

    # ── Place ─────────────────────────────────────────────────
    try:
        result = place_order(
            client=client,
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=tif.upper(),
        )
    except BinanceAPIError as exc:
        click.echo(click.style(f"\n✗ API Error [{exc.code}]: {exc.message}\n", fg="red", bold=True))
        logger.error("API error: %s", exc)
        sys.exit(1)
    except BinanceNetworkError as exc:
        click.echo(click.style(f"\n✗ Network Error: {exc}\n", fg="red", bold=True))
        logger.error("Network error: %s", exc)
        sys.exit(1)

    _print_order_response(result)
    click.echo(click.style(f"\n  ✓ Order placed successfully!\n", fg="green", bold=True))


# ── account ───────────────────────────────────────────────────

@cli.command("account")
@click.pass_context
def account_cmd(ctx: click.Context) -> None:
    """Display account balances and positions."""
    client = _get_client(ctx.obj["log_level"])
    logger = get_logger("cli")

    try:
        data = client.get_account()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(click.style(f"\n✗ Error: {exc}\n", fg="red", bold=True))
        logger.error("account command failed: %s", exc)
        sys.exit(1)

    _print_section("ACCOUNT BALANCES (non-zero)")
    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) != 0]
    if assets:
        for asset in assets:
            _print_kv(asset["asset"], f"wallet={asset['walletBalance']}  available={asset['availableBalance']}")
    else:
        click.echo("  No funded assets found.")

    positions = [p for p in data.get("positions", []) if float(p.get("positionAmt", 0)) != 0]
    if positions:
        _print_section("OPEN POSITIONS")
        for pos in positions:
            _print_kv(
                pos["symbol"],
                f"amt={pos['positionAmt']}  entryPrice={pos['entryPrice']}  unrealisedPnl={pos['unrealizedProfit']}",
            )
    click.echo()


# ── open-orders ───────────────────────────────────────────────

@cli.command("open-orders")
@click.option("--symbol", default=None, help="Filter by symbol.")
@click.pass_context
def open_orders_cmd(ctx: click.Context, symbol: Optional[str]) -> None:
    """List all open orders."""
    client = _get_client(ctx.obj["log_level"])
    logger = get_logger("cli")

    try:
        orders = client.get_open_orders(symbol=symbol.upper() if symbol else None)
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(click.style(f"\n✗ Error: {exc}\n", fg="red", bold=True))
        logger.error("open-orders command failed: %s", exc)
        sys.exit(1)

    _print_section(f"OPEN ORDERS{' for ' + symbol.upper() if symbol else ''}")
    if not orders:
        click.echo("  No open orders.\n")
        return

    for order in orders:
        click.echo(
            f"  [{order.get('orderId')}] {order.get('symbol')} "
            f"{order.get('side')} {order.get('type')} "
            f"qty={order.get('origQty')} price={order.get('price')} "
            f"status={order.get('status')}"
        )
    click.echo()


# ── server-time ───────────────────────────────────────────────

@cli.command("server-time")
@click.pass_context
def server_time_cmd(ctx: click.Context) -> None:
    """Print Binance Futures Testnet server time."""
    client = _get_client(ctx.obj["log_level"])
    try:
        data = client.get_server_time()
        _print_section("SERVER TIME")
        _print_kv("Server Time (ms)", data.get("serverTime"))
        click.echo()
    except (BinanceAPIError, BinanceNetworkError) as exc:
        click.echo(click.style(f"\n✗ Error: {exc}\n", fg="red", bold=True))
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli(obj={})
