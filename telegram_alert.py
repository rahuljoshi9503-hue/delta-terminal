import requests

def send_alert(message: str) -> bool:
    """टेलिग्रामवर मेसेज पाठवण्यासाठी सुरक्षित फंक्शन"""
    token = "8504808734:AAFKsO180rGQL3U2ijYpUZ7_KPJFkezLrh4"
    chat_id = "1250528464"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram alert failed: {e}")
        return False

if __name__ == "__main__":
    send_alert("🚀 *AI Delta Terminal* Alert Engine Online!")