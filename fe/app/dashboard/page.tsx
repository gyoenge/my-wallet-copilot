"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import Chat from "@/components/Chat";
import Dashboard from "@/components/Dashboard";
import Debate from "@/components/Debate";
import { getDashboard, getHealth } from "@/lib/api";
import type { Dashboard as DashboardData } from "@/lib/types";

const SESSION_KEY = "wallet_session_id";

export default function DashboardPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [hasKey, setHasKey] = useState(true);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"analysis" | "debate" | "chat">("analysis");

  useEffect(() => {
    const sid = localStorage.getItem(SESSION_KEY);
    if (!sid) {
      router.replace("/");
      return;
    }
    setSessionId(sid);
    getHealth()
      .then((h) => setHasKey(h.has_api_key))
      .catch(() => setHasKey(false));
    getDashboard(sid)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
        // 세션이 만료/무효(예: 백엔드 재시작)면 웰컴으로 복귀.
        localStorage.removeItem(SESSION_KEY);
        router.replace("/");
      });
  }, [router]);

  // 토론에서 목표가 설정되면 대시보드를 다시 불러와 '목표 추적' 카드에 반영한다.
  const refreshDashboard = useCallback(() => {
    const sid = sessionId ?? localStorage.getItem(SESSION_KEY);
    if (!sid) return;
    getDashboard(sid)
      .then(setData)
      .catch(() => {});
  }, [sessionId]);

  if (loading || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[#8a92a6]">
        불러오는 중...
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col" style={{ animation: "wcFade 0.5s ease both" }}>
      {/* 상단 바 — 웰컴 페이지와 통일 (로고 + 새 분석) */}
      <header className="flex items-center justify-between px-6 py-6 md:px-10">
        <Link href="/" aria-label="홈으로" className="flex items-center transition hover:opacity-80">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/savy_logo.png" alt="SAVY: My Wallet Copilot" className="h-[46px] w-auto" />
        </Link>
        <button
          onClick={() => router.push("/")}
          className="rounded-[12px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] py-3 text-[16px] font-semibold text-white transition hover:opacity-90"
        >
          새 분석
        </button>
      </header>

      <div className="mx-auto w-full max-w-[1280px] px-8 pb-14">
      {!hasKey && (
        <div className="mb-[22px] rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-[14px] text-amber-200">
          ANTHROPIC_API_KEY가 설정되지 않아 챗봇이 비활성화됩니다. 대시보드는 정상 동작합니다.
        </div>
      )}

      {/* 탭 전환 */}
      <div className="mb-6 inline-flex gap-1 rounded-[15px] border border-[#e7e9f1] bg-white p-[5px] shadow-[0_1px_2px_rgba(20,20,50,0.04)]">
        {(
          [
            ["analysis", "📊 분석 결과"],
            ["debate", "🧠 토론 모드"],
            ["chat", "💬 세이비와 채팅"],
          ] as const
        ).map(([t, label]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-[11px] px-5 py-2.5 text-[14px] font-bold transition ${
              tab === t
                ? "bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] text-white shadow-[0_6px_16px_rgba(124,92,246,0.32)]"
                : "text-[#8a92a6] hover:text-[#1c1f2b]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 탭 내용 */}
      {tab === "analysis" ? (
        <div style={{ animation: "wcFade 0.35s ease both" }}>
          <Dashboard data={data} />
        </div>
      ) : tab === "debate" ? (
        <div
          className="mx-auto max-w-[860px]"
          style={{ height: "calc(100vh - 230px)", animation: "wcFade 0.35s ease both" }}
        >
          <Debate sessionId={hasKey ? sessionId : null} onGoalSet={refreshDashboard} />
        </div>
      ) : (
        <div
          className="mx-auto max-w-[860px]"
          style={{ height: "calc(100vh - 230px)", animation: "wcFade 0.35s ease both" }}
        >
          <Chat sessionId={hasKey ? sessionId : null} />
        </div>
      )}
      </div>
    </div>
  );
}
