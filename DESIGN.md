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
- [x] **Phase 2 クイズMVP**: 車種当て4択・繰り返し・スコア(単一HTML)
- [x] **Phase 3 図鑑+復習+モード**: 図鑑(検索/フィルタ/ソート/詳細モーダル)・苦手復習(Leitner)・メーカー/ボディタイプ当て・ヒント・統計。※ロゴ当てのみ未実装(下記)
- [x] **デプロイ**: GitHub Pages 公開 https://tomokinozawa.github.io/car-dex/ + NozaBoardリンク
- [x] **デイリーチャレンジ**: 日付シード固定10問・最高記録保存(localStorage、Firebase不要)
- [ ] **Phase 4 Firebase アカウント保持**: 設計済(下記)。実装は現行Rules取得後
- [ ] **ロゴ当てモード**: 設計済(下記)。ロゴ素材収集・商標ライセンス検討後

## 残タスク整理（優先度・ブロッカー付き）
| # | タスク | 優先 | ブロッカー | 状態 |
|---|---|---|---|---|
| T1 | ブラウザ実機テスト(スマホ/PC) | 高 | ユーザー操作 | 待ち(構文+ロジックは自動検証済) |
| T2 | Phase4 Firebase アカウント保持 | 高 | **現行Firebase Rules全文** + 相乗りプロジェクト確認 | 設計済↓ |
| T3 | 一部の車の主画像が後方アングル→前方差し替え | 中 | なし(目視作業) | 未(図鑑ギャラリーで吸収中) |
| T4 | 全60台の画像 目視QA(未チェック42台) | 中 | なし | 18台確認済/42台未 |
| T5 | ロゴ当てモード(ロゴ素材+UI) | 中 | ロゴ画像の商標ライセンス検討 | 設計済↓ |
| T6 | 収録車の拡張(輸入車/旧車/スポーツ追加) | 低 | ユーザー方針 | 任意 |
| T7 | デイリーの結果をアカウント保持・連続日数(ストリーク) | 低 | T2(Firebase) | T2に内包 |

## Phase 4 設計: Firebase アカウント保持
**目的**: 学習進捗(成績/マスター度/苦手/デイリー記録)を端末でなくアカウントに保持し、機種変・別端末でも継続。

- **相乗り**: 既存Firebaseプロジェクトに名前付きインスタンスで相乗り（`firebase.initializeApp(config,'cardex')`、参照 memory feedback_firebase_named_instance）。Storageは使わず画像はrepo同梱継続(Sparkプラン維持)。
- **Auth**: Googleログイン(Prismaera同方式)。未ログイン時はゲスト=localStorageのまま動作し、ログイン時にマージアップロード。
- **保存先(Realtime DB)**:
  ```
  /cardex/$uid/
    cars/$carId/{shown,correct,wrong,box,last}   // 1台ごとの進捗(現localStorage PROGと同形)
    daily/{date,best,plays,streak}               // デイリー結果+連続日数
    updatedAt
  ```
- **クライアント実装方針**:
  1. 現状の `PROG`(localStorage) を「ローカルキャッシュ」に格上げ。
  2. ログイン時: DB値とローカル値を **box/correct/shown を車ごとに max マージ**(古い端末で上書き事故を防ぐ) → DBへ書き戻し。
  3. 以後 `save()` を「localStorage + デバウンスでDB書き込み」に。
  4. 既存の `load/save/p()` を抽象化(store層)するだけで画面ロジックは不変。
- **Rules(提案・未確定)**: `/cardex/$uid` は本人のみ read/write。**実適用前に現行Rules全文をユーザーから取得し、既存path(prismaera等)を壊さない全置換版を作る**(CLAUDE.md 全置換ルール)。
- **未決**: ①ゲスト→ログイン時のマージUI(自動 or 確認) ②匿名Authを使うか(端末跨ぎ不可なので原則Googleのみ)。

## 設計: ロゴ当てモード
- **概要**: ブランドエンブレム画像を出し、4択でメーカーを当てる(`mode='logo'`)。既存の maker当てモードのロジックを流用でき、画像ソースだけ差し替え。
- **データ**: `makers.json` を新設 = `[{maker,makerEn,logo:"images/logos/toyota.webp"}]`。クイズは7メーカーから出題。
- **素材**: 7社ロゴ(トヨタ/スズキ/ホンダ/日産/ダイハツ/マツダ/スバル)。Wikimedia Commons の `{{PD-textlogo}}`(単純図形=非著作物) or SVG を確認して採用。**商標のため「識別目的の教育利用」範囲で使用**、出典明記。collect_images.py はSVG除外なので別途取得ルート(SVG→PNGラスタ化 or PD-textlogo PNG)が必要。
- **UI**: 出題タイプsegに「ロゴ」を追加。画像枠にロゴを `object-fit:contain`+白背景で表示(写真と別スタイル)。
- **ブロッカー**: ロゴ画像のライセンス精査(企業ロゴは{{trademark}}が付くため、PD-textlogo該当かを1社ずつ確認)。

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
