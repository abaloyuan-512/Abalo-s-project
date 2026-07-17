import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://guanxiang-abalo.abaloyuan.chatgpt.site"),
  title: "观象 · 在变化之中，看见清晰的方向",
  description: "以确定性排盘呈现卦象结构，陪你理解原因、影响与可以落实的下一步。",
  openGraph: {
    title: "观象 · 在变化之中，看见清晰的方向",
    description: "以确定性排盘呈现卦象结构，陪你理解原因、影响与可以落实的下一步。",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "观象水墨金色分享封面" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "观象 · 在变化之中，看见清晰的方向",
    description: "以确定性排盘呈现卦象结构，陪你理解原因、影响与可以落实的下一步。",
    images: ["/og.png"],
  },
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
