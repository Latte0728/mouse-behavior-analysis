"""
Analysis Layer - mixed_model.py
---------------------------------
선형 혼합 효과 모델(Linear Mixed Effects Model) 구현.

모델 공식:
    y_it = β0 + β1·Dose_i + β2·Time_t + b_i + ε_it

    - y_it   : 행동 강도 점수 (Behavioral Intensity Score)
    - Dose_i : 투여 농도 고정 효과 (0, 1, 3, 6)
    - Time_t : 시간 경과 고정 효과
    - b_i    : 개체(Animal_ID) 무작위 효과 (개체 간 편차 통제)
    - ε_it   : 잔차
"""
import pandas as pd
import statsmodels.formula.api as smf

from src.constants import FPS, SCORE_COLS_TITLE as SCORE_COLS  # 행동 점수 컬럼(Title_Score)
from config.lme import TIME_SCALE_FACTOR, FIXED_EFFECTS


def fit_mixed_model(df: pd.DataFrame, score_col: str) -> object:
    """
    단일 행동 점수에 대해 혼합 효과 모델을 피팅합니다.

    Args:
        df        : Animal_ID, Frame, Dose, {score_col} 컬럼 포함 DataFrame
        score_col : 분석할 행동 점수 컬럼명

    Returns:
        statsmodels MixedLMResults (피팅 실패 시 None)
    """
    # FIXED_EFFECTS 중 파생 컬럼(Time_Scaled)을 제외한 실제 필요 컬럼 동적 추출
    cols_to_extract = ['Animal_ID', 'Frame', score_col]
    for effect in FIXED_EFFECTS:
        if effect != 'Time_Scaled' and effect in df.columns:
            cols_to_extract.append(effect)
    
    cols_to_extract = list(dict.fromkeys(cols_to_extract))
    data = df[cols_to_extract].dropna().copy()
    
    # LME 피팅 성능 최적화 및 수렴 안정성을 위해 1초 단위(FPS프레임)로 다운샘플링
    data = data.iloc[::FPS].copy()
    
    # 수렴 안정성을 위해 프레임 단위 스케일 축소
    data['Time_Scaled'] = data['Frame'] / TIME_SCALE_FACTOR

    formula = f'{score_col} ~ ' + ' + '.join(FIXED_EFFECTS)
    try:
        model = smf.mixedlm(formula, data, groups=data['Animal_ID'])
        result = model.fit(method='cg', disp=False)
        return result
    except Exception as e:
        print(f"[MixedModel] {score_col} 피팅 실패: {e}")
        return None


def extract_summary(result, score_col: str) -> dict:
    """피팅 결과에서 핵심 통계량을 딕셔너리로 추출합니다."""
    if result is None:
        return {'Behavior': score_col, 'Status': 'FAILED'}
    return {
        'Behavior':              score_col,
        'Dose_Coef':             result.params.get('Dose'),
        'Dose_Pval':             result.pvalues.get('Dose'),
        'Time_Coef':             result.params.get('Time_Scaled'),
        'Time_Pval':             result.pvalues.get('Time_Scaled'),
        'Random_Effect_Var':     result.cov_re.iloc[0, 0] if not result.cov_re.empty else None,
        'Status':                'OK',
    }


def run_all_models(df: pd.DataFrame) -> pd.DataFrame:
    """
    5가지 행동 점수 전체에 대해 혼합 모델을 실행하고
    요약 통계를 DataFrame으로 반환합니다.
    """
    summaries = []
    for col in SCORE_COLS:
        if col not in df.columns:
            continue
        print(f"[MixedModel] Fitting: {col} ...")
        result = fit_mixed_model(df, col)
        summaries.append(extract_summary(result, col))
    return pd.DataFrame(summaries)
