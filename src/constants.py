class Constants:
    NOTEN_BAPPU = 3000  # 不聴罰符の合計点

# --- AIモデル ハイパーパラメータ ---

# AIが一度に考慮する過去のイベントの最大数
MAX_CONTEXT_LENGTH = 150

# AIが一度に考慮する行動選択肢の最大数
MAX_CHOICES = 50

# ゲームの状況や選択肢を表現するベクトルの次元数
VECTOR_DIM = 100

