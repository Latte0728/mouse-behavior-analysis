"""
Data Layer - loader.py
----------------------
메타데이터와 DeepLabCut 원본 추적 데이터를 결합하고,
Likelihood 기반 저신뢰도 좌표 제거 → 선형 보간 → Savitzky-Golay 스무딩 순서로 전처리합니다.
"""
import os
import glob
import re
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from config.csv import CSV_MAPPING


def load_metadata(metadata_path: str) -> pd.DataFrame:
    """METADATA_ROCHE.csv 로드 후 Animal_ID를 문자열로 통일합니다."""
    df = pd.read_csv(metadata_path, sep=';')
    # 실제 컬럼명(설정에서 로드) → 내부 표준 'Animal_ID'로 통일
    df = df.rename(columns={CSV_MAPPING["animal"]: 'Animal_ID'})
    df['Animal_ID'] = df['Animal_ID'].astype(str).str.strip()
    return df


def process_tracking_file(
    file_path: str,
    likelihood_threshold: float = 0.6,
    window_length: int = 15,
    polyorder: int = 3
) -> pd.DataFrame:
    """
    단일 개체의 DLC CSV 파일에 전처리를 수행하여 (Frame × Keypoint_xy) 구조로 반환합니다.

    처리 단계:
        1. Likelihood < threshold 좌표 → NaN 처리 (저신뢰도 제거)
        2. 선형 보간(Linear Interpolation)으로 결측치 보완
        3. Savitzky-Golay 필터로 급격한 좌표 변화(추적 오류) 완화
    """
    df_dlc = pd.read_csv(file_path, header=[1, 2], index_col=0)
    bodyparts = df_dlc.columns.get_level_values(0).unique()

    for bp in bodyparts:
        if (bp, 'likelihood') not in df_dlc.columns:
            continue
        low_conf = df_dlc[(bp, 'likelihood')] < likelihood_threshold
        df_dlc.loc[low_conf, (bp, 'x')] = np.nan
        df_dlc.loc[low_conf, (bp, 'y')] = np.nan
        df_dlc[(bp, 'x')] = df_dlc[(bp, 'x')].interpolate(
            method='linear', limit_direction='both'
        )
        df_dlc[(bp, 'y')] = df_dlc[(bp, 'y')].interpolate(
            method='linear', limit_direction='both'
        )
        df_dlc[(bp, 'x')] = savgol_filter(
            df_dlc[(bp, 'x')].fillna(0), window_length=window_length, polyorder=polyorder
        )
        df_dlc[(bp, 'y')] = savgol_filter(
            df_dlc[(bp, 'y')].fillna(0), window_length=window_length, polyorder=polyorder
        )

    return df_dlc


def _extract_animal_id(filename: str) -> str | None:
    """
    파일명에서 Animal_ID 패턴 (예: 16459-67049) 추출.
    DLC 파일명 규칙: ..._16459-67049DLC_...
    """
    match = re.search(r'(\d{5}-\d{5})DLC', filename)
    return match.group(1) if match else None


def build_dataset(metadata_path: str, data_dir: str) -> pd.DataFrame:
    """
    메타데이터와 모든 개체의 전처리된 트래킹 데이터를 결합하여
    분석에 사용할 통합 DataFrame을 구성합니다.

    반환 컬럼 구조:
        Frame, Animal_ID, Dose, {bodypart}_x, {bodypart}_y, ...
    """
    df_meta = load_metadata(metadata_path)
    csv_files = glob.glob(os.path.join(data_dir, '*.csv'))

    records = []
    for file_path in csv_files:
        filename = os.path.basename(file_path)
        animal_id = _extract_animal_id(filename)
        if animal_id is None:
            print(f"[SKIP] Animal_ID 추출 실패: {filename}")
            continue

        meta_row = df_meta[df_meta['Animal_ID'] == animal_id]
        if meta_row.empty:
            print(f"[SKIP] 메타데이터 미매칭: {animal_id}")
            continue

        dose = int(meta_row.iloc[0][CSV_MAPPING["dose"]])
        df_tracking = process_tracking_file(file_path)

        flat = {'Frame': df_tracking.index.tolist()}
        flat['Animal_ID'] = animal_id
        flat['Dose'] = dose
        bodyparts = df_tracking.columns.get_level_values(0).unique()
        for bp in bodyparts:
            if (bp, 'x') in df_tracking.columns:
                flat[f'{bp}_x'] = df_tracking[(bp, 'x')].values
                flat[f'{bp}_y'] = df_tracking[(bp, 'y')].values

        records.append(pd.DataFrame(flat))
        print(f"[OK] {animal_id} (Dose {dose}) - {len(df_tracking)} frames")

    if not records:
        raise RuntimeError("분석 가능한 데이터가 없습니다. 경로와 파일명 규칙을 확인하세요.")

    return pd.concat(records, ignore_index=True)
 