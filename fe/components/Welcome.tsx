"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { streamAnalyze, streamFinalize, type ReviewData } from "@/lib/api";

const SESSION_KEY = "wallet_session_id";

export default function Welcome() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [panel, setPanel] = useState<null | "help" | "explore">(null);
  // 닫히는 동안에도 내용이 유지되도록 마지막으로 연 패널을 기억한다.
  const lastView = useRef<"help" | "explore">("help");
  if (panel) lastView.current = panel;
  const view = panel ?? lastView.current;

  // 분석 진행(스트리밍) 상태
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [steps, setSteps] = useState<string[]>([]);
  // 카테고리 검토(HITL) 상태
  const [review, setReview] = useState<ReviewData | null>(null);
  const [edited, setEdited] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<"amount" | "date" | "category">("amount");
  const changedCount = review
    ? review.merchants.filter(
        (m) => edited[m.merchant] !== undefined && edited[m.merchant] !== m.category,
      ).length
    : 0;

  async function start(fileToAnalyze: File | null) {
    setError(null);
    setSteps([]);
    setReview(null);
    setEdited({});
    setPanel(null);
    setLoading(true);
    await streamAnalyze(
      fileToAnalyze,
      (s) => setSteps((prev) => [...prev, s]),
      (data) => {
        setReview(data); // 분류 결과 검토 화면으로 전환
        setLoading(false);
      },
      (msg) => {
        setError(msg);
        setLoading(false);
      },
    );
  }

  async function confirmReview() {
    if (!review) return;
    const sessionId = review.session_id;
    setReview(null);
    setSteps([]);
    setLoading(true);
    const sid = await streamFinalize(
      sessionId,
      edited,
      (s) => setSteps((prev) => [...prev, s]),
      (msg) => {
        setError(msg);
        setLoading(false);
      },
    );
    if (sid) {
      localStorage.setItem(SESSION_KEY, sid);
      router.push("/dashboard");
    } else {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* 슬림 상단 바: 좌 브랜드 / 우 도움말·로그인 */}
      <header className="flex items-center justify-between px-6 py-6 md:px-10">
        <Link href="/" aria-label="홈으로" className="flex items-center transition hover:opacity-80">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/savy_logo.png" alt="SAVY: My Wallet Copilot" className="h-[46px] w-auto" />
        </Link>
        <nav className="flex items-center gap-2.5">
          <button
            onClick={() => setPanel("help")}
            className="rounded-[12px] px-[18px] py-3 text-[16px] font-medium text-[#4b5263] transition hover:bg-[#eef0f5]"
          >
            도움말
          </button>
          <button
            onClick={() => setPanel("explore")}
            className="rounded-[12px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] py-3 text-[16px] font-semibold text-white transition hover:opacity-90"
          >
            둘러보기
          </button>
        </nav>
      </header>

      {review ? (
        <div className="flex flex-1 items-center justify-center px-8 py-8">
          <div className="flex w-full max-w-[680px] flex-col gap-5" style={{ animation: "wcFade 0.4s ease both" }}>
            <div className="flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/savy_character.png" alt="세이비" className="h-12 w-12 rounded-full object-cover" />
              <div>
                <div className="text-[19px] font-extrabold text-[#1c1f2b]">카테고리 분류를 확인해 주세요</div>
                <div className="text-[14px] text-[#8a92a6]">잘못 분류된 가맹점이 있으면 카테고리를 바꿔주세요.</div>
              </div>
            </div>
            {/* 정렬 토글 */}
            <div className="flex gap-1.5">
              {(
                [
                  ["amount", "금액순"],
                  ["date", "날짜순"],
                  ["category", "유형별"],
                ] as const
              ).map(([k, label]) => (
                <button
                  key={k}
                  onClick={() => setSort(k)}
                  className={`rounded-[10px] px-3.5 py-1.5 text-[13px] font-semibold transition ${
                    sort === k ? "bg-[#efeaff] text-[#7c5cf6]" : "text-[#8a92a6] hover:bg-[#f3f4f8]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="max-h-[52vh] overflow-y-auto rounded-[18px] border border-[#ebedf3] bg-white">
              {[...review.merchants]
                .sort((a, b) =>
                  sort === "date"
                    ? b.date.localeCompare(a.date) || b.amount - a.amount
                    : sort === "category"
                      ? a.category.localeCompare(b.category) || b.amount - a.amount
                      : b.amount - a.amount,
                )
                .map((m) => {
                  const changed =
                    edited[m.merchant] !== undefined && edited[m.merchant] !== m.category;
                  return (
                  <div
                    key={m.merchant}
                    className={`flex items-center justify-between gap-3 border-b border-[#f0f1f5] px-4 py-2.5 last:border-0 ${changed ? "bg-[#f6f2ff]" : ""}`}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate text-[14px] text-[#1c1f2b]">{m.merchant}</span>
                        {changed && (
                          <span className="flex-none rounded-full bg-[#efeaff] px-2 py-0.5 text-[10px] font-bold text-[#7c5cf6]">
                            변경
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#9aa1b2]">
                        {m.date} · {Math.round(m.amount).toLocaleString()}원
                      </div>
                    </div>
                  <select
                    value={edited[m.merchant] ?? m.category}
                    onChange={(e) =>
                      setEdited((prev) => ({ ...prev, [m.merchant]: e.target.value }))
                    }
                    className={`flex-none rounded-[10px] border bg-[#f7f8fb] px-2.5 py-1.5 text-[13px] text-[#3c4252] outline-none focus:border-[#a78bfa] ${changed ? "border-[#a78bfa]" : "border-[#e2e5ee]"}`}
                  >
                    {review.categories.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                  );
                })}
            </div>
            <button
              onClick={confirmReview}
              className="wc-primary w-full rounded-[16px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] p-[16px] text-[16px] font-bold text-white"
              style={{ boxShadow: "0 10px 26px rgba(124,92,246,0.3)" }}
            >
              {changedCount > 0 ? `이대로 분석하기 (${changedCount}건 수정)` : "이대로 분석하기"}
            </button>
          </div>
        </div>
      ) : loading ? (
        <div className="flex flex-1 items-center justify-center px-8 pb-[10vh]">
          <div className="flex flex-col items-center gap-7" style={{ animation: "wcFade 0.4s ease both" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/savy_character.png"
              alt="세이비"
              className="h-[180px] w-[180px] rounded-full object-cover"
              style={{ animation: "wcFloat 4s ease-in-out infinite" }}
            />
            <div className="text-[20px] font-extrabold text-[#1c1f2b]">세이비가 분석하고 있어요</div>
            <ul className="flex w-[330px] max-w-[80vw] flex-col gap-2.5">
              {steps.map((s, i) => {
                const done = i < steps.length - 1;
                return (
                  <li
                    key={i}
                    className="flex items-center gap-2.5 text-[14px]"
                    style={{ animation: "wcFade 0.3s ease both" }}
                  >
                    {done ? (
                      <span className="flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full bg-[#7c5cf6] text-[10px] font-bold text-white">
                        ✓
                      </span>
                    ) : (
                      <span className="h-[18px] w-[18px] flex-none animate-spin rounded-full border-2 border-[#e4ddff] border-t-[#7c5cf6]" />
                    )}
                    <span className={done ? "text-[#9aa1b2]" : "font-semibold text-[#1c1f2b]"}>{s}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      ) : (
      <div className="relative flex flex-1 overflow-hidden">
        <div
          className="flex flex-1 items-center justify-center px-8 pb-[16vh] transition-[margin] duration-300 ease-out"
          style={{ marginRight: panel ? 450 : 0 }}
        >
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
            onClick={() => file && start(file)}
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

        {/* 우측 사이드바 — 세로 전체 높이, 오른쪽에서 슬라이드 인 */}
        <aside
          className="absolute top-0 flex h-full w-[450px] max-w-[90vw] flex-col overflow-y-auto border-l border-[#ebedf3] bg-white p-7 shadow-[-8px_0_40px_rgba(20,20,50,0.10)]"
          style={{
            right: panel ? 0 : -480,
            opacity: panel ? 1 : 0,
            transition: "right 0.3s ease, opacity 0.3s ease",
          }}
        >
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-[20px] font-extrabold text-[#1c1f2b]">
                {view === "help" ? "도움말" : "둘러보기"}
              </h2>
              <button
                onClick={() => setPanel(null)}
                aria-label="닫기"
                className="rounded-[10px] px-2.5 py-1.5 text-[18px] text-[#8a92a6] transition hover:bg-[#eef0f5]"
              >
                ✕
              </button>
            </div>

            {view === "help" ? (
              <div className="flex flex-col gap-5 text-[14.5px] leading-[1.7] text-[#3c4252]">
                <section>
                  <h3 className="mb-1.5 text-[15px] font-bold text-[#1c1f2b]">시작하기</h3>
                  <p className="m-0">
                    카드 내역 파일(CSV·엑셀)을 올린 뒤 <b>분석하기</b>를 누르면 대시보드가 열려요.
                    파일이 없다면 <b>둘러보기</b>에서 샘플로 체험할 수 있어요.
                  </p>
                </section>
                <section>
                  <h3 className="mb-1.5 text-[15px] font-bold text-[#1c1f2b]">무엇을 해주나요</h3>
                  <p className="m-0">
                    카테고리·요일·시간대별 지출을 시각화하고, 소비 건강 점수와 절약 포인트를 알려줘요.
                    세이비에게 자연어로 질문하면 실제 숫자로 답해줘요.
                  </p>
                </section>
                <section>
                  <h3 className="mb-1.5 text-[15px] font-bold text-[#1c1f2b]">개인정보</h3>
                  <p className="m-0">업로드한 내역은 분석에만 쓰이고 저장되지 않아요.</p>
                </section>
              </div>
            ) : (
              <div className="flex flex-1 flex-col gap-5 text-[14.5px] leading-[1.7] text-[#3c4252]">
                <p className="m-0">
                  파일이 없어도 괜찮아요. 샘플 카드 내역으로 세이비의 분석 대시보드와 채팅을 바로 체험해볼 수 있어요.
                </p>
                <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
                  <li className="flex gap-2"><span className="text-[#7c5cf6]">•</span><span>카테고리·월·요일·시간대 지출 차트</span></li>
                  <li className="flex gap-2"><span className="text-[#7c5cf6]">•</span><span>소비 건강 점수와 한 줄 진단</span></li>
                  <li className="flex gap-2"><span className="text-[#7c5cf6]">•</span><span>세이비와 자연어 채팅</span></li>
                </ul>
                <button
                  onClick={() => start(null)}
                  disabled={loading}
                  className="wc-primary mt-1 w-full rounded-[14px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] p-[15px] text-[15px] font-bold text-white disabled:opacity-60"
                  style={{ boxShadow: "0 10px 26px rgba(124,92,246,0.3)" }}
                >
                  {loading ? "세이비가 내역 분석하는 중..." : "샘플로 둘러보기"}
                </button>
              </div>
            )}
        </aside>
      </div>
      )}
    </div>
  );
}
