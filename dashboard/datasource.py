"""
dashboard/datasource.py — 대시보드 데이터 접근 계층(모든 페이지 공유)
─────────────────────────────────────────────────────────────
역할: DB(PostgreSQL, 없으면 SQLite 샘플)에서 조회·집계·통계분석을 수행해
      페이지에 DataFrame/dict 로 돌려준다. 페이지는 SQL 을 직접 쓰지 않는다.

주요 흐름:
  get_animals/get_group_means/get_model_results  → 목록·KPI·도넛
  run_comparison/compare_individuals/compare_time_windows → 비교 분석(통계)
  get_coords → 개체 궤적·히트맵 좌표(샘플 DB 직접 읽기)

※ 모듈명이 datasource 인 이유: 프로젝트 루트의 data/ 폴더와 이름 충돌 방지.
※ sys.path 설정은 진입점 app.py 에서 일괄 처리(여기서 안 함). 테스트는 conftest.py.
"""
import os
import warnings
import numpy as np
import pandas as pd
import streamlit as st
from db.schema import SCHEMA, read_sql as _db_read, using_sqlite, get_conn, init_experiments_table
# 공용 상수는 src/constants.py 단일 출처에서 가져와 페이지로 재export 한다
from src.constants import (
    SCORE_COLS, BEH_KR, BEH_EN, INVERSE_BEH, DOSE_COLORS, BEH_COLOR, FPS,
)

warnings.filterwarnings('ignore')  # pandas read_sql DBAPI 경고 억제


def _read(sql, params=None):
    # PostgreSQL ↔ SQLite 샘플 폴백을 자동 처리하는 공용 읽기 계층
    return _db_read(sql, params=params)


# ── 개체(animals) ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_animals() -> pd.DataFrame:
    """개체 메타 + 데이터량(프레임 수)·실험 시간(초)·상태를 합쳐 반환."""
    sql = f"""
        SELECT a.animal_id, a.dose, a.group_name,
               COUNT(s.id)        AS n_frames,
               MAX(s.frame)        AS max_frame
        FROM {SCHEMA}.animals a
        LEFT JOIN {SCHEMA}.scores s ON s.animal_id = a.animal_id
        GROUP BY a.animal_id, a.dose, a.group_name
        ORDER BY a.dose, a.animal_id;
    """
    df = _read(sql)
    df['n_frames'] = df['n_frames'].fillna(0).astype(int)
    df['duration_sec'] = (df['max_frame'].fillna(0) / FPS).round(0).astype(int)
    df['dose_label'] = df['dose'].apply(lambda d: f"{'Control' if d == 0 else 'Dose ' + str(int(d))} ({int(d)} mg/kg)")
    # 데이터 보유 여부 기반 상태
    df['status'] = np.where(df['n_frames'] > 0, '정상', '데이터 없음')
    return df


@st.cache_data(ttl=300)
def get_animal_means() -> pd.DataFrame:
    """개체별 평균 행동 점수."""
    cols = ', '.join([f'AVG(s.{c}) AS {c}' for c in SCORE_COLS])
    sql = f"""
        SELECT s.animal_id, a.dose, {cols}
        FROM {SCHEMA}.scores s
        JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
        GROUP BY s.animal_id, a.dose
        ORDER BY a.dose, s.animal_id;
    """
    return _read(sql)


@st.cache_data(ttl=300)
def get_group_means() -> pd.DataFrame:
    """투여군(dose)별 평균 행동 점수 + 개체 수."""
    cols = ', '.join([f'AVG(s.{c}) AS {c}' for c in SCORE_COLS])
    sql = f"""
        SELECT a.dose, COUNT(DISTINCT s.animal_id) AS n, {cols}
        FROM {SCHEMA}.scores s
        JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
        GROUP BY a.dose ORDER BY a.dose;
    """
    return _read(sql)


@st.cache_data(ttl=300)
def get_model_results() -> pd.DataFrame:
    """최신 LME 혼합 모델 결과(행동별 1행)."""
    sql = f"""
        SELECT m.behavior, m.dose_coef, m.dose_pval, m.time_coef, m.time_pval,
               m.random_var, m.status, m.run_at
        FROM {SCHEMA}.model_results m
        WHERE m.run_at = (
            SELECT MAX(m2.run_at) FROM {SCHEMA}.model_results m2
            WHERE m2.behavior = m.behavior)
        ORDER BY m.behavior;
    """
    return _read(sql)


@st.cache_data(ttl=300)
def get_validation() -> pd.DataFrame:
    """검증(추세/효과크기) 지표."""
    return _read(f"SELECT test_type, behavior, metric_name, metric_value FROM {SCHEMA}.validation;")


@st.cache_data(ttl=600)
def get_coords(animal_id: str) -> pd.DataFrame:
    """개체의 bodycentre x/y 궤적(1fps). 번들 샘플 DB 에서 직접 읽는다(백엔드 무관)."""
    import sqlite3
    from db.schema import SAMPLE_DB
    if not os.path.exists(SAMPLE_DB):
        return pd.DataFrame(columns=['frame', 'x', 'y'])
    con = sqlite3.connect(SAMPLE_DB)
    try:
        has = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coords'").fetchone()
        if not has:
            return pd.DataFrame(columns=['frame', 'x', 'y'])
        return pd.read_sql("SELECT frame, x, y FROM coords WHERE animal_id = ? ORDER BY frame",
                           con, params=(animal_id,))
    finally:
        con.close()


# ── 집계 지표 (대시보드 KPI 등) ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_overview() -> dict:
    """대시보드 상단 카드용 핵심 수치."""
    animals = get_animals()
    groups = get_group_means()
    models = get_model_results()
    n_completed = int((models['status'] == 'OK').sum()) if not models.empty else 0
    # 대조군 대비 분석 가능한 비교 실험 = 투여군 수
    n_dose_groups = int((groups['dose'] != 0).sum())
    return {
        'total_animals': int(len(animals)),
        'total_groups': int(len(groups)),
        'experiments': n_dose_groups,        # Control vs 각 dose 비교 실험
        'completed_analyses': n_completed,
        'total_frames': int(animals['n_frames'].sum()),
    }


# ── 비교 분석 실제 실행 ──────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def _binned_scores(doses: tuple, metrics: tuple) -> pd.DataFrame:
    """선택 투여군의 개체별·초당(1s bin) 평균 점수 — LME 입력용."""
    mcols = ', '.join([f'AVG(s.{m}) AS {m}' for m in metrics])
    dose_list = ','.join(str(int(d)) for d in doses)
    sql = f"""
        SELECT s.animal_id, a.dose, (s.frame / {FPS}) AS tbin, {mcols}
        FROM {SCHEMA}.scores s
        JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
        WHERE a.dose IN ({dose_list})
        GROUP BY s.animal_id, a.dose, (s.frame / {FPS});
    """
    return _read(sql)


def update_animal_group(animal_id: str, group_name: str) -> tuple[bool, str]:
    """개체의 group_name 을 갱신한다. PostgreSQL 및 SQLite 공통 지원."""
    sql = f"UPDATE {SCHEMA}.animals SET group_name = ? WHERE animal_id = ?" if using_sqlite() else f"UPDATE {SCHEMA}.animals SET group_name = %s WHERE animal_id = %s"
    try:
        with get_conn() as conn:
            if using_sqlite():
                conn.execute(sql, (group_name, animal_id))
            else:
                with conn.cursor() as cur:
                    cur.execute(sql, (group_name, animal_id))
        get_animals.clear()  # 캐시 무효화
        return True, "저장되었습니다."
    except Exception as e:
        return False, f"저장 실패: {e}"


def get_experiments() -> pd.DataFrame:
    """실험 테이블에서 목록을 읽어옵니다. 테이블이 비어있으면 기본 실험 5종을 프리폴딩합니다."""
    init_experiments_table()
    
    sql = f"""
        SELECT name, experiment_type, base_dose, comp_doses, metrics, animal_ids, status, created_at 
        FROM {SCHEMA}.experiments 
        ORDER BY created_at DESC;
    """
    df = _read(sql)
    
    if df.empty:
        # 기본 실험 프리폴딩
        all_metrics = "locomotion,exploration,anxiety,hyperactivity,freezing"
        defaults = [
            ("Yohimbine Dose 1 vs Control", "Open Field", 0, "1", all_metrics, "", "분석 완료"),
            ("Yohimbine Dose 3 vs Control", "Open Field", 0, "3", all_metrics, "", "분석 완료"),
            ("Yohimbine Dose 6 vs Control", "Open Field", 0, "6", all_metrics, "", "분석 완료"),
            ("All Dose Comparison", "Open Field", 0, "1,3,6", all_metrics, "", "분석 완료"),
            ("Control Baseline", "Open Field", 0, "", all_metrics, "", "업로드 완료"),
        ]
        
        for name, etype, bd, cd, mt, ams, status in defaults:
            save_experiment(name, etype, bd, [int(x) for x in cd.split(',') if x], mt.split(','), ams.split(',') if ams else None, status)
            
        df = _read(sql)
        
    return df


def save_experiment(name: str, experiment_type: str, base_dose: int, comp_doses: list[int], metrics: list[str], animal_ids: list[str] | None = None, status: str = '분석 완료') -> tuple[bool, str]:
    """실험 정보를 데이터베이스에 저장하거나 갱신합니다."""
    comp_doses_str = ','.join(str(int(d)) for d in comp_doses)
    metrics_str = ','.join(metrics)
    animals_str = ','.join(animal_ids) if animal_ids else None
    
    if using_sqlite():
        sql = f"""
            INSERT INTO {SCHEMA}.experiments (name, experiment_type, base_dose, comp_doses, metrics, animal_ids, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (name) DO UPDATE SET
                experiment_type=excluded.experiment_type,
                base_dose=excluded.base_dose,
                comp_doses=excluded.comp_doses,
                metrics=excluded.metrics,
                animal_ids=excluded.animal_ids,
                status=excluded.status;
        """
        params = (name, experiment_type, base_dose, comp_doses_str, metrics_str, animals_str, status)
    else:
        sql = f"""
            INSERT INTO {SCHEMA}.experiments (name, experiment_type, base_dose, comp_doses, metrics, animal_ids, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                experiment_type=EXCLUDED.experiment_type,
                base_dose=EXCLUDED.base_dose,
                comp_doses=EXCLUDED.comp_doses,
                metrics=EXCLUDED.metrics,
                animal_ids=EXCLUDED.animal_ids,
                status=EXCLUDED.status;
        """
        params = (name, experiment_type, base_dose, comp_doses_str, metrics_str, animals_str, status)

    try:
        with get_conn() as conn:
            if using_sqlite():
                conn.execute(sql, params)
            else:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
        return True, "저장되었습니다."
    except Exception as e:
        return False, f"저장 실패: {e}"


def delete_experiment(name: str) -> tuple[bool, str]:
    """특정 실험을 데이터베이스에서 삭제합니다."""
    sql = f"DELETE FROM {SCHEMA}.experiments WHERE name = ?;" if using_sqlite() else f"DELETE FROM {SCHEMA}.experiments WHERE name = %s;"
    try:
        with get_conn() as conn:
            if using_sqlite():
                conn.execute(sql, (name,))
            else:
                with conn.cursor() as cur:
                    cur.execute(sql, (name,))
        return True, "삭제되었습니다."
    except Exception as e:
        return False, f"삭제 실패: {e}"


@st.cache_data(ttl=600, show_spinner=False)
def _binned_scores_animals(animal_ids: tuple, metrics: tuple) -> pd.DataFrame:
    """지정 개체들의 초당(1s bin) 평균 점수 — 개체별/시간대 비교용."""
    mcols = ', '.join([f'AVG(s.{m}) AS {m}' for m in metrics])
    ph = ','.join(['%s'] * len(animal_ids))
    sql = f"""
        SELECT s.animal_id, (s.frame / {FPS}) AS tbin, {mcols}
        FROM {SCHEMA}.scores s
        WHERE s.animal_id IN ({ph})
        GROUP BY s.animal_id, (s.frame / {FPS})
        ORDER BY s.animal_id, tbin;
    """
    return _read(sql, params=tuple(animal_ids))


def _cohens_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    sp = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (b.mean() - a.mean()) / sp if sp > 0 else np.nan


def compare_individuals(animal_a: str, animal_b: str, metrics: list) -> dict:
    """두 개체(A vs B)의 행동 지표를 비교한다.
    지표별 평균·차이와, 초당 시계열에 대한 t-검정(독립표본)을 산출한다."""
    from scipy import stats
    metrics = [m for m in metrics if m in SCORE_COLS]
    df = _binned_scores_animals((animal_a, animal_b), tuple(metrics))
    da = df[df['animal_id'] == animal_a]
    db = df[df['animal_id'] == animal_b]
    rows = []
    for m in metrics:
        va, vb = da[m].dropna().values, db[m].dropna().values
        try:
            _, p = stats.ttest_ind(va, vb, equal_var=False)
        except Exception:
            p = np.nan
        ma, mb = va.mean() * 100 if len(va) else np.nan, vb.mean() * 100 if len(vb) else np.nan
        rows.append({
            'metric': m, 'behavior_kr': BEH_KR[m], 'behavior_en': BEH_EN[m],
            'a_mean': ma, 'b_mean': mb, 'diff': mb - ma,
            'cohens_d': _cohens_d(va, vb), 't_pval': p, 'inverse': m in INVERSE_BEH,
        })
    return {'rows': pd.DataFrame(rows), 'a': animal_a, 'b': animal_b, 'metrics': metrics}


def compare_time_windows(animal: str, metrics: list, n_windows: int = 2) -> dict:
    """단일 개체의 행동을 시간 구간(n_windows 등분)으로 나눠 비교한다.
    각 구간 평균 + 전체 시계열(라인)을 반환한다."""
    from scipy import stats
    metrics = [m for m in metrics if m in SCORE_COLS]
    df = _binned_scores_animals((animal,), tuple(metrics)).copy()
    if df.empty:
        return {'rows': pd.DataFrame(), 'timeline': df, 'animal': animal, 'metrics': metrics, 'n_windows': n_windows}
    df['min'] = df['tbin'] / 60.0  # 분
    # 시간 구간 라벨(구간 1..n)
    edges = np.linspace(df['tbin'].min(), df['tbin'].max() + 1, n_windows + 1)
    df['win'] = pd.cut(df['tbin'], bins=edges, labels=[f"구간 {i+1}" for i in range(n_windows)],
                       include_lowest=True, right=False)
    rows = []
    for m in metrics:
        win_means = df.groupby('win', observed=True)[m].mean() * 100
        row = {'metric': m, 'behavior_kr': BEH_KR[m], 'behavior_en': BEH_EN[m], 'inverse': m in INVERSE_BEH}
        for w in win_means.index:
            row[w] = win_means[w]
        # 첫 구간 vs 마지막 구간 변화 + t검정
        first = df[df['win'] == f"구간 1"][m].dropna().values
        last = df[df['win'] == f"구간 {n_windows}"][m].dropna().values
        row['change'] = (last.mean() - first.mean()) * 100 if len(first) and len(last) else np.nan
        try:
            row['t_pval'] = stats.ttest_ind(first, last, equal_var=False)[1]
        except Exception:
            row['t_pval'] = np.nan
        rows.append(row)
    return {'rows': pd.DataFrame(rows), 'timeline': df, 'animal': animal,
            'metrics': metrics, 'n_windows': n_windows}


def run_comparison(base_dose: int, comp_doses: list, metrics: list,
                   selected_animals: list | None = None) -> dict:
    """
    실제 비교 분석을 수행한다.
      • 기준군(base_dose) vs 비교군(comp_doses)
      • 각 지표마다: 그룹 평균, 개체평균 t-검정, Cohen's d 효과크기,
        선형 혼합 효과 모델(LME, Dose+Time, 개체 random effect) 계수·p값
    1초 단위로 다운샘플링하여 LME를 빠르게 피팅한다.

    Returns dict: {'rows': DataFrame, 'group_means': DataFrame, 'meta': {...}}
    """
    import statsmodels.formula.api as smf
    from scipy import stats

    metrics = [m for m in metrics if m in SCORE_COLS]
    all_doses = tuple(sorted(set([base_dose] + list(comp_doses))))
    df = _binned_scores(all_doses, tuple(metrics))
    if selected_animals:
        df = df[df['animal_id'].isin(selected_animals)]

    base = df[df['dose'] == base_dose]
    comp = df[df['dose'].isin(comp_doses)]

    rows = []
    for m in metrics:
        # 개체별 평균(검정·효과크기는 개체 단위가 통계적으로 적절)
        base_amean = base.groupby('animal_id')[m].mean()
        comp_amean = comp.groupby('animal_id')[m].mean()
        d = _cohens_d(base_amean.values, comp_amean.values)
        try:
            t_stat, t_p = stats.ttest_ind(comp_amean.values, base_amean.values, equal_var=False)
        except Exception:
            t_stat, t_p = np.nan, np.nan

        # LME: 기준+비교군 합쳐 Dose 고정효과
        sub = df[df['dose'].isin(all_doses)][['animal_id', 'dose', 'tbin', m]].dropna().copy()
        sub['Time'] = sub['tbin'] / 60.0  # 분 단위
        dose_coef, dose_p = np.nan, np.nan
        try:
            res = smf.mixedlm(f'{m} ~ dose + Time', sub, groups=sub['animal_id']).fit(method='cg', disp=False)
            dose_coef = res.params.get('dose', np.nan)
            dose_p = res.pvalues.get('dose', np.nan)
        except Exception:
            pass

        bm, cm = base_amean.mean(), comp_amean.mean()
        rows.append({
            'metric': m,
            'behavior_kr': BEH_KR[m],
            'behavior_en': BEH_EN[m],
            'base_mean': bm * 100,
            'comp_mean': cm * 100,
            'pct_change': ((cm - bm) / bm * 100) if bm else np.nan,
            'cohens_d': d,
            't_pval': t_p,
            'lme_coef': dose_coef,
            'lme_pval': dose_p,
            'inverse': m in INVERSE_BEH,
        })

    rows_df = pd.DataFrame(rows)

    # 그룹별 평균 (막대 차트용)
    gmeans = df.groupby('dose')[metrics].mean().reset_index()

    meta = {
        'base_dose': base_dose,
        'comp_doses': list(comp_doses),
        'n_base': int(base['animal_id'].nunique()),
        'n_comp': int(comp['animal_id'].nunique()),
        'metrics': metrics,
    }
    return {'rows': rows_df, 'group_means': gmeans, 'meta': meta}
