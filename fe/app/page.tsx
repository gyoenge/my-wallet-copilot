"use client";

import { useEffect, useRef, useState } from "react";

import Avatar from "@/components/Avatar";
import Chat from "@/components/Chat";
import Dashboard from "@/components/Dashboard";
import { getDashboard, getHealth, uploadFile } from "@/lib/api";
import type { Dashboard as DashboardData } from "@/lib/types";

const SCORE_TONE: Record<string, string> = {
  양호: "text-emerald-400",
  보통: "text-sky-400",
  주의: "text-amber-400",
  위험: "text-rose-400",
};

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasKey, setHasKey] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);

  async function init(file: File | null) {
    setLoading(true);
    setError(null);
    try {
      const { session_id } = await uploadFile(file);
      const dash = await getDashboard(session_id);
      setSessionId(session_id);
      setData(dash);
    } catch (e) {
      setError(e instanceof Error ? e.message : "백엔드에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    getHealth()
      .then((h) => setHasKey(h.has_api_key))
      .catch(() => setHasKey(false));
    init(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 md:px-6">
      {/* 헤더 */}
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar size={52} variant="main" />
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              My Wallet Copilot
            </h1>
            <p className="text-sm font-semibold text-accent">
              김티(T) · 팩폭 전문 현실 절친
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".xls,.xlsx"
            className="hidden"
            onChange={(e) => init(e.target.files?.[0] ?? null)}
          />
          <button
            onClick={() => fileRef.current?.click()}
            className="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:border-accent/50"
          >
            내역 업로드
          </button>
        </div>
      </header>

      {!hasKey && (
        <div className="mb-5 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          ANTHROPIC_API_KEY가 설정되지 않아 챗봇이 비활성화됩니다. 대시보드는 정상 동작합니다.
        </div>
      )}

      {error && (
        <div className="mb-5 rounded-2xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-200">
          {error} — FastAPI 백엔드(127.0.0.1:8000)가 실행 중인지 확인하세요.
        </div>
      )}

      {loading && !data && (
        <div className="py-20 text-center text-slate-400">분석하는 중...</div>
      )}

      {data && (
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div className="space-y-6">
            {/* 페르소나 요약 */}
            <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-violet-600/20 via-white/[0.03] to-blue-600/10 p-6">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Avatar size={44} />
                  <div className="text-sm font-bold text-white">김티의 한 줄 진단</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-400">소비 건강 점수</div>
                  <div className={`text-2xl font-black ${SCORE_TONE[data.health.label] ?? "text-white"}`}>
                    {data.health.score}
                    <span className="ml-1 text-sm font-bold text-slate-400">
                      {data.health.label}
                    </span>
                  </div>
                </div>
              </div>
              <ul className="space-y-2">
                {data.insights.map((t, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-200">
                    <span className="text-accent">•</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </section>

            <Dashboard data={data} />
          </div>

          {/* 채팅 */}
          <div className="lg:sticky lg:top-8 lg:self-start">
            <Chat sessionId={hasKey ? sessionId : null} />
            {!hasKey && (
              <p className="mt-2 text-center text-xs text-slate-500">
                챗봇을 쓰려면 백엔드에 ANTHROPIC_API_KEY를 설정하세요.
              </p>
            )}
          </div>
        </div>
      )}

      <footer className="mt-10 text-center text-xs text-slate-600">
        FastAPI + LangGraph + Claude · 모든 숫자는 데이터에서 직접 계산됩니다.
      </footer>
    </main>
  );
}
