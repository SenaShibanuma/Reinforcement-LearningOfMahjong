# -*- coding: utf-8 -*-
"""
TensorFlow/Kerasを使用して、TransformerベースのAIモデルの構造を定義する。
"""
import tensorflow as tf
from tensorflow.keras import layers
from src.constants import MAX_CONTEXT_LENGTH, MAX_CHOICES, VECTOR_DIM

def build_masked_transformer(
    context_len=MAX_CONTEXT_LENGTH, 
    choices_len=MAX_CHOICES, 
    embed_dim=VECTOR_DIM, 
    num_heads=4, 
    ff_dim=256, 
    num_transformer_blocks=2
):
    """
    3つの入力(context, choices, mask)を受け取り、各選択肢のスコアを出力する
    Transformerモデルを構築する。
    """
    context_input = layers.Input(shape=(context_len, embed_dim), name="context_input")
    choices_input = layers.Input(shape=(choices_len, embed_dim), name="choices_input")
    mask_input = layers.Input(shape=(choices_len,), name="mask_input")
    
    x = context_input
    for _ in range(num_transformer_blocks):
        attn_output = layers.MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim)(x, x)
        x = layers.Add()([x, attn_output])
        x = layers.LayerNormalization(epsilon=1e-6)(x)
        ffn_output = layers.Dense(ff_dim, activation="relu")(x)
        ffn_output = layers.Dense(embed_dim)(ffn_output)
        x = layers.Add()([x, ffn_output])
        x = layers.LayerNormalization(epsilon=1e-6)(x)
        
    context_vector = layers.GlobalAveragePooling1D()(x)
    context_vector_expanded = layers.RepeatVector(choices_len)(context_vector)
    
    merged = layers.Concatenate()([context_vector_expanded, choices_input])
    
    ff_out = layers.Dense(128, activation='relu')(merged)
    ff_out = layers.Dropout(0.2)(ff_out)
    logits = layers.Dense(1, name="output_logits")(ff_out)
    logits = layers.Reshape((choices_len,))(logits)
    
    masked_logits = layers.Multiply()([logits, mask_input])
    
    # マスクされた部分を非常に小さい値に設定して、softmaxで確率が0になるようにする
    mask_adder = (1.0 - mask_input) * -1e9
    final_logits = layers.Add()([masked_logits, mask_adder])
    
    return tf.keras.Model(inputs=[context_input, choices_input, mask_input], outputs=final_logits)
