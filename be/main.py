"""My Wallet Copilot — FastAPI 백엔드.

기존 core/(데이터 로드·분류·분석·LangGraph 에이전트)를 그대로 재사용해
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

from core import analysis as A
from core.categorize import categorize
from core.data_loader import load_transactions

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


def _dashboard_payload(df: pd.DataFrame) -> dict:
    """대시보드가 필요로 하는 모든 분석 결과를 한 번에 묶는다."""
    return {
        "summary": _summary(df),
        "health": A.health_score(df),
        "insights": A.key_insights(df),
        "categories": _records(A.category_breakdown(df)),
        "monthly": _records(A.monthly_trend(df)),
        "weekday": _records(A.weekday_spending(df)),
        "timeBucket": _records(A.time_bucket_spending(df)),
        "topMerchants": _records(A.top_merchants(df, 10)),
        "recentChange": _records(A.category_monthly_change(df)),
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
        from core.agent import build_agent

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
