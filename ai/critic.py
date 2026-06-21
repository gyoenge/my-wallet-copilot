"""소비 항목 분류 검증가(critic).

분류기(categorize.py)가 매긴 카테고리를 '검증가'가 다시 검토해, 신뢰도가
낮은 항목을 '불확실' 태그와 근거(reason)와 함께 표시한다. 검토 화면은 이
결과를 신뢰도 오름차순으로 정렬해, 사용자가 의심스러운 항목부터 우선
검수하도록 한다.

분류기(무엇으로 분류할지)와 검증가(그 분류를 믿어도 되는지)를 분리해,
- 규칙으로 직접 매칭된 항목은 결정적·고신뢰로 통과시키고,
- 규칙이 못 잡아 LLM이 추정했거나 '기타'로 남은 항목만 의심 대상으로
  끌어올린다. 선택적으로 LLM 검증가가 근거 있는 신뢰도를 다시 매긴다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd

from ai.categorize import CATEGORIES, match_all_rules

# 이 값 미만이면 '불확실' 배지를 단다.
UNCERTAIN_THRESHOLD = 0.6


@dataclass
class Review:
    """가맹점 한 건에 대한 검증 결과."""

    merchant: str
    category: str            # 분류기가 매긴 카테고리
    confidence: float        # 0.0~1.0, 그 분류를 믿을 수 있는 정도
    reason: str              # 신뢰도 판단 근거
    suggested: str | None = None  # 검증가가 더 맞다고 본 대안 카테고리

    @property
    def uncertain(self) -> bool:
        return self.confidence < UNCERTAIN_THRESHOLD


def _heuristic_review(merchant: str, category: str) -> Review:
    """LLM 없이 분류 '근거'만으로 신뢰도를 매기는 결정적 검증가."""
    hits = match_all_rules(merchant)
    rule_cat, kw = (hits[0] if hits else ("기타", None))
    distinct_cats = {c for c, _ in hits}

    if kw is not None and rule_cat == category:
        # 서로 다른 카테고리 규칙이 동시에 걸리면 모호 → 불확실로 끌어올린다.
        if len(distinct_cats) > 1:
            competitors = " vs ".join(sorted(distinct_cats))
            return Review(
                merchant, category, 0.55,
                f"여러 카테고리 규칙이 동시 매칭({competitors}) — '{category}'로 우선 분류됨",
            )
        return Review(merchant, category, 0.9, f"'{kw}' 규칙 키워드로 직접 매칭")
    if kw is not None and rule_cat != category:
        return Review(
            merchant, category, 0.4,
            f"규칙은 '{rule_cat}'('{kw}')로 보는데 '{category}'로 분류됨 — 충돌",
        )
    if category != "기타":
        return Review(
            merchant, category, 0.5,
            "규칙 미매칭 → LLM 추정 분류 (결정적 근거 없음)",
        )
    return Review(merchant, category, 0.2, "규칙·LLM 모두 분류 실패 ('기타')")


def critique(
    df: pd.DataFrame,
    use_llm: bool | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """분류된 거래 DataFrame을 가맹점 단위로 검증한 표를 돌려준다.

    Args:
        df: categorize() 결과 ('category' 컬럼 포함).
        use_llm: True면 규칙으로 확정되지 않은 항목을 LLM 검증가가 재평가.
            None이면 환경변수 WALLET_COPILOT_LLM_CRITIC을 따른다.
        model: Claude 모델 ID. None이면 WALLET_COPILOT_MODEL.

    Returns:
        컬럼: merchant, category, suggested, confidence, uncertain,
        reason, count(거래건수), total_amount(총지출). 신뢰도 오름차순,
        같으면 지출 큰 순으로 정렬 — 검토 우선순위 그대로.
    """
    agg = (
        df.groupby("merchant")["amount"]
        .agg(count="count", total_amount="sum")
        .reset_index()
    )
    # 가맹점별 대표 카테고리(분류기 결과는 가맹점당 동일하다고 가정).
    cat_by_merchant = df.groupby("merchant")["category"].first()

    reviews: dict[str, Review] = {
        m: _heuristic_review(m, cat_by_merchant[m]) for m in cat_by_merchant.index
    }

    if use_llm is None:
        use_llm = os.getenv("WALLET_COPILOT_LLM_CRITIC", "false").lower() == "true"

    if use_llm:
        # 규칙으로 확정(0.9)되지 않은 항목만 LLM 검증가에게 보낸다.
        pending = [(m, r.category) for m, r in reviews.items() if r.confidence < 0.9]
        if pending:
            for m, (conf, suggested, reason) in _llm_critique(pending, model=model).items():
                cat = reviews[m].category
                reviews[m] = Review(
                    merchant=m,
                    category=cat,
                    confidence=conf,
                    reason=reason,
                    suggested=suggested if suggested and suggested != cat else None,
                )

    rows = [
        {
            "merchant": r.merchant,
            "category": r.category,
            "suggested": r.suggested,
            "confidence": round(r.confidence, 2),
            "uncertain": r.uncertain,
            "reason": r.reason,
        }
        for r in reviews.values()
    ]
    out = agg.merge(pd.DataFrame(rows), on="merchant")
    return out.sort_values(
        ["confidence", "total_amount"], ascending=[True, False]
    ).reset_index(drop=True)


def review_queue(reviews: pd.DataFrame) -> pd.DataFrame:
    """검증 표에서 '불확실' 항목만 추려, 검수 큐로 돌려준다."""
    return reviews[reviews["uncertain"]].reset_index(drop=True)


def _llm_critique(
    items: list[tuple[str, str]],
    model: str | None = None,
) -> dict[str, tuple[float, str | None, str]]:
    """(가맹점, 제안 카테고리) 목록을 LLM 검증가에게 한 번에 재평가시킨다.

    실패하면(키 없음/오류) 빈 dict를 돌려줘 휴리스틱 결과를 유지한다.

    Returns:
        {가맹점: (confidence, suggested_category, reason)}.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return {}

    model = model or os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")
    listing = "\n".join(f"- {m} → 제안: {c}" for m, c in items)
    prompt = (
        "당신은 카드 소비 카테고리 분류 '검증가'입니다. 분류기가 가맹점마다 매긴 "
        "제안 카테고리가 타당한지 검토하세요.\n"
        f"가능한 카테고리: {', '.join(CATEGORIES)}\n\n"
        "각 항목에 대해 (1) 제안이 옳을 확률 confidence(0~1), (2) 더 맞는 카테고리 "
        "suggested, (3) 한 줄 근거 reason 을 매기세요. 가맹점명만으로 판단이 어려우면 "
        "confidence를 낮게 주세요.\n\n"
        f"{listing}"
    )

    try:
        client = Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "save_reviews",
                "description": "가맹점별 분류 검증 결과를 저장한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "reviews": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "merchant": {"type": "string"},
                                    "confidence": {"type": "number"},
                                    "suggested": {"type": "string", "enum": CATEGORIES},
                                    "reason": {"type": "string"},
                                },
                                "required": ["merchant", "confidence", "suggested", "reason"],
                            },
                        }
                    },
                    "required": ["reviews"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_reviews"},
        )
    except Exception:
        return {}

    valid = {m for m, _ in items}
    for block in resp.content:
        if block.type == "tool_use":
            result: dict[str, tuple[float, str | None, str]] = {}
            for r in block.input.get("reviews", []):
                m = r.get("merchant")
                if m not in valid:
                    continue
                conf = max(0.0, min(1.0, float(r.get("confidence", 0.0))))
                suggested = r.get("suggested")
                if suggested not in CATEGORIES:
                    suggested = None
                result[m] = (conf, suggested, str(r.get("reason", "")))
            return result
    return {}


if __name__ == "__main__":
    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    _df = categorize(load_transactions(), use_llm=False)
    reviews = critique(_df, use_llm=False)
    queue = review_queue(reviews)

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 120)
    print(f"검수 필요(불확실) {len(queue)}건 / 전체 가맹점 {len(reviews)}곳\n")
    print(queue.to_string(index=False))
