# -*- coding: utf-8 -*-
"""
麻雀のルール判定や選択肢生成など、複雑なロジックを扱うヘルパー関数群。
MahjongEnvクラスの負担を軽減し、コードの見通しを良くする責務を持つ。
"""
from mahjong.tile import TilesConverter
from mahjong.shanten import Shanten
from mahjong.meld import Meld
from mahjong.hand_calculating.hand import HandCalculator

# --- グローバルインスタンス ---
# これらのクラスは状態を持たないため、一度だけインスタンス化して共有する
SHANTEN_CALCULATOR = Shanten()
HAND_CALCULATOR = HandCalculator()


def check_tenpai(hand_136, melds_136):
    """
    プレイヤーが聴牌（形式聴牌）しているか判定する。
    `mahjong`ライブラリの推奨される使い方に修正。Meldオブジェクトのリストを
    直接渡すことで、ライブラリがチーとポン・カンを正確に判別する。
    """
    num_tiles = len(hand_136)

    # --- 13枚の手牌（打牌後・流局時など）の聴牌判定 ---
    if num_tiles % 3 == 1:
        try:
            hand_34 = TilesConverter.to_34_array(hand_136)
            # --- START: MODIFICATION - 副露の渡し方をライブラリの推奨形式に修正 ---
            shanten = SHANTEN_CALCULATOR.calculate_shanten(hand_34, melds=melds_136)
            # --- END: MODIFICATION ---
            return shanten == 0
        except Exception:
            return False

    # --- 14枚の手牌（ツモ後）の聴牌判定 ---
    elif num_tiles % 3 == 2:
        for i in range(num_tiles):
            temp_hand_13_tiles = hand_136[:i] + hand_136[i+1:]
            try:
                hand_34 = TilesConverter.to_34_array(temp_hand_13_tiles)
                # --- START: MODIFICATION - 副露の渡し方をライブラリの推奨形式に修正 ---
                shanten = SHANTEN_CALCULATOR.calculate_shanten(hand_34, melds=melds_136)
                # --- END: MODIFICATION ---
                if shanten == 0:
                    return True
            except Exception:
                continue
        return False

    return False


def check_agari(player_idx, win_tile, is_tsumo, game_state, rules):
    """
    指定された牌でアガれるか（役があるか）を判定する。
    """
    hand_136 = game_state['hands'][player_idx]
    melds = game_state['melds'][player_idx]
    dora_indicators = game_state['dora_indicators']

    try:
        # 手計算用の設定オブジェクトを作成
        config = HAND_CALCULATOR.config_class(
            is_tsumo=is_tsumo,
            is_riichi=game_state['is_riichi'][player_idx],
            player_wind=game_state['player_winds'][player_idx],
            round_wind=game_state['round_wind'],
            options=HAND_CALCULATOR.config_class.options_class(
                has_open_tanyao=rules.get('has_open_tanyao', True),
                has_aka_dora=rules.get('has_aka_dora', True)
            )
        )
        
        full_hand = hand_136 if is_tsumo else hand_136 + [win_tile]
        
        result = HAND_CALCULATOR.estimate_hand_value(
            tiles=full_hand,
            win_tile=win_tile,
            melds=melds,
            dora_indicators=dora_indicators,
            config=config
        )
        return result.error is None
    except Exception:
        return False


def find_my_turn_actions(player_idx, game_state, rules):
    """
    手番プレイヤーの可能な行動リストを生成する。
    """
    actions = []
    hand = game_state['hands'][player_idx]
    
    # ツモ和了
    last_drawn = game_state.get('last_drawn_tile')
    if last_drawn and check_agari(player_idx, last_drawn, True, game_state, rules):
        actions.append("ACTION_TSUMO")

    # 打牌
    unique_tiles = sorted(list(set(hand)))
    for tile in unique_tiles:
        actions.append(f"DISCARD_{tile}")

    # リーチ
    is_menzen = not any(m.opened for m in game_state['melds'][player_idx])
    can_riichi = (not game_state['is_riichi'][player_idx] and 
                  is_menzen and game_state['scores'][player_idx] >= 1000)

    if can_riichi:
        # 現在の手牌（14枚）が「1枚捨てれば聴牌になる」状態かを確認
        if check_tenpai(hand, game_state['melds'][player_idx]):
            # 聴牌を維持できる捨て牌の選択肢を生成
            for tile in unique_tiles:
                temp_hand = hand[:]
                temp_hand.remove(tile)
                # 実際に捨てた後の13枚の手牌が聴牌しているか最終確認
                if check_tenpai(temp_hand, game_state['melds'][player_idx]):
                     actions.append(f"ACTION_RIICHI_{tile}")

    # TODO: カンのロジックを追加

    return list(dict.fromkeys(actions))


def find_opponent_turn_actions(player_idx, discarded_tile, game_state, rules):
    """
    他家の捨て牌に対する行動リストを生成する。
    """
    actions = ["ACTION_PASS"]
    hand = game_state['hands'][player_idx]
    
    # ロン和了
    if check_agari(player_idx, discarded_tile, False, game_state, rules):
        actions.append("ACTION_RON")

    # 副露（鳴き）
    if not game_state['is_riichi'][player_idx]:
        hand_34 = TilesConverter.to_34_array(hand)
        discarded_34 = discarded_tile // 4

        # ポン
        if hand_34[discarded_34] >= 2:
            actions.append("ACTION_PUNG")
        
        # チー (下家からのみ)
        discarder_idx = game_state['last_discarder']
        if (discarder_idx + 1) % 4 == player_idx and discarded_34 < 27:
            num = discarded_34 % 9
            # パターン1: [n-2, n-1], n
            if num >= 2 and hand_34[discarded_34-2] > 0 and hand_34[discarded_34-1] > 0:
                actions.append(f"ACTION_CHII_{discarded_34-2}_{discarded_34-1}")
            # パターン2: n-1, [n], n+1
            if 1 <= num <= 7 and hand_34[discarded_34-1] > 0 and hand_34[discarded_34+1] > 0:
                actions.append(f"ACTION_CHII_{discarded_34-1}_{discarded_34+1}")
            # パターン3: n, [n+1, n+2]
            if num <= 6 and hand_34[discarded_34+1] > 0 and hand_34[discarded_34+2] > 0:
                actions.append(f"ACTION_CHII_{discarded_34+1}_{discarded_34+2}")

    # TODO: 大明槓のロジックを追加

    return list(dict.fromkeys(actions))

