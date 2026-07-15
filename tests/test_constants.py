"""상수 단일 출처(src/constants.py)의 일관성 검증."""
from src import constants as C


def test_score_cols_lengths_match():
    assert len(C.SCORE_COLS) == 5
    assert len(C.SCORE_COLS_TITLE) == len(C.SCORE_COLS)


def test_score_col_map_roundtrip():
    # 소문자 → Title_Score → 소문자 가 원래대로 돌아와야 한다
    for c in C.SCORE_COLS:
        title = C.SCORE_COL_MAP[c]
        assert title.endswith("_Score")
        assert C.SCORE_COL_MAP_INV[title] == c


def test_labels_cover_all_metrics():
    for c in C.SCORE_COLS:
        assert c in C.BEH_KR and c in C.BEH_EN and c in C.BEH_COLOR


def test_inverse_beh_subset():
    assert C.INVERSE_BEH <= set(C.SCORE_COLS)


def test_fps_positive():
    assert C.FPS > 0
 