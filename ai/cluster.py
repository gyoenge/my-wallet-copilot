"""소비 패턴 자동 군집화 (데이터 마이닝).

사람이 라벨링하지 않고, 시스템이 가맹점을 '행동 특성'만으로 군집화해 소비
유형을 자동 발굴한다. 카테고리는 군집의 입력이 아니라 군집을 '설명'하는
출력으로만 쓴다 — 카테고리에 의존하지 않고 행동에서 패턴을 찾기 위함.

- 특성: 빈도, 총액(log), 평균단가(log), 주말비율, 심야비율, 활동개월
- 표준화(StandardScaler) → KMeans, k는 silhouette score로 자동 선택
- 각 군집에 휴리스틱 라벨을 붙이고, 선택적으로 LLM이 사람이 읽을 라벨 부여
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

_WEEKEND = {"토", "일"}
_NIGHT = {"밤", "심야"}

# KMeans에 들어가는 행동 특성(카테고리는 제외 — 설명용으로만 사용).
FEATURES = ["빈도", "총액_log", "평균단가_log", "주말비율", "심야비율", "활동개월"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """가맹점 단위 행동 특성 행렬을 만든다."""
    g = df.groupby("merchant")
    feat = pd.DataFrame({
        "빈도": g.size(),
        "총액": g["amount"].sum(),
        "평균단가": g["amount"].mean(),
        "주말비율": g["weekday"].apply(lambda s: s.isin(_WEEKEND).mean()),
        "심야비율": g["time_bucket"].apply(lambda s: s.isin(_NIGHT).mean()),
        "활동개월": g["year_month"].nunique().astype(float),
    })
    feat["총액_log"] = np.log1p(feat["총액"])
    feat["평균단가_log"] = np.log1p(feat["평균단가"])
    return feat


def _choose_k(x: np.ndarray, kmin: int = 2, kmax: int = 8) -> tuple[int, float]:
    """silhouette score가 가장 높은 k를 고른다."""
    kmax = min(kmax, x.shape[0] - 1)
    best_k, best_s = kmin, -1.0
    for k in range(kmin, kmax + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(x)
        if len(set(labels)) < 2:
            continue
        s = silhouette_score(x, labels)
        if s > best_s:
            best_k, best_s = k, s
    return best_k, best_s


def _heuristic_label(p: dict) -> str:
    """군집 프로파일에서 사람이 읽을 라벨을 규칙으로 만든다(LLM 없이도 동작)."""
    parts = []
    if p["평균빈도"] >= 4:
        parts.append("다빈도")
    elif p["평균빈도"] <= 1.5:
        parts.append("간헐")
    if p["평균단가"] >= 50000:
        parts.append("고액")
    elif p["평균단가"] <= 10000:
        parts.append("소액")
    if p["심야비율"] >= 0.4:
        parts.append("야간")
    if p["주말비율"] >= 0.5:
        parts.append("주말")
    base = "·".join(parts) if parts else "일반"
    cat = p["주요카테고리"][0] if p["주요카테고리"] else ""
    return f"{base} {cat} 소비형".strip()


def _profiles(feat: pd.DataFrame, cat_by_merchant: pd.Series) -> list[dict]:
    """군집별 프로파일(규모·행동·주요 카테고리·예시 가맹점)을 만든다."""
    total = float(feat["총액"].sum())
    out: list[dict] = []
    for c, sub in feat.groupby("cluster"):
        merchants = list(sub.index)
        cats = cat_by_merchant.loc[merchants].value_counts()
        prof = {
            "cluster": int(c),
            "size": int(len(sub)),
            "총액": float(sub["총액"].sum()),
            "지출비중": round(float(sub["총액"].sum()) / total * 100, 1) if total else 0.0,
            "평균빈도": round(float(sub["빈도"].mean()), 1),
            "평균단가": int(sub["평균단가"].mean()),
            "주말비율": round(float(sub["주말비율"].mean()), 2),
            "심야비율": round(float(sub["심야비율"].mean()), 2),
            "주요카테고리": list(cats.head(3).index),
            "예시가맹점": list(sub.sort_values("총액", ascending=False).index[:4]),
        }
        prof["label"] = _heuristic_label(prof)
        out.append(prof)
    out.sort(key=lambda p: p["총액"], reverse=True)
    return out


def cluster_merchants(
    df: pd.DataFrame, k: int | None = None, use_llm: bool | None = None
) -> dict:
    """가맹점을 행동 특성으로 군집화해 군집 프로파일을 돌려준다.

    Args:
        df: categorize() 결과.
        k: 군집 수. None이면 silhouette로 자동 선택.
        use_llm: True면 LLM이 군집 라벨을 다시 붙인다. None이면
            환경변수 WALLET_COPILOT_LLM_CLUSTER 를 따른다.

    Returns:
        {"k", "silhouette", "clusters": [프로파일...]}.
    """
    feat = build_features(df)
    if len(feat) < 4:
        feat["cluster"] = 0
        cat = df.groupby("merchant")["category"].agg(lambda s: s.value_counts().idxmax())
        return {"k": 1, "silhouette": None, "clusters": _profiles(feat, cat)}

    x = StandardScaler().fit_transform(feat[FEATURES].to_numpy())
    sil: float | None
    if k is None:
        k, sil = _choose_k(x)
    else:
        sil = None
    feat["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(x)
    if sil is None and feat["cluster"].nunique() > 1:
        sil = float(silhouette_score(x, feat["cluster"]))

    cat = df.groupby("merchant")["category"].agg(lambda s: s.value_counts().idxmax())
    profiles = _profiles(feat, cat)

    if use_llm is None:
        use_llm = os.getenv("WALLET_COPILOT_LLM_CLUSTER", "false").lower() == "true"
    if use_llm:
        for c, label in _label_llm(profiles).items():
            for p in profiles:
                if p["cluster"] == c:
                    p["label"] = label
    return {"k": k, "silhouette": round(sil, 3) if sil is not None else None, "clusters": profiles}


def _label_llm(profiles: list[dict], model: str | None = None) -> dict[int, str]:
    """군집 프로파일을 LLM에게 주고 짧은 라벨을 받는다. 실패 시 빈 dict."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return {}

    model = model or os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")
    lines = [
        f"군집 {p['cluster']}: 빈도 {p['평균빈도']}, 평균단가 {p['평균단가']:,}원, "
        f"주말비율 {p['주말비율']}, 심야비율 {p['심야비율']}, "
        f"주요 카테고리 {p['주요카테고리']}, 예시 {p['예시가맹점']}"
        for p in profiles
    ]
    prompt = (
        "다음은 소비 행동으로 자동 군집화한 결과입니다. 각 군집에 사용자가 한눈에 이해할 "
        "짧은 라벨(예: '야간 충동 배달형', '정기 구독형', '주말 외식형')을 붙이세요.\n\n"
        + "\n".join(lines)
    )
    try:
        client = Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "save_labels",
                "description": "군집별 라벨을 저장한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "labels": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "cluster": {"type": "integer"},
                                    "label": {"type": "string"},
                                },
                                "required": ["cluster", "label"],
                            },
                        }
                    },
                    "required": ["labels"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_labels"},
        )
    except Exception:
        return {}

    for block in resp.content:
        if block.type == "tool_use":
            return {int(r["cluster"]): str(r["label"]) for r in block.input.get("labels", [])}
    return {}


if __name__ == "__main__":
    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    _df = categorize(load_transactions(), use_llm=False)
    result = cluster_merchants(_df, use_llm=False)
    print(f"군집 {result['k']}개 (silhouette={result['silhouette']})\n")
    for p in result["clusters"]:
        print(f"[{p['label']}]  가맹점 {p['size']}곳 · 지출비중 {p['지출비중']}%")
        print(
            f"   평균빈도 {p['평균빈도']} · 평균단가 {p['평균단가']:,}원 · "
            f"주말 {p['주말비율']} · 심야 {p['심야비율']}"
        )
        print(f"   주요 카테고리 {p['주요카테고리']} · 예시 {p['예시가맹점']}\n")
