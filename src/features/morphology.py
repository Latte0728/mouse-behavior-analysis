"""
Feature Layer - morphology.py
------------------------------
형태학적 특성(Morphological Features) 추출:
    - body_length   : 신체 길이 (nose ~ tailbase, cm)
    - body_curvature: 몸체 굽은 정도 (0=직선, 1=완전히 구부러짐)
    - tail_curvature: 꼬리 굽은 정도
"""
import numpy as np
import pandas as pd


def _angle_between(v1x, v1y, v2x, v2y) -> np.ndarray:
    """두 벡터 간의 내각(라디안)을 반환합니다."""
    dot = v1x * v2x + v1y * v2y
    mag1 = np.sqrt(v1x ** 2 + v1y ** 2)
    mag2 = np.sqrt(v2x ** 2 + v2y ** 2)
    cos_t = dot / (mag1 * mag2 + 1e-8)
    return np.arccos(np.clip(cos_t, -1.0, 1.0))


def calculate_morphology(
    df: pd.DataFrame,
    pixels_per_cm: float = 10.0
) -> pd.DataFrame:
    """
    통합 DataFrame에 형태학적 특성 컬럼을 추가하여 반환합니다.
    """
    results = []
    for animal_id, grp in df.groupby('Animal_ID'):
        grp = grp.copy().sort_values('Frame').reset_index(drop=True)

        # 주요 관절 좌표 추출
        nx,  ny  = grp['nose_x'].values,        grp['nose_y'].values
        bc_x, bc_y = grp['bodycentre_x'].values, grp['bodycentre_y'].values
        tb_x, tb_y = grp['tailbase_x'].values,   grp['tailbase_y'].values
        tc_x, tc_y = grp['tailcentre_x'].values, grp['tailcentre_y'].values
        tt_x, tt_y = grp['tailtip_x'].values,    grp['tailtip_y'].values

        # 1. 신체 길이 (nose → tailbase, cm)
        grp['body_length'] = (
            np.sqrt((nx - tb_x) ** 2 + (ny - tb_y) ** 2) / pixels_per_cm
        )

        # 2. 몸체 곡률 (nose–bodycentre–tailbase 내각 기반)
        #    내각이 π(180°)에 가까울수록 직선, 작을수록 구부러짐
        #    curvature = 1 - angle/π : 직선 → 0, 구부러짐 → 1
        angle_body = _angle_between(
            nx - bc_x, ny - bc_y,
            tb_x - bc_x, tb_y - bc_y
        )
        grp['body_curvature'] = 1.0 - (angle_body / np.pi)

        # 3. 꼬리 곡률 (tailbase–tailcentre–tailtip 내각 기반)
        angle_tail = _angle_between(
            tb_x - tc_x, tb_y - tc_y,
            tt_x - tc_x, tt_y - tc_y
        )
        grp['tail_curvature'] = 1.0 - (angle_tail / np.pi)

        results.append(grp)

    return pd.concat(results, ignore_index=True)
