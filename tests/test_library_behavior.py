# -*- coding: utf-8 -*-
"""
このファイルは、外部ライブラリ `mahjong` の挙動、特に点数計算や
シャンテン数計算の結果を調査するためのテストです。
"""
import pytest
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.constants import EAST
from mahjong.shanten import calculate_shanten
from mahjong.meld import Meld


def test_hand_calculator_response_attributes():
    """
    mahjongライブラリのHandCalculatorが返すオブジェクトの構造を調査する。
    """
    calculator = HandCalculator()

    # シンプルな平和・タンヤオ・ドラ1の手を定義 (13枚)
    # 手牌: 2m3m4m 8m8m 5p6p7p 3s4s5s 6s7s (待ち: 5s, 8s)
    hand_136 = TilesConverter.string_to_136_array(man='23488', pin='567', sou='34567')
    
    # ロン牌として8sを指定
    win_tile_136 = TilesConverter.string_to_136_array(sou='8')[0]

    # ドラ表示牌が1mの場合、ドラは2mになる
    dora_indicators = TilesConverter.string_to_136_array(man='1')

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

    assert result is not None, "Calculation result should not be None."
    assert result.error is None, f"Hand calculation failed: {result.error}"


def test_problematic_tenpai_hand():
    """
    直近のログで問題となった、複数の副露がある聴牌形 (3m待ち) を
    mahjongライブラリが正しく「向聴数0」と判定できるか調査する。
    - 手牌: 2455m
    - 副露: [678m], [456p], [345m]
    """
    print("\n--- Investigating Problematic Tenpai Hand ---")
    
    hand_tiles = TilesConverter.string_to_136_array(man='2455')
    
    meld1 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='678'))
    meld2 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(pin='456'))
    meld3 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='345'))
    melds = [meld1, meld2, meld3]

    hand_34_array = TilesConverter.to_34_array(hand_tiles)
    
    chi_sets, pon_sets, kan_sets = [], [], []
    for meld in melds:
        tiles_34 = sorted([t // 4 for t in meld.tiles])
        if meld.type == Meld.CHI:
            chi_sets.append(tiles_34)
        elif meld.type == Meld.PON:
            pon_sets.append(tiles_34[:3])
        elif meld.type == Meld.KAN:
            kan_sets.append(tiles_34)

    # --- START: FINAL FIX ---
    # Shantenクラスのインスタンスではなく、スタンドアロン関数を呼び出す
    shanten_result = calculate_shanten(
        hand_34_array, 
        chi_sets_34=chi_sets,
        pon_sets_34=pon_sets,
        kan_sets_34=kan_sets
    )
    # --- END: FINAL FIX ---

    print(f"Hand: 2455m, Melds: [678m, 456p, 345m]")
    print(f"Library's Calculated Shanten: {shanten_result}")
    print("Expected Shanten: 0 (Tenpai)")

    assert shanten_result == 0, "The library should have calculated shanten as 0 for this tenpai hand."
    print(">>> SUCCESS: The library correctly identifies this hand as tenpai.")

