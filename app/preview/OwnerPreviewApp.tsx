"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./preview.module.css";

const DOMAINS = {
  WORK_CAREER: "工作与职业发展",
  PROJECT_COOPERATION: "项目与合作推进",
  RELATIONSHIP_COMMUNICATION: "关系与沟通",
  PERSONAL_PLANNING: "个人规划",
};
const GOALS = {
  IDENTIFY_OBSTACLES: "识别阻力与支持条件",
  PLAN_NEXT_STEP: "规划下一步",
  PREPARE_COMMUNICATION: "准备一次现实沟通",
  ADJUST_COMMITMENT_BOUNDARIES: "调整投入与边界",
  OBSERVE_VERIFY_SIGNALS: "观察和核实现实信号",
};
const GOALS_BY_DOMAIN: Record<string, (keyof typeof GOALS)[]> = {
  WORK_CAREER: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "OBSERVE_VERIFY_SIGNALS"],
  PROJECT_COOPERATION: Object.keys(GOALS) as (keyof typeof GOALS)[],
  RELATIONSHIP_COMMUNICATION: ["PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  PERSONAL_PLANNING: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
};
const HORIZONS = { CURRENT: "当前阶段", NEXT_30_DAYS: "未来 30 天", NEXT_QUARTER: "未来一个季度", NEXT_6_MONTHS: "未来 6 个月" };
const STAGES = { EXPLORING: "正在了解", PREPARING: "正在准备", ALREADY_ACTING: "已经行动", WAITING_FEEDBACK: "正在等待回应" };
const UNCERTAINTIES = { CONDITIONS: "现实条件是否具备", OTHER_RESPONSE: "对方会如何回应", OWN_COMMITMENT: "自己是否值得继续投入", TIMING: "时机是否合适" };

type Reading = { core_judgment: string; explanation: string; reality_application: string; action: string; switch_condition: string };
type PreviewResponse = {
  status?: string;
  error?: string | null;
  deterministic_result?: { base_hexagram?: { name?: string }; mutual_hexagram?: { name?: string }; changed_hexagram?: { name?: string }; moving_line?: number } | null;
  personalized_reading?: Reading | null;
  preview_meta?: { actual_api_cost_usd?: number; total_attempts?: number; actual_total_usd?: number; hard_limit_enabled?: boolean };
};

function lines(value: string): string[] {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function SelectField({ label, value, options, onChange, disabled = false }: { label: string; value: string; options: Record<string, string>; onChange: (value: string) => void; disabled?: boolean }) {
  return <label><span>{label}</span><select value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}><option value="">请选择</option>{Object.entries(options).map(([key, text]) => <option key={key} value={key}>{text}</option>)}</select></label>;
}

export function OwnerPreviewApp() {
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("");
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [stage, setStage] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [facts, setFacts] = useState("");
  const [unknowns, setUnknowns] = useState("");
  const [actions, setActions] = useState("");
  const [responses, setResponses] = useState("");
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [result, setResult] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const allowedGoals = useMemo(() => Object.fromEntries((GOALS_BY_DOMAIN[domain] ?? []).map((key) => [key, GOALS[key]])), [domain]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setResult(null);
    const parsedNumbers = numbers.map(Number);
    if (question.trim().length < 6 || !domain || !goal || !horizon || !stage || !uncertainty || lines(facts).length < 1 || lines(unknowns).length < 1 || parsedNumbers.some((value, index) => !numbers[index] || !Number.isInteger(value) || value < 1 || value > 999) || !acknowledged) {
      setError("请完整填写问题、现实事实、未知项、处境选择和三个数字，并确认私有体验边界。");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/preview/v1/meihua", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
          request_id: `owner-${crypto.randomUUID()}`,
          question_text: question.trim(),
          question_domain: domain,
          decision_goal: goal,
          time_horizon: horizon,
          decision_stage: stage,
          key_uncertainty: uncertainty,
          confirmed_facts: lines(facts),
          unknowns: lines(unknowns),
          options: [],
          actions_already_taken: lines(actions),
          observable_responses: lines(responses),
          numbers: parsedNumbers,
          locale: "zh-CN",
          client_timestamp: new Date().toISOString(),
          user_acknowledgements: { owner_preview_only: true, live_model_cost_acknowledged: true, no_formal_persistence: true, user_statements_not_verified_facts: true },
        }),
      });
      const payload = await response.json() as PreviewResponse;
      if (!response.ok || payload.status !== "SUCCESS" || !payload.personalized_reading) throw new Error(payload.error || "本次新版解读没有通过检查，也不会自动重试。");
      setResult(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "新版解读暂时无法连接。");
    } finally { setLoading(false); }
  }

  const reading = result?.personalized_reading;
  return <main className={styles.page}>
    <header className={styles.header}><Link href="/">观象</Link><span>新版解读 · 所有者私有体验</span></header>
    <section className={styles.intro}>
      <p>校准入口 · 不替代现有 v16</p>
      <h1>先把事实说清，<br />再看卦象如何落到这件事。</h1>
      <p>这里专门用来体验新版解读。它不会写入观事簿，不会形成正式报告，也不会改变现有观象页面。</p>
    </section>
    <form className={styles.form} onSubmit={submit}>
      <section><h2>一 · 所问与处境</h2><label><span>你真正想问的问题</span><textarea value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这次合作已经反复推迟，我还应该继续投入吗？" /></label><div className={styles.grid}><SelectField label="事情属于" value={domain} options={DOMAINS} onChange={(value) => { setDomain(value); setGoal(""); }} /><SelectField label="最想看清" value={goal} options={allowedGoals} disabled={!domain} onChange={setGoal} /><SelectField label="观察范围" value={horizon} options={HORIZONS} onChange={setHorizon} /><SelectField label="事情阶段" value={stage} options={STAGES} onChange={setStage} /><SelectField label="关键未知" value={uncertainty} options={UNCERTAINTIES} onChange={setUncertainty} /></div></section>
      <section><h2>二 · 事实与未知</h2><p className={styles.help}>每行写一件事。只写你已经确认的内容，不写猜测，也不要填写姓名、电话、住址等敏感信息。</p><label><span>已经确认的现实事实</span><textarea value={facts} onChange={(event) => setFacts(event.target.value)} placeholder={"已经沟通过两次，对方都没有明确截止时间\n本周需要决定是否继续预留资源"} /></label><label><span>目前不能假设的未知项</span><textarea value={unknowns} onChange={(event) => setUnknowns(event.target.value)} placeholder={"不知道最终负责人是否已经看过方案\n不知道下个月是否仍有预算"} /></label><div className={styles.two}><label><span>已经采取的行动（可留空）</span><textarea value={actions} onChange={(event) => setActions(event.target.value)} /></label><label><span>已经出现的回应（可留空）</span><textarea value={responses} onChange={(event) => setResponses(event.target.value)} /></label></div></section>
      <section><h2>三 · 静心取数</h2><div className={styles.numbers}>{numbers.map((value, index) => <label key={index}><span>{["上卦", "下卦", "动爻"][index]}</span><input type="number" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>)}</div></section>
      <label className={styles.ack}><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：这是所有者私有校准版；真实模型调用会产生 API 费用，系统逐次记录实际成本但不设置次数或金额硬上限；结果不保存、不自动重试，也不是正式上线结论。</span></label>
      {error && <p className={styles.error} role="alert">{error}</p>}
      <button className={styles.submit} disabled={loading}>{loading ? "正在整理事实与卦象，请稍候" : "生成新版解读"}</button>
    </form>
    {reading && <section className={styles.result} id="preview-result"><p>私有体验结果</p><h2>{reading.core_judgment}</h2><article><h3>为什么这样判断</h3><p>{reading.explanation}</p></article><article><h3>落到你的现实</h3><p>{reading.reality_application}</p></article><article><h3>下一步</h3><p>{reading.action}</p></article><article><h3>何时需要转向</h3><p>{reading.switch_condition}</p></article><small>本次 API 费用：${Number(result?.preview_meta?.actual_api_cost_usd ?? 0).toFixed(6)} · 累计 {Number(result?.preview_meta?.total_attempts ?? 0)} 次 / ${Number(result?.preview_meta?.actual_total_usd ?? 0).toFixed(6)} · 不计入产品收费 · 未保存</small></section>}
    <footer><Link href="/">返回现有观象</Link><span>私有校准 · 非正式发布</span></footer>
  </main>;
}
