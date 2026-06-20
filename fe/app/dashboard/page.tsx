"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import Chat from "@/components/Chat";
import Dashboard from "@/components/Dashboard";
import TLogo from "@/components/TLogo";
import { getDashboard, getHealth } from "@/lib/api";
import type { Dashboard as DashboardData } from "@/lib/types";

const SESSION_KEY = "wallet_session_id";

export default function DashboardPage() {
  const router = useRouter();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [data, setData] = useState<DashboardData | null>(null);
  const [hasKey, setHasKey] = useState(true);
  const [loading, setLoading] = useState(true);

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

  if (loading || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center text-[#9aa3bd]">
        불러오는 중...
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1640px] px-8 pb-14 pt-7" style={{ animation: "wcFade 0.5s ease both" }}>
      {/* 헤더 */}
      <header className="mb-[26px] flex items-center justify-between">
        <div className="flex items-center gap-4">
          <TLogo size={56} radius={16} />
          <div>
            <div className="text-[25px] font-extrabold tracking-tight">My Wallet Copilot</div>
            <div className="mt-0.5 text-[14px] text-[#9aa3bd]">세이비 · 새는 돈을 찾아주는 지갑 수호자</div>
          </div>
        </div>
        <button
          onClick={() => router.push("/")}
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
