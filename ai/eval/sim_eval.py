"""시뮬레이션 모드의 ground-truth 없는 정량 평가.

페르소나 기반 전략 시뮬레이션은 '정답'이 없다. 대신 셋을 측정한다:

1. 일관성 (Consistency): 페르소나의 선택이 그 동기와 모순되지 않는가.
   예: '맛집 탐색형'인데 탐색을 죽이는 전략(밀키트 구독)을 1순위로 고르면 모순.
   → 지표: 모순 응답 비율(%). 전략에 '훼손하는 동기' 태그를 달아 규칙으로 채점.

2. 분리도 (Discriminative power): 서로 다른 유형에게 같은 N개 전략을 제시했을 때
   선호 분포가 통계적으로 다른가. → JS divergence + 카이제곱 p-value.
   분리가 안 나오면 그것도 결과다.

3. 안정성 (Stability): 같은 페르소나·같은 전략을 여러 번 돌렸을 때 결론이
   흔들리지 않는가(LLM 비결정성). → 최빈 선택 일치율.

통제를 위해 전략 풀과 페르소나는 태그가 달린 고정 셋을 쓴다.
"""

from __future__ import annotations

import os

import numpy as np
from scipy.spatial.distance import jensenshannon
from scipy.stats import chi2_contingency

# 고정 전략 풀 — violates: 이 전략이 훼손하는 동기(일관성 채점용).
FIXED_STRATEGIES: list[dict] = [
    {"title": "밀키트 정기구독 전환", "desc": "배달 대신 밀키트를 정기구독해 집에서 간편 조리", "violates": {"탐색"}},
    {"title": "주말 외식으로 탐색 유지·평일 배달 감축", "desc": "평일 배달은 줄이고 주말 맛집 외식으로 새로운 맛 탐색", "violates": set()},
    {"title": "평일 직접 요리 늘리기", "desc": "평일 저녁을 직접 요리로 대체", "violates": {"편의"}},
    {"title": "편의점 간편식 대체", "desc": "평일 배달을 편의점 간편식으로 대체", "violates": {"탐색"}},
    {"title": "배달 빈도만 30% 감축(가게 유지)", "desc": "가던 가게는 유지하되 횟수만 줄임", "violates": set()},
]

# 페르소나 — motivation: 핵심 동기(일관성 채점 기준).
PERSONAS: dict[str, dict] = {
    "편의성형": {
        "motivation": "편의",
        "prefs": "배달은 시간 절약과 편의성 때문에 씁니다. 직접 요리할 시간이 없고 번거로운 건 피하고 싶어요.",
    },
    "탐색형": {
        "motivation": "탐색",
        "prefs": "배달로 새로운 맛집을 탐색하는 재미를 중요하게 여깁니다. 다양한 음식을 시도하고 싶어요.",
    },
}


def persona_scores(prefs: str, strategies: list[dict], model: str | None = None) -> np.ndarray:
    """한 페르소나가 각 전략을 선호할 정도(0~1) 벡터를 반환한다."""
    from anthropic import Anthropic

    model = model or os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")
    listing = "\n".join(f"{i}. {s['title']} — {s['desc']}" for i, s in enumerate(strategies))
    resp = Anthropic().messages.create(
        model=model,
        max_tokens=800,
        system=(
            "당신은 주어진 사용자 페르소나로서 각 절약 전략을 얼마나 선호할지 0~1로 매깁니다. "
            "사용자가 중요하게 여기는 가치를 지키는 전략을 높게 주세요."
        ),
        messages=[{
            "role": "user",
            "content": f"사용자 선호:\n{prefs}\n\n전략 목록:\n{listing}\n\n각 전략의 선호도를 저장하세요.",
        }],
        tools=[{
            "name": "save_scores",
            "description": "전략별 선호도(0~1)를 저장한다.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "scores": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "preference": {"type": "number"},
                            },
                            "required": ["index", "preference"],
                        },
                    }
                },
                "required": ["scores"],
            },
        }],
        tool_choice={"type": "tool", "name": "save_scores"},
    )
    out = np.full(len(strategies), 0.5)
    for block in resp.content:
        if block.type == "tool_use":
            for s in block.input.get("scores", []):
                i = s.get("index")
                if isinstance(i, int) and 0 <= i < len(strategies):
                    out[i] = max(0.0, min(1.0, float(s.get("preference", 0.5))))
    return out


def compute_metrics(
    runs: dict[str, list[np.ndarray]],
    strategies: list[dict] = FIXED_STRATEGIES,
    personas: dict[str, dict] = PERSONAS,
) -> dict:
    """페르소나별 선호 벡터 반복 결과에서 세 지표를 계산한다(LLM 비의존)."""
    n = len(strategies)
    stability, consistency, top_counts, mean_pref = {}, {}, {}, {}
    for key, vectors in runs.items():
        tops = [int(np.argmax(v)) for v in vectors]
        modal = max(set(tops), key=tops.count)
        stability[key] = round(tops.count(modal) / len(tops), 2)
        mot = personas[key]["motivation"]
        contra = sum(1 for t in tops if mot in strategies[t]["violates"])
        consistency[key] = {
            "모순율": round(contra / len(tops), 2),
            "최빈선택": strategies[modal]["title"],
        }
        top_counts[key] = np.bincount(tops, minlength=n)
        mean_pref[key] = np.mean(vectors, axis=0)

    discriminative: dict = {}
    keys = list(runs)
    if len(keys) == 2:
        a, b = keys
        pa = mean_pref[a] / (mean_pref[a].sum() or 1)
        pb = mean_pref[b] / (mean_pref[b].sum() or 1)
        discriminative["JS_divergence"] = round(float(jensenshannon(pa, pb) ** 2), 3)
        table = np.vstack([top_counts[a], top_counts[b]])
        table = table[:, table.sum(axis=0) > 0]
        try:
            _, p, _, _ = chi2_contingency(table)
            discriminative["chi2_p"] = round(float(p), 3)
        except ValueError:
            discriminative["chi2_p"] = None

    return {
        "repeats": len(next(iter(runs.values()))),
        "stability": stability,
        "consistency": consistency,
        "discriminative": discriminative,
        "top_pick_dist": {
            k: {strategies[i]["title"]: int(c) for i, c in enumerate(v) if c}
            for k, v in top_counts.items()
        },
    }


def run_sim_eval(repeats: int = 10, model: str | None = None) -> dict:
    """페르소나 시뮬레이션을 반복 실행해 세 지표를 측정한다(LLM 필요)."""
    runs = {
        key: [persona_scores(p["prefs"], FIXED_STRATEGIES, model) for _ in range(repeats)]
        for key, p in PERSONAS.items()
    }
    return compute_metrics(runs)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    import sys

    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    r = run_sim_eval(repeats=runs)
    print(f"=== 시뮬레이션 평가 (반복 {r['repeats']}회) ===\n")
    print("[안정성] 최빈 선택 일치율 (1.0=완전 안정)")
    for k, v in r["stability"].items():
        print(f"  {k}: {v}")
    print("\n[일관성] 동기와 모순된 선택 비율")
    for k, v in r["consistency"].items():
        print(f"  {k}: 모순율 {v['모순율']} (최빈선택: {v['최빈선택']})")
    print("\n[분리도] 유형 간 선호 분포 차이")
    print(f"  JS divergence: {r['discriminative'].get('JS_divergence')} (0=동일, 클수록 다름)")
    print(f"  카이제곱 p-value: {r['discriminative'].get('chi2_p')} (작을수록 유의미하게 다름)")
    print("\n[유형별 1순위 분포]")
    for k, dist in r["top_pick_dist"].items():
        print(f"  {k}: {dist}")
