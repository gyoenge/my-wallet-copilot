"use client";

import { useRef } from "react";

import TLogo from "./TLogo";

export default function Welcome({
  onStart,
  loading,
  error,
}: {
  onStart: (file: File | null) => void;
  loading: boolean;
  error: string | null;
}) {
  const fileRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex min-h-screen items-center justify-center px-6 py-10">
      <div className="w-full max-w-[560px]" style={{ animation: "wcFade 0.6s ease both" }}>
        {/* 히어로 */}
        <div className="mb-9 flex flex-col items-center text-center">
          <div
            className="mb-[22px] flex h-[88px] w-[88px] items-center justify-center rounded-[26px] bg-gradient-to-br from-[#8b7cf6] to-[#5b8def] text-[38px] font-extrabold text-white"
            style={{ boxShadow: "0 16px 44px rgba(124,92,246,0.42)" }}
          >
            T
          </div>
          <div className="mb-3 text-[13px] font-semibold uppercase tracking-[0.14em] text-[#8b7cf6]">
            My Wallet Copilot
          </div>
          <h1 className="mb-3.5 text-[30px] font-extrabold leading-[1.3]">
            안녕, 나는 <span className="text-[#a78bfa]">김티(T)</span>야
          </h1>
          <p className="m-0 max-w-[420px] text-[16px] leading-[1.7] text-[#9aa3bd]">
            팩폭 전문 현실 절친. 카드 내역만 던져주면
            <br />
            어디에 돈을 흘리고 있는지 가감 없이 까볼게.
          </p>
        </div>

        {/* 드롭존 */}
        <input
          ref={fileRef}
          type="file"
          accept=".xls,.xlsx,.csv"
          className="hidden"
          onChange={(e) => onStart(e.target.files?.[0] ?? null)}
        />
        <div
          onClick={() => !loading && fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (!loading) onStart(e.dataTransfer.files?.[0] ?? null);
          }}
          className="wc-drop cursor-pointer rounded-[22px] border-[1.5px] border-dashed border-[rgba(139,124,246,0.5)] px-7 py-[46px] text-center"
          style={{
            background: "linear-gradient(160deg, rgba(34,28,62,0.6), rgba(20,24,38,0.6))",
          }}
        >
          <div className="mx-auto mb-[18px] flex h-14 w-14 items-center justify-center rounded-2xl bg-[rgba(139,124,246,0.16)]">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4M12 4l-5 5M12 4l5 5" />
              <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
            </svg>
          </div>
          <div className="mb-[7px] text-[16px] font-bold">카드 내역 파일을 올려줘</div>
          <div className="text-[13.5px] text-[#7b84a0]">
            CSV · 엑셀 파일을 끌어다 놓거나 클릭해서 선택
          </div>
        </div>

        {/* 구분선 */}
        <div className="my-[22px] flex items-center gap-3.5">
          <div className="h-px flex-1 bg-white/[0.07]" />
          <div className="text-xs text-[#5f6885]">또는</div>
          <div className="h-px flex-1 bg-white/[0.07]" />
        </div>

        {/* 샘플 버튼 */}
        <button
          onClick={() => onStart(null)}
          disabled={loading}
          className="wc-primary w-full rounded-2xl bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] p-4 text-[15px] font-bold text-white disabled:opacity-60"
          style={{ boxShadow: "0 10px 30px rgba(124,92,246,0.35)" }}
        >
          {loading ? "김티가 내역 까보는 중..." : "샘플 데이터로 바로 둘러보기"}
        </button>

        {error && (
          <p className="mt-4 text-center text-[13px] text-rose-300">
            {error} — FastAPI 백엔드(127.0.0.1:8000)가 실행 중인지 확인하세요.
          </p>
        )}

        <p className="m-0 mt-[18px] text-center text-xs text-[#5f6885]">
          업로드한 내역은 분석에만 쓰이고 저장되지 않아.
        </p>
      </div>
    </div>
  );
}
