"use client";

import { useRef, useState } from "react";
import Link from "next/link";

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
  const [file, setFile] = useState<File | null>(null);

  return (
    <div className="flex min-h-screen flex-col">
      {/* 슬림 상단 바: 좌 브랜드 / 우 도움말·로그인 */}
      <header className="flex items-center justify-between px-6 py-6 md:px-10">
        <Link href="/" aria-label="홈으로" className="flex items-center transition hover:opacity-80">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/savy_logo.png" alt="SAVY: My Wallet Copilot" className="h-[46px] w-auto" />
        </Link>
        <nav className="flex items-center gap-2.5">
          <button className="rounded-[12px] px-[18px] py-3 text-[16px] font-medium text-[#4b5263] transition hover:bg-[#eef0f5]">
            도움말
          </button>
          <button
            onClick={() => onStart(null)}
            disabled={loading}
            className="rounded-[12px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] py-3 text-[16px] font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
          >
            둘러보기
          </button>
        </nav>
      </header>

      <div className="flex flex-1 items-center justify-center px-8 pb-[16vh]">
        <div
          className="flex w-full max-w-[1080px] flex-col items-center gap-12 md:flex-row md:items-start md:gap-[60px]"
          style={{ animation: "wcFade 0.6s ease both" }}
        >
        {/* 좌: 대형 캐릭터 */}
        <div className="flex flex-none flex-col items-center">
          <div className="relative" style={{ animation: "wcFloat 5s ease-in-out infinite" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/savy_character.png"
              alt="세이비"
              className="relative h-[340px] w-[340px] rounded-full object-cover"
            />
          </div>
        </div>

        {/* 우: 말풍선 + 업로드 (말풍선 꼬리를 캐릭터 입/중심 높이에 맞추려 데스크톱에서 아래로 내림) */}
        <div className="flex w-full min-w-0 max-w-[600px] flex-col gap-[24px] md:mt-[104px]">
          {/* 말풍선 */}
          <div
            className="relative self-start rounded-[24px] border border-[#ebe7fb] bg-white px-8 py-7"
            style={{
              borderBottomLeftRadius: 6,
              boxShadow: "0 16px 38px rgba(80,70,160,0.12)",
              animation: "wcPop 0.5s 0.15s ease both",
            }}
          >
            <div
              className="absolute h-[19px] w-[19px] rotate-45 bg-white"
              style={{
                left: -9,
                top: 34,
                borderLeft: "1px solid #ebe7fb",
                borderBottom: "1px solid #ebe7fb",
              }}
            />
            <h1 className="m-0 mb-3 text-[32px] font-extrabold leading-[1.3] text-[#1c1f2b]">
              안녕, 나는 <span className="text-[#7c5cf6]">세이비</span>야
            </h1>
            <p className="m-0 text-[17px] leading-[1.7] text-[#6b7280]">
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
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <div
            onClick={() => !loading && fileRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!loading) setFile(e.dataTransfer.files?.[0] ?? null);
            }}
            className="wc-drop cursor-pointer rounded-[22px] border-[1.5px] border-dashed border-[rgba(124,92,246,0.45)] bg-[#faf9ff] px-[30px] py-[40px] text-center"
          >
            <div className="mx-auto mb-4 flex h-[60px] w-[60px] items-center justify-center rounded-[17px] bg-[#efeaff]">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#7c5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 16V4M12 4l-5 5M12 4l5 5" />
                <path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" />
              </svg>
            </div>
            {file ? (
              <>
                <div className="mb-1.5 text-[17.5px] font-bold text-[#7c5cf6]">{file.name}</div>
                <div className="text-[14px] text-[#9aa1b2]">다른 파일을 올리려면 다시 클릭</div>
              </>
            ) : (
              <>
                <div className="mb-1.5 text-[17.5px] font-bold text-[#1c1f2b]">카드 내역 파일을 올려줘</div>
                <div className="text-[14px] text-[#9aa1b2]">CSV · 엑셀 파일을 끌어다 놓거나 클릭해서 선택</div>
              </>
            )}
          </div>

          {/* 분석 버튼 — 파일이 업로드되어야 활성화 */}
          <button
            onClick={() => file && onStart(file)}
            disabled={!file || loading}
            className="wc-primary w-full rounded-[16px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] p-[18px] text-[16.5px] font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
            style={{ boxShadow: "0 10px 26px rgba(124,92,246,0.3)" }}
          >
            {loading ? "세이비가 내역 분석하는 중..." : "분석하기"}
          </button>

          {error && (
            <p className="m-0 text-[14px] text-rose-500">
              {error} — FastAPI 백엔드(127.0.0.1:8000)가 실행 중인지 확인하세요.
            </p>
          )}

          <p className="m-0 -mt-1.5 text-[13px] text-[#aab0c0]">
            업로드한 내역은 분석에만 쓰이고 저장되지 않아.
          </p>
        </div>
      </div>
      </div>
    </div>
  );
}
