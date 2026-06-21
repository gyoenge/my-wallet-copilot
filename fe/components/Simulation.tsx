"use client";

import { useState } from "react";

import {
  streamSimulate,
  type SimEval,
  type SimRecommendation,
  type SimStrategy,
} from "@/lib/api";

const PREF_SUGGESTIONS = [
  "배달은 새 맛집 탐색 재미 때문. 주말 외식은 유지하고 평일 야식은 줄여도 됨.",
  "카페는 작업 공간이라 포기 어려움. 구독은 안 쓰는 게 많음. 단기 절약 목표.",
];

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
  const [prefs, setPrefs] = useState("");
  const [busy, setBusy] = useState(false);
  const [strategies, setStrategies] = useState<SimStrategy[]>([]);
  const [evals, setEvals] = useState<Record<number, SimEval>>({});
  const [rec, setRec] = useState<SimRecommendation | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!sessionId || busy) return;
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

  const started = strategies.length > 0 || busy;

  return (
    <div className="flex h-full min-h-[560px] flex-col rounded-[22px] border border-[#ebedf3] bg-white shadow-[0_1px_3px_rgba(20,20,50,0.04)]">
      <div className="flex items-center gap-3 border-b border-[#eef0f5] px-[22px] py-5">
        <span className="text-[26px]">🧪</span>
        <div>
          <div className="text-[16px] font-bold text-[#1c1f2b]">시뮬레이션 모드</div>
          <div className="text-[12.5px] text-[#8a92a6]">
            선호를 반영한 절약 전략들을 평가해 ‘절약 실행 효율’이 가장 높은 안을 찾습니다.
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-[22px]">
        {!started && (
          <div className="text-[15px] leading-[1.6] text-[#3c4252]">
            줄여도 되는 소비와 지키고 싶은 소비, 절약 목표를 알려주면 그 선호를 보존하는
            전략을 우선 평가합니다.
          </div>
        )}

        {strategies.map((s, i) => {
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

        {busy && !rec && (
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

      <form
        onSubmit={(e) => {
          e.preventDefault();
          start();
        }}
        className="border-t border-[#eef0f5] px-[18px] py-4"
      >
        {!started && (
          <div className="mb-2 flex flex-wrap gap-[7px]">
            {PREF_SUGGESTIONS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPrefs(p)}
                className="rounded-[10px] border border-[#e5e7ef] bg-white px-2.5 py-1.5 text-[12px] text-[#4b5263] hover:bg-[#f6f2ff]"
              >
                {p.slice(0, 22)}…
              </button>
            ))}
          </div>
        )}
        <div className="flex gap-3">
          <input
            value={prefs}
            onChange={(e) => setPrefs(e.target.value)}
            placeholder={sessionId ? "선호·맥락 (비워두면 일반 가정)" : "데이터 로딩 중..."}
            disabled={!sessionId || busy}
            className="flex-1 rounded-[13px] border border-[#e2e5ee] bg-[#f7f8fb] px-4 py-[13px] text-[14px] text-[#1c1f2b] outline-none placeholder:text-[#9aa1b2] disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!sessionId || busy}
            className="rounded-[13px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] text-[14px] font-bold text-white disabled:opacity-40"
          >
            {busy ? "시뮬레이션 중…" : started ? "다시 시뮬레이션" : "시뮬레이션 시작"}
          </button>
        </div>
      </form>
    </div>
  );
}
