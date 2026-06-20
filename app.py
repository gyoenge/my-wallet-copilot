"""My Wallet Copilot — Chat-first Streamlit App.

실행:
streamlit run app.py
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src import analysis as A
from src.categorize import categorize
from src.data_loader import load_transactions

load_dotenv()

DEFAULT_DATA = Path(__file__).resolve().parent / "data" / "카드이용내역.xls"

st.set_page_config(
    page_title="My Wallet Copilot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def _won(x: float) -> str:
    return f"{x:,.0f}원"


@st.cache_data(show_spinner="소비 내역을 분석하는 중...")
def load_data(file_bytes: bytes | None, use_llm: bool, model: str) -> pd.DataFrame:
    source = io.BytesIO(file_bytes) if file_bytes else DEFAULT_DATA
    df = load_transactions(source)
    return categorize(df, use_llm=use_llm, model=model)


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Pretendard', sans-serif;
}

[data-testid="stHeader"], #MainMenu, footer {
    display: none;
    visibility: hidden;
}

.block-container {
    padding-top: 1.4rem;
    padding-bottom: 4rem;
    max-width: 1180px;
}

.main {
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.16), transparent 32%),
        radial-gradient(circle at top right, rgba(14,165,233,0.14), transparent 30%),
        linear-gradient(180deg, #F8FAFC 0%, #EEF2F7 100%);
}

.app-shell {
    padding: 28px 32px;
    border-radius: 34px;
    background:
        linear-gradient(135deg, #020617 0%, #111827 46%, #312E81 100%);
    color: white;
    box-shadow: 0 30px 90px rgba(15, 23, 42, 0.30);
    margin-bottom: 24px;
}

.app-title {
    font-size: 42px;
    font-weight: 900;
    letter-spacing: -1.4px;
    margin: 0;
}

.app-subtitle {
    margin-top: 10px;
    color: rgba(255,255,255,0.68);
    font-size: 16px;
}

.agent-card {
    padding: 24px 28px;
    border-radius: 28px;
    background: rgba(255,255,255,0.9);
    border: 1px solid rgba(226,232,240,0.95);
    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
    margin-bottom: 22px;
}

.upload-zone {
    padding: 24px;
    border-radius: 26px;
    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px dashed #CBD5E1;
    margin-bottom: 20px;
}

.metric-card {
    padding: 22px 24px;
    border-radius: 24px;
    background: rgba(255,255,255,0.92);
    border: 1px solid rgba(226,232,240,0.95);
    box-shadow: 0 16px 42px rgba(15, 23, 42, 0.07);
}

.metric-label {
    color: #64748B;
    font-size: 13px;
    font-weight: 800;
}

.metric-value {
    color: #020617;
    font-size: 29px;
    font-weight: 900;
    letter-spacing: -0.8px;
    margin-top: 8px;
}

.insight-card {
    padding: 26px 30px;
    border-radius: 28px;
    background:
        radial-gradient(circle at top right, rgba(124,58,237,0.34), transparent 30%),
        linear-gradient(135deg, rgba(15,23,42,0.98), rgba(30,41,59,0.98));
    border: 1px solid rgba(148,163,184,0.22);
    color: white;
    box-shadow: 0 24px 70px rgba(15, 23, 42, 0.18);
    margin: 24px 0;
}

.insight-card h3 {
    margin-top: 0;
    font-size: 26px;
    font-weight: 900;
}

.insight-card p {
    color: rgba(255,255,255,0.78);
    font-size: 16px;
    line-height: 1.9;
}

.section-card {
    padding: 22px;
    border-radius: 26px;
    background: rgba(255,255,255,0.92);
    border: 1px solid rgba(226,232,240,0.95);
    box-shadow: 0 16px 42px rgba(15, 23, 42, 0.07);
    margin-bottom: 18px;
}

.example-chip {
    display: inline-block;
    padding: 10px 14px;
    border-radius: 999px;
    background: #F1F5F9;
    border: 1px solid #E2E8F0;
    color: #0F172A;
    font-size: 14px;
    font-weight: 700;
    margin: 4px 6px 4px 0;
}

.small-muted {
    color: #64748B;
    font-size: 14px;
    font-weight: 600;
}
</style>
""",
    unsafe_allow_html=True,
)


def metric_card(label: str, value: str, emoji: str) -> None:
    st.markdown(
        f"""
<div class="metric-card">
    <div class="metric-label">{emoji} {label}</div>
    <div class="metric-value">{value}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_dashboard(df: pd.DataFrame) -> None:
    s = A.spending_summary(df)
    cat = A.category_breakdown(df)
    wk = A.weekday_spending(df)
    chg = A.category_monthly_change(df)

    top_cat = cat.iloc[0]
    top_wk = wk.loc[wk["합계"].idxmax()]
    save = A.savings_estimate(df, top_cat.category, 30)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("총지출", _won(s["총지출"]), "💸")
    with c2:
        metric_card("월평균", _won(s["월평균"]), "📆")
    with c3:
        metric_card("거래건수", f"{s['거래건수']}건", "🧾")
    with c4:
        metric_card("건당평균", _won(s["건당평균"]), "⚡")

    st.markdown(
        f"""
<div class="small-muted" style="margin-top: 8px;">
분석 기간: {s['시작일']} ~ {s['종료일']} · {s['분석개월수']}개월
</div>
""",
        unsafe_allow_html=True,
    )

    insights = [
        f"가장 많이 쓰는 카테고리는 <b>{top_cat.category}</b>입니다. 총 {_won(top_cat.합계)}로 전체의 {top_cat.비중}%를 차지해요.",
        f"요일별로는 <b>{top_wk.요일}요일</b> 소비가 가장 큽니다. 총 {_won(top_wk.합계)}를 사용했어요.",
    ]

    if not chg.empty:
        drv = chg.iloc[0]
        if drv.증감액 > 0:
            insights.append(
                f"최근 달에는 <b>{drv.category}</b> 지출이 전월보다 {_won(drv.증감액)} 증가했습니다."
            )

    insights.append(
        f"<b>{top_cat.category}</b> 지출을 30% 줄이면 월 {_won(save['월절약액'])}, 연 {_won(save['연절약액'])} 절약할 수 있어요."
    )

    st.markdown(
        f"""
<div class="insight-card">
    <h3>✨ 분석이 끝났어요</h3>
    <p>{"<br>".join("• " + x for x in insights)}</p>
</div>
""",
        unsafe_allow_html=True,
    )

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("카테고리별 지출")
        fig = px.pie(cat, names="category", values="합계", hole=0.58)
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(
            height=400,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("월별 지출 추이")
        mt = A.monthly_trend(df)
        fig = px.bar(
            mt,
            x="year_month",
            y="합계",
            text_auto=".2s",
            labels={"year_month": "월", "합계": "지출"},
        )
        fig.update_layout(
            height=400,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("상세 분석 보기"):
        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("요일별 소비")
            wk_fig = px.bar(wk, x="요일", y="합계", text_auto=".2s")
            wk_fig.update_layout(
                height=340,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(wk_fig, use_container_width=True)

        with col_r:
            st.subheader("시간대별 소비")
            tb = A.time_bucket_spending(df)
            tb_fig = px.bar(tb, x="시간대", y="합계", text_auto=".2s")
            tb_fig.update_layout(
                height=340,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(tb_fig, use_container_width=True)

        st.subheader("지출 상위 가맹점")
        top = A.top_merchants(df, 10).copy()
        top["합계"] = top["합계"].map(_won)
        st.dataframe(top, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# App Header
# ─────────────────────────────────────────────
st.markdown(
    """
<div class="app-shell">
    <h1 class="app-title">💰 My Wallet Copilot</h1>
    <div class="app-subtitle">
        카드 이용내역을 업로드하면 소비 패턴을 분석하고, 이후 Wallet Agent에게 자유롭게 질문할 수 있어요.
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("설정")
    model = st.text_input(
        "Claude 모델",
        os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8"),
    )
    use_llm = st.toggle(
        "Claude로 미분류 가맹점 분류",
        value=os.getenv("WALLET_COPILOT_LLM_CATEGORIZE", "false").lower() == "true",
    )
    has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
    if has_key:
        st.success("ANTHROPIC_API_KEY 연결됨")
    else:
        st.warning("ANTHROPIC_API_KEY 없음")


# ─────────────────────────────────────────────
# Chat-first Flow
# ─────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None

if "dashboard_shown" not in st.session_state:
    st.session_state.dashboard_shown = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


with st.chat_message("assistant"):
    st.markdown(
        """
안녕하세요. 저는 **Wallet Agent**입니다.

먼저 카드 이용내역 파일을 업로드해주세요.  
업로드가 완료되면 소비 패턴을 분석해서 대시보드를 보여드릴게요.
"""
    )

    uploaded = st.file_uploader(
        "카드 이용내역 업로드",
        type=["xls", "xlsx"],
        label_visibility="collapsed",
    )

    demo = st.button("샘플 데이터로 시작하기")

    if uploaded is not None or demo:
        file_bytes = uploaded.getvalue() if uploaded else None

        with st.spinner("카드 이용내역을 분석하는 중..."):
            st.session_state.df = load_data(file_bytes, use_llm and has_key, model)
            st.session_state.dashboard_shown = True
            st.session_state.chat_history = []

        st.success("분석이 완료되었습니다. 아래에서 결과를 확인하세요.")


if st.session_state.df is not None and st.session_state.dashboard_shown:
    with st.chat_message("assistant"):
        render_dashboard(st.session_state.df)

        st.markdown(
            """
<div style="margin-top: 20px;">
    <span class="example-chip">이번 달 소비 요약해줘</span>
    <span class="example-chip">내가 가장 돈을 많이 쓰는 요일은?</span>
    <span class="example-chip">배달비 30% 줄이면 얼마 절약돼?</span>
    <span class="example-chip">지난달 대비 뭐가 늘었어?</span>
</div>
""",
            unsafe_allow_html=True,
        )

    if has_key:
        sig = (id(st.session_state.df), model)

        if st.session_state.get("agent_sig") != sig:
            from src.agent import build_agent

            st.session_state.agent = build_agent(st.session_state.df, model=model)
            st.session_state.agent_sig = sig

        for role, msg in st.session_state.chat_history:
            st.chat_message(role).write(msg)

        if prompt := st.chat_input("소비 내역에 대해 질문해보세요"):
            st.session_state.chat_history.append(("user", prompt))
            st.chat_message("user").write(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Wallet Agent가 소비 패턴을 분석하는 중..."):
                    try:
                        result = st.session_state.agent.invoke(
                            {"messages": [("user", prompt)]}
                        )
                        answer = result["messages"][-1].content
                    except Exception as e:
                        answer = f"오류가 발생했습니다: {e}"

                st.write(answer)

            st.session_state.chat_history.append(("assistant", answer))
    else:
        st.warning("질문 기능을 사용하려면 ANTHROPIC_API_KEY 환경변수를 설정하세요.")

