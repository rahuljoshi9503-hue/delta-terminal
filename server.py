# -*- coding: utf-8 -*-
"""
AI Delta Terminal - Core Backend Server (FastAPI + Strategy Hub + Risk Guard)
Platform: Delta Exchange India & Indian Market Live Feeds
"""

import threading
import time
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

import models
import auth_routes
import ai_routes
import telegram_alert
import strategy1
import strategy2
import strategy3

# FastAPI App इनिशियलायझेशन
app = FastAPI(title="AI Delta Terminal Core", version="2.0")

# CORS सक्षम करणे (Flutter Web व Desktop साठी)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes जोडणे
app.include_router(auth_routes.router)
app.include_router(ai_routes.router)

# रिअल-टाइम इन-मेमरी स्टेट (Dashboard & Circuit Breakers)
trade_data: Dict[str, Any] = {
    "summary": {
            "btc_ltp": 64250.0,
            "nifty_ltp": 24500.0,
            "banknifty_ltp": 52300.0,
            "market_sentiment": {
                "crypto": "SIDEWAYS 🟡",
                "indian": "BULLISH 🟢"
            },
            "live_tickers": [
                {"symbol": "NIFTY 50", "price": "24,580.40", "change": "+0.45%", "type": "NSE IN", "up": True},
                {"symbol": "BANKNIFTY", "price": "52,410.15", "change": "+0.62%", "type": "NSE IN", "up": True},
                {"symbol": "FINNIFTY", "price": "23,890.30", "change": "-0.15%", "type": "NSE IN", "up": False},
                {"symbol": "GOLD (MCX)", "price": "₹71,450", "change": "+0.28%", "type": "MCX", "up": True},
                {"symbol": "BTC / USDT", "price": "$64,250.00", "change": "+1.80%", "type": "CRYPTO", "up": True},
                {"symbol": "ETH / USDT", "price": "$3,480.20", "change": "-0.75%", "type": "CRYPTO", "up": False},
                {"symbol": "SOL / USDT", "price": "$154.60", "change": "+3.10%", "type": "CRYPTO", "up": True}
            ],
            "total_pnl": 0.0,
            "kill_switch_active": False,
            "max_daily_loss": 50.0
        },
        "strategies": {
            "strategy1": {"name": "Fish Indicator (5m)", "status": "Running", "position": "Flat", "pnl": 0.0},
            "strategy2": {"name": "Volatility Option Buyer (5m)", "status": "Running", "position": "Flat", "pnl": 0.0},
            "strategy3": {"name": "30m Delta Strangle", "status": "Running", "position": "Flat", "pnl": 0.0}
        },
        "recent_trades": []
    }

def log_paper_trade(strategy_id: str, action: str, symbol: str, price: float, pnl: float = 0.0):
    """ट्रेडची नोंद घेणे आणि डेटाबेस + डॅशबोर्डवर अपडेट करणे"""
    global trade_data

    # ग्लोबल सर्किट ब्रेकर तपासणी
    if trade_data["summary"]["kill_switch_active"]:
        print(f"🛑 [KILL SWITCH ACTIVE] Trade ignored for {strategy_id}")
        return

    trade_entry = {
        "strategy_id": strategy_id,
        "action": action,
        "symbol": symbol,
        "price": price,
        "pnl": pnl,
        "time": time.strftime("%H:%M:%S")
    }
    trade_data["recent_trades"].insert(0, trade_entry)
    if len(trade_data["recent_trades"]) > 30:
        trade_data["recent_trades"].pop()

    # PnL अपडेट
    trade_data["summary"]["total_pnl"] += pnl
    if strategy_id in trade_data["strategies"]:
        trade_data["strategies"][strategy_id]["pnl"] += pnl

    # Max Loss Circuit Breaker Check
    if trade_data["summary"]["total_pnl"] <= -abs(trade_data["summary"]["max_daily_loss"]):
        trade_data["summary"]["kill_switch_active"] = True
        telegram_alert.send_alert(
            f"🚨 *[CIRCUIT BREAKER TRIGGERED]* Max Daily Loss reached: "
            f"${trade_data['summary']['total_pnl']:.2f}. System Locked!"
        )[span_1](start_span)[span_1](end_span)

    # SQLite डेटाबेसमध्ये सुरक्षित नोंद
    try:
        conn = models.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO master_trades_ledger (strategy_id, action, symbol, entry_price, pnl, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (strategy_id, action, symbol, price, pnl, "EXECUTED"))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Logging Error: {e}")

@app.on_event("startup")
def startup_event():
    models.init_db()

    # स्ट्रॅटेजीज बॅकग्राउंड थ्रेड्समध्ये सुरू करणे
    t1 = threading.Thread(target=strategy1.start, daemon=True)
    t2 = threading.Thread(target=strategy2.start, daemon=True)
    t3 = threading.Thread(target=strategy3.start, daemon=True)

    t1.start()
    t2.start()
    t3.start()
    print("🚀 All strategy background workers successfully started.")

@app.get("/")
def root():
    return {"message": "AI Delta Terminal Server Online", "status": "active"}

@app.get("/api/terminal/status")
def get_terminal_status():
    """Flutter मोबाईल ॲपसाठी रिअल-टाइम डेटा एंडपॉईंट"""
    return trade_data

@app.post("/api/terminal/kill-switch")
def trigger_kill_switch():
    """आपत्कालीन किल स्विच (सर्व ट्रेड्स बंद करणे)"""
    trade_data["summary"]["kill_switch_active"] = True
    telegram_alert.send_alert("Emergency Kill Switch Activated")
    return {"status": "success", "message": "Kill Switch On"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)