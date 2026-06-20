"use client";

import { useEffect, useRef, useState } from "react";

import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import TLogo from "./TLogo";

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
    <div className="flex h-full min-h-[560px] flex-col rounded-[22px] border border-[#ebedf3] bg-white shadow-[0_1px_3px_rgba(20,20,50,0.04)]">
      {/* 헤더 */}
      <div className="flex items-center gap-3 border-b border-[#eef0f5] px-[22px] py-5">
        <TLogo size={40} radius={12} glow={false} />
        <div>
          <div className="text-[16px] font-bold text-[#1c1f2b]">세이비</div>
          <div className="text-[12.5px] text-[#8a92a6]">새는 돈을 찾아주는 지갑 수호자</div>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div ref={scrollRef} className="flex flex-1 flex-col gap-3.5 overflow-y-auto p-[22px]">
        <div className="text-[15px] leading-[1.6] text-[#3c4252]">
          카드 내역에 대해 뭐든 물어봐. 숫자는 내가 직접 까보고 답할게.
        </div>
        <div className="flex flex-wrap gap-[9px]">
          {SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              onClick={() => send(sug)}
              disabled={!sessionId || busy}
              className="wc-chip rounded-[11px] border border-[#e5e7ef] bg-white px-3.5 py-[9px] text-[13px] text-[#4b5263] disabled:opacity-50"
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
                className="max-w-[84%] whitespace-pre-wrap rounded-[15px] bg-[#f1f2f6] px-[15px] py-[11px] text-[14.5px] leading-[1.6] text-[#2a2d38]"
                style={{ borderBottomLeftRadius: 5 }}
              >
                {m.content || <span className="text-[#9aa1b2]">…</span>}
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
        className="flex gap-3 border-t border-[#eef0f5] px-[18px] py-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={sessionId ? "질문을 입력하세요" : "데이터 로딩 중..."}
          disabled={!sessionId || busy}
          className="flex-1 rounded-[13px] border border-[#e2e5ee] bg-[#f7f8fb] px-4 py-[13px] text-[14px] text-[#1c1f2b] outline-none placeholder:text-[#9aa1b2] disabled:opacity-50"
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
