"""
Order placement logic for Binance Futures Testnet.

This module sits between the CLI layer and the raw API client:
- Builds properly typed parameter dicts
- Calls the client
- Formats and returns clean result summaries
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from .client import BinanceClient, BinanceAPIError, BinanceNetworkError
from .logging_config import get_logger

logger = get_logger("orders")


# ──────────────────────────────────────────────────────────────
# Result dataclass (plain dict for simplicity / no extra deps)
# ──────────────────────────────────────────────────────────────

def _build_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract the most useful fields from a Binance order response.

    Returns a normalised summary dict.
    """
    return {
        "orderId":     raw.get("orderId"),
        "symbol":      raw.get("symbol"),
        "side":        raw.get("side"),
        "type":        raw.get("type"),
        "origQty":     raw.get("origQty"),
        "executedQty": raw.get("executedQty"),
        "avgPrice":    raw.get("avgPrice"),
        "price":       raw.get("price"),
        "stopPrice":   raw.get("stopPrice"),
        "status":      raw.get("status"),
        "timeInForce": raw.get("timeInForce"),
        "clientOrderId": raw.get("clientOrderId"),
        "updateTime":  raw.get("updateTime"),
        "raw":         raw,          # always attach raw for debugging
    }


# ──────────────────────────────────────────────────────────────
# Order placement functions
# ──────────────────────────────────────────────────────────────

def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> Dict[str, Any]:
    """
    Place a MARKET order on Binance Futures.

    Args:
        client:   Initialised BinanceClient.
        symbol:   Trading pair (e.g. 'BTCUSDT').
        side:     'BUY' or 'SELL'.
        quantity: Order quantity.

    Returns:
        Normalised result dict.

    Raises:
        BinanceAPIError, BinanceNetworkError on failure.
    """
    params = {
        "symbol":   symbol,
        "side":     side,
        "type":     "MARKET",
        "quantity": str(quantity),
    }
    logger.info(
        "MARKET %s %s qty=%s",
        side, symbol, quantity,
    )
    raw = client.place_order(**params)
    result = _build_result(raw)
    logger.info(
        "MARKET order placed successfully | orderId=%s status=%s executedQty=%s avgPrice=%s",
        result["orderId"], result["status"], result["executedQty"], result["avgPrice"],
    )
    return result


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Place a LIMIT order on Binance Futures.

    Args:
        client:        Initialised BinanceClient.
        symbol:        Trading pair.
        side:          'BUY' or 'SELL'.
        quantity:      Order quantity.
        price:         Limit price.
        time_in_force: 'GTC' (default) | 'IOC' | 'FOK'.

    Returns:
        Normalised result dict.
    """
    params = {
        "symbol":      symbol,
        "side":        side,
        "type":        "LIMIT",
        "quantity":    str(quantity),
        "price":       str(price),
        "timeInForce": time_in_force,
    }
    logger.info(
        "LIMIT %s %s qty=%s price=%s tif=%s",
        side, symbol, quantity, price, time_in_force,
    )
    raw = client.place_order(**params)
    result = _build_result(raw)
    logger.info(
        "LIMIT order placed successfully | orderId=%s status=%s price=%s",
        result["orderId"], result["status"], result["price"],
    )
    return result


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> Dict[str, Any]:
    """
    Place a STOP_MARKET order on Binance Futures (bonus order type).

    The order triggers a market exit when the price crosses `stop_price`.

    Args:
        client:     Initialised BinanceClient.
        symbol:     Trading pair.
        side:       'BUY' or 'SELL'.
        quantity:   Order quantity.
        stop_price: Price that triggers the market order.

    Returns:
        Normalised result dict.
    """
    params = {
        "symbol":    symbol,
        "side":      side,
        "type":      "STOP_MARKET",
        "quantity":  str(quantity),
        "stopPrice": str(stop_price),
    }
    logger.info(
        "STOP_MARKET %s %s qty=%s stopPrice=%s",
        side, symbol, quantity, stop_price,
    )
    raw = client.place_order(**params)
    result = _build_result(raw)
    logger.info(
        "STOP_MARKET order placed successfully | orderId=%s status=%s stopPrice=%s",
        result["orderId"], result["status"], result["stopPrice"],
    )
    return result


# ──────────────────────────────────────────────────────────────
# Unified dispatcher
# ──────────────────────────────────────────────────────────────

def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
    stop_price: Optional[Decimal] = None,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Unified order dispatcher – routes to the correct placement function.

    Args:
        client:        BinanceClient instance.
        symbol:        Trading pair.
        side:          'BUY' or 'SELL'.
        order_type:    'MARKET', 'LIMIT', or 'STOP_MARKET'.
        quantity:      Order quantity.
        price:         Required for LIMIT orders.
        stop_price:    Required for STOP_MARKET orders.
        time_in_force: Time-in-force for LIMIT orders (default 'GTC').

    Returns:
        Normalised result dict.

    Raises:
        ValueError:           Missing required params for the order type.
        BinanceAPIError:      API-level error.
        BinanceNetworkError:  Network-level error.
    """
    order_type = order_type.upper()

    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)

    elif order_type == "LIMIT":
        if price is None:
            raise ValueError("price is required for LIMIT orders.")
        return place_limit_order(client, symbol, side, quantity, price, time_in_force)

    elif order_type == "STOP_MARKET":
        if stop_price is None:
            raise ValueError("stop_price is required for STOP_MARKET orders.")
        return place_stop_market_order(client, symbol, side, quantity, stop_price)

    else:
        raise ValueError(f"Unsupported order type: {order_type}")
