"use client";

import { FormEvent, useEffect, useState } from "react";
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
  IDENTIFY_OBSTACLES: "çœ‹æ¸…é˜»åŠ›ä¸æ¡ä»¶",
  PLAN_NEXT_STEP: "åˆ¤æ–­ä¸‹ä¸€æ­¥æ€ä¹ˆèµ°",
  PREPARE_COMMUNICATION: "å‡†å¤‡ä¸€æ¬¡é‡è¦æ²Ÿé€š",
  ADJUST_COMMITMENT_BOUNDARIES: "è°ƒæ•´æŠ•å…¥ä¸è¾¹ç•Œ",
  OBSERVE_VERIFY_SIGNALS: "ç¡®è®¤è¯¥è§‚å¯Ÿä»€ä¹ˆä¿¡å·",
} as const;
const GOALS_BY_DOMAIN: Record<string, (keyof typeof GOALS)[]> = {
  WORK_CAREER: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "OBSERVE_VERIFY_SIGNALS"],
  PROJECT_COOPERATION: Object.keys(GOALS) as (keyof typeof GOALS)[],
  RELATIONSHIP_COMMUNICATION: ["PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  PERSONAL_PLANNING: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
};
const HORIZONS = { CURRENT: "å½“å‰é˜¶æ®µ", NEXT_30_DAYS: "æœªæ¥ä¸‰åå¤©", NEXT_QUARTER: "æœªæ¥ä¸€ä¸ªå­£åº¦", NEXT_6_MONTHS: "æœªæ¥å…­ä¸ªæœˆ" } as const;
const STAGES = { EXPLORING: "åˆšå¼€å§‹äº†è§£", PREPARING: "å‡†å¤‡è¡ŒåŠ¨", ALREADY_ACTING: "æ­£åœ¨æ¨è¿›", WAITING_FEEDBACK: "ç­‰å¾…å›åº”" } as const;

const QUESTION_EXAMPLES = [
  { topic: "å·¥ä½œ", domain: "WORK_CAREER", text: "é¢å¯¹ç°åœ¨çš„å·¥ä½œæœºä¼šï¼Œæˆ‘ä¸‹ä¸€æ­¥æœ€è¯¥å…ˆç¡®è®¤ä»€ä¹ˆï¼Ÿ" },
  { topic: "åˆä½œ", domain: "PROJECT_COOPERATION", text: "è¿™æ¬¡åˆä½œï¼Œæˆ‘è¿˜åº”è¯¥ç»§ç»­æŠ•å…¥å—ï¼Ÿ" },
  { topic: "å…³ç³»", domain: "RELATIONSHIP_COMMUNICATION", text: "è¿™æ®µå…³ç³»ä¸€ç›´æ²¡æœ‰è¿›å±•ï¼Œæˆ‘è¿˜è¦ç»§ç»­ä¸»åŠ¨å—ï¼Ÿ" },
  { topic: "è§„åˆ’", domain: "PERSONAL_PLANNING", text: "æˆ‘ç°åœ¨å¼€å§‹è¿™é¡¹é•¿æœŸè®¡åˆ’ï¼Œæœ€éœ€è¦å…ˆå‡†å¤‡ä»€ä¹ˆï¼Ÿ" },
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
  const question = escapeHtml(response.user_question ?? "ä½ æ‰€é—®ä¹‹äº‹");
  const cultural = result.cultural_reading;
  const personalized = response.personalized_reading ?? result.personalized_reading;
  const report = result.clarity_report;
  const hexagrams = cultural?.hexagrams.map((item) => `<article><header><span>${escapeHtml(item.role)}</span><b>${escapeHtml(item.symbol)}</b><div><small>ç¬¬ ${item.king_wen_number} å¦</small><h2>${escapeHtml(item.name)}</h2></div></header><p>${escapeHtml(item.reading_role)}</p><blockquote><i>ã€Šæ˜“ã€‹æ›°</i>${escapeHtml(item.canonical_text)}</blockquote><p>${escapeHtml(item.plain_note)}</p></article>`).join("") ?? "";
  const terms = cultural?.terms.map((term) => `<article><span>${escapeHtml(term.title)}</span><h3>${escapeHtml(term.current_value)}</h3><p>${escapeHtml(term.meaning)}</p><b>æœ¬æ¬¡å½±å“</b><p>${escapeHtml(term.current_effect)}</p></article>`).join("") ?? "";
  const personal = personalized ? `<section><p class="eyebrow">å›åˆ°ä½ çš„ç°å®</p><h2>${escapeHtml(personalized.core_judgment)}</h2><div class="columns"><article><h3>ä¸ºä»€ä¹ˆè¿™æ ·åˆ¤æ–­</h3><p>${escapeHtml(personalized.explanation)}</p></article><article><h3>è½åˆ°ç°å®</h3><p>${escapeHtml(personalized.reality_application)}</p></article><article><h3>ä¸‹ä¸€æ­¥</h3><p>${escapeHtml(personalized.action)}</p></article><article><h3>ä½•æ—¶è½¬å‘</h3><p>${escapeHtml(personalized.switch_condition)}</p></article></div></section>` : "";
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>è§‚è±¡ Â· ${escapeHtml(result.base_hexagram.name)}</title><style>@font-face{font-family:gx;src:url(data:font/woff2;base64,) format('woff2')}*{box-sizing:border-box}body{margin:0;color:#2a2b25;background:#f2ead9;font-family:STKaiti,KaiTi,serif;letter-spacing:.055em}main{max-width:1180px;margin:auto;padding:9vw 7vw;background:url('data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="80" height="80"%3E%3Cfilter id="n"%3E%3CfeTurbulence baseFrequency=".7" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23n)" opacity=".025"/%3E%3C/svg%3E')}header.hero{text-align:center;min-height:58vh;display:grid;place-content:center;border-bottom:1px solid rgba(53,55,48,.2)}.hero b{font-size:8rem;font-weight:400}.hero h1{margin:.1em 0;font-size:4rem;font-weight:400}.hero p{color:#62665d}.eyebrow{color:#963b28;letter-spacing:.22em}section{padding:5rem 0;border-bottom:1px solid rgba(53,55,48,.2)}section>h2{font-size:2.5rem;font-weight:400;line-height:1.45}.grid,.columns{display:grid;grid-template-columns:repeat(3,1fr);gap:2.4rem}.columns{grid-template-columns:repeat(2,1fr)}article header{display:flex;gap:1rem;align-items:center}article header>b{font-size:3.4rem;font-weight:400}article h2,article h3{font-weight:400}article p{line-height:1.85;color:#50544b}blockquote{margin:1.5rem 0;padding:1.5rem 0;border-block:1px solid rgba(53,55,48,.16);line-height:1.9}blockquote i{display:block;color:#963b28;font-style:normal}.terms{display:grid;grid-template-columns:repeat(3,1fr);gap:2rem}.final{font-size:2rem;line-height:1.65;text-align:center}.boundary{font-size:.85rem;color:#62665d;line-height:1.8}@media(max-width:720px){main{padding:3rem 1.4rem}.hero b{font-size:5rem}.hero h1{font-size:2.8rem}.grid,.columns,.terms{grid-template-columns:1fr}}</style></head><body><main><header class="hero"><p class="eyebrow">æœ¬æ¬¡æ‰€å¾—ä¹‹å¦</p><b>${escapeHtml(result.base_hexagram.symbol)}</b><h1>ç¬¬ ${result.base_hexagram.king_wen_number} å¦ Â· ${escapeHtml(result.base_hexagram.name)}</h1><p>æ‰€é—®ï¼š${question}</p></header><section><p class="eyebrow">æœ¬å¦ Â· äº’å¦ Â· å˜å¦</p><div class="grid">${hexagrams}</div></section><section><p class="eyebrow">åŠ¨çˆ» Â· ä½“ç”¨ Â· æ—ºè¡°</p><div class="terms">${terms}</div></section>${personal}<section><p class="eyebrow">è§£è¯»è‡³æ­¤</p><p class="final">${escapeHtml(personalized?.action ?? report.next_action)}</p><p class="boundary">${escapeHtml(report.boundary_note)}</p></section></main></body></html>`;
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `è§‚è±¡-${result.base_hexagram.name}.html`;
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
  return <div className="vertical-brand" aria-label="è§‚è±¡"><b>è§‚</b><b>è±¡</b><i aria-hidden="true">è§‚</i></div>;
}

function BaguaMark({ className = "", decorative = true }: { className?: string; decorative?: boolean }) {
  return <img
    className={`bagua-mark ${className}`}
    src="/fuxi-bagua-taiji.svg"
    alt={decorative ? "" : "ä¼ç¾²å…ˆå¤©å¤ªæå…«å¦å›¾"}
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
  if (/å…³ç³»|å–œæ¬¢|è¡¨ç™½|æœ‹å‹|ä¼´ä¾£|æ²Ÿé€š|åŒäº‹ä¹‹é—´|å®¶äºº/.test(text)) return "RELATIONSHIP_COMMUNICATION";
  if (/é¡¹ç›®|åˆä½œ|å®¢æˆ·|åˆåŒ|æ–¹æ¡ˆ|åˆä¼™|èµ„æº/.test(text)) return "PROJECT_COOPERATION";
  if (/å·¥ä½œ|èŒä¸š|å²—ä½|å…¬å¸|å‡èŒ|ç¦»èŒ|æ±‚èŒ/.test(text)) return "WORK_CAREER";
  return "PERSONAL_PLANNING";
}

function inferGoal(text: string): keyof typeof GOALS {
  if (/æ²Ÿé€š|è¡¨è¾¾|è°ˆ|è¯´/.test(text)) return "PREPARE_COMMUNICATION";
  if (/è¾¹ç•Œ|æŠ•å…¥|ä»˜å‡º|åœæ­¢|é€€å‡º/.test(text)) return "ADJUST_COMMITMENT_BOUNDARIES";
  if (/å›åº”|ä¿¡å·|è¿¹è±¡|åé¦ˆ/.test(text)) return "OBSERVE_VERIFY_SIGNALS";
  if (/é˜»åŠ›|å›°éš¾|å¡ä½|åŸå› /.test(text)) return "IDENTIFY_OBSTACLES";
  return "PLAN_NEXT_STEP";
}

function inferUncertainty(text: string): "CONDITIONS" | "OTHER_RESPONSE" | "OWN_COMMITMENT" | "TIMING" {
  if (/æ—¶æœº|æ—¶å€™|å¤šä¹…|æ—¶é—´|ç°åœ¨/.test(text)) return "TIMING";
  if (/å›åº”|æ€åº¦|å¯¹æ–¹|åé¦ˆ|ç­”å¤/.test(text)) return "OTHER_RESPONSE";
  if (/æŠ•å…¥|ä»˜å‡º|åšæŒ|ç»§ç»­/.test(text)) return "OWN_COMMITMENT";
  return "CONDITIONS";
}

function LocalGuidedIntake({ question, onFacts, onUnknowns, onActions, onObservableResponses, onQuestion, onStructured, onComplete }: GuidedIntakeProps) {
  const [turn, setTurn] = useState(0);
  const [draft, setDraft] = useState("");
  const [answers, setAnswers] = useState<IntakeAnswer[]>([]);
  const [horizonAnswer, setHorizonAnswer] = useState("");
  const [stageAnswer, setStageAnswer] = useState("");
  const prompts = [
    "å…ˆç¡®å®šè§‚å¯Ÿçš„èŒƒå›´ï¼šä½ å¸Œæœ›åœ¨å¤šé•¿æ—¶é—´å†…çœ‹æ¸…è¿™ä»¶äº‹ï¼Ÿ",
    "è¿™ä»¶äº‹ç°åœ¨èµ°åˆ°äº†å“ªä¸€æ­¥ï¼Ÿ",
    "åˆ°ç›®å‰ä¸ºæ­¢ï¼Œå“ªäº›æ˜¯ä½ å·²ç»ç¡®è®¤çš„ç°å®äº‹å®ï¼Ÿè¯·ä¸è¦å†™æ¨æµ‹ã€‚",
    "å“ªä¸€éƒ¨åˆ†ä»ç„¶æœªçŸ¥ï¼Œä¸èƒ½å…ˆå½“ä½œäº‹å®ï¼Ÿ",
    "ä¸ºäº†è¿™ä»¶äº‹ï¼Œä½ å·²ç»é‡‡å–è¿‡ä»€ä¹ˆè¡ŒåŠ¨ï¼Ÿå¦‚æœè¿˜æ²¡æœ‰ï¼Œå¯ä»¥å†™â€œå°šæœªè¡ŒåŠ¨â€ã€‚",
    "äº‹æƒ…å·²ç»ç»™è¿‡ä½ æ€æ ·çš„å›åº”æˆ–åé¦ˆï¼Ÿå¦‚æœè¿˜æ²¡æœ‰ï¼Œå¯ä»¥å†™â€œå°šæ— å›åº”â€ã€‚",
    "å¦‚æœè¿™ä¸€æ¬¡åªèƒ½çœ‹æ¸…ä¸€ä»¶äº‹ï¼Œä½ æœ€å¸Œæœ›ç¡®è®¤ä»€ä¹ˆï¼Ÿ",
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
    if (turn === 4) onActions(v×MzÖÚ$z{-®éÜj×VW7F–öâ“²6WDFöÖ–â‡&V6÷&Bç7G'V7GW&VEö–çF¶RçVW7F–öåöFöÖ–â“²6WDvöÂ‡&V6÷&Bç7G'V7GW&VEö–çF¶RæFV6—6–öåövöÂ“²6WD†÷&—¦öâ‡&V6÷&Bç7G'V7GW&VEö–çF¶RçF–ÖUö†÷&—¦öâ“²6WE7FvR‡&V6÷&Bç7G'V7GW&VEö–çF¶RæFV6—6–öå÷7FvR“²6WEVæ6W'F–çG’‡&V6÷&Bç7G'V7GW&VEö–çF¶Ræ¶W•÷Væ6W'F–çG’“²6WE&—6µ&öf–ÆR‡&V6÷&Bç7G'V7GW&VEö–çF¶RæFV6—6–öå÷&—6µ÷&öf–ÆRóò%5DäD$B"“²6WDçVÖ&W'2‡&V6÷&BæçVÖ&W'2æÖ…7G&–ær’“²6WD–çF¶T6ö×ÆWFR‡G'VR“²6WD6¶æ÷vÆVFvVB‡G'VR“²6WE6fVE&V6÷&D–B‡&V6÷&Bæ–B“°¢6WE&W7öç6R‡²7FGW3¢%5T44U52"ÂW6W%÷VW7F–öã¢&V6÷&BçVW7F–öâÂ7G'V7GW&VEö–çF¶S¢&V6÷&Bç7G'V7GW&VEö–çF¶RÂFWFW&Ö–æ—7F–5÷&W7VÇC¢&V6÷&Bç&W7VÇBÂW'6öæÆ—¦VE÷&VF–æs¢&V6÷&Bç&W7VÇBçW'6öæÆ—¦VE÷&VF–æróòçVÆÂÒ“°¢ÒÂ“°¢&WGW&â‚’Óâv–æF÷ræ6ÆV%F–ÖV÷WB‡F–ÖW"“°¢ÒÂµÒ“° Ğ¢W6TVffV7B‚‚’Óâ°Ğ¢–b‚&W7öç6R’&WGW&ã°Ğ¢6öç7Bg&ÖRÒv–æF÷rç&WVW7Dæ–ÖF–öäg&ÖR‚‚’Óâ°Ğ¢Fö7VÖVçBævWDVÆVÖVçD'”–B‚'&W7VÇB"“òç67&öÆÄ–çFõf–Wr‡²&V†f–÷#¢'6Öö÷F‚"Â&Æö6³¢'7F'B"Ò“°Ğ¢Fö7VÖVçBævWDVÆVÖVçD'”–B‚'&W7VÇB×F—FÆR"“òæfö7W2‡²&WfVçE67&öÆÃ¢G'VRÒ“°Ğ¢Ò“°Ğ¢&WGW&â‚’Óâv–æF÷ræ6æ6VÄæ–ÖF–öäg&ÖR†g&ÖR“°Ğ¢ÒÂ·&W7öç6UÒ“°Ğ Ğ¢gVæ7F–öâVF—EVW7F–öâ‚’°Ğ¢6WE&W7öç6R†çVÆÂ“²6WDW'&÷"‚""“°Ğ¢v–æF÷rç6WEF–ÖV÷WB‚‚’ÓâFö7VÖVçBævWDVÆVÖVçD'”–B‚&–çV—'’"“òç67&öÆÄ–çFõf–Wr‡²&V†f–÷#¢'6Öö÷F‚"Ò’Â“°Ğ¢ĞĞ Ğ¢gVæ7F–öâ6ÆV%VW7F–öâ‚’°¢6WEVW7F–öâ‚""“²6WDFöÖ–â‚""“²6WDvöÂ‚""“²6WD†÷&—¦öâ‚""“²6WE7FvR‚""“²6WEVæ6W'F–çG’‚""“²6WE&—6µ&öf–ÆR‚%5DäD$B"“°Ğ¢6WDf7G2‚""“²6WEVæ¶æ÷vç2‚""“²6WD7F–öç2‚""“²6WDö'6W'f&ÆU&W7öç6W2‚""“°Ğ¢6WDçVÖ&W'2…²""Â""Â"%Ò“²6WD–çF¶T6ö×ÆWFR†fÇ6R“²6WD6¶æ÷vÆVFvVB†fÇ6R“²6WE&W7öç6R†çVÆÂ“²6WDW'&÷"‚""“²6WE6fVE&V6÷&D–B†çVÆÂ“°¢v–æF÷rç6WEF–ÖV÷WB‚‚’ÓâFö7VÖVçBævWDVÆVÖVçD'”–B‚&–çV—'’"“òç67&öÆÄ–çFõf–Wr‡²&V†f–÷#¢'6Öö÷F‚"Ò’Â“°Ğ¢ĞĞ Ğ¢7–æ2gVæ7F–öâ6fTö'6W'fF–öâ†7F–öåFW‡C¢7G&–ærÂ&Wf–Wtöã¢7G&–ærÂçVÆÂ’°¢–b‚&W7öç6SòæFWFW&Ö–æ—7F–5÷&W7VÇB’&WGW&ã°¢6WE6f–æu&V6÷&B‡G'VR“²6WDW'&÷"‚""“°¢6öç7B–BÒ7'—Fòç&æFöÕUT”B‚“°Ğ¢G'’°Ğ¢6öç7B&WVW7BÒv—BfWF6‚‚"ö’ö¦÷W&æÂ"Â²ÖWF†öC¢%õ5B"Â†VFW'3¢¦÷W&æÄ†VFW'2‚’Â&öG“¢¥4ôâç7G&–æv–g’‡°Ğ¢–BÂVW7F–öã¢&W7öç6RçW6W%÷VW7F–öâóòVW7F–öâçG&–Ò‚’Â7G'V7GW&VEö–çF¶S¢&W7öç6Rç7G'V7GW&VEö–çF¶Róò²VW7F–öåöFöÖ–ã¢FöÖ–âÂFV6—6–öåövöÃ¢vöÂÂF–ÖUö†÷&—¦öã¢†÷&—¦öâÂFV6—6–öå÷7FvS¢7FvRÂ¶W•÷Væ6W'F–çG“¢Væ6W'F–çG’ÂFV6—6–öå÷&—6µ÷&öf–ÆS¢&—6µ&öf–ÆRÒÀĞ¢çVÖ&W'3¢&W7öç6RæFWFW&Ö–æ—7F–5÷&W7VÇBæ–çWEöçVÖ&W'2ÀĞ¢&W7VÇC¢²ââç&W7öç6RæFWFW&Ö–æ—7F–5÷&W7VÇBÂâââ‡&W7öç6RçW'6öæÆ—¦VE÷&VF–ærò²W'6öæÆ—¦VE÷&VF–æs¢&W7öç6RçW'6öæÆ—¦VE÷&VF–ærÒ¢·Ò’ÒÀĞ¢7F–öå÷FW‡C¢7F–öåFW‡BÂ&Wf–Wuööã¢&Wf–WtöâÀĞ¢Ò’Ò“°Ğ¢6öç7B–ÆöBÒv—B&WVW7Bæ§6öâ‚’2²&V6÷&Có¢¦÷W&æÅ&V6÷&C²W'&÷#ó¢7G&–ærÓ°Ğ¢–b‚&WVW7Bæö²ÇÂ–ÆöBç&V6÷&B’F‡&÷ræWrW'&÷"‡–ÆöBæW'&÷"ÇÂ.‹ùjÊŠx.‹i¨.i{nk*iÈKùŞZÙh‰X©ş8""“°Ğ¢6WE6fVE&V6÷&D–B†–B“°¢Ò6F6‚†6Vv‡B’²6WDW'&÷"†6Vv‡B–ç7Fæ6VöbW'&÷"ò6Vv‡BæÖW76vR¢.‹ùjÊŠx.‹i¨.i{nk*iÈKùŞZÙh‰X©ş8""“²Ğ¢f–æÆÇ’²6WE6f–æu&V6÷&B†fÇ6R“²Ğ¢Ğ Ğ¢7–æ2gVæ7F–öâ7V&Ö—B†WfVçC¢f÷&ÔWfVçB’°Ğ¢WfVçBç&WfVçDFVfVÇB‚“²6WDW'&÷"‚""“²6WE&W7öç6R†çVÆÂ“²6WE6fVE&V6÷&D–B†çVÆÂ“°Ğ¢6öç7B7F—fU&WVW7D–BÒ6W76–öå7F÷&vRævWD—FVÒ„5D•dUõ$UTU5Eô´U’“°Ğ¢–b†7F—fU&WVW7D–Bbbõå´Õ¦×£Ó•Õ´Õ¦×£Ó’åòÕ×³Ãs—ÒBòçFW7B†7F—fU&WVW7D–B’’°Ğ¢6WDÆöF–ær‡G'VR“°Ğ¢G'’²v—BöÆÅW'6öæÆ—¦VE&WVW7B†7F—fU&WVW7D–B“²ĞĞ¢6F6‚†6Vv‡B’²6WDW'&÷"‡W'6öæÆ—¦VDW'&÷$ÖW76vR†6Vv‡BÂ7F—fU&WVW7D–B’“²ĞĞ¢f–æÆÇ’²6WDÆöF–ær†fÇ6R“²6WE&öw&W72‚""“²ĞĞ¢&WGW&ã°Ğ¢ĞĞ¢–b†7F—fU&WVW7D–B’6W76–öå7F÷&vRç&VÖ÷fT—FVÒ„5D•dUõ$UTU5Eô´U’“°Ğ Ğ¢6öç7Bf7DÆ–æW2ÒæöæV×G”Æ–æW2†f7G2“°Ğ¢6öç7BVæ¶æ÷väÆ–æW2ÒæöæV×G”Æ–æW2‡Væ¶æ÷vç2“°Ğ¢6öç7B7F–öäÆ–æW2ÒæöæV×G”Æ–æW2†7F–öç2“°Ğ¢6öç7B&W7öç6TÆ–æW2ÒæöæV×G”Æ–æW2†ö'6W'f&ÆU&W7öç6W2“°Ğ¢6öç7B'6VBÒçVÖ&W'2æÖ„çVÖ&W"“°Ğ¢6öç7BFW‡DÆ—7G2Ò¶f7DÆ–æW2ÂVæ¶æ÷väÆ–æW2Â7F–öäÆ–æW2Â&W7öç6TÆ–æW5Ó°Ğ¢–b‡VW7F–öâçG&–Ò‚’æÆVæwF‚ÂbÇÂVW7F–öâçG&–Ò‚’æÆVæwF‚âcÇÂ–çF¶T6ö×ÆWFRÇÂFöÖ–âÇÂvöÂÇÂ†÷&—¦öâÇÂ7FvRÇÂVæ6W'F–çG’ÇÂ&—6µ&öf–ÆRÇÂf7DÆ–æW2æÆVæwF‚ÂÇÂf7DÆ–æW2æÆVæwF‚â‚ÇÂVæ¶æ÷väÆ–æW2æÆVæwF‚ÂÇÂVæ¶æ÷väÆ–æW2æÆVæwF‚âbÇÂ7F–öäÆ–æW2æÆVæwF‚âbÇÂ&W7öç6TÆ–æW2æÆVæwF‚âbÇÂFW‡DÆ—7G2ç6öÖR‚†—FV×2’Óâ—FV×2ç6öÖR‚†—FVÒ’Óâ—FVÒæÆVæwF‚âC’’ÇÂ'6VBç6öÖR‚†âÂ–æFW‚’ÓâçVÖ&W'5¶–æFW…ÒÇÂçVÖ&W"æ—4–çFVvW"†â’ÇÂâÂÇÂââ““’’ÇÂ6¶æ÷vÆVFvVB’°¢6WDW'&÷"‚.Šû~XXZèÎh‰jÚ>™zîKˆî‹êŠønûÈÎXhŞ™Ù[ø>Z¾XiKˆKŠ¢(	3““’y¨Ni[Ni[ûÈÎ[›nzîŠêNKÛşyJ‹ëyXÎ8""“²&WGW&ã°¢ĞĞ¢6WDÆöF–ær‡G'VR“²6WE&öw&W72‚.jÚ>YÊhùKªNiÊÎjÊŠx.‹K»¾Xª(
n(
b"“°Ğ¢6öç7B&WVW7D–BÒ6—FW2ÒG¶7'—Fòç&æFöÕUT”B‚—Ö°Ğ¢G'’°Ğ¢6W76–öå7F÷&vRç6WD—FVÒ„5D•dUõ$UTU5Eô´U’Â&WVW7D–B“°Ğ¢6öç7B&öG’Ò¥4ôâç7G&–æv–g’‡°Ğ¢6öçG&7E÷fW'6–öã¢%4•DU5õU%4ôäÄ•¤TEôÔT”…Tô4ôåE$5Eõc"Â&WVW7Eö–C¢&WVW7D–BÀĞ¢VW7F–öå÷FW‡C¢VW7F–öâçG&–Ò‚’ÂVW7F–öåöFöÖ–ã¢FöÖ–âÂFV6—6–öåövöÃ¢vöÂÀĞ¢F–ÖUö†÷&—¦öã¢†÷&—¦öâÂFV6—6–öå÷7FvS¢7FvRÂ¶W•÷Væ6W'F–çG“¢Væ6W'F–çG’ÂFV6—6–öå÷&—6µ÷&öf–ÆS¢&—6µ&öf–ÆRÀĞ¢6öæf—&ÖVEöf7G3¢f7DÆ–æW2ÂVæ¶æ÷vç3¢Væ¶æ÷väÆ–æW2Â÷F–öç3¢µÒÀĞ¢7F–öç5öÇ&VG•÷F¶Vã¢7F–öäÆ–æW2Âö'6W'f&ÆU÷&W7öç6W3¢&W7öç6TÆ–æW2ÀĞ¢çVÖ&W'3¢'6VBÂÆö6ÆS¢'¦‚Ô4â"Â6Æ–VçE÷F–ÖW7F×¢æWrFFR‚’çFô•4õ7G&–ær‚’ÀĞ¢W6W%ö6¶æ÷vÆVFvVÖVçG3¢²æõöWFöÖF–5÷&VvVæW&F–öã¢G'VRÂW6W%÷7FFVÖVçG5öæ÷E÷fW&–f–VEöf7G3¢G'VRÒÀĞ¢Ò“°Ğ¢ÆWB66WFVBÒfÇ6S°Ğ¢f÷"†ÆWBGFV×BÒ²GFV×BÂ2bb66WFVC²GFV×B³Ò’°Ğ¢G'’°Ğ¢6öç7B&WVW7BÒv—BfWF6‚‚"ö’÷cBöÖV–‡V"Â²ÖWF†öC¢%õ5B"Â†VFW'3¢²$6öçFVçBÕG—R#¢&Æ–6F–öâö§6öâ"ÒÂ66†S¢&æò×7F÷&R"Â&öG’Ò“°Ğ¢6öç7B–ÆöBÒv—B&WVW7Bæ§6öâ‚’2•&W7öç6S°Ğ¢–b‡&WVW7Bç7FGW2ÓÓÒ#"’²66WFVBÒG'VS²'&V³²ĞĞ¢–b‡&WVW7Bæö²’²f–æ—6…W'6öæÆ—¦VE&WVW7B‡–ÆöB“²&WGW&ã²ĞĞ¢–b‡&WVW7Bç7FGW2ÓÒS2’°Ğ¢6W76–öå7F÷&vRç&VÖ÷fT—FVÒ„5D•dUõ$UTU5Eô´U’“°Ğ¢F‡&÷ræWrW'&÷"‡–ÆöBæW'&÷"ÇÂ–ÆöBæW'&÷'3òå³ÓòæÖW76vRÇÂ.iÊÎjÊiÊ®ˆ;ŞyIşh‰{¹>iéÎ8""“°Ğ¢ĞĞ¢Ò6F6‚†6Vv‡B’°Ğ¢–b†6Vv‡B–ç7Fæ6VöbW'&÷"bbôf–ÆVBFòfWF6‡ÆfWF6‚f–ÆVGÆæWGv÷&²ö’çFW7B†6Vv‡BæÖW76vR’’F‡&÷r6Vv‡C°Ğ¢ĞĞ¢v—B6ÆVWƒóS“°Ğ¢ĞĞ¢v—BöÆÅW'6öæÆ—¦VE&WVW7B‡&WVW7D–B“°Ğ¢Ò6F6‚†6Vv‡B’²6WDW'&÷"‡W'6öæÆ—¦VDW'&÷$ÖW76vR†6Vv‡BÂ&WVW7D–B’“²ĞĞ¢f–æÆÇ’²6WDÆöF–ær†fÇ6R“²6WE&öw&W72‚""“²ĞĞ¢ĞĞ Ğ¢&WGW&âÃàĞ¢Æ†VFW"6Æ74æÖSÒ'6—FRÖ†VFW"#àĞ¢Æ6Æ74æÖSÒ'v÷&FÖ&²"‡&VcÒ"7F÷#îŠx.‹ÂöàĞ¢ÆæcãÆ‡&VcÒ"6ÖWF†öB#îZh.KÙ^Šx#ÂöãÆ‡&VcÒ"6–çV—'’#î[ÈZx¾™zãÂöãÆ‡&VcÒ"ö¦÷W&æÂ#îŠx.K¨¾{óÂöãÂöæcà¢Ç6ÖÆÃîzîZé®h
~hé.y¹‚+rKŠ®h
~XÉnŠz>Šû³Â÷6ÖÆÃàĞ¢Âö†VFW#àĞ¢ÆÖ–â–CÒ'F÷"6Æ74æÖSÒ'67&öÆÂÖ6çf2#àĞ¢Ç6V7F–öâ6Æ74æÖSÒ&†W&ò67&öÆÂ×6V7F–öâ"FF×&WfVÂ&–ÖÆ&VÆÆVF'“Ò&†W&ò×F—FÆR#à¢ÆF—b6Æ74æÖSÒ&†W&òÖÆö6·W#à¢Ç6Æ74æÖSÒ&†W&òÖÖ÷GFò#î[ø>iÈh˜™zîûÈÎ™ÙŠx.X[n‹8#Â÷à¢Æ–Ör6Æ74æÖSÒ&†W&ò×6VÂ"7&3Ò"ö&wV×6VÂçær"ÇCÒ""&–Ö†–FFVãÒ'G'VR"óà¢Æƒ–CÒ&†W&ò×F—FÆR#ãÇ7ãîŠx#Â÷7ããÇ7ãî‹Â÷7ããÂöƒà¢ÂöF—cà¢ÆF—b6Æ74æÖSÒ&†W&òÖ6Æ76–2#à¢Ç7â6Æ74æÖSÒ&†W&òÖ–æ²Ö&ÆööÒ"&–Ö†–FFVãÒ'G'VR#ãÆ–Ör7&3Ò"ö–æ²ÖvöÆFVâÖÆæG66Rçær"ÇCÒ""óãÂ÷7ãà¢Æ&Æö6·V÷FSîZø.xKnKˆŞXªûÈÎhIşˆÎ˜.˜	®ZJKˆ¾K˜¾iX^8#Âö&Æö6·V÷FSà¢Æ6—FSî8®Yi‰<+~{;¾‹éîKˆ®8³Âö6—FSà¢ÂöF—cà¢Æ6Æ74æÖSÒ&†W&ò×67&öÆÂÖ7VR"‡&VcÒ"6ÖWF†öB#îY	Kˆ²+rŠx.k9SÂöà¢Â÷6V7F–öãà Ğ¢Ç6V7F–öâ–CÒ&ÖWF†öB"6Æ74æÖSÒ&ÖWF†öB67&öÆÂ×6V7F–öâ"FF×&WfVÂ&–ÖÆ&VÆÆVF'“Ò&ÖWF†öB×F—FÆR#à¢ÅfW'F–6Ä'&æBóà¢ÆF—b6Æ74æÖSÒ&ÖWF†öB×V÷FR#ãÇ6Æ74æÖSÒ&W–V'&÷r#îŠx.‹K˜¾k9SÂ÷ãÆƒ"–CÒ&ÖWF†öB×F—FÆR#ãÇ7â6Æ74æÖSÒ'7"ÖöæÇ’#îYÊZJh‰‹ûÈÎYÊYËh‰[Ú.ûÈÎXùXÉnŠxyú>8#Â÷7ããÇ7â&–Ö†–FFVãÒ'G'VR#îYÊZJh‰‹ûÈÃÂ÷7ããÇ7â&–Ö†–FFVãÒ'G'VR#îYÊYËh‰[Ú.ûÈÃÂ÷7ããÇ7â&–Ö†–FFVãÒ'G'VR#îXùXÉnŠxyú>8#Â÷7ããÂöƒ#ãÆ6—FSî8®Yi‰<+~{;¾‹éîKˆ®8³Âö6—FSãÂöF—cà¢ÆF—b6Æ74æÖSÒ&ÖWF†öBÖW‡Æ–æW"#à¢Ç6Æ74æÖSÒ&ÖWF†öBÖÆVB#îyJKˆXˆn™)şûÈÎh¨®KˆK»nh»şKˆŞXxny¨NK¨¾ynkˆ^ikY	ûÈÎK™şyÈ¾kˆ^Kˆ¾KˆjÚ^Šú^yYhHşK¸K˜8#Â÷à¢ÇîŠx.‹KˆŞKÉ®i»şKÚXk>Zé®ûÈÎK™şKˆŞKÉ®š(NXXXiZ[Ş{¹>iéÎ8.h‰KºÎKÉ®™š®KÚXikˆ^h˜™zî8‹êiˆîK¨¾ZéîKˆîiÊ®yú^ûÈÎXhŞKéŞKˆi[h‰XÚnûÈÎh¨®XÚn‹y¨N{¹>ièN8XùXÉnKˆîxëZéîKŠŞXÎ[é~Šx.Zùşy¨NiÚK»nKˆ[.[.[^[È8#Â÷à¢ÆöÃãÆÆ“ãÇ7ãîZ;“Â÷7ããÆ#îjÚ>™zãÂö#ãÇîXiKˆ¾KˆK»nX[~KÙ>ˆÎyÉşZéîy¨NK¨¾8#Â÷ãÂöÆ“ãÆÆ“ãÇ7ãî‹KÂ÷7ããÆ#î‹êŠøcÂö#ãÇîYÊ˜	jÚ^ZûŠùŞKŠŞûÈÎh›îX‹yÉşjÚ>h;>™zîy¨Nj[ø>8#Â÷ãÂöÆ“ãÆÆ“ãÇ7ãîXøÂ÷7ããÆ#îh‰XÚcÂö#ãÇî™Ù[ø>XùnKˆi[ûÈÎzˆ¾[¨şKéŞŠxNX‰ZèÎh‰hé.y¹8#Â÷ãÂöÆ“ãÆÆ“ãÇ7ãîˆ(cÂ÷7ããÆ#îŠx.XÚcÂö#ãÇîK¸îiÊÎXÚnX‹XùXÉnûÈÎiÈYîY¹îX‹ˆz®[{y¨NZHNZ(>8#Â÷ãÂöÆ“ãÂööÃà¢ÆF—b6Æ74æÖSÒ&ÖWF†öB×&VF–æW72#ãÇîZh.iéÎKÚ[{.{¸şXxnZH~Z[ŞK¨nûÈÎŠû~™zŞKˆ®yËÎyÙ¾ûÈÎ{É>{É>i[‹ø~KˆKŠ®YÎY8.XhŞyØ[ÈyËÎi{nûÈÎh‰KºÎK¸î[ø>KŠŞ˜*>K»nK¨¾[ÈZx¾8#Â÷ãÆ6Æ74æÖSÒ&ÖWF†öBÖ7F"‡&VcÒ"6–çV—'’#îh‰[{.XxnZH~Z[ÓÂöãÂöF—cà¢ÂöF—cà¢Â÷6V7F–öãà Ğ¢Ç6V7F–öâ–CÒ&–çV—'’"6Æ74æÖSÒ&–çV—'’67&öÆÂ×6V7F–öâ"FF×&WfVÃàĞ¢ÅfW'F–6Ä'&æBóàĞ¢Æf÷&Òöå7V&Ö—C×·7V&Ö—GÒæõfÆ–FFSàĞ¢Æ†VFW"6Æ74æÖSÒ&–çV—'’Ö†VF–ær#ãÇ6Æ74æÖSÒ&W–V'&÷r#îŠx.‹K˜¾k9R+rY¹¾jÚSÂ÷ãÆƒ#îK¸î[ø>KŠŞh˜™zîûÈÎ‹[X‹yËÎX˜ŞXúşŠÃÂöƒ#ãÇîjøşjÊXú®ZHNynKˆK»nX[~KÙ>y¨NK¨¾8.š^™Ú.KÉ®hÈjÚ>™zî8‹êŠøn8h‰XÚn8Šx.XÚny¨Nš®[¨ş™š®KÚZèÎh‰ûÈÎKˆŞ™ÈŠhKˆjÊZ¾ZèÎKˆ[Ê™zîXÛ~8#Â÷ãÂö†VFW#à Ğ¢Ç6V7F–öâ6Æ74æÖSÒ&–çV—'’×7FW–çV—'’×æVÂ#ãÆF—b6Æ74æÖSÒ'7FWÖ†VF–ær#ãÇ7ãîZ;“Â÷7ããÆF—cãÆƒ3îjÚ>™zãÂöƒ3ãÇîXiKˆ¾KˆK»nX[~KÙ>ˆÎyÉşZéîy¨NK¨¾8.XXhÈjÚNX‹¾iÈˆz®xKny¨Nik[ÈşXiûÈÎYî™Ú.‹ùiÈiË®KÉ®˜xŞikzîŠêN8#Â÷ãÂöF—cãÂöF—cà¢ÆÆ&VÂ6Æ74æÖSÒ'VW7F–öâÖÆ&VÂ#ãÇ7ãîKÚyÉşjÚ>h;>™zîy¨N™zîš)‚£Â÷7ããÇFW‡F&V&–ÖÆ&VÃÒ.KÚyÉşjÚ>h;>™zîy¨N™zîš)‚"Æ6V†öÆFW#Ò.Kè¾Zh.ûÉ®‹ùjÊYKÙÎûÈÎh‰‹ù[©NŠú^{º~{ºŞh©^XZ^Y	~ûÉò"fÇVS×·VW7F–öçÒÖ„ÆVæwFƒ×³cÒöä6†ævS×²†WfVçB’Óâ6WEVW7F–öâ†WfVçBçF&vWBçfÇVR—ÒóãÇ6ÖÆÃç·VW7F–öâçG&–Ò‚’æÆVæwF‡Òòc+rŠû~yJkˆ^i›X[~KÙ>y¨Nih~ZÙ~ŠûNX{®KÚh;>[ÈNiˆîy›Şy¨NK¨¾ûÈÎ‹ùKÉ®[ŠîXªh‰KºÎh¨®h«Ş‹y¨NXÚnhHş‰ŞX‹xëZéîZHNZ(>KŠŞ8#Â÷6ÖÆÃãÂöÆ&VÃà¢ÆF—b6Æ74æÖSÒ'VW7F–öâÖW†×ÆW2#ãÆ†VFW#ãÇ7ãîKˆŞyú^hîj~[ÈXú>ûÈÎXúşKº^K¸î‹ùK©¾™zîš)[ÈZx³Â÷7ããÇ6ÖÆÃîx+X{¾K»¾hHşKˆXú^ûÈÎKÉ®ˆz®XªZ¾XZ^Kˆ®ik“Â÷6ÖÆÃãÂö†VFW#ãÆF—cçµTU5D”ôåôU„ÕÄU2æÖ‚†W†×ÆR’ÓâÆ'WGFöâG—SÒ&'WGFöâ"¶W“×¶W†×ÆRçFW‡GÒöä6Æ–6³×²‚’ÓâÇ•VW7F–öäW†×ÆR†W†×ÆR—ÓãÇ7ãç¶W†×ÆRçF÷–7ÓÂ÷7ããÆ#ç¶W†×ÆRçFW‡GÓÂö#ãÂö'WGFöãâ—ÓÂöF—cãÂöF—cà¢Â÷6V7F–öãà ¢Ç6V7F–öâ6Æ74æÖSÒ&–çV—'’×7FW–çV—'’×æVÂ#ãÆF—b6Æ74æÖSÒ'7FWÖ†VF–ær#ãÇ7ãî‹KÂ÷7ããÆF—cãÆƒ3î‹êŠøcÂöƒ3ãÇîKˆjÊXú®Y¹îzÙNKˆ™zî8.h‰KºÎh¨®K¨¾ZéîKˆîiÊ®yú^Xˆn[ÈûÈÎK™ş[ŠîXªKÚ‹êŠêNiÈX‰ŞXiKˆ¾y¨N™zîš)iŠşY
nyÉşy¨N™zîX‹K¨n[ø>˜xÎ8#Â÷ãÂöF—cãÂöF—cà¢·VW7F–öâçG&–Ò‚’æÆVæwF‚ãÒbòÄwV–FVD–çF¶RVW7F–öã×·VW7F–öçÒöäf7G3×·6WDf7G7ÒöåVæ¶æ÷vç3×·6WEVæ¶æ÷vç7Òöä7F–öç3×·6WD7F–öç7Òöäö'6W'f&ÆU&W7öç6W3×·6WDö'6W'f&ÆU&W7öç6W7ÒöåVW7F–öã×·6WEVW7F–öçÒöå7G'V7GW&VC×²‡²FöÖ–ã¢æW‡DFöÖ–âÂvöÃ¢æW‡DvöÂÂ†÷&—¦öã¢æW‡D†÷&—¦öâÂ7FvS¢æW‡E7FvRÂVæ6W'F–çG“¢æW‡EVæ6W'F–çG’Â&—6µ&öf–ÆS¢æW‡E&—6µ&öf–ÆRÒ’Óâ²6WDFöÖ–â†æW‡DFöÖ–â“²6WDvöÂ†æW‡DvöÂ“²6WD†÷&—¦öâ†æW‡D†÷&—¦öâ“²6WE7FvR†æW‡E7FvR“²6WEVæ6W'F–çG’†æW‡EVæ6W'F–çG’“²–b†æW‡E&—6µ&öf–ÆR’6WE&—6µ&öf–ÆR†æW‡E&—6µ&öf–ÆR“²×Òöä6ö×ÆWFS×·6WD–çF¶T6ö×ÆWFWÒóâ¢Ç6Æ74æÖSÒ&F–ÆöwVR×&W&WV—6—FR#îXXYÊKˆ®KˆjÚ^XiKˆ¾ˆ{>[	XZŞKŠ®ZÙ~y¨NX[~KÙ>™zîš)ûÈÎ‹êŠønZûŠùŞh˜ŞKÉ®[ÈZx¾8#Â÷çĞ¢Â÷6V7F–öãà ¢Ç6V7F–öâ6Æ74æÖSÒ&–çV—'’×7FW–çV—'’×æVÂçVÖ&W"×7FW#ãÆF—b6Æ74æÖSÒ'7FWÖ†VF–ær#ãÇ7ãîXøÂ÷7ããÆF—cãÆƒ3îh‰XÚcÂöƒ3ãÇî™zŞKˆ®yËÎyÙ¾ûÈÎ{É>{É>YÎYKˆjÊûÈÎYÊ[ø>KŠŞXhŞ˜xŞZHŞKˆ˜ŞzîŠêNYîy¨N™zîš)8.XxnZH~Z[Şi{nûÈÎXhŞXzŞ[Ù>Kˆ¾h˜hIşXùnKˆKŠ®i[8#Â÷ãÂöF—cãÂöF—cà¢ÆF—b6Æ74æÖSÒ&'&VF‚×&—GVÂ"&–ÖÆ&VÃÒ.KˆjÊYÎYhùzK¢#ãÇ7ãîKˆhò+riÛî[ÈiØ.[ûSÂ÷7ããÇ7ãîK¨Îhò+rY¹îX‹h˜™zãÂ÷7ããÇ7ãîKˆhò+r[ø>Zé®Xùni[Â÷7ããÂöF—cà¢Æf–VÆG6WB6Æ74æÖSÒ&çVÖ&W'2×6Æ—#ãÆÆVvVæB6Æ74æÖSÒ'7"ÖöæÇ’#îXùnKˆKŠ®i[Ni[ÂöÆVvVæCç¶çVÖ&W'2æÖ‚‡fÇVRÂ–æFW‚’ÓâÆÆ&VÂ¶W“×¶–æFW‡ÓãÇ7ãçµ².Z;’+rKˆ®XÚb"Â.‹K+rKˆ¾XÚb"Â.Xø+rXªx‹²%Õ¶–æFW…×ÓÂ÷7ããÆ–çWB&–ÖÆ&VÃ×¶zÊÂG¶–æFW‚²ŞKŠ®i[ZÙvÒÆ6V†öÆFW#Ò#(	C““’"G—SÒ&çVÖ&W""–çWDÖöFSÒ&çVÖW&–2"Ö–ãÒ#"ÖƒÒ#““’"fÇVS×·fÇVWÒöä6†ævS×²†WfVçB’Óâ6WDçVÖ&W'2†çVÖ&W'2æÖ‚†—FVÒÂ—FVÔ–æFW‚’Óâ—FVÔ–æFW‚ÓÓÒ–æFW‚òWfVçBçF&vWBçfÇVR¢—FVÒ’—ÒóãÂöÆ&VÃâ—ÓÂöf–VÆG6WCà¢Ç6Æ74æÖSÒ&çVÖ&W"Öæ÷FR#îzÊÎKˆi[Zé®Kˆ®XÚnûÈÎzÊÎK¨Îi[Zé®Kˆ¾XÚnûÈÎzÊÎKˆi[Zé®Xªx‹¾8.zˆ¾[¨ş™¨şYîKéŞŠxNX‰hé.Zé®iÊÎXÚn8K©.XÚnKˆîXùXÚn8#Â÷à¢Â÷6V7F–öãà ¢Ç6V7F–öâ6Æ74æÖSÒ&–çV—'’×7FW–çV—'’×æVÂ67B×7FW#ãÆF—b6Æ74æÖSÒ'7FWÖ†VF–ær#ãÇ7ãîˆ(cÂ÷7ããÆF—cãÆƒ3îŠx.XÚcÂöƒ3ãÇîzîŠêN‹ëyXÎYîûÈÎzˆ¾[¨şXXxºÎz¸¾ZèÎh‰zîZé®h
~hé.y¹ûÈÎXhŞ{¹>YKÚYÊ‹êŠønKŠŞhùKé¾y¨NxëZéîKúhşyIşh‰Šz>˜x®8#Â÷ãÂöF—cãÂöF—cà¢ÆÆ&VÂ6Æ74æÖSÒ&6²#ãÆ–çWBG—SÒ&6†V6¶&÷‚"6†V6¶VC×¶6¶æ÷vÆVFvVGÒöä6†ævS×²†WfVçB’Óâ6WD6¶æ÷vÆVFvVB†WfVçBçF&vWBæ6†V6¶VB—ÒóãÇ7ãîh‰ynŠz>ûÉ®XÚn‹hùKé¾KˆzxŞŠx.ZùşŠy.[ªnûÈÎKŠ®h
~XÉnih~ZÙ~Xú®KÛşyJh‰XiKˆ¾y¨NK¨¾Zéî8iÊ®yú^šY(Îzˆ¾[¨şhé.X{®y¨NXÚn‹ûÉ¾Zè>KˆŞi»şKº>XË¾yi~8k9^[è¾8‹J.XªzØK‰>K‰®hHşŠx8.yIşh‰ZK‹J^KˆŞKÉ®ˆz®Xª˜xŞikyIşh‰ûÉ¾Xú®iÈh‰K‹¾XªKùŞZÙi{nûÈÎ{¹>iéÎh˜ŞKÉ®‹ù¾XZ^Šx.K¨¾{ş8#Â÷7ããÂöÆ&VÃà¢·&öw&W72bbÇ6Æ74æÖSÒ&vVæW&F–öâ×&öw&W72"&öÆSÒ'7FGW2#ç·&öw&W77ÓÂ÷çĞ¢¶W'&÷"bbÇ6Æ74æÖSÒ&W'&÷""&öÆSÒ&ÆW'B#ç¶W'&÷'ÓÂ÷çĞ¢Æ'WGFöâ6Æ74æÖSÒ&67BÖ'WGFöâ"F—6&ÆVC×¶ÆöF–æwÓãÄ&wVÖ&²óç¶ÆöF–ærò.jÚ>YÊyIşh‰Šz>Šû²"¢.Šx.XÚb'ÓÂö'WGFöãà¢¶ÆöF–ærbbÄ67F–ætÆöFW"óçĞ¢Â÷6V7F–öãà¢Âöf÷&Óà¢Â÷6V7F–öãàĞ Ğ¢·&W7öç6RbbÅ&W7VÇEf–Wr&W7öç6S×·&W7öç6WÒöäVF—C×¶VF—EVW7F–öçÒöä6ÆV#×¶6ÆV%VW7F–öçÒöå6fS×·6fTö'6W'fF–öçÒ6f–æs×·6f–æu&V6÷&GÒ6fVC×·6fVE&V6÷&D–BÓÒçVÆÇÒóçĞĞ¢Æ6–FR6Æ74æÖSÒ'fW'6–öâÖæ÷FR#îXÚn‹KˆŞiŠşš(NXXXiZ[Şy¨NXŠNŠøŞûÈÎˆÎiŠşZû[Ù>Kˆ¾{¹>ièNy¨NKˆjÊxZ~Šx8.h˜‹	>(	Îz›~X‰XùûÈÎXùX‰˜	®(	ŞûÈÎ[ø>[û^KˆîŠÎXªKˆXùûÈÎYî{ºŞiÚK»nK™şKÉ®™¨şK˜¾iKXù8.[é~š®X«şK˜¾‹ûÈÎKˆŞXúşYºjÚNXÎjÚ^ûÉ¾Šx™‹¾X©¾K˜¾‹ûÈÎK™şKˆŞ[ø^ˆz®[È>8.Šx.‹y¨NhHşK˜ûÈÎiŠşŠêh‰KºÎyÈ¾ŠxxZ~iz~X˜ŞŠÎXúşˆ;Şh«^‹ëîK˜¾ZHNûÈÎK¸îˆÎXø®izXxnZH~8KúîjÚ>KˆîŠÎXª8#Âö6–FSà¢ÂöÖ–ãàĞ¢Æfö÷FW"6Æ74æÖSÒ'6—FRÖfö÷FW"#ãÆ#îŠx.‹Âö#ãÇ7ãîKÊ{¹şih~XÉn{¹>ièNXø.ˆ2+rKº^xëZéîš¨ÎŠøi»NikXŠNijÓÂ÷7ããÆæcãÆ‡&VcÒ"öwV–FR#îZh.KÙ^KÛşyJƒÂöãÆ‡&VcÒ"ö&÷WB#îikk9^Kˆî‹ëyXÃÂöãÆ‡&VcÒ"÷&—f7’#î™©zxŠûNiˆãÂöãÂöæcãÂöfö÷FW#àĞ¢Âóã°Ğ§ĞĞ 