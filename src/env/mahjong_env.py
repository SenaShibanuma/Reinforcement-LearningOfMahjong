# -*- coding: utf-8 -*-
"""
麻雀のルールと状態遷移を管理する「環境」クラス。
強化学習の標準的なインターフェース（reset, stepなど）を持つ。
"""
import random
from .deck import Deck
from . import mahjong_logic as logic  # ロジック判定用モジュールをインポート
from mahjong.tile import TilesConverter
from mahjong.meld import Meld
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.hand_calculating.hand import HandCalculator
from mahjong.constants import EAST, SOUTH, WEST, NORTH

class MahjongEnv:
    """
    麻雀のゲーム環境をシミュレートするクラス。
    """

    def __init__(self, agents, rules=None, config=None):
        self.agents = agents
        self.num_players = len(agents)
        self.game_state = {}
        self.hand_calculator = HandCalculator()
        self.config = config or {}
        self.rules = {'has_aka_dora': True, 'has_open_tanyao': True}
        if rules: self.rules.update(rules)
        self.num_rounds = self.config.get('game', {}).get('num_rounds', 8)
        print(f"MahjongEnv: Initialized for {self.num_rounds}-round game.")

    def _is_yaochuhai(self, tile_136):
        tile_34 = tile_136 // 4
        return tile_34 >= 27 or (tile_34 % 9 == 0) or (tile_34 % 9 == 8)

    def _deal(self):
        deck = Deck(rules=self.rules)
        self.game_state['wall'] = deck.tiles[:-14]
        self.game_state['dead_wall'] = deck.tiles[-14:]
        self.game_state['dora_indicators'] = [self.game_state['dead_wall'][4]]
        hands = [[] for _ in range(self.num_players)]
        for _ in range(13):
            for i in range(self.num_players):
                hands[i].append(self.game_state['wall'].pop(0))
        for i in range(self.num_players):
            hands[i] = sorted(hands[i])
        self.game_state['hands'] = hands

    def _calculate_agari_result(self, player_idx, tile, is_tsumo):
        hand = self.game_state['hands'][player_idx]
        melds = self.game_state['melds'][player_idx]
        full_hand = hand if is_tsumo else hand + [tile]
        
        config = HandConfig(
            is_tsumo=is_tsumo,
            is_riichi=self.game_state['is_riichi'][player_idx],
            player_wind=self.game_state['player_winds'][player_idx],
            round_wind=self.game_state['round_wind'],
            options=OptionalRules(
                has_open_tanyao=self.rules['has_open_tanyao'],
                has_aka_dora=self.rules['has_aka_dora']
            )
        )
        return self.hand_calculator.estimate_hand_value(
            tiles=full_hand, win_tile=tile, melds=melds,
            dora_indicators=self.game_state['dora_indicators'], config=config)

    def reset(self, initial_state=None):
        if initial_state:
            self.game_state = initial_state
        else:
            self.game_state = {
                'round': 0, 'honba': 0, 'riichi_sticks': 0,
                'scores': [25000] * self.num_players, 'oya_player_id': 0
            }
        
        winds = [EAST, SOUTH, WEST, NORTH]
        round_wind_idx = self.game_state['round'] // 4
        self.game_state['round_wind'] = winds[round_wind_idx]
        
        player_winds = [0] * self.num_players
        for i in range(self.num_players):
            wind_idx = (i - self.game_state['oya_player_id'] + 4) % 4
            player_winds[i] = winds[wind_idx]
        self.game_state['player_winds'] = player_winds

        self.game_state.update({
            'turn_count': 0, 'is_riichi': [False] * self.num_players,
            'melds': [[] for _ in range(self.num_players)],
            'rivers': [[] for _ in range(self.num_players)],
            'events': [],
        })
        self.current_player_idx = self.game_state['oya_player_id']
        self.game_phase = 'DISCARD'
        self._deal()
        
        init_event = {
            'event_id': 'INIT',
            'scores': self.game_state['scores'],
            'oya_player_id': self.game_state['oya_player_id'],
            'round': self.game_state['round'],
            'honba': self.game_state['honba'],
            'riichi_sticks': self.game_state['riichi_sticks'],
            'dora_indicator': self.game_state['dora_indicators'][0]
        }
        self.game_state['events'].append(init_event)

        drawn_tile = self.game_state['wall'].pop(0)
        self.game_state['last_drawn_tile'] = drawn_tile
        self.game_state['hands'][self.current_player_idx].append(drawn_tile)
        self.game_state['hands'][self.current_player_idx].sort()

        draw_event = {
            'event_id': 'DRAW',
            'player': self.current_player_idx,
            'tile': drawn_tile
        }
        self.game_state['events'].append(draw_event)
        
        choices = logic.find_my_turn_actions(self.current_player_idx, self.game_state, self.rules)
        return (self.game_state['events'], choices)

    def step(self, action):
        if self.game_phase == 'DISCARD':
            return self._handle_discard_phase(action)
        elif self.game_phase == 'CALL':
            return self._handle_call_phase(action)
        raise ValueError(f"Unknown game phase: {self.game_phase}")

    def _handle_discard_phase(self, action):
        if action == 'ACTION_TSUMO':
            return self._process_agari(is_tsumo=True)

        action_parts = action.split('_')
        tile_to_discard = int(action_parts[-1])
        
        self.game_state['hands'][self.current_player_idx].remove(tile_to_discard)

        if action.startswith('ACTION_RIICHI'):
            self.game_state['is_riichi'][self.current_player_idx] = True
            self.game_state['scores'][self.current_player_idx] -= 1000
            self.game_state['riichi_sticks'] += 1
            
        self.game_state['rivers'][self.current_player_idx].append(tile_to_discard)
        
        discard_event = {
            'event_id': 'DISCARD',
            'player': self.current_player_idx,
            'tile': tile_to_discard
        }
        self.game_state['events'].append(discard_event)

        self.game_state['last_discarded_tile'] = tile_to_discard
        self.game_state['last_discarder'] = self.current_player_idx
        
        self.game_phase = 'CALL'
        self.call_check_player_idx = (self.current_player_idx + 1) % self.num_players
        self.call_checked_count = 0
        return self._check_next_opponent_call()

    def _handle_call_phase(self, action):
        if action == 'ACTION_RON':
            return self._process_agari(is_tsumo=False)
        
        if action == "ACTION_PASS":
            return self._process_pass()

        caller_idx = self.current_player_idx
        discarded = self.game_state['last_discarded_tile']
        hand = self.game_state['hands'][caller_idx]
        
        action_parts = action.split('_')
        meld_type_str = action_parts[1]
        
        if meld_type_str == "PUNG":
            tiles_34 = discarded // 4
            to_remove = [t for t in hand if t//4 == tiles_34][:2]
            meld = Meld(Meld.PON, tiles=sorted(to_remove + [discarded]))
        elif meld_type_str == "CHII":
            t1_34 = int(action_parts[2])
            t2_34 = int(action_parts[3])
            to_remove = [next(t for t in hand if t//4 == t1_34), next(t for t in hand if t//4 == t2_34)]
            meld = Meld(Meld.CHI, tiles=sorted(to_remove + [discarded]))
        
        for tile in to_remove: hand.remove(tile)
        self.game_state['melds'][caller_idx].append(meld)
        
        meld_event = {
            'event_id': 'MELD',
            'player': caller_idx,
            'meld_type': meld_type_str,
        }
        self.game_state['events'].append(meld_event)

        self.game_phase = 'DISCARD'
        self.current_player_idx = caller_idx
        choices = logic.find_my_turn_actions(self.current_player_idx, self.game_state, self.rules)
        return (self.game_state['events'], choices), [0]*4, False, {}

    def _check_next_opponent_call(self):
        self.current_player_idx = self.call_check_player_idx
        discarded_tile = self.game_state['last_discarded_tile']
        choices = logic.find_opponent_turn_actions(self.current_player_idx, discarded_tile, self.game_state, self.rules)

        if len(choices) == 1 and choices[0] == 'ACTION_PASS':
            return self._process_pass()

        return (self.game_state['events'], choices), [0]*4, False, {}

    def _process_pass(self):
        self.call_checked_count += 1
        if self.call_checked_count >= self.num_players - 1:
            self.game_phase = 'DISCARD'
            self.current_player_idx = (self.game_state['last_discarder'] + 1) % self.num_players
            
            if not self.game_state['wall']: return self._process_ryuukyoku()

            self.game_state['turn_count'] += 1
            drawn_tile = self.game_state['wall'].pop(0)
            
            draw_event = {
                'event_id': 'DRAW',
                'player': self.current_player_idx,
                'tile': drawn_tile
            }
            self.game_state['events'].append(draw_event)
            
            self.game_state['last_drawn_tile'] = drawn_tile
            self.game_state['hands'][self.current_player_idx].append(drawn_tile)
            self.game_state['hands'][self.current_player_idx].sort()
            
            choices = logic.find_my_turn_actions(self.current_player_idx, self.game_state, self.rules)
            return (self.game_state['events'], choices), [0]*4, False, {}
        else:
            self.call_check_player_idx = (self.call_check_player_idx + 1) % self.num_players
            if self.call_check_player_idx == self.game_state['last_discarder']:
                 self.call_check_player_idx = (self.call_check_player_idx + 1) % self.num_players
            return self._check_next_opponent_call()

    def _process_agari(self, is_tsumo):
        winner_idx = self.current_player_idx
        win_tile = self.game_state['last_drawn_tile'] if is_tsumo else self.game_state['last_discarded_tile']
        
        result = self._calculate_agari_result(winner_idx, win_tile, is_tsumo)
        if result.error: return (self.game_state['events'], []), [0]*4, True, {'reason': f'agari_error: {result.error}'}

        total_cost = result.cost['main'] + result.cost['additional']
        rewards = [0] * self.num_players
        
        if is_tsumo:
            for i in range(self.num_players):
                if i == winner_idx: continue
                is_oya = i == self.game_state['oya_player_id']
                payment = result.cost['main'] if is_oya else result.cost['additional']
                self.game_state['scores'][i] -= payment
                rewards[i] = -payment
        else:
            loser_idx = self.game_state['last_discarder']
            self.game_state['scores'][loser_idx] -= total_cost
            rewards[loser_idx] = -total_cost

        riichi_bonus = self.game_state['riichi_sticks'] * 1000
        self.game_state['scores'][winner_idx] += total_cost + riichi_bonus
        rewards[winner_idx] = total_cost + riichi_bonus
        self.game_state['riichi_sticks'] = 0
        
        agari_event = {
            'event_id': 'AGARI',
            'winner': winner_idx,
            'hand_value': total_cost,
        }
        self.game_state['events'].append(agari_event)

        oya_renchan = winner_idx == self.game_state['oya_player_id']
        if oya_renchan:
            self.game_state['honba'] += 1
        else:
            self.game_state['honba'] = 0
            self.game_state['round'] += 1
            self.game_state['oya_player_id'] = (self.game_state['oya_player_id'] + 1) % self.num_players

        game_over = self.game_state['round'] >= self.num_rounds or any(s < 0 for s in self.game_state['scores'])
        return (self.game_state['events'], []), rewards, True, {'reason': 'agari', 'game_over': game_over}

    def _process_ryuukyoku(self):
        tenpai_players = [i for i in range(self.num_players) if logic.check_tenpai(self.game_state['hands'][i], self.game_state['melds'][i])]
        num_tenpai = len(tenpai_players)
        rewards = [0] * self.num_players

        payment, receipt = 0, 0
        if num_tenpai == 1: receipt, payment = 3000, 1000
        elif num_tenpai == 2: receipt, payment = 1500, 1500
        elif num_tenpai == 3: receipt, payment = 1000, 3000
        
        if payment > 0:
            for i in range(self.num_players):
                if i in tenpai_players:
                    self.game_state['scores'][i] += receipt
                    rewards[i] = receipt
                else:
                    self.game_state['scores'][i] -= payment
                    rewards[i] = -payment
        
        ryuukyoku_event = {
            'event_id': 'RYUUKYOKU',
            'tenpai_players': tenpai_players,
        }
        self.game_state['events'].append(ryuukyoku_event)

        oya_in_tenpai = self.game_state['oya_player_id'] in tenpai_players
        if oya_in_tenpai: self.game_state['honba'] += 1
        else:
            self.game_state['honba'] = 0
            self.game_state['round'] += 1
            self.game_state['oya_player_id'] = (self.game_state['oya_player_id'] + 1) % self.num_players

        game_over = self.game_state['round'] >= self.num_rounds
        return (self.game_state['events'], []), rewards, True, {'reason': 'ryuukyoku', 'game_over': game_over}

