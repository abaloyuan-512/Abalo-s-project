import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://guanxiang-abalo.abaloyuan.chatgpt.site"),
  title: "观象 · 把心里的疑问，问得更清楚一点",
  description: "写下具体所问，以确定性排盘看清方向、现实信号与下一步。",
  openGraph: {
    title: "观象 · 把心里的疑问，问得更清楚一点",
    description: "写下具体所问，以确定性排盘看清方向、现实信号与下一步。",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "观象宋韵分享封面" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "观象 · 把心里的疑问，问得更清楚一点",
    description: "写下具体所问，以确定性排盘看清方向、现实信号与下一步。",
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
