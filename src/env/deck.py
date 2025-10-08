# -*- coding: utf-8 -*-
"""
麻雀の牌山（デッキ）を管理するための独立したクラス。
赤ドラなどのルールを考慮した、より堅牢な実装。
"""
import random

class Deck:
    def __init__(self, rules=None):
        """
        ルールに基づいて136枚の牌で構成される山を初期化し、シャッフルする。

        Args:
            rules (dict, optional): ゲームルール設定。
                                    'has_aka_dora'キー（bool）を想定。
        """
        if rules is None:
            rules = {}

        self._build_deck(rules)
        random.shuffle(self.tiles)

    def _build_deck(self, rules):
        """
        ルールに従って136枚の牌セットを構築する。
        """
        # 0から33までの34種類の牌を、それぞれ4枚ずつ生成する。
        # これにより、0から135までの136個のユニークなIDを持つ牌のリストが作成される。
        self.tiles = []
        for tile_type in range(34):
            # 例：萬子の1 (tile_type=0) -> [0, 1, 2, 3]
            #     萬子の2 (tile_type=1) -> [4, 5, 6, 7]
            base_id = tile_type * 4
            self.tiles.extend(range(base_id, base_id + 4))

        # --- 赤ドラの扱いについて ---
        # このプロジェクトが利用している`mahjong`ライブラリでは、
        # 牌のIDそのものを書き換える必要はありません。
        #
        # 点数計算を行う`HandCalculator`が、`HandConfig`オブジェクト経由で
        # `has_aka_dora=True`というルールを受け取ると、以下の特定のIDを持つ牌を
        # 自動的に「赤ドラ」として解釈し、点数計算に含めます。
        #
        # - 牌ID 16: 赤五萬 (通常の五萬は 17, 18, 19)
        # - 牌ID 52: 赤五筒 (通常の五筒は 53, 54, 55)
        # - 牌ID 88: 赤五索 (通常の五索は 89, 90, 91)
        #
        # したがって、このDeckクラスの責務は、ルールに関わらず常に0から135までの
        # 136枚の牌セットを生成することです。赤ドラを実際にどう扱うかは、
        # この牌セットを利用する側の`MahjongEnv`や`HandCalculator`が担います。
        #
        # has_aka_dora = rules.get('has_aka_dora', True)
        # if has_aka_dora:
        #     # 将来的に「赤ドラ2枚」のような特殊ルールを実装する場合は、
        #     # ここで特定の牌IDをリストから除外するなどの処理を追加する。
        #     # 現状の「赤ドラあり/なし」ルールでは、このままで問題ありません。
        #     pass

