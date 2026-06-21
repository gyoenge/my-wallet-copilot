# 💰 My Wallet Copilot

카드·계좌 소비 내역을 분석해 소비 패턴을 발견하고, 절약 포인트를 제안하며,
자연어 질문에 데이터 기반으로 답하는 AI Agent.

> "가장 돈을 많이 쓰는 요일은 토요일로, 총 824,736원을 지출하셨어요."
> "배달을 30% 줄이면 월 68,630원, 연 823,566원을 아낄 수 있어요."

## 아키텍처

```
[ Next.js (React) + Tailwind ]   fe/     ← 아바타·대시보드·차트·SSE 채팅 UI
            │  REST + SSE
[ FastAPI ]                      be/     ← 얇은 API 레이어
            │
[ Python 분석/에이전트 ]          core/   ← 데이터 로드·분류·분석·LangGraph 에이전트
```

- **백엔드**: FastAPI — `core/`를 그대로 재사용. `/upload`, `/dashboard`, `/chat`(SSE 스트리밍).
- **프론트**: Next.js(App Router) + TypeScript + Tailwind + Recharts.
- **에이전트**: LangGraph ReAct + Claude(`claude-opus-4-8`), `langchain-anthropic` 경유.
- **핵심 설계**: 모든 숫자는 `core/analysis.py`에서 계산되어 에이전트에 **도구**로 제공 → Claude가 금액을 지어내지 않음.

## 구조

```
be/main.py           FastAPI (/upload, /dashboard/{id}, /chat SSE)
core/
  data_loader.py     .xls 로드/정제
  categorize.py      가맹점 → 카테고리 (규칙 + Claude 폴백)
  analysis.py        결정적 분석 (카테고리/월/요일/시간대/MoM/절약/건강점수)
  agent.py           LangGraph 에이전트 + 분석 도구
fe/
  app/page.tsx       메인 화면 (페르소나 요약 + 대시보드 + 채팅)
  components/        Avatar, Dashboard(차트), Chat(SSE)
  lib/api.ts         FastAPI 클라이언트 + SSE 파서
data/카드이용내역.xls  샘플 데이터
```

## 실행

### 1) 백엔드 (FastAPI)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ANTHROPIC_API_KEY 입력
uvicorn be.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2) 프론트엔드 (Next.js)

```bash
cd fe
npm install
# 기본 API 주소는 http://127.0.0.1:8000. 바꾸려면:
cp .env.local.example .env.local
npm run dev                   # http://localhost:3000
```

`ANTHROPIC_API_KEY` 없이도 **대시보드**는 동작합니다. **챗봇**과 미분류 가맹점
Claude 분류에만 키가 필요합니다.

> 💡 `localhost`가 IPv6(::1)로 풀려 백엔드(127.0.0.1) 연결이 안 될 수 있어,
> 프론트는 기본적으로 `127.0.0.1:8000`을 호출합니다.

### 환경 변수

| 변수 | 위치 | 기본값 | 설명 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | `.env` (백엔드) | — | Claude API 키 |
| `WALLET_COPILOT_MODEL` | `.env` | `claude-opus-4-8` | 사용 모델 |
| `WALLET_COPILOT_LLM_CATEGORIZE` | `.env` | `false` | 미분류 가맹점 Claude 분류 |
| `NEXT_PUBLIC_API_BASE` | `fe/.env.local` | `http://127.0.0.1:8000` | 백엔드 주소 |

## CLI 빠른 테스트

```bash
python -m core.data_loader      # 로드/정제
python -m core.categorize       # 분류 커버리지
python -m core.agent "배달비 30% 줄이면 얼마 절약돼?"   # 에이전트 (키 필요)
```
