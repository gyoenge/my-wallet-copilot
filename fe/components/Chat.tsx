"use client";

import { useEffect, useRef, useState } from "react";

import { streamChat } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";
import Avatar from "./Avatar";

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
    <div className="flex h-[600px] flex-col rounded-3xl border border-white/10 bg-white/[0.03]">
      <div className="flex items-center gap-3 border-b border-white/10 px-5 py-4">
        <Avatar size={40} />
        <div>
          <div className="text-sm font-extrabold text-white">김티(T)</div>
          <div className="text-xs text-accent">팩폭 전문 현실 절친</div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="space-y-3">
            <p className="text-sm text-slate-400">
              카드 내역에 대해 뭐든 물어봐. 숫자는 내가 직접 까보고 답할게.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition hover:border-accent/50 hover:text-white"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="ml-auto max-w-[80%] rounded-2xl rounded-br-md bg-white px-4 py-2.5 text-sm font-medium text-slate-900">
              {m.content}
            </div>
          ) : (
            <div key={i} className="flex max-w-[88%] gap-3">
              <Avatar size={32} />
              <div className="whitespace-pre-wrap rounded-2xl rounded-tl-md border border-white/10 bg-white/[0.04] px-4 py-2.5 text-sm leading-relaxed text-slate-100">
                {m.content || <span className="text-slate-500">…</span>}
              </div>
            </div>
          ),
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex gap-2 border-t border-white/10 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={sessionId ? "질문을 입력하세요" : "데이터 로딩 중..."}
          disabled={!sessionId || busy}
          className="flex-1 rounded-2xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:border-accent/60 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!sessionId || busy || !input.trim()}
          className="rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 px-5 py-2.5 text-sm font-bold text-white transition hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "…" : "전송"}
        </button>
      </form>
    </div>
  );
}
