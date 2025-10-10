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
from mahjong.shanten import Shanten
from mahjong.tile import TilesConverter
from mahjong.meld import Meld

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

        # 起動時にロードするモデルパスのみを決定する
        print(f"Searching for latest model to load with base name '{model_name}' in '{model_dir}'...")
        model_path, _ = self._find_latest_model(model_dir, model_name)
        
        if not model_path:
            base_model_path = os.path.join(model_dir, f"{model_name}.keras")
            print(f"No versioned model found. Checking for base model at '{base_model_path}'...")
            if os.path.exists(base_model_path):
                print(f"Found base model: {base_model_path}")
                model_path = base_model_path

        if model_path:
            print(f"Loading model from: {model_path}")
        else:
            print(f"No existing model found for '{model_name}'. A new model will be created.")

        self.agents = [MahjongAgent(model_path=model_path) for _ in range(4)]
        
        self.env = MahjongEnv(self.agents, rules=self.rules, config=self.config)
        
        self.buffers = [ExperienceBuffer() for _ in range(4)]

        self.shanten_calculator = Shanten()

        # TensorBoardのセットアップ
        self.log_dir = self.config.get('logging', {}).get('tensorboard_log_dir', 'logs/tensorboard')
        self.summary_writer = tf.summary.create_file_writer(self.log_dir)

    def _calculate_shanten(self, hand_136, melds_136):
        """与えられた手牌と副露からシャンテン数を計算するヘルパー関数"""
        try:
            hand_34 = TilesConverter.to_34_array(hand_136)
            
            pon_sets_34 = []
            chi_sets_34 = []

            for meld in melds_136:
                meld_type = meld.type
                meld_tiles_34 = [t // 4 for t in meld.tiles]
                
                if meld_type == Meld.PON:
                    pon_sets_34.append(meld_tiles_34)
                elif meld_type == Meld.CHI:
                    chi_sets_34.append(meld_tiles_34)
                # KAN (ankan, daiminkan, kakan) はポンとして扱ってもシャンテン数計算は可能
                elif meld_type == Meld.KAN:
                    pon_sets_34.append(meld_tiles_34[:3])

            return self.shanten_calculator.calculate_shanten(
                hand_34,
                chi_sets_34=chi_sets_34,
                pon_sets_34=pon_sets_34
            )
        except Exception:
            return 8

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
        
        # バージョン付きモデルが見つからなかった場合、バージョンを0として扱う
        if latest_version == -1:
             latest_version = 0

        return latest_model_path, latest_version

    def self_play(self):
        """1半荘の自己対戦を実行し、経験を収集する。"""
        game_over = False
        game_state = None
        
        while not game_over:
            current_observation = self.env.reset(initial_state=game_state)
            game_state = self.env.game_state
            round_done = False
            
            round_experiences = [[] for _ in range(4)]

            # --- START: MODIFICATION ---
            # ログ表示を分かりやすく修正
            round_num_in_wind = (game_state['round'] % 4) + 1
            wind_num = game_state['round'] // 4
            winds = ["East", "South", "West", "North"]
            round_wind = winds[wind_num]
            round_name = f"{round_wind} {round_num_in_wind}"
            
            print(f"\n======== Starting Round: {round_name}, Honba: {game_state['honba']}, Riichi Sticks: {game_state['riichi_sticks']} ========")
            # --- END: MODIFICATION ---
            print(f"Oya is Player {game_state['oya_player_id']}. Initial Scores: {game_state['scores']}")

            while not round_done:
                current_player_id = self.env.current_player_idx
                context, choices = current_observation
                
                if not choices:
                    print("Error: No choices available. Ending round as abortive draw.")
                    _, rewards, round_done, info = self.env._process_abortive_draw("no_choices")
                    break

                # 行動前のシャンテン数を計算
                hand_before = self.env.game_state['hands'][current_player_id]
                melds_before = self.env.game_state['melds'][current_player_id]
                shanten_before = self._calculate_shanten(hand_before, melds_before)

                current_agent = self.agents[current_player_id]
                selected_action, _ = current_agent.choose_action(context, choices, current_player_id, is_training=True)

                turn = self.env.game_state.get('turn_count', 0)
                if self.env.game_phase == 'DISCARD':
                    print(f" -> Turn {turn}: Player {current_player_id} draws and considers...")
                print(f"    Action: Player {current_player_id} chooses {selected_action}")
                
                if selected_action not in choices:
                    print(f"Error: Agent selected an invalid action '{selected_action}'. Defaulting to first choice.")
                    selected_action = choices[0]
                
                action_index = choices.index(selected_action)

                next_observation, rewards, round_done, info = self.env.step(selected_action)
                
                # 行動後のシャンテン数を計算
                hand_after = self.env.game_state['hands'][current_player_id]
                melds_after = self.env.game_state['melds'][current_player_id]
                shanten_after = self._calculate_shanten(hand_after, melds_after)

                # 中間報酬を計算
                intermediate_reward = 0.0
                if shanten_after < shanten_before:
                    intermediate_reward += 0.1
                elif shanten_after > shanten_before:
                    intermediate_reward -= 0.1

                if shanten_after == 0 and shanten_before > 0:
                    intermediate_reward += 0.5

                # アガリに対する追加ボーナス
                if selected_action in ["ACTION_TSUMO", "ACTION_RON"]:
                    intermediate_reward += 1.0

                experience = (current_observation, action_index, intermediate_reward, current_player_id) 
                round_experiences[current_player_id].append(experience)

                current_observation = next_observation

            for player_id in range(4):
                final_reward = rewards[player_id]
                for obs, act_idx, intermediate_reward, pov in round_experiences[player_id]:
                    total_reward = intermediate_reward + (final_reward / 1000.0)
                    self.buffers[player_id].add((obs, act_idx, total_reward, pov))

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
            
            # --- 自己対戦 ---
            final_game_state = self.self_play()
            
            # --- 順位点計算 ---
            final_scores = final_game_state['scores']
            ranking_rewards = np.zeros(4)
            is_all_draw_game = len(final_game_state.get('agari_stats', [])) == 0
            
            print("\n--- Final Ranks & Ranking Rewards ---")
            
            if is_all_draw_game:
                print("No agari in this game. Ranking points will be scaled down.")

            if len(set(final_scores)) == 1:
                print("All players have the same score. No ranking points will be awarded.")
            else:
                player_ranks = sorted(range(len(final_scores)), key=lambda k: final_scores[k], reverse=True)
                ranking_points = self.config.get('rewards', {}).get('ranking_points', [15, 5, -5, -15])
                
                if is_all_draw_game:
                    penalty_factor = self.config.get('rewards', {}).get('all_draw_ranking_penalty_factor', 0.5)
                    ranking_points = [p * penalty_factor for p in ranking_points]
                
                for rank, player_idx in enumerate(player_ranks):
                    ranking_rewards[player_idx] = ranking_points[rank]
                    print(f"Rank {rank+1}: Player {player_idx} (Score: {final_scores[player_idx]}) -> Reward: {ranking_rewards[player_idx]}")
            
            print("------------------------------------")

            # --- 経験データに順位点を加算 ---
            all_experiences = []
            for player_id in range(4):
                player_buffer = self.buffers[player_id].get_all()
                for obs, act_idx, reward, pov in player_buffer:
                    total_reward = reward + (ranking_rewards[player_id] / 10.0)
                    all_experiences.append((obs, act_idx, total_reward, pov))

            # --- モデル更新 ---
            print("\n-------- Updating Models --------")
            main_agent = self.agents[0]
            
            avg_loss = 0.0
            if all_experiences:
                batch_size = self.config.get('training', {}).get('batch_size', 64)
                avg_loss = main_agent.learn(all_experiences, batch_size=batch_size)
            
            # --- モデルの同期と保存 ---
            print("Synchronizing weights to all agents...")
            weights = main_agent.model.get_weights()
            for agent in self.agents[1:]:
                agent.model.set_weights(weights)

            # モデルを保存し、保存された場合はそのバージョン番号を取得
            saved_version = self.save_model(i) # ループカウンタ `i` を渡す
            
            # モデルが保存された場合のみ、ログと統計も同じバージョン番号で保存
            if saved_version is not None:
                self.save_log(final_game_state, saved_version)
                self.save_stats(final_game_state, saved_version)
                
                # TensorBoardへの記録も保存された時だけ行う
                with self.summary_writer.as_default():
                    tf.summary.scalar('loss', avg_loss, step=saved_version)
                    scores = np.array(final_game_state['scores'])
                    score_std_dev = np.std(scores)
                    tf.summary.scalar('score_standard_deviation', score_std_dev, step=saved_version)

    def save_log(self, game_state, game_version):
        log_config = self.config.get('logging', {})
        if not log_config.get('save_game_logs', False):
            return

        try:
            log_dir = log_config.get('game_log_dir', 'logs/games')
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(log_dir, f"game_ver{game_version}_{timestamp}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_state, f, indent=2, ensure_ascii=False, default=lambda o: '<not serializable>')
            
            print(f"======== Game log saved to {filename} ========")

        except Exception as e:
            print(f"Error saving game log file: {e}")
            
    def save_model(self, loop_counter):
        """
        現在のモデルを保存する。保存した場合、新しいバージョン番号を返す。
        保存しなかった場合、Noneを返す。
        """
        model_config = self.config.get('model', {})
        if not model_config.get('save_models', False):
            return None
        
        # configで指定された間隔で保存するかどうかをチェック
        if loop_counter % model_config.get('save_interval_games', 1) == 0:
            try:
                model_dir = model_config.get('model_save_dir', 'models')
                model_name = model_config.get('model_name', 'model')
                os.makedirs(model_dir, exist_ok=True)
                
                # 保存する直前に、ディレクトリ内の最新バージョンを動的に取得
                _, latest_version = self._find_latest_model(model_dir, model_name)
                new_version = latest_version + 1
                
                model_path = os.path.join(model_dir, f"{model_name}_ver{new_version}.keras")
                self.agents[0].model.save(model_path)
                print(f"======== Model saved to {model_path} ========")
                return new_version # 保存したバージョン番号を返す
            except Exception as e:
                print(f"Error saving model: {e}")
                return None
        
        return None # 保存間隔外なのでNoneを返す

    def save_stats(self, game_state, game_version):
        log_config = self.config.get('logging', {})
        if not log_config.get('save_stats', False):
            return
            
        stats_file = log_config.get('stats_file', 'logs/game_stats.jsonl')
        
        try:
            os.makedirs(os.path.dirname(stats_file), exist_ok=True)
            with open(stats_file, 'a', encoding='utf-8') as f:
                for stat in game_state.get('agari_stats', []):
                    stat_with_game_num = {'game': game_version, **stat}
                    f.write(json.dumps(stat_with_game_num, ensure_ascii=False) + '\n')
            
            if game_state.get('agari_stats'):
                 print(f"======== Agari stats saved to {stats_file} ========")
        except Exception as e:
            print(f"Error saving stats file: {e}")

