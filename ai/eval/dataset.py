"""벤치마크 질문셋 + 정답 오라클.

정답은 plain pandas로 직접 계산한다(분석 시스템이 쓰는 analysis.py와
독립). 이렇게 해야 '시스템이 도구를 옳게 골라 정확한 수를 보고하는가'를
독립적으로 채점할 수 있다 — 환각·오답을 잡아내는 것이 목적.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Question:
    id: str
    text: str
    kind: str  # "amount" | "label"
    truth: float | str
    note: str = ""


def build_benchmark(df: pd.DataFrame) -> list[Question]:
    """주어진 거래 df에서 정답이 코드로 검증되는 질문들을 만든다."""
    qs: list[Question] = []

    total = float(df["amount"].sum())
    qs.append(Question("total", "내 총 지출은 얼마야?", "amount", total))

    avg = float(df["amount"].mean())
    qs.append(Question("avg_txn", "거래 건당 평균 지출은 얼마야?", "amount", avg))

    by_cat = df.groupby("category")["amount"].sum()
    top_cat = str(by_cat.idxmax())
    qs.append(Question("top_category", "내가 가장 많이 쓴 카테고리는 뭐야?", "label", top_cat))

    by_wd = df.groupby("weekday")["amount"].sum()
    top_wd = str(by_wd.idxmax())
    qs.append(Question("top_weekday", "무슨 요일에 가장 많이 써?", "label", top_wd))

    # 카테고리 의존 질문 — 해당 카테고리가 있을 때만 추가
    n_months = max(int(df["year_month"].nunique()), 1)
    if "배달" in by_cat.index:
        delivery_total = float(by_cat["배달"])
        qs.append(Question("delivery_total", "배달에 총 얼마 썼어?", "amount", delivery_total))
        # 월평균 배달비의 30% — savings_estimate와 동일 정의를 코드로 직접 계산
        saving = delivery_total / n_months * 0.30
        qs.append(Question(
            "delivery_saving",
            "배달비를 30% 줄이면 한 달에 얼마 아낄 수 있어?",
            "amount", saving,
            note="월평균 배달비 × 30%",
        ))

    return qs
