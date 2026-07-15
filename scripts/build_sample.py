"""
scripts/build_sample.py
─────────────────────────────────────────────────────────────
PostgreSQL(mouse_behavior) → SQLite 샘플 스냅샷 빌더.

면접관/협업자가 PostgreSQL 없이도 `streamlit run` 만으로 대시보드를 재현할 수
있도록, 실제 DB의 핵심 데이터를 가벼운 SQLite 파일로 내보낸다.
  • animals / model_results / validation : 전량
  • scores : 1 fps(30프레임당 1행)로 다운샘플 → 용량 최소화(실 frame 번호 보존)

결과물: dashboard/sample_data/behavior_sample.db  (저장소에 커밋)
재생성: python scripts/build_sample.py
"""
import os
import sqlite3
import warnings
import pandas as pd

warnings.filterwarnings('ignore')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
import sys
sys.path.insert(0, ROOT)
from db.schema import get_conn, SCHEMA  # noqa: E402
from src.constants import FPS  # 단일 출처 프레임레이트(30fps) → 30프레임당 1행 다운샘플

OUT_DIR = os.path.join(ROOT, 'dashboard', 'sample_data')
OUT_DB = os.path.join(OUT_DIR, 'behavior_sample.db')
DATA_DIR = os.path.join(ROOT, 'data', 'Yohimbine_Roche')
METADATA = os.path.join(ROOT, 'METADATA_ROCHE.csv')


def extract_coords() -> pd.DataFrame:
    """DLC CSV 에서 개체별 bodycentre x/y 를 1fps 로 추출 (궤적·히트맵 시각화용).

    원시 영상/DLC(data/) 는 gitignore 대상이므로, 이 좌표를 샘플 DB 에 번들해
    클론 환경(데모)에서도 개체별 공간 시각화가 재현되도록 한다.
    """
    import glob
    from src.data.loader import load_metadata, _extract_animal_id  # noqa: E402
    if not os.path.isdir(DATA_DIR):
        print(f"[coords] DLC 데이터 폴더 없음({DATA_DIR}) → 좌표 추출 생략")
        return pd.DataFrame(columns=['animal_id', 'frame', 'x', 'y'])

    meta_ids = set(load_metadata(METADATA)['Animal_ID'])
    recs = []
    files = sorted(glob.glob(os.path.join(DATA_DIR, '*.csv')))
    for fp in files:
        aid = _extract_animal_id(os.path.basename(fp))
        if aid is None or aid not in meta_ids:
            continue
        dlc = pd.read_csv(fp, header=[1, 2], index_col=0)
        if ('bodycentre', 'x') not in dlc.columns:
            continue
        x = dlc[('bodycentre', 'x')].astype(float)
        y = dlc[('bodycentre', 'y')].astype(float)
        frames = dlc.index.to_numpy()
        mask = (frames % FPS) == 0
        recs.append(pd.DataFrame({
            'animal_id': aid, 'frame': frames[mask],
            'x': x.to_numpy()[mask], 'y': y.to_numpy()[mask],
        }))
        print(f"[coords] {aid}: {int(mask.sum())} pts")
    return pd.concat(recs, ignore_index=True) if recs else \
        pd.DataFrame(columns=['animal_id', 'frame', 'x', 'y'])


def main():
    """PostgreSQL 의 핵심 데이터를 SQLite 샘플 스냅샷으로 내보낸다.

    animals/model_results/validation 은 전량, scores 는 1fps 로 다운샘플하여
    dashboard/sample_data/behavior_sample.db 에 기록한다.
    """
    os.makedirs(OUT_DIR, exist_ok=True)
    with get_conn() as pg:
        animals = pd.read_sql(f"SELECT animal_id, dose, group_name, created_at FROM {SCHEMA}.animals", pg)
        models = pd.read_sql(f"SELECT * FROM {SCHEMA}.model_results", pg)
        valid = pd.read_sql(f"SELECT * FROM {SCHEMA}.validation", pg)
        print(f"animals={len(animals)}  model_results={len(models)}  validation={len(valid)}")
        print("scores 다운샘플(1fps) 추출 중 ...")
        scores = pd.read_sql(f"""
            SELECT animal_id, frame, locomotion, exploration, anxiety, hyperactivity, freezing
            FROM {SCHEMA}.scores
            WHERE MOD(frame, {FPS}) = 0
            ORDER BY animal_id, frame
        """, pg)
    print(f"scores(sampled)={len(scores):,}")

    print("bodycentre 좌표 추출 중 (DLC CSV) ...")
    coords = extract_coords()
    print(f"coords(sampled)={len(coords):,}")

    if os.path.exists(OUT_DB):
        os.remove(OUT_DB)
    con = sqlite3.connect(OUT_DB)
    animals.to_sql('animals', con, index=False)
    scores.reset_index(drop=False).rename(columns={'index': 'id'}).to_sql('scores', con, index=False)
    models.to_sql('model_results', con, index=False)
    valid.to_sql('validation', con, index=False)
    coords.to_sql('coords', con, index=False)
    con.execute("CREATE INDEX idx_scores_animal ON scores(animal_id)")
    con.execute("CREATE INDEX idx_scores_frame ON scores(animal_id, frame)")
    if len(coords):
        con.execute("CREATE INDEX idx_coords_animal ON coords(animal_id)")
    con.commit()
    con.close()

    size_mb = os.path.getsize(OUT_DB) / 1e6
    print(f"\n✅ 샘플 DB 생성: {OUT_DB}  ({size_mb:.1f} MB)")


if __name__ == '__main__':
    main()
  