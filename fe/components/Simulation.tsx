"use client";

import { useState } from "react";

import {
  getPreferenceQuestions,
  streamSimulate,
  type PrefQuestion,
  type SimEval,
  type SimRecommendation,
  type SimStrategy,
} from "@/lib/api";

function Bar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-[52px] flex-none text-[11px] text-[#8a92a6]">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#eef0f5]">
        <div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: color }} />
      </div>
      <span className="w-[34px] flex-none text-right text-[11px] font-semibold text-[#4b5263]">
        {Math.round(value * 100)}
      </span>
    </div>
  );
}

export default function Simulation({ sessionId }: { sessionId: string | null }) {
  const [questions, setQuestions] = useState<PrefQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [loadingQ, setLoadingQ] = useState(false);

  const [simStarted, setSimStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [strategies, setStrategies] = useState<SimStrategy[]>([]);
  const [evals, setEvals] = useState<Record<number, SimEval>>({});
  const [rec, setRec] = useState<SimRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  const phase = simStarted ? "result" : questions.length > 0 ? "qa" : "intro";

  async function loadQuestions() {
    if (!sessionId || loadingQ) return;
    setLoadingQ(true);
    setError(null);
    try {
      setQuestions(await getPreferenceQuestions(sessionId));
    } catch (e) {
      setError(e instanceof Error ? e.message : "질문 생성 실패");
    } finally {
      setLoadingQ(false);
    }
  }

  async function run(prefs: string) {
    if (!sessionId || busy) return;
    setSimStarted(true);
    setBusy(true);
    setError(null);
    setStrategies([]);
    setEvals({});
    setRec(null);
    await streamSimulate(sessionId, prefs.trim() || null, {
      onCandidates: (s) => setStrategies(s),
      onEval: (r) => setEvals((prev) => ({ ...prev, [r.index]: r })),
      onRecommendation: (r) => setRec(r),
      onError: (msg) => setError(msg),
    });
    setBusy(false);
  }

  function runWithAnswers() {
    const prefs = questions
      .map((q) => (answers[q.id] ? `- ${q.question} → ${answers[q.id]}` : null))
      .filter(Boolean)
      .join("\n");
    run(prefs);
  }

  function reset() {
    setSimStarted(false);
    setQuestions([]);
    setAnswers({});
    setStrategies([]);
    setEvals({});
    setRec(null);
    setError(null);
  }

  return (
    <div className="flex h-full min-h-[560px] flex-col rounded-[22px] border border-[#ebedf3] bg-white shadow-[0_1px_3px_rgba(20,20,50,0.04)]">
      <div className="flex items-center gap-3 border-b border-[#eef0f5] px-[22px] py-5">
        <span className="text-[26px]">🧪</span>
        <div>
          <div className="text-[16px] font-bold text-[#1c1f2b]">시뮬레이션 모드</div>
          <div className="text-[12.5px] text-[#8a92a6]">
            선호를 물어보고 반영해 ‘절약 실행 효율’이 가장 높은 전략을 찾습니다.
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-[22px]">
        {phase === "intro" && (
          <div className="text-[15px] leading-[1.6] text-[#3c4252]">
            거래 내역만으론 그 소비가 ‘낭비’인지 ‘중요한 만족’인지 알 수 없어요. 먼저 소비
            패턴을 바탕으로 몇 가지를 여쭤본 뒤, 답변을 반영한 전략을 평가합니다.
          </div>
        )}

        {/* 선호 질문 (Q&A) */}
        {phase === "qa" &&
          questions.map((q) => (
            <div key={q.id} className="rounded-[16px] border border-[#ebedf3] bg-[#fafbfe] p-4">
              <div className="mb-2 text-[14px] font-semibold text-[#1c1f2b]">{q.question}</div>
              <div className="mb-2 flex flex-wrap gap-1.5">
                {q.options.map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setAnswers((p) => ({ ...p, [q.id]: opt }))}
                    className={`rounded-[10px] px-3 py-1.5 text-[12.5px] transition ${
                      answers[q.id] === opt
                        ? "bg-[#7c5cf6] font-semibold text-white"
                        : "border border-[#e5e7ef] bg-white text-[#4b5263] hover:bg-[#f3f4f8]"
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
              <input
                value={answers[q.id] && !q.options.includes(answers[q.id]) ? answers[q.id] : ""}
                onChange={(e) => setAnswers((p) => ({ ...p, [q.id]: e.target.value }))}
                placeholder="또는 직접 입력"
                className="w-full rounded-[10px] border border-[#e2e5ee] bg-white px-3 py-2 text-[13px] text-[#1c1f2b] outline-none placeholder:text-[#b6bcca]"
              />
            </div>
          ))}

        {/* 결과 */}
        {phase === "result" &&
          strategies.map((s, i) => {
            const ev = evals[i];
            const isWinner = rec?.winner_index === i;
            return (
              <div
                key={i}
                className={`rounded-[16px] border p-4 ${
                  isWinner ? "border-[#a78bfa] bg-[#f6f2ff]" : "border-[#ebedf3] bg-white"
                }`}
                style={{ animation: "wcFade 0.3s ease both" }}
              >
                <div className="mb-1 flex items-center justify-between gap-2">
                  <span className="truncate text-[14.5px] font-bold text-[#1c1f2b]">
                    {isWinner && "🏆 "}
                    {s.title}
                  </span>
                  {ev && (
                    <span className="flex-none rounded-full bg-[#efeaff] px-2.5 py-0.5 text-[11px] font-bold text-[#7c5cf6]">
                      절약실행효율 {ev.efficiency}
                    </span>
                  )}
                </div>
                <div className="mb-2 text-[12.5px] text-[#7b8494]">
                  {s.category} {Math.round(s.reduction_pct)}% · 월 {s.monthly_saving.toLocaleString()}원 절감
                  <span className="text-[#9aa1b2]"> — {s.description}</span>
                </div>
                {ev ? (
                  <div className="flex flex-col gap-1.5">
                    <Bar label="절감" value={ev.saving_score} color="#8b7cf6" />
                    <Bar label="만족보존" value={ev.satisfaction} color="#2bb98a" />
                    <Bar label="실행" value={ev.feasibility} color="#f0a830" />
                    <div className="mt-0.5 text-[11.5px] text-[#9aa1b2]">{ev.reason}</div>
                  </div>
                ) : (
                  <div className="text-[12px] text-[#9aa1b2]">평가 중…</div>
                )}
              </div>
            );
          })}

        {phase === "result" && busy && !rec && (
          <div className="text-[13px] text-[#9aa1b2]">
            {strategies.length === 0 ? "전략 생성 중…" : "전략 평가 중…"}
          </div>
        )}

        {rec && (
          <div
            className="rounded-[18px] border border-[#d7ccff] bg-gradient-to-br from-[#f6f2ff] to-[#eef4ff] p-5"
            style={{ animation: "wcFade 0.35s ease both" }}
          >
            <div className="mb-1 text-[14px] font-extrabold text-[#5b46d6]">
              ⚖️ 추천 — {rec.title} (효율 {rec.efficiency})
            </div>
            <div className="whitespace-pre-wrap text-[14px] leading-[1.6] text-[#2a2d38]">
              {rec.rationale}
            </div>
          </div>
        )}

        {error && <div className="text-[13.5px] text-[#d14343]">⚠️ {error}</div>}
      </div>

      {/* 푸터: 단계별 액션 */}
      <div className="flex gap-3 border-t border-[#eef0f5] px-[18px] py-4">
        {phase === "intro" && (
          <>
            <button
              onClick={loadQuestions}
              disabled={!sessionId || loadingQ}
              className="flex-1 rounded-[13px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] py-[13px] text-[14px] font-bold text-white disabled:opacity-40"
            >
              {loadingQ ? "질문 준비 중…" : "맞춤 질문 받기"}
            </button>
            <button
              onClick={() => run("")}
              disabled={!sessionId || loadingQ}
              className="rounded-[13px] border border-[#e2e5ee] px-[18px] text-[13px] font-semibold text-[#8a92a6] hover:bg-[#f6f2ff] disabled:opacity-40"
            >
              질문 없이 바로
            </button>
          </>
        )}
        {phase === "qa" && (
          <button
            onClick={runWithAnswers}
            disabled={!sessionId}
            className="flex-1 rounded-[13px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] py-[13px] text-[14px] font-bold text-white disabled:opacity-40"
          >
            이 답변으로 시뮬레이션 시작
          </button>
        )}
        {phase === "result" && (
          <button
            onClick={reset}
            disabled={busy}
            className="flex-1 rounded-[13px] border border-[#e2e5ee] py-[13px] text-[14px] font-bold text-[#4b5263] hover:bg-[#f6f2ff] disabled:opacity-40"
          >
            {busy ? "시뮬레이션 중…" : "다시 시작"}
          </button>
        )}
      </div>
    </div>
  );
}
