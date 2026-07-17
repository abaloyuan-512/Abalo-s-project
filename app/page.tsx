import type { Metadata } from "next";
import { GuanxiangApp } from "./GuanxiangApp";

export const metadata: Metadata = {
  title: "观象 · 传统文化决策辅助",
  description: "输入三个数字，查看卦象结构、判断依据和现实行动建议。",
};

export default function Home() {
  return <GuanxiangApp />;
}
