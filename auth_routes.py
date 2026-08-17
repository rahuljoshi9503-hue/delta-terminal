from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import sqlite3
import models
import security

router = APIRouter(prefix="/api/auth", tags=["Auth & Broker Accounts"])

class UserRegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLoginRequest(BaseModel):
    username: str
    password: str

class BrokerAccountAddRequest(BaseModel):
    user_id: int = 1
    broker_name: str
    account_label: Optional[str] = "Default Account"
    api_key: str
    api_secret: str

@router.post("/register")
def register_user(data: UserRegisterRequest):
    conn = models.get_db_connection()
    cursor = conn.cursor()

    hashed_pwd = security.hash_password(data.password)
    try:
        cursor.execute(
            "INSERT INTO users (username, hashed_password, email) VALUES (?, ?, ?)",
            (data.username, hashed_pwd, data.email)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"status": "success", "message": "User registered successfully", "user_id": user_id}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Username already exists")
    finally:
        conn.close()

@router.post("/login")
def login_user(data: UserLoginRequest):
    conn = models.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, hashed_password FROM users WHERE username = ?", (data.username,))
    user = cursor.fetchone()
    conn.close()

    if not user or not security.verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "status": "success",
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"]
        }
    }

@router.post("/add-broker-account")
def add_broker_account(data: BrokerAccountAddRequest):
    encrypted_key = security.encrypt_api_key(data.api_key)
    encrypted_secret = security.encrypt_api_key(data.api_secret)

    conn = models.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO user_broker_accounts 
            (user_id, broker_name, account_label, api_key_encrypted, api_secret_encrypted)
            VALUES (?, ?, ?, ?, ?)
        """, (data.user_id, data.broker_name, data.account_label, encrypted_key, encrypted_secret))
        conn.commit()
        account_id = cursor.lastrowid
        return {"status": "success", "message": f"{data.broker_name} account connected successfully", "account_id": account_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()