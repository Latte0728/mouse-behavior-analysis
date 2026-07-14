"""
Analysis Layer - comparison.py
--------------------------------
대조군 대비 약물 효과를 시각화합니다.

산출물:
    - Trajectory Plot     : 개체별 이동 경로
    - Heatmap             : 공간 체류 밀도
    - Continuous Score Plot: 시간별 행동 강도 변화
    - Dose-response Plot  : 농도별 행동 점수 (Mixed Model 요약과 연동)
    - Distribution Plot   : Dose별 점수 분포 (Violin/Box)
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import seaborn as sns

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

from src.constants import FPS, SCORE_COLS_TITLE as SCORE_COLS, DOSE_PALETTE  # 점수 컬럼·투여군 색
from config.plot import DOWNSAMPLE_THRESHOLD


def _ensure_dir(output_dir: str):
    os.makedirs(output_dir, exist_ok=True)


def plot_trajectory(df: pd.DataFrame, output_dir: str):
    """Dose별 대표 개체의 이동 경로를 시각화합니다."""
    _ensure_dir(output_dir)
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    for ax, (dose, color) in zip(axes, DOSE_PALETTE.items()):
        sample = df[df['Dose'] == dose].groupby('Animal_ID').first().index
        if len(sample) == 0:
            continue
        animal = sample[0]
        traj = df[(df['Dose'] == dose) & (df['Animal_ID'] == animal)]
        ax.plot(traj['bodycentre_x'], traj['bodycentre_y'],
                color=color, alpha=0.6, linewidth=0.5)
        ax.set_title(f'Dose {dose} mg/kg', fontsize=12)
        ax.set_aspect('equal')
        ax.axis('off')
    plt.suptitle('그룹별 이동 궤적', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'trajectory_plot.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] trajectory_plot.png")


def plot_heatmap(df: pd.DataFrame, output_dir: str):
    """Dose별 공간 점유 Heatmap을 시각화합니다."""
    _ensure_dir(output_dir)
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    for ax, dose in zip(axes, DOSE_PALETTE.keys()):
        sub = df[df['Dose'] == dose]
        ax.hist2d(sub['bodycentre_x'], sub['bodycentre_y'],
                  bins=50, cmap='YlOrRd', density=True)
        ax.set_title(f'Dose {dose} mg/kg', fontsize=12)
        ax.set_aspect('equal')
        ax.axis('off')
    plt.suptitle('공간 점유 히트맵', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] heatmap.png")


def plot_continuous_scores(df: pd.DataFrame, output_dir: str, bin_size: int = 900):
    """시간 흐름에 따른 행동 강도 점수를 Dose별로 시각화합니다."""
    _ensure_dir(output_dir)
    df = df.copy()
    df['Time_Bin'] = (df['Frame'] // bin_size) * bin_size

    for score_col in SCORE_COLS:
        if score_col not in df.columns:
            continue
        grouped = df.groupby(['Time_Bin', 'Dose'])[score_col].mean().reset_index()
        plt.figure(figsize=(12, 4))
        for dose, color in DOSE_PALETTE.items():
            sub = grouped[grouped['Dose'] == dose]
            plt.plot(sub['Time_Bin'], sub[score_col],
                     label=f'Dose {dose}', color=color, linewidth=1.5)
        plt.title(f'Temporal Dynamics: {score_col}', fontsize=13)
        plt.xlabel('Frame', fontsize=11)
        plt.ylabel('Behavioral Intensity Score', fontsize=11)
        plt.legend(title='Dose (mg/kg)')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'continuous_{score_col}.png'),
                    dpi=150, bbox_inches='tight')
        plt.close()
    print("[OK] continuous_score plots")


def plot_dose_response(df: pd.DataFrame, output_dir: str):
    """농도별 행동 점수의 평균과 신뢰구간을 Dose-response Curve로 시각화합니다."""
    _ensure_dir(output_dir)
    # 시각화 성능 최적화를 위해 1초 단위(FPS프레임)로 다운샘플링
    plot_df = df.iloc[::FPS] if len(df) > DOWNSAMPLE_THRESHOLD else df
    for score_col in SCORE_COLS:
        if score_col not in plot_df.columns:
            continue
        plt.figure(figsize=(7, 5))
        sns.pointplot(
            data=plot_df, x='Dose', y=score_col,
            order=sorted(plot_df['Dose'].unique()),
            capsize=0.1, err_kws={'linewidth': 1.5},
            color='#2d6a9f', linestyles='--', markers='o'
        )
        plt.title(f'Dose-Response Curve: {score_col}', fontsize=13)
        plt.xlabel('Yohimbine Dose (mg/kg)', fontsize=11)
        plt.ylabel('Mean Behavioral Intensity Score', fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'dose_response_{score_col}.png'),
                    dpi=150, bbox_inches='tight')
        plt.close()
    print("[OK] dose_response plots")


def plot_distribution(df: pd.DataFrame, output_dir: str):
    """Dose별 행동 점수의 분포를 Violin + Box Plot으로 시각화합니다."""
    _ensure_dir(output_dir)
    # 시각화 성능 최적화를 위해 1초 단위(FPS프레임)로 다운샘플링
    plot_df = df.iloc[::FPS] if len(df) > DOWNSAMPLE_THRESHOLD else df
    for score_col in SCORE_COLS:
        if score_col not in plot_df.columns:
            continue
        plt.figure(figsize=(8, 5))
        doses_sorted = sorted(plot_df['Dose'].unique())
        palette = [DOSE_PALETTE[d] for d in doses_sorted]
        sns.violinplot(
            data=plot_df, x='Dose', y=score_col,
            order=doses_sorted,
            hue='Dose', hue_order=doses_sorted,
            palette=palette, inner='box', linewidth=1.0,
            legend=False
        )
        plt.title(f'Distribution by Dose: {score_col}', fontsize=13)
        plt.xlabel('Yohimbine Dose (mg/kg)', fontsize=11)
        plt.ylabel('Behavioral Intensity Score', fontsize=11)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f'distribution_{score_col}.png'),
                    dpi=150, bbox_inches='tight')
        plt.close()
    print("[OK] distribution plots")
