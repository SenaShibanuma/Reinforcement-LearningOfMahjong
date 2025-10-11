import os
import numpy as np
import tensorflow as tf
from collections import deque
import random

from src.agent.model import build_masked_transformer
from src.utils.vectorizer import vectorize_event, vectorize_choice


class MahjongAgent:
    def __init__(self, agent_id, model_dir, base_model_name, config):
        """
        __init__ メソッドに agent_id パラメータを追加
        """
        self.agent_id = agent_id  # agent_id をインスタンス変数として保存
        self.config = config
        self.model_dir = model_dir
        self.base_model_name = base_model_name
        self.memory = deque(maxlen=2000)

        self.model = self._load_or_initialize_model()

    def _find_latest_model(self):
        """
        指定されたベース名を持つ最新のバージョン付きモデルファイルを見つける。
        """
        if not os.path.exists(self.model_dir):
            os.makedirs(self.model_dir)
            return None

        # バージョン番号付きのモデル（例: tenho_model_v50.keras）のみを対象とする
        model_files = [f for f in os.listdir(self.model_dir) if f.startswith(
            self.base_model_name) and f.endswith('.keras') and '_v' in f]
        if not model_files:
            return None

        # バージョン番号に基づいてファイルをソートし、最新のものを返す
        try:
            latest_file = max(model_files, key=lambda x: int(
                x.split('_v')[-1].split('.')[0]))
            return os.path.join(self.model_dir, latest_file)
        except (ValueError, IndexError):
            # 不正な形式のファイル名を無視する
            return None

    def _load_or_initialize_model(self):
        """
        事前学習済みモデルをロードする。ロードに失敗した場合は新しいモデルを初期化する。
        """
        print(
            f"Searching for model to load with base name '{self.base_model_name}' in '{self.model_dir}'...")

        path_to_load = None

        # 最初に最新のバージョン付きモデルを探す
        latest_versioned_path = self._find_latest_model()
        if latest_versioned_path:
            path_to_load = latest_versioned_path
        else:
            # バージョン付きモデルがなければ、ベースモデルを探す
            base_model_path = os.path.join(
                self.model_dir, f"{self.base_model_name}.keras")
            if os.path.exists(base_model_path):
                print(
                    f"No versioned model found. Using base model at '{base_model_path}'...")
                path_to_load = base_model_path

        # モデルの読み込みを試みる
        if path_to_load:
            try:
                print(f"Attempting to load model from: {path_to_load}")
                model = tf.keras.models.load_model(path_to_load)
                print("Model loaded successfully.")
                return model
            except Exception as e:
                print(
                    f"WARN: Failed to load model from '{path_to_load}'. Reason: {e}")

        # プライマリモデルの読み込みに失敗した場合、または見つからなかった場合にバックアップを試す
        backup_model_path = os.path.join(
            self.model_dir, f"{self.base_model_name}.keras.bk")
        if os.path.exists(backup_model_path):
            print(
                f"Attempting to load from backup: {backup_model_path}")
            try:
                model = tf.keras.models.load_model(backup_model_path)
                print("Backup model loaded successfully.")
                return model
            except Exception as backup_e:
                print(
                    f"WARN: Failed to load backup model as well. Reason: {backup_e}")

        # すべてのモデルの読み込みに失敗した場合、新しいモデルを初期化する
        print("WARN: Could not load any existing model. Initializing a new model.")
        # configから必要なパラメータを取得して渡す
        return build_masked_transformer(
            input_shape=self.config['model']['input_shape'],
            num_actions=self.config['model']['num_actions'],
            d_model=self.config['model']['d_model'],
            num_heads=self.config['model']['num_heads'],
            dff=self.config['model']['dff'],
            num_layers=self.config['model']['num_layers'],
            dropout_rate=self.config['model']['dropout_rate']
        )

    def choose_action(self, state, legal_actions):
        """
        現在の状態と有効なアクションに基づいてアクションを選択する。
        """
        # (仮実装) ランダムに行動を選択
        if not legal_actions:
            # 万が一有効なアクションがない場合のフォールバック
            return None
        return random.choice(legal_actions)

    def remember(self, state, action, reward, next_state, done):
        """
        エージェントの経験をメモリに追加する。
        """
        self.memory.append((state, action, reward, next_state, done))

    def replay(self):
        """
        メモリからの経験のバッチを使ってモデルを再学習する。
        """
        if len(self.memory) < self.config['training']['batch_size']:
            return

        minibatch = random.sample(
            self.memory, self.config['training']['batch_size'])
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                # ここにQ学習やポリシーグラディエントなどの学習ロジックが入る
                pass
            # (仮実装) 学習ロジックをここに追加
            # self.model.fit(...)

    def save_model(self, game_number):
        """
        現在のモデルをバージョン番号付きで保存する。
        """
        versioned_model_name = f"{self.base_model_name}_v{game_number}.keras"
        save_path = os.path.join(self.model_dir, versioned_model_name)
        self.model.save(save_path)
        print(f"Model for agent {self.agent_id} saved to {save_path}")

