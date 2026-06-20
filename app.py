"""My Wallet Copilot — Streamlit 앱.

카드 이용내역(.xls)을 업로드하면 소비 패턴을 시각화하고,
자연어로 질문하면 LangGraph + Claude 에이전트가 데이터 기반으로 답한다.

실행:  streamlit run app.py
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

st.set_page_config(page_title="My Wallet Copilot", page_icon="💰", layout="wide")


def _won(x: float) -> str:
    return f"{x:,.0f}원"


@st.cache_data(show_spinner="소비 내역을 분석하는 중...")
def load_data(file_bytes: bytes | None, use_llm: bool, model: str) -> pd.DataFrame:
    """파일 바이트(또는 기본 파일)를 로드·분류한다. 결과는 캐시된다."""
    source = io.BytesIO(file_bytes) if file_bytes else DEFAULT_DATA
    df = load_transactions(source)
    return categorize(df, use_llm=use_llm, model=model)


# ── 사이드바 ────────────────────────────────────────────────────────────────
st.sidebar.title("💰 My Wallet Copilot")
st.sidebar.caption("카드 소비 분석 AI 에이전트")

uploaded = st.sidebar.file_uploader("카드 이용내역 (.xls/.xlsx)", type=["xls", "xlsx"])
model = st.sidebar.text_input("Claude 모델", os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8"))
use_llm = st.sidebar.checkbox(
    "미분류 가맹점을 Claude로 분류",
    value=os.getenv("WALLET_COPILOT_LLM_CATEGORIZE", "false").lower() == "true",
    help="규칙으로 분류되지 않은 가맹점만 Claude에게 물어봅니다. (토큰 소비)",
)

has_key = bool(os.getenv("ANTHROPIC_API_KEY"))
if has_key:
    st.sidebar.success("ANTHROPIC_API_KEY 감지됨 ✔")
else:
    st.sidebar.warning("ANTHROPIC_API_KEY 미설정 — 챗봇/LLM 분류는 비활성화됩니다.")

file_bytes = uploaded.getvalue() if uploaded else None
if uploaded is None:
    st.sidebar.info("업로드하지 않으면 샘플 데이터로 분석합니다.")

df = load_data(file_bytes, use_llm and has_key, model)

# ── 본문 ───────────────────────────────────────────────────────────────────
tab_dash, tab_chat = st.tabs(["📊 대시보드", "💬 챗봇"])

with tab_dash:
    s = A.spending_summary(df)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총지출", _won(s["총지출"]))
    c2.metric("월평균", _won(s["월평균"]))
    c3.metric("거래건수", f"{s['거래건수']}건")
    c4.metric("건당평균", _won(s["건당평균"]))
    st.caption(f"분석 기간: {s['시작일']} ~ {s['종료일']} ({s['분석개월수']}개월)")

    # 자동 인사이트.
    cat = A.category_breakdown(df)
    wk = A.weekday_spending(df)
    chg = A.category_monthly_change(df)
    top_cat = cat.iloc[0]
    top_wk = wk.loc[wk["합계"].idxmax()]
    insights = [
        f"가장 많이 쓰는 카테고리는 **{top_cat.category}** ({_won(top_cat.합계)}, 전체의 {top_cat.비중}%)입니다.",
        f"요일별로는 **{top_wk.요일}요일**에 가장 많이 ({_won(top_wk.합계)}) 씁니다.",
    ]
    if not chg.empty:
        drv = chg.iloc[0]
        if drv.증감액 > 0:
            insights.append(
                f"최근 달에는 **{drv.category}** 지출이 전월보다 {_won(drv.증감액)} 늘었습니다."
            )
    save = A.savings_estimate(df, top_cat.category, 30)
    insights.append(
        f"**{top_cat.category}**를 30% 줄이면 월 {_won(save['월절약액'])}, "
        f"연 {_won(save['연절약액'])}을 아낄 수 있어요."
    )
    st.info("  \n".join("• " + t for t in insights))

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("카테고리별 지출")
        fig = px.pie(cat, names="category", values="합계", hole=0.45)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)
    with col_r:
        st.subheader("월별 지출 추이")
        mt = A.monthly_trend(df)
        fig = px.bar(mt, x="year_month", y="합계", text_auto=".2s", labels={"year_month": "월", "합계": "지출"})
        st.plotly_chart(fig, use_container_width=True)

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("요일별 지출")
        fig = px.bar(wk, x="요일", y="합계", text_auto=".2s", labels={"합계": "지출"})
        st.plotly_chart(fig, use_container_width=True)
    with col_r:
        st.subheader("시간대별 지출")
        tb = A.time_bucket_spending(df)
        fig = px.bar(tb, x="시간대", y="합계", text_auto=".2s", labels={"합계": "지출"})
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("지출 상위 가맹점")
    top = A.top_merchants(df, 10).copy()
    top["합계"] = top["합계"].map(_won)
    st.dataframe(top, use_container_width=True, hide_index=True)

    with st.expander("원본 거래 내역 보기"):
        st.dataframe(
            df[["date", "merchant", "category", "amount", "weekday", "time_bucket"]],
            use_container_width=True,
            hide_index=True,
        )

with tab_chat:
    st.subheader("무엇이든 물어보세요")
    st.caption(
        '예: "내가 가장 돈을 많이 쓰는 요일은?", "배달비 30% 줄이면 얼마 절약돼?", '
        '"지난달 대비 뭐가 늘었어?"'
    )

    if not has_key:
        st.warning("챗봇을 사용하려면 ANTHROPIC_API_KEY 환경변수를 설정하세요.")
    else:
        # 에이전트는 데이터/모델이 바뀔 때만 새로 만든다.
        sig = (id(df), model)
        if st.session_state.get("agent_sig") != sig:
            from src.agent import build_agent

            st.session_state.agent = build_agent(df, model=model)
            st.session_state.agent_sig = sig
            st.session_state.chat_history = []

        for role, msg in st.session_state.get("chat_history", []):
            st.chat_message(role).write(msg)

        if prompt := st.chat_input("질문을 입력하세요"):
            st.session_state.chat_history.append(("user", prompt))
            st.chat_message("user").write(prompt)
            with st.chat_message("assistant"):
                with st.spinner("분석 중..."):
                    try:
                        result = st.session_state.agent.invoke(
                            {"messages": [("user", prompt)]}
                        )
                        answer = result["messages"][-1].content
                    except Exception as e:  # noqa: BLE001
                        answer = f"오류가 발생했습니다: {e}"
                st.write(answer)
            st.session_state.chat_history.append(("assistant", answer))
