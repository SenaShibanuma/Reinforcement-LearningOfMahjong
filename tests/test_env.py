import unittest
from src.env.mahjong_env import MahjongEnv
from mahjong.tile import TilesConverter

class TestMahjongEnv(unittest.TestCase):
    def setUp(self):
        self.env = MahjongEnv()

    def test_initialization(self):
        self.assertEqual(len(self.env.players), 4)
        for player in self.env.players:
            self.assertEqual(len(player.hand), 13)
        # 親は14枚
        self.assertEqual(len(self.env.players[0].hand), 14)
        self.assertEqual(self.env.current_player_id, 0)
        self.assertEqual(len(self.env.deck.tiles), 136 - 13 * 4 - 1 - 1) # 山 - 配牌 - ドラ - 親のツモ

    def test_discard_action(self):
        player = self.env.players[0]
        initial_hand_size = len(player.hand)
        tile_to_discard = player.hand[0]
        
        self.env.step(("discard", tile_to_discard))
        
        self.assertEqual(len(player.hand), initial_hand_size - 1)
        self.assertIn(tile_to_discard, player.discards)
        self.assertEqual(self.env.current_player_id, 1)

    def test_ryukyoku_tenpai_settlement(self):
        """流局時に聴牌者と不聴者の間で点数が正しく精算されるかテスト"""
        # プレイヤー0: 形式聴牌 (役なし、待ち2z)
        # 123m 456p 789s 11z 2z (手牌) + 2z (ツモ牌)
        tenpai_hand = TilesConverter.from_string(m="123", p="456", s="789", z="1122")
        self.env.players[0].hand = tenpai_hand

        # プレイヤー1: 不聴
        noten_hand = TilesConverter.from_string(m="111", p="222", s="333", z="4455")
        self.env.players[1].hand = noten_hand
        
        # プレイヤー2: 聴牌
        tenpai_hand_2 = TilesConverter.from_string(m="234", p="567", s="89", z="33366")
        self.env.players[2].hand = tenpai_hand_2
        
        # プレイヤー3: 不聴
        noten_hand_2 = TilesConverter.from_string(m="123456789", p="123", s="1")
        self.env.players[3].hand = noten_hand_2
        
        # 初期スコアを記録
        initial_scores = [p.score for p in self.env.players]

        # 流局処理を直接呼び出す
        self.env._handle_ryukyoku()

        # 点数移動の確認
        # 聴牌者2人、不聴者2人 -> 3000点移動
        # 不聴者はそれぞれ-1500点
        # 聴牌者はそれぞれ+1500点
        self.assertEqual(self.env.players[0].score, initial_scores[0] + 1500)
        self.assertEqual(self.env.players[1].score, initial_scores[1] - 1500)
        self.assertEqual(self.env.players[2].score, initial_scores[2] + 1500)
        self.assertEqual(self.env.players[3].score, initial_scores[3] - 1500)
        
        self.assertTrue(self.env.game_over)

if __name__ == '__main__':
    unittest.main()
