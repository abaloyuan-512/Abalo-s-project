"use client";

import { FormEvent, useEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import {
  PersonalizedPollError,
  pollPersonalizedTask,
} from "./personalized-reading-poll";
import { resultSectionVisibility } from "./result-presentation.mjs";

type Hexagram = { king_wen_number: number; name: string; symbol: string };
type EvidenceItem = { title: string; text: string };
type ClarityReport = {
  template_version: string;
  answer: string;
  what_it_means: string;
  priority: string;
  continue_signals: string[];
  pause_signals: string[];
  next_action: string;
  evidence_path: EvidenceItem[];
  boundary_note: string;
};
type NumberPathItem = {
  input_number: number;
  role: string;
  resolved_number: number;
  result_name: string;
  result_symbol: string;
  explanation: string;
};
type CanonicalHexagramItem = {
  role: string;
  king_wen_number: number;
  name: string;
  symbol: string;
  canonical_text: string;
  plain_note: string;
  source_name: string;
  source_reference: string;
  reading_role: string;
};
type CulturalReading = {
  template_version: string;
  number_path: NumberPathItem[];
  hexagrams: CanonicalHexagramItem[];
  moving_line: {
    position: number;
    line_name: string;
    canonical_text: string;
    source_name: string;
    source_reference: string;
    stage: string;
  };
  terms: { title: string; current_value: string; meaning: string; current_effect: string }[];
  classic_counsel: { quote: string; source: string };
  knowledge_notice: string | null;
};
type PersonalizedReading = {
  core_judgment: string;
  explanation: string;
  reality_application: string;
  action: string;
  switch_condition: string;
  question_responses?: { question_text: string; answer_text: string }[];
};
type ProductResult = {
  input_numbers: number[];
  base_hexagram: Hexagram;
  mutual_hexagram: Hexagram;
  changed_hexagram: Hexagram;
  moving_line: number;
  body_use: { body_trigram: string; initial_relation: string; changed_relation: string };
  seasonal_strength: { body: string; solar_term: string; month_branch: string };
  deterministic_conclusion: { conclusion_level: string };
  clarity_report: ClarityReport;
  cultural_reading?: CulturalReading;
  personalized_reading?: PersonalizedReading;
};
type StructuredIntake = {
  question_domain: string;
  decision_goal: string;
  time_horizon: string;
  decision_stage: string;
  key_uncertainty: string;
  decision_risk_profile?: string;
};
type ApiResponse = {
  status?: string;
  user_question?: string;
  structured_intake?: StructuredIntake;
  deterministic_result?: ProductResult | null;
  personalized_reading?: PersonalizedReading | null;
  error?: string;
  errors?: { message?: string }[];
};
export type JournalRecord = {
  id: string;
  created_at: string;
  updated_at: string;
  question: string;
  structured_intake: StructuredIntake;
  numbers: number[];
  result: ProductResult;
  action_text: string;
  review_on: string | null;
  reality_text: string;
  learning_text: string;
  status: "OPEN" | "REVIEWED";
};
export type JournalDraft = Pick<JournalRecord, "action_text" | "review_on" | "reality_text" | "learning_text" | "status">;

const GOALS = {
  IDENTIFY_OBSTACLES: "看清阻力与条件",
  PLAN_NEXT_STEP: "判断下一步怎么走",
  PREPARE_COMMUNICATION: "准备一次重要沟通",
  ADJUST_COMMITMENT_BOUNDARIES: "调整投入与边界",
  OBSERVE_VERIFY_SIGNALS: "确认该观察什么信号",
} as const;
const GOALS_BY_DOMAIN: Record<string, (keyof typeof GOALS)[]> = {
  WORK_CAREER: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "OBSERVE_VERIFY_SIGNALS"],
  PROJECT_COOPERATION: Object.keys(GOALS) as (keyof typeof GOALS)[],
  RELATIONSHIP_COMMUNICATION: ["PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  PERSONAL_PLANNING: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
};
const HORIZONS = { CURRENT: "当前阶段", NEXT_30_DAYS: "未来三十天", NEXT_QUARTER: "未来一个季度", NEXT_6_MONTHS: "未来六个月" } as const;
const STAGES = { EXPLORING: "刚开始了解", PREPARING: "准备行动", ALREADY_ACTING: "正在推进", WAITING_FEEDBACK: "等待回应" } as const;

const QUESTION_EXAMPLES = [
  { topic: "工作", domain: "WORK_CAREER", text: "面对现在的工作机会，我下一步最该先确认什么？" },
  { topic: "合作", domain: "PROJECT_COOPERATION", text: "这次合作，我还应该继续投入吗？" },
  { topic: "关系", domain: "RELATIONSHIP_COMMUNICATION", text: "这段关系一直没有进展，我还要继续主动吗？" },
  { topic: "规划", domain: "PERSONAL_PLANNING", text: "我现在开始这项长期计划，最需要先准备什么？" },
] as const;

const METHOD_CLASSIC_LINES = ["在天成象", "在地成形", "变化见矣"] as const;

const JOURNAL_KEY = "guanxiang-observation-key-v1";
const ACTIVE_REQUEST_KEY = "guanxiang-personalized-active-request-v1";
const JOURNAL_OPEN_KEY = "guanxiang-open-journal-record-v1";
const FIRST_DISCERNMENT_QUESTION = "这件事现在具体走到了哪一步？";

function nonemptyLines(value: string): string[] {
  return value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character] ?? character);
}

function downloadReadingHtml(response: ApiResponse): void {
  const result = response.deterministic_result;
  if (!result) return;
  const question = escapeHtml(response.user_question ?? "你所问之事");
  const cultural = result.cultural_reading;
  const personalized = response.personalized_reading ?? result.personalized_reading;
  const report = result.clarity_report;
  const hexagrams = cultural?.hexagrams.map((item) => `<article><header><span>${escapeHtml(item.role)}</span><b>${escapeHtml(item.symbol)}</b><div><small>第 ${item.king_wen_number} 卦</small><h2>${escapeHtml(item.name)}</h2></div></header><p>${escapeHtml(item.reading_role)}</p><blockquote><i>《易》曰</i>${escapeHtml(item.canonical_text)}</blockquote><p>${escapeHtml(item.plain_note)}</p></article>`).join("") ?? "";
  const terms = cultural?.terms.map((term) => `<article><span>${escapeHtml(term.title)}</span><h3>${escapeHtml(term.current_value)}</h3><p>${escapeHtml(term.meaning)}</p><b>本次影响</b><p>${escapeHtml(term.current_effect)}</p></article>`).join("") ?? "";
  const personal = personalized ? `<section><p class="eyebrow">回到你的现实</p><h2>${escapeHtml(personalized.core_judgment)}</h2><div class="columns"><article><h3>为什么这样判断</h3><p>${escapeHtml(personalized.explanation)}</p></article><article><h3>落到现实</h3><p>${escapeHtml(personalized.reality_application)}</p></article><article><h3>下一步</h3><p>${escapeHtml(personalized.action)}</p></article><article><h3>何时转向</h3><p>${escapeHtml(personalized.switch_condition)}</p></article></div></section>` : "";
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>观象 · ${escapeHtml(result.base_hexagram.name)}</title><style>@font-face{font-family:gx;src:url(data:font/woff2;base64,) format('woff2')}*{box-sizing:border-box}body{margin:0;color:#2a2b25;background:#f2ead9;font-family:STKaiti,KaiTi,serif;letter-spacing:.055em}main{max-width:1180px;margin:auto;padding:9vw 7vw;background:url('data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="80"%3E%3Cfilter id="n"%3E%3CfeTurbulence baseFrequency=".7" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23n)" opacity=".025"/%3E%3C/svg%3E')}header.hero{text-align:center;min-height:58vh;display:grid;place-content:center;border-bottom:1px solid rgba(53,55,48,.2)}.hero b{font-size:8rem;font-weight:400}.hero h1{margin:.1em 0;font-size:4rem;font-weight:400}.hero p{color:#62665d}.eyebrow{color:#963b28;letter-spacing:.22em}section{padding:5rem 0;border-bottom:1px solid rgba(53,55,48,.2)}section>h2{font-size:2.5rem;font-weight:400;line-height:1.45}.grid,.columns{display:grid;grid-template-columns:repeat(3,1fr);gap:2.4rem}.columns{grid-template-columns:repeat(2,1fr)}article header{display:flex;gap:1rem;align-items:center}article header>b{font-size:3.4rem;font-weight:400}article h2,article h3{font-weight:400}article p{line-height:1.85;color:#50544b}blockquote{margin:1.5rem 0;padding:1.5rem 0;border-block:1px solid rgba(53,55,48,.16);line-height:1.9}blockquote i{display:block;color:#963b28;font-style:normal}.terms{display:grid;grid-template-columns:repeat(3,1fr);gap:2rem}.final{font-size:2rem;line-height:1.65;text-align:center}.boundary{font-size:.85rem;color:#62665d;line-height:1.8}@media(max-width:720px){main{padding:3rem 1.4rem}.hero b{font-size:5rem}.hero h1{font-size:2.8rem}.grid,.columns,.terms{grid-template-columns:1fr}}</style></head><body><main><header class="hero"><p class="eyebrow">本次所得之卦</p><b>${escapeHtml(result.base_hexagram.symbol)}</b><h1>第 ${result.base_hexagram.king_wen_number} 卦 · ${escapeHtml(result.base_hexagram.name)}</h1><p>所问：${question}</p></header><section><p class="eyebrow">本卦 · 互卦 · 变卦</p><div class="grid">${hexagrams}</div></section><section><p class="eyebrow">动爻 · 体用 · 旺衰</p><div class="terms">${terms}</div></section>${personal}<section><p class="eyebrow">解读至此</p><p class="final">${escapeHtml(personalized?.action ?? report.next_action)}</p><p class="boundary">${escapeHtml(report.boundary_note)}</p></section></main></body></html>`;
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `观象-${result.base_hexagram.name}.html`;
  anchor.click();
  URL.revokeObjectURL(url);
}

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

function observationKey(): string {
  const existing = window.localStorage.getItem(JOURNAL_KEY);
  if (existing) return existing;
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const value = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  window.localStorage.setItem(JOURNAL_KEY, value);
  return value;
}

function journalHeaders(): HeadersInit {
  return { "Content-Type": "application/json", "X-Guanxiang-Key": observationKey() };
}

function defaultReviewDate(): string {
  const date = new Date();
  date.setDate(date.getDate() + 14);
  return date.toISOString().slice(0, 10);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

function VerticalBrand() {
  return <div className="vertical-brand" aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>;
}

function BaguaMark({ className = "", decorative = true }: { className?: string; decorative?: boolean }) {
  return <img
    className={`bagua-mark ${className}`}
    src="/fuxi-bagua-taiji.svg"
    alt={decorative ? "" : "伏羲先天太极八卦图"}
    aria-hidden={decorative ? "true" : undefined}
  />;
}

const PEONY_BREATHS = [
  { numeral: "一息", guidance: "松开杂念", flower: "/casting-peony-bloom-1-v1.png" },
  { numeral: "二息", guidance: "回到所问", flower: "/casting-peony-bloom-2-v1.png" },
  { numeral: "三息", guidance: "心定取数", flower: "/casting-peony-bloom-3-v1.png" },
] as const;

const PEONY_PETAL_MOTIONS = [
  { left: 18, midX: -10, travelX: -39, travelY: 34, spin: -286, size: 22 },
  { left: 31, midX: -16, travelX: -48, travelY: 42, spin: 238, size: 18 },
  { left: 45, midX: -8, travelX: -44, travelY: 49, spin: 326, size: 25 },
  { left: 58, midX: -19, travelX: -55, travelY: 38, spin: -344, size: 20 },
  { left: 69, midX: -13, travelX: -50, travelY: 46, spin: 272, size: 17 },
  { left: 78, midX: -21, travelX: -60, travelY: 43, spin: 388, size: 23 },
] as const;

type IntakeAnswer = { prompt: string; answer: string };
type DiscernmentCompletionReason = "ENOUGH" | "MAX_TURNS" | "USER_EARLY";
type GuidedIntakeProps = {
  question: string;
  onFacts: (value: string) => void;
  onUnknowns: (value: string) => void;
  onActions: (value: string) => void;
  onObservableResponses: (value: string) => void;
  onSuggestion: (value: { question: string; reason: string } | null) => void;
  onStructured: (value: { domain: string; goal: string; horizon: string; stage: string; uncertainty: string; riskProfile?: string }) => void;
  onCompletionReason: (reason: DiscernmentCompletionReason) => void;
  onComplete: (complete: boolean) => void;
  onContinue: () => void;
};

type GuidedIntakeApiResponse = {
  status: "ASK" | "COMPLETE";
  assistant_message: string;
  next_question: string | null;
  suggested_question: string;
  question_change_reason: string;
  structured_intake: StructuredIntake;
  confirmed_facts: string[];
  unknowns: string[];
  actions_already_taken: string[];
  observable_responses: string[];
  boundary_note: string;
  error?: string;
};

function inferDomain(text: string): string {
  if (/关系|喜欢|表白|朋友|伴侣|沟通|同事之间|家人/.test(text)) return "RELATIONSHIP_COMMUNICATION";
  if (/项目|合作|客户|合同|方案|合伙|资源/.test(text)) return "PROJECT_COOPERATION";
  if (/工作|职业|岗位|公司|升职|离职|求职/.test(text)) return "WORK_CAREER";
  return "PERSONAL_PLANNING";
}

function inferGoal(text: string): keyof typeof GOALS {
  if (/沟通|表达|谈|说/.test(text)) return "PREPARE_COMMUNICATION";
  if (/边界|投入|付出|停止|退出/.test(text)) return "ADJUST_COMMITMENT_BOUNDARIES";
  if (/回应|信号|迹象|反馈/.test(text)) return "OBSERVE_VERIFY_SIGNALS";
  if (/阻力|困难|卡住|原因/.test(text)) return "IDENTIFY_OBSTACLES";
  return "PLAN_NEXT_STEP";
}

function inferUncertainty(text: string): "CONDITIONS" | "OTHER_RESPONSE" | "OWN_COMMITMENT" | "TIMING" {
  if (/时机|时候|多久|时间|现在/.test(text)) return "TIMING";
  if (/回应|态度|对方|反馈|答复/.test(text)) return "OTHER_RESPONSE";
  if (/投入|付出|坚持|继续/.test(text)) return "OWN_COMMITMENT";
  return "CONDITIONS";
}

function LocalGuidedIntake({ question, onFacts, onUnknowns, onActions, onObservableResponses, onSuggestion, onStructured, onCompletionReason, onComplete, onContinue }: GuidedIntakeProps) {
  const [turn, setTurn] = useState(0);
  const [draft, setDraft] = useState("");
  const [answers, setAnswers] = useState<IntakeAnswer[]>([]);
  const [horizonAnswer, setHorizonAnswer] = useState("");
  const [stageAnswer, setStageAnswer] = useState("");
  const prompts = [
    "先确定观察的范围：你希望在多长时间内看清这件事？",
    "这件事现在走到了哪一步？",
    "到目前为止，哪些是你已经确认的现实事实？请不要写推测。",
    "哪一部分仍然未知，不能先当作事实？",
    "为了这件事，你已经采取过什么行动？如果还没有，可以写“尚未行动”。",
    "事情已经给过你怎样的回应或反馈？如果还没有，可以写“尚无回应”。",
    "如果这一次只能看清一件事，你最希望确认什么？",
  ];
  const currentPrompt = prompts[turn];
  const previousAnswer = answers[answers.length - 1];
  const localProgress = `第 ${Math.min(turn + 1, prompts.length)} 问 · 共 ${prompts.length} 问`;

  function record(answer: string) {
    const value = answer.trim();
    if (!value || !currentPrompt) return;
    setAnswers((current) => [...current, { prompt: currentPrompt, answer: value }]);
    if (turn === 0) setHorizonAnswer(Object.entries(HORIZONS).find(([, label]) => label === value)?.[0] ?? "CURRENT");
    if (turn === 1) setStageAnswer(Object.entries(STAGES).find(([, label]) => label === value)?.[0] ?? "EXPLORING");
    const skipped = value === "暂不回答";
    if (turn === 2) onFacts(skipped ? "" : value);
    if (turn === 3) onUnknowns(skipped ? "" : value);
    if (turn === 4) onActions(skipped || value === "尚未行动" ? "" : value);
    if (turn === 5) onObservableResponses(skipped || value === "尚无回应" ? "" : value);
    if (turn === prompts.length - 1) {
      const combined = `${question}\n${answers.map((item) => item.answer).join("\n")}\n${value}`;
      const domain = inferDomain(combined);
      const desiredGoal = inferGoal(value);
      const allowed = GOALS_BY_DOMAIN[domain] ?? [];
      onStructured({
        domain,
        goal: allowed.includes(desiredGoal) ? desiredGoal : allowed[0] ?? "PLAN_NEXT_STEP",
        horizon: horizonAnswer,
        stage: stageAnswer,
        uncertainty: inferUncertainty(combined),
      });
    }
    setTurn((current) => current + 1);
    setDraft("");
  }

  function reset() {
    setTurn(0); setDraft(""); setAnswers([]); setHorizonAnswer(""); setStageAnswer("");
    onFacts(""); onUnknowns(""); onActions(""); onObservableResponses("");
    onSuggestion(null);
    onComplete(false);
  }

  function finish() {
    onSuggestion(null);
    onCompletionReason("ENOUGH");
    onComplete(true);
    onContinue();
  }

  function finishEarly() {
    const combined = `${question}\n${answers.map((item) => item.answer).join("\n")}`;
    const domain = inferDomain(combined);
    const desiredGoal = inferGoal(answers[answers.length - 1]?.answer ?? question);
    const allowed = GOALS_BY_DOMAIN[domain] ?? [];
    onStructured({
      domain,
      goal: allowed.includes(desiredGoal) ? desiredGoal : allowed[0] ?? "PLAN_NEXT_STEP",
      horizon: horizonAnswer || "CURRENT",
      stage: stageAnswer || "EXPLORING",
      uncertainty: inferUncertainty(combined),
    });
    onSuggestion(null);
    onCompletionReason("USER_EARLY");
    onComplete(true);
    onContinue();
  }

  const completed = turn >= prompts.length;
  return <div className="guided-intake">
    {!completed && <div className="discernment-turn" aria-live="polite">
      {previousAnswer && <div className="discernment-echo" key={`local-echo-${answers.length}`} aria-hidden="true"><span>{previousAnswer.prompt}</span><p>{previousAnswer.answer}</p></div>}
      <div className="discernment-progress"><span>{localProgress}</span><small>基础整理 · 可跳过，也可提前结束</small></div>
      <p className="discernment-understanding">{turn === 0 ? "先把这一问放进现实的时间范围里。" : "上一项已经记下。现在只看眼前这一件事。"}</p>
      <div className="discernment-current" key={`local-prompt-${turn}`}><img src="/fuxi-bagua-taiji.svg" alt="" /><p>{currentPrompt}</p></div>
    </div>}
    {!completed && turn === 0 && <div className="dialogue-options">{Object.entries(HORIZONS).map(([key, label]) => <button type="button" key={key} onClick={() => record(label)}><span>{label}</span></button>)}</div>}
    {!completed && turn === 1 && <div className="dialogue-options">{Object.entries(STAGES).map(([key, label]) => <button type="button" key={key} onClick={() => record(label)}><span>{label}</span></button>)}</div>}
    {!completed && turn > 1 && <div className="dialogue-compose"><textarea aria-label="回答当前问题" value={draft} maxLength={turn === 6 ? 300 : 1200} onChange={(event) => setDraft(event.target.value)} placeholder="只回答眼前这一问……" /><button type="button" disabled={!draft.trim()} onClick={() => record(draft)}>答完这一问</button></div>}
    {!completed && <div className="discernment-controls"><button type="button" onClick={() => record("暂不回答")}>跳过这一问</button><button type="button" onClick={finishEarly}>已经说清，提前结束</button></div>}
    {completed && <div className="dialogue-review discernment-complete"><p className="eyebrow">基础整理完成</p><h3>现实脉络已经分开</h3><p>这次使用的是基础引导，因此不会提出改写建议。下一页仍由你亲自定下最后这一问。</p><div className="dialogue-review-actions"><button type="button" onClick={finish}>继续定问</button><button type="button" className="text-button" onClick={reset}>重新辨识</button></div></div>}
    <p className="guided-boundary">辨识只整理你主动提供的内容，不会替你补写事实，也不参与后面的确定性排盘。</p>
  </div>;
}

function GuidedIntake(props: GuidedIntakeProps) {
  const { question, onFacts, onUnknowns, onActions, onObservableResponses, onSuggestion, onStructured, onCompletionReason, onComplete, onContinue } = props;
  const [mode, setMode] = useState<"ASKING" | "REVIEW" | "FALLBACK" | "STOPPED">("ASKING");
  const [sessionId] = useState(() => `intake-${crypto.randomUUID()}`);
  const [turns, setTurns] = useState<IntakeAnswer[]>([]);
  const [currentPrompt, setCurrentPrompt] = useState(FIRST_DISCERNMENT_QUESTION);
  const [assistantMessage, setAssistantMessage] = useState("先从眼前的进展开始，不必一次说完所有细节。");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [review, setReview] = useState<GuidedIntakeApiResponse | null>(null);
  const [reviewReason, setReviewReason] = useState<"ENOUGH" | "MAX_TURNS">("ENOUGH");
  const [pendingTurns, setPendingTurns] = useState<IntakeAnswer[] | null>(null);

  async function requestTurn(nextTurns: IntakeAnswer[], id: string) {
    setBusy(true); setError(""); setPendingTurns(nextTurns);
    try {
      const response = await fetch("/api/intake", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contract_version: "SITES_GUIDED_INTAKE_CONTRACT_V1",
          session_id: id,
          question_text: question.trim(),
          turns: nextTurns.map((item) => ({ question: item.prompt, answer: item.answer })),
          locale: "zh-CN",
        }),
      });
      const payload = await response.json() as GuidedIntakeApiResponse;
      if (!response.ok || !payload.status) throw new Error(payload.error || "辨识服务暂时不可用");
      setPendingTurns(null);
      setAssistantMessage(payload.assistant_message);
      if (payload.status === "COMPLETE") {
        setReview(payload); setReviewReason("ENOUGH"); setCurrentPrompt(""); setMode("REVIEW");
      } else if (nextTurns.length >= 8) {
        setReview(payload); setReviewReason("MAX_TURNS"); setCurrentPrompt(""); setMode("REVIEW");
      } else {
        setCurrentPrompt(payload.next_question ?? "请再说清一项你尚未确认的部分。"); setMode("ASKING");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "辨识服务暂时不可用");
      setMode("ASKING");
    } finally {
      setBusy(false);
    }
  }

  async function answerWithValue(rawValue: string) {
    const value = rawValue.trim();
    if (!value || !currentPrompt || !sessionId) return;
    const nextTurns = [...turns, { prompt: currentPrompt, answer: value }];
    setTurns(nextTurns); setDraft(""); setCurrentPrompt("");
    await requestTurn(nextTurns, sessionId);
  }

  async function answer() {
    await answerWithValue(draft);
  }

  async function retryTurn() {
    if (!pendingTurns || !sessionId || busy) return;
    await requestTurn(pendingTurns, sessionId);
  }

  function finishWithoutSuggestion() {
    onFacts(""); onUnknowns(""); onActions(""); onObservableResponses("");
    onSuggestion(null);
    onCompletionReason("USER_EARLY");
    onComplete(true);
    onContinue();
  }

  function completeDiscernment() {
    if (!review) return;
    onFacts(review.confirmed_facts.join("\n"));
    onUnknowns(review.unknowns.join("\n"));
    onActions(review.actions_already_taken.join("\n"));
    onObservableResponses(review.observable_responses.join("\n"));
    onSuggestion({ question: review.suggested_question, reason: review.question_change_reason });
    onStructured({
      domain: review.structured_intake.question_domain,
      goal: review.structured_intake.decision_goal,
      horizon: review.structured_intake.time_horizon,
      stage: review.structured_intake.decision_stage,
      uncertainty: review.structured_intake.key_uncertainty,
      riskProfile: review.structured_intake.decision_risk_profile,
    });
    onCompletionReason(reviewReason);
    onComplete(true);
    onContinue();
  }

  if (mode === "FALLBACK") return <LocalGuidedIntake {...props} />;

  const previousTurn = turns[turns.length - 1];
  return <div className="guided-intake ai-guided-intake">
    {mode === "ASKING" && <div className="discernment-turn" aria-live="polite">
      {previousTurn && <div className="discernment-echo" key={`ai-echo-${turns.length}`} aria-hidden="true"><span>{previousTurn.prompt}</span><p>{previousTurn.answer}</p></div>}
      <div className="discernment-progress"><span>第 {Math.min(turns.length + 1, 8)} 问</span><small>信息足够即结束 · 最多 8 问</small></div>
      {!busy && !error && <p className="discernment-understanding">{assistantMessage}</p>}
      {currentPrompt && !busy && !error && <div className="discernment-current" key={currentPrompt}><img src="/fuxi-bagua-taiji.svg" alt="" /><p>{currentPrompt}</p></div>}
      {busy && <div className="discernment-working" role="status"><span>你刚才的回答已经记下</span><p>正在从这句话里分清已知与未知，下一问会接着你刚才所说的内容。</p><span className="discernment-mist-scroll" aria-hidden="true"><img src="/discernment-mist-scroll-v1.png" alt="" /></span></div>}
      {error && <div className="discernment-recovery" role="alert"><span>前 {turns.length} 个回答都还在</span><p>{error.replace(/[。！？]+$/, "")}。不需要从头再答，只要从这里继续。</p><div><button type="button" disabled={busy} onClick={retryTurn}>继续这一轮</button><button type="button" className="text-button" onClick={() => setMode("FALLBACK")}>改用基础引导</button></div></div>}
    </div>}
    {mode === "ASKING" && !error && <div className="dialogue-compose"><textarea aria-label="回答当前问题" value={draft} maxLength={1200} disabled={busy || !currentPrompt} onChange={(event) => setDraft(event.target.value)} placeholder="只回答眼前这一问……" /><button type="button" disabled={busy || !draft.trim() || !currentPrompt} onClick={answer}>{busy ? "回答已记下" : "答完这一问"}</button></div>}
    {mode === "ASKING" && !error && <div className="discernment-controls"><button type="button" disabled={busy || !currentPrompt} onClick={() => answerWithValue("暂不回答")}>跳过这一问</button><button type="button" disabled={busy} onClick={() => setMode("STOPPED")}>已经说清，提前结束</button></div>}
    {mode === "REVIEW" && review && <div className="dialogue-review discernment-complete"><p className="eyebrow">辨识已经足够</p><h3>现在，可以定下真正要问的事</h3><p>我已经整理好这次对话。下一页只会在确有必要时提出一个更聚焦的问法，是否采用仍由你决定。</p><div className="dialogue-review-actions"><button type="button" onClick={completeDiscernment}>结束辨识，继续定问</button></div></div>}
    {mode === "STOPPED" && <div className="dialogue-review discernment-complete discernment-classic"><p className="eyebrow">《周易·系辞下》</p><blockquote>穷则变，变则通，通则久。</blockquote><div className="dialogue-review-actions"><button type="button" onClick={finishWithoutSuggestion}>继续定问</button></div></div>}
    <p className="guided-boundary">辨识只整理你主动提供的内容，不会替你补写事实，也不参与后面的确定性排盘。</p>
  </div>;
}

type FinalQuestionProps = {
  hidden: boolean;
  originalQuestion: string;
  suggestedQuestion: string;
  earlyExit: boolean;
  decisionMade: boolean;
  confirmed: boolean;
  onChooseOriginal: () => void;
  onChooseSuggestion: () => void;
  onConfirm: () => void;
};

function normalizedQuestion(value: string): string {
  return value.replace(/[\s，。！？、,.!?；;：:]/g, "").toLocaleLowerCase("zh-CN");
}

function FinalQuestion({ hidden, originalQuestion, suggestedQuestion, earlyExit, decisionMade, confirmed, onChooseOriginal, onChooseSuggestion, onConfirm }: FinalQuestionProps) {
  const hasSuggestion = suggestedQuestion.trim().length >= 6;
  const suggestionChangesQuestion = !earlyExit && hasSuggestion && normalizedQuestion(suggestedQuestion) !== normalizedQuestion(originalQuestion);
  const ready = earlyExit || !suggestionChangesQuestion || decisionMade;
  return <section id="final-question" className="inquiry-step inquiry-panel final-question-step" hidden={hidden} aria-labelledby="final-question-title">
    <div className="final-question-heading">
      <p className="eyebrow">观象之法 · 叁</p>
      <h3 id="final-question-title" tabIndex={-1}>定问</h3>
      <p>看过现实脉络之后<br />由你定下最后这一问</p>
    </div>

    <div className="final-question-workspace">
      {suggestionChangesQuestion && !decisionMade && <div className="question-change-proposal">
        <p>通过跟你的沟通，我建议你在卜卦之前，把问题更换为：</p>
        <blockquote>{suggestedQuestion}</blockquote>
        <p>会更能给到你切实的建议。你愿意更换吗？</p>
        <div><button type="button" onClick={onChooseSuggestion}>采取建议</button><button type="button" className="text-button" onClick={onChooseOriginal}>保持原题</button></div>
      </div>}

      {ready && <div className="final-question-ready" role="status" aria-live="polite">
        {earlyExit
          ? <p>我感受到你想尽快进入取数卜卦的环节，现在请心中再次默念你的问题，深呼吸。</p>
          : <><p>{decisionMade ? "那现在" : "现在"}已经更清晰你的现状，我们准备开始取数卜卦了。</p><strong>请心中再次默念你的问题，深呼吸。</strong></>}
      </div>}

      {ready && <div className="final-question-readiness">
        <button type="button" className="method-cta final-question-cta" aria-pressed={confirmed} onClick={onConfirm}><span className="method-cta-label">{confirmed ? "已经开始" : "开始卜卦"}</span></button>
      </div>}
    </div>
  </section>;
}

function JournalEntry({ record, onOpen, onUpdate, onDelete }: {
  record: JournalRecord;
  onOpen: (record: JournalRecord) => void;
  onUpdate: (id: string, draft: JournalDraft) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState<JournalDraft>({ action_text: record.action_text, review_on: record.review_on, reality_text: record.reality_text, learning_text: record.learning_text, status: record.status });
  const [busy, setBusy] = useState(false);
  const due = record.review_on && record.status === "OPEN" && record.review_on <= new Date().toISOString().slice(0, 10);
  async function saveReview() {
    setBusy(true);
    await onUpdate(record.id, { ...draft, status: draft.reality_text.trim() || draft.learning_text.trim() ? "REVIEWED" : "OPEN" });
    setBusy(false);
  }
  return <details className="journal-entry">
    <summary>
      <div><span>{record.status === "REVIEWED" ? "已复盘" : due ? "待复盘" : "观察中"}</span><h3>{record.question}</h3><small>{formatDate(record.created_at)} · {record.result.base_hexagram.name} → {record.result.changed_hexagram.name}</small></div>
      <b>{record.result.base_hexagram.symbol}</b>
    </summary>
    <div className="journal-entry-body">
      <button type="button" className="text-button" onClick={() => onOpen(record)}>重新打开完整结果</button>
      <label><span>当时准备采取的行动</span><textarea value={draft.action_text} maxLength={500} onChange={(event) => setDraft({ ...draft, action_text: event.target.value })} /></label>
      <label><span>计划回看日期</span><input type="date" value={draft.review_on ?? ""} onChange={(event) => setDraft({ ...draft, review_on: event.target.value || null })} /></label>
      <label><span>后来实际发生了什么</span><textarea value={draft.reality_text} maxLength={2000} placeholder="只写事实：谁做了什么、条件发生了什么变化。" onChange={(event) => setDraft({ ...draft, reality_text: event.target.value })} /></label>
      <label><span>这次经历修正了什么认识</span><textarea value={draft.learning_text} maxLength={2000} placeholder="哪些判断得到验证，哪些没有；下一次会怎样调整。" onChange={(event) => setDraft({ ...draft, learning_text: event.target.value })} /></label>
      <div className="journal-actions"><button type="button" disabled={busy} onClick={saveReview}>{busy ? "正在保存" : "保存复盘"}</button><button type="button" className="danger-link" onClick={() => onDelete(record.id)}>永久删除</button></div>
    </div>
  </details>;
}

export function JournalSection({ records, loading, message, hasUnsavedResult, onOpen, onUpdate, onDelete, onExport, onSaveCurrent }: {
  records: JournalRecord[];
  loading: boolean;
  message: string;
  hasUnsavedResult: boolean;
  onOpen: (record: JournalRecord) => void;
  onUpdate: (id: string, draft: JournalDraft) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onExport: () => void;
  onSaveCurrent: () => void;
}) {
  const openCount = records.filter((record) => record.status === "OPEN").length;
  return <section id="journal" className="journal scroll-section" data-reveal>
    <VerticalBrand />
    <header className="section-heading"><p className="eyebrow">事后再看，才知所见是否准确</p><h2>观事簿</h2><p>把一次观象留到现实中继续。记录采取了什么行动、后来发生了什么，再用新证据修正判断。</p></header>
    <div className="journal-intro"><p><b>{records.length}</b> 次记录</p><p><b>{openCount}</b> 次等待复盘</p><button type="button" className="text-button" disabled={!records.length} onClick={onExport}>导出全部记录</button></div>
    <p className="journal-privacy">记录与当前浏览器中的随机凭据相连，不要求姓名或账号。换设备前请先导出；你也可以随时逐条删除。</p>
    {hasUnsavedResult && <div className="journal-current-prompt"><p>刚才这次解读还没有保存。如果你希望以后回来看看事情实际怎样发展，可以先写下准备采取的行动，再存入观事簿。</p><button type="button" className="text-button" onClick={onSaveCurrent}>去保存刚才这次观象</button></div>}
    {loading ? <p className="journal-empty">正在打开观事簿……</p> : records.length ? <div className="journal-list">{records.map((record) => <JournalEntry key={record.id} record={record} onOpen={onOpen} onUpdate={onUpdate} onDelete={onDelete} />)}</div> : <div className="journal-empty"><BaguaMark /><div><p>这里还没有记录。每次解读结束后，你都可以写下准备怎么做并保存；过一段时间再回来记录真实结果。</p>{hasUnsavedResult && <button type="button" className="text-button" onClick={onSaveCurrent}>保存刚才这次观象</button>}</div></div>}
    {message && <p className="journal-message" role="status">{message}</p>}
  </section>;
}

function ResultView({ response, onEdit, onClear, onSave, saving, saved }: { response: ApiResponse; onEdit: () => void; onClear: () => void; onSave: (action: string, reviewOn: string | null) => Promise<void>; saving: boolean; saved: boolean }) {
  const result = response.deterministic_result;
  const initialAction = response.personalized_reading?.action ?? result?.personalized_reading?.action ?? result?.clarity_report.next_action ?? "";
  const [action, setAction] = useState(`我准备这样做：${initialAction}`);
  const [reviewOn, setReviewOn] = useState(defaultReviewDate());
  if (!result) return null;
  const report = result.clarity_report;
  const cultural = result.cultural_reading;
  const personalized = response.personalized_reading ?? result.personalized_reading;
  const sectionVisibility = resultSectionVisibility(Boolean(personalized));
  const questionResponses = personalized?.question_responses ?? [];
  const question = response.user_question ?? "你所问之事";
  const primaryJudgment = personalized?.core_judgment ?? report.answer;
  const primaryAction = personalized?.action ?? report.next_action;
  const baseClassic = cultural?.hexagrams[0];
  const upperPath = cultural?.number_path[0];
  const lowerPath = cultural?.number_path[1];
  const movingTerm = cultural?.terms.find((term) => term.title.startsWith("动爻"));
  const counsel = cultural?.classic_counsel ?? {
    quote: "穷则变，变则通，通则久。",
    source: "《周易·系辞下》",
  };

  return <section id="result" className="result-shell" aria-labelledby="result-title">
    <section className="result-overview scroll-section" data-reveal>
      <VerticalBrand />
      <p className="result-question">所问：{question}</p>
      <div className="result-verdict">
        <p className="eyebrow">本次所得之卦</p>
        <div className="hexagram-title"><strong>{result.base_hexagram.symbol}</strong><span>第 {result.base_hexagram.king_wen_number} 卦</span><h2 id="result-title" tabIndex={-1}>{result.base_hexagram.name}</h2></div>
        {baseClassic && <blockquote className="result-canonical"><b>卦辞</b>{baseClassic.canonical_text}</blockquote>}
      </div>
      <aside className="result-aside">
        <span>先不急着得到结论</span><p>接下来从本卦、互卦和变卦开始，看清这个卦怎样形成，又怎样落回你所问的事情。</p><a href="#why-reading">开始解读此卦</a>
      </aside>
    </section>

    <section id="why-reading" className="reading-scroll layered-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第一章 · 读卦</p><h2>本卦、互卦与变卦</h2><p>本卦看眼下的主要局面，互卦看内部怎样发展，变卦看变化之后重点转向哪里。先把三者逐一看清，再谈这件事应当如何判断。</p></header>
      {cultural ? <div className="canonical-grid">{cultural.hexagrams.map((item) => <article key={item.role} className="canonical-card">
        <header><span>{item.role}</span><strong>{item.symbol}</strong><div><small>第 {item.king_wen_number} 卦</small><h3>{item.name}</h3></div></header>
        <p className="reading-role">{item.reading_role}</p>
        <blockquote><b>《易》曰</b>{item.canonical_text}</blockquote>
        <p className="plain-note">{item.plain_note}</p>
      </article>)}</div> : <p className="compatibility-note">经典原文正在随排盘引擎同步，请稍后重新观卦。</p>}
    </section>

    <section id="deep-reading" className="evidence-scroll layered-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第二章 · 察变</p><h2>卦从何来，变化落在哪里</h2><p>这一章解释三数怎样成卦、动爻怎样带来变化，以及体用和旺衰怎样帮助我们判断当下能否承接。</p></header>
      <details className="reading-disclosure"><summary><span>三数如何成卦</span><small>第一数定上卦 · 第二数定下卦 · 第三数定动爻</small></summary>{cultural && <><div className="concept-explainer"><h3>先分清三个容易混在一起的概念</h3><p><b>上卦和下卦</b>都是由三条爻组成的“八经卦”，例如“离”。上下两个三爻卦叠在一起，才组成一个六爻的<b>本卦</b>，例如“离为火”。所以“离”与“离为火”不是同一个层级：前者是组成部分，后者是完整卦象。</p><p>本次上卦为<b>{upperPath?.result_name}</b>，下卦为<b>{lowerPath?.result_name}</b>，两者相叠得到本卦<b>{result.base_hexagram.name}</b>；第三个数字再确定其中哪一条爻发生变化。</p></div><div className="number-path">{cultural.number_path.map((item, index) => <article key={item.role}><span>{["壹", "贰", "叁"][index]}</span><b>{item.input_number}</b><i aria-hidden="true">→</i><strong>{item.role} · {item.result_name}</strong><small>{item.explanation}</small></article>)}</div></>}</details>
      <details className="reading-disclosure"><summary><span>本卦、互卦与变卦</span><small>眼下的局面 · 内部的发展 · 变化后的方向</small></summary><div className="concept-explainer"><h3>三个卦各自看什么</h3><p><b>本卦</b>看眼下最主要的局面；<b>互卦</b>从本卦中间四爻重新组合，帮助看事情内部怎样发展；<b>变卦</b>由动爻变化后形成，帮助看局面改变后会把重点带向哪里。</p></div><div className="hexagram-route">{[{ label: "本卦", value: result.base_hexagram, note: cultural?.hexagrams[0]?.reading_role }, { label: "互卦", value: result.mutual_hexagram, note: cultural?.hexagrams[1]?.reading_role }, { label: "变卦", value: result.changed_hexagram, note: cultural?.hexagrams[2]?.reading_role }].map(({ label, value, note }) => <article key={label}><span>{label}</span><strong>{value.symbol}</strong><h3>{value.name}</h3><small>第 {value.king_wen_number} 卦</small><p>{note}</p></article>)}</div></details>
      {cultural && <details className="reading-disclosure"><summary><span>本次动爻</span><small>{cultural.moving_line.line_name} · {cultural.moving_line.stage}</small></summary><article className="moving-line-reading"><header><span>什么是动爻</span><h3>{cultural.moving_line.line_name}</h3><p>一卦共有六条爻。动爻就是这次发生变化的那一条；它一变，本卦便随之成为变卦。</p></header><div className="moving-change"><section><span>变化之前</span><b>{result.base_hexagram.symbol} {result.base_hexagram.name}</b><p>这是没有发生本次变化前，事情眼下呈现的主要局面。</p></section><section><span>发生了什么</span><b>{cultural.moving_line.line_name}发生变化</b><p>变化落在“{cultural.moving_line.stage}”，说明这一处是本次最需要留意的转折。</p></section><section><span>变化之后</span><b>{result.changed_hexagram.symbol} {result.changed_hexagram.name}</b><p>这一爻改变后形成变卦，局面的重点也随之转向。</p></section></div><blockquote><b>爻辞原文</b>{cultural.moving_line.canonical_text}</blockquote><p className="moving-reality"><b>落到你所问的这件事上</b>{movingTerm?.current_effect}</p></article></details>}
      <details className="reading-disclosure"><summary><span>体用关系与旺衰</span><small>双方关系 · 变化方向 · 当前承接能力</small></summary><div className="term-grid">{cultural?.terms.map((term) => <article key={term.title}><span>{term.title}</span><h3>{term.current_value}</h3><p>{term.meaning}</p><strong>本次影响</strong><p>{term.current_effect}</p></article>)}</div></details>
      <p className="evidence-boundary">{report.boundary_note}</p>
    </section>

    {personalized && <section id="personalized-reading" className="personalized-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第三章 · 回到现实</p><h2>把卦象放回你所问的事</h2><p>以下文字只使用你明确写下的事实、未知项与程序排出的卦象；它不会把猜测补成事实，也不会替你做决定。</p></header>
      <div className="personalized-reading-grid">
        {questionResponses.length > 1 && <article className="question-responses"><span>逐项回答</span><ul>{questionResponses.map((item) => <li key={item.question_text}><b>{item.question_text}</b><p>{item.answer_text}</p></li>)}</ul></article>}
        <article><span>为什么这样判断</span><p>{personalized.explanation}</p></article>
        <article><span>落到你的现实</span><p>{personalized.reality_application}</p></article>
        <article><span>下一步</span><p>{personalized.action}</p></article>
        <article><span>何时需要转向</span><p>{personalized.switch_condition}</p></article>
      </div>
    </section>}

    <section className="final-guidance scroll-section" data-reveal>
      <VerticalBrand />
      <p className="final-question">你问的是：{question}</p>
      <header className="section-heading"><p className="eyebrow">解读 · 最终收束</p><h2>{primaryJudgment}</h2><p>{report.what_it_means}</p></header>
      {sectionVisibility.showGenericGuidance && <div className="guidance-columns"><article><span>当下有利</span><ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul></article><article><span>尤其注意</span><ul>{report.pause_signals.map((item) => <li key={item}>{item}</li>)}</ul></article></div>}
      <div className="next-action"><span>眼下可做的一步</span><p>{primaryAction}</p>{personalized && <small>若出现以下情况，应停下来重新判断：{personalized.switch_condition}</small>}</div>
      <section id="save-current-reading" className="save-current-reading"><p className="eyebrow">解读至此</p><h3>把这次所见留到以后再看</h3><p>到这里，这次卦象的解读就完成了。希望它已经帮你理清方向，也让你更清楚下一步准备怎么做。如果你想在事情有了进展后回来复盘，可以在下面写下准备采取的行动，并选择一个回看日期。</p><div className="save-observation">
        <label><span>我准备采取的行动</span><textarea aria-describedby="action-help" placeholder="请用自己的话写下：我接下来准备做什么、先观察什么，什么情况出现时会调整。" value={action} maxLength={500} onChange={(event) => setAction(event.target.value)} /></label>
        <label><span>我准备回来复盘的日期</span><input type="date" value={reviewOn} onChange={(event) => setReviewOn(event.target.value)} /></label>
        <button type="button" disabled={saving || saved || !action.trim()} onClick={() => onSave(action, reviewOn || null)}>{saved ? "已经存入观事簿" : saving ? "正在保存" : "存入观事簿"}</button>
        <small id="action-help">保存后，你可以在观事簿里重新打开本次卦象，记录后来实际发生了什么，并据此修正自己的判断。记录可以导出，也可以随时删除。</small>
      </div></section>
      <div className="result-actions"><button type="button" className="restart-button secondary" onClick={() => downloadReadingHtml(response)}>导出本次 HTML</button><a className="restart-button secondary" href="/journal">打开观事簿</a><button type="button" className="restart-button secondary" onClick={onEdit}>回到本题修改</button><button type="button" className="restart-button" onClick={onClear}>清空并再问一事</button></div>
      <blockquote className="classic-counsel"><p>{counsel.quote}</p><cite>{counsel.source}</cite></blockquote>
    </section>
  </section>;
}

function CastingLoader() {
  return <div className="casting" role="status"><BaguaMark /><p><b>正在观象</b><span>排定本卦 · 分清事实与未知 · 生成现实解读</span></p></div>;
}

function EntryArtwork({ className, imgRef }: { className: string; imgRef?: RefObject<HTMLImageElement | null> }) {
  return <picture className={className}>
    <source media="(max-aspect-ratio: 3 / 4)" srcSet="/hero-entry-mobile-v6.webp" />
    <source media="(max-aspect-ratio: 4 / 3)" srcSet="/hero-entry-square-v6.webp" />
    <img ref={imgRef} src="/hero-entry-wide-v6.webp" alt="" loading="eager" decoding="async" fetchPriority="high" />
  </picture>;
}

function EntryMistArtwork({ imgRef }: { imgRef?: RefObject<HTMLImageElement | null> }) {
  return <picture className="entry-mist-scene" aria-hidden="true">
    <source media="(max-aspect-ratio: 3 / 4)" srcSet="/hero-entry-mist-mobile-v2.webp" />
    <source media="(max-aspect-ratio: 4 / 3)" srcSet="/hero-entry-mist-square-v2.webp" />
    <img ref={imgRef} src="/hero-entry-mist-wide-v2.webp" alt="" loading="eager" decoding="async" fetchPriority="high" />
  </picture>;
}

const ENTRY_BIRDS = [
  { left: "4%", top: "58%", scale: ".72", flap: ".74s", delay: "-.16s", drift: "7.2s", frame: "0%" },
  { left: "19%", top: "42%", scale: ".56", flap: ".81s", delay: "-.48s", drift: "8.4s", frame: "33.333%" },
  { left: "36%", top: "66%", scale: ".82", flap: ".69s", delay: "-.31s", drift: "6.8s", frame: "66.666%" },
  { left: "53%", top: "31%", scale: ".62", flap: ".77s", delay: "-.62s", drift: "8.9s", frame: "100%" },
  { left: "69%", top: "51%", scale: ".76", flap: ".72s", delay: "-.27s", drift: "7.8s", frame: "33.333%" },
  { left: "84%", top: "23%", scale: ".51", flap: ".86s", delay: "-.55s", drift: "9.3s", frame: "66.666%" },
] as const;

export function GuanxiangApp() {
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("");
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [stage, setStage] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [riskProfile, setRiskProfile] = useState("STANDARD");
  const [facts, setFacts] = useState("");
  const [unknowns, setUnknowns] = useState("");
  const [actions, setActions] = useState("");
  const [observableResponses, setObservableResponses] = useState("");
  const [originalQuestion, setOriginalQuestion] = useState("");
  const [suggestedQuestion, setSuggestedQuestion] = useState("");
  const [, setSuggestionReason] = useState("");
  const [finalQuestionDraft, setFinalQuestionDraft] = useState("");
  const [finalQuestionDecisionMade, setFinalQuestionDecisionMade] = useState(false);
  const [finalQuestionConfirmed, setFinalQuestionConfirmed] = useState(false);
  const [discernmentCompletionReason, setDiscernmentCompletionReason] = useState<DiscernmentCompletionReason>("ENOUGH");
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [intakeComplete, setIntakeComplete] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState("");
  const [loading, setLoading] = useState(false);
  const [savingRecord, setSavingRecord] = useState(false);
  const [savedRecordId, setSavedRecordId] = useState<string | null>(null);
  const [homeNavigationVisible, setHomeNavigationVisible] = useState(false);
  const [entrySequenceStarted, setEntrySequenceStarted] = useState(false);
  const [entryReleased, setEntryReleased] = useState(false);
  const [methodReady, setMethodReady] = useState(false);
  const [questionConfirmed, setQuestionConfirmed] = useState(false);
  const [activeMethodLine, setActiveMethodLine] = useState<number | null>(null);
  const [previewMethodLine, setPreviewMethodLine] = useState<number | null>(null);
  const [methodWritingRun, setMethodWritingRun] = useState(0);
  const [titleAwake, setTitleAwake] = useState(false);
  const [soundOn, setSoundOn] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const entryHeroImageRef = useRef<HTMLImageElement | null>(null);
  const entryMistImageRef = useRef<HTMLImageElement | null>(null);
  const methodAdvanceTimerRef = useRef<number | null>(null);

  useEffect(() => {
    const openingSavedReading = Boolean(sessionStorage.getItem(JOURNAL_OPEN_KEY));
    if (!openingSavedReading) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    let cancelled = false;
    let frame = 0;
    let fallbackTimer = 0;
    const criticalArtworkReady = Promise.all(
      [entryHeroImageRef.current, entryMistImageRef.current].map((image) => image?.decode().catch(() => undefined)),
    );
    const fallbackReady = new Promise<void>((resolve) => {
      fallbackTimer = window.setTimeout(resolve, 1800);
    });
    void Promise.race([criticalArtworkReady, fallbackReady]).then(() => {
      if (cancelled) return;
      frame = window.requestAnimationFrame(() => {
        setEntrySequenceStarted(true);
        if (openingSavedReading) {
          setEntryReleased(true);
          setMethodReady(true);
        }
      });
    });
    return () => {
      cancelled = true;
      window.clearTimeout(fallbackTimer);
      window.cancelAnimationFrame(frame);
    };
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("entry-locked", !entryReleased);
    document.body.classList.toggle("entry-locked", !entryReleased);
    return () => {
      document.documentElement.classList.remove("entry-locked");
      document.body.classList.remove("entry-locked");
    };
  }, [entryReleased]);

  useEffect(() => {
    if (entryReleased) return;
    const blockScroll = (event: Event) => event.preventDefault();
    const blockScrollKeys = (event: KeyboardEvent) => {
      if (["ArrowDown", "ArrowUp", "End", "Home", "PageDown", "PageUp", " "].includes(event.key)) {
        event.preventDefault();
      }
    };
    const holdEntryPosition = () => {
      if (window.scrollX !== 0 || window.scrollY !== 0) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    };
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    window.addEventListener("wheel", blockScroll, { passive: false });
    window.addEventListener("touchmove", blockScroll, { passive: false });
    window.addEventListener("keydown", blockScrollKeys);
    window.addEventListener("scroll", holdEntryPosition, { passive: true });
    return () => {
      window.removeEventListener("wheel", blockScroll);
      window.removeEventListener("touchmove", blockScroll);
      window.removeEventListener("keydown", blockScrollKeys);
      window.removeEventListener("scroll", holdEntryPosition);
    };
  }, [entryReleased]);

  useEffect(() => {
    const updateNavigation = () => {
      const revealAt = Math.max(120, window.innerHeight * .62);
      setHomeNavigationVisible(window.scrollY >= revealAt);
    };
    updateNavigation();
    window.addEventListener("scroll", updateNavigation, { passive: true });
    window.addEventListener("resize", updateNavigation);
    return () => {
      window.removeEventListener("scroll", updateNavigation);
      window.removeEventListener("resize", updateNavigation);
    };
  }, []);

  useEffect(() => () => {
    audioRef.current?.pause();
    if (methodAdvanceTimerRef.current !== null) window.clearTimeout(methodAdvanceTimerRef.current);
  }, []);

  async function toggleSound() {
    const audio = audioRef.current;
    if (!audio) return;
    if (soundOn) {
      audio.pause();
      setSoundOn(false);
      return;
    }
    audio.volume = .18;
    try {
      await audio.play();
      setSoundOn(true);
    } catch {
      setSoundOn(false);
    }
  }

  function enterMethod() {
    setEntryReleased(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      document.getElementById("method")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    }));
  }

  function confirmMethodReady() {
    if (methodReady) return;
    setMethodReady(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    methodAdvanceTimerRef.current = window.setTimeout(() => {
      document.getElementById("inquiry")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      window.requestAnimationFrame(() => document.getElementById("inquiry-title")?.focus({ preventScroll: true }));
      methodAdvanceTimerRef.current = null;
    }, reducedMotion ? 0 : 780);
  }

  function writeMethodLine(index: number) {
    setPreviewMethodLine(null);
    setActiveMethodLine(index);
    setMethodWritingRun((run) => run + 1);
  }

  function applyQuestionExample(example: typeof QUESTION_EXAMPLES[number]) {
    setQuestion(example.text);
    setDomain(example.domain);
    setGoal("");
    setQuestionConfirmed(false);
    setIntakeComplete(false);
    setDiscernmentCompletionReason("ENOUGH");
    setFinalQuestionDecisionMade(false);
    setFinalQuestionConfirmed(false);
  }

  function confirmQuestion() {
    if (question.trim().length < 6) return;
    const nextQuestion = question.trim();
    setOriginalQuestion(nextQuestion);
    setFinalQuestionDraft(nextQuestion);
    setSuggestedQuestion("");
    setSuggestionReason("");
    setIntakeComplete(false);
    setDiscernmentCompletionReason("ENOUGH");
    setFinalQuestionDecisionMade(false);
    setFinalQuestionConfirmed(false);
    setQuestionConfirmed(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      document.getElementById("discernment")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    }));
  }

  function continueToFinalQuestion() {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      document.getElementById("final-question")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      document.getElementById("final-question-title")?.focus({ preventScroll: true });
    }));
  }

  function receiveQuestionSuggestion(value: { question: string; reason: string } | null) {
    setSuggestedQuestion(value?.question.trim() ?? "");
    setSuggestionReason(value?.reason.trim() ?? "");
    setFinalQuestionDraft(originalQuestion || question.trim());
    setFinalQuestionDecisionMade(false);
    setFinalQuestionConfirmed(false);
  }

  function chooseOriginalQuestion() {
    setFinalQuestionDraft(originalQuestion);
    setFinalQuestionDecisionMade(true);
    setFinalQuestionConfirmed(false);
  }

  function chooseSuggestedQuestion() {
    if (!suggestedQuestion.trim()) return;
    setFinalQuestionDraft(suggestedQuestion.trim());
    setFinalQuestionDecisionMade(true);
    setFinalQuestionConfirmed(false);
  }

  function confirmFinalQuestion() {
    const value = finalQuestionDraft.trim();
    if (value.length < 6) return;
    setQuestion(value);
    setFinalQuestionDraft(value);
    setFinalQuestionConfirmed(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      document.querySelector<HTMLElement>(".number-step")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
    }));
  }

  function finishPersonalizedRequest(payload: ApiResponse): void {
    sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
    if (payload.status !== "SUCCESS" || !payload.personalized_reading || !payload.deterministic_result?.clarity_report) {
      throw new Error(payload.error || "本次解读没有通过检查，也不会自动重新生成。");
    }
    setResponse(payload);
    setProgress("");
  }

  async function pollPersonalizedRequest(requestId: string, cancelled: () => boolean = () => false): Promise<void> {
    setProgress("正在结合卦象与现实信息生成解读。页面会自动取得同一任务的结果，不会重复生成。");
    try {
      const payload = await pollPersonalizedTask(requestId, {
        fetchResult: () => fetch(`/api/v4/meihua?request_id=${encodeURIComponent(requestId)}`, { cache: "no-store" }),
        sleep,
        cancelled,
      });
      if (payload) finishPersonalizedRequest(payload as ApiResponse);
    } catch (caught) {
      if (caught instanceof PersonalizedPollError && caught.terminal) sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
      throw caught;
    }
  }

  function personalizedErrorMessage(caught: unknown, requestId?: string): string {
    const message = caught instanceof Error ? caught.message : "查询生成结果时出现异常。";
    const taskId = caught instanceof PersonalizedPollError ? caught.requestId : requestId;
    return taskId ? `${message}（任务编号：${taskId}）` : message;
  }

  useEffect(() => {
    const activeRequestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (!activeRequestId || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(activeRequestId)) return;
    let cancelled = false;
    const resumeTimer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      void pollPersonalizedRequest(activeRequestId, () => cancelled)
        .catch((caught) => { if (!cancelled) setError(personalizedErrorMessage(caught, activeRequestId)); })
        .finally(() => { if (!cancelled) { setLoading(false); setProgress(""); } });
    }, 0);
    return () => { cancelled = true; window.clearTimeout(resumeTimer); };
  // An unfinished request is intentionally resumed only once when the formal page mounts.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { elements.forEach((item) => item.classList.add("is-visible")); return; }
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); } }), { threshold: .08, rootMargin: "0px 0px -3%" });
    elements.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, [response]);

  useEffect(() => {
    const saved = sessionStorage.getItem(JOURNAL_OPEN_KEY);
    if (!saved) return;
    sessionStorage.removeItem(JOURNAL_OPEN_KEY);
    let record: JournalRecord;
    try {
      record = JSON.parse(saved) as JournalRecord;
    } catch { return; }
    const timer = window.setTimeout(() => {
      setQuestion(record.question); setDomain(record.structured_intake.question_domain); setGoal(record.structured_intake.decision_goal); setHorizon(record.structured_intake.time_horizon); setStage(record.structured_intake.decision_stage); setUncertainty(record.structured_intake.key_uncertainty); setRiskProfile(record.structured_intake.decision_risk_profile ?? "STANDARD"); setNumbers(record.numbers.map(String)); setDiscernmentCompletionReason("ENOUGH"); setIntakeComplete(true); setAcknowledged(true); setSavedRecordId(record.id);
      setResponse({ status: "SUCCESS", user_question: record.question, structured_intake: record.structured_intake, deterministic_result: record.result, personalized_reading: record.result.personalized_reading ?? null });
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!response) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("result-title")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [response]);

  function editQuestion() {
    setResponse(null); setError("");
    window.setTimeout(() => document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  function clearQuestion() {
    setQuestion(""); setDomain(""); setGoal(""); setHorizon(""); setStage(""); setUncertainty(""); setRiskProfile("STANDARD");
    setFacts(""); setUnknowns(""); setActions(""); setObservableResponses("");
    setNumbers(["", "", ""]); setIntakeComplete(false); setDiscernmentCompletionReason("ENOUGH"); setFinalQuestionDecisionMade(false); setFinalQuestionConfirmed(false); setAcknowledged(false); setResponse(null); setError(""); setSavedRecordId(null);
    window.setTimeout(() => document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  async function saveObservation(actionText: string, reviewOn: string | null) {
    if (!response?.deterministic_result) return;
    setSavingRecord(true); setError("");
    const id = crypto.randomUUID();
    try {
      const request = await fetch("/api/journal", { method: "POST", headers: journalHeaders(), body: JSON.stringify({
        id, question: response.user_question ?? question.trim(), structured_intake: response.structured_intake ?? { question_domain: domain, decision_goal: goal, time_horizon: horizon, decision_stage: stage, key_uncertainty: uncertainty, decision_risk_profile: riskProfile },
        numbers: response.deterministic_result.input_numbers,
        result: { ...response.deterministic_result, ...(response.personalized_reading ? { personalized_reading: response.personalized_reading } : {}) },
        action_text: actionText, review_on: reviewOn,
      }) });
      const payload = await request.json() as { record?: JournalRecord; error?: string };
      if (!request.ok || !payload.record) throw new Error(payload.error || "这次观象暂时没有保存成功。");
      setSavedRecordId(id);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "这次观象暂时没有保存成功。"); }
    finally { setSavingRecord(false); }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResponse(null); setSavedRecordId(null);
    const activeRequestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (activeRequestId && /^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(activeRequestId)) {
      setLoading(true);
      try { await pollPersonalizedRequest(activeRequestId); }
      catch (caught) { setError(personalizedErrorMessage(caught, activeRequestId)); }
      finally { setLoading(false); setProgress(""); }
      return;
    }
    if (activeRequestId) sessionStorage.removeItem(ACTIVE_REQUEST_KEY);

    const factLines = nonemptyLines(facts);
    const unknownLines = nonemptyLines(unknowns);
    const actionLines = nonemptyLines(actions);
    const responseLines = nonemptyLines(observableResponses);
    const parsed = numbers.map(Number);
    const textLists = [factLines, unknownLines, actionLines, responseLines];
    if (question.trim().length < 6 || question.trim().length > 160 || !intakeComplete || !domain || !goal || !horizon || !stage || !uncertainty || !riskProfile || factLines.length < 1 || factLines.length > 8 || unknownLines.length < 1 || unknownLines.length > 6 || actionLines.length > 6 || responseLines.length > 6 || textLists.some((items) => items.some((item) => item.length > 400)) || parsed.some((n, index) => !numbers[index] || !Number.isInteger(n) || n < 1 || n > 999) || !acknowledged) {
      setError("请先完成正问与辨识，再静心填写三个 1–999 的整数，并确认使用边界。"); return;
    }
    setLoading(true); setProgress("正在提交本次观象任务……");
    const requestId = `sites-${crypto.randomUUID()}`;
    try {
      sessionStorage.setItem(ACTIVE_REQUEST_KEY, requestId);
      const body = JSON.stringify({
        contract_version: "SITES_PERSONALIZED_MEIHUA_CONTRACT_V1", request_id: requestId,
        question_text: question.trim(), question_domain: domain, decision_goal: goal,
        time_horizon: horizon, decision_stage: stage, key_uncertainty: uncertainty, decision_risk_profile: riskProfile,
        confirmed_facts: factLines, unknowns: unknownLines, options: [],
        actions_already_taken: actionLines, observable_responses: responseLines,
        numbers: parsed, locale: "zh-CN", client_timestamp: new Date().toISOString(),
        user_acknowledgements: { no_automatic_regeneration: true, user_statements_not_verified_facts: true },
      });
      let accepted = false;
      for (let attempt = 0; attempt < 3 && !accepted; attempt += 1) {
        try {
          const request = await fetch("/api/v4/meihua", { method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store", body });
          const payload = await request.json() as ApiResponse;
          if (request.status === 202) { accepted = true; break; }
          if (request.ok) { finishPersonalizedRequest(payload); return; }
          if (request.status !== 503) {
            sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
            throw new Error(payload.error || payload.errors?.[0]?.message || "本次未能生成结果。");
          }
        } catch (caught) {
          if (caught instanceof Error && !/Failed to fetch|fetch failed|network/i.test(caught.message)) throw caught;
        }
        await sleep(1_500);
      }
      await pollPersonalizedRequest(requestId);
    } catch (caught) { setError(personalizedErrorMessage(caught, requestId)); }
    finally { setLoading(false); setProgress(""); }
  }

  const emphasizedMethodLine = activeMethodLine ?? previewMethodLine;

  return <>
    <header className={`site-header home-header${homeNavigationVisible ? " is-visible" : ""}`} aria-hidden={!homeNavigationVisible}>
      <a className="wordmark" href="#top" tabIndex={homeNavigationVisible ? undefined : -1}>观象</a>
      <nav><a href="#method" tabIndex={homeNavigationVisible ? undefined : -1}>如何观</a><a href={methodReady ? "#inquiry" : "#method"} onClick={(event) => { if (!methodReady) { event.preventDefault(); document.getElementById("method-ready")?.focus(); } }} tabIndex={homeNavigationVisible ? undefined : -1}>开始问</a><a href="/journal" tabIndex={homeNavigationVisible ? undefined : -1}>观事簿</a></nav>
      <small>确定性排盘 · 个性化解读</small>
    </header>
    <main id="top" className="scroll-canvas">
      <section className={`hero entry-hero scroll-section${entrySequenceStarted ? " is-sequence-started" : ""}${titleAwake ? " is-title-awake" : ""}`} aria-labelledby="hero-title">
        <EntryArtwork className="entry-hero-final" imgRef={entryHeroImageRef} />
        <EntryMistArtwork imgRef={entryMistImageRef} />
        <EntryArtwork className="entry-title-focus" />
        <img className="entry-boat-life" src="/hero-boat-v1.png" alt="" aria-hidden="true" />
        <div className="entry-bird-flock" aria-hidden="true">
          {ENTRY_BIRDS.map((bird, index) => <span
            className="entry-bird"
            key={index}
            style={{
              "--bird-left": bird.left,
              "--bird-top": bird.top,
              "--bird-scale": bird.scale,
              "--bird-flap": bird.flap,
              "--bird-delay": bird.delay,
              "--bird-drift": bird.drift,
              "--bird-frame": bird.frame,
            } as CSSProperties}
          />)}
        </div>
        <h1 id="hero-title" className="sr-only">观象</h1>
        <p className="sr-only">心有所问 静观其象</p>
        <button type="button" className="hero-title-hotspot" aria-pressed={titleAwake} aria-label="让观象题字与水墨太极浮现" onPointerEnter={() => setTitleAwake(true)} onPointerLeave={() => setTitleAwake(false)} onFocus={() => setTitleAwake(true)} onBlur={() => setTitleAwake(false)} onClick={() => setTitleAwake((current) => !current)}><span className="sr-only">观象</span></button>
        <blockquote className="sr-only">寂然不动，感而遂通天下之故。</blockquote>
        <span className="sr-only">《周易·系辞上》</span>
        <audio ref={audioRef} src="/audio/guqin-zheng-diao.ogg" preload="none" loop />
        <button type="button" className="hero-sound-control" aria-pressed={soundOn} onClick={toggleSound}><span aria-hidden="true">{soundOn ? "静" : "琴"}</span><b>{soundOn ? "静音" : "闻琴"}</b></button>
        <button type="button" className="hero-scroll-cue" onClick={enterMethod}><span className="sr-only">了解观象之法</span></button>
      </section>

      <section id="method" className={`method scroll-section${methodReady ? " is-ready" : ""}`} data-reveal aria-labelledby="method-title">
        <VerticalBrand />
        <div className="method-stage">
          <div className="method-quote"><h2 id="method-title" aria-label="在天成象 在地成形 变化见矣" className={emphasizedMethodLine === null ? undefined : "has-active"}>{METHOD_CLASSIC_LINES.map((line, index) => <button key={line} type="button" className={`method-ink-line${emphasizedMethodLine === index ? " is-active" : ""}${activeMethodLine === index ? " is-writing" : ""}`} aria-pressed={activeMethodLine === index} aria-label={`${line} 点击观看整句书写过程`} onPointerEnter={(event) => { if (event.pointerType !== "touch" && activeMethodLine === null) setPreviewMethodLine(index); }} onPointerLeave={(event) => { if (event.pointerType !== "touch") setPreviewMethodLine(null); }} onFocus={() => { if (activeMethodLine === null) setPreviewMethodLine(index); }} onBlur={() => setPreviewMethodLine(null)} onClick={() => writeMethodLine(index)}><span className="method-line-label">{line}</span>{activeMethodLine === index && <span key={`${line}-${methodWritingRun}`} className="method-writing-layer" aria-hidden="true">{Array.from(line).map((character, characterIndex) => <i key={`${character}-${characterIndex}`} style={{ "--char-index": characterIndex } as CSSProperties}>{character}</i>)}</span>}</button>)}</h2><cite>《周易·系辞上》</cite></div>
          <div className="method-explainer">
            <p className="method-lead">接下来<br />我们尝试观象</p>
            <p className="method-breath"><span>请闭上眼睛</span><b>做三个呼吸</b></p>
          </div>
        </div>
        <div className="method-readiness"><button id="method-ready" className="method-cta" type="button" aria-label={methodReady ? "已定心，进入正问" : "开始正问"} aria-pressed={methodReady} aria-describedby="method-ready-status" onClick={confirmMethodReady}><span className="method-cta-label">{methodReady ? "已定心" : "开始正问"}</span></button><p id="method-ready-status" className="method-ready-status" role="status" aria-live="polite">{methodReady ? "准备状态已确认，正在进入正问。" : ""}</p></div>
      </section>

      <section id="inquiry" className="inquiry scroll-section" data-reveal hidden={!methodReady} aria-labelledby="inquiry-title">
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <div className="inquiry-stage">
            <header className="inquiry-heading">
              <p className="eyebrow">观象之法 · 壹</p>
              <h2 id="inquiry-title" tabIndex={-1}>正问</h2>
              <p>写下一件<br />真实具体的事</p>
            </header>

            <div className="inquiry-writing">
              <label className="question-label" htmlFor="primary-question"><span>此刻，你真正想问的是什么？</span></label>
              <textarea id="primary-question" aria-label="你真正想问的问题" aria-describedby="question-guidance question-count" placeholder="把心里的这一问，写在这里……" value={question} maxLength={160} onChange={(event) => { setQuestion(event.target.value); setQuestionConfirmed(false); setIntakeComplete(false); setDiscernmentCompletionReason("ENOUGH"); setFinalQuestionDecisionMade(false); setFinalQuestionConfirmed(false); }} />
              <div className="question-meta"><p id="question-guidance">先照此刻最自然的方式写。下一步，我们会陪你慢慢辨清事实、未知与真正的需要。</p><span id="question-count" aria-live="polite">{question.trim().length} / 160</span></div>

              <div className="question-examples"><header><span>若一时不知怎样开口</span><small>轻点一句，放入上方继续修改</small></header><div>{QUESTION_EXAMPLES.map((example, index) => <button type="button" key={example.text} aria-label={`参考${example.topic}例句：${example.text}`} onClick={() => applyQuestionExample(example)}><span>{String(index + 1).padStart(2, "0")} · {example.topic}</span><b>{example.text}</b></button>)}</div></div>

              <div className="inquiry-advance"><button type="button" disabled={question.trim().length < 6} onClick={confirmQuestion}><span>{questionConfirmed ? "这一问已写下" : "写好了，继续辨识"}</span></button><p role="status" aria-live="polite">{question.trim().length > 0 && question.trim().length < 6 ? "再写具体一些，至少六个字。" : ""}</p></div>
            </div>
          </div>

          <div className="inquiry-future-flow" hidden={!questionConfirmed}>
          <section id="discernment" className="inquiry-step inquiry-panel discernment-step">
            <header className="discernment-heading">
              <p className="eyebrow">观象之法 · 贰</p>
              <h3>辨识</h3>
              <p>为了能结合卦象，给你更具实际意义的建议，我还有几个问题请你回答。</p>
            </header>
            <div className="discernment-workspace">
              {originalQuestion.length >= 6 ? <GuidedIntake key={originalQuestion} question={originalQuestion} onFacts={setFacts} onUnknowns={setUnknowns} onActions={setActions} onObservableResponses={setObservableResponses} onSuggestion={receiveQuestionSuggestion} onStructured={({ domain: nextDomain, goal: nextGoal, horizon: nextHorizon, stage: nextStage, uncertainty: nextUncertainty, riskProfile: nextRiskProfile }) => { setDomain(nextDomain); setGoal(nextGoal); setHorizon(nextHorizon); setStage(nextStage); setUncertainty(nextUncertainty); if (nextRiskProfile) setRiskProfile(nextRiskProfile); }} onCompletionReason={setDiscernmentCompletionReason} onComplete={setIntakeComplete} onContinue={continueToFinalQuestion} /> : <p className="dialogue-prerequisite">先在上一步写下至少六个字的具体问题，辨识对话才会开始。</p>}
            </div>
          </section>

          <FinalQuestion hidden={!intakeComplete} originalQuestion={originalQuestion} suggestedQuestion={suggestedQuestion} earlyExit={discernmentCompletionReason === "USER_EARLY"} decisionMade={finalQuestionDecisionMade} confirmed={finalQuestionConfirmed} onChooseOriginal={chooseOriginalQuestion} onChooseSuggestion={chooseSuggestedQuestion} onConfirm={confirmFinalQuestion} />

          <section className="inquiry-step inquiry-panel number-step casting-number-step" hidden={!finalQuestionConfirmed} aria-labelledby="casting-title">
            <div className="casting-peony-scene" aria-hidden="true">
              <div className="casting-peony-backdrop" />
              {PEONY_BREATHS.map((breath, index) => <span
                className={`peony-bloom peony-bloom-scene-${index + 1}`}
                key={breath.numeral}
                style={{ "--breath-delay": `${index * 4.4}s` } as CSSProperties}
              >
                <img className="peony-bloom-image" src={breath.flower} alt="" />
                {PEONY_PETAL_MOTIONS.map((motion, petalIndex) => <img
                  className="peony-falling-petal"
                  src="/casting-peony-petal-v1.png"
                  alt=""
                  key={`${breath.numeral}-${petalIndex}`}
                  style={{
                    "--petal-delay": `${petalIndex * .72}s`,
                    "--petal-left": `${motion.left}%`,
                    "--petal-mid-x": `${motion.midX}vw`,
                    "--petal-late-x": `${motion.midX * 1.8}vw`,
                    "--petal-travel-x": `${motion.travelX}vw`,
                    "--petal-travel-y": `${motion.travelY}vh`,
                    "--petal-mid-spin": `${motion.spin * .28}deg`,
                    "--petal-late-spin": `${motion.spin * .62}deg`,
                    "--petal-spin": `${motion.spin}deg`,
                    "--petal-size": `${motion.size}px`,
                  } as CSSProperties}
                />)}
              </span>)}
            </div>
            <header className="final-question-heading casting-heading">
              <p className="eyebrow">观象之法 · 肆</p>
              <h3 id="casting-title" tabIndex={-1}>成卦</h3>
              <p>三息之间收束心念<br />凭当下所感取三个数</p>
            </header>

            <div className="casting-number-workspace">
              <p className="casting-instruction">闭上眼睛，缓缓呼吸三次，在心中再默念一遍确认后的问题。花瓣落下时，不必推算，只写下当下浮现的数。</p>
              <fieldset className="peony-number-field" aria-describedby="number-rule-note">
                <legend className="sr-only">依三次呼吸取三个整数</legend>
                {PEONY_BREATHS.map((breath, index) => <label
                  className={`peony-number peony-number-${index + 1}`}
                  key={breath.numeral}
                >
                  <span className="peony-number-copy"><b>{breath.numeral}</b><small>{breath.guidance}</small></span>
                  <input aria-label={`第${index + 1}个数字`} placeholder="1—999" type="number" inputMode="numeric" min="1" max="999" value={numbers[index]} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} />
                </label>)}
              </fieldset>
              <p id="number-rule-note" className="number-note">第一数定上卦，第二数定下卦，第三数定动爻。三个数字只交给程序，随后依既定规则排定本卦、互卦与变卦。</p>
            </div>
          </section>

          <section className="inquiry-step inquiry-panel cast-step" hidden={!finalQuestionConfirmed}><div className="step-heading"><span>伍</span><div><h3>观卦</h3><p>确认边界后，程序先独立完成确定性排盘，再结合你在辨识中提供的现实信息生成解释。</p></div></div>
            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：卦象提供一种观察角度，个性化文字只使用我写下的事实、未知项和程序排出的卦象；它不替代医疗、法律、财务等专业意见。生成失败不会自动重新生成；只有我主动保存时，结果才会进入观事簿。</span></label>
            {progress && <p className="generation-progress" role="status">{progress}</p>}
            {error && <p className="error" role="alert">{error}</p>}
            <button className="cast-button" disabled={loading}><BaguaMark />{loading ? "正在生成解读" : "观卦"}</button>
            {loading && <CastingLoader />}
          </section>
          </div>
        </form>
      </section>

      {response && <ResultView response={response} onEdit={editQuestion} onClear={clearQuestion} onSave={saveObservation} saving={savingRecord} saved={savedRecordId !== null} />}
      <aside className="version-note">卦象不是预先写好的判词，而是对当下结构的一次照见。所谓“穷则变，变则通”，心念与行动一变，后续条件也会随之改变。得顺势之象，不可因此停步；见阻力之象，也不必自弃。观象的意义，是让我们看见照旧前行可能抵达之处，从而及早准备、修正与行动。</aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span><nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私说明</a></nav></footer>
  </>;
}
