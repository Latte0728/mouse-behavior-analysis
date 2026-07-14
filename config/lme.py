"""config/lme.py — 선형 혼합 효과 모델(LME) 분석 관련 설정."""

# 수렴 안정성을 위한 프레임 단위 스케일 조정 비율
TIME_SCALE_FACTOR = 1000.0

# 고정 효과(Fixed Effects) 요인 목록
FIXED_EFFECTS = [
    "Dose",
    "Time_Scaled",
]
