"""My Wallet Copilot — FastAPI 백엔드.

기존 ai/(데이터 로드·분류·분석·LangGraph 에이전트)를 그대로 재사용해
프론트엔드(Next.js)에 REST + SSE API로 노출한다.

실행:  uvicorn be.main:app --reload --port 8000
"""

from __future__ import annotations

import io
import json
import os
import uuid
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ai import analysis as A
from ai.categorize import categorize
from ai.data_loader import load_transactions

load_dotenv()

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "카드이용내역.xls"

app = FastAPI(title="My Wallet Copilot API")

# 개발 편의를 위해 모든 오리진 허용. 프로덕션에서는 프론트 도메인만 허용할 것.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# session_id -> {"df": DataFrame, "agent": graph | None}
# 데모용 인메모리 저장소. 프로덕션은 Redis 등 외부 저장소로 교체.
SESSIONS: dict[str, dict] = {}


# ── 직렬화 헬퍼 ──────────────────────────────────────────────────────────────
def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame을 JSON 직렬화 가능한 dict 리스트로 변환한다."""
    return json.loads(df.to_json(orient="records", force_ascii=False))


def _summary(df: pd.DataFrame) -> dict:
    return A.spending_summary(df)


def _dynamic_cards(df: pd.DataFrame) -> list[dict]:
    """입력 데이터에 따라 가변적으로 노출할 분석 카드 목록을 만든다.

    고정 섹션(진단/월평균/카테고리/월별추이)을 제외한 나머지 분석을
    데이터 상황에 맞춰 카드로 추가한다. 프론트엔드는 이 배열을 순회해 렌더한다.
    """
    cards: list[dict] = []

    # 요일별 지출 (막대)
    wk = A.weekday_spending(df)
    cards.append({
        "kind": "bars",
        "title": "요일별 지출",
        "gradient": ["#b9a7ff", "#9275f0"],
        "bars": [{"label": str(r.요일), "value": float(r.합계)} for r in wk.itertuples()],
    })

    # 시간대별 지출 (막대)
    tb = A.time_bucket_spending(df)
    cards.append({
        "kind": "bars",
        "title": "시간대별 지출",
        "gradient": ["#5ee9b5", "#2bb98a"],
        "bars": [{"label": str(r.시간대), "value": float(r.합계)} for r in tb.itertuples()],
    })

    # 최근 달 카테고리 증감 (두 달 이상일 때만)
    chg = A.category_monthly_change(df)
    if not chg.empty:
        prev_m, last_m = chg.attrs.get("prev_month"), chg.attrs.get("last_month")
        items = [
            {
                "name": str(r.category),
                "sub": f"{prev_m} → {last_m}",
                "value": f"{'+' if r.증감액 >= 0 else ''}{r.증감액:,.0f}원",
            }
            for r in chg.head(6).itertuples()
        ]
        cards.append({"kind": "list", "title": "최근 달 카테고리 증감", "items": items})

    # 지출 상위 가맹점 (있을 때만)
    top = A.top_merchants(df, 7)
    if len(top):
        items = [
            {
                "name": str(r.가맹점),
                "sub": f"{r.카테고리} · {r.건수}건",
                "value": f"{r.합계:,.0f}원",
            }
            for r in top.itertuples()
        ]
        cards.append({"kind": "list", "title": "지출 상위 가맹점", "items": items})

    # 절약 포인트 (최다 지출이 변동비 카테고리일 때만)
    cat = A.category_breakdown(df)
    top_cat = str(cat.iloc[0]["category"])
    if top_cat in A.DISCRETIONARY:
        s = A.savings_estimate(df, top_cat, 30)
        cards.append({
            "kind": "savings",
            "title": "절약 포인트",
            "text": (
                f"{top_cat}를 30% 줄이면 월 {s['월절약액']:,.0f}원, "
                f"연 {s['연절약액']:,.0f}원 절약할 수 있어요."
            ),
        })

    return cards


def _dashboard_payload(df: pd.DataFrame) -> dict:
    """대시보드가 필요로 하는 분석 결과를 묶는다.

    고정 섹션 + 데이터에 따라 가변적으로 추가되는 cards 배열을 함께 내려준다.
    """
    return {
        "summary": _summary(df),
        "health": A.health_score(df),
        "insights": A.key_insights(df),
        "categories": _records(A.category_breakdown(df)),
        "monthly": _records(A.monthly_trend(df)),
        "cards": _dynamic_cards(df),
    }


def _load_session(file_bytes: bytes | None) -> str:
    """파일(또는 기본 샘플)을 로드·분류하고 새 세션을 만든다."""
    source = io.BytesIO(file_bytes) if file_bytes else DEFAULT_DATA
    df = categorize(
        load_transactions(source),
        use_llm=os.getenv("WALLET_COPILOT_LLM_CATEGORIZE", "false").lower() == "true",
    )
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"df": df, "agent": None}
    return session_id


def _get_session(session_id: str) -> dict:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다. 먼저 업로드하세요.")
    return session


def _chunk_text(content) -> str:
    """AIMessageChunk.content(문자열 또는 콘텐츠 블록 리스트)에서 텍스트만 뽑는다."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts)


# ── 라우트 ──────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "has_api_key": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/upload")
async def upload(file: UploadFile | None = File(default=None)) -> dict:
    """카드 이용내역 업로드(또는 미업로드 시 샘플)로 세션을 생성한다."""
    file_bytes = await file.read() if file is not None else None
    try:
        session_id = _load_session(file_bytes)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"파일을 분석할 수 없습니다: {e}") from e
    df = SESSIONS[session_id]["df"]
    return {"session_id": session_id, "summary": _summary(df)}


@app.get("/api/dashboard/{session_id}")
async def dashboard(session_id: str) -> dict:
    df = _get_session(session_id)["df"]
    return _dashboard_payload(df)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """에이전트 응답을 SSE 토큰 스트림으로 흘린다."""
    session = _get_session(req.session_id)

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY가 설정되지 않았습니다.")

    if session["agent"] is None:
        from ai.agent import build_agent

        session["agent"] = build_agent(session["df"])
    agent = session["agent"]

    async def event_generator():
        try:
            async for chunk, meta in agent.astream(
                {"messages": [("user", req.message)]}, stream_mode="messages"
            ):
                # 최종 답변 노드의 토큰만 전송한다(도구 호출 노드는 건너뜀).
                if meta.get("langgraph_node") != "agent":
                    continue
                text = _chunk_text(getattr(chunk, "content", ""))
                if text:
                    yield {"event": "token", "data": text}
        except Exception as e:  # noqa: BLE001
            yield {"event": "error", "data": str(e)}
        finally:
            yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())
