"""
Input validation for order parameters.
All validators raise ValueError with clear messages on failure.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """
    Validate and normalise a trading symbol.

    Rules:
    - Must be non-empty.
    - Converted to uppercase.
    - Must be alphanumeric (no spaces, special chars).

    Args:
        symbol: Raw symbol string from the user.

    Returns:
        Normalised uppercase symbol string.

    Raises:
        ValueError: If the symbol is invalid.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol cannot be empty.")
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValueError(
            f"Symbol '{symbol}' contains invalid characters. "
            "Use alphanumeric only (e.g. BTCUSDT)."
        )
    return symbol


def validate_side(side: str) -> str:
    """
    Validate order side.

    Args:
        side: 'BUY' or 'SELL' (case-insensitive).

    Returns:
        Uppercase side string.

    Raises:
        ValueError: If the side is not BUY or SELL.
    """
    if not side:
        raise ValueError("Side cannot be empty.")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{side}'. Allowed values: {', '.join(sorted(VALID_SIDES))}."
        )
    return side


def validate_order_type(order_type: str) -> str:
    """
    Validate order type.

    Args:
        order_type: 'MARKET', 'LIMIT', or 'STOP_MARKET' (case-insensitive).

    Returns:
        Uppercase order type string.

    Raises:
        ValueError: If the order type is unsupported.
    """
    if not order_type:
        raise ValueError("Order type cannot be empty.")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{order_type}'. "
            f"Allowed values: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """
    Validate order quantity.

    Args:
        quantity: Quantity as a string or float.

    Returns:
        Decimal quantity value.

    Raises:
        ValueError: If quantity is not a positive number.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    Validate price for LIMIT and STOP_MARKET orders.

    Args:
        price: Price as string or float, or None.
        order_type: The order type (already validated and uppercased).

    Returns:
        Decimal price for LIMIT/STOP_MARKET, or None for MARKET.

    Raises:
        ValueError: If price is missing for LIMIT/STOP_MARKET or is non-positive.
    """
    if order_type == "MARKET":
        if price is not None:
            # Warn but don't fail – price is silently ignored for MARKET orders
            pass
        return None

    if order_type == "LIMIT":
        if price is None:
            raise ValueError(
                f"Price is required for {order_type} orders."
            )
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be greater than zero, got {p}.")
        return p

    return None


def validate_stop_price(stop_price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    Validate stop price for STOP_MARKET orders.

    Args:
        stop_price: Stop price value, or None.
        order_type: The validated order type.

    Returns:
        Decimal stop price or None.

    Raises:
        ValueError: If stop price is missing or non-positive for STOP_MARKET.
    """
    if order_type != "STOP_MARKET":
        return None

    if stop_price is None:
        raise ValueError("stopPrice is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be greater than zero, got {sp}.")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validators and return a clean params dict.

    Returns:
        Dict with keys: symbol, side, order_type, quantity, price, stop_price.

    Raises:
        ValueError: On any validation failure.
    """
    vsymbol = validate_symbol(symbol)
    vside = validate_side(side)
    vtype = validate_order_type(order_type)
    vqty = validate_quantity(quantity)
    vprice = validate_price(price, vtype)
    vstop = validate_stop_price(stop_price, vtype)

    return {
        "symbol": vsymbol,
        "side": vside,
        "order_type": vtype,
        "quantity": vqty,
        "price": vprice,
        "stop_price": vstop,
    }
