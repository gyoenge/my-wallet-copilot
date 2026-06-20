"use client";

import { useEffect, useState } from "react";

import Chat from "@/components/Chat";
import Dashboard from "@/components/Dashboard";
import TLogo from "@/components/TLogo";
import Welcome from "@/components/Welcome";
import { getDashboard, getHealth, uploadFile } from "@/lib/api";
import type { Dashboard as DashboardData } from "@/lib/types";

export default function Home() {
  const [screen, setScreen] = useState<"welcome" | "dashboard">("welcome");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasKey, setHasKey] = useState(true);

  useEffect(() => {
    getHealth()
      .then((h) => setHasKey(h.has_api_key))
      .catch(() => setHasKey(false));
  }, []);

  async function start(file: File | null) {
    setLoading(true);
    setError(null);
    try {
      const { session_id } = await uploadFile(file);
      const dash = await getDashboard(session_id);
      setSessionId(session_id);
      setData(dash);
      setScreen("dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "백엔드에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  if (screen === "welcome" || !data) {
    return <Welcome onStart={start} loading={loading} error={error} />;
  }

  return (
    <div className="mx-auto max-w-[1640px] px-8 pb-14 pt-7" style={{ animation: "wcFade 0.5s ease both" }}>
      {/* 헤더 */}
      <header className="mb-[26px] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <TLogo size={56} font={22} radius={16} />
          <div>
            <div className="text-[25px] font-extrabold tracking-tight">My Wallet Copilot</div>
            <div className="mt-0.5 text-[14px] text-[#9aa3bd]">김티(T) · 팩폭 전문 현실 절친</div>
          </div>
        </div>
        <button
          onClick={() => setScreen("welcome")}
          className="wc-ghost rounded-xl border border-white/10 bg-white/[0.04] px-5 py-[11px] text-[14px] font-semibold text-[#cfd5e8]"
        >
          내역 업로드
        </button>
      </header>

      {!hasKey && (
        <div className="mb-[22px] rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-[14px] text-amber-200">
          ANTHROPIC_API_KEY가 설정되지 않아 챗봇이 비활성화됩니다. 대시보드는 정상 동작합니다.
        </div>
      )}

      {/* 본문: 대시보드(좌) + 채팅(우) */}
      <div className="grid items-start gap-[22px] lg:grid-cols-[1.85fr_1fr]">
        <Dashboard data={data} />
        <Chat sessionId={hasKey ? sessionId : null} />
      </div>
    </div>
  );
}
