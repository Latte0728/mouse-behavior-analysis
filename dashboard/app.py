"""
dashboard/app.py — Streamlit 대시보드 진입점(라우팅·전역 설정)
─────────────────────────────────────────────────────────────
역할: sys.path 등록(루트·dashboard), 백그라운드 영상 서버 기동(영상 폴더가 있을 때만),
      전역 스타일/폰트, st.navigation 으로 5개 페이지 라우팅.
※ 페이지보다 먼저 매 rerun 마다 실행되는 메인 스크립트.
"""
import os
import sys

# ── 모듈 경로 설정(이 진입점에서 한 번만) ───────────────────────────────────
# app.py 는 st.navigation 의 메인 스크립트라 매 rerun 마다 페이지보다 먼저 실행된다.
# 여기서 프로젝트 루트(=db, src import용)와 dashboard(=datasource import용)를
# sys.path 에 한 번만 추가하면, 각 페이지에서 sys.path.insert 반복이 불필요해진다.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in (PROJECT_ROOT, _DASHBOARD_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import matplotlib.pyplot as plt

# 영상 폴더 경로 (절대경로 하드코딩 제거 → 어느 머신에서도 재현 가능)
VIDEO_DIR = os.environ.get("BEHAVIOR_VIDEO_DIR", os.path.join(PROJECT_ROOT, "Videos"))

# ── 백그라운드 영상 서버 (영상 폴더가 있을 때만 구동) ─────────────────────
def start_video_server(port, directory):
    class CORSRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Accept-Ranges', 'bytes')
            super().end_headers()

    httpd = HTTPServer(('127.0.0.1', port), CORSRequestHandler)
    httpd.serve_forever()

# 영상은 gitignore 대상이라 클론 환경엔 없을 수 있음 → 폴더가 있을 때만 서버 기동
if 'video_port' not in st.session_state and os.path.isdir(VIDEO_DIR):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    
    t = threading.Thread(target=start_video_server, args=(port, VIDEO_DIR), daemon=True)
    t.start()
    st.session_state.video_port = port

# 전역 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(
    page_title="Laboratory AI Platform",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* 메인 배경색 (전체 화이트 테마) */
    [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
    }
    [data-testid="stHeader"] { background: transparent; }

    /* ── 사이드바: 화이트 테마 ───────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e8edf3;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {
        color: #1e293b !important;
    }

    /* 네비게이션 아이템 (화이트 베이스 + 블루 액티브) */
    [data-testid="stSidebarNav"] ul { padding-top: 4px; }
    [data-testid="stSidebarNav"] li div a {
        border-radius: 8px;
        margin: 2px 6px;
        padding: 8px 12px;
        transition: background 0.15s ease;
    }
    [data-testid="stSidebarNav"] li div a span { color: #475569 !important; font-weight: 500; }
    [data-testid="stSidebarNav"] li div a:hover { background-color: #f1f5f9; }
    [data-testid="stSidebarNav"] li div a:hover span { color: #1e293b !important; }
    /* 현재 선택된 페이지 */
    [data-testid="stSidebarNav"] li div a[aria-current="page"] {
        background-color: #2563eb;
    }
    [data-testid="stSidebarNav"] li div a[aria-current="page"] span { color: #ffffff !important; }

    /* 사이드바 요소 순서 뒤집기 (로고를 맨 위로) */
    [data-testid="stSidebarContent"] {
        display: flex;
        flex-direction: column;
    }
    [data-testid="stSidebarNav"] {
        order: 2;
        margin-top: 6px;
    }
    [data-testid="stSidebarUserContent"] {
        order: 1;
    }

    /* 불필요 UI 숨김 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 상단 로고 ──────────────────────────────────────────────
st.sidebar.markdown("""
<div style="display:flex; align-items:center; margin-bottom:6px; padding-top:18px;">
    <div style="background:#2563eb; width:34px; height:34px; border-radius:9px; margin-right:10px; display:flex; align-items:center; justify-content:center;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10a4 4 0 0 0-4-4h-2a6 6 0 0 0-6 6v2a6 6 0 0 0 6 6h12a2 2 0 0 0 2-2v-4a4 4 0 0 0-4-4z"/><circle cx="15" cy="11" r="1"/><path d="M4 12c-1.1 0-2 .9-2 2v2"/></svg>
    </div>
    <h3 style="margin:0; font-size:1.05rem; font-weight:800; color:#0f172a !important;">Laboratory AI Platform</h3>
</div>
<div style="color:#64748b !important; font-size:0.82rem; margin-bottom:24px; padding-left:2px;">행동 분석 대시보드</div>
""", unsafe_allow_html=True)

# ── Navigation 설정 ───────────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/01_dashboard.py", title="대시보드"),
    st.Page("pages/02_experiments.py", title="실험 관리"),
    st.Page("pages/03_mice.py", title="개체 관리"),
    st.Page("pages/04_comparison.py", title="비교 분석"),
    st.Page("pages/05_mouse_detail.py", title="단일 개체 분석"),
])

# 페이지 렌더링
pg.run()
  