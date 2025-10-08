# -*- coding: utf-8 -*-
"""
強化学習のサイクル（自己対戦、データ収集、モデル更新）を管理するトレーナークラス。
"""
import os
import json
from datetime import datetime
from src.agent.agent import MahjongAgent
from src.env.mahjong_env import MahjongEnv

LOG_INTERVAL = 1
LOG_DIR = "logs"

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
    def __init__(self, rules=None):
        self.rules = rules or {'has_aka_dora': True, 'has_open_tanyao': True}
        
        model_path = 'models/initial_model.keras'
        if not os.path.exists(model_path):
            print(f"Warning: Model file not found at '{model_path}'. Agents will use random weights.")
            model_path = None

        self.agents = [MahjongAgent(model_path=model_path) for _ in range(4)]
        self.env = MahjongEnv(self.agents, rules=self.rules)
        self.buffers = [ExperienceBuffer() for _ in range(4)]

    def self_play(self):
        """1半荘（東風戦）の自己対戦を実行し、経験を収集する。"""
        game_over = False
        game_state = None
        round_count = 0

        while not game_over:
            current_observation = self.env.reset(initial_state=game_state)
            game_state = self.env.game_state
            round_count += 1
            round_done = False
            
            round_experiences = [[] for _ in range(4)]

            print(f"\n======== Starting Round: East {game_state['round'] + 1}, Honba: {game_state['honba']}, Riichi Sticks: {game_state['riichi_sticks']} ========")
            print(f"Oya is Player {game_state['oya_player_id']}. Initial Scores: {game_state['scores']}")

            while not round_done:
                current_player_id = self.env.current_player_idx
                context, choices = current_observation
                
                if not choices:
                    print("Error: No choices available. Ending game.")
                    game_over = True
                    break

                current_agent = self.agents[current_player_id]
                selected_action, _ = current_agent.choose_action(context, choices, current_player_id, is_training=True)
                action_index = choices.index(selected_action)

                next_observation, rewards, round_done, info = self.env.step(selected_action)
                
                experience = (current_observation, action_index, 0, current_player_id) 
                round_experiences[current_player_id].append(experience)

                current_observation = next_observation

                if info.get('game_over', False):
                    game_over = True
            
            for player_id in range(4):
                final_reward = rewards[player_id]
                for obs, act_idx, _, pov in round_experiences[player_id]:
                    normalized_reward = final_reward / 1000.0
                    self.buffers[player_id].add((obs, act_idx, normalized_reward, pov))

            game_state = self.env.game_state
            print(f"======== Round Ended. Reason: {info.get('reason')} ========")

            if round_count % LOG_INTERVAL == 0:
                self.save_log(game_state)

        print("\n--- Game Over ---")
        
        # ゲーム終了時に供託リーチ棒が残っている場合の処理
        if game_state.get('riichi_sticks', 0) > 0:
            riichi_bonus = game_state['riichi_sticks'] * 1000
            scores = game_state['scores']
            top_player_score = max(scores)
            top_players = [i for i, score in enumerate(scores) if score == top_player_score]
            
            # Note: 同着トップの場合は上家取りが一般的だが、ここでは簡略化のためプレイヤーIDの若い人に加算
            top_player_idx = top_players[0]

            print(f"  -> {riichi_bonus} points from leftover riichi sticks are awarded to the top player (Player {top_player_idx}).")
            game_state['scores'][top_player_idx] += riichi_bonus
            game_state['riichi_sticks'] = 0

        print(f"Final Scores: {game_state['scores']}")

    def train(self, num_games=1):
        """指定されたゲーム数だけ自己対戦と学習のサイクルを回す。"""
        for i in range(num_games):
            print(f"\n\n<<<<<<<<<< Starting Game {i+1}/{num_games} >>>>>>>>>>")
            
            for buffer in self.buffers:
                buffer.clear()
            
            self.self_play()
            
            print("\n-------- Updating Models --------")
            main_agent = self.agents[0]
            all_experiences = []
            for buffer in self.buffers:
                all_experiences.extend(buffer.get_all())
            
            if all_experiences:
                main_agent.learn(all_experiences)
            
            print("Synchronizing weights to all agents...")
            weights = main_agent.model.get_weights()
            for agent in self.agents[1:]:
                agent.model.set_weights(weights)

    def save_log(self, game_state):
        """現在の局のイベント履歴をJSONファイルとして保存する。"""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            round_num = game_state.get('round', 0)
            honba = game_state.get('honba', 0)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(LOG_DIR, f"round_E{round_num+1}-{honba}_{timestamp}.json")
            
            loggable_events = []
            for event in game_state.get('events', []):
                loggable_event = {}
                for key, value in event.items():
                    if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                        loggable_event[key] = value
                loggable_events.append(loggable_event)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(loggable_events, f, indent=2, ensure_ascii=False)
            
            print(f"======== Log saved to {filename} ========")

        except Exception as e:
            print(f"Error saving log file: {e}")

