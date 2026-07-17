import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "观象 · 传统文化决策辅助",
  description: "通过固定规则排盘与导师式导读，帮助你把问题放回清晰的结构里。",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
