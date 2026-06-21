"""답변 채점기 (numeric verifier).

LLM 답변 텍스트에서 수치를 추출해 코드 정답과 대조한다. LLM이 계산을
직접 하게 두지 않고, 답에 정답 값이 실제로 들어 있는지를 코드로 검증한다.
"""

from __future__ import annotations

import re

from .dataset import Question

# 1,234 / 1234.5 / -100 등 콤마 포함 숫자.
_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def extract_numbers(text: str) -> list[float]:
    out = []
    for m in _NUM.findall(text or ""):
        try:
            out.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return out


def score_answer(q: Question, answer: str, rel_tol: float = 0.01) -> dict:
    """질문 하나에 대한 채점 결과.

    Returns:
        {correct: bool, expected, found, hallucinated_numbers}.
        - amount: 정답 값이 답 안의 수치 중 하나와 rel_tol 내 일치하면 정답.
        - label: 정답 문자열이 답에 포함되면 정답.
        - hallucinated: 오답일 때 답이 '엉뚱한 수'를 단정했는지(환각 신호).
    """
    if q.kind == "label":
        correct = str(q.truth) in (answer or "")
        return {"correct": correct, "expected": q.truth, "found": None, "hallucinated": False}

    expected = float(q.truth)
    nums = extract_numbers(answer)
    tol = max(rel_tol * abs(expected), 1.0)
    hit = next((n for n in nums if abs(n - expected) <= tol), None)
    correct = hit is not None
    # 오답인데 수치를 제시했다면 = 잘못된 수를 자신있게 말함(환각).
    hallucinated = (not correct) and len(nums) > 0
    # 상대오차(MAPE 재료): 정답에 가장 가까운 수치 기준(=최소 상대오차).
    rel_err = None
    if nums and expected:
        closest = min(nums, key=lambda n: abs(n - expected))
        rel_err = abs(closest - expected) / abs(expected)
    return {
        "correct": correct,
        "expected": expected,
        "found": hit if correct else (nums[:3] or None),
        "hallucinated": hallucinated,
        "rel_err": rel_err,
    }
