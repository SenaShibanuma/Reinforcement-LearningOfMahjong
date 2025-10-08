# -*- coding: utf-8 -*-
"""
プロジェクトのメインエントリーポイント。
トレーナーを初期化し、強化学習のサイクルを開始する。
"""
import tensorflow as tf
from src.train.trainer import Trainer

def check_gpu_availability():
    """
    TensorFlowが利用可能な物理デバイス（CPU, GPU）をリストアップする。
    """
    print("\n--- Checking for available devices ---")
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        for gpu in gpus:
            print(f"Found GPU: {gpu}")
        try:
            tf.config.experimental.set_memory_growth(gpus[0], True)
            print(" -> Set memory growth to True for the first GPU.")
        except RuntimeError as e:
            print(e)
    else:
        print("No GPU found. TensorFlow will run on CPU.")
    
    cpus = tf.config.list_physical_devices('CPU')
    for cpu in cpus:
        print(f"Found CPU: {cpu}")
    print("--------------------------------------\n")


def main():
    """
    強化学習のメインプロセス
    """
    check_gpu_availability()

    print("--- Initializing Reinforcement Learning Trainer ---")
    
    # トレーナーを初期化
    trainer = Trainer()
    
    # 学習サイクルを開始（例として1ゲーム実行）
    trainer.train(num_games=1)
    
    print("\n--- Training process finished ---")


if __name__ == '__main__':
    main()

