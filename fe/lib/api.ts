import type { Dashboard, Summary } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";

export async function uploadFile(
  file: File | null,
): Promise<{ session_id: string; summary: Summary }> {
  const form = new FormData();
  if (file) form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? "업로드 실패");
  return res.json();
}

export async function getDashboard(sessionId: string): Promise<Dashboard> {
  const res = await fetch(`${API_BASE}/api/dashboard/${sessionId}`);
  if (!res.ok) throw new Error("대시보드 로드 실패");
  return res.json();
}

export async function getHealth(): Promise<{ ok: boolean; has_api_key: boolean }> {
  const res = await fetch(`${API_BASE}/api/health`);
  return res.json();
}

export interface ReviewMerchant {
  merchant: string;
  category: string;
  suggested: string | null; // 검증가가 더 맞다고 본 대안 카테고리
  amount: number;
  count: number;
  date: string;
  confidence: number; // 0~1, 분류를 믿을 수 있는 정도
  uncertain: boolean; // 검증가가 '불확실'로 표시
  reason: string; // 신뢰도 판단 근거
}

export interface ReviewData {
  session_id: string;
  categories: string[];
  merchants: ReviewMerchant[];
  uncertain_count: number;
}

// 한 줄씩 오는 SSE 텍스트를 (event, data)로 파싱해 콜백한다. (CRLF 안전)
async function readSSE(
  res: Response,
  on: (event: string, data: string) => boolean | void,
  onError?: (msg: string) => void,
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";
      for (const evt of events) {
        let eventType = "message";
        const dataLines: string[] = [];
        for (const line of evt.split(/\r?\n/)) {
          if (line.startsWith("event:")) eventType = line.slice(6).trim();
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
        }
        if (on(eventType, dataLines.join("\n"))) return;
      }
    }
  } catch {
    onError?.("연결이 끊겼습니다. 다시 시도해 주세요.");
  }
}

/**
 * POST /api/analyze 의 SSE를 읽어 분석 단계(step)를 콜백하고,
 * 분류가 끝나면 review 이벤트로 검토 데이터를 콜백한다.
 */
export async function streamAnalyze(
  file: File | null,
  onStep: (text: string) => void,
  onReview: (data: ReviewData) => void,
  onError?: (msg: string) => void,
): Promise<void> {
  const form = new FormData();
  if (file) form.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
  } catch {
    onError?.("백엔드에 연결할 수 없습니다. FastAPI(127.0.0.1:8000)가 실행 중인지 확인하세요.");
    return;
  }
  if (!res.ok || !res.body) {
    onError?.((await res.json().catch(() => ({})))?.detail ?? "분석 요청 실패");
    return;
  }

  await readSSE(
    res,
    (event, data) => {
      if (event === "step") onStep(data);
      else if (event === "review") {
        try {
          onReview(JSON.parse(data) as ReviewData);
        } catch {
          onError?.("검토 데이터를 읽지 못했습니다.");
        }
        return true;
      } else if (event === "error") {
        onError?.(data);
        return true;
      }
    },
    onError,
  );
}

/**
 * POST /api/finalize 의 SSE를 읽어 남은 단계(step)를 콜백하고,
 * 완료(done) 시 session_id를 반환한다. 실패 시 null.
 */
export async function streamFinalize(
  sessionId: string,
  overrides: Record<string, string>,
  onStep: (text: string) => void,
  onError?: (msg: string) => void,
): Promise<string | null> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/finalize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, overrides }),
    });
  } catch {
    onError?.("백엔드에 연결할 수 없습니다.");
    return null;
  }
  if (!res.ok || !res.body) {
    onError?.((await res.json().catch(() => ({})))?.detail ?? "분석 요청 실패");
    return null;
  }

  let result: string | null = null;
  await readSSE(
    res,
    (event, data) => {
      if (event === "step") onStep(data);
      else if (event === "done") {
        result = data;
        return true;
      } else if (event === "error") {
        onError?.(data);
        return true;
      }
    },
    onError,
  );
  return result;
}

export interface DebateFact {
  id: string;
  text: string;
}
export interface DebateTurn {
  persona: string;
  name: string;
  text: string;
}
export interface DebateVerdict {
  consensus: string;
  tension: string;
  conclusion: string;
  actions: string[];
  confidence: number;
}

/**
 * POST /api/debate 의 SSE를 읽어 페르소나 토론을 단계별로 콜백한다.
 * facts(팩트시트) → turn(페르소나 발언 N회) → verdict(조정자 결론).
 */
export async function streamDebate(
  sessionId: string,
  question: string | null,
  cb: {
    onFacts: (facts: DebateFact[]) => void;
    onTurn: (turn: DebateTurn) => void;
    onVerdict: (verdict: DebateVerdict) => void;
    onError?: (msg: string) => void;
  },
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/debate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: question }),
    });
  } catch {
    cb.onError?.("백엔드에 연결할 수 없습니다. FastAPI(127.0.0.1:8000)가 실행 중인지 확인하세요.");
    return;
  }
  if (!res.ok || !res.body) {
    cb.onError?.((await res.json().catch(() => ({})))?.detail ?? "토론 요청 실패");
    return;
  }

  await readSSE(
    res,
    (event, data) => {
      try {
        if (event === "facts") cb.onFacts((JSON.parse(data) as { facts: DebateFact[] }).facts);
        else if (event === "turn") cb.onTurn(JSON.parse(data) as DebateTurn);
        else if (event === "verdict") cb.onVerdict(JSON.parse(data) as DebateVerdict);
        else if (event === "error") {
          cb.onError?.(data);
          return true;
        } else if (event === "done") return true;
      } catch {
        cb.onError?.("토론 데이터를 읽지 못했습니다.");
        return true;
      }
    },
    cb.onError,
  );
}

/**
 * POST /api/chat 의 SSE 스트림을 읽어 토큰 단위로 콜백한다.
 * EventSource는 GET만 지원하므로 fetch + ReadableStream으로 직접 파싱한다.
 */
export async function streamChat(
  sessionId: string,
  message: string,
  onToken: (text: string) => void,
  onError?: (msg: string) => void,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  } catch {
    // 연결 실패(백엔드 미실행 등)는 fetch가 예외를 던진다 — 반드시 잡아야
    // 채팅 말풍선이 무한 로딩에 멈추지 않는다.
    onError?.("백엔드에 연결할 수 없습니다. FastAPI(127.0.0.1:8000)가 실행 중인지 확인하세요.");
    return;
  }

  if (!res.ok || !res.body) {
    onError?.((await res.json().catch(() => ({})))?.detail ?? "요청 실패");
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE 이벤트는 빈 줄로 구분된다. sse-starlette는 CRLF(\r\n)를 쓰므로
      // \r\n / \n 양쪽을 모두 처리한다.
      const events = buffer.split(/\r?\n\r?\n/);
      buffer = events.pop() ?? "";

      for (const evt of events) {
        let eventType = "message";
        const dataLines: string[] = [];
        for (const line of evt.split(/\r?\n/)) {
          if (line.startsWith("event:")) eventType = line.slice(6).trim();
          // 한 이벤트의 여러 data: 줄은 줄바꿈으로 복원해야 마크다운 표/줄바꿈이 유지된다.
          else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
        }
        const data = dataLines.join("\n");
        if (eventType === "token") onToken(data);
        else if (eventType === "error") onError?.(data);
        else if (eventType === "done") return;
      }
    }
  } catch {
    onError?.("응답을 받는 중 연결이 끊겼습니다. 다시 시도해 주세요.");
  }
}
