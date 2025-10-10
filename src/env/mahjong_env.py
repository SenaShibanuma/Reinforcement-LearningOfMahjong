# -*- coding: utf-8 -*-
"""
麻雀のルールと状態遷移を管理する「環境」クラス。
強化学習の標準的なインターフェース（reset, stepなど）を持つ。
"""
import random
import json
from .deck import Deck
from mahjong.tile import TilesConverter
from mahjong.shanten import Shanten
from mahjong.meld import Meld
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.constants import EAST
import numpy as np


class MahjongEnv:
    """
    麻雀のゲーム環境をシミュレートするクラス。
    """

    def __init__(self, agents, rules=None, config=None):
        """
        環境を初期化する。
        
        Args:
            agents (list): 対戦に参加するエージェントのリスト
            rules (dict, optional): カスタムルール設定. Defaults to None.
            config (dict, optional): 外部設定ファイルからの設定. Defaults to None.
        """
        self.agents = agents
        self.num_players = len(agents)
        self.game_state = {}
        self.shanten_calculator = Shanten()
        self.hand_calculator = HandCalculator()

        self.config = config or {}

        # デフォルトルールを設定し、引数で渡されたもので上書きする
        self.rules = {
            'has_aka_dora': True,
            'has_open_tanyao': True,
            'has_double_yakuman': True
        }
        if rules:
            self.rules.update(rules)
        
        self.num_rounds = self.config.get('game', {}).get('num_rounds', 8)
        print(
            f"MahjongEnv: Initialized for {self.num_rounds}-round game with rules: {self.rules}"
        )

    def _is_yaochuhai(self, tile_136):
        """牌が么九牌（ヤオチュウハイ）かどうかを判定する"""
        tile_34 = tile_136 // 4
        is_jihai = tile_34 >= 27
        is_terminal = (tile_34 % 9 == 0) or (tile_34 % 9 == 8)
        return is_jihai or is_terminal

    def _deal(self):
        """
        牌をシャッフルし、各プレイヤーに配る。
        """
        deck = Deck(rules=self.rules)

        self.game_state['wall'] = deck.tiles[:-14]
        self.game_state['dead_wall'] = deck.tiles[-14:]

        self.game_state['dora_indicators'] = [self.game_state['dead_wall'][4]]
        self.game_state['kan_count'] = 0

        hands = [[] for _ in range(self.num_players)]
        for i in range(13):
            for player_idx in range(self.num_players):
                hands[player_idx].append(self.game_state['wall'].pop(0))

        for player_idx in range(self.num_players):
            hands[player_idx] = sorted(hands[player_idx])

        self.game_state['hands'] = hands

    def _calculate_agari_result(self, player_idx, tile, is_tsumo,
                                dora_indicators):
        """アガリ点数を計算して結果を返す"""
        hand_136 = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]
        full_hand = hand_136 if is_tsumo else hand_136 + [tile]

        config = HandConfig(
            is_tsumo=is_tsumo,
            is_riichi=self.game_state['is_riichi'][player_idx],
            is_ippatsu=self.game_state['is_ippatsu_chance'][player_idx],
            is_rinshan=self.game_state['is_rinshan_chance'][player_idx]
            if is_tsumo else False,
            is_chankan=self.game_state.get('is_chankan_chance', False),
            is_haitei=(len(self.game_state['wall']) == 0),
            player_wind=EAST + ((player_idx - self.game_state['oya_player_id'] +
                                 self.num_players) % self.num_players),
            round_wind=EAST + self.game_state['round'] // self.num_players,
            options=OptionalRules(
                has_open_tanyao=self.rules['has_open_tanyao'],
                has_aka_dora=self.rules['has_aka_dora'],
                has_double_yakuman=self.rules['has_double_yakuman']))

        try:
            return self.hand_calculator.estimate_hand_value(
                tiles=full_hand,
                win_tile=tile,
                melds=melds,
                dora_indicators=dora_indicators,
                config=config)
        except: # mahjongライブラリが稀に例外を出すことがあるため
            return None

    def _calculate_shanten(self, hand_136, melds):
        """
        手牌とMeldオブジェクトのリストから正確なシャンテン数を計算するヘルパー。
        """
        hand_34 = TilesConverter.to_34_array(hand_136)
        
        # --- START: FINAL FIX ---
        # すべての副露を単一のリスト `open_sets_34` にまとめる
        open_sets = []
        for meld in melds:
            open_sets.append(sorted([t // 4 for t in meld.tiles]))

        try:
            # ライブラリの正しい引数名 `open_sets_34` を使って関数を呼び出す
            return self.shanten_calculator.calculate_shanten(
                hand_34, 
                open_sets_34=open_sets
            )
        # --- END: FINAL FIX ---
        except Exception:
            return 9 # Calculation error

    def _is_agari_shape(self, hand_136, melds):
        """
        手牌が4面子1雀頭の和了形になっているか、ライブラリを使って判定する。
        """
        # A completed hand has a shanten of -1
        return self._calculate_shanten(hand_136, melds) == -1

    def _can_agari(self, player_idx, tile, is_tsumo):
        """
        指定された牌でアガれるか判定する。
        海底・河底・槍槓・嶺上開花など、手牌に役がなくても成立する役も考慮する。
        """
        hand_136 = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]
        
        full_hand = hand_136 + [tile]

        # 1. そもそもアガリ形か？ (ライブラリが判定)
        if not self._is_agari_shape(full_hand, melds):
            return False

        # 2. 状況役だけでアガれるか？
        is_haitei = len(self.game_state['wall']) == 0
        is_chankan = not is_tsumo and self.game_state.get('is_chankan_chance', False)
        is_rinshan = is_tsumo and self.game_state['is_rinshan_chance'][player_idx]
        
        if is_haitei or is_chankan or is_rinshan:
            return True

        # 3. 手牌に役があるか？
        result = self._calculate_agari_result(
            player_idx, tile, is_tsumo, self.game_state['dora_indicators'])
        
        return result is not None and result.error is None
    
    def _get_waiting_tiles(self, player_idx):
        """
        プレイヤーの待ち牌（アガリ牌）のリストを返す。役がなければ空リストを返す。
        Returns:
            list: 待ち牌の34種IDのリスト
        """
        hand_136 = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]
        
        shanten = self._calculate_shanten(hand_136, melds)
        if shanten > 0:
            return []

        waiting_tiles = []
        hand_34 = TilesConverter.to_34_array(hand_136)
        for tile_34 in range(34):
            if hand_34[tile_34] == 4:
                continue
            
            if self._can_agari(player_idx, tile_34 * 4, is_tsumo=False):
                waiting_tiles.append(tile_34)
        
        return waiting_tiles

    def _is_furiten(self, player_idx, waiting_tiles):
        """
        指定された待ち牌でフリテンかどうかを判定する。
        """
        if not waiting_tiles:
            return False

        river_34 = {tile // 4 for tile in self.game_state['rivers'][player_idx]}
        
        for wait in waiting_tiles:
            if wait in river_34:
                return True
        return False

    def _is_yakuari_tenpai(self, player_idx):
        """
        プレイヤーが役あり聴牌（リーチやロンが可能）か判定する。
        """
        return len(self._get_waiting_tiles(player_idx)) > 0

    def _is_keishiki_tenpai(self, player_idx):
        """
        プレイヤーが形式聴牌しているか判定する。
        """
        hand_136 = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]
        return self._calculate_shanten(hand_136, melds) == 0

    def _check_kyuushu_kyuuhai(self, hand_136):
        """手牌が九種九牌の条件を満たすかチェックする"""
        unique_yaochuhai = set()
        for tile in hand_136:
            if self._is_yaochuhai(tile):
                unique_yaochuhai.add(tile // 4)
        return len(unique_yaochuhai) >= 9

    def _get_my_turn_actions(self, player_idx):
        """
        手番のプレイヤーが可能な行動のリストを生成する。
        """
        actions = []
        hand_136 = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]

        if self.game_state['turn_count'] < self.num_players and not any(
                player_melds for player_melds in self.game_state['melds']):
            if self._check_kyuushu_kyuuhai(hand_136):
                actions.append("ACTION_KYUUSHU_KYUUHAI")

        last_drawn_tile = self.game_state.get('last_drawn_tile')
        if last_drawn_tile is not None:
            if self._can_agari(player_idx, last_drawn_tile, is_tsumo=True):
                actions.append("ACTION_TSUMO")
        
        temp_hand_for_discard = hand_136[:]
        if last_drawn_tile is not None:
            temp_hand_for_discard.append(last_drawn_tile)

        unique_tiles_136 = sorted(list(set(temp_hand_for_discard)))
        for tile in unique_tiles_136:
            actions.append(f"DISCARD_{tile}")

        if self.game_state['wall']:
            hand_34 = TilesConverter.to_34_array(temp_hand_for_discard)
            for tile_34, count in enumerate(hand_34):
                if count == 4:
                    actions.append(f"ACTION_ANKAN_{tile_34*4}")

            if last_drawn_tile is not None:
                for meld in melds:
                    if meld.type == Meld.PON and meld.tiles[
                            0] // 4 == last_drawn_tile // 4:
                        actions.append(f"ACTION_KAKAN_{last_drawn_tile}")

        is_menzen = not any(meld.opened for meld in melds)

        if not self.game_state['is_riichi'][player_idx] and is_menzen:
            if self._is_yakuari_tenpai(player_idx):
                for tile_to_discard in unique_tiles_136:
                    temp_hand = temp_hand_for_discard[:]
                    temp_hand.remove(tile_to_discard)
                    
                    if self._calculate_shanten(temp_hand, melds) == 0:
                        actions.append(f"ACTION_RIICHI_{tile_to_discard}")
        
        return list(dict.fromkeys(actions))

    def _get_opponent_turn_actions(self, player_idx, discarded_tile):
        """
        他家の捨て牌に対して可能な行動のリストを生成する。
        """
        actions = ["ACTION_PASS"]

        can_ron = self._can_agari(player_idx, discarded_tile, is_tsumo=False)
        
        if can_ron:
            waiting_tiles = self._get_waiting_tiles(player_idx)
            is_player_furiten = self._is_furiten(player_idx, waiting_tiles)
            
            if not is_player_furiten:
                actions.append("ACTION_RON")
            else:
                print(f"  -> Player {player_idx} is in furiten. Cannot ron.")

        if not self.game_state['is_riichi'][player_idx]:
            hand_136 = self.game_state['hands'][player_idx]
            hand_34 = TilesConverter.to_34_array(hand_136)
            discarded_tile_34 = discarded_tile // 4

            if hand_34[discarded_tile_34] >= 2:
                actions.append("ACTION_PUNG")

            if self.game_state['wall'] and hand_34[discarded_tile_34] >= 3:
                actions.append("ACTION_DAIMINKAN")

            discarder_idx = self.game_state['last_discarder']
            is_kamicha = (discarder_idx + 1) % self.num_players == player_idx
            
            if is_kamicha and discarded_tile_34 < 27:
                tile_number = discarded_tile_34 % 9
                if tile_number >= 2 and hand_34[discarded_tile_34 - 2] > 0 and hand_34[discarded_tile_34 - 1] > 0:
                    actions.append(f"ACTION_CHII_{discarded_tile_34 - 2}_{discarded_tile_34 - 1}")
                if 1 <= tile_number <= 7 and hand_34[discarded_tile_34 - 1] > 0 and hand_34[discarded_tile_34 + 1] > 0:
                    actions.append(f"ACTION_CHII_{discarded_tile_34 - 1}_{discarded_tile_34 + 1}")
                if tile_number <= 6 and hand_34[discarded_tile_34 + 1] > 0 and hand_34[discarded_tile_34 + 2] > 0:
                    actions.append(f"ACTION_CHII_{discarded_tile_34 + 1}_{discarded_tile_34 + 2}")

        return list(dict.fromkeys(actions))

    def reset(self, initial_state=None):
        """
        環境をリセットし、局の開始準備を行う。
        """
        if initial_state:
            self.game_state = initial_state
        else:
            self.game_state = {
                'round': 0,
                'honba': 0,
                'riichi_sticks': 0,
                'scores': [25000] * self.num_players,
                'oya_player_id': 0
            }

        self.game_state.update({
            'turn_count': 0,
            'is_riichi': [False] * self.num_players,
            'is_ippatsu_chance': [False] * self.num_players,
            'is_rinshan_chance': [False] * self.num_players,
            'is_chankan_chance': False,
            'pending_kakan_player': -1,
            'events': [],
            'last_discarder': -1,
            'last_drawn_tile': None,
            'melds': [[] for _ in range(self.num_players)],
            'rivers': [[] for _ in range(self.num_players)],
            'can_nagashi': [True] * self.num_players,
            'first_turn_discards': [None] * self.num_players,
            'kan_makers': [],
            'pao_info': {
                'pao_player': -1,
                'responsible_for': -1
            },
            'agari_stats': []
        })

        self.current_player_idx = self.game_state['oya_player_id']
        self.game_phase = 'DISCARD'

        self._deal()

        drawn_tile = self.game_state['wall'].pop(0)
        self.game_state['last_drawn_tile'] = drawn_tile
        
        initial_event = {
            'event_id': 'INIT',
            'scores': self.game_state['scores'],
            'dora_indicator': self.game_state['dora_indicators'][0],
            'rules': self.rules
        }
        self.game_state['events'].append(initial_event)

        choices = self._get_my_turn_actions(self.current_player_idx)
        return (self.game_state['events'], choices)

    def step(self, action):
        """
        指定されたアクションを実行し、環境を1ステップ進める。
        """
        if self.game_phase == 'DISCARD' and self.game_state['last_drawn_tile'] is not None:
            self.game_state['hands'][self.current_player_idx].append(self.game_state['last_drawn_tile'])
            self.game_state['hands'][self.current_player_idx].sort()

        if self.game_phase == 'DISCARD':
            return self._handle_discard_phase(action)
        elif self.game_phase == 'CALL':
            return self._handle_call_phase(action)
        else:
            raise ValueError(f"Unknown game phase: {self.game_phase}")

    def _handle_discard_phase(self, action):
        """DISCARDフェーズのアクションを処理する"""
        if action == 'ACTION_TSUMO':
            return self._process_agari(is_tsumo=True)
        if action == 'ACTION_KYUUSHU_KYUUHAI':
            return self._process_abortive_draw(reason='kyuushu_kyuuhai')

        self.game_state['is_rinshan_chance'] = [False] * self.num_players
        self.game_state['is_chankan_chance'] = False

        action_parts = action.split('_')
        action_type = action_parts[0]

        if action_type == 'ACTION' and action_parts[1] == 'ANKAN':
            tile = int(action_parts[2])
            return self._perform_kan('ankan', tile)
        elif action_type == 'ACTION' and action_parts[1] == 'KAKAN':
            tile = int(action_parts[2])
            self.game_state['is_chankan_chance'] = True
            self.game_state['last_discarded_tile'] = tile
            self.game_state['last_discarder'] = self.current_player_idx
            self.game_state['pending_kakan_player'] = self.current_player_idx

            self.game_phase = 'CALL'
            self.call_check_player_idx = (self.current_player_idx +
                                          1) % self.num_players
            self.call_checked_count = 0
            return self._check_next_opponent_call()

        player_hand = self.game_state['hands'][self.current_player_idx]
        if action_type == 'ACTION' and action_parts[1] == 'RIICHI':
            self.game_state['is_riichi'][self.current_player_idx] = True
            self.game_state['is_ippatsu_chance'][
                self.current_player_idx] = True
            self.game_state['scores'][self.current_player_idx] -= 1000
            self.game_state['riichi_sticks'] += 1

            tile_to_discard = int(action_parts[2])
            player_hand.remove(tile_to_discard)
        elif action_type == 'DISCARD':
            tile_to_discard = int(action_parts[1])
            player_hand.remove(tile_to_discard)
        else:
            raise ValueError(f"Invalid action in DISCARD phase: {action}")

        self.game_state['last_drawn_tile'] = None

        self.game_state['rivers'][self.current_player_idx].append(
            tile_to_discard)
        self.game_state['events'].append({
            'event_id': 'DISCARD',
            'player': self.current_player_idx,
            'tile': tile_to_discard
        })
        self.game_state['last_discarded_tile'] = tile_to_discard
        self.game_state['last_discarder'] = self.current_player_idx

        if self.game_state['turn_count'] < self.num_players:
            if self.game_state['first_turn_discards'][self.current_player_idx] is None:
                self.game_state['first_turn_discards'][self.current_player_idx] = tile_to_discard

            if all(d is not None for d in self.game_state['first_turn_discards']):
                first_discard_34 = self.game_state['first_turn_discards'][0] // 4
                is_wind = 27 <= first_discard_34 <= 30
                if is_wind and all(d // 4 == first_discard_34 for d in self.game_state['first_turn_discards']):
                    return self._process_abortive_draw('suufuu_renda')

        self.game_phase = 'CALL'
        self.call_check_player_idx = (self.current_player_idx +
                                      1) % self.num_players
        self.call_checked_count = 0
        return self._check_next_opponent_call()

    def _handle_call_phase(self, action):
        """CALLフェーズのアクションを処理する"""
        if action == 'ACTION_RON':
            return self._process_agari(is_tsumo=False)

        action_parts = action.split('_')
        action_type = action_parts[1]
        if action_type == 'PUNG':
            return self._perform_pung()
        elif action_type == 'DAIMINKAN':
            return self._perform_kan('daiminkan')
        elif action_type == 'CHII':
            tile1_base = int(action_parts[2])
            tile2_base = int(action_parts[3])
            return self._perform_chii(tile1_base, tile2_base)
        elif action_type == 'PASS':
            return self._process_pass()
        else:
            raise ValueError(f"Invalid action in CALL phase: {action}")

    def _check_for_pao(self, melder_idx):
        """鳴きによってパオが成立したかチェックする"""
        melds = self.game_state['melds'][melder_idx]

        dragon_melds = 0
        dragon_tiles_34 = [31, 32, 33]
        for meld in melds:
            if not meld.opened: continue
            meld_tile_34 = meld.tiles[0] // 4
            if meld_tile_34 in dragon_tiles_34:
                dragon_melds += 1

        if dragon_melds == 3:
            pao_player = self.game_state['last_discarder']
            print(
                f"  -> PAO! Player {pao_player} is responsible for Player {melder_idx}'s Daisangen."
            )
            self.game_state['pao_info'] = {
                'pao_player': pao_player,
                'responsible_for': melder_idx
            }

    def _process_agari(self, is_tsumo):
        """アガリ処理（点数計算とスコア更新）"""
        winner_idx = self.current_player_idx
        win_tile = self.game_state[
            'last_drawn_tile'] if is_tsumo else self.game_state[
                'last_discarded_tile']

        pao_player = self.game_state['pao_info']['pao_player']
        responsible_for = self.game_state['pao_info']['responsible_for']
        is_pao_agari = (pao_player != -1 and winner_idx == responsible_for)

        rewards = [0] * self.num_players
        result = None

        if is_pao_agari:
            is_oya = winner_idx == self.game_state['oya_player_id']
            yakuman_value = 48000 if is_oya else 32000
            print(f"  -> PAO AGARI! Value: {yakuman_value}")
            total_cost = yakuman_value
        else:
            final_dora_indicators = self.game_state['dora_indicators'][:]
            if self.game_state['is_riichi'][winner_idx]:
                for i in range(1 + self.game_state['kan_count']):
                    ura_dora_indicator = self.game_state['dead_wall'][5 + i]
                    final_dora_indicators.append(ura_dora_indicator)

            result = self._calculate_agari_result(winner_idx, win_tile,
                                                  is_tsumo,
                                                  final_dora_indicators)

            if result is None or result.error:
                return (self.game_state['events'], []), [0] * self.num_players, True, {
                    'reason':
                    f'agari_error: {result.error if result else "None"}',
                    'game_over':
                    True
                }

            total_cost = result.cost['main'] + result.cost['additional']

        if is_pao_agari:
            if is_tsumo:
                self.game_state['scores'][pao_player] -= total_cost
                rewards[pao_player] = -total_cost
            else:
                loser_idx = self.game_state['last_discarder']
                if loser_idx == pao_player:
                    self.game_state['scores'][loser_idx] -= total_cost
                    rewards[loser_idx] = -total_cost
                else:
                    payment = total_cost // 2
                    self.game_state['scores'][pao_player] -= payment
                    self.game_state['scores'][loser_idx] -= payment
                    rewards[pao_player] = -payment
                    rewards[loser_idx] = -payment
        else:
            if is_tsumo:
                oya_payment = result.cost['main'] if result else 0
                ko_payment = result.cost['additional'] if result else 0
                for i in range(self.num_players):
                    if i == winner_idx: continue
                    payment = oya_payment if winner_idx == self.game_state['oya_player_id'] else (
                        oya_payment if i == self.game_state['oya_player_id'] else ko_payment
                    )
                    self.game_state['scores'][i] -= payment
                    rewards[i] = -payment
            else:
                loser_idx = self.game_state['last_discarder']
                self.game_state['scores'][loser_idx] -= total_cost
                rewards[loser_idx] = -total_cost

        riichi_bonus = self.game_state['riichi_sticks'] * 1000
        honba_bonus = self.game_state['honba'] * 300
        self.game_state['scores'][winner_idx] += total_cost + riichi_bonus + honba_bonus
        rewards[winner_idx] += total_cost + riichi_bonus + honba_bonus
        self.game_state['riichi_sticks'] = 0

        if result:
            dora_count = sum(y.han_closed or y.han_opened or 0 for y in result.yaku if 'Dora' in y.name)
            stat = { 'winner': winner_idx, 'is_tsumo': is_tsumo, 'han': result.han, 'fu': result.fu, 'cost': total_cost, 'yaku': [y.name for y in result.yaku], 'dora': dora_count }
            self.game_state['agari_stats'].append(stat)

        self.game_state['events'].append({ 'event_id': 'AGARI', 'winner': winner_idx, 'hand_value': total_cost })

        if winner_idx == self.game_state['oya_player_id']:
            self.game_state['honba'] += 1
        else:
            self.game_state['honba'] = 0
            self.game_state['round'] += 1
            self.game_state['oya_player_id'] = (self.game_state['oya_player_id'] + 1) % self.num_players

        game_over = self.game_state['round'] >= self.num_rounds or any(s < 0 for s in self.game_state['scores'])
        if any(s < 0 for s in self.game_state['scores']):
            print("  -> A player's score is below zero. Game ends (Tobi).")
        
        return (self.game_state['events'], []), rewards, True, { 'reason': 'agari', 'game_over': game_over }

    def _perform_pung(self):
        self.game_state['is_ippatsu_chance'] = [False] * self.num_players
        self.game_state['can_nagashi'][self.game_state['last_discarder']] = False
        caller_idx = self.current_player_idx
        discarded_tile = self.game_state['last_discarded_tile']
        discarded_tile_34 = discarded_tile // 4
        hand = self.game_state['hands'][caller_idx]
        tiles_to_remove = [t for t in hand if t // 4 == discarded_tile_34][:2]
        for tile in tiles_to_remove:
            hand.remove(tile)

        meld = Meld(Meld.PON, tiles=sorted(tiles_to_remove + [discarded_tile]), opened=True)
        self.game_state['melds'][caller_idx].append(meld)
        self.game_state['events'].append({ 'event_id': 'MELD', 'player': caller_idx, 'meld_info': 'pung' })
        self._check_for_pao(caller_idx)
        self.game_phase = 'DISCARD'
        self.game_state['last_drawn_tile'] = None
        choices = self._get_my_turn_actions(caller_idx)
        return (self.game_state['events'], choices), [0] * self.num_players, False, {}

    def _perform_chii(self, tile1_base, tile2_base):
        self.game_state['is_ippatsu_chance'] = [False] * self.num_players
        self.game_state['can_nagashi'][self.game_state['last_discarder']] = False
        caller_idx = self.current_player_idx
        discarded_tile = self.game_state['last_discarded_tile']
        hand = self.game_state['hands'][caller_idx]
        tile1_to_remove = next((t for t in hand if t // 4 == tile1_base), None)
        tile2_to_remove = next((t for t in hand if t // 4 == tile2_base), None)
        if tile1_to_remove: hand.remove(tile1_to_remove)
        if tile2_to_remove: hand.remove(tile2_to_remove)
        meld = Meld(Meld.CHI, tiles=sorted([tile1_to_remove, tile2_to_remove, discarded_tile]), opened=True)
        self.game_state['melds'][caller_idx].append(meld)
        self.game_state['events'].append({ 'event_id': 'MELD', 'player': caller_idx, 'meld_info': 'chii' })
        self.game_phase = 'DISCARD'
        self.game_state['last_drawn_tile'] = None
        choices = self._get_my_turn_actions(caller_idx)
        return (self.game_state['events'], choices), [0] * self.num_players, False, {}

    def _perform_kan(self, kan_type, tile=None):
        if kan_type != 'ankan':
            self.game_state['is_ippatsu_chance'] = [False] * self.num_players
            if kan_type == 'daiminkan':
                self.game_state['can_nagashi'][self.game_state['last_discarder']] = False
        caller_idx = self.current_player_idx
        hand = self.game_state['hands'][caller_idx]
        tile_34 = (tile or self.game_state['last_discarded_tile']) // 4
        
        if kan_type == 'daiminkan':
            tiles_to_remove = [t for t in hand if t // 4 == tile_34]
            meld_tiles = tiles_to_remove + [self.game_state['last_discarded_tile']]
            for t in tiles_to_remove: hand.remove(t)
            meld = Meld(Meld.KAN, tiles=sorted(meld_tiles), opened=True)
            self.game_state['melds'][caller_idx].append(meld)
            self._check_for_pao(caller_idx)
        elif kan_type == 'ankan':
            tiles_to_remove = [t for t in hand if t // 4 == tile_34]
            for t in tiles_to_remove: hand.remove(t)
            meld = Meld(Meld.KAN, tiles=sorted(tiles_to_remove), opened=False)
            self.game_state['melds'][caller_idx].append(meld)
        elif kan_type == 'kakan':
            hand.remove(tile)
            original_pon = next((m for m in self.game_state['melds'][caller_idx] if m.type == Meld.PON and m.tiles[0] // 4 == tile_34), None)
            if original_pon:
                self.game_state['melds'][caller_idx].remove(original_pon)
                new_kan_tiles = original_pon.tiles + [tile]
                meld = Meld(Meld.KAN, tiles=sorted(new_kan_tiles), opened=True)
                self.game_state['melds'][caller_idx].append(meld)

        self.game_state['kan_makers'].append(caller_idx)
        if len(self.game_state['kan_makers']) == 4 and len(set(self.game_state['kan_makers'])) > 1:
            return self._process_abortive_draw('suukansanra')

        self.game_state['is_rinshan_chance'][caller_idx] = True
        rinshan_tile = self.game_state['dead_wall'].pop(0)
        
        self.game_state['last_drawn_tile'] = rinshan_tile
        if self.game_state['wall']:
            self.game_state['dead_wall'].append(self.game_state['wall'].pop())
        self.game_state['kan_count'] += 1
        new_dora_indicator = self.game_state['dead_wall'][4 + self.game_state['kan_count']]
        self.game_state['dora_indicators'].append(new_dora_indicator)
        self.game_state['events'].append({ 'event_id': 'MELD', 'type': 'kan', 'player': caller_idx })
        self.game_phase = 'DISCARD'
        choices = self._get_my_turn_actions(caller_idx)
        return (self.game_state['events'], choices), [0] * self.num_players, False, {}

    def _process_ryuukyoku(self, reason='ryuukyoku'):
        print(f"  -> Wall is empty. Processing Ryuukyoku (draw reason: {reason}).")
        self.game_state['events'].append({ 'event_id': 'RYUUKYOKU', 'reason': reason })
        rewards = [0] * self.num_players
        
        nagashi_winners = []
        if reason == 'ryuukyoku':
            nagashi_winners = [i for i, river in enumerate(self.game_state['rivers']) if self.game_state['can_nagashi'][i] and all(self._is_yaochuhai(t) for t in river)]
        
        if nagashi_winners:
            print(f"  -> Nagashi Mangan achieved by player(s): {nagashi_winners}")
            # ... (Nagashi Mangan point transfer logic)
        else:
            tenpai_players = [i for i in range(self.num_players) if self._is_keishiki_tenpai(i)]
            noten_players = [i for i in range(self.num_players) if i not in tenpai_players]
            num_tenpai = len(tenpai_players)
            print(f"  -> Tenpai players: {tenpai_players}")
            print(f"  -> Noten players: {noten_players}")
            if 0 < num_tenpai < self.num_players:
                payments = {1: (3000, 1000), 2: (1500, 1500), 3: (1000, 3000)}
                receipt, payment = payments[num_tenpai]
                print(f"  -> Point transfer: Tenpai get {receipt}, Noten pay {payment}.")
                for i in range(self.num_players):
                    if i in tenpai_players:
                        self.game_state['scores'][i] += receipt
                        rewards[i] += receipt
                    else:
                        self.game_state['scores'][i] -= payment
                        rewards[i] -= payment
            else:
                print("  -> No point transfer.")

        oya_in_tenpai = self.game_state['oya_player_id'] in tenpai_players or self.game_state['oya_player_id'] in nagashi_winners
        if oya_in_tenpai:
            self.game_state['honba'] += 1
            print(f"  -> Oya ({self.game_state['oya_player_id']}) is tenpai. Oya renchan. Honba is now {self.game_state['honba']}.")
        else:
            self.game_state['honba'] = 0
            self.game_state['round'] += 1
            self.game_state['oya_player_id'] = (self.game_state['oya_player_id'] + 1) % self.num_players
            print(f"  -> Oya is noten. Oya nagare. Next round is {self.game_state['round']}, new Oya is {self.game_state['oya_player_id']}.")
        
        game_over = self.game_state['round'] >= self.num_rounds or any(s < 0 for s in self.game_state['scores'])
        return (self.game_state['events'], []), rewards, True, { 'reason': reason, 'game_over': game_over }

    def _process_abortive_draw(self, reason):
        print(f"  -> Abortive draw due to {reason}.")
        self.game_state['honba'] += 1
        self.game_state['events'].append({ 'event_id': 'RYUUKYOKU', 'reason': reason })
        return (self.game_state['events'], []), [0] * self.num_players, True, { 'reason': reason, 'game_over': False }

    def _process_pass(self):
        self.call_checked_count += 1
        if self.call_checked_count < self.num_players - 1:
            self.call_check_player_idx = (self.call_check_player_idx + 1) % self.num_players
            if self.call_check_player_idx == self.game_state['last_discarder']:
                self.call_check_player_idx = (self.call_check_player_idx + 1) % self.num_players
            return self._check_next_opponent_call()
        
        # All players passed
        if all(self.game_state['is_riichi']):
            return self._process_ryuukyoku(reason='suucha_riichi')

        if self.game_state['is_chankan_chance']:
            self.game_state['is_chankan_chance'] = False
            kakan_player = self.game_state['pending_kakan_player']
            kakan_tile = self.game_state['last_discarded_tile']
            self.current_player_idx = kakan_player
            self.game_state['pending_kakan_player'] = -1
            print(f"  -> Chankan passed. Player {kakan_player} completes Kakan.")
            return self._perform_kan('kakan', kakan_tile)

        self.game_phase = 'DISCARD'
        self.current_player_idx = (self.game_state['last_discarder'] + 1) % self.num_players
        self.game_state['is_ippatsu_chance'] = [False] * self.num_players
        
        if not self.game_state['wall']:
            return self._process_ryuukyoku()

        self.game_state['turn_count'] += 1
        drawn_tile = self.game_state['wall'].pop(0)
        self.game_state['last_drawn_tile'] = drawn_tile
        
        self.game_state['events'].append({ 'event_id': 'DRAW', 'player': self.current_player_idx, 'tile': drawn_tile })
        
        choices = self._get_my_turn_actions(self.current_player_idx)
        return (self.game_state['events'], choices), [0] * self.num_players, False, {}

    def _check_next_opponent_call(self):
        self.current_player_idx = self.call_check_player_idx
        discarded_tile = self.game_state['last_discarded_tile']
        choices = self._get_opponent_turn_actions(self.current_player_idx, discarded_tile)
        if len(choices) == 1 and choices[0] == 'ACTION_PASS':
            return self._process_pass()
        return (self.game_state['events'], choices), [0] * self.num_players, False, {}

