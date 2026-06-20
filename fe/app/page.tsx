"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import Welcome from "@/components/Welcome";
import { uploadFile } from "@/lib/api";

const SESSION_KEY = "wallet_session_id";

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start(file: File | null) {
    setLoading(true);
    setError(null);
    try {
      const { session_id } = await uploadFile(file);
      localStorage.setItem(SESSION_KEY, session_id);
      router.push("/dashboard");
      // 네비게이션 중 화면 유지를 위해 loading은 해제하지 않는다.
    } catch (e) {
      setError(e instanceof Error ? e.message : "백엔드에 연결할 수 없습니다.");
      setLoading(false);
    }
  }

  return <Welcome onStart={start} loading={loading} error={error} />;
}
