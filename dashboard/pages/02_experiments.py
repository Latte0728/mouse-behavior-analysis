"""
02_experiments.py — 실험 관리
흐름: data.get_group_means()/get_model_results() → 투여군 구성에서
      'Control vs 각 dose' 비교 실험 목록을 도출 → 탭·검색으로 표시.
"""
import streamlit as st
import pandas as pd
import datasource as data  # dashboard/datasource.py (루트 data/ 폴더와 이름 충돌 방지)

st.markdown("""
<style>
    .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    div[data-testid="stTabs"] button { font-weight: 600; font-size: 1rem; }
    div[data-testid="stTabs"] button[aria-selected="true"] { color: #2563eb !important; border-bottom-color: #2563eb !important; }
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem; }
    .custom-table th { background-color: #f8fafc; color: #64748b; font-weight: 600; padding: 12px 16px; text-align: left; border-bottom: 2px solid #e2e8f0; border-top: 1px solid #e2e8f0; }
    .custom-table td { padding: 12px 16px; border-bottom: 1px solid #e2e8f0; color: #334155; vertical-align: middle; }
    .custom-table tr:hover { background-color: #f8fafc; }
</style>
""", unsafe_allow_html=True)

# ── 헤더 ────────────────────────────────────────────────────────────────
st.markdown('<h1 class="header-title" style="margin-bottom:0;">실험 관리</h1>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 실제 데이터에서 실험 목록 도출 ─────────────────────────────────────────
df_raw_exp = data.get_experiments()
df_animals = data.get_animals()

experiments = []
if not df_raw_exp.empty:
    for _, row in df_raw_exp.iterrows():
        base_d = int(row['base_dose'])
        comp_ds = [int(x) for x in row['comp_doses'].split(',') if x] if row['comp_doses'] else []
        
        # 개체 수 계산
        if row['animal_ids']:
            a_list = [x.strip() for x in row['animal_ids'].split(',') if x.strip()]
            n_animals = len(a_list)
        else:
            target_doses = [base_d] + comp_ds
            n_animals = int(df_animals[df_animals['dose'].isin(target_doses)]['animal_id'].nunique())
            
        experiments.append({
            "실험 이름": row['name'],
            "실험 유형": row['experiment_type'],
            "그룹 구성": f"{base_d}, " + ", ".join(str(d) for d in comp_ds) + " mg/kg" if comp_ds else f"{base_d} mg/kg",
            "개체 수": n_animals,
            "_status": row['status'],
            "생성일": pd.to_datetime(row['created_at']).strftime('%Y-%m-%d'),
            "base_dose": base_d,
            "comp_doses": row['comp_doses'],
            "metrics": row['metrics'],
            "animal_ids": row['animal_ids']
        })
df_exp = pd.DataFrame(experiments) if experiments else pd.DataFrame(columns=["실험 이름", "실험 유형", "그룹 구성", "개체 수", "_status", "생성일", "base_dose", "comp_doses", "metrics", "animal_ids"])


def status_badge(s):
    if "완료" in s and "분석" in s:
        return f'<span style="background:#dcfce7; color:#166534; padding:4px 10px; border-radius:12px; font-size:0.8rem; font-weight:500;">{s}</span>'
    if "중" in s:
        return f'<span style="background:#fef9c3; color:#854d0e; padding:4px 10px; border-radius:12px; font-size:0.8rem; font-weight:500;">{s}</span>'
    return f'<span style="background:#dbeafe; color:#1e40af; padding:4px 10px; border-radius:12px; font-size:0.8rem; font-weight:500;">{s}</span>'

tab_all, tab_done, tab_up = st.tabs(["전체", "분석 완료", "업로드 완료"])

def render(df_view, key):
    sc, _ = st.columns([1, 3])
    with sc:
        q = st.text_input("실험 검색...", key=f"q_{key}", label_visibility="collapsed", placeholder="실험 검색...")
    d = df_view
    if q:
        d = d[d['실험 이름'].str.contains(q, case=False, na=False)]
    if d.empty:
        st.info("조건에 맞는 실험이 없습니다.")
        return
    show = d.copy()
    show['상태'] = show['_status'].apply(status_badge)
    show = show[["실험 이름", "실험 유형", "그룹 구성", "개체 수", "상태", "생성일"]]
    st.markdown(show.to_html(escape=False, index=False, classes="custom-table"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.95rem; font-weight: 600; color: #1e293b;'>작업 — 실험을 선택해 통계 분석을 실행하거나 설정을 삭제하세요.</div>", unsafe_allow_html=True)
    
    a1, a2, a3 = st.columns([3, 1, 1])
    with a1:
        selected_name = st.selectbox("작업할 실험 선택", d['실험 이름'].tolist(), key=f"sel_{key}", label_visibility="collapsed")
    with a2:
        if st.button("분석 실행", key=f"run_btn_{key}", type="primary", use_container_width=True):
            exp_row = d[d['실험 이름'] == selected_name].iloc[0]
            
            comp_doses_list = [int(x) for x in exp_row['comp_doses'].split(',') if x] if exp_row['comp_doses'] else []
            metrics_list = exp_row['metrics'].split(',') if exp_row['metrics'] else []
            animal_ids_list = exp_row['animal_ids'].split(',') if exp_row['animal_ids'] else []
            
            st.session_state["comp_type"] = "group"
            st.session_state["comp_step"] = 4
            
            base_d = int(exp_row['base_dose'])
            base_animals = df_animals[df_animals['dose'] == base_d]['animal_id'].tolist()
            comp_animals = df_animals[df_animals['dose'].isin(comp_doses_list)]['animal_id'].tolist()
            
            if animal_ids_list:
                sel_base_animals = [a for a in animal_ids_list if a in base_animals]
                sel_comp_animals = [a for a in animal_ids_list if a in comp_animals]
            else:
                sel_base_animals = base_animals
                sel_comp_animals = comp_animals
                
            st.session_state["cfg_group"] = {
                "base_dose": base_d,
                "comp_doses": comp_doses_list,
                "metrics": metrics_list,
                "base_animals": sel_base_animals,
                "comp_animals": sel_comp_animals,
                "title": exp_row['실험 이름'],
                "template": "표준 리포트",
            }
            st.session_state["auto_run_comparison"] = True
            st.switch_page("pages/04_comparison.py")
            
    with a3:
        if st.button("삭제", key=f"del_btn_{key}", use_container_width=True):
            ok, msg = data.delete_experiment(selected_name)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

with tab_all:
    render(df_exp, "all")
with tab_done:
    render(df_exp[df_exp['_status'] == "분석 완료"], "done")
with tab_up:
    render(df_exp[df_exp['_status'] == "업로드 완료"], "up")
