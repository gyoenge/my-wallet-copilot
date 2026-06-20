# 💰 My Wallet Copilot

카드·계좌 소비 내역을 분석해 소비 패턴을 발견하고, 절약 포인트를 제안하며,
자연어 질문에 데이터 기반으로 답하는 AI Agent입니다.

> **예시 인사이트**
> - "이번 분석 기간 동안 배달에 915,073원을 썼습니다." (전체의 24.6%)
> - "토요일에 가장 많이 (824,736원) 씁니다."
> - "배달을 30% 줄이면 월 68,630원, 연 823,566원을 아낄 수 있어요."

## 기능

- **소비 카테고리 자동 분류** — 한국 가맹점 규칙 기반(비용 0, 결정적) + 미분류 가맹점 Claude 폴백
- **소비 패턴 발견** — 카테고리/월별/요일별/시간대별 지출 시각화
- **절약 포인트 제안** — 카테고리별 절감 시 월/연 절약액 추정
- **자연어 질의응답** — "가장 돈을 많이 쓰는 요일은?", "배달비 줄이면 얼마 절약돼?" 등

## 기술 스택

- **Streamlit** — 대시보드 + 챗 UI
- **LangGraph** — ReAct 에이전트 (분석 도구 오케스트레이션)
- **Claude API** (`claude-opus-4-8`) — `langchain-anthropic` 경유
- **pandas / plotly** — 결정적 분석 및 시각화

핵심 설계: 모든 숫자는 pandas 분석 함수(`src/analysis.py`)에서 계산되어 에이전트에
**도구**로 제공됩니다. Claude는 도구 결과를 근거로만 답하므로 금액을 지어내지 않습니다.

## 구조

```
app.py                 # Streamlit 앱 (대시보드 + 챗봇)
src/
  data_loader.py       # .xls 로드/정제 (합계행 제거, 정상건 필터, 파생 컬럼)
  categorize.py        # 가맹점 → 카테고리 (규칙 + Claude 폴백)
  analysis.py          # 결정적 pandas 분석 (카테고리/월/요일/MoM/절약)
  agent.py             # LangGraph 에이전트 + 분석 도구
data/카드이용내역.xls    # 샘플 데이터
```

## 시작하기

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # ANTHROPIC_API_KEY 입력
streamlit run app.py
```

`ANTHROPIC_API_KEY` 없이도 **대시보드**는 동작합니다(분석은 LLM을 쓰지 않음).
**챗봇**과 미분류 가맹점 Claude 분류에는 키가 필요합니다.

### 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Claude API 키 (챗봇/LLM 분류용) |
| `WALLET_COPILOT_MODEL` | `claude-opus-4-8` | 사용할 모델 |
| `WALLET_COPILOT_LLM_CATEGORIZE` | `false` | 미분류 가맹점을 Claude로 분류할지 |

## CLI로 빠르게 테스트

```bash
python -m src.data_loader      # 로드/정제 확인
python -m src.categorize       # 카테고리 분류 커버리지
python -m src.agent "배달비 30% 줄이면 얼마 절약돼?"   # 에이전트 (키 필요)
```
