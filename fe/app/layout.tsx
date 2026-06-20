import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SAVY: My Wallet Copilot",
  description: "카드 소비 분석 AI 에이전트 — 세이비",
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
