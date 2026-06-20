"""카드 이용내역 .xls 파일을 로드하고 정제한다.

원본 파일(`data/카드이용내역.xls`)은 상단 3행이 안내/조회기간/공백이고,
4번째 행(0-index 3)이 헤더이며, 하단에는 '정상승인건수/합계' 같은 합계 행이 붙어 있다.
이 모듈은 그 잡음을 제거하고 분석에 바로 쓸 수 있는 깔끔한 DataFrame을 돌려준다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# 원본 .xls 안의 헤더는 줄바꿈이 섞여 있어( '포인트\n사용' 등) 정규화한다.
HEADER_ROW = 3

# 분석에 사용할 한글 컬럼명 → 표준 컬럼명 매핑.
COLUMN_RENAME = {
    "이용일": "date",
    "이용시간": "time",
    "이용카드": "card",
    "승인번호": "approval_no",
    "가맹점명": "merchant",
    "승인금액": "amount",
    "포인트사용": "points_used",
    "이용구분": "pay_type",
    "할부기간": "installment",
    "매입": "captured",
    "매입금액": "captured_amount",
    "매입할인금액": "captured_discount",
    "매입취소금액": "captured_cancel",
    "상태": "status",
}

WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "카드이용내역.xls"


def _time_bucket(hour: int) -> str:
    """이용 시간(시)을 사람이 읽기 좋은 시간대 구간으로 변환한다."""
    if 5 <= hour < 11:
        return "아침"
    if 11 <= hour < 14:
        return "점심"
    if 14 <= hour < 17:
        return "오후"
    if 17 <= hour < 21:
        return "저녁"
    if 21 <= hour < 24:
        return "밤"
    return "심야"


def load_transactions(path: str | Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """카드 이용내역을 정제된 DataFrame으로 로드한다.

    Returns:
        컬럼: date(datetime), time, card, approval_no, merchant, amount(float),
        points_used, pay_type, installment, captured, status,
        그리고 파생 컬럼 year_month, weekday, hour, time_bucket.
        '정상' 상태의 거래만 포함하며 합계/공백 행은 제거된다.
    """
    raw = pd.read_excel(path, header=HEADER_ROW)
    raw.columns = [str(c).replace("\n", "") for c in raw.columns]
    df = raw.rename(columns=COLUMN_RENAME)

    # 날짜로 파싱되지 않는 행(합계/공백/'이하 여백')을 제거한다.
    df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d", errors="coerce")
    df = df.dropna(subset=["date"]).copy()

    # 취소/매출취소를 제외하고 실제 지출만 남긴다.
    df = df[df["status"] == "정상"].copy()

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df[df["amount"] > 0].copy()

    df["merchant"] = df["merchant"].astype(str).str.strip()

    # 파생 컬럼.
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["weekday"] = df["date"].dt.weekday.map(lambda i: WEEKDAY_KO[i])
    df["hour"] = (
        pd.to_datetime(df["time"], format="%H:%M:%S", errors="coerce").dt.hour.fillna(-1).astype(int)
    )
    df["time_bucket"] = df["hour"].map(lambda h: _time_bucket(h) if h >= 0 else "기타")

    df = df.sort_values("date").reset_index(drop=True)
    return df


if __name__ == "__main__":
    _df = load_transactions()
    print(f"거래 {len(_df)}건, 기간 {_df['date'].min().date()} ~ {_df['date'].max().date()}")
    print(f"총 지출 {_df['amount'].sum():,.0f}원")
    print(_df.head().to_string())
