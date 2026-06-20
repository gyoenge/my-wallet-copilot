"use client";

import { useEffect, useRef, useState } from "react";

import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const SUGGESTIONS = [
  "내가 가장 돈을 많이 쓰는 요일은?",
  "배달비 30% 줄이면 얼마 절약돼?",
  "지난달 대비 뭐가 늘었어?",
  "카테고리별로 얼마 썼어?",
];

export default function Chat({ sessionId }: { sessionId: string | null }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || !sessionId || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "" }]);

    try {
      await streamChat(
        sessionId,
        q,
        (token) =>
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = {
              role: "assistant",
              content: next[next.length - 1].content + token,
            };
            return next;
          }),
        (err) =>
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = { role: "assistant", content: `⚠️ ${err}` };
            return next;
          }),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sticky top-7 flex min-h-[620px] flex-col rounded-[22px] border border-white/[0.06] bg-[rgba(20,24,38,0.7)]" style={{ height: "calc(100vh - 56px)" }}>
      {/* 헤더 */}
      <div className="flex items-center gap-3 border-b border-white/[0.06] px-[22px] py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#8b7cf6] to-[#5b8def] text-[16px] font-extrabold text-white">
          T
        </div>
        <div>
          <div className="text-[16px] font-bold">김티(T)</div>
          <div className="text-[12.5px] text-[#9aa3bd]">팩폭 전문 현실 절친</div>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div ref={scrollRef} className="flex flex-1 flex-col gap-3.5 overflow-y-auto p-[22px]">
        <div className="text-[15px] leading-[1.6] text-[#d7dcec]">
          카드 내역에 대해 뭐든 물어봐. 숫자는 내가 직접 까보고 답할게.
        </div>
        <div className="flex flex-wrap gap-[9px]">
          {SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              onClick={() => send(sug)}
              disabled={!sessionId || busy}
              className="wc-chip rounded-[11px] border border-white/10 bg-white/[0.04] px-3.5 py-[9px] text-[13px] text-[#cfd5e8] disabled:opacity-50"
            >
              {sug}
            </button>
          ))}
        </div>

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex flex-col items-end">
              <div
                className="max-w-[84%] rounded-[15px] px-[15px] py-[11px] text-[14.5px] leading-[1.6] text-white"
                style={{ background: "linear-gradient(135deg,#8b7cf6,#6d5ef0)", borderBottomRightRadius: 5 }}
              >
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="flex flex-col items-start">
              <div
                className="max-w-[84%] whitespace-pre-wrap rounded-[15px] bg-white/[0.06] px-[15px] py-[11px] text-[14.5px] leading-[1.6] text-[#e3e7f3]"
                style={{ borderBottomLeftRadius: 5 }}
              >
                {m.content || <span className="text-[#7b84a0]">…</span>}
              </div>
            </div>
          ),
        )}
      </div>

      {/* 입력 */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-3 border-t border-white/[0.06] px-[18px] py-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={sessionId ? "질문을 입력하세요" : "데이터 로딩 중..."}
          disabled={!sessionId || busy}
          className="flex-1 rounded-[13px] border border-white/10 bg-white/[0.04] px-4 py-[13px] text-[14px] text-[#e9ecf5] outline-none placeholder:text-[#5f6885] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!sessionId || busy || !input.trim()}
          className="rounded-[13px] bg-gradient-to-br from-[#8b7cf6] to-[#6d5ef0] px-[22px] text-[14px] font-bold text-white disabled:opacity-40"
        >
          {busy ? "…" : "전송"}
        </button>
      </form>
    </div>
  );
}
