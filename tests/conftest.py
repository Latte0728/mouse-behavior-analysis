"""
tests/conftest.py — 테스트 실행 시 모듈 경로·백엔드 설정
프로젝트 루트와 dashboard 를 sys.path 에 추가하고(앱 진입점 app.py 대용),
PostgreSQL 없이도 돌도록 SQLite 샘플을 강제한다.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (ROOT, os.path.join(ROOT, "dashboard")):
    if p not in sys.path:
        sys.path.insert(0, p)

# 테스트는 항상 번들 SQLite 샘플로 (로컬 PostgreSQL 유무와 무관하게 재현)
os.environ.setdefault("BEHAVIOR_FORCE_SQLITE", "1")
 