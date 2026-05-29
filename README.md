# 🚗 CarDex

実車写真から車種を当てるクイズと、見分け方つきの図鑑で「車を覚える」学習Webアプリ。

**公開URL**: https://tomokinozawa.github.io/car-dex/

## 機能
- **クイズ**: 実車写真→4択（車種 / メーカー / タイプ当て）。やさしい/むずかしい、出題範囲(全車/カテゴリ別)、苦手復習モード、ヒント(シルエット/メーカー)
- **図鑑**: 60車種を検索/フィルタ/ソート。複数アングルのギャラリー＋見分けポイント＋マスター度
- **統計**: マスター数・正答率・苦手車ランキング
- 学習進捗は端末に保存（※将来 Firebase アカウント保持へ移行予定）

## 収録
日本でよく見る人気車60台。トヨタは現行ラインナップ全種＋軽・他社人気車。

## 構成
- `index.html` — アプリ本体（単一ファイル）
- `data/cars.json` — 車データ（見分けポイント＋画像参照）
- `images/cars/<id>/` — 実車写真（各3枚, webp）
- `scripts/cars_master.json`, `scripts/collect_images.py` — データ生成パイプライン
- `CREDITS.md` — 全画像の撮影者・ライセンス・出典
- `DESIGN.md` — 設計書・開発フェーズ

## 画像について
全画像は Wikimedia Commons のフリーライセンス（CC0 / CC BY / CC BY-SA / Public Domain）。帰属は `CREDITS.md` 参照。

## 車種の追加
`scripts/cars_master.json` に1エントリ足して再実行するだけ：
```
bash ~/.claude/scripts/run_py.sh scripts/collect_images.py --only <id>
```
