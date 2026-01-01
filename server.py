import os
import json
import time
from flask import Flask, request, jsonify, send_from_directory
from parser import fetch_and_parse_rules

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(APP_DIR, "cache.json")

ALLOWED_DISTRICTS = {"北區", "北屯區", "西區", "西屯區", "南屯區"}
CACHE_TTL_SECONDS = 86400  # 24 小時

app = Flask(__name__, static_folder="web")

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"updated_at": 0, "rules": []}
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def ensure_cache_fresh():
    cache = load_cache()
    now = int(time.time())
    if (now - cache.get("updated_at", 0) > CACHE_TTL_SECONDS) or (not cache.get("rules")):
        rules = fetch_and_parse_rules()
        rules = [r for r in rules if r.get("area_district") in ALLOWED_DISTRICTS]
        cache = {"updated_at": now, "rules": rules}
        save_cache(cache)
    return cache

def normalize_text(s: str) -> str:
    return (s or "").strip().replace("　", "").replace(" ", "")

def normalize_li(li: str) -> str:
    li = normalize_text(li)
    if li and not li.endswith("里"):
        li += "里"
    return li

def in_ranges(n: int, ranges):
    for r in ranges:
        if isinstance(r, int) and n == r:
            return True
        if isinstance(r, list) and len(r) == 2 and r[0] <= n <= r[1]:
            return True
    return False
@app.get("/api/meta")
def api_meta():
    cache = load_cache()
    return jsonify({"ok": True, "updated_at": cache.get("updated_at", 0), "districts": sorted(ALLOWED_DISTRICTS)})

@app.get("/api/update")
def api_update():
    try:
        rules = fetch_and_parse_rules()
        rules = [r for r in rules if r.get("area_district") in ALLOWED_DISTRICTS]
        cache = {"updated_at": int(time.time()), "rules": rules}
        save_cache(cache)
        return jsonify({"ok": True, "rules": len(rules), "districts": sorted(ALLOWED_DISTRICTS)})
    except Exception as e:
        # 不讓服務掛掉，回傳錯誤給前端顯示
        return jsonify({"ok": False, "error": f"更新失敗：{type(e).__name__}"})

@app.get("/api/query")
def api_query():
    district = normalize_text(request.args.get("district"))
    li = normalize_li(request.args.get("li"))
    lin_str = normalize_text(request.args.get("lin"))

    if district not in ALLOWED_DISTRICTS:
        return jsonify({"ok": False, "error": "行政區不在查詢範圍（北區/北屯區/西區/西屯區/南屯區）"})

    if not li:
        return jsonify({"ok": False, "error": "請輸入里名"})

    if not lin_str.isdigit():
        return jsonify({"ok": False, "error": "鄰請輸入數字（正整數）"})

    lin = int(lin_str)
    cache = ensure_cache_fresh()
    rules = cache.get("rules", [])

    hits = []
    manual = []

    for r in rules:
        if r.get("area_district") != district:
            continue
        if r.get("li") != li:
            continue

        if r.get("type") == "all":
            hits.append(r)
        elif r.get("type") == "ranges":
            if in_ranges(lin, r.get("ranges", [])):
                hits.append(r)
        elif r.get("type") == "manual":
            manual.append(r)

    if hits:
        schools = sorted(set(h["school"] for h in hits))
        status = "ok" if len(schools) == 1 else "overlap"
        return jsonify({"ok": True, "status": status, "schools": schools})

    if manual:
        return jsonify({
            "ok": True,
            "status": "manual",
            "message": "官方資料含道路/方位/文字界線，僅輸入里+鄰無法百分百判定，請依原文人工確認。",
            "candidates": manual[:50]
        })

    return jsonify({"ok": True, "status": "not_found", "message": "依教育局學區查詢資料查無對應"})

@app.get("/")
def index():
    return send_from_directory("web", "index.html")

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory("web", path)
