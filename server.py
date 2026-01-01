from flask import Flask, request, jsonify, send_from_directory
import os
import json
import time

app = Flask(__name__, static_folder="web")

CACHE_FILE = "cache.json"
ALLOWED_DISTRICTS = {"北區", "北屯區", "西區", "西屯區", "南屯區"}
CACHE_TTL_SECONDS = 86400  # 24 小時

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"updated_at": 0, "rules": []}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_cache():
    cache = load_cache()
    now = int(time.time())
    if now - cache["updated_at"] > CACHE_TTL_SECONDS or not cache["rules"]:
        # 之後由 parser.py 來補
        cache = {"updated_at": now, "rules": []}
        save_cache(cache)
    return cache

@app.get("/api/query")
def query():
    district = request.args.get("district", "").strip()
    li = request.args.get("li", "").strip()
    lin = request.args.get("lin", "").strip()

    if district not in ALLOWED_DISTRICTS:
        return jsonify({"ok": False, "error": "行政區不在查詢範圍"})

    if not lin.isdigit():
        return jsonify({"ok": False, "error": "鄰請輸入數字"})

    return jsonify({
        "ok": True,
        "message": "伺服器正常，下一步會接上官方學區資料"
    })

@app.get("/")
def index():
    return send_from_directory("web", "index.html")
