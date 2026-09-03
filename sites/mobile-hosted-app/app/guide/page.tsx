import type { Metadata } from "next";
import Link from "next/link";
import { InfoLayout } from "../InfoLayout";

export const metadata: Metadata = { title: "如何使用 · 观象", description: "用四个步骤完成一次清楚、可复盘的观象。" };

export default function GuidePage() {
  return <InfoLayout eyebrow="使用引导" title="问得具体，才能回到现实验证" lead="一次观象通常需要一至三分钟。先写清所问与处境，再分清事实和未知，最后凭当下所感取三个整数。">
    <section><h2>第一步：只问一件事</h2><p>好的问题有明确对象、当前选择和现实范围。例如：“这次合作，我还应该继续投入吗？”</p><p>尽量避免“我的一生会怎样”“他到底爱不爱我”这类无法用现实行动和反馈验证的问题。</p></section>
    <section><h2>第二步：说明现在走到哪里</h2><p>领域、目的、阶段与担忧不参与排盘，但会帮助结果把重点放在你真正需要观察的条件上。</p></section>
    <section><h2>第三步：分清事实与未知</h2><p>每行写一件已经确认的现实事实，并把仍不能确定的内容单独列为未知项。不要填写姓名、电话、住址、证件号码等敏感信息。</p></section>
    <section><h2>第四步：取三个整数</h2><p>三个数字没有吉凶，也没有标准答案。第一数定上卦，第二数定下卦，第三数定动爻；请凭当下所感填写，不必反复筛选。</p></section>
    <section><h2>看完以后</h2><p>先看核心判断、眼下可做的一步与三个观察信号。需要理解依据时，再展开本卦、互卦、变卦、动爻、体用和旺衰。最后把结果存入观事簿，在现实出现新证据后回来复盘。</p></section>
    <Link className="info-primary-link" href="/#inquiry">开始一次观象</Link>
  </InfoLayout>;
}
