import base64
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from passlib.context import CryptContext

# पासवर्ड हॅशिंगसाठी
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# मास्टर सिक्रेट की
MASTER_ENCRYPTION_KEY = hashlib.sha256(b"DELTA_SUPER_SECRET_VAULT_KEY_2026").digest()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def encrypt_api_key(plain_text: str) -> str:
    """API Key ला AES-256 द्वारे एन्क्रिप्ट करणे"""
    if not plain_text:
        return ""
    try:
        iv = get_random_bytes(16)
        cipher = AES.new(MASTER_ENCRYPTION_KEY, AES.MODE_CBC, iv)
        pad_len = 16 - (len(plain_text.encode()) % 16)
        padded_data = plain_text.encode() + bytes([pad_len] * pad_len)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(iv + encrypted).decode()
    except Exception as e:
        print(f"Encryption Error: {e}")
        return ""

def decrypt_api_key(cipher_text: str) -> str:
    """डेटाबेसमधून API Key डिक्रिप्ट करणे"""
    if not cipher_text:
        return ""
    try:
        raw = base64.b64decode(cipher_text.encode())
        iv = raw[:16]
        encrypted_data = raw[16:]
        cipher = AES.new(MASTER_ENCRYPTION_KEY, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(encrypted_data)
        pad_len = decrypted_padded[-1]
        return decrypted_padded[:-pad_len].decode()
    except Exception as e:
        print(f"Decryption Error: {e}")
        return ""