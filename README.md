# Binance Futures Testnet Trading Bot

A clean, production-quality Python CLI application that places orders on **Binance Futures Testnet (USDT-M)**.

---

## Features

| Feature | Details |
|---|---|
| Order Types | `MARKET`, `LIMIT`, `STOP_MARKET` (bonus) |
| Sides | `BUY` / `SELL` |
| Validation | Symbol, side, type, quantity, price, stop-price |
| Logging | Rotating file + console; structured format |
| Error Handling | API errors, network failures, invalid input |
| CLI | `click`-based with `--help` on every command |

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST API wrapper (signing, retries, errors)
│   ├── orders.py            # Order placement logic (MARKET / LIMIT / STOP_MARKET)
│   ├── validators.py        # Input validation (raises ValueError on bad input)
│   └── logging_config.py   # File + console logging setup
├── cli.py                   # Click CLI entry point
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── .env.example             # Template for credentials
├── requirements.txt
└── README.md
```

---

## Setup

### 1 · Prerequisites

- Python 3.9+
- `pip`

### 2 · Clone & install dependencies

```bash
git clone https://github.com/YOUR_USERNAME/binance-futures-bot.git
cd binance-futures-bot

pip install -r requirements.txt
```

### 3 · Create a Binance Futures Testnet account

1. Visit **https://testnet.binancefuture.com**
2. Log in with GitHub or Google
3. Navigate to **API Management** → **Create API**
4. Copy the API Key and Secret

### 4 · Configure credentials

```bash
cp .env.example .env
# Open .env and fill in your keys:
# BINANCE_API_KEY=your_key_here
# BINANCE_API_SECRET=your_secret_here
```

> **Tip:** You can also export them directly in your shell:
> ```bash
> export BINANCE_API_KEY="..."
> export BINANCE_API_SECRET="..."
> ```

---

## How to Run

### Global help

```bash
python cli.py --help
```

### Place a MARKET order

```bash
# Market BUY 0.001 BTC
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001

# Market SELL 0.5 ETH
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --quantity 0.5
```

### Place a LIMIT order

```bash
# Limit BUY 0.001 BTC at $90,000
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 90000

# Limit SELL 0.001 BTC at $98,000  (GTC default)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 98000

# Limit order with custom time-in-force
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.001 --price 90000 --tif IOC
```

### Place a STOP_MARKET order (bonus)

```bash
# Stop-Market BUY triggers when price rises above $100,000
python cli.py place --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.001 --stop-price 100000

# Stop-Market SELL triggers when price falls below $85,000
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 85000
```

### Account balance & positions

```bash
python cli.py account
```

### Open orders

```bash
# All open orders
python cli.py open-orders

# Filtered by symbol
python cli.py open-orders --symbol BTCUSDT
```

### Server time (connectivity check)

```bash
python cli.py server-time
```

### Verbose / debug logging

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

---

## Example Output

```
──────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────────────
  Symbol:               BTCUSDT
  Side:                 BUY
  Type:                 MARKET
  Quantity:             0.001

  Proceed with this order? [Y/n]: Y

──────────────────────────────────────────────────────────
  ORDER RESPONSE
──────────────────────────────────────────────────────────
  Order ID:             4751823945
  Status:               FILLED
  Symbol:               BTCUSDT
  Side:                 BUY
  Type:                 MARKET
  Orig Qty:             0.001
  Executed Qty:         0.001
  Avg Price:            97234.50000
  Limit Price:          N/A
  Stop Price:           N/A
  Time In Force:        GTC
  Client OID:           x-Cb7ytekJc6234ab12

  ✓ Order placed successfully!
```

---

## Logging

Logs are written to `logs/trading_bot_YYYYMMDD.log` (rotating, max 5 MB × 5 files).

Each log line format:

```
2025-01-15 10:23:41 | INFO     | trading_bot.orders | MARKET BUY BTCUSDT qty=0.001
```

Sample log files are included in the `logs/` directory:

| File | Contents |
|---|---|
| `logs/market_order_sample.log` | Full request → response for a MARKET BUY |
| `logs/limit_order_sample.log`  | Full request → response for a LIMIT SELL |

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Missing `--price` for LIMIT | Validation error before any API call |
| Invalid symbol characters | Validation error |
| Non-positive quantity | Validation error |
| Binance API error (e.g. -1121 Invalid symbol) | Red ✗ message + logged + non-zero exit |
| Network timeout / connection refused | Red ✗ message + logged + non-zero exit |
| Missing API credentials | Clear guidance + exit 1 |

---

## Assumptions

1. **Testnet only.** The base URL is hardcoded to `https://testnet.binancefuture.com`. To use mainnet, set `BINANCE_BASE_URL=https://fapi.binance.com` (requires code change in `client.py`).
2. **Hedge-mode not supported.** All orders use `positionSide=BOTH` (one-way mode default).
3. **Quantity precision.** The CLI accepts any positive decimal; if Binance rejects it for precision (error -1111), reduce decimals to match the symbol's step size.
4. **`python-binance` not used.** Direct REST calls via `requests` were chosen for transparency and to avoid library version pinning issues.

---

## Dependencies

```
requests>=2.31.0     # HTTP client
click>=8.1.0         # CLI framework
python-dotenv>=1.0.0 # .env file loading
```

No Binance SDK required.
