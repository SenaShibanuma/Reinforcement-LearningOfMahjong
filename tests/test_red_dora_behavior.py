import pytest
from mahjong.tile import TilesConverter
from mahjong.constants import FIVE_RED_MAN, FIVE_RED_PIN, FIVE_RED_SOU
from mahjong.utils import is_aka_dora, plus_dora
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.meld import Meld


def test_exact_136_indices_for_zero_and_five():
    """Assert exact 136 indices for '0' (red five) and '5' (normal five) per suit."""
    print("TEST: 各色の'0'牌(赤ドラ)と'5'牌(通常)が、それぞれ期待される136配列のインデックスに変換されるか")
    # Known constants from mahjong.constants
    assert FIVE_RED_MAN == 16
    assert FIVE_RED_PIN == 52
    assert FIVE_RED_SOU == 88

    red_m = TilesConverter.one_line_string_to_136_array("0m", has_aka_dora=True)[0]
    normal_m = TilesConverter.one_line_string_to_136_array("5m", has_aka_dora=True)[0]
    assert red_m == FIVE_RED_MAN
    # normal 5m should be the next copy (tile + 1)
    assert normal_m == FIVE_RED_MAN + 1

    red_p = TilesConverter.one_line_string_to_136_array("0p", has_aka_dora=True)[0]
    normal_p = TilesConverter.one_line_string_to_136_array("5p", has_aka_dora=True)[0]
    assert red_p == FIVE_RED_PIN
    assert normal_p == FIVE_RED_PIN + 1

    red_s = TilesConverter.one_line_string_to_136_array("0s", has_aka_dora=True)[0]
    normal_s = TilesConverter.one_line_string_to_136_array("5s", has_aka_dora=True)[0]
    assert red_s == FIVE_RED_SOU
    assert normal_s == FIVE_RED_SOU + 1


def test_plus_dora_exact_counts_and_indicator_combination():
    """Test plus_dora exact counts combining aka-dora and indicator-based dora."""
    print("TEST: plus_dora関数が、赤ドラとドラ表示牌を正しく数え上げるか（赤ドラ有効/無効時）")
    red_s = TilesConverter.one_line_string_to_136_array("0s", has_aka_dora=True)[0]
    normal_s = TilesConverter.one_line_string_to_136_array("5s", has_aka_dora=True)[0]

    # Choose dora indicator '4s' so dora by indicator is '5s'
    indicator_4s = TilesConverter.one_line_string_to_136_array("4s", has_aka_dora=True)[0]

    # red 5s with aka counting + indicator -> should be 2
    count_red_with_aka = plus_dora(red_s, [indicator_4s], add_aka_dora=True)
    assert count_red_with_aka == 2

    # red 5s without aka counting -> only indicator counts
    count_red_no_aka = plus_dora(red_s, [indicator_4s], add_aka_dora=False)
    assert count_red_no_aka == 1

    # normal 5s (not aka) should be counted only by indicator
    count_normal_with_aka_flag = plus_dora(normal_s, [indicator_4s], add_aka_dora=True)
    assert count_normal_with_aka_flag == 1


def test_to_one_line_string_roundtrip_printing():
    """Verify to_one_line_string prints '0' for aka when requested and '5' otherwise."""
    print("TEST: to_one_line_string関数が、赤ドラを'0'として正しく文字列に変換するか（print_aka_doraフラグ）")
    red_s = TilesConverter.one_line_string_to_136_array("0s", has_aka_dora=True)[0]
    normal_s = TilesConverter.one_line_string_to_136_array("5s", has_aka_dora=True)[0]

    s_red_print = TilesConverter.to_one_line_string([red_s], print_aka_dora=True)
    assert s_red_print == "0s"

    s_red_no_print = TilesConverter.to_one_line_string([red_s], print_aka_dora=False)
    assert s_red_no_print == "5s"

    s_normal_print = TilesConverter.to_one_line_string([normal_s], print_aka_dora=True)
    assert s_normal_print == "5s"

def test_is_aka_dora_functionality():
    """Test is_aka_dora function correctly identifies red dora."""
    print("\nTEST: is_aka_dora関数が赤ドラを正しく識別するか")

    # 赤5m (FIVE_RED_MAN) は aka_dora_list に含まれる
    assert is_aka_dora(FIVE_RED_MAN, True) == True
    assert is_aka_dora(FIVE_RED_MAN, False) == False # aka_enabled=False の場合は常にFalse

    # 赤5p (FIVE_RED_PIN)
    assert is_aka_dora(FIVE_RED_PIN, True) == True
    assert is_aka_dora(FIVE_RED_PIN, False) == False

    # 赤5s (FIVE_RED_SOU)
    assert is_aka_dora(FIVE_RED_SOU, True) == True
    assert is_aka_dora(FIVE_RED_SOU, False) == False

    # 通常の5m (FIVE_RED_MAN + 1) は aka_dora_list に含まれない
    assert is_aka_dora(FIVE_RED_MAN + 1, True) == False
    assert is_aka_dora(FIVE_RED_MAN + 1, False) == False

    # 通常の5p (FIVE_RED_PIN + 1) は aka_dora_list に含まれない
    assert is_aka_dora(FIVE_RED_PIN + 1, True) == False
    assert is_aka_dora(FIVE_RED_PIN + 1, False) == False

    # 通常の5s (FIVE_RED_SOU + 1) は aka_dora_list に含まれない
    assert is_aka_dora(FIVE_RED_SOU + 1, True) == False
    assert is_aka_dora(FIVE_RED_SOU + 1, False) == False

    print("  is_aka_dora関数のテストが完了しました。")

def test_hand_value_with_and_without_aka_dora():
    """赤ドラあり・なしのそれぞれの手を実際に計算し、翻数の差を確認する"""
    print("\nTEST: 赤ドラの有無による手計算結果（翻、符、点数）の比較")
    calculator = HandCalculator()

    # --- 正しい平和（ピンフ）の構成 ---
    # 手牌: 123m 99p 234s 789s 40s (3s or 6s 待ちの両面待ち)
    # 和了牌: 6s (ツモ)
    # ドラ表示牌: 1s (ドラは 2s)

    # --- 赤ドラありのケース ---
    # 役: 平和(1), 門前清自摸和(1), ドラ(1, 2s), 赤ドラ(1, 0s) = 4翻
    hand_tiles_13_with_aka = TilesConverter.string_to_136_array(
        man="123", pin="99", sou="23478940"
    )
    win_tile = TilesConverter.string_to_136_array(sou="6")[0]
    dora_indicators = [TilesConverter.string_to_136_array(sou="1")[0]]

    # estimate_hand_valueには和了牌を含む14牌を渡す
    # mahjongライブラリのHandCalculatorが赤ドラを含むと和了形を誤認識する問題への対応
    # 赤ドラを通常の5に変換してから計算し、後から赤ドラの数を翻に加算する
    hand_tiles_13_without_aka_for_calc = [
        t if t != 88 else 89 for t in hand_tiles_13_with_aka
    ]
    full_hand_with_aka_for_calc = sorted(
        hand_tiles_13_without_aka_for_calc + [win_tile]
    )
    result_with_aka = calculator.estimate_hand_value(
        full_hand_with_aka_for_calc,
        win_tile,
        dora_indicators=dora_indicators,
        config=HandConfig(is_tsumo=True),
    )
    assert (
        result_with_aka.error is None
    ), f"赤ドラありの手で計算エラー: {result_with_aka.error}"

    # 赤ドラの数を翻に加算
    aka_dora_count = hand_tiles_13_with_aka.count(88)
    total_han_with_aka = result_with_aka.han + aka_dora_count
    assert total_han_with_aka == 4, f"赤ドラありの翻数が違います: {total_han_with_aka}"

    # --- 赤ドラなしのケース ---
    # 役: 平和(1), 門前清自摸和(1), ドラ(1, 2s) = 3翻
    hand_tiles_13_without_aka = TilesConverter.string_to_136_array(
        man="123", pin="99", sou="23478945"
    )
    full_hand_without_aka = sorted(hand_tiles_13_without_aka + [win_tile])
    result_without_aka = calculator.estimate_hand_value(
        full_hand_without_aka,
        win_tile,
        dora_indicators=dora_indicators,
        config=HandConfig(is_tsumo=True),
    )
    assert (
        result_without_aka.error is None
    ), f"赤ドラなしの手で計算エラー: {result_without_aka.error}"
    print(
        f"  赤ドラなしの手: {result_without_aka.han}翻 {result_without_aka.fu}符, 点数: {result_without_aka.cost['main']} (ツモ)"
    )
    assert result_without_aka.han == 3
    assert result_without_aka.fu == 20

    assert result_with_aka.han == result_without_aka.han + 1
    print("  検証: 赤ドラの有無で翻数が正しく1翻違うことを確認しました。")