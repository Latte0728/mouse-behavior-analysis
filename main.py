"""
main.py - 전체 파이프라인 실행 스크립트
==========================================
Data → Feature → State → Scoring → Analysis → Validation 순서로 실행합니다.
"""
import os
import pandas as pd

# ── 경로 설정 ─────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
METADATA_PATH = os.path.join(BASE_DIR, 'METADATA_ROCHE.csv')
DATA_DIR      = os.path.join(BASE_DIR, 'data', 'Yohimbine_Roche')
OUTPUT_DIR    = os.path.join(BASE_DIR, 'outputs')

# ── 모듈 임포트 ───────────────────────────────────────────────────────────
from src.data.loader            import build_dataset
from src.features.kinematics    import calculate_kinematics
from src.features.spatial       import calculate_spatial_features
from src.features.morphology    import calculate_morphology
from src.state.representation   import compute_state_vector
from src.scoring.continuous_score import calculate_scores
from src.analysis.mixed_model   import run_all_models
from src.analysis.comparison    import (
    plot_trajectory, plot_heatmap,
    plot_continuous_scores, plot_dose_response, plot_distribution
)
from src.validation.validate_model import run_validation
from db.schema import (
    init_schema, save_animals, save_scores,
    save_model_results, save_validation
)


def main():
    """전체 분석 파이프라인을 순차 실행한다.

    DLC CSV → df(원시 좌표) → 특성 추가 → 정규화 → 점수 → 혼합모델/검증 → PostgreSQL 적재.
    하나의 df 를 단계마다 누적 변형하며, 결과물(PNG·CSV)은 outputs/ 에, 지표는 DB에 저장한다.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ── 1. 데이터 계층: DLC 좌표 로드·전처리 → df 생성 ───────────────────────
    print("\n[1/6] 데이터 계층: 데이터 로드 및 전처리 ...")
    df = build_dataset(METADATA_PATH, DATA_DIR)  # df 컬럼: Frame, Animal_ID, Dose, {부위}_x/y
    print(f"      → {len(df):,} 프레임 / {df['Animal_ID'].nunique()} 개체 로드 완료")

    # ── 2. 특성 계층: 운동학·공간·형태 특성 컬럼을 df 에 추가 ────────────────
    print("\n[2/6] 특성 계층: 특성 추출 ...")
    df = calculate_kinematics(df)         # 속도·가속도 등
    df = calculate_spatial_features(df)   # 중심부 체류·벽 근접 등
    df = calculate_morphology(df)         # 자세·신체 길이 등
    print(f"      → {df.shape[1]} 컬럼으로 확장 완료")

    # ── 3. 상태 계층: 특성을 Z-score 로 정규화(개체 간 스케일 통일) ──────────
    print("\n[3/6] 상태 계층: Z-score 정규화 ...")
    df, scaler = compute_state_vector(df)

    # ── 4. 점수 계층: 정규화 특성 → 5종 행동 강도 점수(_Score 컬럼) ──────────
    print("\n[4/6] 점수 계층: 행동 강도 점수 산출 ...")
    df = calculate_scores(df)
    score_cols = [c for c in df.columns if c.endswith('_Score')]
    print(f"      → 산출된 점수: {score_cols}")

    # ── 5. 분석 계층: df → 혼합효과모델(LME) 요약 + 시각화 PNG 생성 ──────────
    print("\n[5/6] 분석 계층: 혼합 모델 피팅 및 시각화 ...")
    mixed_summary = run_all_models(df)  # 행동별 dose/time 계수·p값 요약 DataFrame
    mixed_summary.to_csv(os.path.join(OUTPUT_DIR, 'mixed_model_summary.csv'), index=False)
    print(mixed_summary.to_string(index=False))

    plot_trajectory(df, OUTPUT_DIR)
    plot_heatmap(df, OUTPUT_DIR)
    plot_continuous_scores(df, OUTPUT_DIR)
    plot_dose_response(df, OUTPUT_DIR)
    plot_distribution(df, OUTPUT_DIR)

    # ── 6. 검증 계층: 추세 검정·효과크기로 모델 결과의 통계적 타당성 확인 ────
    print("\n[6/6] 검증 계층: 통계적 유효성 검증 ...")
    val_results = run_validation(df, mixed_summary)
    val_results['trend'].to_csv(
        os.path.join(OUTPUT_DIR, 'trend_test.csv'), index=False
    )
    val_results['effect_size'].to_csv(
        os.path.join(OUTPUT_DIR, 'effect_size.csv'), index=False
    )

    # ── DB 계층: 개체·점수·모델결과·검증결과를 PostgreSQL 에 적재(대시보드 소스) ──
    print("\n[DB] PostgreSQL 저장 (mouse_behavior 스키마) ...")
    init_schema()
    df_meta = __import__('src.data.loader', fromlist=['load_metadata']).load_metadata(METADATA_PATH)
    save_animals(df_meta)
    save_scores(df)
    save_model_results(mixed_summary)
    save_validation({k: v for k, v in val_results.items() if k in ('trend', 'effect_size')})

    print(f"\n✅ 분석 완료 — 결과물 저장 위치: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
  