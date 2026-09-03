"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import ProductPresentationView, { buildPage9FinaleContent, Page9FinaleView, type Page9FinaleContent, type ProductPresentation } from "./ProductPresentation";
import { shouldContinuePolling } from "./pollPolicy";
import styles from "./page.module.css";

const CONTRACT_VERSION = "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1";
const INTAKE_CONTRACT_VERSION = "SITES_CONDITIONAL_INTAKE_PRODUCT_V1";
const POLL_MS = 1500;
const POLL_LIMIT_ATTEMPTS = 140;
const ACTIVE_REQUEST_KEY = "guanxiang.direct-reading-v2.active-request";
const ACTIVE_CONTEXT_KEY = "guanxiang.direct-reading-v2.active-context";

type ReadingResponse = {
  request_id?: string;
  status?: string;
  stage?: string;
  chart_facts?: ChartFacts | null;
  direct_reading?: { text?: string; chart_facts?: ChartFacts | null } | null;
  product_presentation?: ProductPresentation | null;
  page9_finale?: {
    content_version?: string;
    source?: string;
    answer?: unknown;
    additional_model_calls?: number;
  } | null;
  direct_high?: { route?: string; entry_mode?: EntryMode; intake_status?: string; router_attempts?: number; automatic_retries?: number } | null;
  error_message?: string | null;
  error?: string;
  terminal?: boolean;
};

type EntryMode = "CLEAR" | "CONFIRMED" | "SKIP";
type IntakeChoice = "AUTO" | "CONFIRMED" | "SKIP";
type IntakeResponse = {
  intake_id?: string;
  status?: "PASS" | "ASK_ONCE";
  ambiguity_kind?: "SUBJECT" | "DECISION_AXIS" | "JUDGMENT_OBJECT" | null;
  clarification_prompt?: string | null;
  error?: string;
  fail_open?: boolean;
};

type HexagramFact = {
  king_wen_number?: number;
  name?: string;
  upper_trigram?: string;
  lower_trigram?: string;
};

type ChartFacts = {
  base_hexagram?: HexagramFact | null;
  mutual_hexagram?: HexagramFact | null;
  changed_hexagram?: HexagramFact | null;
  moving_line?: { position?: number; name?: string; canonical_line_text?: string } | null;
};

type ActiveContext = {
  question: string;
  numbers: [string, string, string];
};


function newRequestId(): string {
  return `drv2-${crypto.randomUUID().replaceAll("-", "")}`;
}

const stageText: Record<string, string> = {
  SUBMITTED: "任务已建立",
  CASTING: "正在完成确定性排盘",
  CAST_READY: "排盘已完成，正在解卦",
  MODEL_REQUESTED: "正在组织解卦",
  MODEL_STREAMING: "正在形成完整判断",
  MODEL_COMPLETED: "正文已经生成",
  VALIDATING: "正在核对卦盘与内容边界",
};

export default function DirectReadingV2PreviewPage() {
  const [question, setQuestion] = useState("");
  const [intakeChoice, setIntakeChoice] = useState<IntakeChoice>("AUTO");
  const [waitingIntake, setWaitingIntake] = useState<{ id: string; prompt: string; kind: string } | null>(null);
  const [clarificationAnswer, setClarificationAnswer] = useState("");
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [stage, setStage] = useState("等待输入");
  const [reading, setReading] = useState<string | null>(null);
  const [presentation, setPresentation] = useState<ProductPresentation | null>(null);
  const [finale, setFinale] = useState<Page9FinaleContent | null>(null);
  const [chartFacts, setChartFacts] = useState<ChartFacts | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [offlinePage9, setOfflinePage9] = useState<Page9FinaleContent | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollAttempts = useRef(0);
  const activeContext = useRef<ActiveContext>({ question: "", numbers: ["", "", ""] });

  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
  };

  useEffect(() => clearTimer, []);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    if (new URLSearchParams(window.location.search).get("offline-p9") !== "1") return;
    void import("./p9OfflineFixture").then(({ p9OfflineFixture }) => setOfflinePage9(p9OfflineFixture));
  }, []);

  const handlePayload = (payload: ReadingResponse, id: string) => {
    const receivedFacts = payload.chart_facts ?? payload.direct_reading?.chart_facts;
    if (receivedFacts) setChartFacts(receivedFacts);
    if (
      payload.status === "SUCCESS" && payload.direct_reading?.text && payload.product_presentation &&
      payload.page9_finale?.content_version === "GUANXIANG_P9_FINALE_V1" &&
      payload.page9_finale.source === "SAME_PROVIDER_OUTPUT" && payload.page9_finale.additional_model_calls === 0 &&
      Array.isArray(payload.page9_finale.answer) && payload.page9_finale.answer.length === 2 &&
      payload.page9_finale.answer.every((line): line is string => typeof line === "string") &&
      ["DIRECT_HIGH", "CONDITIONAL_INTAKE_THEN_HIGH"].includes(payload.direct_high?.route ?? "")
    ) {
      clearTimer();
      setStage("解卦完成");
      setReading(payload.direct_reading.text);
      setPresentation(payload.product_presentation);
      const context = activeContext.current;
      setFinale(buildPage9FinaleContent(
        id,
        context.question,
        context.numbers.map(Number),
        payload.direct_reading.text,
        payload.product_presentation,
        payload.page9_finale.answer as [string, string],
      ));
      return;
    }
    if (payload.status === "RUNNING") {
      setStage(stageText[payload.stage ?? ""] ?? "解卦正在进行");
      timer.current = setTimeout(() => void poll(id), POLL_MS);
      return;
    }
    clearTimer();
    setError(payload.error_message || payload.error || "本次没有形成可发布的完整解卦。");
    setStage("任务已停止");
  };

  const poll = async (id: string) => {
    pollAttempts.current += 1;
    if (pollAttempts.current > POLL_LIMIT_ATTEMPTS) {
      clearTimer();
      setError("等待已超过本次私有预览上限。系统没有自动重新生成；可稍后使用同一任务编号核对状态。");
      setStage("查询已停止");
      return;
    }
    try {
      const response = await fetch(`/api/direct-reading/v2?request_id=${encodeURIComponent(id)}`, {
        cache: "no-store",
      });
      const payload = await response.json() as ReadingResponse;
      if (response.status === 202 || response.ok) handlePayload(payload, id);
      else if (shouldContinuePolling(response.status, payload.terminal)) timer.current = setTimeout(() => void poll(id), POLL_MS);
      else handlePayload(payload, id);
    } catch {
      setStage("连接暂时中断，正在查询同一个任务");
      timer.current = setTimeout(() => void poll(id), POLL_MS);
    }
  };

  const restore = () => {
    const existing = window.sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (!/^drv2-[a-f0-9]{16,64}$/.test(existing ?? "")) {
      setError("当前浏览器里没有可以恢复的Direct Reading任务。");
      return;
    }
    setError(null);
    setRequestId(null);
    setReading(null);
    setPresentation(null);
    setFinale(null);
    setChartFacts(null);
    setRequestId(existing);
    try {
      const context = JSON.parse(window.sessionStorage.getItem(ACTIVE_CONTEXT_KEY) ?? "null") as ActiveContext | null;
      if (context && typeof context.question === "string" && Array.isArray(context.numbers) && context.numbers.length === 3) {
        activeContext.current = context;
        setQuestion(context.question);
        setNumbers(context.numbers);
      }
    } catch {
      // A legacy task can still be queried; missing display context is handled by the release gate.
    }
    setStage("正在恢复同一个任务");
    pollAttempts.current = 0;
    void poll(existing as string);
  };

  const startHigh = async (entryMode: EntryMode, intakeId?: string, answer?: string) => {
    clearTimer();
    setReading(null);
    setPresentation(null);
    setFinale(null);
    setChartFacts(null);
    setError(null);
    setWaitingIntake(null);
    const id = newRequestId();
    activeContext.current = { question, numbers: numbers as [string, string, string] };
    window.sessionStorage.setItem(ACTIVE_REQUEST_KEY, id);
    window.sessionStorage.setItem(ACTIVE_CONTEXT_KEY, JSON.stringify({ question, numbers } satisfies ActiveContext));
    pollAttempts.current = 0;
    setRequestId(id);
    setStage("正在建立任务");
    const parsed = numbers.map((value) => Number(value));
    try {
      const response = await fetch("/api/direct-reading/v2", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_version: CONTRACT_VERSION,
          request_id: id,
          question_text: question,
          numbers: parsed,
          entry_mode: entryMode,
          ...(intakeId ? { intake_id: intakeId } : {}),
          ...(answer ? { clarification_answer: answer } : {}),
        }),
      });
      const payload = await response.json() as ReadingResponse;
      if (response.status === 202 || response.ok) handlePayload(payload, id);
      else if (shouldContinuePolling(response.status, payload.terminal)) {
        setStage("提交状态待确认，正在查询同一个任务");
        timer.current = setTimeout(() => void poll(id), POLL_MS);
      } else handlePayload(payload, id);
    } catch {
      setStage("提交状态待确认，正在查询同一个任务");
      timer.current = setTimeout(() => void poll(id), POLL_MS);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setWaitingIntake(null);
    setClarificationAnswer("");
    if (intakeChoice === "CONFIRMED" || intakeChoice === "SKIP") {
      await startHigh(intakeChoice);
      return;
    }
    setStage("正在辨识原题是否需要确认一个关键对象");
    const intakeId = `intake-${crypto.randomUUID().replaceAll("-", "")}`;
    try {
      const response = await fetch("/api/direct-reading/v2/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_version: INTAKE_CONTRACT_VERSION,
          intake_id: intakeId,
          original_question: question,
        }),
      });
      const payload = await response.json() as IntakeResponse;
      if (response.ok && payload.status === "ASK_ONCE" && payload.intake_id && payload.clarification_prompt && payload.ambiguity_kind) {
        setWaitingIntake({ id: payload.intake_id, prompt: payload.clarification_prompt, kind: payload.ambiguity_kind });
        setStage("辨识完成：只需确认一次，不会排盘或解卦");
        return;
      }
      if (response.ok && payload.status === "PASS" && payload.intake_id) {
        setStage("原题已经足够明确，直接进入解卦");
        await startHigh("CLEAR", payload.intake_id);
        return;
      }
      setStage("辨识暂时不可用，按原题直接进入解卦");
      await startHigh("CLEAR");
    } catch {
      setStage("辨识连接暂时不可用，按原题直接进入解卦");
      await startHigh("CLEAR");
    }
  };

  const busy = Boolean(!waitingIntake && requestId && !reading && !error && stage !== "等待输入");

  if (offlinePage9) {
    return <main className={styles.offlineShell} data-offline-p9-review="true">
      <Page9FinaleView content={offlinePage9} />
    </main>;
  }

  return (
    <main className={styles.shell}>
      <section className={styles.panel}>
        <p className={styles.eyebrow}>Owner-only · Non-production</p>
        <h1>Direct Reading V2</h1>
        <p className={styles.lead}>默认先做一次轻量辨识：问题足够明确就直接解卦；只有主体、比较轴或判断对象会导致答错时，才固定问一次。你也可以确认原题或跳过辨识。</p>
        <form onSubmit={submit} className={styles.form}>
          <label>
            所问之事
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} minLength={6} maxLength={160} required />
          </label>
          <fieldset>
            <legend>辨识方式</legend>
            <div className={styles.entryModes}>
              {(["AUTO", "CONFIRMED", "SKIP"] as const).map((mode) => (
                <label key={mode}>
                  <input type="radio" name="intake-mode" value={mode} checked={intakeChoice === mode} onChange={() => setIntakeChoice(mode)} />
                  {mode === "AUTO" ? "自动辨识（推荐）" : mode === "CONFIRMED" ? "我已确认原题" : "跳过辨识，直接解卦"}
                </label>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>三个起卦数（1–999）</legend>
            <div className={styles.numbers}>
              {numbers.map((value, index) => (
                <input
                  key={index}
                  aria-label={`第${index + 1}个数字`}
                  type="number"
                  min="1"
                  max="999"
                  step="1"
                  value={value}
                  onChange={(event) => setNumbers((current) => current.map((item, itemIndex) => itemIndex === index ? event.target.value : item))}
                  required
                />
              ))}
            </div>
          </fieldset>
          <button type="submit" disabled={busy}>{busy ? "正在处理" : intakeChoice === "AUTO" ? "辨识后取数解卦" : "直接取数解卦"}</button>
        </form>
        {waitingIntake ? (
          <section className={styles.clarification} aria-labelledby="clarification-title">
            <p className={styles.eyebrow}>只问一次 · {waitingIntake.kind}</p>
            <h2 id="clarification-title">{waitingIntake.prompt}</h2>
            <textarea
              aria-label="一次澄清回答"
              value={clarificationAnswer}
              onChange={(event) => setClarificationAnswer(event.target.value)}
              maxLength={400}
              placeholder="用你自己的原话简短说明；这段内容只作为用户背景，不会变成卦象证据。"
            />
            <div className={styles.clarificationActions}>
              <button type="button" disabled={!clarificationAnswer.trim()} onClick={() => void startHigh("CONFIRMED", waitingIntake.id, clarificationAnswer.trim())}>带着回答继续解卦</button>
              <button type="button" className={styles.secondary} onClick={() => void startHigh("SKIP", waitingIntake.id)}>跳过这次确认，按原题解卦</button>
            </div>
          </section>
        ) : null}
        <div className={styles.status} role="status" aria-live="polite">{stage}</div>
        {requestId ? <p className={styles.requestId}>任务编号：{requestId}</p> : null}
        {!busy && !reading ? <button type="button" className={styles.restore} onClick={restore}>恢复上次任务</button> : null}
        {error ? <p className={styles.error}>{error}</p> : null}
      </section>
      {chartFacts ? (
        <section className={styles.chart} aria-label="确定性排盘">
          <p className={styles.eyebrow}>程序确定性排盘</p>
          <div className={styles.chartGrid}>
            <div><span>本卦</span><strong>{chartFacts.base_hexagram?.name}</strong><small>第 {chartFacts.base_hexagram?.king_wen_number} 卦</small></div>
            <div><span>互卦</span><strong>{chartFacts.mutual_hexagram?.name}</strong><small>第 {chartFacts.mutual_hexagram?.king_wen_number} 卦</small></div>
            <div><span>动爻</span><strong>{chartFacts.moving_line?.name}</strong><small>{chartFacts.moving_line?.canonical_line_text}</small></div>
            <div><span>变卦</span><strong>{chartFacts.changed_hexagram?.name}</strong><small>第 {chartFacts.changed_hexagram?.king_wen_number} 卦</small></div>
          </div>
        </section>
      ) : null}
      {reading && presentation && finale ? <>
        <ProductPresentationView presentation={presentation} />
        <Page9FinaleView content={finale} />
      </> : null}
    </main>
  );
}
