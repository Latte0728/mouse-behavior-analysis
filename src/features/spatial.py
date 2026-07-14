"""
Feature Layer - spatial.py
---------------------------
공간적 특성(Spatial Features) 추출:
    - wall_distance     : 벽면까지의 거리 (cm)
    - center_occupancy  : 중앙 영역 점유 여부 (0/1)
    - path_tortuosity   : 경로 곡절도 (실제이동/직선거리)
"""
import numpy as np
import pandas as pd


def calculate_spatial_features(
    df: pd.DataFrame,
    arena_x_cols: tuple = ('tl_x', 'tr_x', 'bl_x', 'br_x'),
    arena_y_cols: tuple = ('tl_y', 'tr_y', 'bl_y', 'br_y'),
    center_zone_ratio: float = 0.5,
    fps: float = 30.0,
    pixels_per_cm: float = 10.0,
    tortuosity_window: int = 30
) -> pd.DataFrame:
    """
    아레나 코너 좌표(tl/tr/bl/br)를 사용해 경계를 추정하고,
    개체별 공간적 특성을 계산합니다.
    """
    results = []
    for animal_id, grp in df.groupby('Animal_ID'):
        grp = grp.copy().sort_values('Frame').reset_index(drop=True)

        # 아레나 경계 추정 (코너 4점의 중간값 기반)
        x_min = grp[['tl_x', 'bl_x']].median().mean()
        x_max = grp[['tr_x', 'br_x']].median().mean()
        y_min = grp[['tl_y', 'tr_y']].median().mean()
        y_max = grp[['bl_y', 'br_y']].median().mean()

        cx = (x_min + x_max) / 2
        cy = (y_min + y_max) / 2
        arena_w = (x_max - x_min) / pixels_per_cm
        arena_h = (y_max - y_min) / pixels_per_cm

        bx = grp['bodycentre_x'].values
        by = grp['bodycentre_y'].values

        # 1. 벽면 거리 (cm): 4벽 중 가장 가까운 거리
        dist_left   = (bx - x_min) / pixels_per_cm
        dist_right  = (x_max - bx) / pixels_per_cm
        dist_top    = (by - y_min) / pixels_per_cm
        dist_bottom = (y_max - by) / pixels_per_cm
        wall_distance = np.minimum.reduce([dist_left, dist_right, dist_top, dist_bottom])
        wall_distance = np.clip(wall_distance, 0, None)
        grp['wall_distance'] = wall_distance

        # 2. 중앙 점유 여부 (0/1)
        zone_w = arena_w * center_zone_ratio / 2
        zone_h = arena_h * center_zone_ratio / 2
        in_center = (
            (np.abs(bx - cx) / pixels_per_cm < zone_w) &
            (np.abs(by - cy) / pixels_per_cm < zone_h)
        ).astype(float)
        grp['center_occupancy'] = in_center

        # 3. 경로 곡절도 (tortuosity_window 프레임 윈도우)
        dx = np.diff(bx, prepend=bx[0]) / pixels_per_cm
        dy = np.diff(by, prepend=by[0]) / pixels_per_cm
        step_dist = np.sqrt(dx ** 2 + dy ** 2)
        rolling_dist = (
            pd.Series(step_dist).rolling(tortuosity_window, min_periods=1).sum().values
        )
        shift_bx = pd.Series(bx).shift(tortuosity_window).fillna(bx[0]).values
        shift_by = pd.Series(by).shift(tortuosity_window).fillna(by[0]).values
        straight_dist = np.sqrt((bx - shift_bx) ** 2 + (by - shift_by) ** 2) / pixels_per_cm
        tortuosity = np.divide(
            rolling_dist, straight_dist,
            out=np.ones_like(rolling_dist),
            where=straight_dist > 0.1
        )
        grp['path_tortuosity'] = np.clip(tortuosity, 1.0, 10.0)

        results.append(grp)

    return pd.concat(results, ignore_index=True)
