# -*- coding: utf-8 -*-
"""
Strategy Name: Indicator base Strategy (Fish Tractor Logic) - Paper Trading Mode
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
SYMBOL = "BTCUSD"
TIMEFRAME = "5"

def calculate_indicators(candles):
    if len(candles) < 20:
        return None, None, None, None

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

    alpha_atr = 1.0 / 10.0
    atr_list = [tr_list[0]]
    for tr in tr_list[1:]:
        atr_val = (alpha_atr * tr) + ((1 - alpha_atr) * atr_list[-1])
        atr_list.append(atr_val)

    mult = 3.0
    upperband = 0.0
    lowerband = 0.0
    direction = 1
    supertrend_val = 0.0

    for i in range(len(candles)):
        hl2 = (highs[i] + lows[i]) / 2.0
        cur_upper = hl2 + (mult * atr_list[i])
        cur_lower = hl2 - (mult * atr_list[i])

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

    return closes[-1], smma, direction, supertrend_val

def is_gamma_risk_zone():
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    if (now.hour == 16 and now.minute >= 0) or (now.hour == 17 and now.minute <= 30):
        return True
    return False

def get_candles(symbol=SYMBOL, resolution=TIMEFRAME):
    try:
        url = f"{BASE_URL}/v2/history/candles"
        end_time = int(time.time())
        start_time = end_time - (100 * int(resolution) * 60)
        params = {
            "resolution": resolution,
            "symbol": symbol,
            "start": start_time,
            "end": end_time,
        }
        res = requests.get(url, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json().get("result", [])
            data = sorted(data, key=lambda x: x["time"])
            return [{
                "open": float(d["open"]),
                "high": float(d["high"]),
                "low": float(d["low"]),
                "close": float(d["close"]),
                "volume": float(d["volume"]),
            } for d in data]
    except Exception as e:
        print(f"[Strategy 1 Fetch Error]: {e}")
    return None

current_position = 0
entry_price = 0.0

def run_strategy():
    global current_position, entry_price
    print("\n" + "=" * 50)
    print(" 🚀 'Strategy 1: Fish Indicator' (Paper Mode) सुरू झाली...")
    print("=" * 50 + "\n")

    telegram_alert.send_alert("🚀 *Strategy 1: Fish Indicator* (Paper Trading Mode) Replit वर यशस्वीपणे सुरू झाली आहे!")

    while True:
        try:
            candles = get_candles(SYMBOL, resolution=TIMEFRAME)
            if candles and len(candles) >= 20:
                close, smma, direction, st = calculate_indicators(candles)
                gamma_risk = is_gamma_risk_zone()

                if hasattr(server, "trade_data") and "summary" in server.trade_data:
                    server.trade_data["summary"]["btc_ltp"] = float(close)

                bullish_tractor = (direction < 0) and (close > smma)
                bearish_tractor = (direction > 0) and (close < smma)

                curr_time = datetime.datetime.now().strftime("%H:%M:%S")
                dir_label = "🟢 Bullish" if direction < 0 else "🔴 Bearish"
                print(f"[{curr_time}] भाव: ${close} | ST: {dir_label} | SMMA 9: {smma:.2f} | Gamma Risk: {gamma_risk}")

                if current_position == 0 and not gamma_risk:
                    if bullish_tractor:
                        entry_price = close
                        current_position = 1
                        server.log_paper_trade("strategy1", "SELL PE (Bullish)", "BTC-PE", entry_price, pnl=0.0)
                        print(f"🟢 [PAPER ENTRY] Bullish Tractor: Sell PE @ ${entry_price}")
                        telegram_alert.send_alert(f"🟢 *[ENTRY ALERT] Strategy 1 (Fish)*\n\n📈 Action: *SELL PE (Bullish)*\n💰 BTC Price: *${entry_price}*\n⏰ Time: `{curr_time}`")

                    elif bearish_tractor:
                        entry_price = close
                        current_position = -1
                        server.log_paper_trade("strategy1", "SELL CE (Bearish)", "BTC-CE", entry_price, pnl=0.0)
                        print(f"🔴 [PAPER ENTRY] Bearish Tractor: Sell CE @ ${entry_price}")
                        telegram_alert.send_alert(f"🔴 *[ENTRY ALERT] Strategy 1 (Fish)*\n\n📉 Action: *SELL CE (Bearish)*\n💰 BTC Price: *${entry_price}*\n⏰ Time: `{curr_time}`")

                elif current_position == 1:
                    if direction > 0 or close <= st or gamma_risk:
                        reason = "Gamma Exit" if gamma_risk else "PE StopLoss Hit"
                        pnl = round(close - entry_price, 2)
                        server.log_paper_trade("strategy1", f"EXIT ({reason})", "BTC-PE", close, pnl=pnl)
                        if hasattr(server, "trade_data") and "strategies" in server.trade_data and "strategy1" in server.trade_data["strategies"]:
                            server.trade_data["strategies"]["strategy1"]["position"] = "Closed"
                        print(f"⚠️ [PAPER EXIT] Bullish Trade Closed ({reason}) @ ${close} | P&L: ${pnl}")
                        telegram_alert.send_alert(f"⚠️ *[EXIT ALERT] Strategy 1 (Fish)*\n\n🎯 Reason: *{reason}*\n💰 Exit Price: *${close}*\n📊 P&L: *${pnl}*\n⏰ Time: `{curr_time}`")
                        current_position = 0

                elif current_position == -1:
                    if direction < 0 or close >= st or gamma_risk:
                        reason = "Gamma Exit" if gamma_risk else "CE StopLoss Hit"
                        pnl = round(entry_price - close, 2)
                        server.log_paper_trade("strategy1", f"EXIT ({reason})", "BTC-CE", close, pnl=pnl)
                        if hasattr(server, "trade_data") and "strategies" in server.trade_data and "strategy1" in server.trade_data["strategies"]:
                            server.trade_data["strategies"]["strategy1"]["position"] = "Closed"
                        print(f"⚠️ [PAPER EXIT] Bearish Trade Closed ({reason}) @ ${close} | P&L: ${pnl}")
                        telegram_alert.send_alert(f"⚠️ *[EXIT ALERT] Strategy 1 (Fish)*\n\n🎯 Reason: *{reason}*\n💰 Exit Price: *${close}*\n📊 P&L: *${pnl}*\n⏰ Time: `{curr_time}`")
                        current_position = 0

            time.sleep(15)
        except Exception as e:
            print(f"Strategy 1 एरर: {e}")
            time.sleep(10)

def start():
    run_strategy()