# -*- coding: utf-8 -*-
"""
AIエージェントを定義するファイル。
モデルを読み込み、観測から行動を決定する責務を持つ。
"""
import os
import numpy as np
import tensorflow as tf
from src.agent.model import build_masked_transformer
from src.utils.vectorizer import vectorize_event, vectorize_choice
from src.constants import MAX_CONTEXT_LENGTH, MAX_CHOICES

class MahjongAgent:
    def __init__(self, model_path=None):
        """
        エージェントを初期化し、モデルの骨格を構築する。
        モデルパスが指定されていれば、学習済みの重みを読み込む。
        """
        print("Initializing Mahjong Agent...")
        # まず、モデルの骨格（アーキテクチャ）を常にコードから構築する
        self.model = build_masked_transformer()

        if model_path and os.path.exists(model_path):
            print(f"Found model file at: {model_path}")
            try:
                # モデル全体ではなく、学習済みの「重み」のみを読み込む
                self.model.load_weights(model_path)
                print("Successfully loaded model weights.")
            except Exception as e:
                # 読み込み失敗のメッセージをより明確にする
                print(f"Warning: Could not load weights from '{model_path}'.")
                print(f"Reason: {e}")
                print("The agent will start with a new, untrained model.")
        else:
            if model_path:
                print(f"Warning: Model file not found at '{model_path}'.")
            else:
                print("Warning: No model path provided.")
            print("The agent will start with a new, untrained model.")

        # モデルの学習用設定をコンパイル
        self.optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
        self.loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
    
    def choose_action(self, context_events, choice_strs, player_pov, is_training=False):
        """
        現在の観測情報(context, choices)から、実行すべき行動を選択する。
        """
        if not choice_strs:
            return None, {}

        context_vec = [vectorize_event(e, player_pov) for e in context_events]
        choice_vecs = [vectorize_choice(c) for c in choice_strs]

        padded_context = tf.keras.preprocessing.sequence.pad_sequences(
            [context_vec], maxlen=MAX_CONTEXT_LENGTH, dtype='float32', padding='post'
        )
        padded_choices = tf.keras.preprocessing.sequence.pad_sequences(
            [choice_vecs], maxlen=MAX_CHOICES, dtype='float32', padding='post'
        )
        mask = np.zeros((1, MAX_CHOICES), dtype='float32')
        mask[0, :len(choice_strs)] = 1.0

        model_inputs = [padded_context, padded_choices, mask]
        
        logits = self.model(model_inputs, training=False)
        
        masked_logits = logits[0, :len(choice_strs)]
        
        masked_logits = tf.clip_by_value(masked_logits, -1e9, 1e9)
        
        probabilities = tf.nn.softmax(masked_logits).numpy()
        
        probabilities /= np.sum(probabilities)

        if is_training:
            selected_idx = np.random.choice(len(choice_strs), p=probabilities)
            selected_action = choice_strs[selected_idx]
        else:
            best_action_index = np.argmax(probabilities)
            selected_action = choice_strs[best_action_index]
        
        action_probs = {choice: prob for choice, prob in zip(choice_strs, probabilities)}
        
        return selected_action, action_probs

    def learn(self, experiences, batch_size=64):
        """
        与えられた経験データからバッチ学習を行う。
        """
        if not experiences:
            print("No experiences to learn from.")
            return 0.0
            
        print(f"Agent is learning from {len(experiences)} experiences...")
        
        total_loss = 0.0
        num_batches = 0
        
        np.random.shuffle(experiences)

        for i in range(0, len(experiences), batch_size):
            batch = experiences[i:i+batch_size]
            observations, action_indices, rewards, povs = zip(*batch)
            
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
            
            total_loss += loss.numpy()
            num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        print(f"Learning finished. Average Loss: {avg_loss:.4f}")
        return avg_loss

