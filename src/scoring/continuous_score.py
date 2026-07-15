"""
Scoring Layer - continuous_score.py
-------------------------------------
표준화된 State Vector에 도메인 지식 기반 가중치를 적용한 뒤
Sigmoid 변환을 거쳐 0~1 사이의 연속적인 행동 강도(Behavioral Intensity Score)를 산출합니다.

가중치 설계 근거:
    초기 버전에서 가중치는 '학습'이 아닌 동물 행동학적 지식(Domain Knowledge)을 바탕으로
    명시적으로 정의하였습니다. 추후 대규모 데이터 확보 시 데이터 기반 최적화로 확장 가능합니다.

Sigmoid 채택 근거:
    - ReLU: 상한이 없어 강도 지표(0~1)로 부적합
    - Softmax: 출력값의 합을 1로 강제 → 복합 행동 표현 불가
    - Sigmoid: 독립적인 0~1 연속 강도 표현에 최적
"""
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 도메인 지식 기반 가중치 정의 (Domain Knowledge Weights)
# 양수: 해당 특성이 높을수록 행동 강도 증가
# 음수: 해당 특성이 낮을수록 행동 강도 증가
# ---------------------------------------------------------------------------
BEHAVIOR_WEIGHTS: dict[str, dict[str, float]] = {
    'Locomotion': {
        'z_velocity':        1.5,
        'z_acceleration':    0.5,
        'z_path_tortuosity': -0.5,
    },
    'Exploration': {
        'z_center_occupancy': 1.0,
        'z_velocity':         0.5,
        'z_body_length':      0.5,
        'z_wall_distance':    1.0,
    },
    'Anxiety': {
        'z_wall_distance':    -1.5,   # Thigmotaxis: 벽에 가까울수록 불안 증가
        'z_center_occupancy': -1.5,
        'z_velocity':         -0.5,
        'z_tail_curvature':    0.5,   # 꼬리를 말아올리는 긴장 행동
    },
    'Hyperactivity': {
        'z_velocity':          1.5,
        'z_acceleration':      1.0,
        'z_angular_velocity':  1.0,   # 잦은 방향 전환
        'z_path_tortuosity':   1.0,
    },
    'Freezing': {
        'z_velocity':         -2.0,   # 거의 움직이지 않음
        'z_acceleration':     -1.0,
        'z_angular_velocity': -1.0,
        'z_body_length':      -0.5,   # 움츠러든 자세
    },
}

# 각 행동별 기저 편향(Bias) — Z-score 0점(평균 상태)에서의 점수 조정
BEHAVIOR_BIAS: dict[str, float] = {
    'Locomotion':    0.0,
    'Exploration':   0.0,
    'Anxiety':      -0.5,
    'Hyperactivity': 0.0,
    'Freezing':     -1.5,  # 일반 상태에서 기본값이 낮게 유지되도록 억제
}


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """오버플로우 방지를 위한 클리핑 후 Sigmoid 변환."""
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def calculate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    State Vector(z_ 컬럼)로부터 5가지 행동 강도(Behavioral Intensity Score)를 산출합니다.

    출력 컬럼:
        Locomotion_Score, Exploration_Score, Anxiety_Score,
        Hyperactivity_Score, Freezing_Score  (범위: 0 ~ 1)
    """
    df = df.copy()

    for behavior, weights in BEHAVIOR_WEIGHTS.items():
        score_sum = np.zeros(len(df))
        for feature, w in weights.items():
            if feature in df.columns:
                score_sum += df[feature].values * w
        score_sum += BEHAVIOR_BIAS.get(behavior, 0.0)
        df[f'{behavior}_Score'] = _sigmoid(score_sum)

    return df
 