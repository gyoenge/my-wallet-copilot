"""감독자(supervisor) 에이전트.

전문가들을 도구로 들고, 복합 질문을 받아 하나 이상의 전문가에게 위임한 뒤
결과를 종합한다. 라우터가 'complex'로 분류한 질문이 여기로 온다.
"""

from __future__ import annotations

import pandas as pd
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from . import build_llm
from .workers import build_workers

SUPERVISOR_PROMPT = (
    "당신은 소비 패턴 인사이트 챗봇의 감독자(Supervisor)입니다.\n"
    "사용 가능한 전문가 도구:\n"
    "- pattern_analysis: 요일·시간대·카테고리·월별 추이 등 소비 패턴 분석\n"
    "- saving_scenario: what-if 절감 시뮬레이션 / 절약 전략\n"
    "질문에 필요한 전문가를 하나 또는 여럿 호출하고, 그 결과를 종합해 "
    "친근하고 일관된 한국어로 최종 답변하세요. 숫자는 전문가가 도구로 낸 값을 "
    "그대로 인용하고 임의로 바꾸지 마세요."
)


def build_supervisor(df: pd.DataFrame, model: str | None = None):
    """복합 질문용 supervisor 그래프를 만든다."""
    return create_agent(
        model=build_llm(model) if model else build_llm(),
        tools=build_workers(df),
        system_prompt=SUPERVISOR_PROMPT,
    )


def ask_complex(df: pd.DataFrame, question: str, model: str | None = None) -> str:
    """단발성 복합 질문에 대한 최종 답변 텍스트를 돌려준다 (테스트용)."""
    sup = build_supervisor(df, model=model)
    result = sup.invoke({"messages": [HumanMessage(content=question)]})
    return result["messages"][-1].text
