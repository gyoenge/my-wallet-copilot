"""선호 질문 에이전트.

거래 내역만으로는 소비의 '이유'(낭비인지, 중요한 만족인지)를 알 수 없다.
탐지된 소비 패턴을 바탕으로 사용자에게 던질 맞춤 질문을 생성하고, 그 답변을
선호 텍스트로 엮어 시뮬레이션(절약 전략 평가)의 입력으로 쓴다.

질문은 (1) 그 소비를 하는 이유, (2) 유지/감축 선호, (3) 절약 목표(단기/장기)
같은 맥락을 데이터에 근거해 구체적으로 묻는다.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel, Field

from ai.debate import build_llm
from ai.debate.orchestrator import _facts_text, build_fact_sheet
from ai.simulate import _candidate_categories


class PrefQuestion(BaseModel):
    id: str = Field(description="q1, q2 ... 형식의 식별자")
    question: str = Field(description="데이터에 근거한 구체적 질문")
    options: list[str] = Field(description="객관식 보기 2~4개")


class PrefQuestionList(BaseModel):
    questions: list[PrefQuestion]


_SYS = (
    "당신은 절약 전략을 개인화하기 위한 '선호 질문 설계자'입니다. 탐지된 소비 패턴을 "
    "바탕으로 사용자에게 물을 질문 3개를 만드세요. 각 질문은 (1) 특정 소비를 하는 이유, "
    "(2) 줄여도 되는/유지하고 싶은 소비, (3) 절약 목표(단기 지출 감소 vs 장기 자산 형성) "
    "중 서로 다른 측면을 데이터에 근거해 구체적으로 묻고, 객관식 보기 2~4개를 제시하세요."
)


def generate_questions(df: pd.DataFrame, model: str | None = None) -> list[dict]:
    """소비 패턴 기반 맞춤 선호 질문을 생성한다."""
    facts = _facts_text(build_fact_sheet(df))
    cands = _candidate_categories(df)
    llm = (build_llm(model) if model else build_llm()).with_structured_output(PrefQuestionList)
    res: PrefQuestionList = llm.invoke([
        {"role": "system", "content": _SYS},
        {
            "role": "user",
            "content": (
                f"소비 근거(Fact Sheet):\n{facts}\n\n"
                f"절약 후보 카테고리: {', '.join(cands)}"
            ),
        },
    ])
    return [q.model_dump() for q in res.questions]


def compose_preferences(qa: list[dict]) -> str:
    """[{question, answer}] 답변을 시뮬레이션 입력 선호 텍스트로 엮는다."""
    return "\n".join(
        f"- {x['question']} → {x['answer']}" for x in qa if x.get("answer")
    )


if __name__ == "__main__":
    from dotenv import load_dotenv

    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    load_dotenv()
    df = categorize(load_transactions(), use_llm=False)
    for q in generate_questions(df):
        print(f"[{q['id']}] {q['question']}")
        for o in q["options"]:
            print(f"    - {o}")
