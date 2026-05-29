# -*- coding: utf-8 -*-
"""
collect_images.py — CarDex 画像収集パイプライン

cars_master.json を読み、各車について Wikimedia Commons から
フリーライセンスの実車写真を収集 → webp 化して images/cars/<id>/ に保存 →
属性(撮影者/ライセンス/出典)を記録 → data/cars.json と CREDITS.md を生成する。

使い方:
  bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py            # 全車
  bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py --only prius,n-box,alphard,jimny,cx-5
  bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py --only prius --list-only   # DLせず候補確認のみ
  オプション: --max 3 (1車あたり画像数) / --candidates 12 (検索取得数) / --min-width 800
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = os.path.join(ROOT, "scripts", "cars_master.json")
IMG_DIR = os.path.join(ROOT, "images", "cars")
DATA_DIR = os.path.join(ROOT, "data")
API = "https://commons.wikimedia.org/w/api.php"
UA = "CarDexBot/0.1 (personal car-learning app; contact tomoki.nozawa@dikandcompany.co.jp)"

# 許可ライセンス(フリー)。non-free / fair use は除外。
ALLOWED_LICENSE_PREFIX = ("cc0", "cc-by", "cc-by-sa", "pd", "public domain")
# クイズに不向きな写真をファイル名で除外(内装/部品/ロゴ等)
BAD_KEYWORDS = (
    "interior", "dashboard", "engine", "motor", "seat", "instrument", "cockpit",
    "gauge", "trunk", "boot", "wheel", "rim", "logo", "emblem", "badge", "gearbox",
    "headlamp", "taillight", "tail light", "drawing", "blueprint", "diagram",
    "chassis", "frame", "cutaway", "assembly", "production line", "factory",
)


def http_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def http_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def license_ok(ext):
    lic = (ext.get("License", {}).get("value") or "").lower()
    short = (ext.get("LicenseShortName", {}).get("value") or "").lower()
    blob = lic + " " + short
    if not blob.strip():
        return None
    if "fair use" in blob or "nonfree" in blob or "non-free" in blob:
        return None
    if any(blob.startswith(p) or (" " + p) in (" " + blob) for p in ALLOWED_LICENSE_PREFIX):
        return ext.get("LicenseShortName", {}).get("value") or lic
    # 個別に cc0 / pd を拾う
    if "cc0" in blob or blob.startswith("pd") or "public domain" in blob:
        return ext.get("LicenseShortName", {}).get("value") or lic
    return None


def filename_ok(title):
    low = title.lower()
    return not any(k in low for k in BAD_KEYWORDS)


def search_images(term, candidates, min_width, exclude=None):
    """Commons をフルテキスト検索し、フリー & 適切な画像候補を返す。"""
    exclude = [e.lower() for e in (exclude or [])]
    params = {
        "action": "query", "format": "json",
        "generator": "search", "gsrnamespace": "6",
        "gsrsearch": term, "gsrlimit": str(candidates),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": "1280",
        "iiextmetadatafilter": "License|LicenseShortName|Artist|LicenseUrl",
    }
    try:
        data = http_json(params)
    except Exception as e:
        print(f"    ! search error: {e}")
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        title = p.get("title", "")
        ii = (p.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        if not mime.startswith("image/") or "svg" in mime:
            continue
        if not filename_ok(title):
            continue
        if exclude and any(x in title.lower() for x in exclude):
            continue
        w = ii.get("width", 0)
        h = ii.get("height", 0)
        if w and w < min_width:
            continue
        # 極端な縦横比(看板やパーツ)を除外
        if w and h and (w / h > 3 or h / w > 1.6):
            continue
        ext = ii.get("extmetadata", {})
        lic = license_ok(ext)
        if not lic:
            continue
        low = title.lower()
        # 主画像は前方〜斜め前が望ましい。後方/真後ろは後ろに回す(学習用に保持はする)
        is_rear = 1 if any(k in low for k in ("rear", "back", "behind", " r.jpg", "-r.jpg")) else 0
        out.append({
            "title": title,
            "thumb": ii.get("thumburl") or ii.get("url"),
            "source": ii.get("descriptionurl") or ("https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title)),
            "author": strip_html(ext.get("Artist", {}).get("value", "")) or "Unknown",
            "license": lic,
            "index": p.get("index", 999),
            "is_rear": is_rear,
        })
    # 前方優先 → 検索関連度順
    out.sort(key=lambda x: (x["is_rear"], x["index"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="id をカンマ区切りで指定(部分実行)")
    ap.add_argument("--max", type=int, default=3, help="1車あたり保存画像数")
    ap.add_argument("--candidates", type=int, default=14, help="検索で取得する候補数(検索語ごと)")
    ap.add_argument("--min-width", type=int, default=800)
    ap.add_argument("--list-only", action="store_true", help="DLせず候補だけ表示")
    args = ap.parse_args()

    try:
        from PIL import Image
    except Exception as e:
        print("Pillow が必要です:", e)
        sys.exit(1)

    with open(MASTER, encoding="utf-8") as f:
        master = json.load(f)
    cars = master["cars"]
    if args.only:
        want = set(s.strip() for s in args.only.split(","))
        cars = [c for c in cars if c["id"] in want]

    os.makedirs(DATA_DIR, exist_ok=True)
    out_cars = []
    summary = []

    for c in cars:
        cid = c["id"]
        print(f"\n== {cid} ({c['name']} / {c['maker']}) ==")
        seen_titles = set()
        picks = []
        for term in c.get("search", []):
            if len(picks) >= args.candidates:
                break
            for cand in search_images(term, args.candidates, args.min_width, c.get("exclude")):
                if cand["title"] in seen_titles:
                    continue
                seen_titles.add(cand["title"])
                picks.append(cand)
            time.sleep(0.4)
        # 全候補で前方写真を優先(安定ソートで関連度順は保持)
        picks.sort(key=lambda x: x["is_rear"])

        if args.list_only:
            for i, p in enumerate(picks[: args.max + 4]):
                print(f"    [{i}] {p['title']}  | {p['license']} | {p['author'][:40]}")
            continue

        car_img_dir = os.path.join(IMG_DIR, cid)
        os.makedirs(car_img_dir, exist_ok=True)
        saved = []
        n = 0
        for p in picks:
            if n >= args.max:
                break
            try:
                raw = http_bytes(p["thumb"])
                im = Image.open(io.BytesIO(raw)).convert("RGB")
                if im.width > 1280:
                    ratio = 1280 / im.width
                    im = im.resize((1280, int(im.height * ratio)))
                fname = f"{cid}-{n+1}.webp"
                im.save(os.path.join(car_img_dir, fname), "WEBP", quality=82, method=6)
                saved.append({
                    "file": f"images/cars/{cid}/{fname}",
                    "author": p["author"],
                    "license": p["license"],
                    "source": p["source"],
                })
                print(f"    + {fname}  ({p['license']}, {p['author'][:30]})")
                n += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"    ! skip {p['title']}: {e}")

        car_out = {k: c[k] for k in c if k not in ("search", "exclude")}
        car_out["images"] = saved
        out_cars.append(car_out)
        summary.append((cid, len(saved)))

    if args.list_only:
        return

    # data/cars.json は「全車を読み、今回処理した分だけ images を更新」する形でマージ
    out_path = os.path.join(DATA_DIR, "cars.json")
    existing = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            for car in json.load(f).get("cars", []):
                existing[car["id"]] = car
    for car in out_cars:
        existing[car["id"]] = car
    # master の順序を維持
    ordered = [existing[c["id"]] for c in master["cars"] if c["id"] in existing]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"version": master["_meta"]["version"],
                   "categories": master["_meta"]["categories"],
                   "cars": ordered}, f, ensure_ascii=False, indent=2)

    # CREDITS.md
    credits = ["# CarDex 画像クレジット\n",
               "全画像は Wikimedia Commons のフリーライセンス(CC0 / CC BY / CC BY-SA / Public Domain)写真です。\n"]
    for car in ordered:
        if not car.get("images"):
            continue
        credits.append(f"\n## {car['name']} ({car['maker']})")
        for im in car["images"]:
            credits.append(f"- {im['file']} — {im['author']} / {im['license']} — {im['source']}")
    with open(os.path.join(ROOT, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(credits) + "\n")

    print("\n==== SUMMARY ====")
    ok = sum(1 for _, n in summary if n > 0)
    print(f"処理 {len(summary)}車 / 画像取得できた {ok}車")
    for cid, n in summary:
        mark = "OK" if n >= args.max else ("LOW" if n > 0 else "ZERO")
        print(f"  [{mark}] {cid}: {n}枚")


if __name__ == "__main__":
    main()
