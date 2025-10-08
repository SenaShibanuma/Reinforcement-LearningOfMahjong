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
        """
        print("Initializing Mahjong Agent...")
        self.model = build_masked_transformer()
        if model_path:
            print(f"Loading weights from {model_path}...")
            self.model.load_weights(model_path)
        else:
            print("Warning: No model path provided. Agent is using initial weights.")
    
    def choose_action(self, context_events, choice_strs, player_pov):
        """
        現在の観測情報(context, choices)から、実行すべき行動を選択する。
        
        Args:
            context_events (list): イベント辞書のリスト
            choice_strs (list): 選択肢文字列のリスト
            player_pov (int): 自身のプレイヤーID (0-3)

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
        
        # 5. Choose action (e.g., greedy)
        best_action_index = np.argmax(probabilities)
        selected_action = choice_strs[best_action_index]
        
        action_probs = {choice: prob for choice, prob in zip(choice_strs, probabilities)}
        
        return selected_action, action_probs
