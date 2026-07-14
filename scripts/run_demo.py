"""
scripts/run_demo.py
─────────────────────────────────────────────────────────────
데모 모드(SQLite 샘플 강제) 로 대시보드를 실행하는 런처.
환경변수 전달이 확실하도록 여기서 직접 설정한 뒤 streamlit 을 띄운다.

    python scripts/run_demo.py            # 기본 포트 8541
"""
import os
import sys
import subprocess

os.environ["BEHAVIOR_FORCE_SQLITE"] = "1"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
port = sys.argv[1] if len(sys.argv) > 1 else "8541"

sys.exit(subprocess.call(
    [sys.executable, "-m", "streamlit", "run",
     os.path.join(ROOT, "dashboard", "app.py"),
     "--server.headless", "true", "--server.port", port],
    cwd=ROOT, env=os.environ,
))
