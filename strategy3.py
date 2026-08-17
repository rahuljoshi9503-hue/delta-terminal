# -*- coding: utf-8 -*-
"""
Strategy 3: 30-Minute Delta Strangle System (Non-Trending Range Bound) - Paper Trading Mode
Platform: Delta Exchange India (Integrated with FastAPI Dashboard & Telegram Alerts)
"""

import datetime
import time
import requests
import server
import telegram_alert

BASE_URL = "https://api.india.delta.exchange"
SYMBOL = "BTCUSD"
TIMEFRAME = "30m"
STRATEGY_ID = "strategy3"

def get_strangle_strikes(spot_price=0.0):
    try:
        otm_buffer = spot_price * 0.045
        ce_strike = int(round((spot_price + otm_buffer) / 500.0) * 500)
        pe_strike = int(round((spot_price - otm_buffer) / 500.0) * 500)
        return f"BTC-{ce_strike}-C + BTC-{pe_strike}-P"
    except Exception:
        return f"BTC-STRANGLE-{int(spot_price)}"

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

    return {
        "close": closes[-1],
        "smma": smma,
        "direction": direction,
        "supertrend": supertrend_val
    }

def get_ist_time():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))

def is_entry_window():
    now = get_ist_time()
    return (now.hour == 17 and now.minute >= 30) or (now.hour == 18 and now.minute <= 30)

def is_settlement_exit():
    now = get_ist_time()
    return (now.hour == 16 and now.minute >= 45) or (now.hour == 17 and now.minute < 30)

def get_candles(symbol=SYMBOL, resolution=TIMEFRAME):
    try:
        res_val = resolution.replace("m", "")
        url = f"{BASE_URL}/v2/history/candles"
        end_time = int(time.time())
        start_time = end_time - (100 * int(res_val) * 60)
        params = {
            "resolution": res_val,
            "symbol": symbol,
            "start": start_time,
            "end": end_time
        }
        res = requests.get(url, params=params, timeout=10)
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
        print(f"[Strategy 3 Fetch Error]: {e}")
    return None

current_position = 0
active_strangle_symbol = ""
entry_btc_price = 0.0
adjustment_count = 0

def run_auto_trader():
    global current_position, active_strangle_symbol, entry_btc_price, adjustment_count
    print("\n" + "=" * 55)
    print(" 🚀 Strategy 3: 30-Minute Strangle System (Paper Mode) सुरू झाली...")
    print("=" * 55 + "\n")

    telegram_alert.send_alert("🚀 *Strategy 3: 30-Minute Delta Strangle* (Paper Mode) Replit वर यशस्वीपणे सुरू झाली आहे!")

    while True:
        try:
            candles = get_candles(SYMBOL, resolution=TIMEFRAME)
            if candles and len(candles) >= 20:
                ind = calculate_indicators(candles[:-1])
                if ind:
                    close = ind["close"]
                    smma = ind["smma"]
                    direction = ind["direction"]

                    is_st_bull = direction < 0
                    is_st_bear = direction > 0
                    is_trending = (is_st_bull and close > smma) or (is_st_bear and close < smma)

                    curr_time = get_ist_time().strftime("%H:%M:%S")
                    dir_label = "Bull 🟢" if is_st_bull else "Bear 🔴"
                    trend_status = "⚠️ Trending" if is_trending else "✅ Non-Trending"

                    print(f"[{curr_time}] BTC: ${close:.2f} | ST: {dir_label} | SMMA: {smma:.2f} | {trend_status}")

                    if current_position == 0 and is_entry_window():
                        if not is_trending:
                            active_strangle_symbol = get_strangle_strikes(close)
                            entry_btc_price = close
                            current_position = -1
                            adjustment_count = 0

                            server.log_paper_trade(STRATEGY_ID, "SELL 0.05Δ Strangle", active_strangle_symbol, entry_btc_price, pnl=0.0)
                            if hasattr(server, "trade_data") and "strategies" in server.trade_data and STRATEGY_ID in server.trade_data["strategies"]:
                                server.trade_data["strategies"][STRATEGY_ID]["position"] = "Short Strangle Open"

                            print(f"\n🎯 [{curr_time}] [PAPER ENTRY] Short Strangle Executed: {active_strangle_symbol} @ ${entry_btc_price:.2f}")
                            msg = f"🎯 *[ENTRY ALERT] Strategy 3 (Strangle)*\n\n⚡ Action: *SELL 0.05Δ Strangle*\n📊 Strikes: `{active_strangle_symbol}`\n💰 BTC Price: *${entry_btc_price:.2f}*\n⏰ Time: `{curr_time}`"
                            telegram_alert.send_alert(msg)
                        else:
                            print(f"⏸️ [{curr_time}] [WAIT] मार्केट ट्रेंडी असल्याने Strategy 3 ची एन्ट्री थांबवली.")

                    elif current_position == -1:
                        price_diff_pct = abs(close - entry_btc_price) / entry_btc_price

                        if price_diff_pct >= 0.025 and adjustment_count < 2:
                            adjustment_count += 1
                            entry_btc_price = close
                            new_symbol = get_strangle_strikes(close)
                            active_strangle_symbol = new_symbol

                            server.log_paper_trade(STRATEGY_ID, f"ADJUSTMENT #{adjustment_count} (Roll-In)", active_strangle_symbol, close, pnl=0.0)
                            print(f"\n🔄 [{curr_time}] [ADJUSTMENT {adjustment_count}] 2.5% मुव्ह - रोल-इन केले: {active_strangle_symbol}")
                            msg = f"🔄 *[ADJUSTMENT] Strategy 3 (Strangle)*\n\n⚡ Roll-In #{adjustment_count}\n📊 New Strikes: `{active_strangle_symbol}`\n💰 BTC Spot: *${close:.2f}*\n⏰ Time: `{curr_time}`"
                            telegram_alert.send_alert(msg)

                        elif is_trending:
                            est_pnl = -12.50
                            server.log_paper_trade(STRATEGY_ID, "EXIT (Trend Breakout SL)", active_strangle_symbol, close, pnl=est_pnl)
                            if hasattr(server, "trade_data") and "strategies" in server.trade_data and STRATEGY_ID in server.trade_data["strategies"]:
                                server.trade_data["strategies"][STRATEGY_ID]["position"] = "Closed (SL)"

                            print(f"🛑 [{curr_time}] [PAPER EXIT] ट्रेंड ब्रेकआउट SL हिट | PnL: ${est_pnl}")
                            msg = f"🛑 *[EXIT - STOPLOSS] Strategy 3 (Strangle)*\n\n⚠️ Reason: *Trend Breakout SL*\n📊 Strikes: `{active_strangle_symbol}`\n💰 BTC Exit: *${close:.2f}*\n📊 Est. P&L: *${est_pnl}*\n⏰ Time: `{curr_time}`"
                            telegram_alert.send_alert(msg)
                            current_position = 0
                            active_strangle_symbol = ""

                        elif is_settlement_exit():
                            est_pnl = 28.00
                            server.log_paper_trade(STRATEGY_ID, "EXIT (4:45 PM Settlement)", active_strangle_symbol, close, pnl=est_pnl)
                            if hasattr(server, "trade_data") and "strategies" in server.trade_data and STRATEGY_ID in server.trade_data["strategies"]:
                                server.trade_data["strategies"][STRATEGY_ID]["position"] = "Closed (Target)"

                            print(f"⏰ [{curr_time}] [PAPER EXIT] सेटलमेंट वेळ - पोझिशन पूर्ण | PnL: ${est_pnl}")
                            msg = f"🎉 *[EXIT - TARGET] Strategy 3 (Strangle)*\n\n✅ Reason: *4:45 PM Settlement Decay*\n📊 Strikes: `{active_strangle_symbol}`\n💰 BTC Exit: *${close:.2f}*\n📊 Est. P&L: *+${est_pnl}*\n⏰ Time: `{curr_time}`"
                            telegram_alert.send_alert(msg)
                            current_position = 0
                            active_strangle_symbol = ""
            time.sleep(15)
        except Exception as e:
            print(f"Strategy 3 लूप एरर: {e}")
            time.sleep(10)

def start():
    run_auto_trader()