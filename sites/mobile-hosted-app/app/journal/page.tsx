import type { Metadata } from "next";
import { JournalApp } from "../JournalApp";

export const metadata: Metadata = {
  title: "观事簿 · 观象",
  description: "保存每一次观象，在现实出现新证据后回来复盘。",
};

export default function JournalPage() {
  return <JournalApp />;
}
