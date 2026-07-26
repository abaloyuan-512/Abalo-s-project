"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
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

const JOURNAL_KEY = "guanxiang-observation-key-v1";
const ACTIVE_REQUEST_KEY = "guanxiang-personalized-active-request-v1";
const JOURNAL_OPEN_KEY = "guanxiang-open-journal-record-v1";

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

type IntakeAnswer = { prompt: string; answer: string };
type GuidedIntakeProps = {
  question: string;
  onFacts: (value: string) => void;
  onUnknowns: (value: string) => void;
  onActions: (value: string) => void;
  onObservableResponses: (value: string) => void;
  onQuestion: (value: string) => void;
  onStructured: (value: { domain: string; goal: string; horizon: string; stage: string; uncertainty: string; riskProfile?: string }) => void;
  onComplete: (complete: boolean) => void;
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

function LocalGuidedIntake({ question, onFacts, onUnknowns, onActions, onObservableResponses, onQuestion, onStructured, onComplete }: GuidedIntakeProps) {
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

  function record(answer: string) {
    const value = answer.trim();
    if (!value || !currentPrompt) return;
    setAnswers((current) => [...current, { prompt: currentPrompt, answer: value }]);
    if (turn === 0) setHorizonAnswer(Object.entries(HORIZONS).find(([, label]) => label === value)?.[0] ?? "CURRENT");
    if (turn === 1) setStageAnswer(Object.entries(STAGES).find(([, label]) => label === value)?.[0] ?? "EXPLORING");
    if (turn === 2) onFacts(value);
    if (turn === 3) onUnknowns(value);
    if (turn === 4) onActions(value === "尚未行动" ? "" : value);
    if (turn === 5) onObservableResponses(value === "尚无回应" ? "" : value);
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
      onComplete(true);
    }
    setTurn((current) => current + 1);
    setDraft("");
  }

  function reset() {
    setTurn(0); setDraft(""); setAnswers([]); setHorizonAnswer(""); setStageAnswer("");
    onFacts(""); onUnknowns(""); onActions(""); onObservableResponses("");
    onComplete(false);
  }

  const completed = turn >= prompts.length;
  return <div className="guided-intake">
    <div className="dialogue-history" aria-live="polite">
      <div className="dialogue-row guide"><img src="/bagua-seal.png" alt="" /><p>我会一次问一个问题。你只需要说清已经知道的部分；不知道的，就明确留作未知。</p></div>
      {answers.map((item) => <div className="dialogue-pair" key={`${item.prompt}-${item.answer}`}><div className="dialogue-row guide"><img src="/bagua-seal.png" alt="" /><p>{item.prompt}</p></div><div className="dialogue-row user"><p>{item.answer}</p></div></div>)}
      {!completed && <div className="dialogue-row guide current"><img src="/bagua-seal.png" alt="" /><p>{currentPrompt}</p></div>}
    </div>
    {!completed && turn === 0 && <div className="dialogue-options">{Object.entries(HORIZONS).map(([key, label]) => <button type="button" key={key} onClick={() => record(label)}><span>{label}</span></button>)}</div>}
    {!completed && turn === 1 && <div className="dialogue-options">{Object.entries(STAGES).map(([key, label]) => <button type="button" key={key} onClick={() => record(label)}><span>{label}</span></button>)}</div>}
    {!completed && turn > 1 && <div className="dialogue-compose"><textarea aria-label="回答当前问题" value={draft} maxLength={turn === 6 ? 300 : 1200} onChange={(event) => setDraft(event.target.value)} placeholder="只回答眼前这一问……" /><button type="button" disabled={!draft.trim()} onClick={() => record(draft)}>答完这一问</button></div>}
    {completed && <div className="dialogue-review"><p className="eyebrow">辨识完成 · 最后确认</p><h3>这仍然是你真正想问的吗？</h3><p>如果对话之后，你发现心里真正关心的已经变了，可以在这里改写。最终排盘只会使用你确认后的这个问题。</p><textarea aria-label="最终确认的问题" value={question} maxLength={160} onChange={(event) => onQuestion(event.target.value)} /><button type="button" className="text-button" onClick={reset}>重新辨识</button></div>}
    <p className="guided-boundary">辨识只整理你主动提供的内容，不会替你补写事实，也不参与后面的确定性排盘。</p>
  </div>;
}

function GuidedIntake(props: GuidedIntakeProps) {
  const { question, onFacts, onUnknowns, onActions, onObservableResponses, onQuestion, onStructured, onComplete } = props;
  const [mode, setMode] = useState<"READY" | "ASKING" | "REVIEW" | "FALLBACK">("READY");
  const [sessionId, setSessionId] = useState("");
  const [turns, setTurns] = useState<IntakeAnswer[]>([]);
  const [currentPrompt, setCurrentPrompt] = useState("");
  const [assistantMessage, setAssistantMessage] = useState("我会根据你的回答，一次只问一个真正有帮助的问题。");
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [review, setReview] = useState<GuidedIntakeApiResponse | null>(null);

  function resetOutputs() {
    onFacts(""); onUnknowns(""); onActions(""); onObservableResponses(""); onComplete(false);
  }

  async function requestTurn(nextTurns: IntakeAnswer[], id: string) {
    setBusy(true); setError("");
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
      if (!response.ok || !payload.status) throw new Error(payload.error || "AI 辨识暂时不可用");
      setAssistantMessage(payload.assistant_message);
      if (payload.status === "COMPLETE") {
        setReview(payload); setCurrentPrompt(""); setMode("REVIEW");
      } else {
        setCurrentPrompt(payload.next_question ?? "请再说清一项你尚未确认的部分。"); setMode("ASKING");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "AI 辨识暂时不可用");
      setMode("READY");
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    resetOutputs(); setTurns([]); setDraft(""); setReview(null);
    const id = `intake-${crypto.randomUUID()}`;
    setSessionId(id);
    await requestTurn([], id);
  }

  async function answer() {
    const value = draft.trim();
    if (!value || !currentPrompt || !sessionId) return;
    const nextTurns = [...turns, { prompt: currentPrompt, answer: value }];
    setTurns(nextTurns); setDraft("");
    await requestTurn(nextTurns, sessionId);
  }

  function confirm(useSuggestion: boolean) {
    if (!review) return;
    if (useSuggestion) onQuestion(review.suggested_question);
    onFacts(review.confirmed_facts.join("\n"));
    onUnknowns(review.unknowns.join("\n"));
    onActions(review.actions_already_taken.join("\n"));
    onObservableResponses(review.observable_responses.join("\n"));
    onStructured({
      domain: review.structured_intake.question_domain,
      goal: review.structured_intake.decision_goal,
      horizon: review.structured_intake.time_horizon,
      stage: review.structured_intake.decision_stage,
      uncertainty: review.structured_intake.key_uncertainty,
      riskProfile: review.structured_intake.decision_risk_profile,
    });
    onComplete(true);
  }

  if (mode === "FALLBACK") return <LocalGuidedIntake {...props} />;

  return <div className="guided-intake ai-guided-intake">
    <div className="dialogue-history" aria-live="polite">
      <div className="dialogue-row guide"><img src="/bagua-seal.png" alt="" /><p>{assistantMessage}</p></div>
      {turns.map((item) => <div className="dialogue-pair" key={`${item.prompt}-${item.answer}`}><div className="dialogue-row guide"><img src="/bagua-seal.png" alt="" /><p>{item.prompt}</p></div><div className="dialogue-row user"><p>{item.answer}</p></div></div>)}
      {mode === "ASKING" && currentPrompt && <div className="dialogue-row guide current"><img src="/bagua-seal.png" alt="" /><p>{currentPrompt}</p></div>}
    </div>
    {mode === "READY" && <div className="dialogue-start"><button type="button" disabled={busy} onClick={start}>{busy ? "正在静心听你所问……" : turns.length ? "重新连接 AI 辨识" : "开始 AI 辨识"}</button>{error && <p role="alert">{error}。你也可以使用不调用 AI 的基础引导。</p>}{error && <button type="button" className="text-button" onClick={() => setMode("FALLBACK")}>使用基础引导继续</button>}</div>}
    {mode === "ASKING" && <div className="dialogue-compose"><textarea aria-label="回答 AI 当前问题" value={draft} maxLength={1200} onChange={(event) => setDraft(event.target.value)} placeholder="只回答眼前这一问……" /><button type="button" disabled={busy || !draft.trim()} onClick={answer}>{busy ? "正在辨识……" : "答完这一问"}</button></div>}
    {mode === "REVIEW" && review && <div className="dialogue-review"><p className="eyebrow">辨识完成 · 由你决定</p><h3>AI 建议把问题聚焦为</h3><blockquote>{review.suggested_question}</blockquote><p>{review.question_change_reason || "它更聚焦于你能核实的条件和下一步行动。"}</p><div className="dialogue-review-actions"><button type="button" onClick={() => confirm(true)}>采用建议问题</button><button type="button" className="text-button" onClick={() => confirm(false)}>保留我原来的问题</button><button type="button" className="text-button" onClick={start}>重新辨识</button></div></div>}
    <p className="guided-boundary">辨识只整理你主动提供的内容，不会替你补写事实，也不参与后面的确定性排盘。</p>
  </div>;
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

function EntryArtwork({ className }: { className: string }) {
  return <picture className={className}>
    <source media="(max-aspect-ratio: 3 / 4)" srcSet="/hero-entry-mobile-v2.png" />
    <source media="(max-aspect-ratio: 4 / 3)" srcSet="/hero-entry-square-v2.png" />
    <img src="/hero-entry-wide-v2.png" alt="" />
  </picture>;
}

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
  const [titleAwake, setTitleAwake] = useState(false);
  const [soundOn, setSoundOn] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const openingSavedReading = Boolean(sessionStorage.getItem(JOURNAL_OPEN_KEY));
    if (!openingSavedReading) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    const frame = window.requestAnimationFrame(() => {
      setEntrySequenceStarted(true);
      if (openingSavedReading) setEntryReleased(true);
    });
    return () => window.cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("entry-locked", !entryReleased);
    return () => document.body.classList.remove("entry-locked");
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

  function applyQuestionExample(example: typeof QUESTION_EXAMPLES[number]) {
    setQuestion(example.text);
    setDomain(example.domain);
    setGoal("");
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
      setQuestion(record.question); setDomain(record.structured_intake.question_domain); setGoal(record.structured_intake.decision_goal); setHorizon(record.structured_intake.time_horizon); setStage(record.structured_intake.decision_stage); setUncertainty(record.structured_intake.key_uncertainty); setRiskProfile(record.structured_intake.decision_risk_profile ?? "STANDARD"); setNumbers(record.numbers.map(String)); setIntakeComplete(true); setAcknowledged(true); setSavedRecordId(record.id);
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
    setNumbers(["", "", ""]); setIntakeComplete(false); setAcknowledged(false); setResponse(null); setError(""); setSavedRecordId(null);
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

  return <>
    <header className={`site-header home-header${homeNavigationVisible ? " is-visible" : ""}`} aria-hidden={!homeNavigationVisible}>
      <a className="wordmark" href="#top" tabIndex={homeNavigationVisible ? undefined : -1}>观象</a>
      <nav><a href="#method" tabIndex={homeNavigationVisible ? undefined : -1}>如何观</a><a href="#inquiry" tabIndex={homeNavigationVisible ? undefined : -1}>开始问</a><a href="/journal" tabIndex={homeNavigationVisible ? undefined : -1}>观事簿</a></nav>
      <small>确定性排盘 · 个性化解读</small>
    </header>
    <main id="top" className="scroll-canvas">
      <section className={`hero entry-hero scroll-section${entrySequenceStarted ? " is-sequence-started" : ""}${titleAwake ? " is-title-awake" : ""}`} aria-labelledby="hero-title">
        <EntryArtwork className="entry-hero-final" />
        <EntryArtwork className="entry-hero-picture" />
        <EntryArtwork className="entry-title-focus" />
        <EntryArtwork className="entry-life-layer entry-boat-life" />
        <EntryArtwork className="entry-life-layer entry-bird-life" />
        <img className="entry-ink-drop" src="/hero-ink-drop-v1.png" alt="" aria-hidden="true" />
        <img className="entry-ink-bloom" src="/hero-ink-whispers-v2.png" alt="" aria-hidden="true" />
        <h1 id="hero-title" className="sr-only">观象</h1>
        <p className="sr-only">心有所问 静观其象</p>
        <button type="button" className="hero-title-hotspot" aria-pressed={titleAwake} aria-label="让观象题字与水墨太极浮现" onPointerEnter={() => setTitleAwake(true)} onPointerLeave={() => setTitleAwake(false)} onFocus={() => setTitleAwake(true)} onBlur={() => setTitleAwake(false)} onClick={() => setTitleAwake((current) => !current)}><span className="sr-only">观象</span></button>
        <blockquote className="sr-only">寂然不动，感而遂通天下之故。</blockquote>
        <span className="sr-only">《周易·系辞上》</span>
        <audio ref={audioRef} src="/audio/guqin-zheng-diao.ogg" preload="none" loop />
        <button type="button" className="hero-sound-control" aria-pressed={soundOn} onClick={toggleSound}><span aria-hidden="true">{soundOn ? "静" : "琴"}</span><b>{soundOn ? "静音" : "闻琴"}</b></button>
        <button type="button" className="hero-scroll-cue" onClick={enterMethod}><span className="sr-only">了解观象之法</span></button>
      </section>

      <section id="method" className="method scroll-section" data-reveal aria-labelledby="method-title">
        <VerticalBrand />
        <div className="method-quote"><p className="eyebrow">观象之法</p><h2 id="method-title"><span className="sr-only">在天成象，在地成形，变化见矣。</span><span aria-hidden="true">在天成象，</span><span aria-hidden="true">在地成形，</span><span aria-hidden="true">变化见矣。</span></h2><cite>《周易·系辞上》</cite></div>
        <div className="method-explainer">
          <p className="method-lead">用三分钟，把一件拿不准的事理清方向，也看清下一步该留意什么。</p>
          <p>观象不会替你决定，也不会预先写好结果。我们会陪你写清所问、辨明事实与未知，再依三数成卦，把卦象的结构、变化与现实中值得观察的条件一层层展开。</p>
          <ol><li><span>壹</span><b>正问</b><p>写下一件具体而真实的事。</p></li><li><span>贰</span><b>辨识</b><p>在逐步对话中，找到真正想问的核心。</p></li><li><span>叁</span><b>成卦</b><p>静心取三数，程序依规则完成排盘。</p></li><li><span>肆</span><b>观卦</b><p>从本卦到变化，最后回到自己的处境。</p></li></ol>
          <div className="method-readiness"><p>如果你已经准备好了，请闭上眼睛，缓缓数过三个呼吸。再睁开眼时，我们从心中那件事开始。</p><a className="method-cta" href="#inquiry">我已准备好</a></div>
        </div>
      </section>

      <section id="inquiry" className="inquiry scroll-section" data-reveal>
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <header className="inquiry-heading"><p className="eyebrow">观象之法 · 四步</p><h2>从心中所问，走到眼前可行</h2><p>每次只处理一件具体的事。页面会按正问、辨识、成卦、观卦的顺序陪你完成，不需要一次填完一张问卷。</p></header>

          <section className="inquiry-step inquiry-panel"><div className="step-heading"><span>壹</span><div><h3>正问</h3><p>写下一件具体而真实的事。先按此刻最自然的方式写，后面还有机会重新确认。</p></div></div>
            <label className="question-label"><span>你真正想问的问题 *</span><textarea aria-label="你真正想问的问题" placeholder="例如：这次合作，我还应该继续投入吗？" value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} /><small>{question.trim().length} / 160 · 请用清晰具体的文字说出你想弄明白的事，这会帮助我们把抽象的卦意落到现实处境中。</small></label>
            <div className="question-examples"><header><span>不知怎样开口，可以从这些问题开始</span><small>点击任意一句，会自动填入上方</small></header><div>{QUESTION_EXAMPLES.map((example) => <button type="button" key={example.text} onClick={() => applyQuestionExample(example)}><span>{example.topic}</span><b>{example.text}</b></button>)}</div></div>
          </section>

          <section className="inquiry-step inquiry-panel"><div className="step-heading"><span>贰</span><div><h3>辨识</h3><p>一次只回答一问。我们把事实与未知分开，也帮助你辨认最初写下的问题是否真的问到了心里。</p></div></div>
            {question.trim().length >= 6 ? <GuidedIntake question={question} onFacts={setFacts} onUnknowns={setUnknowns} onActions={setActions} onObservableResponses={setObservableResponses} onQuestion={setQuestion} onStructured={({ domain: nextDomain, goal: nextGoal, horizon: nextHorizon, stage: nextStage, uncertainty: nextUncertainty, riskProfile: nextRiskProfile }) => { setDomain(nextDomain); setGoal(nextGoal); setHorizon(nextHorizon); setStage(nextStage); setUncertainty(nextUncertainty); if (nextRiskProfile) setRiskProfile(nextRiskProfile); }} onComplete={setIntakeComplete} /> : <p className="dialogue-prerequisite">先在上一步写下至少六个字的具体问题，辨识对话才会开始。</p>}
          </section>

          <section className="inquiry-step inquiry-panel number-step"><div className="step-heading"><span>叁</span><div><h3>成卦</h3><p>闭上眼睛，缓缓呼吸三次，在心中再重复一遍确认后的问题。准备好时，再凭当下所感取三个数。</p></div></div>
            <div className="breath-ritual" aria-label="三次呼吸提示"><span>一息 · 松开杂念</span><span>二息 · 回到所问</span><span>三息 · 心定取数</span></div>
            <fieldset className="numbers-slip"><legend className="sr-only">取三个整数</legend>{numbers.map((value, index) => <label key={index}><span>{["壹 · 上卦", "贰 · 下卦", "叁 · 动爻"][index]}</span><input aria-label={`第${index + 1}个数字`} placeholder="1—999" type="number" inputMode="numeric" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>)}</fieldset>
            <p className="number-note">第一数定上卦，第二数定下卦，第三数定动爻。程序随后依规则排定本卦、互卦与变卦。</p>
          </section>

          <section className="inquiry-step inquiry-panel cast-step"><div className="step-heading"><span>肆</span><div><h3>观卦</h3><p>确认边界后，程序先独立完成确定性排盘，再结合你在辨识中提供的现实信息生成解释。</p></div></div>
            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：卦象提供一种观察角度，个性化文字只使用我写下的事实、未知项和程序排出的卦象；它不替代医疗、法律、财务等专业意见。生成失败不会自动重新生成；只有我主动保存时，结果才会进入观事簿。</span></label>
            {progress && <p className="generation-progress" role="status">{progress}</p>}
            {error && <p className="error" role="alert">{error}</p>}
            <button className="cast-button" disabled={loading}><BaguaMark />{loading ? "正在生成解读" : "观卦"}</button>
            {loading && <CastingLoader />}
          </section>
        </form>
      </section>

      {response && <ResultView response={response} onEdit={editQuestion} onClear={clearQuestion} onSave={saveObservation} saving={savingRecord} saved={savedRecordId !== null} />}
      <aside className="version-note">卦象不是预先写好的判词，而是对当下结构的一次照见。所谓“穷则变，变则通”，心念与行动一变，后续条件也会随之改变。得顺势之象，不可因此停步；见阻力之象，也不必自弃。观象的意义，是让我们看见照旧前行可能抵达之处，从而及早准备、修正与行动。</aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span><nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私说明</a></nav></footer>
  </>;
}
