"use client";

import { useRef } from "react";

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
    <div className="flex min-h-screen items-center justify-center px-8 py-12">
      <div
        className="flex w-full max-w-[1080px] flex-col items-center gap-12 md:flex-row md:gap-[60px]"
        style={{ animation: "wcFade 0.6s ease both" }}
      >
        {/* 좌: 대형 캐릭터 */}
        <div className="flex flex-none flex-col items-center gap-5">
          <div className="relative" style={{ animation: "wcFloat 5s ease-in-out infinite" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/savy_character.png"
              alt="세이비"
              className="relative h-[300px] w-[300px] rounded-full object-cover"
            />
          </div>
          <div className="text-[13px] font-bold uppercase tracking-[0.16em] text-[#7c5cf6]">
            My Wallet Copilot
          </div>
        </div>

        {/* 우: 말풍선 + 업로드 */}
        <div className="flex w-full min-w-0 max-w-[540px] flex-col gap-[22px]">
          {/* 말풍선 */}
          <div
            className="relative self-start rounded-[22px] border border-[#ebe7fb] bg-white px-7 py-6"
            style={{
              borderBottomLeftRadius: 6,
              boxShadow: "0 16px 38px rgba(80,70,160,0.12)",
              animation: "wcPop 0.5s 0.15s ease both",
            }}
          >
            <div
              className="absolute h-[17px] w-[17px] rotate-45 bg-white"
              style={{
                left: -8,
                top: 30,
                borderLeft: "1px solid #ebe7fb",
                borderBottom: "1px solid #ebe7fb",
              }}
            />
            <h1 className="m-0 mb-2.5 text-[28px] font-extrabold leading-[1.3] text-[#1c1f2b]">
              안녕, 나는 <span className="text-[#7c5cf6]">세이비</span>야
            </h1>
            <p className="m-0 text-[15.5px] leading-[1.7] text-[#6b7280]">
              새는 돈을 찾아주는 지갑 수호자.
              <br />
              카드 내역만 올리면 소비 습관을 분석해줄게.
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
            className="wc-drop cursor-pointer rounded-[20px] border-[1.5px] border-dashed border-[rgba(124,92,246,0.45)] bg-[#faf9ff] px-[26px] py-[34px] text-center"
          >
            <div className="mx-auto mb-3.5 flex h-[52px] w-[52px] items-center justify-center rounded-[15px] bg-[#efeaff]">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7c5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 16V4M12 4l-5 5M12 4l5 5" />
                <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
              </svg>
            </div>
            <div className="mb-1.5 text-[15.5px] font-bold text-[#1c1f2b]">카드 내역 파일을 올려줘</div>
            <div className="text-[13px] text-[#9aa1b2]">CSV · 엑셀 파일을 끌어다 놓거나 클릭해서 선택</div>
          </div>

          {/* 구분선 */}
          <div className="flex items-center gap-3.5">
            <div className="h-px flex-1 bg-[#e6e8ef]" />
            <div className="text-xs text-[#aab0c0]">또는</div>
            <div className="h-px flex-1 bg-[#e6e8ef]" />
          </div>

          {/* 샘플 버튼 */}
          <button
            onClick={() => onStart(null)}
            disabled={loading}
            className="wc-primary w-full rounded-[15px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] p-[15px] text-[15px] font-bold text-white disabled:opacity-60"
            style={{ boxShadow: "0 10px 26px rgba(124,92,246,0.3)" }}
          >
            {loading ? "세이비가 내역 분석하는 중..." : "샘플 데이터로 바로 둘러보기"}
          </button>

          {error && (
            <p className="m-0 text-[13px] text-rose-500">
              {error} — FastAPI 백엔드(127.0.0.1:8000)가 실행 중인지 확인하세요.
            </p>
          )}

          <p className="m-0 -mt-1.5 text-xs text-[#aab0c0]">
            업로드한 내역은 분석에만 쓰이고 저장되지 않아.
          </p>
        </div>
      </div>
    </div>
  );
}
