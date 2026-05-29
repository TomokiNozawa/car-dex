# CarDex 設計書 v0.1

車を全く知らない人が「街で見た車を当てられる」ようになる学習アプリ。クイズ + 図鑑 + 苦手復習。

## 確定方針
- 画像: 実車写真をキュレーション（Wikimedia Commons の CC ライセンス）
- 範囲: 日本でよく見る人気車中心。**トヨタは現行ラインナップ全種**を収録。初期60台。
- 構成: 単一ページ Web アプリ + Firebase（アカウント保持）、公開は GitHub Pages（個人利用）

## 機能
1. **クイズ**: 実車写真→4択。車種当て / メーカー当て / ロゴ当て / ボディタイプ当て。難易度(やさしい=バラバラ4択 / むずかしい=同カテゴリ4択)。出題範囲3階層(全車/カテゴリ別/苦手のみ)。ヒント(シルエット/一部表示/メーカー)
2. **図鑑**: 検索/フィルタ(メーカー・ボディタイプ)/ソート。複数アングルのギャラリー、見分けポイント、マスター度バッジ
3. **苦手復習**: Leitner式 間隔反復。間違えた車を優先再出題
4. **やり込み**: スコア/連続正解/デイリーチャレンジ/統計(苦手車ランキング・マスター数)

## データ
- `scripts/cars_master.json`: 車マスター(id/name/maker/bodyType/category/years/features/distinguish/search[/exclude])
- `data/cars.json`: アプリ用(マスター + images[]) ← collect_images.py が生成
- `images/cars/<id>/<id>-N.webp`: 実車写真(各車3枚、前方優先、最大幅1280/webp q82)
- ユーザー進捗: Firebase Realtime DB `/cardex/$uid/`(車ごとの出題/正答/Leitner/次回出題日, スコア, 設定) ※Phase4
- 画像は Firebase Storage を使わず repo 同梱(Sparkプラン維持)。属性は CREDITS.md

## カテゴリ(distractor グルーピング)
kei(軽) / compact / sedan(セダン・ハッチ) / minivan / suv / sports / van(商用)

## 開発フェーズ
- [x] **Phase 1 データ整備**: 60台 + 180画像収集・ライセンス検証・cars.json生成
- [ ] **Phase 2 クイズMVP**: 車種当て4択・繰り返し・スコア(単一HTML、ローカル動作)
- [ ] **Phase 3 図鑑+復習+モード**: 図鑑(検索/フィルタ/ソート)・苦手復習・メーカー/ロゴ/ボディタイプ・ヒント
- [ ] **Phase 4 Firebase+公開**: Auth・進捗保存・統計・デイリー、GitHub Pages反映

## 画像収集の使い方
```
bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py                 # 全車
bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py --only prius     # 部分
bash ~/.claude/scripts/run_py.sh ~/car-dex/scripts/collect_images.py --only prius --list-only  # 候補確認
```
- フリーライセンス(cc0/cc-by/cc-by-sa/pd)のみ採用。内装/部品/ロゴ等はファイル名で除外。
- 前方写真を主画像に優先(後方は学習バリエーションとして後ろに保持)。
- 検索で別車種が混じる場合は master の `exclude`(例 gr-corolla: ["gr sport","touring"])で弾く。

## 既知メモ
- century は先代G50画像(形は象徴的で許容)。新型3代目の良質フリー画像が少ない。
- probox は1代目寄り(形は同系統)。
- 主画像が後方になる車が一部あり→図鑑はギャラリー表示で吸収、Phase3で前方差し替え検討可。
