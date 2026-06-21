"""목표 추적 루프 (실행·모니터링).

분석/토론의 결론을 추적 가능한 '목표'로 구조화하고(목표화), 데이터로
달성 여부를 추적(backtest)하며, 추세로 다음 달을 예측(forecast)해
'분석→판단→실행→모니터링'의 닫힌 루프를 완성한다.

데모는 한 데이터셋 안에서 holdout으로 보인다: 마지막 달을 제외한 기간을
'목표 설정 시점'의 기준선으로, 마지막 달을 '실측'으로 본다. 새 달 데이터가
업로드되면 그대로 다음 달 추적에 쓰인다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ai.categorize import CATEGORIES


@dataclass
class Goal:
    category: str
    target_monthly: float  # 월 목표 지출 상한(원)
    rationale: str = ""
    source: str = ""  # 목표 출처(예: '토론 결론', '사용자 설정')


def _monthly_series(df: pd.DataFrame, category: str) -> pd.Series:
    """카테고리의 월별 지출 시계열(년월 오름차순)."""
    return (
        df[df["category"] == category]
        .groupby("year_month")["amount"]
        .sum()
        .sort_index()
    )


def monthly_baseline(df: pd.DataFrame, category: str, exclude_last: bool = True) -> float:
    """목표 설정 기준선 = (옵션상 마지막 달 제외) 월평균 지출."""
    s = _monthly_series(df, category)
    if exclude_last and len(s) > 1:
        s = s.iloc[:-1]
    return float(s.mean()) if len(s) else 0.0


def forecast_next(df: pd.DataFrame, category: str) -> float:
    """다음 달 지출 예측. 3개월 이상이면 선형추세, 아니면 최근값."""
    s = _monthly_series(df, category)
    if len(s) == 0:
        return 0.0
    if len(s) < 3:
        return float(s.iloc[-1])
    y = s.to_numpy(dtype=float)
    a, b = np.polyfit(np.arange(len(y)), y, 1)  # y = a*x + b
    return float(max(0.0, a * len(y) + b))


def goal_from_reduction(df: pd.DataFrame, category: str, reduction_pct: float) -> Goal:
    """현재 월평균에서 reduction_pct% 줄인 값을 목표로 잡는다(수동/데모용)."""
    base = monthly_baseline(df, category, exclude_last=False)
    return Goal(
        category=category,
        target_monthly=round(base * (1 - reduction_pct / 100)),
        rationale=f"월평균 대비 {reduction_pct:.0f}% 감축",
        source="사용자 설정",
    )


def track_goal(df: pd.DataFrame, goal: Goal) -> dict:
    """holdout 추적: 기준선(이전 달들) 대비 최근 달 실측 + 다음 달 예측."""
    s = _monthly_series(df, goal.category)
    baseline = monthly_baseline(df, goal.category, exclude_last=True)
    actual = float(s.iloc[-1]) if len(s) else 0.0
    last_month = str(s.index[-1]) if len(s) else None
    target = float(goal.target_monthly)
    forecast = forecast_next(df, goal.category)

    need = baseline - target
    done = baseline - actual
    progress = 0.0 if need <= 0 else max(0.0, min(1.0, done / need))

    return {
        "category": goal.category,
        "target_monthly": round(target),
        "baseline_monthly": round(baseline),
        "actual_last_month": round(actual),
        "last_month": last_month,
        "achieved": actual <= target,
        "gap": round(actual - target),  # +면 목표 초과(미달성)
        "progress": round(progress, 2),  # 기준선→목표 사이 달성 비율
        "forecast_next": round(forecast),
        "on_track": forecast <= target,  # 추세가 목표 안에 드는가
    }


def extract_goal(text: str, df: pd.DataFrame, model: str | None = None) -> Goal | None:
    """분석/토론 결론 텍스트에서 추적할 목표 하나를 LLM으로 구조화 추출한다.

    실패하면(키 없음/오류) None. 현재 월평균을 함께 줘 목표를 데이터에
    grounding 한다.
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        return None

    model = model or os.getenv("WALLET_COPILOT_MODEL", "claude-opus-4-8")
    baselines = {c: monthly_baseline(df, c, exclude_last=False) for c in CATEGORIES}
    base_txt = ", ".join(f"{c} 월평균 {int(v):,}원" for c, v in baselines.items() if v > 0)
    prompt = (
        "다음은 소비 분석/토론의 결론입니다. 여기서 추적할 '절약 목표' 하나를 뽑아 "
        "구조화하세요.\n"
        f"카테고리 후보: {', '.join(CATEGORIES)}\n현재 월평균: {base_txt}\n\n"
        f"결론:\n{text}\n\n"
        "category는 후보 중 하나, target_monthly는 월 목표 지출 상한(원, 현재 월평균보다 낮게)."
    )
    try:
        client = Anthropic()
        resp = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            tools=[{
                "name": "save_goal",
                "description": "추적할 절약 목표를 저장한다.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": CATEGORIES},
                        "target_monthly": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["category", "target_monthly", "rationale"],
                },
            }],
            tool_choice={"type": "tool", "name": "save_goal"},
        )
    except Exception:
        return None

    for block in resp.content:
        if block.type == "tool_use":
            d = block.input
            if d.get("category") in CATEGORIES:
                return Goal(
                    category=d["category"],
                    target_monthly=float(d["target_monthly"]),
                    rationale=str(d.get("rationale", "")),
                    source="결론에서 추출",
                )
    return None


if __name__ == "__main__":
    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    df = categorize(load_transactions(), use_llm=False)
    goal = goal_from_reduction(df, "배달", 30)
    print(f"목표: {goal.category} 월 {goal.target_monthly:,}원 이하 ({goal.rationale})\n")

    r = track_goal(df, goal)
    status = "✅ 달성" if r["achieved"] else "❌ 미달성"
    track = "🟢 순항" if r["on_track"] else "🔴 이탈 위험"
    print(f"기준선 월 {r['baseline_monthly']:,}원 → 목표 {r['target_monthly']:,}원")
    print(f"최근 달({r['last_month']}) 실측 {r['actual_last_month']:,}원  {status} "
          f"(목표 대비 {r['gap']:+,}원, 진행률 {r['progress']*100:.0f}%)")
    print(f"다음 달 예측 {r['forecast_next']:,}원  {track}")
