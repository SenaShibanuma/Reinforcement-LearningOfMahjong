import numpy as np
from mahjong.shanten import Shanten
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig  # 修正: GameRoundConfigを削除
from mahjong.tile import TilesConverter
from mahjong.meld import Meld
from .deck import Deck
from ..constants import Constants

class Player:
    def __init__(self, player_id):
        self.player_id = player_id
        self.hand = []  # 136形式の牌
        self.discards = []
        self.melds = []  # 副露
        self.riichi = False
        self.score = 25000

    def draw(self, tile):
        self.hand.append(tile)
        self.hand.sort()

    def discard(self, tile):
        self.hand.remove(tile)
        self.discards.append(tile)
        return tile
    
    def to_dict(self):
        return {
            "player_id": self.player_id,
            "hand": self.hand,
            "discards": self.discards,
            "melds": [
                {
                    "type": meld.type,
                    "tiles": meld.tiles,
                    "opened": meld.opened,
                    "who": meld.who,
                    "from_who": meld.from_who,
                    "is_concealed": meld.is_concealed
                } for meld in self.melds
            ],
            "riichi": self.riichi,
            "score": self.score
        }

class MahjongEnv:
    def __init__(self):
        self.shanten_calculator = Shanten()
        self.calculator = HandCalculator()
        self.reset()

    def reset(self):
        self.deck = Deck()
        self.players = [Player(i) for i in range(4)]
        self.current_player_id = 0
        self.turn = 0
        self.dora_indicators = [self.deck.draw()]
        self.ura_dora_indicators = []
        self.game_over = False
        self.game_log = []

        # 配牌
        for _ in range(13):
            for player in self.players:
                player.draw(self.deck.draw())
        
        # 初期ツモ
        self.players[self.current_player_id].draw(self.deck.draw())
        
        return self._get_state()

    def step(self, action):
        """
        アクションを実行し、環境を1ステップ進める
        action: (action_type, tile)
        action_type: "discard", "chi", "pon", "kan", "riichi", "tsumo"
        """
        player = self.players[self.current_player_id]
        action_type, tile = action

        reward = 0
        done = False

        if action_type == "discard":
            player.discard(tile)
            
            # 他のプレイヤーが和了できるかチェック
            for other_player in self.players:
                if other_player.player_id != self.current_player_id:
                    win_result = self._check_win(other_player, tile, is_tsumo=False)
                    if win_result:
                        # ロン和了処理
                        reward = self._handle_win(win_result, other_player, from_player=player)
                        done = True
                        self.game_over = True
                        return self._get_state(), reward, done, {}
            
            # 次のプレイヤーへ
            self.current_player_id = (self.current_player_id + 1) % 4
            if not self.deck.is_empty():
                 self.players[self.current_player_id].draw(self.deck.draw())
            else:
                reward = self._handle_ryukyoku()
                done = True

        # TODO: その他のアクション（チー、ポン、カンなど）を実装

        if self.deck.is_empty():
            reward = self._handle_ryukyoku()
            done = True

        self.turn += 1
        
        return self._get_state(), reward, done, {}

    def _get_state(self):
        """現在のゲーム状態を返す"""
        state = {
            "players": [p.to_dict() for p in self.players],
            "current_player_id": self.current_player_id,
            "deck_size": len(self.deck.tiles),
            "dora_indicators": self.dora_indicators,
            "turn": self.turn
        }
        return state

    def _check_win(self, player, win_tile, is_tsumo=True):
        """和了判定を行う"""
        tiles = TilesConverter.to_34_array(player.hand)
        
        # shanten数が-1（和了）でなければNoneを返す
        shanten = self.shanten_calculator.calculate_shanten(tiles, closed_hand=True)
        if shanten != -1:
            return None
        
        # 修正: HandConfigをここで生成する
        config = HandConfig(
            is_tsumo=is_tsumo,
            aka_dora_enabled=True  # 赤ドラを有効にする
        )

        # HandCalculatorで役と点数を計算
        result = self.calculator.estimate_hand_value(
            player.hand,
            win_tile,
            config=config
        )

        # 役がなければ和了ではない
        if result.error:
            return None

        return result
    
    def _handle_win(self, result, winner, from_player=None):
        """和了処理"""
        score = result.cost['main'] + result.cost['additional']
        if from_player:  # ロン
            from_player.score -= score
            winner.score += score
        else:  # ツモ
            # TODO: 点数移動を実装
            pass
        
        self.game_over = True
        return score

    def _handle_ryukyoku(self):
        """流局処理（荒牌平局）"""
        tenpai_players = []
        noten_players = []

        for p in self.players:
            tiles_34 = TilesConverter.to_34_array(p.hand)
            melds_34 = [TilesConverter.to_34_array(meld.tiles) for meld in p.melds]

            # 副露を考慮したシャンテン数を計算
            shanten = self.shanten_calculator.calculate_shanten(tiles_34, melds=melds_34)
            
            # シャンテン数が0以下（聴牌）か判定
            if shanten <= 0:
                tenpai_players.append(p)
            else:
                noten_players.append(p)

        # 不聴罰符の精算
        num_tenpai = len(tenpai_players)
        num_noten = len(noten_players)

        # 全員聴牌または全員不聴の場合は点数移動なし
        if num_tenpai == 0 or num_tenpai == 4:
            return 0
        
        # 役満払いなどの特殊なケースは未実装
        payment_per_noten = Constants.NOTEN_BAPPU / num_noten
        reward_per_tenpai = Constants.NOTEN_BAPPU / num_tenpai

        for p in noten_players:
            p.score -= payment_per_noten
        
        for p in tenpai_players:
            p.score += reward_per_tenpai

        self.game_over = True
        return 0 # 流局自体の報酬は0とする

    def render(self):
        """現在のゲーム状態をコンソールに表示"""
        state = self._get_state()
        print(f"--- Turn {state['turn']}, Current Player: {state['current_player_id']} ---")
        print(f"Deck: {state['deck_size']} tiles left")
        print(f"Dora Indicators: {TilesConverter.to_one_line_string(state['dora_indicators'])}")
        
        for p in state['players']:
            hand_str = TilesConverter.to_one_line_string(p['hand'])
            discard_str = TilesConverter.to_one_line_string(p['discards'])
            melds_str = ", ".join([Meld.to_str(m) for m in p['melds']])
            print(f"Player {p['player_id']} (Score: {p['score']})")
            print(f"  Hand: {hand_str}")
            if melds_str:
                print(f"  Melds: {melds_str}")
            print(f"  Discards: {discard_str}")
        print("-" * 20)

