import type { Metadata } from "next";
import { GuanxiangApp } from "./GuanxiangApp";

export const metadata: Metadata = {
  title: "观象 · 把心里的疑问，问得更清楚一点",
  description: "写下具体所问，以确定性排盘看清方向、现实信号与下一步。",
};

export default function Home() {
  return <GuanxiangApp />;
}
