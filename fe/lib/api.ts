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

/**
 * POST /api/analyze 의 SSE를 읽어 분석 단계(step)를 콜백하고,
 * 완료(done) 시 session_id를 반환한다. 실패 시 null.
 */
export async function streamAnalyze(
  file: File | null,
  onStep: (text: string) => void,
  onError?: (msg: string) => void,
): Promise<string | null> {
  const form = new FormData();
  if (file) form.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: form });
  } catch {
    onError?.("백엔드에 연결할 수 없습니다. FastAPI(127.0.0.1:8000)가 실행 중인지 확인하세요.");
    return null;
  }
  if (!res.ok || !res.body) {
    onError?.((await res.json().catch(() => ({})))?.detail ?? "분석 요청 실패");
    return null;
  }

  const reader = res.body.getReader();
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
        const data = dataLines.join("\n");
        if (eventType === "step") onStep(data);
        else if (eventType === "done") return data;
        else if (eventType === "error") {
          onError?.(data);
          return null;
        }
      }
    }
  } catch {
    onError?.("분석 중 연결이 끊겼습니다. 다시 시도해 주세요.");
  }
  return null;
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
