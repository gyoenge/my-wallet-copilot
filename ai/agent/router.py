"""질문 라우터 (옵션 2).

값싼 모델(haiku)로 질문을 simple/complex 로 1회 분류한 뒤,
- simple  → 단일 ReAct 에이전트(single.build_agent): 빠르고 저렴
- complex → supervisor: 여러 전문가를 종합

단순 질문에 supervisor의 중첩 LLM 호출 오버헤드를 물리지 않는 것이 목적이다.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from . import build_llm
from .single import build_agent
from .supervisor import build_supervisor

# 분류 같은 단순 작업에는 값싼 모델이 적합하다.
# (메인 에이전트는 build_llm 기본값(opus)을 그대로 쓴다 — 라우터만 별도)
ROUTER_MODEL = "claude-haiku-4-5"

ROUTER_PROMPT = (
    "너는 소비 분석 챗봇의 라우터다. 사용자 질문을 두 경로 중 하나로 '분류만' 한다. "
    "답변하지 마라.\n"
    "- simple: 하나의 지표/사실로 답할 수 있는 질문. "
    "예: '가장 많이 쓴 요일은?', '배달비 총액은?', '지난달 대비 뭐가 늘었어?'\n"
    "- complex: 둘 이상의 관점을 종합·비교하거나 전략·시나리오가 필요한 질문. "
    "예: '내 소비 진단하고 절약안까지 알려줘', '패턴 보고 다음달 예산 짜줘'"
)


class Route(BaseModel):
    """질문을 처리 경로로 분류한 결과."""

    mode: Literal["simple", "complex"] = Field(
        description=(
            "단일 지표/도구로 답할 수 있으면 simple, "
            "여러 관점(패턴+절약 등)의 종합·전략이 필요하면 complex."
        )
    )


def classify(question: str) -> str:
    """질문을 'simple' | 'complex' 로 분류한다."""
    llm = build_llm(ROUTER_MODEL).with_structured_output(Route)
    decision = llm.invoke(
        [("system", ROUTER_PROMPT), ("human", question)]
    )
    return decision.mode


def ask(
    df: pd.DataFrame, question: str, model: str | None = None
) -> tuple[str, str]:
    """질문을 라우팅해 처리한다.

    Returns:
        (선택된 경로, 최종 답변 텍스트) 튜플.
    """
    mode = classify(question)
    if mode == "simple":
        agent = build_agent(df, model=model)
        result = agent.invoke({"messages": [("user", question)]})
        return mode, result["messages"][-1].content

    sup = build_supervisor(df, model=model)
    result = sup.invoke({"messages": [HumanMessage(content=question)]})
    return mode, result["messages"][-1].text


if __name__ == "__main__":
    import sys

    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    _df = categorize(load_transactions(), use_llm=False)
    q = sys.argv[1] if len(sys.argv) > 1 else "내 소비 패턴 진단하고 절약안까지 알려줘"
    route, answer = ask(_df, q)
    print(f"Q: {q}")
    print(f"[route={route}]")
    print("A:", answer)
