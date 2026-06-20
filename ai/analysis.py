"""소비 내역에 대한 결정적(pandas) 분석 함수 모음.

여기 있는 함수들은 LLM을 쓰지 않는다. 숫자는 항상 데이터에서 직접 계산하며,
에이전트의 도구(agent.py)와 대시보드(app.py)가 공통으로 사용한다.
"""

from __future__ import annotations

import pandas as pd

WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]
TIME_ORDER = ["아침", "점심", "오후", "저녁", "밤", "심야", "기타"]


def spending_summary(df: pd.DataFrame) -> dict:
    """전체 기간의 핵심 지표를 요약한다."""
    months = df["year_month"].nunique()
    total = float(df["amount"].sum())
    return {
        "총지출": total,
        "거래건수": int(len(df)),
        "건당평균": float(df["amount"].mean()) if len(df) else 0.0,
        "월평균": total / months if months else total,
        "분석개월수": int(months),
        "시작일": df["date"].min().strftime("%Y-%m-%d"),
        "종료일": df["date"].max().strftime("%Y-%m-%d"),
    }


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """카테고리별 지출 합계/건수/비중을 큰 순서로 돌려준다."""
    g = (
        df.groupby("category")["amount"]
        .agg(합계="sum", 건수="count")
        .sort_values("합계", ascending=False)
    )
    g["비중"] = (g["합계"] / g["합계"].sum() * 100).round(1)
    return g.reset_index()


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """월별 총지출과 전월 대비 증감(금액/%)을 돌려준다.

    데이터가 월 중간에 시작/종료해 해당 월이 일부만 포함되는 경우
    'partial' 플래그를 True로 표시한다(차트에서 별도 표식용).
    """
    g = df.groupby("year_month")["amount"].agg(합계="sum", 건수="count").reset_index()
    g = g.sort_values("year_month").reset_index(drop=True)
    g["전월대비금액"] = g["합계"].diff()
    g["전월대비%"] = (g["합계"].pct_change() * 100).round(1)

    # 첫 달이 1일에 시작하지 않거나, 마지막 달이 말일에 끝나지 않으면 '부분 월'.
    start, end = df["date"].min(), df["date"].max()
    g["partial"] = False
    if not start.is_month_start:
        g.loc[g["year_month"] == start.strftime("%Y-%m"), "partial"] = True
    if not end.is_month_end:
        g.loc[g["year_month"] == end.strftime("%Y-%m"), "partial"] = True
    return g


def monthly_category_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """월 × 카테고리 지출 교차표 (행=카테고리, 열=년월)."""
    pivot = df.pivot_table(
        index="category", columns="year_month", values="amount", aggfunc="sum", fill_value=0
    )
    pivot["합계"] = pivot.sum(axis=1)
    return pivot.sort_values("합계", ascending=False).drop(columns="합계")


def weekday_spending(df: pd.DataFrame) -> pd.DataFrame:
    """요일별 지출 합계/건수/건당평균. 월~일 순서로 정렬."""
    g = df.groupby("weekday")["amount"].agg(합계="sum", 건수="count", 건당평균="mean")
    g = g.reindex(WEEKDAY_ORDER).fillna(0)
    g["건당평균"] = g["건당평균"].round(0)
    return g.reset_index().rename(columns={"weekday": "요일"})


def time_bucket_spending(df: pd.DataFrame) -> pd.DataFrame:
    """시간대별 지출 합계/건수. 아침→심야 순서."""
    g = df.groupby("time_bucket")["amount"].agg(합계="sum", 건수="count")
    order = [t for t in TIME_ORDER if t in g.index]
    return g.reindex(order).fillna(0).reset_index().rename(columns={"time_bucket": "시간대"})


def top_merchants(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """지출이 큰 가맹점 상위 n개."""
    g = (
        df.groupby(["merchant", "category"])["amount"]
        .agg(합계="sum", 건수="count")
        .sort_values("합계", ascending=False)
        .head(n)
    )
    return g.reset_index().rename(columns={"merchant": "가맹점", "category": "카테고리"})


def category_monthly_change(df: pd.DataFrame) -> pd.DataFrame:
    """가장 최근 두 달을 비교해 카테고리별 증감을 큰 순서로 돌려준다.

    '지난달 대비 무엇이 늘었나'를 설명하는 데 쓴다. 두 달 미만이면 빈 표.
    """
    months = sorted(df["year_month"].unique())
    if len(months) < 2:
        return pd.DataFrame(columns=["category", "이전달", "최근달", "증감액"])
    prev_m, last_m = months[-2], months[-1]
    prev = df[df["year_month"] == prev_m].groupby("category")["amount"].sum()
    last = df[df["year_month"] == last_m].groupby("category")["amount"].sum()
    cmp = pd.DataFrame({"이전달": prev, "최근달": last}).fillna(0)
    cmp["증감액"] = cmp["최근달"] - cmp["이전달"]
    cmp = cmp.sort_values("증감액", ascending=False).reset_index()
    cmp.attrs["prev_month"] = prev_m
    cmp.attrs["last_month"] = last_m
    return cmp


def savings_estimate(df: pd.DataFrame, category: str, reduction_pct: float) -> dict:
    """특정 카테고리 지출을 reduction_pct% 줄였을 때의 절약액을 추정한다.

    Args:
        category: 카테고리명 (예: '배달').
        reduction_pct: 줄이는 비율 (예: 30 = 30%).
    """
    months = max(df["year_month"].nunique(), 1)
    cat_total = float(df.loc[df["category"] == category, "amount"].sum())
    monthly = cat_total / months
    factor = reduction_pct / 100
    return {
        "카테고리": category,
        "절감비율%": reduction_pct,
        "현재총지출": cat_total,
        "현재월평균": monthly,
        "월절약액": monthly * factor,
        "연절약액": monthly * factor * 12,
    }


# 변동비 성격이 강해 줄이기 쉬운(=소비 점검 대상) 카테고리.
DISCRETIONARY = {"배달", "외식", "카페/디저트", "편의점", "쇼핑/생활"}


def health_score(df: pd.DataFrame) -> dict:
    """변동비 카테고리의 지출 비중으로 0~100 소비 건강 점수를 매긴다.

    숫자만 돌려준다(중립). 페르소나 문구는 프론트엔드에서 입힌다.
    """
    cat = category_breakdown(df)
    score = 100
    for r in cat.itertuples():
        if r.category in DISCRETIONARY:
            if r.비중 >= 25:
                score -= 15
            elif r.비중 >= 15:
                score -= 8
    score = max(40, min(98, int(score)))
    if score >= 85:
        label = "양호"
    elif score >= 70:
        label = "보통"
    elif score >= 55:
        label = "주의"
    else:
        label = "위험"
    return {"score": score, "label": label}


def key_insights(df: pd.DataFrame) -> list[str]:
    """대시보드 상단에 띄울 핵심 인사이트 문장들(중립 톤)."""
    cat = category_breakdown(df)
    wk = weekday_spending(df)
    chg = category_monthly_change(df)
    top_cat = cat.iloc[0]
    top_wk = wk.loc[wk["합계"].idxmax()]
    save = savings_estimate(df, str(top_cat.category), 30)

    out = [
        f"가장 많이 쓰는 카테고리는 {top_cat.category}로 전체의 {top_cat.비중}%입니다.",
        f"{top_wk.요일}요일에 가장 많이({top_wk.합계:,.0f}원) 씁니다.",
    ]
    if not chg.empty:
        drv = chg.iloc[0]
        if drv.증감액 > 0:
            out.append(f"최근 달에는 {drv.category} 지출이 전월보다 {drv.증감액:,.0f}원 늘었습니다.")
    out.append(
        f"{top_cat.category}를 30% 줄이면 월 {save['월절약액']:,.0f}원, "
        f"연 {save['연절약액']:,.0f}원 절약할 수 있어요."
    )
    return out
