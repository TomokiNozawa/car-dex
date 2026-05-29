# -*- coding: utf-8 -*-
"""QA用コンタクトシート生成。各車の画像3枚を横並べ、N車/枚 でタイル化して qa/ に出力。
使い方: bash run_py.sh make_montage.py [--ids a,b,c] [--per 8]
ラベルはASCII(id/makerEn/index)のみ(PIL既定フォントが日本語非対応のため)。"""
import argparse, json, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "cars.json")
QA = os.path.join(ROOT, "qa")

TW, TH = 300, 188          # サムネ枠
LBL = 16                   # 左ラベル幅の係数
PAD = 6

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--per", type=int, default=8)
    args = ap.parse_args()
    cars = json.load(open(DATA, encoding="utf-8"))["cars"]
    if args.ids:
        want = [s.strip() for s in args.ids.split(",")]
        cars = [c for c in cars if c["id"] in want]
    os.makedirs(QA, exist_ok=True)
    # clear old sheets
    for f in os.listdir(QA):
        if f.startswith("sheet_"):
            os.remove(os.path.join(QA, f))

    rowh = TH + 26
    leftw = 150
    sheetw = leftw + 3 * (TW + PAD) + PAD
    per = args.per
    sheets = [cars[i:i+per] for i in range(0, len(cars), per)]
    for si, group in enumerate(sheets):
        sheeth = PAD + len(group) * rowh + PAD
        im = Image.new("RGB", (sheetw, sheeth), (24, 28, 34))
        d = ImageDraw.Draw(im)
        for ri, c in enumerate(group):
            y = PAD + ri * rowh
            d.text((6, y + 4), c["id"], fill=(120, 230, 230))
            d.text((6, y + 18), c.get("makerEn", ""), fill=(150, 160, 175))
            d.text((6, y + 34), c.get("bodyType", ""), fill=(150, 160, 175))
            for k, img in enumerate(c.get("images", [])[:3]):
                x = leftw + k * (TW + PAD)
                try:
                    th = Image.open(os.path.join(ROOT, img["file"].replace("/", os.sep))).convert("RGB")
                    th.thumbnail((TW, TH))
                    ox = x + (TW - th.width) // 2
                    oy = y + (TH - th.height) // 2
                    im.paste(th, (ox, oy))
                except Exception as e:
                    d.text((x + 4, y + 4), "ERR", fill=(255, 80, 80))
                d.rectangle([x, y, x + TW, y + TH], outline=(60, 70, 84))
                d.text((x + 4, y + 2), "[" + str(k + 1) + "]", fill=(255, 220, 90))
            d.line([(0, y + rowh - 2), (sheetw, y + rowh - 2)], fill=(45, 54, 66))
        out = os.path.join(QA, "sheet_%02d.webp" % si)
        im.save(out, "WEBP", quality=80)
        print(out, "(%d cars)" % len(group))

if __name__ == "__main__":
    main()
