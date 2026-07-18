import type { Metadata } from "next";
import { GuanxiangApp } from "./GuanxiangApp";

export const metadata: Metadata = {
  title: "观象 · 寂然不动，感而遂通天下之故",
  description: "写下具体所问，依确定性排盘读懂本卦、互卦、变卦与动爻。",
};

export default function Home() {
  return <GuanxiangApp />;
}
