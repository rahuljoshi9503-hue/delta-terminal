# -*- coding: utf-8 -*-
"""
Strategy: Monthly Volatility Option Buyer with Auto-Execution (Fixed 5m API)
Platform: Delta Exchange India (Pure Python)
"""

import time
import datetime
import requests
import hmac
import hashlib
import json

# ==========================================
# 1. Delta Exchange API कॉन्फिगरेशन
# ==========================================
API_KEY = "SOxFmKUPVo5nBx9fONzTdCLCJmlseO"
API_SECRET = "v5C2gKDiezMqu3KCEAyXV2Jc4u6xd2xOR8aOn4ZwWr5wu5MkkouRSxHM75ZW"
BASE_URL = "https://api.india.delta.exchange"
UNDERLYING = "BTC"
RESOLUTION = "5m"          # Delta Exchange 5m फॉरमॅट
ORDER_SIZE = 1             # १ कॉन्ट्रॅक्ट / लॉट

# ==========================================
# 2. सुरक्षित API रिक्वेस्ट सिग्नेचर
# ==========================================
def generate_signature(secret, method, path, query_string="", payload_str=""):
    timestamp = str(int(time.time()))
    message = method + timestamp + path + query_string + payload_str
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature, timestamp

def send_private_request(method, path, payload=None):
    payload_str = json.dumps(payload) if payload else ""
    signature, timestamp = generate_signature(API_SECRET, method, path, "", payload_str)
    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }
    url = BASE_URL + path
    if method == "POST":
        return requests.post(url, headers=headers, data=payload_str, timeout=10)
    elif method == "GET":
        return requests.get(url, headers=headers, timeout=10)

# ==========================================
# 3. ATM स्ट्राइक शोधणे आणि ऑर्डर प्लेस करणे
# ==========================================
def place_option_order(contract_type="C", size=ORDER_SIZE):
    try:
        res = requests.get(f"{BASE_URL}/v2/products", timeout=10)
        if res.status_code != 200:
            return None

        products = res.json().get("result", [])
        opt_products = [
            p for p in products 
            if p.get("contract_type") == "options" and p.get("underlying_asset", {}).get("symbol") == UNDERLYING
        ]

        if not opt_products:
            return None

        # BTC चा मार्क प्राईस
        spot_res = requests.get(f"{BASE_URL}/v2/tickers/BTCUSD", timeout=10)
        spot_price = float(spot_res.json().get("result", {}).get("mark_price", 0))

        suitable_products = [
            p for p in opt_products 
            if p.get("symbol", "").endswith(f"-{contract_type}")
        ]

        if not suitable_products:
            return None

        closest_prod = min(suitable_products, key=lambda x: abs(float(x.get("strike_price", 0)) - spot_price))
        product_id = closest_prod["id"]
        prod_symbol = closest_prod["symbol"]

        print(f"🎯 निवडलेला स्ट्राइक: {prod_symbol} (ID: {product_id})")

        order_payload = {
            "product_id": product_id,
            "size": size,
            "side": "buy",
            "order_type": "market_order"
        }

        order_res = send_private_request("POST", "/v2/orders", order_payload)
        if order_res.status_code in [200, 201]:
            print(f"✅ [SUCCESS] {prod_symbol} बाय ऑर्डर यशस्वी झाली!")
            return product_id
        else:
            print(f"❌ [ORDER FAILED]: {order_res.text}")
            return None

    except Exception as e:
        print(f"[ERROR] ऑर्डर एरर: {e}")
        return None

def close_option_position(product_id, size=ORDER_SIZE):
    try:
        order_payload = {
            "product_id": product_id,
            "size": size,
            "side": "sell",
            "order_type": "market_order"
        }
        order_res = send_private_request("POST", "/v2/orders", order_payload)
        if order_res.status_code in [200, 201]:
            print(f"✅ [SUCCESS] पोझिशन यशस्वीरीत्या एक्झिट केली!")
            return True
        else:
            print(f"❌ [EXIT FAILED]: {order_res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] एक्झिट एरर: {e}")
        return False

# ==========================================
# 4. इंडिकेटर्स कॅल्क्युलेशन (Pure Python)
# ==========================================
def calculate_indicators(candles):
    if len(candles) < 20:
        return None

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]

    # SMMA 9
    alpha_smma = 1.0 / 9.0
    smma = closes[0]
    for c in closes[1:]:
        smma = (alpha_smma * c) + ((1 - alpha_smma) * smma)

    # TR
    tr_list = []
    for i in range(len(candles)):
        if i == 0:
            tr_list.append(highs[i] - lows[i])
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            tr_list.append(tr)

    # SuperTrend ATR (10)
    alpha_st_atr = 1.0 / 10.0
    st_atr_list = [tr_list[0]]
    for tr in tr_list[1:]:
        val = (alpha_st_atr * tr) + ((1 - alpha_st_atr) * st_atr_list[-1])
        st_atr_list.append(val)

    # SuperTrend (10, 3.0)
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
            if closes[i-1] > lowerband:
                lowerband = max(cur_lower, lowerband)
            else:
                lowerband = cur_lower

            if closes[i-1] < upperband:
                upperband = min(cur_upper, upperband)
            else:
                upperband = cur_upper

            if closes[i-1] > upperband:
                direction = -1
            elif closes[i-1] < lowerband:
                direction = 1

        else:
            lowerband = cur_lower
            upperband = cur_upper

        supertrend_val = lowerband if direction == -1 else upperband

    # ATR 14
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
        url = f"{BASE_URL}/v2/history/candles"
        end_time = int(time.time())
        start_time = end_time - (50 * 5 * 60)  # मागील 50 कँडल्स (5m)
        params = {"resolution": resolution, "symbol": symbol, "start": start_time, "end": end_time}
        res = requests.get(url, params=params, timeout=8)
        if res.status_code == 200:
            data = res.json().get("result", [])
            if data:
                data = sorted(data, key=lambda x: x['time'])
                return [{
                    "open": float(d["open"]),
                    "high": float(d["high"]),
                    "low": float(d["low"]),
                    "close": float(d["close"]),
                    "volume": float(d["volume"])
                } for d in data]
        else:
            print(f"[API Warning] Status Code: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"[Fetch Error]: {e}")
    return None

# ==========================================
# 5. मुख्य ऑटो-ट्रेडिंग लूप
# ==========================================
current_position = 0
active_product_id = None

def run_auto_trader():
    global current_position, active_product_id
    print("\n" + "="*55)
    print(" 🚀 Auto Option Buyer बॉट सुरू झाला आहे...")
    print("="*55 + "\n")

    while True:
        try:
            candles = get_candles("BTCUSD", resolution=RESOLUTION)
            if candles and len(candles) >= 20:
                ind = calculate_indicators(candles)
                if ind:
                    close = ind['close']
                    prev_close = ind['prev_close']
                    smma = ind['smma']
                    direction = ind['direction']
                    atr_val = ind['atr']
                    is_high_vol = ind['is_high_volatility']

                    st_bullish = (direction < 0)
                    st_bearish = (direction > 0)
                    smma_bullish = (close > smma)
                    smma_bearish = (close < smma)

                    volatile_buy_call = (st_bearish and smma_bullish) and is_high_vol
                    volatile_buy_put  = (st_bullish and smma_bearish) and is_high_vol

                    curr_time = datetime.datetime.now().strftime('%H:%M:%S')
                    vol_txt = "🔥 High Vol" if is_high_vol else "Normal Vol"
                    st_txt = "Bull 🟢" if st_bullish else "Bear 🔴"
                    print(f"[{curr_time}] BTC: ${close:.2f} | ST: {st_txt} | SMMA: {smma:.2f} | {vol_txt}")

                    # 1. ENTRY
                    if current_position == 0:
                        if volatile_buy_call:
                            print("🟢 [SIGNAL] Buy CE Triggered! ऑर्डर प्लेस करत आहे...")
                            prod_id = place_option_order("C", size=ORDER_SIZE)
                            if prod_id:
                                current_position = 1
                                active_product_id = prod_id

                        elif volatile_buy_put:
                            print("🔴 [SIGNAL] Buy PE Triggered! ऑर्डर प्लेस करत आहे...")
                            prod_id = place_option_order("P", size=ORDER_SIZE)
                            if prod_id:
                                current_position = -1
                                active_product_id = prod_id

                    # 2. EXIT
                    elif current_position == 1:
                        if (close <= prev_close - (atr_val * 1.0)) or direction < 0:
                            print("⚠️ [EXIT] CE StopLoss / Target Triggered! पोझिशन बंद करत आहे...")
                            if active_product_id:
                                close_option_position(active_product_id, size=ORDER_SIZE)
                            current_position = 0
                            active_product_id = None

                    elif current_position == -1:
                        if (close >= prev_close + (atr_val * 1.0)) or direction > 0:
                            print("⚠️ [EXIT] PE StopLoss / Target Triggered! पोझिशन बंद करत आहे...")
                            if active_product_id:
                                close_option_position(active_product_id, size=ORDER_SIZE)
                            current_position = 0
                            active_product_id = None
            else:
                print("⏳ डेटा लोड करत आहे...")

            time.sleep(15)

        except Exception as e:
            print(f"लूप एरर: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_auto_trader()