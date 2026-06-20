"""My Wallet Copilot — Agent Avatar Chat-first Streamlit App.

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


# ─────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────
def _won(x: float) -> str:
    return f"{x:,.0f}원"


@st.cache_data(show_spinner="소비 내역을 분석하는 중...")
def load_data(file_bytes: bytes | None, use_llm: bool, model: str) -> pd.DataFrame:
    source = io.BytesIO(file_bytes) if file_bytes else DEFAULT_DATA
    df = load_transactions(source)
    return categorize(df, use_llm=use_llm, model=model)


def calc_health_score(df: pd.DataFrame) -> tuple[int, str]:
    cat = A.category_breakdown(df)
    score = 100

    risky_categories = ["배달", "외식", "카페", "편의점", "쇼핑"]
    for _, row in cat.iterrows():
        category = str(row["category"])
        ratio = float(row["비중"])

        if category in risky_categories and ratio >= 25:
            score -= 12
        elif category in risky_categories and ratio >= 15:
            score -= 7

    score = max(45, min(98, score))

    if score >= 85:
        label = "아주 좋아요"
    elif score >= 70:
        label = "괜찮지만 개선 여지가 있어요"
    elif score >= 55:
        label = "주의가 필요해요"
    else:
        label = "소비 습관 점검이 필요해요"

    return score, label


def make_problem_list(df: pd.DataFrame) -> list[str]:
    cat = A.category_breakdown(df)
    wk = A.weekday_spending(df)
    problems = []

    top_cat = cat.iloc[0]
    top_wk = wk.loc[wk["합계"].idxmax()]

    problems.append(
        f"🚨 <b>{top_cat.category}</b> 지출 비중이 {top_cat.비중}%로 가장 높아요."
    )

    if str(top_cat.category) in ["배달", "외식", "카페", "편의점", "쇼핑"]:
        problems.append(
            f"💸 <b>{top_cat.category}</b>는 줄이면 바로 절약 효과가 큰 변동비예요."
        )

    problems.append(
        f"📅 <b>{top_wk.요일}요일</b> 소비가 가장 큽니다. 총 {_won(top_wk.합계)}를 사용했어요."
    )

    chg = A.category_monthly_change(df)
    if not chg.empty:
        drv = chg.iloc[0]
        if drv.증감액 > 0:
            problems.append(
                f"📈 최근 달에는 <b>{drv.category}</b> 지출이 전월보다 {_won(drv.증감액)} 증가했어요."
            )

    return problems[:4]


def get_summary(df: pd.DataFrame) -> dict:
    s = A.spending_summary(df)
    cat = A.category_breakdown(df)
    top_cat = cat.iloc[0]
    save = A.savings_estimate(df, top_cat.category, 30)
    score, score_label = calc_health_score(df)

    return {
        "spending": s,
        "category": cat,
        "top_cat": top_cat,
        "save": save,
        "score": score,
        "score_label": score_label,
        "problems": make_problem_list(df),
    }


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
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
    padding-top: 1.2rem;
    padding-bottom: 5rem;
    max-width: 980px;
}

.main {
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.13), transparent 32%),
        radial-gradient(circle at top right, rgba(14,165,233,0.12), transparent 30%),
        linear-gradient(180deg, #F8FAFC 0%, #EEF2F7 100%);
}

[data-testid="stSidebar"] {
    background: #F1F5F9;
}

.app-shell {
    padding: 28px 32px;
    border-radius: 32px;
    background:
        radial-gradient(circle at 88% 18%, rgba(139,92,246,0.55), transparent 30%),
        linear-gradient(135deg, #020617 0%, #111827 52%, #312E81 100%);
    color: white;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.28);
    margin-bottom: 28px;
}

.app-title {
    font-size: 34px;
    font-weight: 900;
    letter-spacing: -1px;
    margin: 0;
}

.app-subtitle {
    margin-top: 10px;
    color: rgba(255,255,255,0.68);
    font-size: 15px;
    line-height: 1.7;
}

.wallet-agent {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    margin: 22px 0;
}

.agent-avatar {
    width: 56px;
    height: 56px;
    min-width: 56px;
    border-radius: 20px;
    background:
        radial-gradient(circle at 30% 20%, rgba(255,255,255,0.45), transparent 26%),
        linear-gradient(135deg, #7C3AED, #2563EB);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 27px;
    box-shadow: 0 18px 45px rgba(37,99,235,0.28);
}

.agent-bubble {
    flex: 1;
    background: rgba(255,255,255,0.93);
    border: 1px solid rgba(226,232,240,0.95);
    border-radius: 28px;
    padding: 24px 26px;
    box-shadow: 0 18px 55px rgba(15, 23, 42, 0.08);
}

.agent-name {
    color: #020617;
    font-weight: 900;
    font-size: 17px;
    margin-bottom: 10px;
}

.agent-text {
    color: #334155;
    font-size: 15px;
    line-height: 1.8;
}

.agent-text b {
    color: #020617;
}

.user-bubble {
    margin: 18px 0 18px auto;
    max-width: 78%;
    background: #020617;
    color: white;
    padding: 17px 20px;
    border-radius: 24px 24px 6px 24px;
    box-shadow: 0 16px 45px rgba(15,23,42,0.16);
    font-weight: 600;
    line-height: 1.6;
}

.upload-card {
    margin-top: 18px;
    padding: 20px;
    border-radius: 24px;
    background: linear-gradient(135deg, #F8FAFC 0%, #FFFFFF 100%);
    border: 1px dashed #CBD5E1;
}

.status-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 16px;
}

.status-pill {
    padding: 9px 13px;
    border-radius: 999px;
    background: #EEF2FF;
    color: #3730A3;
    font-weight: 800;
    font-size: 13px;
}

.result-grid {
    display: grid;
    grid-template-columns: 1.1fr 1fr 1fr;
    gap: 14px;
    margin-top: 18px;
}

.result-card {
    padding: 22px;
    border-radius: 26px;
    background: rgba(255,255,255,0.94);
    border: 1px solid rgba(226,232,240,0.95);
    box-shadow: 0 16px 45px rgba(15, 23, 42, 0.07);
}

.result-label {
    color: #64748B;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 8px;
}

.result-value {
    color: #020617;
    font-size: 30px;
    font-weight: 900;
    letter-spacing: -1px;
}

.result-sub {
    color: #64748B;
    font-size: 13px;
    font-weight: 600;
    margin-top: 8px;
    line-height: 1.6;
}

.score-bar {
    width: 100%;
    height: 11px;
    border-radius: 999px;
    background: #E2E8F0;
    margin-top: 14px;
    overflow: hidden;
}

.score-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #2563EB, #7C3AED);
}

.problem-card {
    margin-top: 16px;
    padding: 24px;
    border-radius: 28px;
    background:
        radial-gradient(circle at top right, rgba(124,58,237,0.34), transparent 30%),
        linear-gradient(135deg, #020617, #1E293B);
    color: white;
    box-shadow: 0 22px 65px rgba(15, 23, 42, 0.20);
}

.problem-card h3 {
    margin: 0 0 16px 0;
    font-size: 23px;
    font-weight: 900;
}

.problem-card li {
    margin: 10px 0;
    color: rgba(255,255,255,0.82);
    line-height: 1.7;
}

.action-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 18px;
}

.stButton > button {
    width: 100%;
    min-height: 48px;
    border-radius: 18px;
    border: 1px solid #E2E8F0;
    background: white;
    color: #020617;
    font-weight: 850;
    box-shadow: 0 10px 28px rgba(15,23,42,0.06);
}

.stButton > button:hover {
    border-color: #7C3AED;
    color: #5B21B6;
    transform: translateY(-1px);
}

.chart-card {
    margin-top: 16px;
    padding: 24px;
    border-radius: 28px;
    background: rgba(255,255,255,0.94);
    border: 1px solid rgba(226,232,240,0.95);
    box-shadow: 0 16px 45px rgba(15, 23, 42, 0.07);
}

.chat-input-spacer {
    height: 12px;
}

[data-testid="stFileUploader"] section {
    border-radius: 18px;
    background: #F8FAFC;
}

@media (max-width: 900px) {
    .result-grid {
        grid-template-columns: 1fr;
    }

    .action-grid {
        grid-template-columns: 1fr;
    }

    .app-title {
        font-size: 28px;
    }

    .wallet-agent {
        gap: 12px;
    }

    .agent-avatar {
        width: 48px;
        height: 48px;
        min-width: 48px;
    }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# UI Components
# ─────────────────────────────────────────────
def agent_message(content: str) -> None:
    st.markdown(
        f"""
<div class="wallet-agent">
    <div class="agent-avatar">🤖</div>
    <div class="agent-bubble">
        <div class="agent-name">Wallet Agent</div>
        <div class="agent-text">{content}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def user_message(content: str) -> None:
    st.markdown(
        f"""
<div class="user-bubble">{content}</div>
""",
        unsafe_allow_html=True,
    )


def render_result_cards(summary: dict) -> None:
    score = summary["score"]
    score_label = summary["score_label"]
    save = summary["save"]
    s = summary["spending"]
    top_cat = summary["top_cat"]

    st.markdown(
        f"""
<div class="result-grid">
    <div class="result-card">
        <div class="result-label">🩺 소비 건강도</div>
        <div class="result-value">{score}점</div>
        <div class="score-bar">
            <div class="score-fill" style="width:{score}%;"></div>
        </div>
        <div class="result-sub">{score_label}</div>
    </div>

    <div class="result-card">
        <div class="result-label">💸 이번 기간 총지출</div>
        <div class="result-value">{_won(s["총지출"])}</div>
        <div class="result-sub">월평균 {_won(s["월평균"])} · {s["거래건수"]}건</div>
    </div>

    <div class="result-card">
        <div class="result-label">💰 절약 가능 금액</div>
        <div class="result-value">{_won(save["월절약액"])}</div>
        <div class="result-sub">{top_cat.category} 30% 절감 기준<br>연 {_won(save["연절약액"])} 가능</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_problem_card(summary: dict) -> None:
    problems = summary["problems"]
    items = "".join(f"<li>{p}</li>" for p in problems)

    st.markdown(
        f"""
<div class="problem-card">
    <h3>AI가 발견한 문제</h3>
    <ul>{items}</ul>
</div>
""",
        unsafe_allow_html=True,
    )


def render_charts(df: pd.DataFrame) -> None:
    cat = A.category_breakdown(df)
    mt = A.monthly_trend(df)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("카테고리별 지출")
        fig = px.pie(cat, names="category", values="합계", hole=0.58)
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(
            height=390,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.subheader("월별 지출 추이")
        fig = px.bar(
            mt,
            x="year_month",
            y="합계",
            text_auto=".2s",
            labels={"year_month": "월", "합계": "지출"},
        )
        fig.update_layout(
            height=390,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_detail_analysis(df: pd.DataFrame) -> None:
    with st.expander("상세 분석 보기"):
        wk = A.weekday_spending(df)
        tb = A.time_bucket_spending(df)

        col_l, col_r = st.columns(2)

        with col_l:
            st.subheader("요일별 소비")
            fig = px.bar(wk, x="요일", y="합계", text_auto=".2s")
            fig.update_layout(
                height=330,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("시간대별 소비")
            fig = px.bar(tb, x="시간대", y="합계", text_auto=".2s")
            fig.update_layout(
                height=330,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("지출 상위 가맹점")
        top = A.top_merchants(df, 10).copy()
        top["합계"] = top["합계"].map(_won)
        st.dataframe(top, use_container_width=True, hide_index=True)


def run_agent_question(prompt: str, model: str) -> str:
    if st.session_state.get("agent_sig") != (id(st.session_state.df), model):
        from src.agent import build_agent

        st.session_state.agent = build_agent(st.session_state.df, model=model)
        st.session_state.agent_sig = (id(st.session_state.df), model)

    result = st.session_state.agent.invoke({"messages": [("user", prompt)]})
    return result["messages"][-1].content


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown(
    """
<div class="app-shell">
    <h1 class="app-title">💰 My Wallet Copilot</h1>
    <div class="app-subtitle">
        카드 이용내역을 올리면 Wallet Agent가 소비 건강도, 문제 패턴, 절약 가능 금액을 말풍선과 카드로 정리해줘요.
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# Sidebar Settings
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
# Session State
# ─────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None

if "summary" not in st.session_state:
    st.session_state.summary = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ─────────────────────────────────────────────
# Upload Flow
# ─────────────────────────────────────────────
if st.session_state.df is None:
    agent_message(
        """
안녕하세요 👋<br><br>
저는 <b>Wallet Agent</b>입니다.<br>
카드 이용내역을 올려주시면 소비 패턴을 분석해서<br>
<b>소비 건강도, 문제 패턴, 절약 가능 금액</b>을 정리해드릴게요.
"""
    )

    st.markdown('<div class="wallet-agent"><div class="agent-avatar">📎</div><div class="agent-bubble">', unsafe_allow_html=True)

    st.markdown('<div class="agent-name">카드 이용내역 업로드</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="agent-text">.xls 또는 .xlsx 파일을 업로드해주세요. 샘플 데이터로도 시작할 수 있어요.</div>',
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "카드 이용내역 업로드",
        type=["xls", "xlsx"],
        label_visibility="collapsed",
    )

    col_a, col_b = st.columns([1, 3])
    with col_a:
        demo = st.button("샘플 데이터로 시작하기")
    with col_b:
        st.markdown(
            """
<div class="status-row">
    <span class="status-pill">1. 거래내역 읽기</span>
    <span class="status-pill">2. 카테고리 분류</span>
    <span class="status-pill">3. 소비 건강도 계산</span>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    if uploaded is not None or demo:
        file_bytes = uploaded.getvalue() if uploaded else None

        with st.spinner("Wallet Agent가 소비 내역을 분석하는 중..."):
            df = load_data(file_bytes, use_llm and has_key, model)
            st.session_state.df = df
            st.session_state.summary = get_summary(df)
            st.session_state.chat_history = []

        st.rerun()


# ─────────────────────────────────────────────
# Analysis Result Flow
# ─────────────────────────────────────────────
else:
    summary = st.session_state.summary or get_summary(st.session_state.df)

    agent_message(
        """
분석 완료했습니다 🤖<br><br>
이번 소비 내역에서 중요한 포인트를 먼저 정리해드릴게요.
"""
    )

    render_result_cards(summary)
    render_problem_card(summary)

    st.markdown(
        """
<div class="wallet-agent">
    <div class="agent-avatar">💬</div>
    <div class="agent-bubble">
        <div class="agent-name">다음에 무엇을 도와드릴까요?</div>
        <div class="agent-text">궁금한 내용을 바로 눌러보거나, 아래 채팅창에 직접 질문해보세요.</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("왜 이렇게 분석했어?"):
            st.session_state.pending_prompt = "왜 이렇게 분석했어?"
            st.rerun()
    with a2:
        if st.button("절약 방법 알려줘"):
            st.session_state.pending_prompt = "절약 방법 알려줘"
            st.rerun()
    with a3:
        if st.button("다음 달 예산 추천"):
            st.session_state.pending_prompt = "다음 달 예산 추천해줘"
            st.rerun()

    render_charts(st.session_state.df)
    render_detail_analysis(st.session_state.df)

    if st.button("다른 파일 다시 업로드하기"):
        st.session_state.df = None
        st.session_state.summary = None
        st.session_state.chat_history = []
        st.session_state.pending_prompt = None
        st.rerun()

    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

        user_message(prompt)

        if not has_key:
            agent_message("질문 기능을 사용하려면 <b>ANTHROPIC_API_KEY</b> 환경변수를 설정해주세요.")
        else:
            with st.spinner("Wallet Agent가 답변을 준비하는 중..."):
                try:
                    answer = run_agent_question(prompt, model)
                except Exception as e:
                    answer = f"오류가 발생했습니다: {e}"

            st.session_state.chat_history.append(("user", prompt))
            st.session_state.chat_history.append(("assistant", answer))
            agent_message(answer)

    for role, msg in st.session_state.chat_history:
        if role == "user":
            user_message(msg)
        else:
            agent_message(msg)

    prompt = st.chat_input("소비 내역에 대해 질문해보세요")

    if prompt:
        user_message(prompt)

        if not has_key:
            answer = "질문 기능을 사용하려면 <b>ANTHROPIC_API_KEY</b> 환경변수를 설정해주세요."
        else:
            with st.spinner("Wallet Agent가 소비 패턴을 분석하는 중..."):
                try:
                    answer = run_agent_question(prompt, model)
                except Exception as e:
                    answer = f"오류가 발생했습니다: {e}"

        st.session_state.chat_history.append(("user", prompt))
        st.session_state.chat_history.append(("assistant", answer))
        st.rerun()
