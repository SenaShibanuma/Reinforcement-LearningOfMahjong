# mahjong ライブラリ利用ガイド

このドキュメントは、`mahjong`ライブラリの主要機能と、その具体的な利用方法について解説します。`tests`フォルダ内のテストコードを基に、実践的な使用例を交えて説明します。

## 1. 牌の形式変換: `TilesConverter`

`TilesConverter`は、麻雀の牌を異なるデータ形式（文字列、34種配列、136枚配列など）間で相互に変換するためのユーティリティクラスです。

### 主なメソッド

#### `string_to_136_array(man, pin, sou, honors, has_aka_dora=False)`
可読性の高い文字列形式の手牌を、内部計算で使われる136枚配列形式に変換します。

- **引数:**
  - `man` (str): 萬子 (例: '123')
  - `pin` (str): 筒子 (例: '456')
  - `sou` (str): 索子 (例: '789')
  - `honors` (str): 字牌 (例: '1234567' は東南西北白發中)
  - `has_aka_dora` (bool): `True`にすると、各数牌の`'5'`の代わりに`'0'`を赤ドラとして扱えます。

- **戻り値:**
  - `list[int]`: 136枚配列形式の牌リスト。

- **使用例:**
  ```python
  from mahjong.tile import TilesConverter

  # 通常の手牌
  hand_tiles = TilesConverter.string_to_136_array(man='123', pin='456', sou='789', honors='11')

  # 赤ドラを含む手牌
  # 0sが赤5索に対応
  hand_with_aka = TilesConverter.string_to_136_array(sou='055', has_aka_dora=True)
  ```

#### `to_34_array(tiles_136)`
136枚配列を、シャンテン数計算などで使われる34種配列形式に変換します。同じ牌が複数ある場合は、その牌種に対応するインデックスの値がインクリメントされます。

- **引数:**
  - `tiles_136` (list[int]): 136枚配列形式の牌リスト。

- **戻り値:**
  - `list[int]`: 34種配列形式の牌リスト（長さ34の配列）。

- **使用例:**
  ```python
  from mahjong.tile import TilesConverter

  hand_136 = TilesConverter.string_to_136_array(man='11123')
  hand_34 = TilesConverter.to_34_array(hand_136)
  # hand_34 の萬子1の位置が3になる
  ```

---

## 2. シャンテン数計算: `Shanten`

`Shanten`クラスは、与えられた手牌が聴牌（テンパイ）まであと何枚有効牌が必要か（シャンテン数）を計算します。

### 主なメソッド

#### `calculate_shanten(tiles_34, open_sets=None)`
手牌のシャンテン数を計算します。一般手（4面子1雀頭）、七対子、国士無双の3つの手役についてそれぞれ計算し、最も小さいシャンテン数を返します。

- **引数:**
  - `tiles_34` (list[int]): 34種配列形式の手牌。
  - `open_sets` (list[list[int]], optional): 副露（鳴き）した面子のリスト。

- **戻り値:**
  - `int`: 計算された最小シャンテン数。
    - `0`: 聴牌 (Tenpai)
    - `1`: 一向聴 (Iishanten)
    - `-1`: 和了 (Agari) ※ ただし、この関数は和了を判定するものではないため、通常は0が聴牌を示す最小値。

- **使用例:**

  - **一向聴（Iishanten）の計算**
    ```python
    from mahjong.tile import TilesConverter
    from mahjong.shanten import Shanten

    shanten_calculator = Shanten()
    hand_tiles = TilesConverter.string_to_136_array(man='123', pin='456', sou='789', honors='112')
    hand_34_array = TilesConverter.to_34_array(hand_tiles)

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)
    # 期待値: 1
    ```

  - **副露（鳴き）を含む聴牌形の計算**
    ```python
    from mahjong.tile import TilesConverter
    from mahjong.shanten import Shanten
    from mahjong.meld import Meld

    shanten_calculator = Shanten()
    hand_tiles = TilesConverter.string_to_136_array(man='2455')
    melds = [
        Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='678')),
        Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(pin='456')),
        Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(man='345'))
    ]

    hand_34_array = TilesConverter.to_34_array(hand_tiles)
    open_sets = [[t // 4 for t in meld.tiles] for meld in melds]

    shanten_result = shanten_calculator.calculate_shanten(hand_34_array, open_sets)
    # 期待値: 0
    ```

  - **特殊手役（七対子、国士無双）の計算**
    ライブラリは自動的に七対子・国士無双のシャンテン数も考慮します。
    ```python
    # 七対子の一向聴
    hand_tiles = TilesConverter.string_to_136_array(man='1199', pin='2288', honors='11567')
    hand_34_array = TilesConverter.to_34_array(hand_tiles)
    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)
    # 期待値: 1 (七対子として)

    # 国士無双の聴牌
    hand_tiles = TilesConverter.string_to_136_array(man='19', pin='19', sou='19', honors='1234567')
    hand_34_array = TilesConverter.to_34_array(hand_tiles)
    shanten_result = shanten_calculator.calculate_shanten(hand_34_array)
    # 期待値: 0 (国士無双として)
    ```

---

## 3. 点数計算: `HandCalculator`

`HandCalculator`クラスは、和了した手牌の点数（翻、符）を計算します。

### 主なメソッド

#### `estimate_hand_value(tiles, win_tile, melds=None, dora_indicators=None, config=None)`
和了形と状況に基づき、手牌の価値を評価します。

- **引数:**
  - `tiles` (list[int]): 和了牌を含む、手牌全体の136枚配列。
  - `win_tile` (int): 和了牌の136枚配列での表現。
  - `melds` (list[Meld], optional): 副露（鳴き）のリスト。
  - `dora_indicators` (list[int], optional): ドラ表示牌のリスト。
  - `config` (HandConfig, optional): 場の状況（自風、場風、ツモ和了かなど）を設定するオブジェクト。

- **戻り値:**
  - `HandResponse` オブジェクト。主な属性は以下の通り。
    - `han` (int): 翻数。役がない場合は `None`。
    - `fu` (int): 符。役がない場合は `None`。
    - `cost` (dict): 点数。
    - `error` (str): 役がない、もしくは手牌構成が不正な場合のエラーメッセージ。

- **使用例:**

  - **役無し聴牌の判定**
    `HandCalculator`は役がない和了を正しくエラーとして判定できます。
    ```python
    from mahjong.tile import TilesConverter
    from mahjong.hand_calculating.hand import HandCalculator
    from mahjong.hand_calculating.hand_config import HandConfig
    from mahjong.meld import Meld
    from mahjong.constants import SOUTH

    calculator = HandCalculator()
    hand_136 = TilesConverter.string_to_136_array(man='234', pin='567', sou='88')
    win_tile_136 = TilesConverter.string_to_136_array(sou='7')[0]
    melds = [Meld(Meld.CHI, tiles=TilesConverter.string_to_136_array(sou='123'))]

    result = calculator.estimate_hand_value(
        tiles=sorted(hand_136 + [win_tile_136]),
        win_tile=win_tile_136,
        melds=melds,
        config=HandConfig(player_wind=SOUTH, round_wind=SOUTH)
    )

    # result.error が 'hand_not_winning' となる
    ```

  - **赤ドラを含む点数計算**
    赤ドラは `HandConfig` や `estimate_hand_value` で直接扱われません。`utils.plus_dora` などで別途計算する必要があります。
    ```python
    from mahjong.utils import plus_dora
    from mahjong.constants import FIVE_RED_SOU

    # 手牌に赤5索が含まれている場合
    # hand_tiles_13_with_aka = [...]
    # aka_dora_count = hand_tiles_13_with_aka.count(FIVE_RED_SOU) # -> 1

    # estimate_hand_valueで計算された翻に、後から加算する
    # total_han = result.han + aka_dora_count
    ```

---

## 4. 補助クラスとユーティリティ

### `HandConfig`
点数計算時の詳細な状況設定に使います。

- **主な引数:**
  - `is_tsumo` (bool): ツモ和了かどうか。
  - `player_wind` (int): 自風（例: `mahjong.constants.EAST`）。
  - `round_wind` (int): 場風。
  - `has_aka_dora` (bool): 赤ドラの有無（ルール設定）。

### `Meld`
副露（鳴き）を表現します。

- **主な引数:**
  - `meld_type` (int): 鳴きの種類 (`Meld.CHI`, `Meld.PON`, `Meld.KAN`)。
  - `tiles` (list[int]): 鳴いた牌の136枚配列。

### `is_aka_dora(tile_136, aka_enabled=True)`
与えられた牌が赤ドラかどうかを判定します。

- **引数:**
  - `tile_136` (int): 判定したい牌。
  - `aka_enabled` (bool): 赤ドラが有効なルールか。

- **戻り値:**
  - `bool`: 赤ドラであれば `True`。