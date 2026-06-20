"""My Wallet Copilot — Kim-T Persona Chat-first Streamlit App.

실행:
streamlit run app.py

선택 이미지:
assets/kim-t-avatar.png
assets/kim-t-face.png
"""

from __future__ import annotations

import base64
import io
import os
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from src import analysis as A
from src.categorize import categorize
from src.data_loader import load_transactions

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA = BASE_DIR / "data" / "카드이용내역.xls"
AVATAR_MAIN = BASE_DIR / "assets" / "kim-t-avatar.png"
AVATAR_FACE = BASE_DIR / "assets" / "kim-t-face.png"

AGENT_NAME = "김티(T)"
AGENT_SUBTITLE = "팩폭 전문 현실 절친"

st.set_page_config(
    page_title="My Wallet Copilot",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# Utils
# ─────────────────────────────────────────────
def _won(x: float) -> str:
    return f"{x:,.0f}원"


def image_to_base64(path: Path) -> str | None:
    if not path.exists():
        return None

    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:image/png;base64,{encoded}"


def avatar_html(size: int = 48, variant: str = "face") -> str:
    path = AVATAR_FACE if variant == "face" else AVATAR_MAIN
    src = image_to_base64(path)

    if src:
        return f'<img src="{src}" class="avatar-img" style="width:{size}px;height:{size}px;" />'

    return f'<div class="avatar-fallback" style="width:{size}px;height:{size}px;">😏</div>'


def new_chat_session() -> str:
    chat_id = str(uuid.uuid4())
    st.session_state.chat_sessions[chat_id] = {
        "title": "새 팩폭 분석",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "df": None,
        "summary": None,
        "messages": [],
    }
    return chat_id


@st.cache_data(show_spinner="김티가 카드 내역 까보는 중...")
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
            score -= 18
        elif category in risky_categories and ratio >= 15:
            score -= 10

    score = max(35, min(98, score))

    if score >= 85:
        label = "오~ 꽤 잘하고 있는데?"
    elif score >= 70:
        label = "괜찮아. 근데 방심하면 바로 샌다."
    elif score >= 55:
        label = "음... 지갑에 경고등 켜졌다."
    else:
        label = "위험. 지금 소비 습관 점검해야 돼."

    return score, label


def make_problem_list(df: pd.DataFrame) -> list[dict]:
    cat = A.category_breakdown(df)
    wk = A.weekday_spending(df)
    chg = A.category_monthly_change(df)

    top_cat = cat.iloc[0]
    top_wk = wk.loc[wk["합계"].idxmax()]

    problems = [
        {
            "title": "지출 1등 발견",
            "level": "danger",
            "emoji": "🚨",
            "text": f"{top_cat.category} 지출이 전체의 {top_cat.비중}%야. 꽤 큼. 모른 척하면 통장만 운다.",
        },
        {
            "title": "요일 패턴 잡았다",
            "level": "warning",
            "emoji": "📅",
            "text": f"{top_wk.요일}요일에 {_won(top_wk.합계)} 썼어. 이 날 지갑 잠금장치 필요해 보임.",
        },
        {
            "title": "잘한 소비도 있음",
            "level": "good",
            "emoji": "👍",
            "text": "그래도 전부 망한 건 아냐. 줄일 곳만 줄이면 꽤 회복 가능해.",
        },
    ]

    if not chg.empty:
        drv = chg.iloc[0]
        if drv.증감액 > 0:
            problems.insert(
                1,
                {
                    "title": "전월 대비 증가",
                    "level": "warning",
                    "emoji": "📈",
                    "text": f"{drv.category} 지출이 전월보다 {_won(drv.증감액)} 늘었어. 우연이라고 하기엔 숫자가 너무 솔직해.",
                },
            )

    return problems[:3]


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
# Session State
# ─────────────────────────────────────────────
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = new_chat_session()

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

current_chat = st.session_state.chat_sessions[st.session_state.current_chat_id]


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

[data-testid="stHeader"] {
    background: transparent;
    height: 0;
}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {
    display: none;
    visibility: hidden;
}

[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    top: 12px;
    left: 12px;
    z-index: 1000;
}

[data-testid="stSidebarCollapsedControl"] button {
    background: #111827;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 14px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.28);
    color: white;
}

.block-container {
    padding-top: 1.2rem;
    padding-bottom: 5.8rem;
    max-width: 1120px;
}

.main {
    background:
        radial-gradient(circle at top left, rgba(124,58,237,0.20), transparent 32%),
        radial-gradient(circle at top right, rgba(59,130,246,0.14), transparent 30%),
        linear-gradient(180deg, #070A12 0%, #0B1120 48%, #050816 100%);
    color: #E5E7EB;
}

[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 50% 0%, rgba(124,58,237,0.16), transparent 30%),
        linear-gradient(180deg, #0B1020 0%, #070A12 100%);
    border-right: 1px solid rgba(148,163,184,0.12);
}

[data-testid="stSidebar"] * {
    color: #E5E7EB;
}

.sidebar-brand {
    font-size: 26px;
    font-weight: 900;
    line-height: 1.15;
    letter-spacing: -0.9px;
    color: white;
    margin-bottom: 18px;
}

.persona-name {
    color: #A78BFA;
    font-size: 24px;
    font-weight: 900;
    margin-top: 8px;
}

.persona-subtitle {
    color: #A78BFA;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 24px;
}

.sidebar-quote {
    position: relative;
    padding: 18px;
    border-radius: 22px;
    background:
        radial-gradient(circle at 75% 15%, rgba(124,58,237,0.35), transparent 36%),
        linear-gradient(135deg, rgba(30,41,59,0.9), rgba(17,24,39,0.85));
    border: 1px solid rgba(167,139,250,0.35);
    margin: 26px 0;
    min-height: 180px;
    overflow: hidden;
}

.sidebar-quote-text {
    color: #EDE9FE;
    font-size: 14px;
    line-height: 1.7;
    font-weight: 700;
    max-width: 58%;
}

.sidebar-quote-img {
    position: absolute;
    right: -12px;
    bottom: -14px;
    width: 135px;
}

.chat-nav-label {
    color: #94A3B8;
    font-size: 13px;
    font-weight: 800;
    margin: 22px 0 10px;
}

.app-hero {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr;
    gap: 24px;
    align-items: center;
    padding: 38px 42px;
    border-radius: 34px;
    background:
        radial-gradient(circle at 85% 22%, rgba(124,58,237,0.38), transparent 32%),
        linear-gradient(135deg, rgba(15,23,42,0.98), rgba(17,24,39,0.92));
    border: 1px solid rgba(148,163,184,0.16);
    box-shadow: 0 32px 90px rgba(0,0,0,0.38);
    margin-bottom: 28px;
    overflow: hidden;
}

.hero-eyebrow {
    color: #A78BFA;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 1.4px;
    margin-bottom: 16px;
}

.hero-title {
    color: white;
    font-size: 38px;
    font-weight: 900;
    letter-spacing: -1.4px;
    line-height: 1.2;
    margin-bottom: 14px;
}

.hero-subtitle {
    color: #CBD5E1;
    font-size: 16px;
    line-height: 1.8;
}

.hero-upload-card {
    margin-top: 24px;
    padding: 22px 24px;
    border-radius: 28px;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.12);
    backdrop-filter: blur(18px);
}

.hero-avatar-wrap {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    min-height: 300px;
}

.hero-avatar {
    width: 300px;
    max-width: 100%;
    filter: drop-shadow(0 35px 55px rgba(0,0,0,0.45));
}

.hero-avatar-fallback {
    font-size: 180px;
    filter: drop-shadow(0 35px 55px rgba(0,0,0,0.45));
}

.wallet-agent {
    display: flex;
    gap: 14px;
    align-items: flex-start;
    margin: 22px 0;
}

.avatar-img {
    object-fit: cover;
    border-radius: 18px;
    box-shadow: 0 14px 35px rgba(0,0,0,0.28);
}

.avatar-fallback {
    border-radius: 18px;
    background: linear-gradient(135deg, #7C3AED, #2563EB);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    box-shadow: 0 14px 35px rgba(0,0,0,0.28);
}

.agent-bubble {
    flex: 1;
    background:
        linear-gradient(135deg, rgba(30,41,59,0.92), rgba(15,23,42,0.88));
    border: 1px solid rgba(148,163,184,0.18);
    border-radius: 22px 22px 22px 8px;
    padding: 20px 22px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.22);
}

.agent-name {
    color: #CBD5E1;
    font-weight: 800;
    font-size: 14px;
    margin-bottom: 8px;
}

.agent-text {
    color: #F8FAFC;
    font-size: 15px;
    line-height: 1.85;
}

.agent-text b {
    color: white;
}

.user-bubble {
    margin: 18px 0 18px auto;
    max-width: 78%;
    background: linear-gradient(135deg, #6D28D9, #4F46E5);
    color: white;
    padding: 16px 19px;
    border-radius: 22px 22px 6px 22px;
    box-shadow: 0 18px 48px rgba(79,70,229,0.26);
    font-weight: 650;
    line-height: 1.65;
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
    background: rgba(124,58,237,0.18);
    color: #DDD6FE;
    border: 1px solid rgba(167,139,250,0.24);
    font-weight: 800;
    font-size: 13px;
}

.result-panel {
    padding: 24px;
    border-radius: 28px;
    background:
        radial-gradient(circle at top right, rgba(124,58,237,0.20), transparent 30%),
        linear-gradient(135deg, rgba(15,23,42,0.98), rgba(17,24,39,0.95));
    border: 1px solid rgba(148,163,184,0.16);
    box-shadow: 0 28px 80px rgba(0,0,0,0.28);
    margin: 18px 0;
}

.result-heading {
    color: white;
    font-size: 23px;
    font-weight: 900;
    margin-bottom: 18px;
}

.result-grid {
    display: grid;
    grid-template-columns: 1.05fr 1fr 1fr;
    gap: 14px;
}

.result-card {
    padding: 22px;
    border-radius: 22px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(148,163,184,0.14);
}

.result-label {
    color: #94A3B8;
    font-size: 13px;
    font-weight: 900;
    margin-bottom: 9px;
}

.result-value {
    color: #F8FAFC;
    font-size: 31px;
    font-weight: 900;
    letter-spacing: -1px;
}

.result-sub {
    color: #CBD5E1;
    font-size: 13px;
    font-weight: 600;
    margin-top: 9px;
    line-height: 1.7;
}

.badge-danger {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 10px;
    background: #7C3AED;
    color: white;
    font-size: 13px;
    margin-left: 8px;
}

.score-bar {
    width: 100%;
    height: 11px;
    border-radius: 999px;
    background: rgba(148,163,184,0.22);
    margin-top: 16px;
    overflow: hidden;
}

.score-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #7C3AED, #A78BFA);
}

.insight-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 14px;
    margin-top: 18px;
}

.insight-card {
    min-height: 210px;
    padding: 22px;
    border-radius: 24px;
    border: 1px solid rgba(148,163,184,0.16);
    background: rgba(255,255,255,0.045);
}

.insight-card.danger {
    border-color: rgba(248,113,113,0.35);
    background: linear-gradient(135deg, rgba(127,29,29,0.28), rgba(255,255,255,0.035));
}

.insight-card.warning {
    border-color: rgba(250,204,21,0.35);
    background: linear-gradient(135deg, rgba(113,63,18,0.28), rgba(255,255,255,0.035));
}

.insight-card.good {
    border-color: rgba(74,222,128,0.32);
    background: linear-gradient(135deg, rgba(20,83,45,0.26), rgba(255,255,255,0.035));
}

.insight-title {
    font-size: 18px;
    font-weight: 900;
    color: white;
    margin-bottom: 16px;
}

.insight-text {
    color: #CBD5E1;
    font-size: 14px;
    line-height: 1.75;
}

.tip-line {
    margin-top: 14px;
    color: #94A3B8;
    font-size: 14px;
    font-weight: 650;
}

.stButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 16px;
    border: 1px solid rgba(167,139,250,0.24);
    background: rgba(255,255,255,0.055);
    color: #C4B5FD;
    font-weight: 850;
    box-shadow: none;
}

.stButton > button:hover {
    border-color: #A78BFA;
    color: white;
    background: rgba(124,58,237,0.22);
    transform: translateY(-1px);
}

.chart-card {
    margin-top: 16px;
    padding: 24px;
    border-radius: 26px;
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(148,163,184,0.14);
}

[data-testid="stFileUploader"] section {
    border-radius: 18px;
    background: rgba(15,23,42,0.45);
    border-color: rgba(148,163,184,0.18);
}

[data-testid="stFileUploader"] * {
    color: #E5E7EB;
}

[data-testid="stChatInput"] {
    background: rgba(15,23,42,0.88);
}

@media (max-width: 900px) {
    .app-hero {
        grid-template-columns: 1fr;
    }

    .result-grid,
    .insight-grid {
        grid-template-columns: 1fr;
    }

    .hero-title {
        font-size: 30px;
    }

    .hero-avatar-wrap {
        min-height: 180px;
    }

    .hero-avatar {
        width: 220px;
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
    {avatar_html(52, "face")}
    <div class="agent-bubble">
        <div class="agent-name">{AGENT_NAME}</div>
        <div class="agent-text">{content}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def user_message(content: str) -> None:
    st.markdown(f'<div class="user-bubble">{content}</div>', unsafe_allow_html=True)


def render_result_panel(summary: dict) -> None:
    score = summary["score"]
    score_label = summary["score_label"]
    save = summary["save"]
    s = summary["spending"]
    top_cat = summary["top_cat"]

    st.markdown(
        f"""
<div class="result-panel">
    <div class="result-heading">분석 완료. 팩폭 나간다.</div>

    <div class="result-grid">
        <div class="result-card">
            <div class="result-label">이번 달 소비 건강 점수</div>
            <div class="result-value">{score}<span style="font-size:18px;color:#94A3B8;"> / 100</span>
                <span class="badge-danger">점검</span>
            </div>
            <div class="result-sub">{score_label}</div>
            <div class="score-bar">
                <div class="score-fill" style="width:{score}%;"></div>
            </div>
        </div>

        <div class="result-card">
            <div class="result-label">💸 총 소비 금액</div>
            <div class="result-value">{_won(s["총지출"])}</div>
            <div class="result-sub">월평균 {_won(s["월평균"])} · {s["거래건수"]}건<br>숫자는 거짓말 안 해.</div>
        </div>

        <div class="result-card">
            <div class="result-label">🐷 절약 가능 금액</div>
            <div class="result-value">{_won(save["월절약액"])}</div>
            <div class="result-sub">{top_cat.category} 30% 줄이면 이 정도 아낀다.<br>연 {_won(save["연절약액"])} 가능.</div>
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_insight_cards(summary: dict) -> None:
    cards = summary["problems"]

    html = '<div class="result-panel"><div class="result-heading">🎯 티의 팩폭 인사이트</div><div class="insight-grid">'

    for card in cards:
        html += f"""
<div class="insight-card {card["level"]}">
    <div class="insight-title">{card["emoji"]} {card["title"]}</div>
    <div class="insight-text">{card["text"]}</div>
</div>
"""

    html += """
</div>
<div class="tip-line">💡 팁: 배달/카페/쇼핑 지출을 30%만 줄여도 꽤 많이 살아난다. 마법 아님. 산수임.</div>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)


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
            height=380,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB",
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
            height=380,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E5E7EB",
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
                font_color="#E5E7EB",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            st.subheader("시간대별 소비")
            fig = px.bar(tb, x="시간대", y="합계", text_auto=".2s")
            fig.update_layout(
                height=330,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#E5E7EB",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("지출 상위 가맹점")
        top = A.top_merchants(df, 10).copy()
        top["합계"] = top["합계"].map(_won)
        st.dataframe(top, use_container_width=True, hide_index=True)


def run_agent_question(prompt: str, model: str) -> str:
    if st.session_state.get("agent_sig") != (st.session_state.current_chat_id, model):
        from src.agent import build_agent

        st.session_state.agent = build_agent(current_chat["df"], model=model)
        st.session_state.agent_sig = (st.session_state.current_chat_id, model)

    kim_t_prompt = f"""
너는 My Wallet Copilot의 팩폭 전문 현실 절친 '김티(T)'다.

성격:
- MBTI T 그 자체
- 이성적이고 솔직함
- 유쾌하지만 뼈 때림
- 뒤끝 없음
- 숫자 기반으로 말함
- 과소비에는 강하게 제동
- 합리적 소비는 쿨하게 칭찬

말투:
- 반말
- 짧고 직설적
- 너무 공격적이지는 않게 유머러스하게
- 데이터 기반으로 답변
- 금융 조언은 단정하지 말고 소비 관리 관점으로 말하기

사용자 질문:
{prompt}
"""

    result = st.session_state.agent.invoke({"messages": [("user", kim_t_prompt)]})
    return result["messages"][-1].content


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
<div class="sidebar-brand">💰 My Wallet<br>Copilot</div>
<div class="persona-name">김티(T)</div>
<div class="persona-subtitle">팩폭 전문 현실 절친</div>
""",
        unsafe_allow_html=True,
    )

    if st.button("➕ 새 대화 시작", use_container_width=True):
        st.session_state.current_chat_id = new_chat_session()
        st.session_state.pending_prompt = None
        st.rerun()

    st.markdown('<div class="chat-nav-label">오늘</div>', unsafe_allow_html=True)

    for chat_id, chat in reversed(list(st.session_state.chat_sessions.items())):
        title = chat.get("title", "새 팩폭 분석")
        created_at = chat.get("created_at", "")

        prefix = "● " if chat_id == st.session_state.current_chat_id else ""
        label = f"{prefix}{title}\n{created_at}"

        if st.button(label, key=f"chat_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.session_state.pending_prompt = None
            st.rerun()

    main_avatar = image_to_base64(AVATAR_MAIN)
    quote_img = f'<img src="{main_avatar}" class="sidebar-quote-img" />' if main_avatar else ""

    st.markdown(
        f"""
<div class="sidebar-quote">
    <div class="sidebar-quote-text">
        티의<br>팩폭 한마디<br><br>
        “돈은 안 쓰면 안 줄어. 너무 당연해서 문제야.”
    </div>
    {quote_img}
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="chat-nav-label">메뉴</div>', unsafe_allow_html=True)
    st.button("📊 대시보드", use_container_width=True)
    st.button("🧾 지출 내역", use_container_width=True)
    st.button("🎯 예산 관리", use_container_width=True)
    st.button("⚙️ 설정", use_container_width=True)

    with st.expander("모델 설정"):
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
# Hero
# ─────────────────────────────────────────────
main_avatar = image_to_base64(AVATAR_MAIN)

hero_avatar = (
    f'<img src="{main_avatar}" class="hero-avatar" />'
    if main_avatar
    else '<div class="hero-avatar-fallback">😏</div>'
)

st.markdown(
    f"""
<div class="app-hero">
    <div>
        <div class="hero-eyebrow">MY WALLET COPILOT · KIM-T MODE</div>
        <div class="hero-title">안녕. 난 팩폭 전문 현실 절친,<br>{AGENT_NAME}야 👋</div>
        <div class="hero-subtitle">
            카드 내역 올려봐. 내가 네 소비 습관, 낭비 포인트, 절약 가능 금액까지
            팩트로 때려줄게.
        </div>
        <div class="hero-upload-card">
            <span style="color:#94A3B8;">숨겨도 소용없어. 숫자는 거짓말 안 하거든.</span>
        </div>
    </div>
    <div class="hero-avatar-wrap">
        {hero_avatar}
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────
# Upload Flow
# ─────────────────────────────────────────────
if current_chat["df"] is None:
    agent_message(
        """
카드 이용내역 올려줘.<br>
내가 팩폭과 함께 돈 관리 도와줄게.<br><br>
그걸 꼭 지금 사야 했는지, 숫자로 같이 보자.
"""
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
    <span class="status-pill">1. 카드 내역 읽기</span>
    <span class="status-pill">2. 낭비 패턴 잡기</span>
    <span class="status-pill">3. 팩폭 준비</span>
</div>
""",
            unsafe_allow_html=True,
        )

    if uploaded is not None or demo:
        file_bytes = uploaded.getvalue() if uploaded else None

        with st.spinner("김티가 소비 내역 보는 중... 잠깐만. 변명은 나중에 듣자."):
            df = load_data(file_bytes, use_llm and has_key, model)
            summary = get_summary(df)

            current_chat["df"] = df
            current_chat["summary"] = summary
            current_chat["messages"] = []

            s = summary["spending"]
            current_chat["title"] = f"{s['시작일']} 소비 분석"

        st.rerun()


# ─────────────────────────────────────────────
# Analysis + Chat Flow
# ─────────────────────────────────────────────
else:
    summary = current_chat["summary"] or get_summary(current_chat["df"])

    agent_message(
        """
분석 완료. 팩폭 나간다.<br>
이번 소비 내역에서 제일 위험한 부분부터 봐.
"""
    )

    render_result_panel(summary)
    render_insight_cards(summary)

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
        if st.button("다음 달 예산 추천해줘"):
            st.session_state.pending_prompt = "다음 달 예산 추천해줘"
            st.rerun()

    render_charts(current_chat["df"])
    render_detail_analysis(current_chat["df"])

    if st.button("다른 파일 다시 업로드하기"):
        current_chat["df"] = None
        current_chat["summary"] = None
        current_chat["messages"] = []
        current_chat["title"] = "새 팩폭 분석"
        st.session_state.pending_prompt = None
        st.rerun()

    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

        user_message(prompt)

        if not has_key:
            answer = "ANTHROPIC_API_KEY부터 설정해. 나도 연료 없으면 팩폭 못 해."
        else:
            with st.spinner("김티가 답변 준비 중... 변명 필터링 중."):
                try:
                    answer = run_agent_question(prompt, model)
                except Exception as e:
                    answer = f"오류 났다. 이건 네 소비 말고 코드 문제야: {e}"

        current_chat["messages"].append(("user", prompt))
        current_chat["messages"].append(("assistant", answer))
        agent_message(answer)

    for role, msg in current_chat["messages"]:
        if role == "user":
            user_message(msg)
        else:
            agent_message(msg)

    prompt = st.chat_input("김티에게 무엇이든 물어봐. 단, 팩폭 감당 가능할 때.")

    if prompt:
        user_message(prompt)

        if not has_key:
            answer = "ANTHROPIC_API_KEY부터 설정해. 나도 연료 없으면 팩폭 못 해."
        else:
            with st.spinner("김티가 소비 패턴 까보는 중..."):
                try:
                    answer = run_agent_question(prompt, model)
                except Exception as e:
                    answer = f"오류 났다. 이건 네 소비 말고 코드 문제야: {e}"

        current_chat["messages"].append(("user", prompt))
        current_chat["messages"].append(("assistant", answer))
        st.rerun()
