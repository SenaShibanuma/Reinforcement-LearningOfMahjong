# -*- coding: utf-8 -*-
"""
MahjongEnvクラスのユニットテスト。
"""
import pytest
from src.env.mahjong_env import MahjongEnv
from src.agent.agent import MahjongAgent
from mahjong.tile import TilesConverter

# テスト用のダミーエージェント
class DummyAgent:
    def choose_action(self, context, choices, player_pov, is_training=False):
        # 常に最初の選択肢を選ぶ
        return choices[0], {c: 1/len(choices) for c in choices}

@pytest.fixture
def env_with_dummy_agents():
    """テスト用のMahjongEnvインスタンスを生成するフィクスチャ"""
    agents = [DummyAgent() for _ in range(4)]
    env = MahjongEnv(agents)
    return env

def test_initialization(env_with_dummy_agents):
    """環境が正しく初期化されるかテスト"""
    env = env_with_dummy_agents
    # reset()を呼び出す前の初期状態は限定的だが、ルールなどは確認できる
    assert env.num_players == 4
    assert env.rules['has_aka_dora'] == True

def test_reset_and_deal(env_with_dummy_agents):
    """reset()によって局が正しく開始されるかテスト"""
    env = env_with_dummy_agents
    obs, choices = env.reset()
    
    # 親（Oya）はプレイヤー0
    assert env.game_state['oya_player_id'] == 0
    
    # 手牌の枚数を確認
    # 親は14枚
    assert len(env.game_state['hands'][0]) == 14
    # 子は13枚
    assert len(env.game_state['hands'][1]) == 13
    assert len(env.game_state['hands'][2]) == 13
    assert len(env.game_state['hands'][3]) == 13

    # 牌山の残り枚数を確認 (136 - (13*4 + 1) = 83)
    assert len(env.game_state['wall']) == 136 - (13 * 4 + 1)
    
    # ドラ表示牌が1枚あるか
    assert len(env.game_state['dora_indicators']) == 1
    
    # 最初のプレイヤー（親）の選択肢が返されているか
    assert env.current_player_idx == 0
    assert len(choices) > 0
    
    # 親の最初の選択肢は打牌のはず
    for choice in choices:
        assert choice.startswith("DISCARD_") or choice.startswith("ACTION_")

def test_simple_discard_step(env_with_dummy_agents):
    """単純な打牌のstepが正しく処理されるかテスト"""
    env = env_with_dummy_agents
    _, choices = env.reset()

    # 親が最初の選択肢（何かを打牌する）を選ぶ
    action = choices[0]
    tile_to_discard = int(action.split('_')[1])

    obs, rewards, done, info = env.step(action)

    # 親の手牌から牌が減っているか (14 -> 13)
    assert len(env.game_state['hands'][0]) == 13
    assert tile_to_discard not in env.game_state['hands'][0]
    
    # ゲームフェーズがCALLになっているか
    assert env.game_phase == 'CALL'
    
    # 次の確認対象プレイヤーが下家(プレイヤー1)になっているか
    assert env.current_player_idx == 1
