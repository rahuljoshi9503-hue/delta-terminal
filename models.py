import sqlite3
import datetime

DB_NAME = "universal_trading_platform.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """डेटाबेस टेबल्स तयार करणे आणि इनिशियलाइज करणे"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. युझर्स टेबल
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. ब्रोकर खाती व्हॉल्ट टेबल (AES-256 Encrypted)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_broker_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        broker_name TEXT NOT NULL,
        account_label TEXT,
        api_key_encrypted TEXT NOT NULL,
        api_secret_encrypted TEXT NOT NULL,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # 3. स्ट्रॅटेजीज टेबल
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_strategies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        strategy_name TEXT NOT NULL,
        asset TEXT NOT NULL,
        timeframe TEXT DEFAULT '5m',
        strategy_json TEXT NOT NULL,
        is_running BOOLEAN DEFAULT 0,
        mode TEXT DEFAULT 'paper',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # 4. मास्टर ट्रेड्स लेजर टेबल
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS master_trades_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 1,
        strategy_id TEXT NOT NULL,
        action TEXT NOT NULL,
        symbol TEXT NOT NULL,
        entry_price REAL,
        exit_price REAL,
        pnl REAL DEFAULT 0.0,
        status TEXT DEFAULT 'CLOSED',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database tables initialized successfully.")

if __name__ == "__main__":
    init_db()