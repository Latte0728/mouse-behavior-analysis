"""
DB Layer - schema.py
---------------------
PostgreSQL 연동 모듈.
스키마: mouse_behavior (기존 mimic4/chym 스키마와 완전히 분리)

테이블 구조:
    mouse_behavior.animals      - 개체 메타데이터
    mouse_behavior.scores       - 프레임별 행동 강도 점수
    mouse_behavior.model_results - 혼합 모델 분석 결과
    mouse_behavior.validation   - 통계 검증 결과
"""
import os
import sqlite3
import psycopg2
import psycopg2.extras
import pandas as pd
from contextlib import contextmanager

# 행동 점수 컬럼명은 단일 출처(src/constants)에서 — DB는 소문자, 원본 df는 Title_Score
from src.constants import SCORE_COLS, SCORE_COL_MAP
from config.database import DB_CONFIG, DEFAULT_BATCH_SIZE
from config.csv import CSV_MAPPING

SCHEMA = 'mouse_behavior'

# 번들 샘플(SQLite) — PostgreSQL 이 없는 환경(면접관/클론)에서의 폴백 데이터
SAMPLE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '..', 'dashboard', 'sample_data', 'behavior_sample.db')
_BACKEND = None  # 'postgres' | 'sqlite' (최초 1회 결정 후 캐시)


@contextmanager
def get_conn():
    """쓰기/파이프라인용 — 백엔드에 맞춰 PostgreSQL 또는 SQLite 에 연결한다."""
    if using_sqlite():
        conn = sqlite3.connect(':memory:')
        conn.execute(f"ATTACH DATABASE ? AS {SCHEMA}", (os.path.abspath(SAMPLE_DB),))
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


# ── 읽기 계층: PostgreSQL 우선, 없으면 SQLite 샘플로 폴백 ─────────────────────
def _detect_backend() -> str:
    """PostgreSQL 연결을 시도하고, 실패하면 SQLite 샘플로 폴백한다."""
    global _BACKEND
    if _BACKEND is not None:
        return _BACKEND
    if os.environ.get('BEHAVIOR_FORCE_SQLITE') == '1':
        _BACKEND = 'sqlite'
        return _BACKEND
    try:
        conn = psycopg2.connect(connect_timeout=2, **DB_CONFIG)
        conn.close()
        _BACKEND = 'postgres'
    except Exception:
        if os.path.exists(SAMPLE_DB):
            _BACKEND = 'sqlite'
            os.environ['BEHAVIOR_FORCE_SQLITE'] = '1'
        else:
            raise RuntimeError(
                "PostgreSQL 에 연결할 수 없고 샘플 DB도 없습니다. "
                "`python scripts/build_sample.py` 로 샘플을 생성하거나 DB를 기동하세요.")
    return _BACKEND


def using_sqlite() -> bool:
    return _detect_backend() == 'sqlite'


@contextmanager
def get_read_conn():
    """조회 전용 연결. 백엔드에 따라 psycopg2 또는 sqlite3 를 돌려준다."""
    if _detect_backend() == 'postgres':
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            yield conn
        finally:
            conn.close()
    else:
        # :memory: 에 샘플 파일을 mouse_behavior 스키마로 ATTACH → `SCHEMA.table` 그대로 동작
        conn = sqlite3.connect(':memory:')
        conn.execute(f"ATTACH DATABASE ? AS {SCHEMA}", (os.path.abspath(SAMPLE_DB),))
        try:
            yield conn
        finally:
            conn.close()


def read_sql(sql: str, params=None) -> pd.DataFrame:
    """백엔드 차이를 흡수하는 조회 헬퍼 (placeholder %s ↔ ? 변환)."""
    with get_read_conn() as conn:
        if _detect_backend() == 'sqlite':
            sql = sql.replace('%s', '?')
        return pd.read_sql(sql, conn, params=params)


# ── DDL: 스키마 및 테이블 생성 ────────────────────────────────────────────
DDL = f"""
CREATE SCHEMA IF NOT EXISTS {SCHEMA};

CREATE TABLE IF NOT EXISTS {SCHEMA}.animals (
    animal_id   TEXT        PRIMARY KEY,
    dose        INTEGER     NOT NULL,
    group_name  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS {SCHEMA}.scores (
    id              BIGSERIAL   PRIMARY KEY,
    animal_id       TEXT        REFERENCES {SCHEMA}.animals(animal_id),
    frame           INTEGER     NOT NULL,
    locomotion      REAL,
    exploration     REAL,
    anxiety         REAL,
    hyperactivity   REAL,
    freezing        REAL
);

CREATE INDEX IF NOT EXISTS idx_scores_animal ON {SCHEMA}.scores(animal_id);
CREATE INDEX IF NOT EXISTS idx_scores_frame  ON {SCHEMA}.scores(animal_id, frame);

CREATE TABLE IF NOT EXISTS {SCHEMA}.model_results (
    id              SERIAL      PRIMARY KEY,
    behavior        TEXT        NOT NULL,
    dose_coef       DOUBLE PRECISION,
    dose_pval       DOUBLE PRECISION,
    time_coef       DOUBLE PRECISION,
    time_pval       DOUBLE PRECISION,
    random_var      DOUBLE PRECISION,
    status          TEXT,
    run_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS {SCHEMA}.validation (
    id              SERIAL      PRIMARY KEY,
    test_type       TEXT        NOT NULL,  -- 'trend' | 'effect_size'
    behavior        TEXT        NOT NULL,
    metric_name     TEXT        NOT NULL,
    metric_value    DOUBLE PRECISION,
    run_at          TIMESTAMPTZ DEFAULT NOW()
);
"""


def init_schema():
    """스키마 및 모든 테이블을 생성합니다. 이미 존재하면 무시합니다."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            if not using_sqlite():
                # PostgreSQL의 경우 기존 REAL 타입을 DOUBLE PRECISION으로 변경 (작은 p-value 지원)
                cur.execute(f"ALTER TABLE {SCHEMA}.model_results ALTER COLUMN dose_coef TYPE DOUBLE PRECISION;")
                cur.execute(f"ALTER TABLE {SCHEMA}.model_results ALTER COLUMN dose_pval TYPE DOUBLE PRECISION;")
                cur.execute(f"ALTER TABLE {SCHEMA}.model_results ALTER COLUMN time_coef TYPE DOUBLE PRECISION;")
                cur.execute(f"ALTER TABLE {SCHEMA}.model_results ALTER COLUMN time_pval TYPE DOUBLE PRECISION;")
                cur.execute(f"ALTER TABLE {SCHEMA}.model_results ALTER COLUMN random_var TYPE DOUBLE PRECISION;")
                cur.execute(f"ALTER TABLE {SCHEMA}.validation ALTER COLUMN metric_value TYPE DOUBLE PRECISION;")
    print(f"[DB] Schema '{SCHEMA}' initialized.")


# ── 데이터 저장 함수 ──────────────────────────────────────────────────────
def save_animals(df_meta: pd.DataFrame):
    """animals 테이블에 개체 메타데이터를 upsert 합니다."""
    rows = [
        (row['Animal_ID'], int(row[CSV_MAPPING["dose"]]), row.get(CSV_MAPPING["group"], None))
        for _, row in df_meta.iterrows()
    ]
    sql = f"""
        INSERT INTO {SCHEMA}.animals (animal_id, dose, group_name)
        VALUES %s
        ON CONFLICT (animal_id) DO UPDATE
            SET dose = EXCLUDED.dose,
                group_name = EXCLUDED.group_name;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    print(f"[DB] {len(rows)} animals saved.")


def save_scores(df: pd.DataFrame, batch_size: int = DEFAULT_BATCH_SIZE):
    """scores 테이블에 프레임별 행동 점수를 배치 저장합니다.
    컬럼 순서·이름은 모두 constants.SCORE_COLS(소문자) / SCORE_COL_MAP(→Title_Score)에서 온다."""
    cols_sql = ', '.join(SCORE_COLS)  # locomotion, exploration, ...
    sql = f"""
        INSERT INTO {SCHEMA}.scores (animal_id, frame, {cols_sql})
        VALUES %s
        ON CONFLICT DO NOTHING;
    """

    # 성능 최적화: iterrows() 대신 itertuples()를 사용하여 대용량 DataFrame 행을 빠르게 리스트로 변환
    target_cols = ['Animal_ID', 'Frame'] + [SCORE_COL_MAP[c] for c in SCORE_COLS]
    df_sub = df[target_cols].copy()
    df_sub['Frame'] = df_sub['Frame'].astype(int)
    rows = list(df_sub.itertuples(index=False, name=None))
    total = len(rows)

    with get_conn() as conn:
        with conn.cursor() as cur:
            for i in range(0, total, batch_size):
                psycopg2.extras.execute_values(cur, sql, rows[i:i+batch_size])
                print(f"[DB] scores: {min(i+batch_size, total):,}/{total:,} rows saved.")

    print(f"[DB] All {total:,} score rows saved.")


def save_model_results(df_summary: pd.DataFrame):
    """model_results 테이블에 혼합 모델 결과를 저장합니다."""
    rows = [
        (
            str(r.get('Behavior')),
            float(r['Dose_Coef']) if r.get('Dose_Coef') is not None else None,
            float(r['Dose_Pval']) if r.get('Dose_Pval') is not None else None,
            float(r['Time_Coef']) if r.get('Time_Coef') is not None else None,
            float(r['Time_Pval']) if r.get('Time_Pval') is not None else None,
            float(r['Random_Effect_Var']) if r.get('Random_Effect_Var') is not None else None,
            str(r.get('Status', 'OK')),
        )
        for _, r in df_summary.iterrows()
    ]
    sql = f"""
        INSERT INTO {SCHEMA}.model_results
            (behavior, dose_coef, dose_pval, time_coef, time_pval, random_var, status)
        VALUES %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    print(f"[DB] {len(rows)} model results saved.")


def save_validation(val_results: dict):
    """validation 테이블에 Trend Test 및 Effect Size 결과를 저장합니다."""
    rows = []
    for test_type, df in val_results.items():
        if df is None or df.empty:
            continue
        for _, r in df.iterrows():
            behavior = str(r.get('Behavior', ''))
            for col in r.index:
                if col == 'Behavior':
                    continue
                val = r[col]
                if val is not None:
                    rows.append((test_type, behavior, col, float(val)))

    sql = f"""
        INSERT INTO {SCHEMA}.validation (test_type, behavior, metric_name, metric_value)
        VALUES %s;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, rows)
    print(f"[DB] {len(rows)} validation metrics saved.")


# ── 조회 함수 (Dashboard용) ───────────────────────────────────────────────
def query_scores(animal_id: str = None, dose: int = None) -> pd.DataFrame:
    """scores 테이블을 조회합니다."""
    conditions = []
    params = []
    if animal_id:
        conditions.append("s.animal_id = %s")
        params.append(animal_id)
    if dose is not None:
        conditions.append("a.dose = %s")
        params.append(int(dose))  # numpy.int64 → Python int 변환

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT s.animal_id, a.dose, s.frame,
               s.locomotion, s.exploration, s.anxiety,
               s.hyperactivity, s.freezing
        FROM {SCHEMA}.scores s
        JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
        {where}
        ORDER BY s.animal_id, s.frame;
    """
    return read_sql(sql, params=params or None)


def query_model_results() -> pd.DataFrame:
    """model_results 테이블의 최신 결과를 조회합니다 (행동별 최신 1행, 이식성 쿼리)."""
    sql = f"""
        SELECT m.behavior, m.dose_coef, m.dose_pval,
               m.time_coef, m.time_pval, m.random_var, m.status, m.run_at
        FROM {SCHEMA}.model_results m
        WHERE m.run_at = (
            SELECT MAX(m2.run_at) FROM {SCHEMA}.model_results m2
            WHERE m2.behavior = m.behavior)
        ORDER BY m.behavior;
    """
    return read_sql(sql)


def query_animals() -> pd.DataFrame:
    """animals 테이블 전체를 조회합니다."""
    return read_sql(f"SELECT animal_id, dose, group_name FROM {SCHEMA}.animals ORDER BY dose, animal_id;")


def init_experiments_table():
    """experiments 테이블을 생성합니다. 존재하면 무시합니다."""
    if using_sqlite():
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.experiments (
            id              INTEGER     PRIMARY KEY AUTOINCREMENT,
            name            TEXT        NOT NULL UNIQUE,
            experiment_type TEXT        NOT NULL DEFAULT 'Open Field',
            base_dose       INTEGER     NOT NULL,
            comp_doses      TEXT        NOT NULL,
            metrics         TEXT        NOT NULL,
            animal_ids      TEXT,
            status          TEXT        NOT NULL DEFAULT '업로드 완료',
            created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP
        );
        """
    else:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.experiments (
            id              SERIAL      PRIMARY KEY,
            name            TEXT        NOT NULL UNIQUE,
            experiment_type TEXT        NOT NULL DEFAULT 'Open Field',
            base_dose       INTEGER     NOT NULL,
            comp_doses      TEXT        NOT NULL,
            metrics         TEXT        NOT NULL,
            animal_ids      TEXT,
            status          TEXT        NOT NULL DEFAULT '업로드 완료',
            created_at      TIMESTAMPTZ DEFAULT NOW()
        );
        """
    with get_conn() as conn:
        if using_sqlite():
            conn.execute(ddl)
        else:
            with conn.cursor() as cur:
                cur.execute(ddl)
