# 開発環境構築ガイド (Windows x64 / Python 3.10)

本プロジェクトのAIモデルの学習・実行を Surface Pro 11 上で行うための最終的な手順です。  
tensorflow-directml-plugin が Python 3.11 に未対応のため、互換性のある Python 3.10（x64）環境を構築します。

---

## 前提
- OS: Windows
- プロジェクトフォルダ: `C:\Work\Reinforcement-LearningOfMahjong`
- Python 3.10（64-bit）を使用
- PowerShell を管理者権限で開くことを推奨

---

## ステップ1: 既存 Python 環境のクリーンアップ

1. Windows 設定 → アプリ → インストールされているアプリ を開き、`Python 3.11` と名の付くものをすべてアンインストールします。  
2. PowerShell を開き、プロジェクトフォルダへ移動して古い仮想環境を削除します。

```powershell
cd C:\Work\Reinforcement-LearningOfMahjong
Remove-Item .\.venv -Recurse -Force
```

---

## ステップ2: x64版 Python 3.10 のインストール

1. ブラウザで Python 公式ダウンロードページへアクセス:  
   https://www.python.org/downloads/windows/
2. 「Python 3.10.x」セクションから **Windows installer (64-bit)** をダウンロード。
3. ダウンロードしたインストーラーを実行し、最初の画面で必ず **Add python.exe to PATH** にチェックを入れてから「Install Now」を選択。
4. インストール後、PC を再起動して確認。

```powershell
python --version
# -> Python 3.10.x と表示されれば OK
```

---

## ステップ3: プロジェクトのセットアップとライブラリインストール

1. プロジェクトフォルダへ移動し仮想環境を作成・有効化。

```powershell
cd C:\Work\Reinforcement-LearningOfMahjong
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. requirements.txt を以下の最終構成に書き換えて保存してください。

```text
# AIライブラリ (Python 3.10 と互換性のあるバージョン)
tensorflow-cpu==2.10
tensorflow-directml-plugin

# 麻雀のルールエンジン
mahjong
```

3. pip を更新して依存関係をインストール。

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## ステップ4: プログラムの実行

1. PowerShell でプロジェクトフォルダへ移動し、仮想環境を有効化。

```powershell
cd C:\Work\Reinforcement-LearningOfMahjong
.\.venv\Scripts\Activate.ps1
```

2. メインスクリプトを実行。

```powershell
python main.py
```

実行後、`main.py` に記述されたデバイスチェックが TensorFlow の CPU / GPU(DML) を検出できるか表示します。GPU が正しく認識されていれば環境構築は完了です。

---