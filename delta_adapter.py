import time
import requests
from typing import List, Dict, Any
from base_broker import BaseBroker

class DeltaAdapter(BaseBroker):
    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.india.delta.exchange"

    def get_candles(self, symbol: str = "BTCUSD", resolution: str = "5m", limit: int = 100) -> List[Dict[str, Any]]:
        """Delta Exchange India कडून कँडल्स डेटा फेच करणे"""
        try:
            # Resolution मॅपिंग (उदा. '5m' -> '5', '30m' -> '30')
            res_val = resolution.replace("m", "")
            end_time = int(time.time())
            start_time = end_time - (limit * int(res_val) * 60)

            url = f"{self.base_url}/v2/history/candles"
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
                        "time": d["time"]
                    } for d in data]
        except Exception as e:
            print(f"[DeltaAdapter Fetch Error]: {e}")
        return []

    def place_order(self, symbol: str, size: int, side: str, order_type: str = "market", price: float = 0.0) -> Dict[str, Any]:
        """लाइव्ह ऑर्डर एक्झिक्युशन (Paper Mode मध्ये व्हर्च्युअल रिटर्न)"""
        return {"status": "success", "mode": "paper", "symbol": symbol, "size": size, "side": side}

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def get_balance(self) -> float:
        return 10000.0