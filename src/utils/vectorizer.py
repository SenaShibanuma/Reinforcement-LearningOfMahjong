import numpy as np
from src.constants import VECTOR_DIM

# --- 以前から必要だった関数 (placeholderとして追加) ---


def vectorize_event(event):
    """
    ゲームのイベントをベクトルに変換する。
    注意: これは基本的なプレースホルダー実装です。
    """
    # ここではイベントの種類を単純なインデックスに変換する例
    event_type_map = {"draw": 0, "discard": 1, "pon": 2, "chi": 3, "kan": 4}
    vector = np.zeros(VECTOR_DIM)
    event_type = event.get("type", "unknown")
    if event_type in event_type_map:
        vector[event_type_map[event_type]] = 1
    # 本来は牌の情報などもベクトルに含める必要がある
    return vector


def vectorize_choice(choice):
    """
    選択肢（アクション）をベクトルに変換する。
    注意: これは基本的なプレースホルダー実装です。
    """
    # ここでは選択肢の種類を単純なインデックスに変換する例
    # event_type_mapとインデックスが被らないように値を設定
    choice_type_map = {
        "discard": 10, "pon": 11, "chi": 12, "kan": 13, "tsumo": 14
    }
    vector = np.zeros(VECTOR_DIM)
    choice_type = choice.get("type", "unknown")
    if choice_type in choice_type_map:
        vector[choice_type_map[choice_type]] = 1
    # 本来はどの牌を対象とするかなどの情報もベクトルに含める必要がある
    return vector

# --- 新しく追加したクラス ---


class MahjongVectorizer:
    """
    麻雀のゲーム状態全体をベクトル表現に変換するクラス。
    """

    def __init__(self):
        """
        コンストラクタ
        """
        self.vector_dim = VECTOR_DIM

    def vectorize_state(self, state):
        """
        与えられたゲーム状態を固定長のベクトルに変換する。
        注意: これは基本的なプレースホルダー実装です。
               実際のプロジェクトでは、状態の各要素を
               より洗練された方法でエンコードする必要があります。

        Args:
            state (dict): ゲームの状態を表す辞書。

        Returns:
            np.array: 状態を表すベクトル。
        """
        if state is None:
            # ゲーム開始前など、状態がNoneの場合
            return np.zeros(self.vector_dim)

        # 簡単な実装例：状態の辞書から数値情報を抽出し、
        # 連結して固定長のベクトルを生成する。
        # 本来は、牌の種類、ドラ、捨て牌などをone-hotエンコーディングすべき。

        feature_vector = []

        # プレイヤーの手牌 (牌の数を特徴量とする)
        for player_hand in state.get('hands', [[] for _ in range(4)]):
            feature_vector.append(len(player_hand))

        # 捨て牌 (牌の数を特徴量とする)
        for player_discards in state.get('discards', [[] for _ in range(4)]):
            feature_vector.append(len(player_discards))

        # ドラ表示牌 (単純な数値として追加)
        feature_vector.append(state.get('dora_indicator', 0))

        # 現在のターン
        feature_vector.append(state.get('turn', 0))

        # NumPy配列に変換
        features = np.array(feature_vector, dtype=np.float32)

        # 固定長のベクトルになるようにパディングまたは切り捨て
        if len(features) > self.vector_dim:
            # ベクトル次元数に合わせて切り捨て
            vector = features[:self.vector_dim]
        else:
            # 足りない部分をゼロで埋める (ゼロパディング)
            vector = np.pad(features, (0, self.vector_dim - len(features)),
                            'constant')

        return vector

