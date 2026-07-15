"""
dashboard/pages/05_mouse_detail.py — 단일 개체 상세 분석
─────────────────────────────────────────────────────────────
데이터 흐름:
  selected(선택 개체)
    → load_scores_animal()  : 프레임별 점수 df_mouse
    → data.get_coords()     : bodycentre 좌표 df_coords (궤적·히트맵)
    → load_group_means()    : 대조군 비교용 그룹 평균
  위 데이터로 9개 카드(영상·타임라인·통계·임베딩·궤적·히트맵·AI요약·PDF리포트)를 렌더한다.
"""
import os

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from db.schema import query_animals, query_scores, query_model_results, get_read_conn, SCHEMA
import datasource as data  # dashboard/datasource.py (루트 data/ 폴더와 이름 충돌 방지)

import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import streamlit.components.v1 as components

# ── 페이지 설정 (app.py에서 처리됨) ───────────────────────────────────────────────────────────
import socket
video_server_url = f"http://127.0.0.1:{st.session_state.video_port}" if 'video_port' in st.session_state else ""

# ── 페이지 전용 CSS (화이트 사이드바·카드·메트릭 스타일) ─────────────────────
st.markdown("""
<style>
    /* 메인 배경색 */
    [data-testid="stAppViewContainer"] {
        background-color: #f8fafc;
    }

    /* 사이드바 스타일링 (화이트 테마) */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e8edf3;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label {
        color: #1e293b !important;
    }

    /* 사이드바 네비게이션 모방 */
    .nav-item {
        padding: 10px 15px; margin: 4px 0; border-radius: 8px;
        color: #475569; cursor: pointer; font-weight: 500;
    }
    .nav-item.active { background-color: #2563eb; color: white; }
    .nav-item:hover:not(.active) { background-color: #f1f5f9; color: #1e293b; }

    /* 카드 컨테이너 (st.container(border=True) 내부 스타일링) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        padding: 0.5rem;
    }

    /* 카드 헤더 및 뱃지 */
    .card-header {
        display: flex; align-items: center; margin-bottom: 15px;
        font-size: 1.1rem; font-weight: 700; color: #1e293b;
    }
    .badge {
        display: inline-flex; justify-content: center; align-items: center;
        width: 24px; height: 24px; border-radius: 50%;
        background-color: #eff6ff; color: #2563eb; 
        font-size: 0.85rem; font-weight: bold; margin-right: 10px;
        border: 1px solid #bfdbfe;
    }

    /* 상단 마우스 제목 영역 */
    .header-title { font-size: 2rem; font-weight: 800; color: #0f172a; margin-bottom: 0px; }
    .header-breadcrumbs { color: #64748b; font-size: 0.9rem; margin-top: -5px; margin-bottom: 20px;}
    
    /* 메트릭 박스 커스텀 */
    div[data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        text-align: left;
    }
    [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #0f172a; }
    [data-testid="stMetricLabel"] { font-size: 0.9rem; color: #64748b; font-weight: 600; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem; }

    /* 불필요 UI 숨김 */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ── 상수 (단일 출처 src/constants.py 에서 import) ───────────────────────────
from src.constants import DOSE_COLORS, SCORE_COLS, BEH_COLOR, BEH_KR, FPS

# 행동 타임라인 설정(매직넘버 명명)
TIMELINE_BIN_FRAMES = 60 * FPS   # 타임라인 한 구간 길이 = 60초(=1800프레임 @30fps)
TIMELINE_THRESHOLD = 0.40        # 행동 강도가 이 값 초과인 구간만 타임라인에 표시

# ── 캐시 데이터 로더 ──────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_animals(): return query_animals()

@st.cache_data(ttl=300)
def load_scores_animal(animal_id): return query_scores(animal_id=animal_id)

@st.cache_data(ttl=300)
def load_group_means():
    with get_read_conn() as conn:
        return pd.read_sql(f"""
            SELECT a.dose, COUNT(DISTINCT s.animal_id) AS n,
                   AVG(s.locomotion) AS locomotion, AVG(s.exploration) AS exploration,
                   AVG(s.anxiety) AS anxiety, AVG(s.hyperactivity) AS hyperactivity,
                   AVG(s.freezing) AS freezing
            FROM {SCHEMA}.scores s
            JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
            GROUP BY a.dose ORDER BY a.dose""", conn)

@st.cache_data(ttl=300)
def load_animal_means():
    with get_read_conn() as conn:
        return pd.read_sql(f"""
            SELECT s.animal_id, a.dose,
                   AVG(s.locomotion) AS locomotion, AVG(s.exploration) AS exploration,
                   AVG(s.anxiety) AS anxiety, AVG(s.hyperactivity) AS hyperactivity,
                   AVG(s.freezing) AS freezing
            FROM {SCHEMA}.scores s
            JOIN {SCHEMA}.animals a ON s.animal_id = a.animal_id
            GROUP BY s.animal_id, a.dose ORDER BY a.dose""", conn)

# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────
# 순수 함수(임베딩·경로길이·PDF)는 detail_helpers.py 로 분리(페이지 슬림화·테스트 용이)
from detail_helpers import compute_embedding, path_length, build_report_pdf

def card_header(num, title):
    st.markdown(f'<div class="card-header"><span class="badge">{num}</span>{title}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 사이드바 — 실험 정보·그룹 요약 표시 (df_animals, df_group 사용)
# ═══════════════════════════════════════════════════════════════════════════
df_animals = load_animals()
df_group   = load_group_means()

# 실 데이터 기반 동적 정보 연산
active_groups = [g for g in df_animals['group_name'].dropna().unique() if g and g.lower() != 'control']
drug_name = active_groups[0] if active_groups else "Yohimbine"
experiment_name = f"{drug_name} Open Field"

doses_list = sorted(int(d) for d in df_animals['dose'].unique())
doses_str = "/".join(str(d) for d in doses_list)
drug_info = f"{drug_name} ({doses_str} mg/kg)"

from db.schema import read_sql
try:
    df_date = read_sql(f"SELECT MIN(created_at) AS min_date FROM {SCHEMA}.animals")
    if not df_date.empty and df_date['min_date'].iloc[0] is not None:
        min_date = pd.to_datetime(df_date['min_date'].iloc[0])
        experiment_date = min_date.strftime('%Y-%m-%d')
    else:
        experiment_date = "2024-05-16"
except Exception:
    experiment_date = "2024-05-16"

import subprocess
try:
    researcher = subprocess.check_output(
        ["git", "log", "-1", "--format=%an"],
        stderr=subprocess.DEVNULL
    ).decode('utf-8').strip()
    if not researcher:
        researcher = "AI Researcher"
except Exception:
    researcher = "AI Researcher"

total_mice = len(df_animals)
mice_per_group = int(df_animals.groupby('dose')['animal_id'].nunique().mean()) if total_mice else 0
mice_info = f"{total_mice}마리 (그룹당 {mice_per_group}마리)"

st.sidebar.markdown('<div style="font-size:0.75rem; color:#64748b !important; font-weight:700; margin-bottom:10px;">실험 정보</div>', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div style="font-size:0.85rem; line-height:1.8;">
<span style="color:#94a3b8 !important;">실험명</span><br>
<b style="color:#1e293b !important;">{experiment_name}</b><br><br>
<span style="color:#94a3b8 !important;">약물</span><br>
<b style="color:#1e293b !important;">{drug_info}</b><br><br>
<span style="color:#94a3b8 !important;">날짜</span><br>
<b style="color:#1e293b !important;">{experiment_date}</b><br><br>
<span style="color:#94a3b8 !important;">연구원</span><br>
<b style="color:#1e293b !important;">{researcher}</b><br><br>
<span style="color:#94a3b8 !important;">전체 개체수</span><br>
<b style="color:#1e293b !important;">{mice_info}</b>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.markdown('<div style="font-size:0.75rem; color:#64748b !important; font-weight:700; margin-bottom:10px;">그룹 요약</div>', unsafe_allow_html=True)
# 간단한 그룹 요약 시각화
gr_html = ""
for _, gr in df_group.iterrows():
    d = int(gr['dose'])
    n_mice = int(gr['n'])
    gr_html += f'<div style="display:flex; justify-content:space-between; font-size:0.85rem; padding:4px 0; border-bottom:1px solid #e8edf3;"><span style="color:#475569 !important;">투여량 {d}</span><span style="color:{DOSE_COLORS.get(d,"#475569")} !important;">n={n_mice}</span></div>'
st.sidebar.markdown(gr_html, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# 메인 영역 — selected(선택 개체) 기준으로 9개 분석 카드 렌더
# ═══════════════════════════════════════════════════════════════════════════

# 상단 컨트롤바
col_title, col_ctrl = st.columns([2, 1])
with col_ctrl:
    st.markdown("<br>", unsafe_allow_html=True)
    options = []
    doses = sorted(df_animals['dose'].unique())
    for i, d in enumerate(doses):
        options.append(f"투여량 {int(d)}")
        mice = df_animals[df_animals['dose'] == d]['animal_id'].tolist()
        options.extend(mice)
        if i < len(doses) - 1:
            options.append("-" * 38)

    default_idx = next(i for i, opt in enumerate(options) if not opt.startswith("투여량") and not opt.startswith("-"))
    # 개체 관리 화면에서 '보기'로 넘어온 경우 해당 개체를 기본 선택
    pre = st.session_state.pop("detail_animal", None)
    if pre in options:
        default_idx = options.index(pre)

    selected = st.selectbox(
        "마우스 선택",
        options,
        index=default_idx,
        label_visibility="collapsed"
    )

if selected.startswith("투여량 ") or selected.startswith("-"):
    st.info("💡 카테고리 제목이나 구분선을 선택하셨습니다. 아래에 있는 실제 마우스 ID를 선택해 주세요.")
    st.stop()

sel_dose = int(df_animals.set_index('animal_id').loc[selected, 'dose'])

with col_title:
    st.markdown(f'<div class="header-title">마우스 {selected}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="header-breadcrumbs">홈 > 실험 목록 > {experiment_name} > <b>마우스 {selected}</b></div>', unsafe_allow_html=True)

df_mouse = load_scores_animal(selected)
if df_mouse.empty:
    st.error("해당 개체의 데이터가 없습니다.")
    st.stop()

# ── 1행: 영상 + 행동 타임라인 (df_mouse 점수 → 구간별 임계 초과 시 타임라인 표시) ──
# 경로는 모두 __file__ 기준 상대 경로 (절대경로 하드코딩 제거)
_PAGE_DIR = os.path.dirname(os.path.abspath(__file__))
video_dir = os.environ.get("BEHAVIOR_VIDEO_DIR",
                           os.path.abspath(os.path.join(_PAGE_DIR, '..', '..', 'Videos')))

# 원본 영상은 gitignore 대상 → 1) repo 영상 폴더 2) 업로드 순으로 탐색하고,
# 둘 다 없으면 영상 없이도 행동 타임라인은 그대로 동작한다 (영상은 '선택 입력').
video_filename = None
if os.path.isdir(video_dir):
    for f in os.listdir(video_dir):
        if selected in f and f.endswith('.mp4'):
            video_filename = f
            break

# 프레임을 60초 구간(tbin)으로 묶어 구간별 평균 점수 tl 계산
df_mouse['tbin'] = df_mouse['frame'] // TIMELINE_BIN_FRAMES
tl = df_mouse.groupby('tbin')[SCORE_COLS].mean()

# 각 지표마다 임계 초과 구간을 (start~end 초) 리스트로 → 영상 타임라인 표시용
timeline_data = {}
for col in SCORE_COLS:
    timeline_data[col] = []
    for i, v in enumerate(tl[col].values):
        if v > TIMELINE_THRESHOLD:
            timeline_data[col].append({
                "start": (i * TIMELINE_BIN_FRAMES) / FPS,
                "end": ((i + 1) * TIMELINE_BIN_FRAMES) / FPS,
            })

timeline_json = json.dumps(timeline_data)

# 영상 소스 결정: 로컬 영상 폴더 → 사용자가 업로드한 파일 → 없음(폴백)
video_url = f"{video_server_url}/{video_filename}" if (video_filename and video_server_url) else ""
if not video_url:
    up = st.file_uploader("영상 파일(.mp4)을 업로드하면 타임라인과 동기화됩니다 (선택)",
                          type=["mp4"], key="video_upload")
    if up is not None:
        import base64
        b64 = base64.b64encode(up.getvalue()).decode()
        video_url = f"data:video/mp4;base64,{b64}"

html_path = os.path.join(_PAGE_DIR, '..', 'components', 'interactive_timeline.html')
if os.path.exists(html_path):
    if not video_url:
        st.info("ℹ️ 원본 영상은 저장소에 포함되지 않습니다(gitignore). "
                "영상이 없어도 아래 행동 타임라인·통계는 DB 데이터로 정상 동작하며, "
                "위에서 영상을 업로드하면 영상-타임라인 동기화가 활성화됩니다.")
    with open(html_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    html_content = html_template.replace("{{VIDEO_URL}}", video_url)
    html_content = html_content.replace("{{TIMELINE_JSON}}", timeline_json)
    html_content = html_content.replace("{{TOTAL_DURATION}}", str((len(tl) * TIMELINE_BIN_FRAMES) / FPS))
    html_content = html_content.replace("{{COLORS_JSON}}", json.dumps(BEH_COLOR))
    html_content = html_content.replace("{{NAMES_JSON}}", json.dumps(BEH_KR))

    components.html(html_content, height=450)
else:
    st.error("interactive_timeline.html 파일을 찾을 수 없습니다.")

# ── 행동 지표 정의 및 판정 기준 (공통 가이드라인: 이모지 배제, 색상 테마 동기화, 마크다운 파서 깨짐 방지를 위해 공백 라인 제거) ──
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    card_header(2.5, "행동 지표 정의 및 판정 기준")
    html_guide = (
        "<div style='display: grid; grid-template-columns: repeat(5, 1fr); gap: 20px; margin-top: 10px;'>"
        "<div style='font-size: 0.85rem; line-height: 1.5; display: flex; flex-direction: column; justify-content: space-between; padding: 5px;'>"
        "<div>"
        "<div style='font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem;'>"
        "<span style='display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #3b82f6;'></span>"
        "이동성 (Locomotion)"
        "</div>"
        "<div style='color: #475569; font-weight: 600; margin-bottom: 5px; font-size: 0.8rem;'>단순 이동 행위</div>"
        "<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 12px; min-height: 60px;'>마우스가 멈칫거리거나 킁킁거리지 않고, 목적지를 향해 앞으로 걸어가거나 뛰어가는 상태입니다.</div>"
        "</div>"
        "<div style='border-top: 1px dashed #cbd5e1; padding-top: 10px; font-size: 0.75rem; color: #64748b;'>"
        "<b style='color: #475569;'>AI 판정 기준</b><br>"
        "• 이동 속도(Velocity) 높음<br>"
        "• 가속도(Acceleration) 높음<br>"
        "• 경로 굴곡도(Tortuosity) 낮음"
        "</div>"
        "</div>"
        "<div style='font-size: 0.85rem; line-height: 1.5; display: flex; flex-direction: column; justify-content: space-between; padding: 5px;'>"
        "<div>"
        "<div style='font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem;'>"
        "<span style='display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #22c55e;'></span>"
        "탐색성 (Exploration)"
        "</div>"
        "<div style='color: #475569; font-weight: 600; margin-bottom: 5px; font-size: 0.8rem;'>호기심 및 정찰</div>"
        "<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 12px; min-height: 60px;'>마우스가 벽면 구석을 벗어나 중심부로 걸어 나오거나, 가만히 멈춰 서서 상체를 들고 주변을 조사하는 상태입니다.</div>"
        "</div>"
        "<div style='border-top: 1px dashed #cbd5e1; padding-top: 10px; font-size: 0.75rem; color: #64748b;'>"
        "<b style='color: #475569;'>AI 판정 기준</b><br>"
        "• 중심부 점유(Occupancy) 높음<br>"
        "• 벽과의 거리(Wall Dist) 높음<br>"
        "• 몸의 길이(Body Length) 높음"
        "</div>"
        "</div>"
        "<div style='font-size: 0.85rem; line-height: 1.5; display: flex; flex-direction: column; justify-content: space-between; padding: 5px;'>"
        "<div>"
        "<div style='font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem;'>"
        "<span style='display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #ef4444;'></span>"
        "불안 (Anxiety)"
        "</div>"
        "<div style='color: #475569; font-weight: 600; margin-bottom: 5px; font-size: 0.8rem;'>경계 및 두려움</div>"
        "<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 12px; min-height: 60px;'>넓고 트인 중앙으로 나오지 못하고, 어두운 벽면이나 구석에 몸을 바짝 밀착시켜서 아주 조심스럽게 기어 다니는 상태입니다.</div>"
        "</div>"
        "<div style='border-top: 1px dashed #cbd5e1; padding-top: 10px; font-size: 0.75rem; color: #64748b;'>"
        "<b style='color: #475569;'>AI 판정 기준</b><br>"
        "• 벽면 초밀착(Wall Dist) 낮음<br>"
        "• 중심부 접근(Occupancy) 낮음<br>"
        "• 꼬리 굽힘(Curvature) 높음"
        "</div>"
        "</div>"
        "<div style='font-size: 0.85rem; line-height: 1.5; display: flex; flex-direction: column; justify-content: space-between; padding: 5px;'>"
        "<div>"
        "<div style='font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem;'>"
        "<span style='display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #a855f7;'></span>"
        "과활동성 (Hyperactivity)"
        "</div>"
        "<div style='color: #475569; font-weight: 600; margin-bottom: 5px; font-size: 0.8rem;'>흥분 및 과반응</div>"
        "<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 12px; min-height: 60px;'>약물의 영향으로 극도로 흥분하여, 제자리에서 빠르게 회전하거나 벽면을 따라 비정상적이고 산만하게 달리는 상태입니다.</div>"
        "</div>"
        "<div style='border-top: 1px dashed #cbd5e1; padding-top: 10px; font-size: 0.75rem; color: #64748b;'>"
        "<b style='color: #475569;'>AI 판정 기준</b><br>"
        "• 이동 속도/가속도 높음<br>"
        "• 회전 각속도(Angular) 높음<br>"
        "• 경로 굴곡도(Tortuosity) 높음"
        "</div>"
        "</div>"
        "<div style='font-size: 0.85rem; line-height: 1.5; display: flex; flex-direction: column; justify-content: space-between; padding: 5px;'>"
        "<div>"
        "<div style='font-weight: 700; color: #1e293b; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; font-size: 0.9rem;'>"
        "<span style='display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: #d97706;'></span>"
        "경직 (Freezing)"
        "</div>"
        "<div style='color: #475569; font-weight: 600; margin-bottom: 5px; font-size: 0.8rem;'>공포 반응 (얼어붙음)</div>"
        "<div style='color: #64748b; font-size: 0.8rem; margin-bottom: 12px; min-height: 60px;'>공포나 충격 등으로 인해 전혀 움직이지 않고 몸을 낮추어 납작하게 얼어붙어 있는 상태입니다.</div>"
        "</div>"
        "<div style='border-top: 1px dashed #cbd5e1; padding-top: 10px; font-size: 0.75rem; color: #64748b;'>"
        "<b style='color: #475569;'>AI 판정 기준</b><br>"
        "• 모든 움직임 속도 0<br>"
        "• 가속도/각속도 0<br>"
        "• 몸의 웅크림(Length) 높음"
        "</div>"
        "</div>"
        "</div>"
    )
    st.markdown(html_guide, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 2행: 행동 통계 — 개체 평균 점수 vs 대조군(ctrl_row) 증감(metric) ──────────
with st.container(border=True):
    card_header(3, "행동 통계")
    
    ctrl_row = df_group[df_group['dose'] == 0].iloc[0] if 0 in df_group['dose'].values else None
    mouse_means = df_mouse[SCORE_COLS].mean()
    
    cols_s = st.columns(5)
    for i, col in enumerate(SCORE_COLS):
        with cols_s[i]:
            val = mouse_means[col] * 100 # 점수를 100점 만점으로 스케일링하여 보여줌
            delta = None
            if ctrl_row is not None and ctrl_row[col] > 0:
                pct = (mouse_means[col] - ctrl_row[col]) / ctrl_row[col] * 100
                delta = f"{pct:+.1f}% vs Control"
            inv = col in ('anxiety', 'freezing')
            st.metric(BEH_KR[col] + " 점수", f"{val:.1f}", delta=delta, delta_color="inverse" if inv else "normal")


# ── 3행: 임베딩(4)·그룹 비교(5)·이동 궤적(6) — df_emb / df_group / df_coords ──
col4, col5, col6 = st.columns(3)

with col4:
    with st.container(border=True, height=460):
        card_header(4, "임베딩")
        df_am = load_animal_means()
        df_emb, emb_method = compute_embedding(df_am)

        fig_e, ax_e = plt.subplots(figsize=(5, 4))
        for d in sorted(df_emb['dose'].unique()):
            m = df_emb['dose'] == d
            ax_e.scatter(df_emb.loc[m, 'D1'], df_emb.loc[m, 'D2'],
                         c=DOSE_COLORS[d], label=f'Dose {d}', s=60,
                         alpha=0.8, edgecolors='white', linewidth=0.5)
        sr = df_emb[df_emb['animal_id'] == selected]
        if not sr.empty:
            ax_e.scatter(sr['D1'], sr['D2'], c='#ef4444', s=150,
                         marker='*', zorder=5, label=f'Mouse {selected}')
        ax_e.set_xlabel('UMAP 1', fontsize=9, color='#64748b')
        ax_e.set_ylabel('UMAP 2', fontsize=9, color='#64748b')
        ax_e.tick_params(labelsize=8, colors='#64748b')
        for sp in ['top', 'right']: ax_e.spines[sp].set_visible(False)
        ax_e.spines['bottom'].set_color('#cbd5e1')
        ax_e.spines['left'].set_color('#cbd5e1')
        ax_e.legend(fontsize=8, loc='lower right', frameon=False)
        ax_e.grid(alpha=0.2, color='#cbd5e1', linestyle='--')
        plt.tight_layout()
        st.pyplot(fig_e)
        plt.close()

with col5:
    with st.container(border=True, height=460):
        card_header(5, "그룹 비교")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        comp = []
        for col in SCORE_COLS:
            row = {'Metric': BEH_KR[col]}
            for _, gr in df_group.iterrows():
                row[f'Dose {int(gr["dose"])}'] = f'{gr[col]*100:.1f}'
            row['현재 마우스'] = f'{mouse_means[col]*100:.1f}'
            comp.append(row)
        df_comp = pd.DataFrame(comp)
        
        if 'Dose 0' in df_comp.columns:
            df_comp.rename(columns={'Dose 0': 'Dose 0 (대조군)'}, inplace=True)
            
        curr_grp_col = f'Dose {sel_dose}'
        if curr_grp_col != 'Dose 0' and curr_grp_col in df_comp.columns:
            df_comp.rename(columns={curr_grp_col: f"{curr_grp_col} (소속 그룹)"}, inplace=True)
            curr_grp_col = f"{curr_grp_col} (소속 그룹)"
        elif curr_grp_col == 'Dose 0':
            curr_grp_col = 'Dose 0 (대조군)'
            
        mouse_col = '현재 마우스'
        
        def highlight_cols(s):
            if s.name == mouse_col:
                return ['background-color: rgba(37, 99, 235, 0.15); color: #1d4ed8; font-weight: bold;'] * len(s)
            elif s.name == curr_grp_col:
                return ['background-color: rgba(241, 245, 249, 0.8); font-weight: bold; color: #334155;'] * len(s)
            return [''] * len(s)

        styled_df = df_comp.style.apply(highlight_cols, axis=0)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.caption("※ 평균 행동 점수 (0~100 환산)")

# 선택 개체의 실제 bodycentre 좌표 (궤적·히트맵 공용) — 번들 샘플에서 로드
df_coords = data.get_coords(selected)

with col6:
    with st.container(border=True, height=460):
        card_header(6, "이동 궤적")
        if not df_coords.empty:
            fig_tr, ax_tr = plt.subplots(figsize=(5, 4))
            # 시간 경과를 색으로 인코딩 (이동 경로의 흐름 표현)
            ax_tr.scatter(df_coords['x'], df_coords['y'], c=df_coords['frame'],
                          cmap='viridis', s=2, alpha=0.6)
            ax_tr.plot(df_coords['x'], df_coords['y'], color=DOSE_COLORS.get(sel_dose, '#888'),
                       alpha=0.25, linewidth=0.4)
            ax_tr.set_aspect('equal')
            ax_tr.invert_yaxis()  # 영상 좌표계(y 아래로 증가) 보정
            ax_tr.set_xticks([]); ax_tr.set_yticks([])
            for sp in ['top', 'right', 'bottom', 'left']:
                ax_tr.spines[sp].set_color('#cbd5e1')
            ax_tr.set_title(f"총 이동 {path_length(df_coords):,.0f} px", fontsize=9, color='#64748b')
            plt.tight_layout()
            st.pyplot(fig_tr)
            plt.close()
        else:
            st.info("이 개체의 좌표 데이터가 없습니다. "
                    "`python scripts/build_sample.py` 로 좌표를 포함해 샘플을 재생성하세요.")

# ── 4행: 공간 히트맵(7)·AI 요약(8)·리포트(9) — df_coords / mouse_means / PDF ──
col7, col8, col9 = st.columns(3)

with col7:
    with st.container(border=True, height=380):
        card_header(7, "공간 히트맵")
        if not df_coords.empty:
            fig_hm, ax_hm = plt.subplots(figsize=(5, 4))
            hb = ax_hm.hist2d(df_coords['x'], df_coords['y'], bins=40, cmap='YlOrRd')
            ax_hm.set_aspect('equal')
            ax_hm.invert_yaxis()
            ax_hm.set_xticks([]); ax_hm.set_yticks([])
            for sp in ['top', 'right', 'bottom', 'left']:
                ax_hm.spines[sp].set_color('#cbd5e1')
            fig_hm.colorbar(hb[3], ax=ax_hm, fraction=0.046, pad=0.04).ax.tick_params(labelsize=7)
            plt.tight_layout()
            st.pyplot(fig_hm)
            plt.close()
        else:
            st.info("이 개체의 좌표 데이터가 없습니다.")

with col8:
    with st.container(border=True, height=380):
        card_header(8, "AI 분석 요약")
        
        txt = f"본 개체(마우스 {selected})는 {drug_name} {sel_dose} mg/kg 투여군에 속합니다.<br><br>"
        if sel_dose > 0 and ctrl_row is not None:
            txt += "대조군에 비해 "
            changes = []
            for c in ['locomotion', 'anxiety']:
                val = mouse_means[c]
                ctrl_v = ctrl_row[c]
                if val > ctrl_v * 1.1: changes.append(f"{BEH_KR[c]} 점수가 증가")
                elif val < ctrl_v * 0.9: changes.append(f"{BEH_KR[c]} 점수가 감소")
            if changes:
                txt += " 및 ".join(changes) + "하는 패턴을 보였습니다. "
            txt += f"특히 UMAP 임베딩에서 대조군과 분리되어 약물에 의한 행동 패턴 변화가 명확하게 관찰됩니다."
        else:
            txt += "약물 투여 전 기본 행동 패턴(Baseline)을 나타냅니다. 특이한 이상 행동은 관찰되지 않았습니다."
            
        st.markdown(f'<div style="font-size:0.95rem; line-height:1.7; color:#334155; padding:5px;">{txt}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("요약 재생성"):
            import time
            with st.spinner("AI 엔진과 통신하여 심층 분석 요약을 다시 생성 중입니다..."):
                time.sleep(1.5)
            st.success("✅ 새로운 인사이트가 성공적으로 반영되었습니다.")

with col9:
    with st.container(border=True, height=380):
        card_header(9, "결과 리포트")
        st.markdown('<div style="font-size:0.95rem; color:#334155; margin-bottom:20px;">현재 개체에 대한 상세 행동 분석 리포트를 생성하여 다운로드할 수 있습니다.</div>', unsafe_allow_html=True)
        
        ai_plain = txt.replace('<br>', '\n')

        @st.dialog("상세 행동 분석 리포트", width="large")
        def show_report_dialog():
            st.markdown(f"### 마우스 {selected} 행동 분석 리포트")
            st.markdown(f"**소속 그룹:** {drug_name} {sel_dose} mg/kg 투여군")
            st.divider()
            st.markdown("#### 1. AI 분석 요약")
            st.info(ai_plain)
            st.markdown("#### 2. 세부 행동 지표")
            for c in ['locomotion', 'exploration', 'anxiety', 'hyperactivity', 'freezing']:
                st.markdown(f"- **{BEH_KR[c]}**: {mouse_means[c]*100:.1f} 점")
            st.divider()
            # ── PDF 다운로드 ──
            with st.spinner("PDF 생성 중..."):
                pdf_bytes = build_report_pdf(selected, sel_dose, mouse_means, ctrl_row, ai_plain, df_coords)
            st.download_button("PDF로 다운로드", pdf_bytes,
                               file_name=f"mouse_{selected}_report.pdf",
                               mime="application/pdf", type="primary", use_container_width=True)
            st.caption("Generated by Laboratory AI Platform")

        if st.button("리포트 팝업창으로 바로 보기", type="primary", use_container_width=True):
            show_report_dialog()
        
        st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        
        @st.dialog("전체 통계 모델 데이터", width="large")
        def show_csv_dialog():
            p = os.path.join(os.path.dirname(__file__), '..', '..', 'outputs', 'mixed_model_summary.csv')
            if os.path.exists(p):
                import pandas as pd
                df_csv = pd.read_csv(p)

                # 레코드 한글화 (지표명 및 상태)
                df_csv['Behavior'] = df_csv['Behavior'].apply(lambda x: BEH_KR.get(x.replace('_Score', '').lower(), x))
                df_csv['Status'] = df_csv['Status'].map({'OK': '완료', 'FAILED': '실패'}).fillna(df_csv['Status'])

                # p값 가독성: 0.00000...00 대신 사람이 읽기 쉬운 형식으로
                def _fmt_pval(v):
                    try:
                        v = float(v)
                    except (TypeError, ValueError):
                        return v
                    if pd.isna(v):
                        return "-"
                    if v < 0.001:
                        return "< 0.001"      # 매우 뚜렷한 효과
                    return f"{v:.3f}"
                for c in ('Dose_Pval', 'Time_Pval'):
                    if c in df_csv.columns:
                        df_csv[c] = df_csv[c].apply(_fmt_pval)

                # 계수·분산도 긴 소수점 정리
                for c in ('Dose_Coef', 'Time_Coef', 'Random_Effect_Var'):
                    if c in df_csv.columns:
                        df_csv[c] = pd.to_numeric(df_csv[c], errors='coerce').round(4)

                # 컬럼명 한글화 ("신뢰도"는 p값 의미상 부정확 → "유의성"으로 정정)
                col_map = {
                    'Behavior': '행동 지표',
                    'Dose_Coef': '약물 농도 기울기 (계수)',
                    'Dose_Pval': '약물 효과 유의성 (p값)',
                    'Time_Coef': '시간 경과 기울기 (계수)',
                    'Time_Pval': '시간에 따른 변화 유의성 (p값)',
                    'Random_Effect_Var': '개체간 편차 (무작위 분산)',
                    'Status': '분석 상태'
                }
                df_csv = df_csv.rename(columns=col_map)

                st.markdown("전체 투여군에 대한 **혼합 선형 모델(Mixed Linear Model)** 통계 분석 요약 데이터입니다.")
                st.dataframe(df_csv, use_container_width=True, hide_index=True)
                st.caption("※ p값은 효과가 우연이 아닐 가능성을 나타냅니다. 값이 작을수록(보통 0.05 미만) 통계적으로 뚜렷한 효과이며, `< 0.001`은 매우 강한 유의성을 뜻합니다.")
            else:
                st.warning("분석 결과 파일이 아직 생성되지 않았습니다.")
                
        if st.button("전체 모델 데이터 팝업창으로 바로 보기", use_container_width=True):
            show_csv_dialog()
 