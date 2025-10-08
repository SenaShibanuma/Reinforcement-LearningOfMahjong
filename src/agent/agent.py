# -*- coding: utf-8 -*-
"""
AIエージェントを定義するファイル。
モデルを読み込み、観測から行動を決定する責務を持つ。
"""
import numpy as np
import tensorflow as tf
from src.agent.model import build_masked_transformer
from src.utils.vectorizer import vectorize_event, vectorize_choice
from src.constants import MAX_CONTEXT_LENGTH, MAX_CHOICES

class MahjongAgent:
    def __init__(self, model_path=None):
        """
        エージェントを初期化し、学習済みモデルを読み込む。
        モデルパスが存在すればモデルをロードし、なければ新規作成する。
        """
        print("Initializing Mahjong Agent...")
        if model_path:
            try:
                print(f"Loading model from {model_path}...")
                self.model = tf.keras.models.load_model(model_path)
            except Exception as e:
                print(f"Error loading model: {e}. Building a new model instead.")
                self.model = build_masked_transformer()
        else:
            print("Warning: No model path provided. Building a new model.")
            self.model = build_masked_transformer()

        # モデルの学習用設定をコンパイル
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        self.loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    
    def choose_action(self, context_events, choice_strs, player_pov, is_training=False):
        """
        現在の観測情報(context, choices)から、実行すべき行動を選択する。
        
        Args:
            context_events (list): イベント辞書のリスト
            choice_strs (list): 選択肢文字列のリスト
            player_pov (int): 自身のプレイヤーID (0-3)
            is_training (bool): 学習モードか否か。Trueの場合、探索的な行動を取る。

        Returns:
            str: 選択された行動の文字列 (例: "DISCARD_24")
            dict: 各行動の選択確率
        """
        if not choice_strs:
            return None, {}

        # 1. Vectorize inputs
        context_vec = [vectorize_event(e, player_pov) for e in context_events]
        choice_vecs = [vectorize_choice(c) for c in choice_strs]

        # 2. Pad and create mask
        padded_context = tf.keras.preprocessing.sequence.pad_sequences(
            [context_vec], maxlen=MAX_CONTEXT_LENGTH, dtype='float32', padding='post'
        )
        padded_choices = tf.keras.preprocessing.sequence.pad_sequences(
            [choice_vecs], maxlen=MAX_CHOICES, dtype='float32', padding='post'
        )
        mask = np.zeros((1, MAX_CHOICES), dtype='float32')
        mask[0, :len(choice_strs)] = 1.0

        # 3. Predict
        model_inputs = [padded_context, padded_choices, mask]
        logits = self.model.predict(model_inputs, verbose=0)
        
        # 4. Convert logits to probabilities
        probabilities = tf.nn.softmax(logits[0][:len(choice_strs)]).numpy()
        
        # 5. Choose action
        if is_training:
            # 学習中は、確率分布に従ってランダムに行動を選択（探索）
            selected_action = np.random.choice(choice_strs, p=probabilities)
        else:
            # 本番（評価）では、最も確率の高い行動を選択（活用）
            best_action_index = np.argmax(probabilities)
            selected_action = choice_strs[best_action_index]
        
        action_probs = {choice: prob for choice, prob in zip(choice_strs, probabilities)}
        
        return selected_action, action_probs

    def learn(self, experiences):
        """
        与えられた経験データからモデルを学習する (REINFORCEアルゴリズムの簡易版)。
        
        Args:
            experiences (list): (observation, action_index, reward, player_pov) のタプルのリスト
        """
        if not experiences:
            print("No experiences to learn from.")
            return
            
        print(f"Agent is learning from {len(experiences)} experiences...")
        
        observations, action_indices, rewards, povs = zip(*experiences)
        
        # 観測データをモデルの入力形式に変換
        contexts = []
        choices_list = []
        masks = []

        for obs, pov in zip(observations, povs):
            context_events, choice_strs = obs
            context_vec = [vectorize_event(e, pov) for e in context_events]
            choice_vecs = [vectorize_choice(c) for c in choice_strs]
            
            padded_context = tf.keras.preprocessing.sequence.pad_sequences(
                [context_vec], maxlen=MAX_CONTEXT_LENGTH, dtype='float32', padding='post'
            )
            padded_choices = tf.keras.preprocessing.sequence.pad_sequences(
                [choice_vecs], maxlen=MAX_CHOICES, dtype='float32', padding='post'
            )
            mask = np.zeros((1, MAX_CHOICES), dtype='float32')
            mask[0, :len(choice_strs)] = 1.0
            
            contexts.append(padded_context[0])
            choices_list.append(padded_choices[0])
            masks.append(mask[0])

        with tf.GradientTape() as tape:
            logits = self.model([np.array(contexts), np.array(choices_list), np.array(masks)], training=True)
            loss = self.loss_fn(y_true=list(action_indices), y_pred=logits, sample_weight=list(rewards))
            
        grads = tape.gradient(loss, self.model.trainable_variables)
        self.optimizer.apply_gradients(zip(grads, self.model.trainable_variables))
        
        print(f"Learning finished. Loss: {loss.numpy()}")

