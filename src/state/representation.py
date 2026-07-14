"""
State Layer - representation.py
---------------------------------
특징(Features) 벡터를 Z-score 표준화하여
다차원 표준화 상태 공간(Standardized State Vector)으로 변환합니다.
"""
import pandas as pd
from sklearn.preprocessing import StandardScaler

FEATURE_COLS = [
    'velocity', 'acceleration', 'angular_velocity',
    'wall_distance', 'center_occupancy', 'path_tortuosity',
    'body_length', 'body_curvature', 'tail_curvature',
]


def compute_state_vector(df: pd.DataFrame) -> tuple[pd.DataFrame, StandardScaler]:
    """
    FEATURE_COLS에 해당하는 원시 특징을 Z-score 정규화하여
    z_ 접두사를 붙인 State Vector 컬럼으로 추가합니다.

    반환값:
        df_state  : z_ 컬럼이 추가된 DataFrame
        scaler    : 피팅된 StandardScaler (추후 역변환 또는 새 데이터 적용에 사용)
    """
    df = df.copy()
    available = [c for c in FEATURE_COLS if c in df.columns]
    missing   = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"[State] 다음 특징이 누락되어 제외됩니다: {missing}")

    filled = df[available].ffill().bfill().fillna(0)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(filled)

    for i, col in enumerate(available):
        df[f'z_{col}'] = scaled[:, i]

    return df, scaler
