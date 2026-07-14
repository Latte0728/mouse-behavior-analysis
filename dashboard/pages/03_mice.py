"""
03_mice.py — 개체 관리
흐름: data.get_animals()(메타+데이터량+상태) + get_animal_means()(평균 점수)
      → 투여군 탭 · 검색/필터/정렬 테이블 · 작업(보기→05 / 편집→update_animal_group).
"""
import streamlit as st
import pandas as pd
import datasource as data  # dashboard/datasource.py (루트 data/ 폴더와 이름 충돌 방지)

st.markdown("""
<style>
    div[data-testid="stTabs"] button { font-weight: 600; font-size: 1rem; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #2563eb !important; border-bottom-color: #2563eb !important; }
</style>
""", unsafe_allow_html=True)

# ── 실제 데이터 로드 ────────────────────────────────────────────────────────
df_animals = data.get_animals()
df_means = data.get_animal_means().set_index('animal_id')

# ── Header (개체 등록 버튼 제거, CSV 내보내기만 유지) ────────────────────────
col_title, col_btn = st.columns([6, 1])
with col_title:
    st.markdown('<h1 class="header-title" style="margin-bottom:0;">개체 관리</h1>', unsafe_allow_html=True)
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    csv = df_animals[['animal_id', 'dose', 'group_name', 'n_frames', 'duration_sec', 'status']].to_csv(index=False).encode('utf-8-sig')
    st.download_button("CSV 내보내기", csv, file_name="animals.csv", mime="text/csv", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 편집 다이얼로그 ─────────────────────────────────────────────────────────
@st.dialog("개체 정보 편집")
def edit_dialog(aid):
    row = df_animals[df_animals['animal_id'] == aid].iloc[0]
    st.markdown(f"**개체 ID:** {aid}")
    st.markdown(f"**용량(Dose):** {int(row['dose'])} mg/kg · **데이터:** {int(row['n_frames']):,} 프레임")
    new_group = st.text_input("그룹명 (group_name)", value=row['group_name'] or "")
    if st.button("저장", type="primary"):
        ok, msg = data.update_animal_group(aid, new_group)
        (st.success if ok else st.warning)(msg)

# ── 탭(투여군) — 실제 개수 ──────────────────────────────────────────────────
doses = sorted(df_animals['dose'].unique())
def dose_name(d): return "Control" if d == 0 else f"Dose {int(d)}"
tab_labels = [f"전체 ({len(df_animals)})"] + [f"{dose_name(d)} ({(df_animals['dose']==d).sum()})" for d in doses]
tabs = st.tabs(tab_labels)


def format_hms(sec):
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    parts = []
    if h > 0:
        parts.append(f"{h}시간")
    if m > 0 or h > 0:
        parts.append(f"{m}분")
    parts.append(f"{s}초")
    return " ".join(parts)


def render_table(df_view, key):
    """검색·필터 + 행 선택형 테이블 + 작업(보기/편집)."""
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        q = st.text_input("개체 검색...", key=f"q_{key}", label_visibility="collapsed", placeholder="개체 ID 검색...")
    with f2:
        status_f = st.selectbox("상태", ["상태 전체", "정상", "데이터 없음"], key=f"s_{key}", label_visibility="collapsed")
    with f3:
        sort_f = st.selectbox("정렬", ["ID 순", "데이터량 많은 순", "데이터량 적은 순"], key=f"sort_{key}", label_visibility="collapsed")

    d = df_view.copy()
    if q:
        d = d[d['animal_id'].str.contains(q, case=False, na=False)]
    if status_f != "상태 전체":
        d = d[d['status'] == status_f]
    if sort_f == "데이터량 많은 순":
        d = d.sort_values('n_frames', ascending=False)
    elif sort_f == "데이터량 적은 순":
        d = d.sort_values('n_frames', ascending=True)
    d = d.reset_index(drop=True)

    if d.empty:
        st.info("조건에 맞는 개체가 없습니다.")
        return

    # 표시용 테이블 (행 클릭 선택 가능)
    disp = pd.DataFrame({
        "개체 ID": d['animal_id'],
        "그룹 (용량)": d['dose_label'],
        "데이터(프레임)": d['n_frames'].map(lambda v: f"{int(v):,}"),
        "기록시간": d['duration_sec'].apply(format_hms),
        "이동성": [f"{df_means.loc[a,'locomotion']*100:.1f}" if a in df_means.index else "—" for a in d['animal_id']],
        "불안": [f"{df_means.loc[a,'anxiety']*100:.1f}" if a in df_means.index else "—" for a in d['animal_id']],
        "상태": d['status'],
    })
    st.dataframe(disp, use_container_width=True, hide_index=True, height=440, key=f"tbl_{key}")
    st.caption(f"전체 {len(d)}개")

    # ── 작업: 개체 선택 후 보기/편집 ──
    st.markdown("**작업** — 개체를 선택해 상세 보기 또는 정보를 편집하세요.")
    a1, a2, a3 = st.columns([3, 1, 1])
    with a1:
        aid = st.selectbox("작업할 개체", d['animal_id'].tolist(),
                           format_func=lambda a: f"{a} · {d[d['animal_id']==a]['dose_label'].iloc[0]}",
                           key=f"act_{key}", label_visibility="collapsed")
    with a2:
        if st.button("상세 보기", key=f"view_{key}", type="primary", use_container_width=True):
            st.session_state["detail_animal"] = aid
            st.switch_page("pages/05_mouse_detail.py")
    with a3:
        if st.button("편집", key=f"edit_{key}", use_container_width=True):
            edit_dialog(aid)

with tabs[0]:
    render_table(df_animals, "all")
for i, d in enumerate(doses):
    with tabs[i + 1]:
        render_table(df_animals[df_animals['dose'] == d], f"d{int(d)}")
