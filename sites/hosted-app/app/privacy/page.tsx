import type { Metadata } from "next";
import { InfoLayout } from "../InfoLayout";

export const metadata: Metadata = { title: "隐私说明 · 观象", description: "了解观象如何保存和删除你的问事与复盘记录。" };

export default function PrivacyPage() {
  return <InfoLayout eyebrow="隐私说明" title="你的问题，应当由你掌握" lead="不保存也可以正常完成一次观象。只有当你主动点击“存入观事簿”时，本站才会保存这次问题、结果和复盘内容。">
    <section><h2>保存哪些内容</h2><p>保存的问题原文、三个数字、结构化处境、排盘结果、你准备采取的行动、复盘日期，以及你后来主动写下的现实结果与认识。</p></section>
    <section><h2>如何识别你的记录</h2><p>目前不要求注册账号。浏览器会生成一把只保存在当前设备中的随机访问凭据，服务器只保存它的不可逆摘要。换浏览器、清除网站数据或更换设备后，旧记录不会自动出现，因此请在需要时先导出备份。</p></section>
    <section><h2>如何删除与导出</h2><p>你可以在“观事簿”中导出全部记录，也可以逐条永久删除。删除后本站不会提供恢复入口。</p></section>
    <section><h2>请不要填写</h2><p>请勿写入身份证号、银行卡、验证码、精确住址、病历等敏感资料。当前版本不采集出生日期、出生地点或出生时辰。</p></section>
    <section><h2>重要边界</h2><p>观象不适合处理紧急医疗、人身安全、违法风险或必须由持证专业人士决定的事项。遇到这些问题，应优先寻求现实中的专业帮助。</p></section>
  </InfoLayout>;
}
