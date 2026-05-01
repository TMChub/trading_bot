"""
Binance Futures Testnet REST API client.

Handles:
- HMAC-SHA256 request signing
- Timestamp synchronisation
- HTTP request execution with retries
- Structured error propagation
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5000
REQUEST_TIMEOUT = 10  # seconds


class BinanceAPIError(Exception):
    """Raised when the Binance API returns an error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised on network / connectivity failures."""


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Args:
        api_key:    Your Binance Futures Testnet API key.
        api_secret: Your Binance Futures Testnet API secret.
        base_url:   Override the base URL (defaults to testnet).
        recv_window: Milliseconds the request remains valid.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be non-empty strings.")

        self.api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.recv_window = recv_window

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        logger.info("BinanceClient initialised → %s", self.base_url)

    # ──────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────

    def _timestamp(self) -> int:
        """Return current UTC time in milliseconds."""
        return int(time.time() * 1000)

    def _sign(self, params: Dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for the given params dict."""
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute an HTTP request against the Binance REST API.

        Args:
            method:   HTTP method ('GET', 'POST', 'DELETE').
            endpoint: API endpoint path (e.g. '/fapi/v1/order').
            params:   Query / body parameters.
            signed:   Whether to attach timestamp + HMAC signature.

        Returns:
            Parsed JSON response dict.

        Raises:
            BinanceAPIError:     API returned an error payload.
            BinanceNetworkError: Connection / timeout failure.
        """
        params = params or {}

        if signed:
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self.recv_window
            params["signature"] = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug("→ %s %s | params: %s", method, url, {k: v for k, v in params.items() if k != "signature"})

        try:
            if method == "GET":
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method == "POST":
                response = self._session.post(url, data=params, timeout=REQUEST_TIMEOUT)
            elif method == "DELETE":
                response = self._session.delete(url, params=params, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise BinanceNetworkError(f"Connection failed: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out after %ss: %s", REQUEST_TIMEOUT, exc)
            raise BinanceNetworkError(f"Request timed out: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected request error: %s", exc)
            raise BinanceNetworkError(f"Request error: {exc}") from exc

        logger.debug("← HTTP %s | body: %s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (%s): %s", response.status_code, response.text[:200])
            raise BinanceNetworkError(f"Invalid JSON response (HTTP {response.status_code})")

        # Binance error responses always contain a numeric 'code' < 0
        if isinstance(data, dict) and data.get("code", 0) < 0:
            err_code = data["code"]
            err_msg = data.get("msg", "Unknown error")
            logger.error("Binance API error %s: %s", err_code, err_msg)
            raise BinanceAPIError(err_code, err_msg)

        return data

    # ──────────────────────────────────────────────────
    # Public API methods
    # ──────────────────────────────────────────────────

    def get_server_time(self) -> Dict[str, Any]:
        """Fetch server time (useful for clock-skew diagnostics)."""
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self) -> Dict[str, Any]:
        """Fetch exchange trading rules and symbol information."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict[str, Any]:
        """Fetch account balance and position information (signed)."""
        logger.info("Fetching account info …")
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **order_params: Any) -> Dict[str, Any]:
        """
        Place an order on Binance Futures.

        Args:
            **order_params: Any valid Binance Futures order parameter
                            (symbol, side, type, quantity, price, …).

        Returns:
            Full order response dict from Binance.
        """
        logger.info(
            "Placing order → %s",
            {k: v for k, v in order_params.items()},
        )
        return self._request("POST", "/fapi/v1/order", params=order_params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Query an existing order by orderId.

        Args:
            symbol:   Trading symbol (e.g. 'BTCUSDT').
            order_id: Binance order ID.

        Returns:
            Order detail dict.
        """
        logger.info("Querying order %s for %s", order_id, symbol)
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """
        Cancel an open order.

        Args:
            symbol:   Trading symbol.
            order_id: Binance order ID.

        Returns:
            Cancellation response dict.
        """
        logger.info("Cancelling order %s for %s", order_id, symbol)
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def get_open_orders(self, symbol: Optional[str] = None) -> list:
        """
        Fetch all open orders, optionally filtered by symbol.

        Args:
            symbol: Optional trading symbol filter.

        Returns:
            List of open order dicts.
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        logger.info("Fetching open orders%s", f" for {symbol}" if symbol else "")
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
