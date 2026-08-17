import time
import threading
from flask import Flask, jsonify
from flask_cors import CORS
import strategy1
import strategy2
import strategy3

# १. मोबाईल ॲपसाठी Flask API तयार करणे
app = Flask(__name__)
CORS(app)  # सर्व ॲप्स आणि ब्राऊझरसाठी परमिशन

@app.route('/')
def home():
    return jsonify({"status": "Server Running", "app": "AI Delta Terminal"})

@app.route('/api/terminal/status', methods=['GET'])
def terminal_status():
    return jsonify({
        "status": "Running",
        "pnl": 0.0,
        "active_trades": [],
        "last_signal": "NONE",
        "market": "BANKNIFTY"
    })

@app.route('/api/terminal/kill-switch', methods=['POST'])
def kill_switch():
    return jsonify({"status": "success", "message": "Emergency Stop Triggered"})

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# २. मुख्य प्रोग्राम सुरू करणे
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AI Delta Terminal - Direct Live Engine + API सुरू होत आहे...")
    print("=" * 60)

    # API सर्व्हर बॅकग्राउंडमध्ये सुरू करणे
    api_thread = threading.Thread(target=run_flask, daemon=True)
    api_thread.start()

    # तिन्ही स्ट्रॅटेजीज सुरू करणे
    t1 = threading.Thread(target=strategy1.start, daemon=True)
    t2 = threading.Thread(target=strategy2.start, daemon=True)
    t3 = threading.Thread(target=strategy3.start, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    # कन्सोल चालू ठेवण्यासाठी लूप
    while True:
        time.sleep(1)