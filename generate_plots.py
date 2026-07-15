"""generate_plots.py — 궤적·히트맵 PNG만 재생성하는 보조 스크립트 (전체 파이프라인은 main.py)."""
import os
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

from src.data.loader import build_dataset
from src.analysis.comparison import plot_trajectory, plot_heatmap

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_PATH = os.path.join(BASE_DIR, 'METADATA_ROCHE.csv')
DATA_DIR = os.path.join(BASE_DIR, 'data', 'Yohimbine_Roche')
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')

def main():
    """궤적·히트맵 PNG만 빠르게 재생성한다.

    흐름: DLC CSV → build_dataset 으로 좌표 df 생성 → 좌표 기반 플롯 저장.
    """
    print("데이터 로드 중 ...")
    df = build_dataset(METADATA_PATH, DATA_DIR)
    print("플롯 생성 중 ...")
    plot_trajectory(df, OUTPUT_DIR)  # bodycentre_x/y → 이동 궤적
    plot_heatmap(df, OUTPUT_DIR)     # bodycentre_x/y → 공간 점유 히트맵
    print("완료!")

if __name__ == "__main__":
    main()
 