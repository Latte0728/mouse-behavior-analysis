"""
비교 분석 함수 회귀 테스트 — 번들 SQLite 샘플 기반(conftest 가 강제).
PostgreSQL 없이도 `pytest` 한 줄로 분석 로직의 정상 동작을 검증한다.
"""
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import datasource as ds

ALL = ds.SCORE_COLS


def test_get_animals_shape():
    a = ds.get_animals()
    assert len(a) == 32
    assert {"animal_id", "dose", "group_name", "n_frames", "status"} <= set(a.columns)


def test_group_means_four_doses():
    g = ds.get_group_means()
    assert sorted(g["dose"].tolist()) == [0, 1, 3, 6]
    assert (g["n"] == 8).all()  # 그룹당 8마리


def test_get_coords_returns_points():
    aid = ds.get_animals()["animal_id"].iloc[0]
    c = ds.get_coords(aid)
    assert not c.empty
    assert {"frame", "x", "y"} <= set(c.columns)


def test_run_comparison_hyperactivity_drops_at_dose6():
    """Yohimbine 6mg/kg 군은 대조군 대비 과활동성이 유의하게 감소(d<0, p<0.05)."""
    r = ds.run_comparison(0, [6], ALL)
    rows = r["rows"].set_index("metric")
    assert r["meta"]["n_base"] == 8 and r["meta"]["n_comp"] == 8
    hyp = rows.loc["hyperactivity"]
    assert hyp["cohens_d"] < 0          # 비교군에서 감소 방향
    assert hyp["lme_pval"] < 0.05       # 통계적으로 유의


def test_compare_individuals_structure():
    ids = ds.get_animals()["animal_id"].tolist()
    r = ds.compare_individuals(ids[0], ids[20], ALL)
    assert len(r["rows"]) == len(ALL)
    assert {"a_mean", "b_mean", "diff", "t_pval"} <= set(r["rows"].columns)


def test_compare_time_windows_has_window_columns():
    aid = ds.get_animals()["animal_id"].iloc[20]
    r = ds.compare_time_windows(aid, ALL, n_windows=3)
    cols = r["rows"].columns
    assert sum(c.startswith("구간") for c in cols) == 3
    assert not r["timeline"].empty


def test_overview_counts():
    ov = ds.get_overview()
    assert ov["total_animals"] == 32
    assert ov["total_groups"] == 4
