# -*- coding: utf-8 -*-
"""
プロジェクトのメインエントリーポイント。
麻雀環境とAIエージェントを初期化し、自己対戦のシミュレーションを実行する。
"""
from src.agent.agent import MahjongAgent
from src.env.mahjong_env import MahjongEnv
import os
import tensorflow as tf

def check_gpu_availability():
    """
    TensorFlowが利用可能な物理デバイス（CPU, GPU）をリストアップする。
    """
    print("\n--- Checking for available devices ---")
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            print(f"Found GPU: {gpu}")
        # 追加の詳細設定
        try:
            tf.config.experimental.set_memory_growth(gpus[0], True)
            print(" -> Set memory growth to True for the first GPU.")
        except RuntimeError as e:
            # メモリ成長はプログラムの開始時に設定する必要がある
            print(e)
    else:
        print("No GPU found. TensorFlow will run on CPU.")
    
    cpus = tf.config.list_physical_devices('CPU')
    for cpu in cpus:
        print(f"Found CPU: {cpu}")
    print("--------------------------------------\n")


def main():
    """
    シミュレーションのメインループ
    """
    # 最初にデバイスの確認を行う
    check_gpu_availability()

    print("--- Starting Mahjong AI Self-Play Simulation ---")

    # 1. AIエージェントを4人分初期化する
    #    - 学習済みモデルは 'models/' ディレクトリに配置することを推奨します。
    #    - ここで指定したパスにモデルが存在しない場合、Agentは警告を出力します。
    model_path = 'models/initial_model.keras'
    
    # model_pathが存在しない場合、Noneに設定してランダム重みで動作させる
    if not os.path.exists(model_path):
        print(f"Warning: Model file not found at '{model_path}'. Agent will use random weights.")
        model_path = None

    agents = [MahjongAgent(model_path=model_path) for i in range(4)]
    print(f"Initialized 4 agents. Using model: {model_path or 'Random Weights'}")

    # 2. 麻雀環境を初期化し、エージェントを渡す
    env = MahjongEnv(agents)
    print("Mahjong environment created.")

    # 3. 環境をリセットして、最初の観測を取得する
    #    - `reset`メソッドは、(context_events, choice_strs) のタプルを返す想定
    current_observation = env.reset()
    
    # 現在のプレイヤーID
    current_player_id = env.current_player_idx
    done = False
    turn_count = 0

    print("\n--- Starting Game Loop ---")
    while not done:
        turn_count += 1
        print(f"\n--- Turn {turn_count} | Player {current_player_id} ---")

        # 4. 現在のプレイヤーに対応するエージェントを選択
        current_agent = agents[current_player_id]

        # 5. エージェントに行動を選択させる
        context, choices = current_observation
        
        if not choices:
            print("No choices available for the player. Skipping turn.")
            break

        print(f"Available choices: {choices}")
        selected_action, action_probs = current_agent.choose_action(context, choices, current_player_id)
        print(f"Agent chose action: {selected_action} with probabilities: {action_probs}")

        # 6. 選択された行動を環境に渡して、1ステップ進める
        next_observation, reward, done, info = env.step(selected_action)

        # 7. 次のプレイヤーのために観測とプレイヤーIDを更新
        current_observation = next_observation
        current_player_id = env.current_player_idx

    print("\n--- Game Over ---")

if __name__ == '__main__':
    main()

