"""
04_comparison.py — 비교 분석 (3가지 타입)
흐름: ss.comp_type 로 화면 분기 및 4단계 마법사 진행
  · group      : 4단계 마법사 → cfg 수집 → LME 분석 실행 및 리포트
  · individual : 4단계 마법사 → 개체 A/B 선택 → 독립표본 t-검정 및 리포트
  · time       : 4단계 마법사 → 개체+구간 수 선택 → 구간별 검정 및 리포트
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import datasource as data  # dashboard/datasource.py

st.markdown("""
<style>
    .stepper-wrap { display: flex; margin-bottom: 30px; }
    .step { flex: 1; height: 46px; display: flex; align-items: center; justify-content: center; background: white; color: #94a3b8; position: relative; font-weight: 600; font-size: 0.95rem; gap: 8px; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; margin-right: 4px; }
    .step:first-child { border-left: 1px solid #e2e8f0; border-top-left-radius: 6px; border-bottom-left-radius: 6px; }
    .step:last-child { border-right: 1px solid #e2e8f0; border-top-right-radius: 6px; border-bottom-right-radius: 6px; margin-right: 0; }
    .step::after { content: ""; position: absolute; right: -16px; top: -1px; width: 33px; height: 33px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; transform: rotate(45deg); background: inherit; z-index: 2; border-radius: 2px; }
    .step:last-child::after { display: none; }
    .step.active { background: #2563eb; color: white; border-color: #2563eb; }
    .step.active::after { background: #2563eb; border-color: #2563eb; }
    .step.completed { color: #2563eb; }
    .step-num { display: inline-flex; justify-content: center; align-items: center; width: 24px; height: 24px; border-radius: 50%; background: #f1f5f9; color: #94a3b8; font-size: 0.85rem; z-index: 3; }
    .step.active .step-num { background: white; color: #2563eb; }
    .step.completed .step-num { background: #2563eb; color: white; }
    .step-text { z-index: 3; }
    .option-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 14px 10px; text-align: center; background: white; display:flex; flex-direction:column; align-items:center; gap: 8px; }
    .option-card.selected { border: 2px solid #2563eb; background: #eff6ff; }
    .option-card h3 { margin: 0; font-size: 1.0rem; color: #1e293b; }
    .option-card p { font-size: 0.8rem; color: #64748b; margin: 0; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="header-title" style="margin-bottom:0;">비교 분석 설정</h1>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── 세션 상태 및 기본값 설정 ──────────────────────────────────────────────────
ss = st.session_state
ss.setdefault("comp_type", "group")
ss.setdefault("comp_step", 1)

df_animals = data.get_animals()
doses = sorted(int(d) for d in df_animals['dose'].unique())
def dose_label(d): return f"{'Control' if d == 0 else 'Dose ' + str(d)} ({d} mg/kg)"
def animal_label(aid):
    d = int(df_animals.set_index('animal_id').loc[aid, 'dose'])
    return f"{aid}  ·  {'Control' if d == 0 else 'Dose ' + str(d)}"
all_animals = df_animals['animal_id'].tolist()

ss.setdefault("cfg_group", {
    "base_dose": 0, "comp_doses": [6], "metrics": list(data.SCORE_COLS),
    "base_animals": [], "comp_animals": [], "title": "실험 그룹 비교 분석 리포트",
    "template": "표준 리포트",
})
ss.setdefault("cfg_indiv", {
    "a_animal": all_animals[0], "b_animal": all_animals[min(20, len(all_animals) - 1)] if len(all_animals) > 1 else all_animals[0],
    "metrics": list(data.SCORE_COLS), "title": "개체별 비교 분석 리포트",
    "template": "표준 리포트",
})
ss.setdefault("cfg_time", {
    "animal": all_animals[min(20, len(all_animals) - 1)] if len(all_animals) > 1 else all_animals[0], "n_win": 3,
    "metrics": list(data.SCORE_COLS), "title": "시간대별 비교 분석 리포트",
    "template": "표준 리포트",
})

# ── 비교 타입 선택 ──────────────────────────────────────────────────────────
TYPES = [
    ("group", "실험 그룹 비교", "여러 실험 그룹 간 통계적 지표 비교",
     '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'),
    ("individual", "개체별 비교", "두 마리 개체 간 행동 비교 분석",
     '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10a4 4 0 0 0-4-4h-2a6 6 0 0 0-6 6v2a6 6 0 0 0 6 6h12a2 2 0 0 0 2-2v-4a4 4 0 0 0-4-4z"/><circle cx="15" cy="11" r="1"/><path d="M4 12c-1.1 0-2 .9-2 2v2"/></svg>'),
    ("time", "시간대 비교", "동일 개체의 시간 구간별 행동 변화",
     '<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'),
]
cols = st.columns(3)
for col, (key, title, desc, svg) in zip(cols, TYPES):
    sel = ss.comp_type == key
    color = "#2563eb" if sel else "#94a3b8"
    with col:
        st.markdown(f'<div class="option-card {"selected" if sel else ""}">{svg % color}'
                    f'<h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
        if st.button(("✓ 선택됨" if sel else "선택"), key=f"type_{key}",
                     type="primary" if sel else "secondary", use_container_width=True):
            ss.comp_type = key
            ss.comp_step = 1
            ss.pop("last_result", None); ss.pop("indiv_result", None); ss.pop("time_result", None)
            st.rerun()

st.divider()
comp_type = ss.comp_type
if comp_type == "group":
    cfg = ss.cfg_group
elif comp_type == "individual":
    cfg = ss.cfg_indiv
else:
    cfg = ss.cfg_time


def sig_badge(p):
    return "유의함" if (pd.notna(p) and p < 0.05) else "유의하지 않음"


# ── Stepper 단계 관리 함수 ────────────────────────────────────────────────────
def next_step(): ss.comp_step += 1
def prev_step(): ss.comp_step -= 1
def sc(n): return "active" if ss.comp_step == n else ("completed" if ss.comp_step > n else "")
def sm(n):
    if ss.comp_step > n:
        return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
    return str(n)

st.markdown(f"""
<div class="stepper-wrap">
    <div class="step {sc(1)}"><span class="step-num">{sm(1)}</span><span class="step-text">비교 설정</span></div>
    <div class="step {sc(2)}"><span class="step-num">{sm(2)}</span><span class="step-text">분석 옵션</span></div>
    <div class="step {sc(3)}"><span class="step-num">{sm(3)}</span><span class="step-text">리포트 구성</span></div>
    <div class="step {sc(4)}"><span class="step-num">{sm(4)}</span><span class="step-text">확인 및 실행</span></div>
</div>""", unsafe_allow_html=True)


# ── 1단계: 비교 설정 ─────────────────────────────────────────────────────────
if ss.comp_step == 1:
    if comp_type == "group":
        st.subheader("실험 그룹 선택")
        g1, gvs, g2 = st.columns([4, 1, 4])
        with g1:
            with st.container(border=True):
                st.markdown("**대조군**")
                base_dose = st.selectbox("용량 (Dose)", doses,
                                         index=doses.index(cfg["base_dose"]) if cfg["base_dose"] in doses else 0,
                                         format_func=dose_label, key="w_base_dose")
                base_pool = df_animals[df_animals['dose'] == base_dose]['animal_id'].tolist()
                base_sel = st.multiselect("개체 선택 (대조군)", base_pool, default=base_pool, key="w_base_animals")
                st.caption(f"선택된 개체: {len(base_sel)}마리")
        with gvs:
            st.markdown('<div style="text-align:center; font-weight:800; color:#94a3b8; margin-top:90px;">VS</div>', unsafe_allow_html=True)
        with g2:
            with st.container(border=True):
                st.markdown("**실험군**")
                comp_opts = [d for d in doses if d != base_dose]
                default_comp = [d for d in cfg["comp_doses"] if d in comp_opts] or comp_opts[-1:]
                comp_doses = st.multiselect("용량 (Dose, 복수 선택 가능)", comp_opts, default=default_comp,
                                            format_func=dose_label, key="w_comp_doses")
                comp_pool = df_animals[df_animals['dose'].isin(comp_doses)]['animal_id'].tolist()
                comp_sel = st.multiselect("개체 선택 (실험군)", comp_pool, default=comp_pool, key="w_comp_animals")
                st.caption(f"선택된 개체: {len(comp_sel)}마리")

        st.markdown("<br>", unsafe_allow_html=True)
        _, cnext = st.columns([8, 2])
        def save1_group():
            cfg["base_dose"] = ss.w_base_dose; cfg["comp_doses"] = ss.w_comp_doses
            cfg["base_animals"] = ss.w_base_animals; cfg["comp_animals"] = ss.w_comp_animals
            next_step()
        with cnext:
            st.button("다음 단계 >", type="primary", use_container_width=True, on_click=save1_group,
                      disabled=(len(comp_doses) == 0 or len(base_sel) == 0 or len(comp_sel) == 0))

    elif comp_type == "individual":
        st.subheader("비교 대상 개체 선택")
        ca, cvs, cb = st.columns([5, 1, 5])
        with ca:
            with st.container(border=True):
                st.markdown("**개체 A**")
                a_sel = st.selectbox("개체 A 선택", all_animals,
                                     index=all_animals.index(cfg["a_animal"]) if cfg["a_animal"] in all_animals else 0,
                                     format_func=animal_label, key="w_indiv_a")
        with cvs:
            st.markdown('<div style="text-align:center; font-weight:800; color:#94a3b8; margin-top:55px;">VS</div>', unsafe_allow_html=True)
        with cb:
            with st.container(border=True):
                st.markdown("**개체 B**")
                b_default = all_animals.index(cfg["b_animal"]) if cfg["b_animal"] in all_animals else min(20, len(all_animals) - 1)
                b_sel = st.selectbox("개체 B 선택", all_animals, index=b_default,
                                     format_func=animal_label, key="w_indiv_b")

        st.markdown("<br>", unsafe_allow_html=True)
        _, cnext = st.columns([8, 2])
        def save1_indiv():
            cfg["a_animal"] = ss.w_indiv_a; cfg["b_animal"] = ss.w_indiv_b
            next_step()
        with cnext:
            st.button("다음 단계 >", type="primary", use_container_width=True, on_click=save1_indiv,
                      disabled=(a_sel == b_sel))

    else:  # time
        st.subheader("개체 및 시간대 설정")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("**분석 대상 개체**")
                animal_sel = st.selectbox("개체 선택", all_animals,
                                          index=all_animals.index(cfg["animal"]) if cfg["animal"] in all_animals else min(20, len(all_animals) - 1),
                                          format_func=animal_label, key="w_time_animal")
        with c2:
            with st.container(border=True):
                st.markdown("**구간 분할 (Time Window)**")
                nwin_sel = st.selectbox("구간 수", [2, 3, 4, 6],
                                        index=[2, 3, 4, 6].index(cfg["n_win"]) if cfg["n_win"] in [2, 3, 4, 6] else 1,
                                        key="w_time_nwin")
        st.markdown("<br>", unsafe_allow_html=True)
        _, cnext = st.columns([8, 2])
        def save1_time():
            cfg["animal"] = ss.w_time_animal; cfg["n_win"] = ss.w_time_nwin
            next_step()
        with cnext:
            st.button("다음 단계 >", type="primary", use_container_width=True, on_click=save1_time)

# ── 2단계: 분석 옵션 ─────────────────────────────────────────────────────────
elif ss.comp_step == 2:
    cl, cr = st.columns([6, 4])
    with cl:
        st.subheader("분석 지표 선택")
        sel_all = st.checkbox("모두 선택", value=len(cfg["metrics"]) == len(data.SCORE_COLS))
        chosen = []
        mcols = st.columns(5)
        for i, m in enumerate(data.SCORE_COLS):
            with mcols[i]:
                if st.checkbox(data.BEH_EN[m], value=(m in cfg["metrics"]) or sel_all, key=f"w_m_{m}"):
                    chosen.append(m)
                st.caption(data.BEH_KR[m])
    with cr:
        st.subheader("통계 분석 옵션")
        with st.container(border=True):
            if comp_type == "group":
                st.selectbox("모델 선택", ["선형 혼합 효과 모델 (LME)"], key="w_model")
            else:
                st.selectbox("모델 선택", ["독립표본 t-검정 (Student's t-test)"], key="w_model")
            st.selectbox("다중 비교 보정", ["Benjamini-Hochberg (FDR)", "Bonferroni", "없음"], key="w_correction")
            st.selectbox("신뢰 구간 (CI)", ["95%", "99%", "90%"], key="w_ci")
    st.markdown("<br>", unsafe_allow_html=True)
    cp, _, cn = st.columns([2, 6, 2])
    def save2():
        cfg["metrics"] = [m for m in data.SCORE_COLS if ss.get(f"w_m_{m}")]; next_step()
    cp.button("< 이전 단계", use_container_width=True, on_click=prev_step)
    cn.button("다음 단계 >", type="primary", use_container_width=True, on_click=save2, disabled=len(chosen) == 0)

# ── 3단계: 리포트 구성 ────────────────────────────────────────────────────────
elif ss.comp_step == 3:
    cl, cr = st.columns([4, 6])
    with cl:
        st.subheader("포함할 내용 선택")
        for label, k in [("개요 요약", "inc_overview"), ("통계 요약 테이블", "inc_table"),
                         ("행동 지표 비교 그래프", "inc_bar"), ("AI 해석 요약", "inc_ai")]:
            st.checkbox(label, value=True, key=k)
    with cr:
        st.subheader("리포트 구성")
        cfg["template"] = st.radio("리포트 템플릿", ["표준 리포트", "논문 스타일", "프레젠테이션"],
                                   index=["표준 리포트", "논문 스타일", "프레젠테이션"].index(cfg["template"]),
                                   horizontal=True, key="w_template")
        cfg["title"] = st.text_input("리포트 제목", value=cfg["title"], key="w_title")
        st.text_area("설명 (선택)", placeholder="리포트에 포함할 추가 설명을 입력하세요...", key="w_desc")
    st.markdown("<br>", unsafe_allow_html=True)
    cp, _, cn = st.columns([2, 6, 2])
    cp.button("< 이전 단계", use_container_width=True, on_click=prev_step)
    cn.button("다음 단계 >", type="primary", use_container_width=True, on_click=next_step)

# ── 4단계: 확인 및 실행 ────────────────────────────────────────────────────────
elif ss.comp_step == 4:
    metrics = cfg["metrics"]
    
    # 자동 분석 실행 플래그 처리
    if ss.get("auto_run_comparison"):
        if comp_type == "group":
            base_d, comp_ds = cfg["base_dose"], cfg["comp_doses"]
            ss["last_result"] = data.run_comparison(base_d, comp_ds, metrics,
                                                    selected_animals=(cfg['base_animals'] + cfg['comp_animals']) or None)
        ss.pop("auto_run_comparison", None)
        
    st.subheader("설정 요약")

    if comp_type == "group":
        base_d, comp_ds = cfg["base_dose"], cfg["comp_doses"]
        with st.container(border=True):
            st.markdown(f"""
            **비교 타입:** 실험 그룹 비교
            **대조군:** {dose_label(base_d)} — {len(cfg['base_animals'])}마리
            **실험군:** {', '.join(dose_label(d) for d in comp_ds)} — {len(cfg['comp_animals'])}마리
            **분석 지표:** {len(metrics)}개 ({', '.join(data.BEH_EN[m] for m in metrics)})
            **통계 모델:** 선형 혼합 효과 모델 (LME) · 리포트: {cfg['template']}
            """)
        cp, _, cn = st.columns([2, 4, 4])
        cp.button("< 이전 단계", use_container_width=True, on_click=prev_step)
        run = cn.button("▶ 분석 실행 및 리포트 생성", type="primary", use_container_width=True)
        if run:
            with st.spinner("선형 혼합 효과 모델(LME)을 피팅하고 비교 분석을 수행 중입니다..."):
                ss["last_result"] = data.run_comparison(base_d, comp_ds, metrics,
                                                        selected_animals=(cfg['base_animals'] + cfg['comp_animals']) or None)

        if "last_result" in ss:
            result = ss["last_result"]; rows = result["rows"]
            st.success(f"분석 완료 — 대조군 {result['meta']['n_base']}마리 vs 실험군 {result['meta']['n_comp']}마리")
            st.divider()
            
            st.markdown("#### 1. 통계 요약 테이블")
            disp = pd.DataFrame({
                "행동 지표": rows["behavior_en"] + " (" + rows["behavior_kr"] + ")",
                "대조군 평균": rows["base_mean"].round(1), "실험군 평균": rows["comp_mean"].round(1),
                "변화율(%)": rows["pct_change"].round(1), "Cohen's d": rows["cohens_d"].round(3),
                "t-검정 p": rows["t_pval"].map(lambda p: "<0.001" if p < 0.001 else f"{p:.3f}"),
                "LME 계수": rows["lme_coef"].round(4),
                "LME p": rows["lme_pval"].map(lambda p: "<0.001" if pd.notna(p) and p < 0.001 else (f"{p:.3f}" if pd.notna(p) else "—")),
                "유의성": rows["lme_pval"].map(sig_badge),
            })
            st.dataframe(disp, use_container_width=True, hide_index=True)

            st.markdown("#### 2. 행동 지표 비교 그래프")
            fig = go.Figure()
            fig.add_bar(name=f"대조군 {dose_label(base_d)}", x=rows["behavior_en"], y=rows["base_mean"], marker_color="#4C72B0")
            fig.add_bar(name="실험군 " + "/".join(dose_label(d) for d in comp_ds), x=rows["behavior_en"], y=rows["comp_mean"], marker_color="#C44E52")
            fig.update_layout(barmode="group", height=380, yaxis_title="평균 점수 (0~100)",
                              margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.1), plot_bgcolor="white")
            fig.update_yaxes(gridcolor="#eef2f6")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 3. AI 해석 요약")
            sig = rows[(rows["lme_pval"].notna()) & (rows["lme_pval"] < 0.05)]
            lines = []
            for _, rr in sig.iterrows():
                direction = "증가" if rr["comp_mean"] > rr["base_mean"] else "감소"
                lines.append(f"**{rr['behavior_en']}({rr['behavior_kr']})** 지표가 실험군에서 유의하게 {direction} "
                             f"(변화율 {rr['pct_change']:+.1f}%, Cohen's d={rr['cohens_d']:.2f}, p<0.05)")
            if lines:
                st.info("대조군 대비 실험군에서 다음과 같은 유의한 행동 변화가 관찰되었습니다:\n\n- " + "\n- ".join(lines))
            else:
                st.info("선택한 지표에서 통계적으로 유의한 차이는 관찰되지 않았습니다 (p ≥ 0.05).")

            st.markdown("#### 4. 리포트 다운로드")
            template = cfg.get("template", "표준 리포트")
            if template == "프레젠테이션":
                from detail_helpers import build_comparison_pptx
                file_bytes = build_comparison_pptx(cfg, result, disp, lines, comp_type="group")
                file_ext = "pptx"
                mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                from detail_helpers import build_comparison_pdf
                file_bytes = build_comparison_pdf(cfg, result, disp, lines, comp_type="group")
                file_ext = "pdf"
                mime_type = "application/pdf"
                
            st.download_button("리포트 다운로드", file_bytes,
                               file_name=f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M')}.{file_ext}",
                               mime=mime_type, type="primary")
            st.download_button("결과 데이터(CSV) 다운로드", rows.to_csv(index=False).encode("utf-8-sig"),
                               file_name="comparison_result.csv", mime="text/csv")

            st.markdown("#### 5. 실험 히스토리에 저장")
            with st.form("save_exp_form", clear_on_submit=True):
                default_name = f"Yohimbine Dose {','.join(str(d) for d in comp_ds)} vs Control [{datetime.now().strftime('%Y-%m-%d')}]"
                exp_name = st.text_input("저장할 실험 이름", value=default_name)
                save_btn = st.form_submit_button("실험 히스토리에 저장", type="primary")
                if save_btn:
                    if not exp_name.strip():
                        st.error("실험 이름을 입력해주세요.")
                    else:
                        all_selected_animals = cfg['base_animals'] + cfg['comp_animals']
                        ok, msg = data.save_experiment(
                            name=exp_name.strip(),
                            experiment_type="Open Field",
                            base_dose=base_d,
                            comp_doses=comp_ds,
                            metrics=metrics,
                            animal_ids=all_selected_animals if len(all_selected_animals) > 0 else None,
                            status="분석 완료"
                        )
                        if ok:
                            st.success(f"실험 '{exp_name}'이(가) 저장되었습니다. '실험 관리' 탭에서 확인할 수 있습니다.")
                        else:
                            st.error(msg)

    elif comp_type == "individual":
        a_an, b_an = cfg["a_animal"], cfg["b_animal"]
        with st.container(border=True):
            st.markdown(f"""
            **비교 타입:** 개체별 비교
            **개체 A:** {animal_label(a_an)}
            **개체 B:** {animal_label(b_an)}
            **분석 지표:** {len(metrics)}개 ({', '.join(data.BEH_EN[m] for m in metrics)})
            **통계 모델:** 독립표본 t-검정 · 리포트: {cfg['template']}
            """)
        cp, _, cn = st.columns([2, 4, 4])
        cp.button("< 이전 단계", use_container_width=True, on_click=prev_step)
        run = cn.button("▶ 분석 실행 및 리포트 생성", type="primary", use_container_width=True)
        if run:
            with st.spinner("두 개체 간 t-검정을 수행 중입니다..."):
                ss["indiv_result"] = data.compare_individuals(a_an, b_an, metrics)

        if "indiv_result" in ss:
            r = ss["indiv_result"]; rows = r["rows"]
            st.success(f"비교 완료 — {r['a']}  vs  {r['b']}")
            st.divider()
            
            st.markdown("#### 1. 통계 요약 테이블")
            disp = pd.DataFrame({
                "행동 지표": rows["behavior_en"] + " (" + rows["behavior_kr"] + ")",
                f"개체 A ({r['a']}) 평균": rows["a_mean"].round(1),
                f"개체 B ({r['b']}) 평균": rows["b_mean"].round(1),
                "차이(B-A)": rows["diff"].round(1),
                "Cohen's d": rows["cohens_d"].round(3),
                "t-검정 p": rows["t_pval"].map(lambda p: "<0.001" if pd.notna(p) and p < 0.001 else (f"{p:.3f}" if pd.notna(p) else "—")),
                "유의성": rows["t_pval"].map(sig_badge),
            })
            st.dataframe(disp, use_container_width=True, hide_index=True)

            st.markdown("#### 2. 행동 지표 비교 그래프")
            fig = go.Figure()
            fig.add_bar(name=f"개체 A ({r['a']})", x=rows["behavior_en"], y=rows["a_mean"], marker_color="#4C72B0")
            fig.add_bar(name=f"개체 B ({r['b']})", x=rows["behavior_en"], y=rows["b_mean"], marker_color="#C44E52")
            fig.update_layout(barmode="group", height=380, yaxis_title="평균 점수 (0~100)",
                              margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.12), plot_bgcolor="white")
            fig.update_yaxes(gridcolor="#eef2f6")
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 3. AI 해석 요약")
            sig = rows[(rows["t_pval"].notna()) & (rows["t_pval"] < 0.05)]
            lines = []
            for _, rr in sig.iterrows():
                direction = "큼" if rr["b_mean"] > rr["a_mean"] else "작음"
                lines.append(f"**{rr['behavior_en']}({rr['behavior_kr']})** 지표가 개체 B({r['b']})에서 개체 A({r['a']}) 대비 유의하게 {direction} "
                             f"(차이 {rr['diff']:+.1f}, Cohen's d={rr['cohens_d']:.2f}, p<0.05)")
            if lines:
                st.info("개체 간 다음과 같은 유의한 행동 변화가 관찰되었습니다:\n\n- " + "\n- ".join(lines))
            else:
                st.info("선택한 지표에서 개체 간 통계적으로 유의한 차이는 관찰되지 않았습니다 (p ≥ 0.05).")

            st.markdown("#### 4. 리포트 다운로드")
            pdf_disp = disp.copy()
            pdf_disp.rename(columns={
                f"개체 A ({r['a']}) 평균": "대조군 평균",
                f"개체 B ({r['b']}) 평균": "실험군 평균",
                "차이(B-A)": "변화율(%)",
                "t-검정 p": "LME p",
                "LME p": "LME p",
                "LME 계수": "LME 계수"
            }, inplace=True)
            if "LME 계수" not in pdf_disp.columns:
                pdf_disp["LME 계수"] = "—"

            template = cfg.get("template", "표준 리포트")
            if template == "프레젠테이션":
                from detail_helpers import build_comparison_pptx
                file_bytes = build_comparison_pptx(cfg, r, pdf_disp, lines, comp_type="individual")
                file_ext = "pptx"
                mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            else:
                from detail_helpers import build_comparison_pdf
                file_bytes = build_comparison_pdf(cfg, r, pdf_disp, lines, comp_type="individual")
                file_ext = "pdf"
                mime_type = "application/pdf"

            st.download_button("리포트 다운로드", file_bytes,
                               file_name=f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M')}.{file_ext}",
                               mime=mime_type, type="primary")
            st.download_button("결과 데이터(CSV) 다운로드", rows.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"individual_{r['a']}_vs_{r['b']}.csv", mime="text/csv")

    else:  # time
        an, n_win = cfg["animal"], cfg["n_win"]
        with st.container(border=True):
            st.markdown(f"""
            **비교 타입:** 시간대별 비교
            **분석 개체:** {animal_label(an)}
            **구간 분할:** {n_win}개 구간
            **분석 지표:** {len(metrics)}개 ({', '.join(data.BEH_EN[m] for m in metrics)})
            **통계 모델:** 독립표본 t-검정 · 리포트: {cfg['template']}
            """)
        cp, _, cn = st.columns([2, 4, 4])
        cp.button("< 이전 단계", use_container_width=True, on_click=prev_step)
        run = cn.button("▶ 분석 실행 및 리포트 생성", type="primary", use_container_width=True)
        if run:
            with st.spinner("시간 구간별 통계 분석을 수행 중입니다..."):
                ss["time_result"] = data.compare_time_windows(an, metrics, n_win)

        if "time_result" in ss:
            r = ss["time_result"]; rows = r["rows"]; tl = r["timeline"]
            if rows.empty:
                st.warning("해당 개체의 데이터가 없습니다.")
            else:
                st.success(f"분석 완료 — {r['animal']} · {r['n_windows']}개 구간")
                st.divider()
                
                st.markdown("#### 1. 통계 요약 테이블")
                win_cols = [c for c in rows.columns if c.startswith("구간")]
                disp = pd.DataFrame({"행동 지표": rows["behavior_en"] + " (" + rows["behavior_kr"] + ")"})
                for w in win_cols:
                    disp[w] = rows[w].round(1)
                disp["변화(첫→끝)"] = rows["change"].round(1)
                disp["t-검정 p"] = rows["t_pval"].map(lambda p: "<0.001" if pd.notna(p) and p < 0.001 else (f"{p:.3f}" if pd.notna(p) else "—"))
                disp["유의성"] = rows["t_pval"].map(sig_badge)
                st.dataframe(disp, use_container_width=True, hide_index=True)

                st.markdown("#### 2. 시간에 따른 행동 점수 (연속)")
                fig = go.Figure()
                palette = ["#3b82f6", "#22c55e", "#ef4444", "#a855f7", "#d97706"]
                for idx_m, m in enumerate(r["metrics"]):
                    fig.add_scatter(x=tl["min"], y=tl[m] * 100, mode="lines",
                                    name=data.BEH_EN[m], line=dict(color=palette[idx_m % 5], width=1.5))
                fig.update_layout(height=380, xaxis_title="시간 (분)", yaxis_title="점수 (0~100)",
                                  margin=dict(t=20, b=10), legend=dict(orientation="h", y=1.12), plot_bgcolor="white")
                fig.update_yaxes(gridcolor="#eef2f6")
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("#### 3. AI 해석 요약")
                sig = rows[(rows["t_pval"].notna()) & (rows["t_pval"] < 0.05)]
                lines = []
                for _, rr in sig.iterrows():
                    direction = "증가" if rr["change"] > 0 else "감소"
                    lines.append(f"**{rr['behavior_en']}({rr['behavior_kr']})** 지표가 시간 경과에 따라 유의하게 {direction} "
                                 f"(변화 {rr['change']:+.1f}, p<0.05)")
                if lines:
                    st.info("시간 경과에 따라 다음과 같은 유의한 행동 변화가 관찰되었습니다:\n\n- " + "\n- ".join(lines))
                else:
                    st.info("선택한 지표에서 시간대 경과에 따른 통계적으로 유의한 차이는 관찰되지 않았습니다 (p ≥ 0.05).")

                st.markdown("#### 4. 리포트 다운로드")
                pdf_disp = disp.copy()
                if "LME 계수" not in pdf_disp.columns:
                    pdf_disp["LME 계수"] = "—"
                if "LME p" not in pdf_disp.columns:
                    pdf_disp["LME p"] = pdf_disp["t-검정 p"]

                template = cfg.get("template", "표준 리포트")
                if template == "프레젠테이션":
                    from detail_helpers import build_comparison_pptx
                    file_bytes = build_comparison_pptx(cfg, r, pdf_disp, lines, comp_type="time")
                    file_ext = "pptx"
                    mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                else:
                    from detail_helpers import build_comparison_pdf
                    file_bytes = build_comparison_pdf(cfg, r, pdf_disp, lines, comp_type="time")
                    file_ext = "pdf"
                    mime_type = "application/pdf"

                st.download_button("리포트 다운로드", file_bytes,
                                   file_name=f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M')}.{file_ext}",
                                   mime=mime_type, type="primary")
                st.download_button("결과 데이터(CSV) 다운로드", rows.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"timewindows_{r['animal']}.csv", mime="text/csv")
 