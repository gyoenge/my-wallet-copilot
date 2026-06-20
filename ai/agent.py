"""LangGraph 기반 소비 분석 에이전트.

Claude(claude-opus-4-8)에게 결정적 분석 함수들을 '도구'로 쥐어 주고,
자연어 질문("내가 가장 돈을 많이 쓰는 요일은?", "배달비 줄이면 얼마 절약돼?")에
실제 데이터를 근거로 답하게 한다. 숫자는 항상 도구를 통해 계산되며,
모델이 임의로 지어내지 않는다.
"""

from __future__ import annotations

import os

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from ai import analysis as A

DEFAULT_MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
당신은 'My Wallet Copilot', 사용자의 카드 소비 내역을 분석하는 한국어 금융 도우미입니다.

원칙:
- 모든 숫자(금액, 비율, 건수)는 반드시 제공된 도구를 호출해 얻으세요. 절대 추측하거나 지어내지 마세요.
- 질문에 답하는 데 필요한 도구를 먼저 호출한 뒤, 그 결과를 근거로 간결하고 친근하게 답하세요.
- 금액은 천 단위 콤마와 '원'을 붙이세요 (예: 915,073원).
- 분석 기간의 첫 달과 마지막 달은 일부 기간만 포함될 수 있으니, 월 비교 시 필요하면 이 점을 언급하세요.
- 절약 관련 질문에는 estimate_savings 도구를 활용해 구체적인 월/연 절약액을 제시하세요.
- 답변은 핵심부터 말하고, 표가 길면 상위 항목만 추려서 보여 주세요.
"""


def _won(x: float) -> str:
    return f"{x:,.0f}원"


def build_tools(df: pd.DataFrame) -> list:
    """주어진 소비 DataFrame을 클로저로 감싼 도구 목록을 만든다."""

    @tool
    def get_spending_summary() -> str:
        """전체 분석 기간의 총지출, 거래 건수, 건당 평균, 월 평균, 기간을 요약한다."""
        s = A.spending_summary(df)
        return (
            f"기간 {s['시작일']}~{s['종료일']} ({s['분석개월수']}개월) | "
            f"총지출 {_won(s['총지출'])} | 거래 {s['거래건수']}건 | "
            f"건당평균 {_won(s['건당평균'])} | 월평균 {_won(s['월평균'])}"
        )

    @tool
    def get_category_breakdown() -> str:
        """카테고리별 지출 합계, 건수, 비중(%)을 큰 순서로 보여 준다."""
        d = A.category_breakdown(df)
        rows = [
            f"{r.category}: {_won(r.합계)} ({r.비중}%, {r.건수}건)"
            for r in d.itertuples()
        ]
        return "\n".join(rows)

    @tool
    def get_monthly_trend() -> str:
        """월별 총지출과 전월 대비 증감(금액/%)을 보여 준다."""
        d = A.monthly_trend(df)
        rows = []
        for r in d.itertuples():
            delta = "" if pd.isna(r._4) else f" (전월대비 {r._4:+,.0f}원, {r._5:+.1f}%)"
            rows.append(f"{r.year_month}: {_won(r.합계)} / {r.건수}건{delta}")
        return "\n".join(rows)

    @tool
    def get_weekday_spending() -> str:
        """요일별 지출 합계, 건수, 건당 평균을 월~일 순으로 보여 준다."""
        d = A.weekday_spending(df)
        top = d.loc[d["합계"].idxmax(), "요일"]
        rows = [f"{r.요일}: {_won(r.합계)} ({r.건수}건, 건당 {_won(r.건당평균)})" for r in d.itertuples()]
        return "\n".join(rows) + f"\n→ 지출이 가장 큰 요일: {top}요일"

    @tool
    def get_time_bucket_spending() -> str:
        """시간대(아침/점심/오후/저녁/밤/심야)별 지출 합계와 건수를 보여 준다."""
        d = A.time_bucket_spending(df)
        return "\n".join(f"{r.시간대}: {_won(r.합계)} ({r.건수}건)" for r in d.itertuples())

    @tool
    def get_top_merchants(n: int = 10) -> str:
        """지출이 큰 가맹점 상위 n개를 보여 준다."""
        d = A.top_merchants(df, n)
        return "\n".join(
            f"{i}. {r.가맹점} [{r.카테고리}]: {_won(r.합계)} ({r.건수}건)"
            for i, r in enumerate(d.itertuples(), 1)
        )

    @tool
    def get_recent_month_change() -> str:
        """가장 최근 두 달을 비교해 카테고리별 지출 증감을 보여 준다. 무엇이 늘었는지 파악할 때 쓴다."""
        d = A.category_monthly_change(df)
        if d.empty:
            return "비교할 두 달치 데이터가 없습니다."
        prev_m, last_m = d.attrs.get("prev_month"), d.attrs.get("last_month")
        rows = [f"{r.category}: {r.이전달:,.0f} → {r.최근달:,.0f} ({r.증감액:+,.0f}원)" for r in d.itertuples()]
        return f"[{prev_m} → {last_m} 비교]\n" + "\n".join(rows)

    @tool
    def estimate_savings(category: str, reduction_pct: float) -> str:
        """특정 카테고리 지출을 reduction_pct% 줄였을 때의 월/연 절약액을 추정한다.

        Args:
            category: 카테고리명. 예: 배달, 카페/디저트, 편의점, 외식, 교통, 쇼핑/생활, 구독/디지털.
            reduction_pct: 줄이는 비율(%). 예: 30.
        """
        s = A.savings_estimate(df, category, reduction_pct)
        if s["현재총지출"] == 0:
            return f"'{category}' 카테고리 지출 내역이 없어 절약액을 계산할 수 없습니다."
        return (
            f"{s['카테고리']} 현재 월평균 {_won(s['현재월평균'])}. "
            f"{s['절감비율%']:.0f}% 줄이면 월 {_won(s['월절약액'])}, "
            f"연 {_won(s['연절약액'])} 절약."
        )

    return [
        get_spending_summary,
        get_category_breakdown,
        get_monthly_trend,
        get_weekday_spending,
        get_time_bucket_spending,
        get_top_merchants,
        get_recent_month_change,
        estimate_savings,
    ]


def build_agent(df: pd.DataFrame, model: str | None = None):
    """소비 분석 ReAct 에이전트를 생성한다.

    Returns:
        langgraph 그래프. `.invoke({"messages": [("user", "...")]})`로 호출.
    """
    model = model or os.getenv("WALLET_COPILOT_MODEL", DEFAULT_MODEL)
    llm = ChatAnthropic(model=model, max_tokens=2048)
    return create_react_agent(llm, build_tools(df), prompt=SYSTEM_PROMPT)


def ask(df: pd.DataFrame, question: str, model: str | None = None) -> str:
    """단발성 질문에 대한 최종 답변 텍스트를 돌려준다 (CLI/테스트용)."""
    agent = build_agent(df, model=model)
    result = agent.invoke({"messages": [("user", question)]})
    return result["messages"][-1].content


if __name__ == "__main__":
    import sys

    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    _df = categorize(load_transactions(), use_llm=False)
    q = sys.argv[1] if len(sys.argv) > 1 else "내가 가장 돈을 많이 쓰는 요일은?"
    print(f"Q: {q}\n")
    print("A:", ask(_df, q))
