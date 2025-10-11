import os
import json
import numpy as np
import tensorflow as tf
from tqdm import tqdm

from src.agent.agent import MahjongAgent
from src.env.mahjong_env import MahjongEnv
from src.utils.vectorizer import MahjongVectorizer


class Trainer:
    """
    強化学習のトレーニングプロセスを管理するクラス。
    """

    def __init__(self, config):
        """
        Trainerのコンストラクタ。

        Args:
            config (dict): config.jsonから読み込まれた設定情報。
        """
        print("\n--- Initializing Reinforcement Learning Trainer ---")
        self.config = config
        self.num_agents = self.config['num_agents']
        self.rules = self.config.get('rules', {})

        print(f"Initializing {self.num_agents} agents...")
        self.agents = [
            self._initialize_agent(i)
            for i in range(self.num_agents)
        ]

        self.env = MahjongEnv(
            agents=self.agents,
            config=self.config
        )
        self.vectorizer = MahjongVectorizer()

    def _initialize_agent(self, agent_id):
        """
        指定されたIDのエージェントを初期化する。

        Args:
            agent_id (int): エージェントのID。

        Returns:
            MahjongAgent: 初期化された麻雀エージェント。
        """
        print(f"Initializing Mahjong Agent {agent_id}...")
        # config.jsonの階層構造に合わせて修正
        return MahjongAgent(
            agent_id=agent_id,
            model_dir=self.config['model']['model_save_dir'],
            base_model_name=self.config['model']['model_name'],
            config=self.config
        )

    def train(self):
        """
        強化学習のメインループを実行する。
        """
        print("\n--- Starting Training Loop ---")
        # config.jsonの階層構造に合わせて修正
        total_games = self.config['training']['num_games']
        save_interval = self.config['model']['save_interval_games']

        for episode in tqdm(range(total_games), desc="Training Progress"):
            state = self.env.reset()
            done = False
            game_reward = 0

            while not done:
                current_player_id = self.env.get_current_player_id()
                agent = self.agents[current_player_id]

                # 状態をベクトル化
                state_vec = self.vectorizer.vectorize_state(state)

                # 有効なアクションを取得
                legal_actions = self.env.get_legal_actions()

                # エージェントに行動を選択させる
                action = agent.choose_action(state_vec, legal_actions)

                # 環境を1ステップ進める
                next_state, reward, done, info = self.env.step(action)

                # 次の状態をベクトル化
                next_state_vec = self.vectorizer.vectorize_state(next_state)

                # エージェントに経験を記憶させる
                agent.remember(state_vec, action, reward, next_state_vec, done)

                state = next_state
                game_reward += reward

                # 定期的にエージェントのモデルを更新（学習）
                agent.replay()

            print(
                f"Episode {episode + 1}/{total_games}, "
                f"Total Reward: {game_reward}"
            )

            # 定期的にモデルを保存
            if self.config['model']['save_models'] and (episode + 1) % save_interval == 0:
                print(f"--- Saving models at episode {episode + 1} ---")
                for agent in self.agents:
                    # バージョン番号をエピソード数からゲーム数に変更
                    agent.save_model(episode + 1)

        print("\n--- Training finished ---")

