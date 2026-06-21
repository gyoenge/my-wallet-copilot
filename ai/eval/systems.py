"""벤치마크 대상 시스템들.

- grounded:  결정적 도구를 쥔 ReAct 에이전트(ai.chat.single). 숫자는 도구가 계산.
- ungrounded: 같은 데이터를 텍스트(CSV)로만 받고 스스로 계산하는 LLM(도구 없음).

두 시스템의 수치 정확도 차이가 곧 '도구 grounding'의 효과다. 각 호출은
답변 텍스트와 함께 토큰 사용량을 돌려줘, 정확도-비용 트레이드오프를 본다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage

from ai.chat import build_llm
from ai.chat.single import build_agent

_UNGROUNDED_SYS = (
    "아래 카드 거래 내역(CSV)만 보고 사용자 질문에 한국어로 답하세요. "
    "계산 도구는 없습니다. 금액·비율은 정확한 숫자로 제시하세요."
)


@dataclass
class SysResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0


def _sum_tokens(messages) -> tuple[int, int]:
    """그래프 실행 결과의 모든 LLM 메시지에서 토큰을 합산한다."""
    i = o = 0
    for m in messages:
        um = getattr(m, "usage_metadata", None)
        if um:
            i += um.get("input_tokens", 0) or 0
            o += um.get("output_tokens", 0) or 0
    return i, o


def grounded(df: pd.DataFrame, question: str) -> SysResult:
    """도구 기반 ReAct 에이전트."""
    res = build_agent(df).invoke({"messages": [("user", question)]})
    msgs = res["messages"]
    i, o = _sum_tokens(msgs)
    return SysResult(msgs[-1].content, i, o)


def ungrounded(df: pd.DataFrame, question: str) -> SysResult:
    """도구 없이 CSV만 보고 스스로 계산하는 LLM(베이스라인)."""
    csv = df[["date", "amount", "category", "weekday", "time_bucket"]].to_csv(index=False)
    resp = build_llm().invoke([
        SystemMessage(content=_UNGROUNDED_SYS),
        HumanMessage(content=f"거래 내역(CSV):\n{csv}\n\n질문: {question}"),
    ])
    um = resp.usage_metadata or {}
    return SysResult(resp.text, um.get("input_tokens", 0) or 0, um.get("output_tokens", 0) or 0)


SYSTEMS = {
    "ungrounded": ungrounded,
    "grounded": grounded,
}
