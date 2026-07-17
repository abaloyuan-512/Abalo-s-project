import type { Metadata } from "next";
import { GuanxiangApp } from "./GuanxiangApp";

export const metadata: Metadata = {
  title: "观象 · 在变化之中，看见清晰的方向",
  description: "以确定性排盘呈现卦象结构，陪你理解原因、影响与可以落实的下一步。",
};

export default function Home() {
  return <GuanxiangApp />;
}
