import type { Metadata } from "next";
import { FeedbackForm } from "../FeedbackForm";
import { InfoLayout } from "../InfoLayout";

export const metadata: Metadata = { title: "方法与边界 · 观象", description: "了解观象如何排盘、如何整理解释，以及它不替你做什么。" };

export default function AboutPage() {
  return <InfoLayout eyebrow="方法与边界" title="让每一句判断，都能找到来处" lead="观象是一套以梅花易数确定性排盘为基础、以现实验证为归宿的观察工具。它不替人预言不可改变的结果。">
    <section><h2>三类信息，各有各的作用</h2><dl><div><dt>你写下的问题</dt><dd>用于帮助你把事情说清楚，也用于在结果页呈现上下文；它不参与排盘计算。</dd></div><div><dt>你选择的现实处境</dt><dd>用于安排解释重点，让相同的卦象能回到不同现实问题中被理解；它不会改变本卦、互卦和变卦。</dd></div><div><dt>你给出的三个数字</dt><dd>依版本化的三数起卦规则，确定上卦、下卦和动爻，是本次排盘的计算输入。</dd></div></dl></section>
    <section><h2>当前采用的规则</h2><p>确定性排盘规则为 <code>MEIHUA_RULE_SPEC_V1</code>，页面接口为 <code>SITES_MEIHUA_API_CONTRACT_V3</code>。算法规则如需改变，必须升级版本并通过自动化测试；AI 不参与确定卦象。</p></section>
    <section><h2>编辑原则</h2><ul><li>先说明卦从何来，再给出现实中可以验证的方向。</li><li>不把现实背景伪装成卦象证据。</li><li>不生成排盘程序没有提供的具体日期。</li><li>不以单一卦象替代医疗、法律、财务或人身安全判断。</li><li>不因得顺势之象鼓励躺平，也不因见阻力之象鼓励放弃。</li></ul></section>
    <section><h2>维护与纠错</h2><p>观象由 Abalo 项目持续维护。经典原文、排盘规则和解释文字分别管理；内容纠错不会悄悄改变确定性算法。</p><FeedbackForm /></section>
  </InfoLayout>;
}
