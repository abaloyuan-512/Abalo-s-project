import type { Metadata } from "next";
import { OwnerPreviewApp } from "./OwnerPreviewApp";

export const metadata: Metadata = {
  title: "观象 · 新版解读 Beta",
  description: "把已确认的现实信息与卦象分开，得到可观察、可转向的新版解读。",
  robots: { index: false, follow: false },
};

export default function OwnerPreviewPage() {
  return <OwnerPreviewApp />;
}
