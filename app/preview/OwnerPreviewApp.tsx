"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./preview.module.css";
import { pollPreviewTask, PreviewPollError, type PreviewTaskPayload } from "./preview-poll";

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
const ACTIVE_REQUEST_KEY = "guanxiang-owner-preview-active-request";
type Reading = { core_judgment: string; explanation: string; reality_application: string; action: string; switch_condition: string };
type PreviewResponse = PreviewTaskPayload & {
  status?: string;
  error?: string | null;
  deterministic_result?: { base_hexagram?: { name?: string }; mutual_hexagram?: { name?: string }; changed_hexagram?: { name?: string }; moving_line?: number } | null;
  personalized_reading?: Reading | null;
  preview_meta?: { actual_api_cost_usd?: number; total_attempts?: number; actual_total_usd?: number; hard_limit_enabled?: boolean };
};

function lines(value: string): string[] {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
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
  const [progress, setProgress] = useState("");
  const allowedGoals = useMemo(() => Object.fromEntries((GOALS_BY_DOMAIN[domain] ?? []).map((key) => [key, GOALS[key]])), [domain]);

  function finish(requestId: string, payload: PreviewResponse): void {
    sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
    if (payload.status !== "SUCCESS" || !payload.personalized_reading) {
      throw new Error(payload.error || "本次新版解读没有通过检查，也不会自动重试。");
    }
    setResult(payload);
    setProgress("");
    window.setTimeout(() => document.getElementById("preview-result")?.scrollIntoView({ behavior: "smooth" }), 0);
    void requestId;
  }

  async function poll(requestId: string, cancelled: () => boolean = () => false): Promise<void> {
    setProgress("模型正在生成新版解读，页面会自动取得结果。你可以留在本页等待。");
    try {
      const payload = await pollPreviewTask(requestId, {
        fetchResult: () => fetch(`/api/preview/v1/meihua?request_id=${encodeURIComponent(requestId)}`, { cache: "no-store" }),
        sleep,
        cancelled,
      });
      if (payload) finish(requestId, payload as PreviewResponse);
    } catch (caught) {
      if (caught instanceof PreviewPollError && caught.terminal) {
        sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
      }
      throw caught;
    }
  }

  function errorMessage(caught: unknown, requestId?: string): string {
    const message = caught instanceof Error ? caught.message : "查询生成结果时出现异常。";
    const taskId = caught instanceof PreviewPollError ? caught.requestId : requestId;
    return taskId ? `${message}（任务编号：${taskId}）` : message;
  }

  useEffect(() => {
    const activeRequestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (!activeRequestId || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(activeRequestId)) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    void poll(activeRequestId, () => cancelled)
      .catch((caught) => { if (!cancelled) setError(errorMessage(caught, activeRequestId)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  // The active request is intentionally resumed only once when this page mounts.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setResult(null);
    const activeRequestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (activeRequestId && /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(activeRequestId)) {
      setLoading(true);
      try {
        await poll(activeRequestId);
      } catch (caught) {
        setError(errorMessage(caught, activeRequestId));
      } finally {
        setLoading(false);
        setProgress("");
      }
      return;
    }
    if (activeRequestId) sessionStorage.removeItem(ACTIVE_REQUEST_KEY);

    const factLines = lines(facts);
    const unknownLines = lines(unknowns);
    const actionLines = lines(actions);
    const responseLines = lines(responses);
    const parsedNumbers = numbers.map(Number);
    const textLists = [factLines, unknownLines, actionLines, responseLines];
    if (question.trim().length < 6 || !domain || !goal || !horizon || !stage || !uncertainty || factLines.length < 1 || factLines.length > 8 || unknownLines.length < 1 || unknownLines.length > 6 || actionLines.length > 6 || responseLines.length > 6 || textLists.some((items) => items.some((item) => item.length > 400)) || parsedNumbers.some((value, index) => !numbers[index] || !Number.isInteger(value) || value < 1 || value > 999) || !acknowledged) {
      setError("请完整填写问题、处境和三个数字；事实最多 8 行，未知项、行动与回应各最多 6 行，每行不超过 400 字，并确认体验边界。");
      return;
    }
    setLoading(true); setProgress("正在提交生成任务……");
    const requestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY) || `beta-${crypto.randomUUID()}`;
    try {
      sessionStorage.setItem(ACTIVE_REQUEST_KEY, requestId);
      const body = JSON.stringify({
          contract_version: "SITES_OWNER_PREVIEW_CONTRACT_V1",
          request_id: requestId,
          question_text: question.trim(),
          question_domain: domain,
          decision_goal: goal,
          time_horizon: horizon,
          decision_stage: stage,
          key_uncertainty: uncertainty,
          confirmed_facts: factLines,
          unknowns: unknownLines,
          options: [],
          actions_already_taken: actionLines,
          observable_responses: responseLines,
          numbers: parsedNumbers,
          locale: "zh-CN",
          client_timestamp: new Date().toISOString(),
          user_acknowledgements: { owner_preview_only: true, live_model_cost_acknowledged: true, no_formal_persistence: true, user_statements_not_verified_facts: true },
      });
      let accepted = false;
      for (let attempt = 0; attempt < 3 && !accepted; attempt += 1) {
        try {
          const response = await fetch("/api/preview/v1/meihua", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            cache: "no-store",
            body,
          });
          const payload = await response.json() as PreviewResponse;
          if (response.status === 202) {
            accepted = true;
            break;
          }
          if (response.ok) {
            finish(requestId, payload);
            return;
          }
          if (response.status !== 503) {
            sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
            throw new Error(payload.error || "生成任务提交失败。");
          }
        } catch (caught) {
          if (caught instanceof Error && !/Failed to fetch|fetch failed|network/i.test(caught.message)) throw caught;
        }
        await sleep(1_500);
      }
      await poll(requestId);
    } catch (caught) {
      setError(errorMessage(caught, requestId));
    } finally { setLoading(false); setProgress(""); }
  }

  const reading = result?.personalized_reading;
  return <main className={styles.page}>
    <header className={styles.header}><Link href="/">观象</Link><span>新版解读 · 受控 Beta</span></header>
    <section className={styles.intro}>
      <p>首位用户体验 · 受控开放</p>
      <h1>先把事实说清，<br />再看卦象如何落到这件事。</h1>
      <p>新版解读会把你确认的现实信息与程序排出的卦象分开，再给出一个可观察、可转向的行动建议。生成通常需要一至三分钟，请勿关闭本页。</p>
    </section>
    <form className={styles.form} onSubmit={submit}>
      <section><h2>一 · 所问与处境</h2><label><span>你真正想问的问题</span><textarea value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这次合作已经反复推迟，我还应该继续投入吗？" /></label><div className={styles.grid}><SelectField label="事情属于" value={domain} options={DOMAINS} onChange={(value) => { setDomain(value); setGoal(""); }} /><SelectField label="最想看清" value={goal} options={allowedGoals} disabled={!domain} onChange={setGoal} /><SelectField label="观察范围" value={horizon} options={HORIZONS} onChange={setHorizon} /><SelectField label="事情阶段" value={stage} options={STAGES} onChange={setStage} /><SelectField label="关键未知" value={uncertainty} options={UNCERTAINTIES} onChange={setUncertainty} /></div></section>
      <section><h2>二 · 事实与未知</h2><p className={styles.help}>每行写一件事。只写你已经确认的内容，不写猜测，也不要填写姓名、电话、住址等敏感信息。</p><label><span>已经确认的现实事实</span><textarea value={facts} onChange={(event) => setFacts(event.target.value)} placeholder={"已经沟通过两次，对方都没有明确截止时间\n本周需要决定是否继续预留资源"} /></label><label><span>目前不能假设的未知项</span><textarea value={unknowns} onChange={(event) => setUnknowns(event.target.value)} placeholder={"不知道最终负责人是否已经看过方案\n不知道下个月是否仍有预算"} /></label><div className={styles.two}><label><span>已经采取的行动（可留空）</span><textarea value={actions} onChange={(event) => setActions(event.target.value)} /></label><label><span>已经出现的回应（可留空）</span><textarea value={responses} onChange={(event) => setResponses(event.target.value)} /></label></div></section>
      <section><h2>三 · 静心取数</h2><div className={styles.numbers}>{numbers.map((value, index) => <label key={index}><span>{["上卦", "下卦", "动爻"][index]}</span><input type="number" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>)}</div></section>
      <label className={styles.ack}><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：这是一项受控 Beta 体验，结果仅供梳理思路，不替代医疗、法律、财务等专业意见；问题与结果只为完成本次生成临时保留，最多约 30 分钟，不写入观事簿；遇到网络中断会沿用同一任务编号，不重复生成。本次体验不向我收费。</span></label>
      {progress && <p className={styles.help} role="status">{progress}</p>}
      {error && <p className={styles.error} role="alert">{error}</p>}
      <button className={styles.submit} disabled={loading}>{loading ? "正在生成，页面会自动取得结果" : "生成新版解读"}</button>
    </form>
    {reading && <section className={styles.result} id="preview-result"><p>本次新版解读</p><h2>{reading.core_judgment}</h2><article><h3>为什么这样判断</h3><p>{reading.explanation}</p></article><article><h3>落到你的现实</h3><p>{reading.reality_application}</p></article><article><h3>下一步</h3><p>{reading.action}</p></article><article><h3>何时需要转向</h3><p>{reading.switch_condition}</p></article><small>本次结果不会写入观事簿。请结合现实信息自行判断，并以可观察的后续变化校准。</small></section>}
    <footer><Link href="/">返回观象首页</Link><span>受控 Beta · 结果仅供参考</span></footer>
  </main>;
}
