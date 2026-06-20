"""가맹점명을 소비 카테고리로 분류한다.

1차로 한국 가맹점 키워드 규칙으로 분류하고(빠르고 비용 0, 결정적),
규칙으로 잡히지 않는 가맹점만 선택적으로 Claude에게 물어본다.
"""

from __future__ import annotations

import json
import os

import pandas as pd

# 사용하는 카테고리 집합. 분류기는 이 중 하나를 반드시 돌려준다.
CATEGORIES = [
    "배달",
    "카페/디저트",
    "편의점",
    "외식",
    "마트",
    "교통",
    "쇼핑/생활",
    "구독/디지털",
    "의료",
    "여가",
    "기타",
]

# (카테고리, 키워드들) — 위에서부터 먼저 매칭되는 규칙이 이긴다.
# 키워드는 소문자로 비교하므로 영문 해외 결제도 함께 잡는다.
_RULES: list[tuple[str, list[str]]] = [
    # 해외/디지털 구독은 가장 먼저 잡아 다른 규칙과 겹치지 않게 한다.
    ("구독/디지털", [
        "anthropic", "claude.ai", "openai", "google", "colab", "aws",
        "amazon", "apple_kcp", "dropbox", "runway", "luma", "pika",
        "capcut", "overleaf", "higgsfield", "github", "netflix", "spotify",
    ]),
    ("배달", ["우아한형제들", "배민", "쿠팡이츠", "요기요"]),
    ("편의점", [
        "지에스25", "gs25", "지에스리테일", "씨유", "cu)", "(cu", "비지에프리테일",
        "세븐일레븐", "코리아세븐", "이마트24", "미래밴딩", "메세코리아",
        "터미널매점", "자판기", "vending",
    ]),
    ("카페/디저트", [
        "카페", "커피", "하이오", "할리스", "이디야", "컴포즈", "메가엠지씨", "메가",
        "스타벅스", "투썸", "공차", "베리티", "핀바", "뚜레쥬르", "파리바게뜨",
        "파리바게트", "설빙", "호떡", "킹스크로스", "디저트", "베이커리", "coffee",
    ]),
    ("마트", ["롯데쇼핑", "롯데슈퍼", "롯데마트", "홈플러스", "이마트(", "농협하나로"]),
    ("교통", [
        "고속버스", "택시", "카카오t", "카카오_택시", "이동의즐거움", "코레일",
        "ktx", "srt", "지하철", "버스운송",
    ]),
    ("의료", ["약국", "의학과", "병원", "메디컬", "정신건강", "치과", "의원", "한의원"]),
    ("여가", ["레드버튼", "노래", "ott", "오티티관", "cgv", "메가박스", "롯데시네마", "pc방"]),
    ("쇼핑/생활", [
        "쿠팡", "템스토어", "프레젠띵", "아르떼제이", "artej", "오렌즈", "올리브영",
        "아쿠아워시", "유쎈아이디", "다이소", "무신사", "지마켓", "11번가",
    ]),
    ("외식", [
        "kfc", "케이에프씨", "롯데리아", "샤오마라", "김모찌", "산카쿠", "삼시세끼",
        "육수당", "코시", "담소", "순대", "해장국", "은희네", "빅웨이브",
        "방앗간컴퍼니", "오차오차", "산삼골", "휴게소", "식당", "맘스터치", "버거",
    ]),
]


def categorize_merchant(merchant: str) -> str:
    """단일 가맹점명을 규칙으로 분류한다. 매칭 실패 시 '기타'."""
    name = str(merchant).lower()
    for category, keywords in _RULES:
        if any(kw in name for kw in keywords):
            return category
    return "기타"


def categorize(
    df: pd.DataFrame,
    use_llm: bool | None = None,
    model: str | None = None,
) -> pd.DataFrame:
    """DataFrame에 'category' 컬럼을 추가해 돌려준다.

    Args:
        df: data_loader.load_transactions() 결과.
        use_llm: True면 규칙으로 '기타'가 된 가맹점을 Claude로 재분류.
            None이면 환경변수 WALLET_COPILOT_LLM_CATEGORIZE를 따른다.
        model: Claude 모델 ID. None이면 WALLET_COPILOT_MODEL(기본 claude-opus-4-8).
    """
    out = df.copy()
    out["category"] = out["merchant"].map(categorize_merchant)

    if use_llm is None:
        use_llm = os.getenv("WALLET_COPILOT_LLM_CATEGORIZE", "false").lower() == "true"

    if use_llm:
        unknown = sorted(out.loc[out["category"] == "기타", "merchant"].unique())
        if unknown:
            mapping = _llm_categorize(unknown, model=model)
            for merchant, category in mapping.items():
                out.loc[out["merchant"] == merchant, "category"] = category

    return out


def _llm_categorize(merchants: list[str], model: str | None = None) -> dict[str, str]:
    """규칙으로 못 잡은 가맹점들을 Claude에게 한 번에 분류시킨다.

    실패하면(키 없음/오류) 빈 dict를 돌려줘 규칙 결과('기타')를 유지한다.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return {}

    model = model or os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")
    categories = ", ".join(c for c in CATEGORIES if c != "기타")

    prompt = (
        "다음은 카드 가맹점명 목록입니다. 각 가맹점을 아래 카테고리 중 하나로 분류하세요.\n"
        f"카테고리: {categories}, 기타\n\n"
        "가맹점 목록:\n" + "\n".join(f"- {m}" for m in merchants) + "\n\n"
        '결과는 {"가맹점명": "카테고리"} 형태의 JSON 객체로만 답하세요.'
    )

    try:
        client = Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "save_categories",
                "description": "가맹점별 카테고리 분류 결과를 저장한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "mapping": {
                            "type": "object",
                            "description": "가맹점명 -> 카테고리",
                            "additionalProperties": {"type": "string", "enum": CATEGORIES},
                        }
                    },
                    "required": ["mapping"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_categories"},
        )
    except Exception:
        return {}

    for block in resp.content:
        if block.type == "tool_use":
            mapping = block.input.get("mapping", {})
            # 알 수 없는 카테고리는 버린다.
            return {m: c for m, c in mapping.items() if c in CATEGORIES}
    return {}


if __name__ == "__main__":
    from src.data_loader import load_transactions

    _df = categorize(load_transactions(), use_llm=False)
    summary = (
        _df.groupby("category")["amount"].agg(["sum", "count"]).sort_values("sum", ascending=False)
    )
    print(summary.to_string())
    leftover = _df.loc[_df["category"] == "기타", "merchant"].unique()
    if len(leftover):
        print("\n규칙 미매칭(기타):", list(leftover))
