import type { Metadata, Viewport } from "next";
import "./globals.css";
import { MobileScrollPetal } from "./MobileScrollPetal";
import { PwaRuntime } from "./PwaRuntime";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.GUANXIANG_PUBLIC_ORIGIN || "https://guanxiang-mobile.abaloyuan.chatgpt.site"),
  applicationName: "观象",
  manifest: "/manifest-v2.webmanifest",
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
    icon: [
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/icon-192.png", type: "image/png", sizes: "192x192" }],
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "观象",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#f2ead9",
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <head><meta name="supported-color-schemes" content="light" /></head>
      <body>{children}<MobileScrollPetal /><PwaRuntime /></body>
    </html>
  );
}
