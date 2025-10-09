# -*- coding: utf-8 -*-
"""
プロジェクトのメインエントリーポイント。
トレーナーを初期化し、強化学習のサイクルを開始する。
"""
import tensorflow as tf
import json
import os
from src.train.trainer import Trainer

def check_gpu_availability():
    """
    TensorFlowが利用可能な物理デバイス（CPU, GPU）をリストアップし、
    メモリ管理の設定を行う。
    """
    print("\n--- Checking for available devices ---")
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            print(f"Found GPU: {gpus[0].name}")
            print(" -> Set memory growth to True for all GPUs.")
        else:
            print("No GPU found. TensorFlow will run on CPU.")
        
        cpus = tf.config.list_physical_devices('CPU')
        for cpu in cpus:
            print(f"Found CPU: {cpu.name}")
    except Exception as e:
        print(f"Error during device check: {e}")
    print("--------------------------------------\n")


def load_config(config_path='config.json'):
    """設定ファイルを読み込む"""
    print("--- Loading Configuration ---")
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            print("Configuration loaded successfully.")
            return json.load(f)
    else:
        print(f"Warning: {config_path} not found. Using default settings.")
        return {}

def main():
    """
    強化学習のメインプロセス
    """
    try:
        check_gpu_availability()
        config = load_config()

        print("--- Initializing Reinforcement Learning Trainer ---")
        trainer = Trainer(config)
        
        trainer.train()
    
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")
        import traceback
        traceback.print_exc()

    finally:
        print("\n--- Training process finished ---")


if __name__ == '__main__':
    main()

