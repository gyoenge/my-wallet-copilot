"use client";

import { useState } from "react";

import {
  streamDebate,
  type DebateFact,
  type DebateGoal,
  type DebateTurn,
  type DebateVerdict,
} from "@/lib/api";

// 페르소나별 색/이모지 (백엔드 persona 키와 일치).
const PERSONA_STYLE: Record<string, { ring: string; bg: string; emoji: string }> = {
  hedonist: { ring: "#f6a5c0", bg: "#fff1f5", emoji: "🍰" },
  planner: { ring: "#8bb8f6", bg: "#eef4ff", emoji: "📋" },
  futurist: { ring: "#7fd6a8", bg: "#eefaf2", emoji: "🌱" },
};

export default function Debate({
  sessionId,
  onGoalSet,
}: {
  sessionId: string | null;
  onGoalSet?: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [facts, setFacts] = useState<DebateFact[]>([]);
  const [turns, setTurns] = useState<DebateTurn[]>([]);
  const [verdict, setVerdict] = useState<DebateVerdict | null>(null);
  const [goal, setGoal] = useState<DebateGoal | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    if (!sessionId || busy) return;
    setBusy(true);
    setError(null);
    setFacts([]);
    setTurns([]);
    setVerdict(null);
    setGoal(null);
    await streamDebate(sessionId, question.trim() || null, {
      onFacts: (f) => setFacts(f),
      onTurn: (t) => setTurns((prev) => [...prev, t]),
      onVerdict: (v) => setVerdict(v),
      onGoal: (g) => {
        setGoal(g);
        onGoalSet?.(); // 분석 탭 '목표 추적' 카드 갱신
      },
      onError: (msg) => setError(msg),
    });
    setBusy(false);
  }

  const started = facts.length > 0 || turns.length > 0 || verdict !== null || busy;

  return (
    <div className="flex h-full min-h-[560px] flex-col rounded-[22px] border border-[#ebedf3] bg-white shadow-[0_1px_3px_rgba(20,20,50,0.04)]">
      {/* 헤더 */}
      <div className="flex items-center gap-3 border-b border-[#eef0f5] px-[22px] py-5">
        <span className="text-[26px]">🧠</span>
        <div>
          <div className="text-[16px] font-bold text-[#1c1f2b]">토론 모드</div>
          <div className="text-[12.5px] text-[#8a92a6]">
            쾌락·계획·미래가 당신의 소비를 두고 토론하고, 조정자가 결론을 냅니다.
          </div>
        </div>
      </div>

      {/* 본문 */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-[22px]">
        {!started && (
          <div className="text-[15px] leading-[1.6] text-[#3c4252]">
            세 페르소나가 실제 소비 데이터(팩트시트)를 근거로 토론합니다. 질문을 비워두면
            “절약과 삶의 질 사이 균형”을 주제로 진행해요.
          </div>
        )}

        {/* 팩트시트 */}
        {facts.length > 0 && (
          <div className="rounded-[16px] border border-[#ebedf3] bg-[#fafbfe] p-4">
            <div className="mb-2 text-[12px] font-bold text-[#8a92a6]">
              📎 팩트시트 (모든 주장은 이 근거를 인용합니다)
            </div>
            <div className="flex flex-col gap-1.5">
              {facts.map((f) => (
                <div key={f.id} className="text-[12.5px] text-[#4b5263]">
                  <span className="mr-1.5 rounded bg-[#eef0f5] px-1.5 py-0.5 font-mono text-[11px] text-[#7c5cf6]">
                    {f.id}
                  </span>
                  {f.text}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 페르소나 발언 */}
        {turns.map((t, i) => {
          const s = PERSONA_STYLE[t.persona] ?? { ring: "#cdd3e0", bg: "#f5f6fa", emoji: "💬" };
          return (
            <div
              key={i}
              className="flex gap-3 rounded-[16px] border p-4"
              style={{ borderColor: s.ring, background: s.bg, animation: "wcFade 0.3s ease both" }}
            >
              <span className="text-[22px]">{s.emoji}</span>
              <div className="min-w-0">
                <div className="mb-1 text-[13px] font-bold text-[#1c1f2b]">{t.name}</div>
                <div className="whitespace-pre-wrap text-[14px] leading-[1.6] text-[#2a2d38]">
                  {t.text}
                </div>
              </div>
            </div>
          );
        })}

        {busy && (
          <div className="text-[13px] text-[#9aa1b2]">
            {verdict ? "" : turns.length === 0 ? "팩트 정리 중…" : "토론 진행 중…"}
          </div>
        )}

        {/* 조정자 결론 */}
        {verdict && (
          <div
            className="rounded-[18px] border border-[#d7ccff] bg-gradient-to-br from-[#f6f2ff] to-[#eef4ff] p-5"
            style={{ animation: "wcFade 0.35s ease both" }}
          >
            <div className="mb-2 flex items-center justify-between">
              <div className="text-[14px] font-extrabold text-[#5b46d6]">⚖️ 조정자 결론</div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-[#8a92a6]">신뢰도</span>
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[#e3ddf7]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#8b7cf6] to-[#6d5ef0]"
                    style={{ width: `${Math.round(verdict.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-[11px] font-bold text-[#5b46d6]">
                  {Math.round(verdict.confidence * 100)}%
                </span>
              </div>
            </div>
            <div className="mb-3 whitespace-pre-wrap text-[14.5px] leading-[1.65] text-[#2a2d38]">
              {verdict.conclusion}
            </div>
            <div className="mb-3 grid gap-2 sm:grid-cols-2">
              <div className="rounded-[12px] bg-white/70 p-3">
                <div className="mb-1 text-[11px] font-bold text-[#2bb98a]">🤝 합의</div>
                <div className="text-[12.5px] text-[#4b5263]">{verdict.consensus}</div>
              </div>
              <div className="rounded-[12px] bg-white/70 p-3">
                <div className="mb-1 text-[11px] font-bold text-[#c2730b]">⚡ 이견</div>
                <div className="text-[12.5px] text-[#4b5263]">{verdict.tension}</div>
              </div>
            </div>
            <div className="text-[12px] font-bold text-[#8a92a6]">실행안</div>
            <ul className="mt-1 flex flex-col gap-1">
              {verdict.actions.map((a, i) => (
                <li key={i} className="flex gap-2 text-[13.5px] text-[#2a2d38]">
                  <span className="text-[#7c5cf6]">→</span>
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* 토론 결론에서 추출한 추적 목표 */}
        {goal && (
          <div
            className="rounded-[16px] border border-[#cdeede] bg-[#f1faf5] p-4"
            style={{ animation: "wcFade 0.35s ease both" }}
          >
            <div className="mb-1 flex items-center justify-between gap-2">
              <div className="text-[13px] font-extrabold text-[#1f9d63]">
                🎯 이 토론으로 설정된 목표
              </div>
              <span
                className={`flex-none rounded-full px-2.5 py-1 text-[11px] font-bold ${
                  goal.onTrack ? "bg-[#e6f7ef] text-[#1f9d63]" : "bg-[#fff3e0] text-[#c2730b]"
                }`}
              >
                {goal.onTrack ? "🟢 순항" : "🔴 이탈 위험"}
              </span>
            </div>
            <div className="text-[14.5px] font-bold text-[#1c1f2b]">
              {goal.category} 월 {goal.target.toLocaleString()}원 이하
            </div>
            <div className="mb-2 text-[12px] text-[#7b8494]">{goal.note}</div>
            <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[12.5px] text-[#4b5263]">
              <span>최근 달({goal.lastMonth}) {goal.actual.toLocaleString()}원</span>
              <span className={goal.gap > 0 ? "text-[#d14343]" : "text-[#1f9d63]"}>
                목표 대비 {goal.gap > 0 ? "+" : ""}
                {goal.gap.toLocaleString()}원
              </span>
              <span>다음 달 예측 {goal.forecast.toLocaleString()}원</span>
            </div>
            <div className="mt-1.5 text-[11px] text-[#9aa1b2]">
              분석 결과 탭의 ‘목표 추적’ 카드에도 반영됩니다.
            </div>
          </div>
        )}

        {error && <div className="text-[13.5px] text-[#d14343]">⚠️ {error}</div>}
      </div>

      {/* 입력 + 시작 */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          start();
        }}
        className="flex gap-3 border-t border-[#eef0f5] px-[18px] py-4"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={sessionId ? "토론 주제 (비워두면 기본 주제)" : "데이터 로딩 중..."}
          disabled={!sessionId || busy}
          className="flex-1 rounded-[13px] border border-[#e2e5ee] bg-[#f7f8fb] px-4 py-[13px] text-[14px] text-[#1c1f2b] outline-none placeholder:text-[#9aa1b2] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!sessionId || busy}
          className="rounded-[13px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] text-[14px] font-bold text-white disabled:opacity-40"
        >
          {busy ? "토론 중…" : started ? "다시 토론" : "토론 시작"}
        </button>
      </form>
    </div>
  );
}
