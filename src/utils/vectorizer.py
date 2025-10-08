# -*- coding: utf-8 -*-
"""
ゲームのイベントや選択肢を、AIモデルが解釈できる固定長のベクトルに変換する関数群。
"""
import numpy as np
import tensorflow as tf
from src.constants import MAX_CONTEXT_LENGTH, MAX_CHOICES, VECTOR_DIM

def vectorize_event(event, player_pov):
    """単一のイベント辞書を固定長のベクトルに変換する"""
    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    event_ids = {'GAME_START': 1, 'INIT': 2, 'DRAW': 3, 'DISCARD': 4, 'MELD': 5, 'RIICHI_DECLARED': 6, 'RIICHI_ACCEPTED': 7, 'NEW_DORA': 8, 'AGARI': 9, 'RYUUKYOKU': 10}
    vec[0] = event_ids.get(event.get('event_id'), 0)
    player = event.get('player', -1)
    if player != -1:
        relative_player = (player - player_pov + 4) % 4
        vec[1] = relative_player
    vec[2] = event.get('turn_count', 0) / 30.0
    scores = event.get('scores', [25000]*4)
    for i in range(4): vec[3 + i] = (scores[(player_pov + i) % 4] - 25000) / 10000.0
    vec[7] = event.get('riichi_sticks', 0)
    vec[8] = event.get('remaining_draws', 70) / 70.0
    vec[10] = event.get('tile', -1)
    vec[11] = 1.0 if event.get('is_tedashi') else 0.0
    vec[12] = event.get('dora_indicator', -1)
    
    # ルール情報をベクトルに追加
    rules = event.get('rules', {})
    vec[20] = 1.0 if rules.get('has_aka_dora') else 0.0
    vec[21] = 1.0 if rules.get('has_open_tanyao') else 0.0
    return vec

def vectorize_choice(choice_str):
    """単一の選択肢（文字列）を固定長のベクトルに変換する"""
    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    parts = choice_str.split('_')
    choice_type = parts[0]
    if choice_type == 'DISCARD':
        vec[0] = 1.0
        vec[1] = int(parts[1])
    elif choice_type == 'ACTION':
        vec[0] = 2.0
        action_type = parts[1]
        # TODO: MahjongEnvで新しいACTIONを追加した場合は、必ずこの辞書にも登録し、
        #       AIがその選択肢を理解できるようにする必要がある。
        action_type_ids = {
            'TSUMO': 1, 'RON': 2, 'RIICHI': 3, 
            'PUNG': 4, 'CHII': 5, 'DAIMINKAN': 6, 
            'ANKAN': 7, 'KAKAN': 8,
            'PASS': 9,
            'KYUUSHU_KYUUHAI': 10 # 新しいアクションを追加
        }
        vec[1] = action_type_ids.get(action_type, 0)
        if action_type == 'RIICHI': 
            vec[2] = int(parts[2])
        elif action_type == 'CHII': 
            vec[2], vec[3] = int(parts[2]), int(parts[3])
        elif action_type in ['ANKAN', 'KAKAN']:
            vec[2] = int(parts[2])

    return vec

