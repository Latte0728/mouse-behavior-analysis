"""
01_dashboard.py — 대시보드(요약 화면)
흐름: data.get_overview()/get_group_means()/get_model_results()
      → KPI 카드 · 투여군 도넛 · 최근 LME 분석 요약 · 빠른 작업 버튼 렌더.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import datasource as data  # dashboard/datasource.py (루트 data/ 폴더와 이름 충돌 방지)

st.markdown("""
<style>
    .metric-card { background-color: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; display: flex; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05); height: 130px; }
    .metric-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; justify-content: center; align-items: center; font-size: 24px; margin-right: 15px; }
    .metric-info { display: flex; flex-direction: column; }
    .metric-label { color: #64748b; font-size: 0.9rem; font-weight: 600; margin-bottom: 5px; }
    .metric-value { color: #0f172a; font-size: 1.8rem; font-weight: 700; }
    .summary-list-item { display: flex; align-items: center; justify-content: space-between; padding: 17px 0; border-bottom: 1px solid #f1f5f9; }
    .summary-list-item:last-child { border-bottom: none; }
    .summary-name { color: #334155; font-size: 0.95rem; flex: 2; }
    .summary-metric { color: #64748b; font-size: 0.9rem; flex: 1.5; }
    .summary-val.up { color: #ef4444; font-weight: 600; }
    .summary-val.down { color: #22c55e; font-weight: 600; }
    .summary-pval { color: #94a3b8; font-size: 0.85rem; width: 100px; text-align: right; line-height: 1.3; }
    .summary-list-header { display: flex; align-items: center; justify-content: space-between; padding: 10px 0 15px 0; border-bottom: 2px solid #e2e8f0; color: #64748b; font-size: 0.85rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── 실제 데이터 로드 ────────────────────────────────────────────────────────
ov = data.get_overview()
df_groups = data.get_group_means()
df_models = data.get_model_results()

# ── 헤더(제목·날짜) ─────────────────────────────────────────────────────────
col_title, col_date = st.columns([3, 1])
with col_title:
    st.markdown('<h1 class="header-title">대시보드</h1>', unsafe_allow_html=True)
with col_date:
    st.markdown(f'<div style="text-align:right; color:#64748b; padding-top:20px;">{datetime.now().strftime("%Y-%m-%d (%a)")}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Top Metrics (실제 수치) ─────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
svg_flask = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.31M14 2v7.31M8.5 2h7M14 9.3l4 9V19a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-.7l4-9Z"/></svg>'
svg_mouse = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10a4 4 0 0 0-4-4h-2a6 6 0 0 0-6 6v2a6 6 0 0 0 6 6h12a2 2 0 0 0 2-2v-4a4 4 0 0 0-4-4z"/><circle cx="15" cy="11" r="1"/><path d="M4 12c-1.1 0-2 .9-2 2v2"/></svg>'
svg_clipboard = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M9 14l2 2 4-4"/></svg>'
svg_doc = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'

metrics = [
    (m1, "전체 개체", ov['total_animals'], svg_mouse, "#fef2f2", "#ef4444"),
    (m2, "투여군(그룹)", ov['total_groups'], svg_flask, "#eff6ff", "#3b82f6"),
    (m3, "분석 완료 지표<br><span style='font-size:0.75rem; font-weight:400; color:#94a3b8;'>(이동성, 탐색성, 불안, 과활동성, 경직)</span>", ov['completed_analyses'], svg_clipboard, "#f0fdf4", "#22c55e"),
    (m4, "총 분석 프레임", f"{ov['total_frames']/1e6:.1f}M", svg_doc, "#fefce8", "#eab308"),
]
for col, label, val, icon, bg, color in metrics:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon" style="background-color: {bg}; color: {color};">{icon}</div>
            <div class="metric-info"><span class="metric-label">{label}</span><span class="metric-value">{val}</span></div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br><br>", unsafe_allow_html=True)

# ── 그리드 레이아웃 (1행: 비교 실험 & 그룹 분포) ──────────────────────────────────────────
row1_col1, row1_col2 = st.columns([6, 4])

with row1_col1:
    with st.container(border=True, height=360):
        st.markdown('<div class="card-header">분석 가능 데이터 현황</div>', unsafe_allow_html=True)
        ctrl_n = int(df_groups[df_groups['dose'] == 0]['n'].iloc[0]) if (df_groups['dose'] == 0).any() else 0
        exp_rows = []
        model_ok = not df_models.empty and (df_models['status'] == 'OK').any()
        for _, g in df_groups[df_groups['dose'] != 0].iterrows():
            d = int(g['dose'])
            exp_rows.append({
                "비교 가능 그룹": f"Control & Dose {d}",
                "테스트 유형": "Open Field",
                "투입 개체 수": int(g['n']) + ctrl_n,
                "상태": "데이터 활성화" if model_ok else "데이터 대기중",
            })
        st.dataframe(pd.DataFrame(exp_rows), use_container_width=True, hide_index=True)

with row1_col2:
    with st.container(border=True, height=360):
        st.markdown('<div class="card-header">실험 그룹 분포</div>', unsafe_allow_html=True)
        total_n = int(df_groups['n'].sum())
        labels, counts, colors = [], [], []
        for _, g in df_groups.iterrows():
            d = int(g['dose'])
            labels.append("Control (0 mg/kg)" if d == 0 else f"Dose {d} mg/kg")
            counts.append(int(g['n']))
            colors.append(data.DOSE_COLORS.get(d, "#888"))
        df_pie = pd.DataFrame({"Group": labels, "Count": counts})
        fig = px.pie(df_pie, values='Count', names='Group', hole=0.5,
                     color='Group', color_discrete_map=dict(zip(labels, colors)))
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=False, height=230)
        st.plotly_chart(fig, use_container_width=True)

        legend = ""
        for lab, cnt, clr in zip(labels, counts, colors):
            pct = cnt / total_n * 100 if total_n else 0
            legend += f'<div style="display:flex; justify-content:space-between; margin-bottom:5px; font-size:0.8rem;"><span style="color:{clr};">● {lab}</span> <span>{cnt} ({pct:.0f}%)</span></div>'
        st.markdown(f'<div style="color:#475569; padding: 0 10px;">{legend}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 그리드 레이아웃 (2행: LME 분석 요약 & 막대 그래프) ─────────────────────────────────────
row2_col1, row2_col2 = st.columns([6, 4])

with row2_col1:
    with st.container(border=True, height=490):
        st.markdown('<div class="card-header">전체 투여군(0~6mg/kg) 행동 변화 추세 (LME 분석)</div>', unsafe_allow_html=True)
        svg_micro = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px; vertical-align:middle; color:#3b82f6;"><path d="M6 18h8"/><path d="M3 22h18"/><path d="M14 22a7 7 0 1 0 0-14h-1"/><path d="M9 14h2"/></svg>'

        if df_models.empty:
            st.info("아직 분석 결과가 없습니다.")
        else:
            dm = df_models.copy()
            dm['absp'] = dm['dose_pval'].fillna(1)
            dm = dm.sort_values('absp')
            items = (
                "<div class='summary-list-header'>"
                "<span class='summary-name'>분석 요인 (원인)</span>"
                "<span class='summary-metric'>행동 지표 (결과)</span>"
                "<span class='summary-val' style='flex: 1.6;'>농도당 변화 추세 (기울기)</span>"
                "<span class='summary-pval'>통계적 신뢰도</span>"
                "</div>"
            )
            for _, r in dm.iterrows():
                beh_en = r['behavior'].replace('_Score', '')
                beh = data.BEH_KR.get(beh_en.lower(), beh_en)
                coef = r['dose_coef'] or 0
                up = coef >= 0
                arrow = "↑" if up else "↓"
                cls = "up" if up else "down"
                change_desc = f"{arrow} 1mg당 {abs(coef):.4f} {'증가' if up else '감소'}"
                
                p = r['dose_pval']
                if pd.isna(p):
                    ptxt = "알 수 없음"
                elif p < 0.001:
                    ptxt = "<div style='color:#0f172a; font-weight:700;'>매우 확실함</div><div style='font-size:0.75rem;'>p &lt; 0.001</div>"
                elif p < 0.05:
                    ptxt = f"<div style='color:#0f172a; font-weight:700;'>유의미함</div><div style='font-size:0.75rem;'>p = {p:.3f}</div>"
                else:
                    ptxt = f"<div style='color:#94a3b8;'>차이 미미함</div><div style='font-size:0.75rem;'>p = {p:.3f}</div>"
                    
                items += (
                    f"<div class='summary-list-item'>"
                    f"<span class='summary-name'>{svg_micro}약물 투여량 (0, 1, 3, 6 mg/kg)</span>"
                    f"<span class='summary-metric'>{beh}</span>"
                    f"<span class='summary-val {cls}' style='flex: 1.6;'>{change_desc}</span>"
                    f"<span class='summary-pval'>{ptxt}</span>"
                    f"</div>"
                )
            
            # 가이드 텍스트의 여백을 늘리고 줄간격을 더 확보하여 전체 카드의 세로 길이를 우측 막대 그래프 카드에 일치시킴
            items += (
                "<div style='margin-top: 25px; font-size: 0.85rem; color: #475569; line-height: 1.6;'>"
                "<div style='font-weight: 700; color: #0f172a; margin-bottom: 8px;'>LME 분석 가이드</div>"
                "• <b>농도당 변화 추세(기울기)</b>: 요힘빈 투여량이 1mg/kg 증가할 때 나타나는 지표별 점수 변화량입니다.<br>"
                "• <b>통계적 신뢰도 (p-value)</b>: 통계적 유의성 검정 결과로, p-value가 0.05 미만일 때 약물 투여 효과가 유의미하다고 판단합니다.<br>"
                "• 본 요약은 개체 간의 선천적 행동 편차(무작위 효과)를 통제한 보정 결과입니다."
                "</div>"
            )
            st.markdown(items, unsafe_allow_html=True)

with row2_col2:
    with st.container(border=True, height=490):
        st.markdown('<div class="card-header">행동 지표별 추세 (막대 그래프)</div>', unsafe_allow_html=True)
        if df_models.empty:
            st.info("아직 분석 결과가 없습니다.")
        else:
            df_chart = df_models.copy()
            df_chart['absp'] = df_chart['dose_pval'].fillna(1)
            # 왼쪽 표(위에서부터 유의미한 순)와 시각적으로 동일하게 맞추기 위해 역순 정렬(Plotly는 밑에서부터 그림)
            df_chart = df_chart.sort_values('absp', ascending=False)
            
            df_chart['beh_kr'] = df_chart['behavior'].apply(lambda x: data.BEH_KR.get(x.replace('_Score', '').lower(), x))
            df_chart['Direction'] = df_chart['dose_coef'].apply(lambda x: '증가' if x >= 0 else '감소')
            
            # 왼쪽 카드 섹션과 동일한 텍스트 포맷 적용
            def format_text(r):
                arrow = "↑" if r['dose_coef'] >= 0 else "↓"
                desc = "증가" if r['dose_coef'] >= 0 else "감소"
                return f"{arrow} 1mg당 {abs(r['dose_coef']):.4f} {desc}"
            
            df_chart['text_label'] = df_chart.apply(format_text, axis=1)
            
            fig2 = px.bar(
                df_chart, 
                x='dose_coef', 
                y='beh_kr', 
                orientation='h',
                color='Direction',
                color_discrete_map={'증가': '#ef4444', '감소': '#22c55e'},
                text='text_label'
            )
            fig2.update_traces(textposition='auto')
            # 컨테이너 높이(490)에 맞게 차트 높이를 380으로 조정
            fig2.update_layout(
                margin=dict(t=10, b=30, l=10, r=30),
                xaxis_title="농도 1mg당 변화량 (기울기)",
                yaxis_title="",
                height=380,
                showlegend=False
            )
            st.plotly_chart(fig2, use_container_width=True)
 