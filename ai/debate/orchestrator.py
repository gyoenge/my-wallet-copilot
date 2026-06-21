"""페르소나 토론 오케스트레이터 ("인사이드 아웃" 모드).

Analyst(=analysis.py)가 만든 Fact Sheet를 공통 입력으로, 세 페르소나가
순서대로 입장을 내며(뒤 페르소나는 앞 발언을 보고 반박), 마지막에 Mediator가
합의/비합의를 정리해 결론·실행안·신뢰도를 산출한다.

설계 기준: ai/debate/DESIGN.md
- 페르소나는 숫자를 지어내지 않고 모든 정량 주장에 [fact_id]를 인용한다.
- Mediator 결론은 구조적 출력(Verdict)으로 받는다.

스트리밍: run_debate()는 async generator로 ("facts"|"turn"|"verdict", payload)를
순서대로 내보낸다. FastAPI SSE가 이를 그대로 이벤트로 흘린다.
"""

from __future__ import annotations

from typing import AsyncIterator

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai import analysis as A

from . import build_llm

# 페르소나: (표시명, 이모지, 입장 지침). 항목을 추가하면 토론에 그대로 참여한다.
# (persona 키, 표시명, 입장 지침). 이모지는 프론트(PERSONA_STYLE)에서 붙인다.
PERSONAS: list[tuple[str, str, str]] = [
    (
        "hedonist", "쾌락",
        "현재의 만족과 삶의 질을 최우선한다. 절약이 일상의 기쁨을 해치는 지점을 짚고, "
        "무리한 긴축에 반대한다.",
    ),
    (
        "planner", "계획",
        "예산 배분과 실행 가능성을 본다. 어떤 카테고리를 얼마나 조정하면 현실적으로 "
        "지킬 수 있는지 구체적 시나리오로 제안한다.",
    ),
    (
        "futurist", "미래",
        "장기 순자산과 기회비용을 본다. 지금의 소비가 복리로 어떤 미래 비용이 되는지 "
        "경고하고 저축·자산 형성을 우선한다.",
    ),
]

_RULES = (
    "당신은 한 사용자의 소비를 두고 벌어지는 내면 토론의 참여자 '{name}'입니다.\n"
    "목적: {stance}\n"
    "규칙:\n"
    "- 모든 정량 주장은 반드시 Fact Sheet의 [fact_id]를 인용한다. 인용 없는 수치는 금지.\n"
    "- 숫자를 직접 계산하지 말 것. Fact Sheet에 있는 값만 쓴다.\n"
    "- 앞 사람의 발언이 있으면 한 문장으로 반박/동의한 뒤 본인 입장을 편다.\n"
    "- 전체 3~4문장 이내. 마지막에 '제안:' 한 줄로 행동을 압축한다."
)


class Verdict(BaseModel):
    """Mediator의 최종 판정."""

    consensus: str = Field(description="페르소나들이 합의한 지점 1~2문장")
    tension: str = Field(description="끝까지 엇갈린 지점 1문장")
    conclusion: str = Field(description="사용자에게 줄 핵심 결론 2~3문장")
    actions: list[str] = Field(description="구체적이고 실행 가능한 행동 2~3개")
    confidence: float = Field(description="결론의 신뢰도 0.0~1.0")


def build_fact_sheet(df: pd.DataFrame) -> dict:
    """analysis.py 집계로 fact_id가 붙은 Fact Sheet를 만든다."""
    facts: list[dict] = []
    s = A.spending_summary(df)
    facts.append({
        "id": "F01",
        "text": f"분석 {s['분석개월수']}개월, 총지출 {s['총지출']:,.0f}원, 월평균 {s['월평균']:,.0f}원",
    })
    for i, r in enumerate(A.category_breakdown(df).head(6).itertuples(), start=1):
        facts.append({
            "id": f"C{i:02d}",
            "text": f"{r.category}: {r.합계:,.0f}원 (비중 {r.비중}%, {r.건수}건)",
        })
    wk = A.weekday_spending(df)
    top_wk = wk.loc[wk["합계"].idxmax()]
    facts.append({"id": "W01", "text": f"지출 최다 요일은 {top_wk.요일}요일 ({top_wk.합계:,.0f}원)"})

    top_cat = str(A.category_breakdown(df).iloc[0]["category"])
    if top_cat in A.DISCRETIONARY:
        sv = A.savings_estimate(df, top_cat, 30)
        facts.append({
            "id": "S01",
            "text": f"{top_cat} 지출을 30% 줄이면 월 {sv['월절약액']:,.0f}원·연 {sv['연절약액']:,.0f}원 절약",
        })

    h = A.health_score(df)
    facts.append({"id": "H01", "text": f"소비 건강 점수 {h['score']}점 ({h['label']})"})

    # 자동 발굴한 소비 유형(군집)도 근거로 제공 — 페르소나가 '집콕형' 등을 인용 가능.
    from ai.cluster import cluster_merchants

    for i, c in enumerate(cluster_merchants(df)["clusters"], start=1):
        facts.append({
            "id": f"G{i:02d}",
            "text": (
                f"소비유형 '{c['label']}': 가맹점 {c['size']}곳, 지출비중 {c['지출비중']}% "
                f"(평균단가 {c['평균단가']:,}원, 예: {', '.join(c['예시가맹점'][:2])})"
            ),
        })
    return {"facts": facts}


def _facts_text(fact_sheet: dict) -> str:
    return "\n".join(f"[{f['id']}] {f['text']}" for f in fact_sheet["facts"])


async def run_debate(
    df: pd.DataFrame, question: str, model: str | None = None
) -> AsyncIterator[tuple[str, dict]]:
    """토론을 진행하며 (이벤트종류, payload)를 순서대로 내보낸다."""
    fact_sheet = build_fact_sheet(df)
    yield "facts", fact_sheet
    facts = _facts_text(fact_sheet)

    llm = build_llm(model) if model else build_llm()
    transcript: list[tuple[str, str]] = []

    for key, name, stance in PERSONAS:
        prior = (
            "\n".join(f"- {n}: {t}" for n, t in transcript)
            if transcript else "(당신이 첫 발언자입니다)"
        )
        prompt = (
            f"사용자의 질문:\n{question}\n\n"
            f"Fact Sheet:\n{facts}\n\n"
            f"지금까지의 발언:\n{prior}\n\n"
            "당신의 입장을 말하세요."
        )
        resp = await llm.ainvoke([
            SystemMessage(content=_RULES.format(name=name, stance=stance)),
            HumanMessage(content=prompt),
        ])
        text = resp.text
        transcript.append((name, text))
        yield "turn", {"persona": key, "name": name, "text": text}

    debate_log = "\n\n".join(f"{n}:\n{t}" for n, t in transcript)
    mediator = (build_llm(model) if model else build_llm()).with_structured_output(Verdict)
    verdict: Verdict = await mediator.ainvoke([
        SystemMessage(content=(
            "당신은 내면 토론의 조정자(Mediator)입니다. 페르소나들의 발언에서 합의 지점과 "
            "끝까지 엇갈린 지점을 분리하고, 사용자에게 줄 결론과 실행안을 정리하세요. "
            "[fact_id] 인용이 없는 정량 주장은 신뢰하지 마세요. 모든 숫자는 Fact Sheet 범위 안에서만 쓰세요."
        )),
        HumanMessage(content=(
            f"질문:\n{question}\n\nFact Sheet:\n{facts}\n\n토론 기록:\n{debate_log}"
        )),
    ])
    yield "verdict", verdict.model_dump()
