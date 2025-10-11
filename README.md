# Reinforcement-LearningOfMahjong

Transformerベースの麻雀AIをローカル環境で強化学習させることを目的としたプロジェクトです。自己対戦を通じてデータ収集・モデル更新を繰り返し、より高い雀力を持つエージェントを育成します。

---

## 目次
- 概要
- 動作環境
- セットアップ手順
- 実行方法
- **mahjongライブラリの基本的な使い方**
- 学習状況の確認
- ディレクトリ構成
- ドキュメント
- 更新履歴

---

## 概要
本プロジェクトは以下の強化学習サイクルを回します：  
自己対戦 → データ収集 → モデル更新。  
モデルは主にTransformerを用いて設計されています。

---

## 動作環境（確認済み）
- OS: Windows  
- Python: 3.10.x (64-bit)  
- 主要ライブラリ:
  - tensorflow-cpu==2.10
  - tensorflow-directml-plugin（GPU利用時）
  - numpy==1.23.5
  - mahjong

注意: TensorFlow 2.10 は NumPy 2.x 系と互換性がないため、指定された NumPy バージョンを使用してください。詳細は requirements.txt を参照してください。

---

## セットアップ手順

1. プロジェクトルートへ移動
```powershell
cd c:\Work\Reinforcement-LearningOfMahjong
```

2. 仮想環境の作成と有効化（PowerShell）
```powershell
# 初回のみ
python -m venv .venv

# 有効化
.\.venv\Scripts\Activate.ps1
```

3. pip を最新にして依存関係をインストール
```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 実行方法

1. （任意）初期学習モデルを配置  
学習のベースとなるモデルファイルがある場合、プロジェクトルートに `models/initial_model.keras` を配置します。無ければランダム初期重みで開始します。

2. 強化学習を開始
```powershell
python main.py
```
実行成功後、コンソールに自己対戦のログが表示され、1ゲーム終了ごとに学習が行われます。

---

## mahjongライブラリの基本的な使い方

本プロジェクトで利用している `mahjong` ライブラリの主要な機能（シャンテン数計算、点数計算など）の簡単な使用例を以下に示します。

- **シャンテン数の計算**:
  ```python
  from mahjong.tile import TilesConverter
  from mahjong.shanten import Shanten

  # 聴牌まであと1枚の手牌（一向聴）
  hand_tiles = TilesConverter.string_to_136_array(man='123', pin='456', sou='789', honors='112')
  hand_34_array = TilesConverter.to_34_array(hand_tiles)

  shanten_calculator = Shanten()
  shanten_result = shanten_calculator.calculate_shanten(hand_34_array)

  print(f"シャンテン数: {shanten_result}") # -> 1
  ```

- **点数の計算**:
  ```python
  from mahjong.tile import TilesConverter
  from mahjong.hand_calculating.hand import HandCalculator
  from mahjong.hand_calculating.hand_config import HandConfig

  # 平和・ツモ・ドラ1 の手牌
  calculator = HandCalculator()
  hand_tiles = TilesConverter.string_to_136_array(man='234', pin='567', sou='789', honors='11')
  win_tile = TilesConverter.string_to_136_array(pin='4')[0]

  result = calculator.estimate_hand_value(
      sorted(hand_tiles + [win_tile]),
      win_tile,
      config=HandConfig(is_tsumo=True)
  )

  if not result.error:
      print(f"翻: {result.han}, 符: {result.fu}")
      print(f"点数: {result.cost['main']}点")
  else:
      print(f"エラー: {result.error}")
  ```

より詳細な使い方については、以下のドキュメントを参照してください。
- [mahjongライブラリ利用ガイド](./doc/mahjong_library_usage.md)

---

## 学習状況の確認

本プロジェクトでは、AIの学習進捗や対戦内容を可視化するための2つのツールを提供しています。

1. 対戦内容のリプレイ (GUI Viewer)  
自己対戦で生成されたログファイルをGUIで再生し、AIの打牌を一手ずつ確認できます。プロジェクトルートにある `mahjong_viewer.html` をWebブラウザで開きます。ファイル選択ボタンを押し、 `logs/games/` ディレクトリに保存されている対戦ログ（.jsonファイル）を選択します。再生コントロールを使って、対局を再生します。

2. 学習進捗のグラフ確認 (TensorBoard)  
学習の損失（loss）など、AIの長期的な学習トレンドをグラフで分析できます。

- 新しいターミナルを起動します（`main.py` を実行しているターミナルとは別に）。
- プロジェクトの仮想環境を有効化します。
```powershell
# プロジェクトルートへ移動
cd c:\Work\Reinforcement-LearningOfMahjong

# 仮想環境を有効化
.\.venv\Scripts\Activate.ps1
```

- 以下のコマンドでTensorBoardを起動します。
```powershell
tensorboard --logdir logs/tensorboard
```

- ターミナルに表示されたURL（通常は http://localhost:6006/）をWebブラウザで開きます。

---

## ディレクトリ構成（概要）
```
.
├── .gitignore
├── README.md
├── main.py
├── requirements.txt
├── mahjong_viewer.html    # <-- NEW: 対戦再生GUI
├── models/                # (任意) initial_model.keras を置く
├── logs/
│   ├── games/             # 対戦ログ(.json)が保存される
│   └── tensorboard/       # 学習グラフ用のデータが保存される
├── src/
│   ├── agent/             # モデル定義・思考エンジン
│   ├── constants.py
│   ├── env/               # ルールエンジン、状態遷移
│   │   └── deck.py        # 牌山管理クラス（自作）
│   ├── train/             # 強化学習ループ
│   └── utils/             # 共通ユーティリティ
└── tests/                 # テストコード
```

---

## ドキュメント
- [システム設計](./doc/architecture.md)
- [モデル入出力仕様](./doc/model_architecture.md)
- [コード構造説明](./doc/code_structure.md)
- [開発ロードマップ](./doc/development_plan.md)
- **[NEW]** [mahjongライブラリ利用ガイド](./doc/mahjong_library_usage.md)

---

## 備考
- Windows 環境での実行手順を想定しています。PowerShell を推奨します。  
- GPU を使う場合は tensorflow-directml-plugin の導入と設定を確認してください。

---

最終更新: 2025-10-11