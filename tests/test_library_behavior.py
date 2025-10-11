# -*- coding: utf-8 -*-
"""
このファイルは、外部ライブラリ `mahjong` の挙動、特に点数計算や
シャンテン数計算の結果を調査するためのテストです。

このテストコードを通じて、以下の点を明らかにすることを目的とします。
1. HandCalculatorによる点数計算オブジェクトの基本的な構造
2. 副露（鳴き）を含む複雑な手牌のシャンテン数計算
3. 一般手（面子手）以外の特殊な手役（七対子、国士無双）のシャンテン数計算
4. 聴牌していない手牌（一向聴、二向聴）のシャンテン数計算
5. 役無し聴牌（アガれない聴牌）の判定
"""
import pytest
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.constants import EAST, SOUTH
from mahjong.shanten import Shanten
from mahjong.meld import Meld

# ===============================================================================
# Section 1: HandCalculator（点数計算）の基本的な挙動調査
# ===============================================================================

def test_yakunashi_tenpai():
    """
    役無し聴牌の状態でアガろうとした場合に、ライブラリが正しくエラーを返すか調査します。
    """
    print("\n--- Running Test: Yakunashi Tenpai (No Yaku) ---")
    calculator = HandCalculator()

    # 手牌: 234m 567p 88s, 鳴き: [123s] -> 待ち: 7s, 9s
    # 1sを鳴いているためタンヤオにならず、他の役もない。
    hand_136 = TilesConverter.string_to_136_array(man='234', pin='567', sou='88')
    win_tile_136 = TilesConverter.string_to_136_array(sou='7')[0]
    melds = [Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(sou='123'))]
    
    full_hand_136 = sorted(hand_136 + [win_tile_136])

    config = HandConfig(player_wind=SOUTH, round_wind=SOUTH)

    result = calculator.estimate_hand_value(
        tiles=full_hand_136,
        win_tile=win_tile_136,
        melds=melds,
        dora_indicators=[],
        config=config
    )
    
    # --- 検証 ---
    # 役がないため、点数計算はエラーになるはず
    assert result.han is None, "役無しの場合、hanはNoneであるべきです。"
    assert result.fu is None, "役無しの場合、fuはNoneであるべきです。"
    assert result.error is not None, "役無しの場合、errorにメッセージが含まれるべきです。"
    assert result.error == 'hand_not_winning', "エラーメッセージが期待と異なります。"

    print(f">>> SUCCESS: 役無しのアガリを正しくエラーとして処理できました。 (Error: {result.error})")


# ===============================================================================
# Section 2: calculate_shanten（シャンテン数計算）の挙動調査
# ===============================================================================

shanten_calculator = Shanten()

def test_tenpai_hand_with_melds():
    """
    複数の副露（鳴き）がある聴牌形の手牌を、ライブラリが正しく
    「向聴数0（聴牌）」と判定できるか調査します。
    """
    print("\n--- Running Test: Tenpai Hand with Melds ---")

    hand_tiles = TilesConverter.string_to_136_array(man='2455')

    meld1 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='678'))
    meld2 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(pin='456'))
    meld3 = Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='345'))
    melds = [meld1, meld2, meld3]

    hand_34_array = TilesConverter.to_34_array(hand_tiles)
    
    open_sets = []
    for meld in melds:
        tiles_34 = sorted([t // 4 for t in meld.tiles])
        open_sets.append(tiles_34)

    shanten_result = shanten_calculator.calculate_shanten(
        hand_34_array,
        open_sets
    )

    print(f"Hand: 2455m, Melds: [678m, 456p, 345m]")
    print(f"Library's Calculated Shanten: {shanten_result}")
    print("Expected Shanten: 0 (Tenpai)")

    assert shanten_result == 0, "この聴牌形はシャンテン数0と計算されるべきです。"
    print(">>> SUCCESS: 鳴きを含んだ聴牌形を正しく認識できました。")


def test_iishanten_hand():
    """
    聴牌していない手牌（一向聴）のシャンテン数が正しく計算されるか調査します。
    """
    print("\n--- Running Test: Iishanten Hand (Not Tenpai) ---")

    hand_tiles = TilesConverter.string_to_136_array(man='123', pin='456', sou='789', honors='112')
    hand_34_array = TilesConverter.to_34_array(hand_tiles)

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)

    print(f"Hand: 123m 456p 789s 11z 2z")
    print(f"Library's Calculated Shanten: {shanten_result}")
    print("Expected Shanten: 1 (Iishanten)")

    assert shanten_result == 1, "この手牌はシャンテン数1（一向聴）と計算されるべきです。"
    print(">>> SUCCESS: 一向聴の手牌を正しく認識できました。")


def test_chitoitsu_iishanten():
    """
    特殊な手役である七対子（チートイツ）の一向聴のシャンテン数が正しく計算されるか調査します。
    """
    print("\n--- Running Test: Chitoitsu (Seven Pairs) Iishanten ---")

    # --- ライブラリの七対子シャンテン数ロジック ---
    # シャンテン数 = 6 - (対子の数)
    # 一向聴 (シャンテン数1) にするためには、対子の数を5にする必要がある。
    # 5対子 + 3枚のバラ牌 = 合計13枚
    hand_tiles = TilesConverter.string_to_136_array(
        man='1199', pin='2288', honors='11567'
    ) # 5対子: 1m,9m,2p,8p,東 + 3枚: 白,發,中
    hand_34_array = TilesConverter.to_34_array(hand_tiles)

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)

    print(f"Hand: 11m 99m 2p2p 8p8p 11z 5z 6z 7z (5 pairs + 3 singles)")
    print(f"Library's Calculated Shanten (min shanten): {shanten_result}")
    print("Expected Shanten (Chitoitsu): 1 (Iishanten)")

    # この手牌の最小シャンテンは七対子由来の1になる
    assert shanten_result == 1, "この七対子の一向聴はシャンテン数1と計算されるべきです。"
    print(">>> SUCCESS: 七対子の一向聴を正しく認識できました。")

def test_chitoitsu_tenpai():
    """
    七対子（チートイツ）の聴牌（シャンテン数0）が正しく計算されるか調査します。
    """
    print("\n--- Running Test: Chitoitsu (Seven Pairs) Tenpai ---")

    # 七対子の聴牌は「6対子 + 1枚のバラ牌」の13枚で構成される
    # シャンテン数 = 6 - (対子の数) = 6 - 6 = 0
    hand_tiles = TilesConverter.string_to_136_array(man='1199', pin='2288', honors='11556') # 6対子1枚、合計13枚
    hand_34_array = TilesConverter.to_34_array(hand_tiles)

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)

    print(f"Hand: 11m 99m 2p2p 8p8p 11z 55z 6z (6 pairs + 1 single)")
    print(f"Library's Calculated Shanten (min shanten): {shanten_result}")
    print("Expected Shanten (Chitoitsu): 0 (Tenpai)")

    assert shanten_result == 0, "この七対子の聴牌はシャンテン数0と計算されるべきです。"
    print(">>> SUCCESS: 七対子の聴牌を正しく認識できました。")


def test_kokushi_musou_tenpai():
    """
    特殊な手役である国士無双（コクシムソウ）の聴牌のシャンテン数が正しく計算されるか調査します。
    """
    print("\n--- Running Test: Kokushi Musou (Thirteen Orphans) Tenpai ---")

    # 手牌: 19m 19p 19s 1234567z (13種全てのヤオチュウ牌) -> 13面待ちの聴牌
    hand_tiles = TilesConverter.string_to_136_array(man='19', pin='19', sou='19', honors='1234567')
    hand_34_array = TilesConverter.to_34_array(hand_tiles)

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)

    print(f"Hand: 19m 19p 19s 1234567z")
    print(f"Library's Calculated Shanten (min shanten): {shanten_result}")
    print("Expected Shanten (Kokushi): 0 (Tenpai)")
    
    # この手牌は聴牌なので、シャンテン数は0になる
    assert shanten_result == 0, "この国士無双の聴牌はシャンテン数0と計算されるべきです。"
    print(">>> SUCCESS: 国士無双の聴牌を正しく認識できました。")

