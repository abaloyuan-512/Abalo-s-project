import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://guanxiang-abalo.abaloyuan.chatgpt.site"),
  title: "观象 · 寂然不动，感而遂通天下之故",
  description: "写下具体所问，依确定性排盘读懂本卦、互卦、变卦与动爻，再把方向放回现实验证。",
  openGraph: {
    title: "观象 · 寂然不动，感而遂通天下之故",
    description: "写下具体所问，读懂卦从何来，也看清当下可借之力与当慎之处。",
    images: [{ url: "/og.png", width: 1536, height: 1024, alt: "观象宋韵分享封面" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "观象 · 寂然不动，感而遂通天下之故",
    description: "写下具体所问，读懂卦从何来，也看清当下可借之力与当慎之处。",
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
