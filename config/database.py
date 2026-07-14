"""config/database.py — 데이터베이스 접속 및 로드 관련 설정."""
import os

# PostgreSQL 접속 설정 — 자격증명은 코드에 하드코딩하지 않고 환경변수로만 주입한다.
#   PGHOST, PGDATABASE, PGUSER, PGPASSWORD
# 미설정 시 host 는 localhost, 그 외 항목은 psycopg2 기본 규칙(.pgpass / peer 인증 등)을 따른다.
# (DB 미설정 환경에서는 연결 실패 후 SQLite 샘플로 자동 폴백된다.)
DB_CONFIG = {
    key: value
    for key, value in (
        ('host',     os.environ.get('PGHOST', 'localhost')),
        ('dbname',   os.environ.get('PGDATABASE')),
        ('user',     os.environ.get('PGUSER')),
        ('password', os.environ.get('PGPASSWORD')),
    )
    if value is not None
}

# 데이터 적재 배치 크기 기본값
DEFAULT_BATCH_SIZE = 50_000
