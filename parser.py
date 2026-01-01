import re
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tc.edu.tw/page/02b0fa2f-7dda-404f-b411-8286cd97c9c1"
SCHOOL_ATTR_ID = "1"  # 國中

ALLOWED_DISTRICTS = {"北區", "北屯區", "西區", "西屯區", "南屯區"}

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.replace("　", " ").strip()
    s = s.replace("（", "(").replace("）", ")")
    s = s.replace("－", "-").replace("—", "-").replace("～", "-").replace("~", "-")
    s = s.replace("，", ",").replace("、", ",")
    return s

def parse_neighbor_ranges(text: str):
    t = _norm(text).replace("第", "").replace("鄰", "")
    t = t.replace("及", ",")
    parts = [p.strip() for p in re.split(r"[,\s]+", t) if p.strip()]
    out = []
    for p in parts:
        if "-" in p:
            a, b = p.split("-", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                out.append([int(a), int(b)])
        else:
            if p.isdigit():
                out.append(int(p))
    return out

def _likely_manual(detail: str) -> bool:
    d = _norm(detail)
    # 有道路界線、方位、或特殊敘述 → 只靠里+鄰無法100%判定
    keywords = ["以", "路", "街", "巷", "段", "東", "西", "南", "北", "為界", "共同學區", "以東", "以西"]
    return any(k in d for k in keywords)

def extract_area_rules(area_text: str, school: str):
    text = _norm(area_text)

    # 抓出：「行政區 + 里名 + (細節/全里/鄰)」
    pattern = re.compile(
        r"(北區|北屯區|西區|西屯區|南屯區)\s*([^\s()]+?)(?:里)?\s*(\([^)]*\)|全里|第[^區]*?鄰|[0-9][^區]*?鄰)?"
    )

    rules = []
    for m in pattern.finditer(text):
        area_district = m.group(1).strip()
        li_base = m.group(2).strip()
        detail = (m.group(3) or "").strip()

        if area_district not in ALLOWED_DISTRICTS:
            continue
        if len(li_base) < 2:
            continue

        li = li_base if li_base.endswith("里") else (li_base + "里")

        d = detail
        if d.startswith("(") and d.endswith(")"):
            d = d[1:-1].strip()
        d = d.strip()
        if not d:
            continue

        if "全里" in d:
            rules.append({
                "area_district": area_district,
                "li": li,
                "type": "all",
                "ranges": None,
                "school": school,
                "raw": f"{area_district} {li} 全里"
            })
            continue

        if _likely_manual(d):
            rules.append({
                "area_district": area_district,
                "li": li,
                "type": "manual",
                "ranges": None,
                "school": school,
                "raw": f"{area_district} {li} {d}"
            })
            continue

        ranges = parse_neighbor_ranges(d)
        if ranges:
            rules.append({
                "area_district": area_district,
                "li": li,
                "type": "ranges",
                "ranges": ranges,
                "school": school,
                "raw": f"{area_district} {li} {d}"
            })
        else:
            rules.append({
                "area_district": area_district,
                "li": li,
                "type": "manual",
                "ranges": None,
                "school": school,
                "raw": f"{area_district} {li} {d}"
            })

    return rules

def fetch_page(page: int):
    params = {
        "keyword": "",
        "school_attr_id": SCHOOL_ATTR_ID,
        "school_region_id": "",
        "page": str(page),
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.text

def parse_table_rows(html: str):
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        school = tds[1].get_text(" ", strip=True)
        area_text = tds[2].get_text(" ", strip=True)
        if school and area_text:
            rows.append((school, area_text))
    return rows

def fetch_and_parse_rules():
    all_rules = []
    seen = set()

    for page in range(1, 51):  # 保護上限
        html = fetch_page(page)
        rows = parse_table_rows(html)
        if not rows:
            break

        for school, area_text in rows:
            rules = extract_area_rules(area_text, school)
            for r in rules:
                key = (r["area_district"], r["li"], r["type"], str(r.get("ranges")), r["school"], r["raw"])
                if key not in seen:
                    seen.add(key)
                    all_rules.append(r)

    return all_rules
