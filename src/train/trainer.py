# -*- coding: utf-8 -*-
"""
強化学習のサイクル（自己対戦、データ収集、モデル更新）を管理するトレーナークラス。
"""
import os
import re
import json
from datetime import datetime
import numpy as np
import tensorflow as tf
from src.agent.agent import MahjongAgent
from src.env.mahjong_env import MahjongEnv

class ExperienceBuffer:
    """経験（状態、行動、報酬など）を一時的に保存するバッファ。"""
    def __init__(self):
        self.buffer = []

    def add(self, experience):
        self.buffer.append(experience)

    def get_all(self):
        return self.buffer

    def clear(self):
        self.buffer = []

class Trainer:
    """強化学習のトレーナー"""
    def __init__(self, config):
        self.config = config
        self.rules = config.get('rules', {})
        
        model_config = self.config.get('model', {})
        model_name = model_config.get('model_name', 'model')
        model_dir = model_config.get('model_save_dir', 'models')

        # 1. まず最新バージョンのモデルを探す
        print(f"Searching for latest versioned model with base name '{model_name}' in '{model_dir}'...")
        model_path, latest_version = self._find_latest_model(model_dir, model_name)
        
        # 2. 見つからなければ、バージョン番号のないベースモデルを探す
        if not model_path:
            base_model_path = os.path.join(model_dir, f"{model_name}.keras")
            print(f"No versioned model found. Checking for base model at '{base_model_path}'...")
            if os.path.exists(base_model_path):
                print(f"Found base model: {base_model_path}")
                model_path = base_model_path
                latest_version = 0 # 次の保存はver1から

        self.latest_model_version = latest_version

        if model_path:
            print(f"Loading model from: {model_path}")
        else:
            print(f"No existing model found for '{model_name}'. A new model will be created.")

        self.agents = [MahjongAgent(model_path=model_path) for _ in range(4)]
        
        self.env = MahjongEnv(self.agents, rules=self.rules, config=self.config)
        
        self.buffers = [ExperienceBuffer() for _ in range(4)]

        # TensorBoardのセットアップ
        self.log_dir = self.config.get('logging', {}).get('tensorboard_log_dir', 'logs/tensorboard')
        self.summary_writer = tf.summary.create_file_writer(self.log_dir)

    def _find_latest_model(self, model_dir, model_name):
        """指定されたモデル名に一致する最新バージョンのモデルファイルを見つける。"""
        if not os.path.exists(model_dir):
            return None, 0
        
        model_pattern = re.compile(f"^{re.escape(model_name)}_ver(\\d+)\\.keras$")
        latest_version = -1
        latest_model_path = None
        
        for filename in os.listdir(model_dir):
            match = model_pattern.match(filename)
            if match:
                version = int(match.group(1))
                if version > latest_version:
                    latest_version = version
                    latest_model_path = os.path.join(model_dir, filename)
        
        return latest_model_path, latest_version if latest_version != -1 else 0

    def self_play(self):
        """1半荘の自己対戦を実行し、経験を収集する。"""
        game_over = False
        game_state = None
        
        while not game_over:
            current_observation = self.env.reset(initial_state=game_state)
            game_state = self.env.game_state
            round_done = False
            
            round_experiences = [[] for _ in range(4)]

            round_name = f"East {(game_state['round'] // 4) + 1}-{game_state['round'] % 4 + 1}" if game_state['round'] < 4 else f"South {( (game_state['round']-4) // 4) + 1}-{(game_state['round']-4) % 4 + 1}"
            print(f"\n======== Starting Round: {round_name}, Honba: {game_state['honba']}, Riichi Sticks: {game_state['riichi_sticks']} ========")
            print(f"Oya is Player {game_state['oya_player_id']}. Initial Scores: {game_state['scores']}")

            while not round_done:
                current_player_id = self.env.current_player_idx
                context, choices = current_observation
                
                if not choices:
                    print("Error: No choices available. Ending round as abortive draw.")
                    _, rewards, round_done, info = self.env._process_abortive_draw("no_choices")
                    break

                current_agent = self.agents[current_player_id]
                selected_action, _ = current_agent.choose_action(context, choices, current_player_id, is_training=True)
                
                if selected_action not in choices:
                    print(f"Error: Agent selected an invalid action '{selected_action}'. Defaulting to first choice.")
                    selected_action = choices[0]
                
                action_index = choices.index(selected_action)

                next_observation, rewards, round_done, info = self.env.step(selected_action)
                
                experience = (current_observation, action_index, 0, current_player_id) 
                round_experiences[current_player_id].append(experience)

                current_observation = next_observation

            for player_id in range(4):
                final_reward = rewards[player_id]
                for obs, act_idx, _, pov in round_experiences[player_id]:
                    normalized_reward = final_reward / 1000.0
                    self.buffers[player_id].add((obs, act_idx, normalized_reward, pov))

            game_state = self.env.game_state
            print(f"======== Round Ended. Reason: {info.get('reason')} ========")
            
            if info.get('game_over', False):
                game_over = True
        
        print("\n--- Game Over ---")
        
        if game_state.get('riichi_sticks', 0) > 0:
            riichi_bonus = game_state['riichi_sticks'] * 1000
            scores = game_state['scores']
            top_player_score = max(scores)
            top_players = [i for i, score in enumerate(scores) if score == top_player_score]
            top_player_idx = top_players[0]
            print(f"  -> {riichi_bonus} points from leftover riichi sticks are awarded to the top player (Player {top_player_idx}).")
            game_state['scores'][top_player_idx] += riichi_bonus
            game_state['riichi_sticks'] = 0

        print(f"Final Scores: {game_state['scores']}")
        return game_state


    def train(self):
        """設定されたゲーム数だけ自己対戦と学習のサイクルを回す。"""
        num_games = self.config.get('training', {}).get('num_games', 1)
        
        for i in range(1, num_games + 1):
            print(f"\n\n<<<<<<<<<< Starting Game {i}/{num_games} >>>>>>>>>>")
            
            for buffer in self.buffers:
                buffer.clear()
            
            final_game_state = self.self_play()
            
            print("\n-------- Updating Models --------")
            main_agent = self.agents[0]
            all_experiences = []
            for buffer in self.buffers:
                all_experiences.extend(buffer.get_all())
            
            avg_loss = 0.0
            if all_experiences:
                batch_size = self.config.get('training', {}).get('batch_size', 64)
                avg_loss = main_agent.learn(all_experiences, batch_size=batch_size)
            
            # TensorBoardに記録
            with self.summary_writer.as_default():
                tf.summary.scalar('loss', avg_loss, step=self.latest_model_version + i)
                
                scores = np.array(final_game_state['scores'])
                score_std_dev = np.std(scores)
                tf.summary.scalar('score_standard_deviation', score_std_dev, step=self.latest_model_version + i)

            print("Synchronizing weights to all agents...")
            weights = main_agent.model.get_weights()
            for agent in self.agents[1:]:
                agent.model.set_weights(weights)

            self.save_log(final_game_state, i)
            self.save_model(i)
            self.save_stats(final_game_state, i)

    def save_log(self, game_state, game_num):
        """現在のゲームのイベント履歴をJSONファイルとして保存する。"""
        log_config = self.config.get('logging', {})
        if not log_config.get('save_game_logs', False):
            return

        try:
            log_dir = log_config.get('game_log_dir', 'logs/games')
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(log_dir, f"game_{self.latest_model_version + game_num}_{timestamp}.json")
            
            loggable_events = []
            for event in game_state.get('events', []):
                loggable_event = {}
                for key, value in event.items():
                    if isinstance(value, (dict, list, str, int, float, bool, type(None), np.number)):
                        loggable_event[key] = value
                loggable_events.append(loggable_event)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(loggable_events, f, indent=2, ensure_ascii=False, default=lambda o: '<not serializable>')
            
            print(f"======== Game log saved to {filename} ========")

        except Exception as e:
            print(f"Error saving game log file: {e}")
            
    def save_model(self, game_num):
        """現在のモデルを保存する。"""
        model_config = self.config.get('model', {})
        if not model_config.get('save_models', False):
            return
            
        if game_num % model_config.get('save_interval_games', 1) == 0:
            try:
                model_dir = model_config.get('model_save_dir', 'models')
                model_name = model_config.get('model_name', 'model')
                os.makedirs(model_dir, exist_ok=True)
                
                new_version = self.latest_model_version + game_num
                
                model_path = os.path.join(model_dir, f"{model_name}_ver{new_version}.keras")
                self.agents[0].model.save(model_path)
                print(f"======== Model saved to {model_path} ========")
            except Exception as e:
                print(f"Error saving model: {e}")

    def save_stats(self, game_state, game_num):
        """アガリ統計情報をファイルに追記する。"""
        log_config = self.config.get('logging', {})
        if not log_config.get('save_stats', False):
            return
            
        stats_file = log_config.get('stats_file', 'logs/game_stats.jsonl')
        
        try:
            os.makedirs(os.path.dirname(stats_file), exist_ok=True)
            with open(stats_file, 'a', encoding='utf-8') as f:
                for stat in game_state.get('agari_stats', []):
                    stat_with_game_num = {'game': self.latest_model_version + game_num, **stat}
                    f.write(json.dumps(stat_with_game_num, ensure_ascii=False) + '\n')
            
            if game_state.get('agari_stats'):
                 print(f"======== Agari stats saved to {stats_file} ========")
        except Exception as e:
            print(f"Error saving stats file: {e}")

