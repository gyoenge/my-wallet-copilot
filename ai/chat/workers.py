"""전문가(worker) 에이전트들.

각 전문가는 `single.py`의 결정적 도구 중 자기 영역의 것만 쥐고,
좁은 시스템 프롬프트로 답변 품질을 높인다. 상위 supervisor는 이들을
'도구처럼' 호출한다(agents-as-tools).
"""

from __future__ import annotations

import pandas as pd
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage

from . import build_llm
from .single import build_tools

PATTERN_PROMPT = (
    "당신은 소비 '패턴 분석가'입니다. 요일·시간대·카테고리·월별 추이 분포를 "
    "도구로 산출해 사실과 숫자 위주로 답하세요. 톤은 중립적으로, 추측하지 말고 "
    "도구 결과만 근거로 삼으세요."
)

SAVING_PROMPT = (
    "당신은 '절약 코치'입니다. 특정 카테고리를 줄였을 때의 월/연 절약액(what-if)과 "
    "지출이 큰 가맹점을 도구로 계산해, 실행 가능한 절감 시나리오를 제시하세요. "
    "절약액은 반드시 estimate_savings 도구로 계산하고 지어내지 마세요."
)


def build_workers(df: pd.DataFrame) -> list:
    """df에 바인딩된 전문가 도구 목록을 만든다."""
    tools = {t.name: t for t in build_tools(df)}

    pattern_agent = create_agent(
        model=build_llm(),
        tools=[
            tools["get_weekday_spending"],
            tools["get_time_bucket_spending"],
            tools["get_category_breakdown"],
            tools["get_monthly_trend"],
        ],
        system_prompt=PATTERN_PROMPT,
    )

    @tool
    def pattern_analysis(request: str) -> str:
        """요일·시간대·카테고리·월별 추이 등 '소비 패턴'을 분석한다."""
        r = pattern_agent.invoke({"messages": [HumanMessage(content=request)]})
        return r["messages"][-1].text

    saving_agent = create_agent(
        model=build_llm(),
        tools=[
            tools["estimate_savings"],
            tools["get_top_merchants"],
            tools["get_category_breakdown"],
        ],
        system_prompt=SAVING_PROMPT,
    )

    @tool
    def saving_scenario(request: str) -> str:
        """카테고리 절감 시 월/연 절약액 등 'what-if 절약 시뮬레이션'을 수행한다."""
        r = saving_agent.invoke({"messages": [HumanMessage(content=request)]})
        return r["messages"][-1].text

    return [pattern_analysis, saving_scenario]
