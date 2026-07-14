"""
Feature Layer - kinematics.py
------------------------------
운동학적 특성(Kinematic Features) 추출:
    - velocity        : 이동 속도 (cm/s)
    - acceleration    : 가속도 (cm/s²)
    - angular_velocity: 각속도 (rad/s)
"""
import numpy as np
import pandas as pd


def calculate_kinematics(
    df: pd.DataFrame,
    fps: float = 30.0,
    pixels_per_cm: float = 10.0
) -> pd.DataFrame:
    """
    통합 DataFrame에 운동학적 특성 컬럼을 추가하여 반환합니다.
    개체(Animal_ID)별로 분리하여 계산, 세션 경계에서의 점프 오류를 방지합니다.
    """
    results = []
    for animal_id, grp in df.groupby('Animal_ID'):
        grp = grp.copy().sort_values('Frame').reset_index(drop=True)

        bx = grp['bodycentre_x'].values / pixels_per_cm
        by = grp['bodycentre_y'].values / pixels_per_cm

        # 1. 속도 (cm/s)
        dx = np.diff(bx, prepend=bx[0])
        dy = np.diff(by, prepend=by[0])
        dist = np.sqrt(dx ** 2 + dy ** 2)
        velocity = dist * fps

        # 2. 가속도 (cm/s²)
        acceleration = np.abs(np.diff(velocity, prepend=velocity[0])) * fps

        # 3. 각속도 (rad/s) - 이동 방향 각도의 변화율
        angles = np.arctan2(dy, dx)
        d_angles = np.diff(angles, prepend=angles[0])
        # -π ~ π 범위로 정규화
        d_angles = (d_angles + np.pi) % (2 * np.pi) - np.pi
        angular_velocity = np.abs(d_angles) * fps

        grp['velocity'] = velocity
        grp['acceleration'] = acceleration
        grp['angular_velocity'] = angular_velocity
        results.append(grp)

    return pd.concat(results, ignore_index=True)
