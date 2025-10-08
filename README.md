# Reinforcement-LearningOfMahjong

Transformerベースの麻雀AIをローカル環境で強化学習させることを目的としたプロジェクトです。自己対戦を通じてデータ収集・モデル更新を繰り返し、より高い雀力を持つエージェントを育成します。

---

## 目次
- 概要
- 動作環境
- セットアップ手順
- 実行方法
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

## ディレクトリ構成（概要）
```
.
├── .gitignore
├── README.md
├── main.py
├── requirements.txt
├── models/                # (任意) initial_model.keras を置く
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
- doc/architecture.md — システム設計  
- doc/model_architecture.md — モデル入出力仕様  
- doc/code_structure.md — コード構造説明  
- doc/development_plan.md — 開発ロードマップ

---

## 備考
- Windows 環境での実行手順を想定しています。PowerShell を推奨します。  
- GPU を使う場合は tensorflow-directml-plugin の導入と設定を確認してください。

---

最終更新: 2025-10-08