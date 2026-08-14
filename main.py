import sys

import ccxt


def main() -> None:
    exchange = ccxt.binance({"enableRateLimit": True})

    try:
        ticker = exchange.fetch_ticker("BTC/USDT")
        price = ticker.get("last")

        if price is None:
            raise RuntimeError("The exchange did not return a current price.")

        print(f"Bitcoin price: ${price:,.2f} USDT")
    except (ccxt.BaseError, RuntimeError) as error:
        print(f"Unable to fetch the Bitcoin price: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
