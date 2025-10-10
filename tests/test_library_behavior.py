# -*- coding: utf-8 -*-
"""
このファイルは、外部ライブラリ `mahjong` の挙動、特に点数計算の結果として
返されるオブジェクトの内部構造を調査するためのテストです。
`HandCalculator.estimate_hand_value`が返すオブジェクトに`dora`や`dora_count`
といった属性が存在するかどうかを直接確認します。
"""
import pytest
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.constants import EAST

def test_hand_calculator_response_attributes():
    """
    mahjongライブラリのHandCalculatorが返すオブジェクトの構造を調査する。
    """
    calculator = HandCalculator()

    # --- START: MODIFICATION ---
    # シンプルな平和・タンヤオ・ドラ1の手を定義 (13枚)
    # 手牌: 2m3m4m 8m8m 5p6p7p 3s4s5s 6s7s (待ち: 5s, 8s)
    hand_136 = TilesConverter.string_to_136_array(man='23488', pin='567', sou='34567')
    
    # ロン牌として8sを指定
    win_tile_136 = TilesConverter.string_to_136_array(sou='8')[0]

    # ドラ表示牌が1mの場合、ドラは2mになる
    dora_indicators = TilesConverter.string_to_136_array(man='1')
    # --- END: MODIFICATION ---

    # 手牌とアガリ牌を結合
    full_hand_136 = sorted(hand_136 + [win_tile_136])

    # 計算のための設定
    config = HandConfig(
        is_tsumo=False,
        is_riichi=False,
        player_wind=EAST,
        round_wind=EAST,
        options=OptionalRules(has_open_tanyao=True, has_aka_dora=True)
    )

    # 点数計算を実行
    result = calculator.estimate_hand_value(
        tiles=full_hand_136,
        win_tile=win_tile_136,
        melds=[],
        dora_indicators=dora_indicators,
        config=config
    )

    # --- ここから結果の調査 ---
    print("\n--- HandCalculator Response Details ---")
    assert result is not None, "Calculation result should not be None."
    assert result.error is None, f"Hand calculation failed: {result.error}"

    print(f"Han: {result.han}, Fu: {result.fu}")
    print(f"Yaku List: {[y.name for y in result.yaku]}")
    
    print("\n--- Dumping all available attributes of the result object ---")
    # resultオブジェクトが持つ全ての公開属性を一覧表示
    for attr in dir(result):
        if not attr.startswith('_'):
            # --- START: MODIFICATION ---
            try:
                value = getattr(result, attr)
                print(f"Attribute: '{attr}', Value: {value}")
            except Exception as e:
                print(f"Attribute: '{attr}', Error accessing value: {e}")
            # --- END: MODIFICATION ---

    # 結論の表示
    has_dora_attr = hasattr(result, 'dora')
    has_dora_count_attr = hasattr(result, 'dora_count')

    print("\n--- Conclusion ---")
    print(f"Does the result object have a 'dora' attribute? -> {has_dora_attr}")
    print(f"Does the result object have a 'dora_count' attribute? -> {has_dora_count_attr}")

    # 前回の修正ロジックが正しいかどうかの検証
    dora_han_from_yaku = 0
    for yaku in result.yaku:
        if 'Dora' in yaku.name:
             dora_han_from_yaku += (yaku.han_closed or yaku.han_opened)
    
    print(f"Total dora han calculated from yaku list: {dora_han_from_yaku}")
    assert dora_han_from_yaku > 0, "Dora should be detected from the yaku list."

