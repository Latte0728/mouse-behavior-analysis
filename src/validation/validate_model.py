"""
Validation Layer - validate_model.py
--------------------------------------
구축된 파이프라인의 통계적 유효성을 검증합니다.

검증 구성:
    1. Mixed Model 기반 Dose Effect 검정 (p-value)
    2. Dose-response Trend Test - 선형 추세 회귀계수 및 p-value
    3. Effect Size (Cohen's d) 및 95% Confidence Interval
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.constants import SCORE_COLS_TITLE as SCORE_COLS  # 행동 점수 컬럼(Title_Score)


def _cohens_d(group_a: np.ndarray, group_b: np.ndarray) -> float:
    """두 그룹 간 Cohen's d 효과 크기를 계산합니다."""
    pooled_std = np.sqrt(
        ((len(group_a) - 1) * group_a.std(ddof=1) ** 2 +
         (len(group_b) - 1) * group_b.std(ddof=1) ** 2)
        / (len(group_a) + len(group_b) - 2)
    )
    if pooled_std == 0:
        return 0.0
    return (group_a.mean() - group_b.mean()) / pooled_std


def validate_dose_effect(
    df: pd.DataFrame,
    mixed_model_summary: pd.DataFrame
) -> pd.DataFrame:
    """
    혼합 모델 요약에서 Dose Effect의 p-value를 추출하여 반환합니다.
    """
    cols = ['Behavior', 'Dose_Coef', 'Dose_Pval']
    available = [c for c in cols if c in mixed_model_summary.columns]
    return mixed_model_summary[available].copy()


def validate_trend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dose(0, 1, 3, 6)를 연속 변수로 두고 행동 점수와의 선형 추세를 검정합니다.
    (Dose-response Trend Test)

    반환 컬럼: Behavior, Trend_Slope, Trend_Pval, R_squared
    """
    records = []
    dose_means = df.groupby(['Animal_ID', 'Dose'])[SCORE_COLS].mean().reset_index()

    for col in SCORE_COLS:
        if col not in dose_means.columns:
            continue
        x = dose_means['Dose'].values.astype(float)
        y = dose_means[col].values
        slope, intercept, r, p, se = stats.linregress(x, y)
        records.append({
            'Behavior':    col,
            'Trend_Slope': round(slope, 6),
            'Trend_Pval':  round(p, 6),
            'R_squared':   round(r ** 2, 4),
        })

    return pd.DataFrame(records)


def validate_effect_size(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dose 0(대조군) vs Dose 6(고농도) 간 Cohen's d와 95% Confidence Interval을 산출합니다.
    """
    records = []
    dose0 = df[df['Dose'] == 0]
    dose6 = df[df['Dose'] == 6]

    # 개체별 평균 사용 (반복 측정 의존성 완화)
    d0_means = dose0.groupby('Animal_ID')[SCORE_COLS].mean()
    d6_means = dose6.groupby('Animal_ID')[SCORE_COLS].mean()

    for col in SCORE_COLS:
        if col not in d0_means.columns:
            continue
        a = d0_means[col].values
        b = d6_means[col].values
        d = _cohens_d(b, a)  # Dose6 - Dose0 방향

        # Welch's t-test로 95% CI 산출
        t, p = stats.ttest_ind(b, a, equal_var=False)
        se = np.sqrt(b.var(ddof=1) / len(b) + a.var(ddof=1) / len(a))
        df_t = len(a) + len(b) - 2
        ci95 = stats.t.ppf(0.975, df_t) * se

        records.append({
            'Behavior': col,
            'Cohens_d': round(d, 4),
            'T_pval':   round(p, 6),
            'CI95_low': round((b.mean() - a.mean()) - ci95, 4),
            'CI95_high':round((b.mean() - a.mean()) + ci95, 4),
        })

    return pd.DataFrame(records)


def run_validation(df: pd.DataFrame, mixed_model_summary: pd.DataFrame) -> dict:
    """
    전체 Validation을 실행하고 결과를 딕셔너리로 반환합니다.
    """
    print("=== [1] Dose Effect (Mixed Model p-value) ===")
    dose_effect = validate_dose_effect(df, mixed_model_summary)
    print(dose_effect.to_string(index=False))

    print("\n=== [2] Dose-response Trend Test ===")
    trend = validate_trend(df)
    print(trend.to_string(index=False))

    print("\n=== [3] Effect Size & 95% CI (Dose 0 vs Dose 6) ===")
    effect = validate_effect_size(df)
    print(effect.to_string(index=False))

    return {
        'dose_effect': dose_effect,
        'trend':       trend,
        'effect_size': effect,
    }
 