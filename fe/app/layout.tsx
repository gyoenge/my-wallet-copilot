import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "My Wallet Copilot",
  description: "카드 소비 분석 AI 에이전트 — 김티(T)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
