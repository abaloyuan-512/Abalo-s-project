import type { Metadata } from "next";
import { OwnerPreviewApp } from "./OwnerPreviewApp";

export const metadata: Metadata = {
  title: "观象 · 新版解读私有体验",
  description: "仅供所有者校准新版解读，不替代现有观象版本。",
  robots: { index: false, follow: false },
};

export default function OwnerPreviewPage() {
  return <OwnerPreviewApp />;
}
