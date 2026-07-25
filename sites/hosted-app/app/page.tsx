import type { Metadata } from "next";
import { GuanxiangApp } from "./GuanxiangApp";

export const metadata: Metadata = {
  title: "观象 · 寂然不动，感而遂通天下之故",
  description: "用三分钟，把一件拿不准的事整理成可以验证的下一步。",
};

export default function Home() {
  return <GuanxiangApp />;
}
