# -*- coding: utf-8 -*-
"""
Strategy: Monthly Volatility Option Buyer with Auto-Execution (Fixed 5m API) - Paper Trading Mode
Platform: Delta Exchange India (Integrated with FastAPI Dashboard & Telegram Alerts)
"""

import datetime
import time
import requests
import server
import telegram_alert

API_KEY = "SOxFmKUPVo5nBx9fONzTdCLCJmlseO"
API_SECRET = "v5C2gKDiezMqu3KCEAyXV2Jc4u6xd2xOR8aOn4ZwWr5wu5MkkouRSxHM75ZW"
BASE_URL = "https://api.india.delta.exchange"
UNDERLYING = "BTC"
RESOLUTION = "5m"
ORDER_SIZE = 1

def get_paper_atm_strike(contract_type="C", spot_price=0.0):
    try:
        res = requests.get(f"{BASE_URL}/v2/products", timeout=10)
        if res.status_code == 200:
            products = res.json().get("result", [])
            opt_products = [
                p for p in products
                if p.get("contract_type") == "options"
                and p.get("underlying_asset", {}).get("symbol") == UNDERLYING
            ]
            suitable_products = [
                p for p in opt_products
                if p.get("symbol", "").endswith(f"-{contract_type}")
            ]
            if suitable_products:
                closest_prod = min(
                    suitable_products,
                    key=lambda x: abs(float(x.get("strike_price", 0)) - spot_price)
                )
                return closest_prod["symbol"]
    except Exception as e:
        print(f"[Strategy 2 Strike Selector Error]: {e}")
    return f"BTC-{int(spot_price)}-{contract_type}"

def calculate_indicators(candles):
    if len(candles) < 20:
        return None

    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]

    alpha_smma = 1.0 / 9.0
    smma = closes[0]
    for c in closes[1:]:
        smma = (alpha_smma * c) + ((1 - alpha_smma) * smma)

    tr_list = []
    for i in range(len(candles)):
        if i == 0:
            tr_list.append(highs[i] - lows[i])
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            tr_list.append(tr)

    alpha_st_atr = 1.0 / 10.0
    st_atr_list = [tr_list[0]]
    for tr in tr_list[1:]:
        val = (alpha_st_atr * tr) + ((1 - alpha_st_atr) * st_atr_list[-1])
        st_atr_list.append(val)

    mult = 3.0
    upperband = 0.0
    lowerband = 0.0
    direction = 1
    supertrend_val = 0.0

    for i in range(len(candles)):
        hl2 = (highs[i] + lows[i]) / 2.0
        cur_upper = hl2 + (mult * st_atr_list[i])
        cur_lower = hl2 - (mult * st_atr_list[i])

        if i > 0:
            if closes[i - 1] > lowerband:
                lowerband = max(cur_lower, lowerband)
            else:
                lowerband = cur_lower

            if closes[i - 1] < upperband:
                upperband = min(cur_upper, upperband)
            else:
                upperband = cur_upper

            if closes[i - 1] > upperband:
                direction = -1
            elif closes[i - 1] < lowerband:
                direction = 1
        else:
            lowerband = cur_lower
            upperband = cur_upper

        supertrend_val = lowerband if direction == -1 else upperband

    alpha_atr14 = 1.0 / 14.0
    atr14_list = [tr_list[0]]
    for tr in tr_list[1:]:
        val = (alpha_atr14 * tr) + ((1 - alpha_atr14) * atr14_list[-1])
        atr14_list.append(val)

    current_atr = atr14_list[-1]
    atr_sma20 = sum(atr14_list[-20:]) / len(atr14_list[-20:])
    is_high_volatility = current_atr >= atr_sma20

    return {
        "close": closes[-1],
        "prev_close": closes[-2],
        "smma": smma,
        "direction": direction,
        "supertrend": supertrend_val,
        "atr": current_atr,
        "is_high_volatility": is_high_volatility
    }

def get_candles(symbol="BTCUSD", resolution=RESOLUTION):
    try:
        res_val = resolution.replace("m", "")
        url = f"{BASE_URL}/v2/history/candles"
        end_time = int(time.time())
        start_time = end_time - (50 * int(res_val) * 60)
        params = {
            "resolution": res_val,
            "symbol": symbol,
            "start": start_time,
            "end": end_time
        }
        res = requests.get(url, params=params, timeout=8)
        if res.status_code == 200:
            data = res.json().get("result", [])
            if data:
                data = sorted(data, key=lambda x: x["time"])
                return [{
                    "open": float(d["open"]),
                    "high": float(d["high"]),
                    "low": float(d["low"]),
                    "close": float(d["close"]),
                    "volume": float(d["volume"]),
                } for d in data]
    except Exception as e:
        print(f"[Strategy 2 Fetch Error]: {e}")
    return None

current_position = 0
active_symbol = ""
entry_price = 0.0

def run_auto_trader():
    global current_position, active_symbol, entry_price
    print("\n" + "=" * 55)
    print(" 🚀 Strategy 2: Auto Option Buyer (Paper Mode) सुरू झाली...")
    print("=" * 55 + "\n")

    telegram_alert.send_alert("🚀 *Strategy 2: Auto Option Buyer* (Paper Mode) Replit वर यशस्वीपणे सुरू झाली आहे!")

    while True:
        try:
            candles = get_candles("BTCUSD", resolution=RESOLUTION)
            if candles and len(candles) >= 20:
                ind = calculate_indicators(candles)
                if ind:
                    close = ind["close"]
                    prev_close = ind["prev_close"]
                    smma = ind["smma"]
                    direction = ind["direction"]
                    atr_val = ind["atr"]
                    is_high_vol = ind["is_high_volatility"]

                    st_bullish = direction < 0
                    st_bearish = direction > 0
                    smma_bullish = close > smma
                    smma_bearish = close < smma

                    volatile_buy_call = (st_bearish and smma_bullish) and is_high_vol
                    volatile_buy_put = (st_bullish and smma_bearish) and is_high_vol

                    curr_time = datetime.datetime.now().strftime("%H:%M:%S")
                    vol_txt = "🔥 High Vol" if is_high_vol else "Normal Vol"
                    st_txt = "Bull 🟢" if st_bullish else "Bear 🔴"
                    print(f"[{curr_time}] BTC: ${close:.2f} | ST: {st_txt} | SMMA: {smma:.2f} | {vol_txt}")

                    # 1. PAPER ENTRY
                    if current_position == 0:
                        if volatile_buy_call:
                            active_symbol = get_paper_atm_strike("C", close)
                            entry_price = close
                            current_position = 1
                            server.log_paper_trade("strategy2", "BUY CE (Option)", active_symbol, entry_price, pnl=0.0)
                            print(f"🟢 [PAPER ENTRY] Buy CE Triggered: {active_symbol} @ ${entry_price:.2f}")
                            telegram_alert.send_alert(f"🟢 *[ENTRY ALERT] Strategy 2 (Option Buyer)*\n\n📈 Action: *BUY CE (Option)*\n🎯 Strike: `{active_symbol}`\n💰 BTC Price: *${entry_price:.2f}*\n⏰ Time: `{curr_time}`")

                        elif volatile_buy_put:
                            active_symbol = get_paper_atm_strike("P", close)
                            entry_price = close
                            current_position = -1
                            server.log_paper_trade("strategy2", "BUY PE (Option)", active_symbol, entry_price, pnl=0.0)
                            print(f"🔴 [PAPER ENTRY] Buy PE Triggered: {active_symbol} @ ${entry_price:.2f}")
                            telegram_alert.send_alert(f"🔴 *[ENTRY ALERT] Strategy 2 (Option Buyer)*\n\n📉 Action: *BUY PE (Option)*\n🎯 Strike: `{active_symbol}`\n💰 BTC Price: *${entry_price:.2f}*\n⏰ Time: `{curr_time}`")

                    # 2. PAPER EXIT
                    elif current_position == 1:
                        if (close <= prev_close - (atr_val * 1.0)) or direction < 0:
                            pnl = round(close - entry_price, 2)
                            server.log_paper_trade("strategy2", "EXIT (SL/Target)", active_symbol, close, pnl=pnl)
                            if hasattr(server, "trade_data") and "strategies" in server.trade_data and "strategy2" in server.trade_data["strategies"]:
                                server.trade_data["strategies"]["strategy2"]["position"] = "Closed"
                            print(f"⚠️ [PAPER EXIT] CE Closed @ ${close:.2f} | P&L: ${pnl}")
                            telegram_alert.send_alert(f"⚠️ *[EXIT ALERT] Strategy 2 (Option Buyer)*\n\n🎯 Strike: `{active_symbol}`\n💰 Exit Price: *${close:.2f}*\n📊 P&L: *${pnl}*\n⏰ Time: `{curr_time}`")
                            current_position = 0
                            active_symbol = ""

                    elif current_position == -1:
                        if (close >= prev_close + (atr_val * 1.0)) or direction > 0:
                            pnl = round(entry_price - close, 2)
                            server.log_paper_trade("strategy2", "EXIT (SL/Target)", active_symbol, close, pnl=pnl)
                            if hasattr(server, "trade_data") and "strategies" in server.trade_data and "strategy2" in server.trade_data["strategies"]:
                                server.trade_data["strategies"]["strategy2"]["position"] = "Closed"
                            print(f"⚠️ [PAPER EXIT] PE Closed @ ${close:.2f} | P&L: ${pnl}")
                            telegram_alert.send_alert(f"⚠️ *[EXIT ALERT] Strategy 2 (Option Buyer)*\n\n🎯 Strike: `{active_symbol}`\n💰 Exit Price: *${close:.2f}*\n📊 P&L: *${pnl}*\n⏰ Time: `{curr_time}`")
                            current_position = 0
                            active_symbol = ""
            time.sleep(15)
        except Exception as e:
            print(f"Strategy 2 लूप एरर: {e}")
            time.sleep(10)

def start():
    run_auto_trader()