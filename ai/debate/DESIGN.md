# 멀티 에이전트 금융 분석 시스템 설계

> "인사이드 아웃" 컨셉의 페르소나 토론 시스템. 실제 구현 가능하고 정량 평가까지
> 가능한 형태로 정리한다. 본 문서는 **설계 기준선**이며, 코드는 이 문서를 따른다.

---

## 0. 설계 원칙

1. **사실과 의견의 분리** — Analyst는 토론 참여자가 아니라 *fact 공급자*. 페르소나는
   숫자를 지어내지 않고, 모든 주장을 Fact Sheet의 `fact_id`에 grounding 한다.
2. **숫자는 코드로, 말은 LLM으로** — 정량 계산은 `ai/analysis.py`(결정적), 해석·설득·
   조정만 LLM. numeric verifier가 LLM 산출 수치를 코드로 재대조한다.
3. **평가 인프라 우선** — Fact Sheet 스키마 · 합성 시나리오셋 · numeric verifier를
   에이전트보다 **먼저** 만든다. 이것이 나머지 전부의 채점 기준이 된다.
4. **비용은 비대칭 배분** — 페르소나 발언은 `low` effort + 길이 제한, Mediator만
   `high`. 토론은 고정 라운드 + 조기 종료(수렴 판단)로 통제한다.

---

## 1. 시스템 아키텍처

```
[거래내역]
   │  data_loader.load_transactions()  +  categorize()  +  critic.critique()
   ▼
[Analyst]  analysis.py 집계 → Fact Sheet(JSON, fact_id 부여)   ◀── 사실 공급자(토론 불참)
   │
   ├─▶ Round 1: 각 페르소나가 fact 기반 초기 입장 (반드시 [fact_id] 인용)
   ├─▶ Round 2~N: 상호 반박 (fact_id 미인용 주장은 Mediator가 자동 기각)
   │        └─ 조기 종료: Mediator가 수렴 판단 시 중단
   ▼
[Mediator/Judge]  합의/비합의 분리 → 결론 + 실행안 + confidence
   │   └─ numeric verifier: 결론 내 모든 수치를 코드로 재계산 대조
   ▼
[Human-in-the-loop]  사용자 검토·수정·승인  (be/main.py review/finalize 흐름 재사용)
   ▼
[Audit trace]  모든 발언·인용·결론을 로그로 저장
```

### 에이전트 구성

| 에이전트 | 역할 | 목적함수(내적 최적화) | effort |
|---|---|---|---|
| **Analyst** | 거래 데이터 → fact sheet (사실 공급자, 토론 불참) | 통계적 정확성 | 코드(LLM 아님) |
| **Hedonist** | 현재 효용 극대화, 소비 정당화 | 단기 만족도·삶의 질 | low |
| **Planner** | 예산 배분, 소비 변화 시나리오 | 예산 준수율·실행 가능성 | low |
| **Futurist** | 저축·자산 형성, 기회비용 경고 | 장기 순자산·복리 | low |
| **Mediator** | 토론 종합, 결론·신뢰도 산출 | 결론 일관성·근거 충실성 | high |

---

## 2. 기존 코드와의 매핑 (재사용)

| 설계 구성요소 | 기존 자산 | 비고 |
|---|---|---|
| Analyst / Fact Sheet | `ai/analysis.py`(집계 11종) + `ai/agent/single.py`의 결정적 도구 | fact_id만 부여하면 됨 |
| numeric verifier | "숫자는 항상 도구로" 원칙(single.py) | 절반 구현됨 — 대조 로직만 추가 |
| Mediator | `ai/agent/supervisor.py` | 전문가 호출 → 토론 종합으로 확장 |
| 단일 LLM 베이스라인 | `ai/agent/single.py` build_agent | 평가 베이스라인 ②로 그대로 사용 |
| HITL 검토·승인 | `be/main.py` `/analyze → review → finalize` | 토론 결론 검수에 재사용 |
| 분류 신뢰도 | `ai/critic.py` | Fact Sheet의 데이터 품질 메타로 포함 |

---

## 3. 데이터 파이프라인 & Fact Sheet

```
원시 거래내역(xls/CSV/오픈뱅킹)
  → 정규화        data_loader.load_transactions()
  → 카테고리 태깅  categorize() + critic.critique()  (불확실 항목 메타 포함)
  → 집계 레이어    analysis.py (월별/카테고리별/시간대별/요일별/가맹점)
  → 도메인 feature 신규 가맹점 탐색 점수, 배달 빈도 등
  → Fact Sheet(JSON)  ── 모든 에이전트 공통 입력
```

### Fact Sheet 스키마(초안)

```json
{
  "period": { "start": "2026-01-01", "end": "2026-06-30", "months": 6 },
  "data_quality": { "uncertain_categories": 4, "total_merchants": 102 },
  "facts": [
    { "id": "F001", "type": "summary",  "metric": "총지출", "value": 5234000, "unit": "KRW" },
    { "id": "F002", "type": "summary",  "metric": "월평균", "value": 915073, "unit": "KRW" },
    { "id": "F012", "type": "category", "category": "배달", "value": 738117, "share_pct": 14.1, "count": 48 },
    { "id": "F031", "type": "weekday",  "weekday": "금", "value": 980000, "rank": 1 },
    { "id": "F040", "type": "novelty",  "metric": "신규 가맹점 비율", "value": 0.23 },
    { "id": "F051", "type": "anomaly",  "merchant": "...", "month": "2026-06", "delta": 120000 },
    { "id": "F060", "type": "whatif",   "category": "배달", "reduction_pct": 30, "월절약액": 221435 }
  ]
}
```

- `fact_id`는 **불변 식별자**. 페르소나/Mediator가 인용하는 단위.
- `whatif` 류는 미리 계산하지 않고, 페르소나가 요청 시 verifier가 코드로 산출해 추가.

---

## 4. 토론 프로토콜

```
입력: Fact Sheet + 사용자 질문
Round 1 (입장):  각 페르소나 → {입장, 근거 [fact_id…], 제안}
Round 2..N (반박): 각 페르소나 → 상대 발언 반박 (반드시 fact_id 인용)
  └ 종료 조건: (a) 고정 최대 라운드 도달  또는
               (b) Mediator가 "새 논점 없음/수렴" 판단
Mediator:  합의 지점 / 비합의 지점 분리
           → 결론 + 실행안(구체적·제약 만족) + confidence(0~1)
           → numeric verifier 통과한 수치만 최종 결론에 포함
```

### 환각·일탈 방지

- **Citation 강제**: 모든 정량 주장은 `[fact_id]` 인용. 미인용 정량 주장은 Mediator가
  자동 기각(결론에 반영 안 함).
- **Numeric verifier**: 결론 텍스트에서 수치를 추출 → `analysis.py`로 재계산 → 불일치 시
  플래그/정정. LLM이 직접 계산하지 않는다.
- **Audit trace**: 발언·인용·기각·결론을 JSON 로그로 저장 → 사람이 추적 검증.

---

## 5. 정량 평가 (3개 층위)

### A. 사실 정확성

| 지표 | 정의 | 측정법 |
|---|---|---|
| Numeric Accuracy | 산출 수치 vs 코드 정답 | 셀 단위 절대오차/정확률 |
| Hallucination Rate | 데이터에 없는 주장 비율 | 인용 검증 통과율의 역수 |
| Citation Validity | 인용 fact_id가 실제 근거를 지지 | 자동 + 샘플 수기 |

### B. 추론·토론 품질

| 지표 | 정의 |
|---|---|
| Recommendation Validity | 제안이 예산·현금흐름 제약을 위반하지 않는 비율 |
| Consistency | 동일 입력 N회 재실행 결론 일치도 (self-consistency) |
| Debate Gain | 단일 vs 멀티에이전트 품질 차 (ablation) |
| Convergence Rounds | 합의까지 평균 라운드 수 |

### C. 결과 효용

| 지표 | 정의 |
|---|---|
| Actionability | 제안 구체성·실행 가능성 (rubric 1–5, 사람/LLM-judge) |
| Backtest Saving | 제안을 과거 데이터에 적용한 절감 시뮬레이션 |
| Forecast Error (MAE/MAPE) | Planner 예측 vs 실제 다음 달 지출 |
| User Acceptance | HITL에서 무수정 채택 비율 |

### 벤치마크 구성

1. **합성 시나리오셋** (50~100건): 정답이 코드로 검증 가능(예: 배달 30% 감축 절감액).
   → A·B 층위 자동 채점.
2. **실데이터 holdout**: 앞 N개월 학습 / 뒤 1개월 검증 → Forecast Error, Backtest.
3. **베이스라인 대조**: ① 룰 기반 가계부 ② 단일 LLM(`single.build_agent`)
   ③ 멀티에이전트(본 시스템). 동일 질문셋.
4. **LLM-as-judge + 인간 검수**: 주관 지표는 LLM 채점 후 일부 수기 검증(Cohen's κ).

### 성공 기준(예시 목표)

- Numeric Accuracy ≥ 99%, Hallucination Rate ≤ 1%
- Recommendation Validity(제약 위반 0건) = 100%
- Debate Gain: Actionability가 단일 대비 통계적으로 유의하게 향상
- Forecast MAPE ≤ 15%

---

## 6. 모듈 구조(제안)

```
ai/agent/
  facts.py       # Fact Sheet 생성 (analysis.py 래핑 + fact_id 부여)
  personas.py    # Hedonist / Planner / Futurist 페르소나 에이전트
  mediator.py    # 토론 종합 + confidence (supervisor.py 확장)
  debate.py      # 토론 오케스트레이션 (라운드/조기종료/citation 강제/audit)
  verify.py      # numeric verifier (결론 수치 ↔ analysis.py 재계산 대조)
ai/eval/
  synth.py       # 합성 시나리오셋 생성 (정답 동봉)
  metrics.py     # A/B/C 층위 지표 계산
  run_bench.py   # 베이스라인 ①②③ 대조 실행
```

---

## 7. 프롬프트 템플릿(골격)

### 페르소나 공통 규칙(시스템 프롬프트 헤더)

```
당신은 '{persona}' 입니다. 목적은 {목적함수}.
규칙:
- 모든 정량 주장은 반드시 Fact Sheet의 [fact_id]를 인용한다. 인용 없는 수치는 금지.
- 숫자를 직접 계산하지 말 것. 필요한 값이 Fact Sheet에 없으면 "verifier 요청: <설명>"으로 남긴다.
- 입장은 3문장 이내, 제안은 1개로 압축한다.
```

### Hedonist / Futurist 예시 차별점

```
Hedonist:  현재의 만족과 삶의 질을 우선한다. 절약이 효용을 해치는 지점을 지적하라.
Futurist:  같은 금액의 장기 기회비용(복리)을 [fact_id] 근거로 경고하라.
```

### Mediator

```
당신은 조정자입니다. 페르소나 발언에서 (1) 합의 지점과 (2) 비합의 지점을 분리하라.
- [fact_id] 미인용 정량 주장은 결론에서 제외한다.
- 결론 = {핵심 진단, 실행안(예산·현금흐름 제약 만족), confidence 0~1}.
- 모든 수치는 verifier 통과본만 사용한다.
```

---

## 8. 평가 스크립트 골격(의사코드)

```python
# ai/eval/run_bench.py
for scenario in synth.load():                  # 정답 동봉 합성셋
    facts = facts.build(scenario.df)
    for system in [rule_baseline, single_llm, multi_agent]:
        out = system.answer(scenario.question, facts)
        record(
            numeric_accuracy = verify.numeric(out, scenario.truth),
            hallucination    = verify.uncited_ratio(out, facts),
            valid            = constraints.satisfied(out, scenario.df),
            actionability    = judge.score(out),     # LLM-judge (+ 수기 표본)
        )
report.compare()                               # 시스템별 지표 대조 + 유의성 검정
```

---

## 9. 핵심 제약 (구현 전 반드시 인지)

- **모델 결정성 통제 불가**: 기본 모델 `claude-opus-4-8`은 `temperature`/`top_p`가
  제거됨(전달 시 400). `temperature=0`으로 재현성을 강제할 수 없다.
  → 재현성이 필요한 지점(verifier 대조)은 **코드로**, 페르소나 발언은 변동을 인정하고
  Consistency 지표로 *관측*한다.
- **비용은 곱으로 증가**: 호출 ≈ 라운드 × 페르소나 × (인용검증). 페르소나는 `low` effort +
  길이 제한, Mediator만 `high`. 조기 종료가 비용 통제의 핵심.
- **단순 질문 오버헤드**: 토론이 불필요한 단순 질문은 기존 `router.py`(simple/complex
  분기)로 단일 에이전트에 위임 — 토론은 complex에만.

---

## 10. 단계적 구축 권장

1. **평가 인프라**: `facts.py`(Fact Sheet) + `eval/synth.py`(합성셋) + `verify.py`. ← 1순위
2. **최소 토론 루프**: Analyst + Hedonist↔Futurist + Mediator (2 페르소나)로 루프·평가 검증.
3. **확장**: Planner 추가, 조기 종료·audit trace 강화, baseline 대조(run_bench).
4. **HITL 연결**: `be/main.py`에 토론 결론 검수 엔드포인트 추가(review/finalize 패턴 재사용).
