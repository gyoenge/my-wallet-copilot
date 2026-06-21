"""절약 전략 시뮬레이션 ("시뮬레이션 모드").

단순히 '많이 쓰는 항목을 줄이기'가 아니라, 사용자가 실제로 실천할 수 있는
전략을 찾는다. 사용자 선호(맥락)와 거래 패턴을 결합해 절약 후보 전략을
생성하고, 각 전략을 세 관점으로 평가해 '절약 실행 효율'이 가장 높은 전략을
고른다.

절약 실행 효율 = w1·절감점수 + w2·만족 보존 + w3·실행 가능성
  - 절감점수: 후보 중 최대 절감액 대비 정규화(코드로 결정적 계산)
  - 만족 보존: 1 - 선호 훼손 정도 (페르소나 시뮬레이션, LLM)
  - 실행 가능성: 얼마나 쉽게 지킬 수 있는가 (LLM)

파이프라인(SSE async-gen):
  candidates(후보 전략) → eval(전략별 평가 N회) → recommendation(최적 전략)
"""

from __future__ import annotations

from typing import AsyncIterator

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ai import analysis as A
from ai.debate import build_llm
from ai.debate.orchestrator import _facts_text, build_fact_sheet

# 절약 실행 효율 가중치 (절감 / 만족 보존 / 실행 가능성)
W_SAVING, W_SATISFACTION, W_FEASIBILITY = 0.4, 0.3, 0.3


class Strategy(BaseModel):
    title: str = Field(description="짧은 전략 이름")
    category: str = Field(description="대상 카테고리")
    reduction_pct: float = Field(description="해당 카테고리 지출을 줄이는 비율(%) 0~100")
    description: str = Field(description="구체적 실행 방법 1~2문장 (선호를 보존하는 방식)")


class StrategyList(BaseModel):
    strategies: list[Strategy]


class Eval(BaseModel):
    satisfaction: float = Field(description="선호 보존 정도 0~1 (1=만족 훼손 없음)")
    feasibility: float = Field(description="실행 가능성 0~1 (1=지키기 매우 쉬움)")
    reason: str = Field(description="평가 근거 1문장")


def _candidate_categories(df: pd.DataFrame) -> list[str]:
    """절약 후보 카테고리 — 변동비 위주, 없으면 상위 지출."""
    cats = A.category_breakdown(df)["category"].tolist()
    disc = [c for c in cats if c in A.DISCRETIONARY]
    return (disc or cats)[:5]


def _savings(df: pd.DataFrame, s: Strategy) -> float:
    """전략의 월 절감액을 결정적으로 계산한다."""
    est = A.savings_estimate(df, s.category, s.reduction_pct)
    return float(est.get("월절약액", 0) or 0)


async def _generate(df, prefs, facts, cands, model) -> list[Strategy]:
    llm = (build_llm(model) if model else build_llm()).with_structured_output(StrategyList)
    sys = (
        "당신은 절약 전략 설계자입니다. 사용자의 선호를 보존하면서 지출을 줄이는 "
        "현실적 후보 전략 3~4개를 제안하세요. 각 전략은 후보 카테고리 중 하나를 "
        "대상으로 하고, 무리한 전면 중단보다 '유지할 건 유지하고 줄일 건 줄이는' "
        "방식을 우선하세요."
    )
    user = (
        f"소비 근거(Fact Sheet):\n{facts}\n\n"
        f"절약 후보 카테고리: {', '.join(cands)}\n\n"
        f"사용자 선호·맥락:\n{prefs or '(제공되지 않음 — 일반적 선호로 가정)'}"
    )
    res: StrategyList = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=user)])
    return res.strategies


async def _evaluate(s: Strategy, prefs: str, monthly_saving: float, model) -> Eval:
    llm = (build_llm(model) if model else build_llm()).with_structured_output(Eval)
    sys = (
        "당신은 사용자 페르소나로서 제안된 절약 전략에 어떻게 반응할지 시뮬레이션합니다. "
        "선호 보존(satisfaction)과 실행 가능성(feasibility)을 0~1로 평가하세요. "
        "사용자가 중요하게 여기는 소비를 해치면 satisfaction을 낮게, 지키기 어려우면 "
        "feasibility를 낮게 주세요."
    )
    user = (
        f"전략: {s.title}\n대상: {s.category} {s.reduction_pct:.0f}% 감축\n"
        f"방법: {s.description}\n예상 월 절감액: {monthly_saving:,.0f}원\n\n"
        f"사용자 선호·맥락:\n{prefs or '(제공되지 않음)'}"
    )
    return await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=user)])


async def _supervise(rows: list[dict], winner: int, prefs: str, model) -> str:
    """Supervisor: 절약 실행 효율 최고 전략을 사용자에게 납득시킬 근거를 쓴다."""
    llm = build_llm(model) if model else build_llm()
    table = "\n".join(
        f"{i}. {r['title']} — 절감 {r['monthly_saving']:,}원, 만족보존 {r['satisfaction']}, "
        f"실행 {r['feasibility']}, 절약실행효율 {r['efficiency']}"
        for i, r in enumerate(rows)
    )
    sys = (
        "당신은 조정자(Supervisor)입니다. 여러 절약 전략을 절감액·만족 보존·실행 "
        "가능성의 균형(절약 실행 효율)으로 비교해, 선택된 전략이 왜 가장 적합한지 "
        "대안과 견주어 2~3문장으로 설명하세요."
    )
    user = f"전략 비교:\n{table}\n\n선택된 전략: {winner}번.\n사용자 선호:\n{prefs or '(없음)'}"
    resp = await llm.ainvoke([SystemMessage(content=sys), HumanMessage(content=user)])
    return resp.text


async def run_simulation(
    df: pd.DataFrame, prefs: str = "", model: str | None = None
) -> AsyncIterator[tuple[str, dict]]:
    """전략 생성 → 평가 → 추천을 순서대로 스트리밍한다."""
    facts = _facts_text(build_fact_sheet(df))
    cands = _candidate_categories(df)

    strategies = await _generate(df, prefs, facts, cands, model)
    enriched = [(s, _savings(df, s)) for s in strategies]
    max_saving = max((m for _, m in enriched), default=0) or 1.0

    yield "candidates", {
        "strategies": [
            {**s.model_dump(), "monthly_saving": round(m)} for s, m in enriched
        ]
    }

    rows: list[dict] = []
    for i, (s, m) in enumerate(enriched):
        ev = await _evaluate(s, prefs, m, model)
        eff = (
            W_SAVING * (m / max_saving)
            + W_SATISFACTION * ev.satisfaction
            + W_FEASIBILITY * ev.feasibility
        )
        row = {
            "index": i,
            "title": s.title,
            "category": s.category,
            "monthly_saving": round(m),
            "saving_score": round(m / max_saving, 2),
            "satisfaction": round(ev.satisfaction, 2),
            "feasibility": round(ev.feasibility, 2),
            "efficiency": round(eff, 2),
            "reason": ev.reason,
        }
        rows.append(row)
        yield "eval", row

    winner = max(range(len(rows)), key=lambda i: rows[i]["efficiency"]) if rows else 0
    rationale = await _supervise(rows, winner, prefs, model) if rows else ""
    yield "recommendation", {
        "winner_index": winner,
        "title": rows[winner]["title"] if rows else "",
        "efficiency": rows[winner]["efficiency"] if rows else 0,
        "rationale": rationale,
    }
