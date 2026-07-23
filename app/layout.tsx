import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://guanxiang-abalo.abaloyuan.chatgpt.site"),
  title: "观象 · 寂然不动，感而遂通天下之故",
  description: "用三分钟，把一件拿不准的事整理成可以验证的下一步，并在现实出现新证据后回来复盘。",
  openGraph: {
    title: "观象 · 寂然不动，感而遂通天下之故",
    description: "把一件拿不准的事整理成可以验证的下一步，并在后来回来复盘。",
    images: [{ url: "/og-v2.png", width: 1536, height: 1024, alt: "观象 · 把一件拿不准的事整理成可以验证的下一步" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "观象 · 寂然不动，感而遂通天下之故",
    description: "把一件拿不准的事整理成可以验证的下一步，并在后来回来复盘。",
    images: ["/og-v2.png"],
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
