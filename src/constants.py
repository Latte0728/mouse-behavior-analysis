"""
src/constants.py — 프로젝트 공용 상수 단일 출처(Single Source of Truth)
─────────────────────────────────────────────────────────────
행동 지표 목록·한글/영문 라벨·색상·FPS 등을 여기 한 곳에서만 정의한다.
파이프라인(src/*)·대시보드(dashboard/*) 모두 이 모듈을 import 해서 쓰므로,
지표나 색을 바꿀 때 이 파일만 고치면 전체에 반영된다.

용어 주의 — 행동 점수 컬럼명이 계층마다 표기가 다르다:
  · DB / 대시보드 : 소문자        (locomotion, anxiety, ...)   → SCORE_COLS
  · 분석 파이프라인 : Title_Score  (Locomotion_Score, ...)      → SCORE_COLS_TITLE
  두 표기 변환은 SCORE_COL_MAP 으로 한다.
"""

# ── 행동 지표(소문자, DB·대시보드 표준) ──────────────────────────────────────
SCORE_COLS = ['locomotion', 'exploration', 'anxiety', 'hyperactivity', 'freezing']

# ── 행동 지표(Title_Score, 분석 파이프라인 표준) ─────────────────────────────
SCORE_COLS_TITLE = [f"{c.capitalize()}_Score" for c in SCORE_COLS]

# 소문자 ↔ Title_Score 상호 변환 매핑
SCORE_COL_MAP = dict(zip(SCORE_COLS, SCORE_COLS_TITLE))       # locomotion -> Locomotion_Score
SCORE_COL_MAP_INV = dict(zip(SCORE_COLS_TITLE, SCORE_COLS))   # Locomotion_Score -> locomotion

# ── 라벨 ────────────────────────────────────────────────────────────────────
BEH_KR = {
    'locomotion': '이동성', 'exploration': '탐색성', 'anxiety': '불안',
    'hyperactivity': '과활동성', 'freezing': '경직',
}
BEH_EN = {
    'locomotion': 'Locomotion', 'exploration': 'Exploration', 'anxiety': 'Anxiety',
    'hyperactivity': 'Hyperactivity', 'freezing': 'Freezing',
}

# 값이 높을수록 부정적인 지표(증가가 "나쁨") — 증감 색상 반전에 사용
INVERSE_BEH = {'anxiety', 'freezing'}

# ── 색상 ────────────────────────────────────────────────────────────────────
# 투여군(dose mg/kg)별 색
DOSE_COLORS = {0: '#4C72B0', 1: '#55A868', 3: '#C44E52', 6: '#8172B2'}
DOSE_PALETTE = DOSE_COLORS  # 파이프라인 쪽 기존 명칭 별칭

# 행동 지표별 색(타임라인 등)
BEH_COLOR = {
    'locomotion': '#3b82f6', 'exploration': '#22c55e', 'anxiety': '#ef4444',
    'hyperactivity': '#a855f7', 'freezing': '#d97706', 'grooming': '#8b5cf6',
}

# ── 영상/시간 ───────────────────────────────────────────────────────────────
FPS = 30  # 분석 영상 프레임레이트(30fps) — 프레임↔초 변환의 기준
 