"""벤치마크 러너 — 시스템별 정량 지표를 대조한다.

지표: 정확도, 환각률, 평균 상대오차(MAPE류), 지연(s), 토큰, 유형별 정확도,
그리고 일관성(self-consistency, 반복 실행 시 답 변동).

실행:
  python -m ai.eval.run_bench [질문수]            # 기본 벤치마크
  python -m ai.eval.run_bench consistency [N]     # 일관성(질문당 N회 반복)
환경: ANTHROPIC_API_KEY 필요.
"""

from __future__ import annotations

import statistics
import sys
import time

import pandas as pd

from .dataset import build_benchmark
from .systems import SYSTEMS
from .verify import extract_numbers, score_answer


def run(df: pd.DataFrame, limit: int | None = None) -> dict:
    """각 시스템을 질문셋에 돌려 채점 + 지연/토큰을 기록한다."""
    questions = build_benchmark(df)
    if limit:
        questions = questions[:limit]

    results: dict[str, list] = {name: [] for name in SYSTEMS}
    for q in questions:
        for name, fn in SYSTEMS.items():
            t0 = time.perf_counter()
            try:
                r = fn(df, q.text)
                text, in_tok, out_tok = r.text, r.input_tokens, r.output_tokens
            except Exception as e:  # noqa: BLE001
                text, in_tok, out_tok = f"[오류: {e}]", 0, 0
            results[name].append({
                "q": q,
                "answer": text,
                "score": score_answer(q, text),
                "latency": time.perf_counter() - t0,
                "in_tok": in_tok,
                "out_tok": out_tok,
            })
    return results


def report(results: dict) -> None:
    names = list(results)
    rows = results[names[0]]

    print("\n=== 질문별 정오 (✓/✗, 괄호는 상대오차) ===")
    print("질문".ljust(20) + "".join(n.ljust(16) for n in names))
    for i, r0 in enumerate(rows):
        line = r0["q"].id.ljust(20)
        for n in names:
            sc = results[n][i]["score"]
            mark = "✓" if sc["correct"] else ("✗환각" if sc.get("hallucinated") else "✗")
            if sc.get("rel_err") is not None and not sc["correct"]:
                mark += f"({sc['rel_err']*100:.0f}%)"
            line += mark.ljust(16)
        print(line)

    print("\n=== 시스템 요약 ===")
    print("system".ljust(12) + "정확도   환각률   평균상대오차   지연(s)  토큰(in/out)")
    for n in names:
        rs = results[n]
        total = len(rs)
        correct = sum(r["score"]["correct"] for r in rs)
        amount = [r for r in rs if not isinstance(r["score"]["expected"], str)]
        halluc = sum(r["score"].get("hallucinated", False) for r in rs)
        errs = [r["score"]["rel_err"] for r in amount if r["score"].get("rel_err") is not None]
        lat = statistics.mean(r["latency"] for r in rs)
        itok = sum(r["in_tok"] for r in rs) // max(total, 1)
        otok = sum(r["out_tok"] for r in rs) // max(total, 1)
        acc = correct / total * 100 if total else 0
        hrate = halluc / len(amount) * 100 if amount else 0
        mape = statistics.mean(errs) * 100 if errs else 0
        print(
            f"{n:12s}{acc:5.0f}%  {hrate:5.0f}%   {mape:9.1f}%   {lat:6.1f}   {itok:>5}/{otok:<5}"
        )

    print("\n=== 유형별 정확도 (amount / label) ===")
    for n in names:
        rs = results[n]
        amt = [r for r in rs if not isinstance(r["score"]["expected"], str)]
        lab = [r for r in rs if isinstance(r["score"]["expected"], str)]
        a = sum(r["score"]["correct"] for r in amt) / len(amt) * 100 if amt else 0
        l = sum(r["score"]["correct"] for r in lab) / len(lab) * 100 if lab else 0
        print(f"  {n:12s} amount {a:5.0f}%  ({len(amt)}문항) | label {l:5.0f}%  ({len(lab)}문항)")


def consistency(df: pd.DataFrame, n: int = 3, limit: int | None = None) -> dict:
    """질문당 N회 반복 실행해 답의 변동(일관성)을 측정한다.

    - amount: 정답 인접 수치(그 수량에 대한 시스템의 답)의 변동계수(CV)로
      1-CV → 일관성(0~1). 결정적 도구는 매번 같은 값 → 1.0.
    - label: 정답 포함 여부의 다수결 일치율.
    """
    questions = build_benchmark(df)
    if limit:
        questions = questions[:limit]

    def _closest(nums: list[float], target: float) -> float | None:
        return min(nums, key=lambda x: abs(x - target)) if nums else None

    out: dict[str, list[float]] = {name: [] for name in SYSTEMS}
    for q in questions:
        for name, fn in SYSTEMS.items():
            answers = [fn(df, q.text).text for _ in range(n)]
            if isinstance(q.truth, str):
                hits = sum(str(q.truth) in a for a in answers)
                out[name].append(max(hits, n - hits) / n)
            else:
                vals = [_closest(extract_numbers(a), float(q.truth)) for a in answers]
                vals = [v for v in vals if v is not None]
                if len(vals) < 2:
                    out[name].append(1.0)
                elif statistics.mean(vals) == 0:
                    out[name].append(1.0 if len(set(vals)) <= 1 else 0.0)
                else:
                    cv = statistics.pstdev(vals) / abs(statistics.mean(vals))
                    out[name].append(max(0.0, 1 - min(cv, 1.0)))
    return out


def report_consistency(scores: dict, n: int) -> None:
    print(f"\n=== 일관성 (질문당 {n}회 반복, 1.0=완전 일관) ===")
    for name, vals in scores.items():
        print(f"  {name:12s} {statistics.mean(vals):.2f}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    from ai.categorize import categorize
    from ai.data_loader import load_transactions

    load_dotenv()
    _df = categorize(load_transactions(), use_llm=False)

    if len(sys.argv) > 1 and sys.argv[1] == "consistency":
        runs = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        lim = int(sys.argv[3]) if len(sys.argv) > 3 else None
        print(f"일관성 측정 (반복 {runs}회, 시스템 {list(SYSTEMS)})")
        report_consistency(consistency(_df, n=runs, limit=lim), runs)
    else:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
        print(f"벤치마크 시작 (시스템 {list(SYSTEMS)})")
        report(run(_df, limit=limit))
