"use client";

import { FormEvent, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type RefObject } from "react";
import {
  PersonalizedPollError,
  pollPersonalizedTask,
} from "./personalized-reading-poll";
import { InquiryCloudfallCanvas } from "./InquiryCloudfallCanvas";
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
type Page8SceneId = "BASE_HEXAGRAM" | "MUTUAL_HEXAGRAM" | "CHANGED_HEXAGRAM" | "MOVING_LINE" | "BODY_USE_STRENGTH";
type Page8LayerInterpretation = {
  scene_id: Page8SceneId;
  layer_summary: string;
  reality_connection: string;
  uncertainty_boundary: string;
  reality_refs: string[];
  evidence_refs: string[];
  interpretation_hypothesis: true;
};
type Page8DeterministicContent = {
  primary_name: string;
  symbol?: string | null;
  king_wen_number?: number | null;
  formation: string;
  reading_role: string;
  canonical_label?: string | null;
  canonical_text?: string | null;
  plain_note?: string | null;
  facts: { label: string; value: string }[];
  source_name: string;
  source_reference: string;
};
type Page8Scene = {
  scene_id: Page8SceneId;
  sequence: number;
  title: string;
  purpose: string;
  deterministic: Page8DeterministicContent;
  interpretation: Page8LayerInterpretation;
};
type Page8Reading = {
  template_version: "SITES_PAGE8_READING_V1";
  stage_title: "读卦";
  user_question: string;
  scenes: Page8Scene[];
  epistemic_boundary: string;
  page9_reserved: true;
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
  page8_reading?: Page8Reading | null;
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

const METHOD_CLASSIC_LINES = ["在天成象", "在地成形", "变化见矣"] as const;

// Presentation-only lookup copied from MEIHUA_HEXAGRAMS_V1; each string is bottom-up.
const KING_WEN_LINES_BOTTOM_UP = [
  "111111", "000000", "100010", "010001", "111010", "010111", "010000", "000010",
  "111011", "110111", "111000", "000111", "101111", "111101", "001000", "000100",
  "100110", "011001", "110000", "000011", "100101", "101001", "000001", "100000",
  "100111", "111001", "100001", "011110", "010010", "101101", "001110", "011100",
  "001111", "111100", "000101", "101000", "101011", "110101", "001010", "010100",
  "110001", "100011", "111110", "011111", "000110", "011000", "010110", "011010",
  "101110", "011101", "100100", "001001", "001011", "110100", "101100", "001101",
  "011011", "110110", "010011", "110010", "110011", "001100", "101010", "010101",
] as const;

const JOURNAL_KEY = "guanxiang-observation-key-v1";
const ACTIVE_REQUEST_KEY = "guanxiang-personalized-active-request-v1";
const JOURNAL_OPEN_KEY = "guanxiang-open-journal-record-v1";
const FIRST_DISCERNMENT_QUESTION = "先从现在说起：这件事目前进行到哪一步了？";

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

function ChrysanthemumMark() {
  return <svg viewBox="0 0 48 48" focusable="false" aria-hidden="true">
    <g className="chrysanthemum-petals">
      {Array.from({ length: 12 }, (_, index) => <ellipse key={index} cx="24" cy="10" rx="3.2" ry="8" transform={`rotate(${index * 30} 24 24)`} />)}
    </g>
    <circle cx="24" cy="24" r="6.2" />
    <circle cx="24" cy="24" r="2.4" />
  </svg>;
}

const PEONY_BREATHS = [
  { numeral: "一息", guidance: "输入第一个数", placeholder: "上卦", flower: "/casting-peony-bloom-1-v1.png" },
  { numeral: "二息", guidance: "输入第二个数", placeholder: "下卦", flower: "/casting-peony-bloom-2-v1.png" },
  { numeral: "三息", guidance: "输入第三个数", placeholder: "动爻", flower: "/casting-peony-bloom-3-v1.png" },
] as const;

const PEONY_PETAL_MOTIONS = [
  { left: 12, midX: -7, travelX: -34, travelY: 32, spin: -420, flipX: 540, flipY: -360, size: 10, duration: 8.8, delay: -1.1 },
  { left: 19, midX: -13, travelX: -44, travelY: 43, spin: 610, flipX: -720, flipY: 540, size: 16, duration: 19.6, delay: -8.7 },
  { left: 25, midX: -5, travelX: -38, travelY: 51, spin: -760, flipX: 900, flipY: 360, size: 27, duration: 14.8, delay: -4.4 },
  { left: 32, midX: -18, travelX: -52, travelY: 37, spin: 530, flipX: 450, flipY: -810, size: 13, duration: 10.4, delay: -11.8 },
  { left: 38, midX: -10, travelX: -47, travelY: 48, spin: -350, flipX: -630, flipY: 720, size: 72, duration: 22.4, delay: -6.3 },
  { left: 44, midX: -22, travelX: -61, travelY: 45, spin: 820, flipX: 1080, flipY: -540, size: 19, duration: 16.2, delay: -13.7 },
  { left: 50, midX: -8, travelX: -42, travelY: 35, spin: -580, flipX: 720, flipY: 450, size: 23, duration: 9.6, delay: -2.9 },
  { left: 56, midX: -15, travelX: -55, travelY: 53, spin: 460, flipX: -900, flipY: 810, size: 12, duration: 20.8, delay: -15.4 },
  { left: 62, midX: -4, travelX: -36, travelY: 41, spin: -910, flipX: 1260, flipY: -720, size: 30, duration: 13.1, delay: -9.6 },
  { left: 68, midX: -20, travelX: -64, travelY: 50, spin: 690, flipX: -540, flipY: 1080, size: 15, duration: 18.6, delay: -5.2 },
  { left: 74, midX: -11, travelX: -49, travelY: 39, spin: -480, flipX: 810, flipY: 630, size: 108, duration: 11.2, delay: -12.5 },
  { left: 81, midX: -24, travelX: -68, travelY: 47, spin: 940, flipX: -1080, flipY: -450, size: 20, duration: 21.5, delay: -7.4 },
  { left: 16, midX: -16, travelX: -57, travelY: 55, spin: 720, flipX: 630, flipY: -990, size: 25, duration: 17.8, delay: -16.2 },
  { left: 29, midX: -6, travelX: -41, travelY: 36, spin: -660, flipX: -810, flipY: 540, size: 11, duration: 8.5, delay: -3.7 },
  { left: 47, midX: -19, travelX: -59, travelY: 44, spin: 390, flipX: 990, flipY: -720, size: 84, duration: 15.4, delay: -10.9 },
  { left: 59, midX: -12, travelX: -46, travelY: 52, spin: -840, flipX: -1260, flipY: 810, size: 17, duration: 23.2, delay: -14.6 },
  { left: 72, midX: -26, travelX: -71, travelY: 42, spin: 570, flipX: 720, flipY: 1260, size: 28, duration: 12.5, delay: -1.9 },
  { left: 86, midX: -9, travelX: -43, travelY: 49, spin: -730, flipX: -900, flipY: -630, size: 14, duration: 19.9, delay: -8.1 },
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

const METHOD_RIVER_VERTEX_SHADER = `
  attribute vec2 a_position;
  varying vec2 v_uv;

  void main() {
    v_uv = a_position * 0.5 + 0.5;
    gl_Position = vec4(a_position, 0.0, 1.0);
  }
`;

const METHOD_RIVER_TUNING = Object.freeze({
  mainFlowSpeed: 0.31,
  fineFlowSpeed: 0.47,
  foamSpeed: 0.39,
  rollSpeed: 0.27,
  foamAmount: 0.72,
  rollStrength: 0.94,
  opacity: 0.98,
  turbulence: 0.66,
  surgeStrength: 0.9,
  waveWallStrength: 0.92,
  breakerStrength: 0.96,
});

const METHOD_RIVER_FRAGMENT_SHADER = `
  precision mediump float;

  varying vec2 v_uv;
  uniform sampler2D u_scene;
  uniform vec2 u_resolution;
  uniform vec2 u_texture_size;
  uniform float u_time;
  uniform vec4 u_flow_speeds;
  uniform vec4 u_river_style;
  uniform vec3 u_river_force;

  float hash(vec2 point) {
    point = fract(point * vec2(123.34, 456.21));
    point += dot(point, point + 45.32);
    return fract(point.x * point.y);
  }

  float noise(vec2 point) {
    vec2 cell = floor(point);
    vec2 local = fract(point);
    local = local * local * (3.0 - 2.0 * local);
    return mix(
      mix(hash(cell), hash(cell + vec2(1.0, 0.0)), local.x),
      mix(hash(cell + vec2(0.0, 1.0)), hash(cell + vec2(1.0, 1.0)), local.x),
      local.y
    );
  }

  float fbm(vec2 point) {
    float value = 0.0;
    float weight = 0.55;
    for (int octave = 0; octave < 4; octave++) {
      value += weight * noise(point);
      point = point * 2.03 + vec2(8.1, 3.7);
      weight *= 0.48;
    }
    return value;
  }

  float path_mix(float y, float y0, float y1, float a, float b) {
    return mix(a, b, smoothstep(y0, y1, y));
  }

  // Hand-traced centerline for this exact painting. Screen y runs from the
  // distant gorge (0.0) toward the foreground (1.0).
  float river_center(float y) {
    if (y < 0.24) return path_mix(y, 0.10, 0.24, 0.500, 0.512);
    if (y < 0.38) return path_mix(y, 0.24, 0.38, 0.512, 0.486);
    if (y < 0.52) return path_mix(y, 0.38, 0.52, 0.486, 0.516);
    if (y < 0.66) return path_mix(y, 0.52, 0.66, 0.516, 0.472);
    if (y < 0.82) return path_mix(y, 0.66, 0.82, 0.472, 0.520);
    return path_mix(y, 0.82, 1.00, 0.520, 0.500);
  }

  // Matching hand-traced half-widths keep every animated sample inside the
  // painted water and away from the mountain silhouettes.
  float river_width(float y) {
    if (y < 0.24) return path_mix(y, 0.10, 0.24, 0.030, 0.052);
    if (y < 0.38) return path_mix(y, 0.24, 0.38, 0.052, 0.086);
    if (y < 0.52) return path_mix(y, 0.38, 0.52, 0.086, 0.145);
    if (y < 0.66) return path_mix(y, 0.52, 0.66, 0.145, 0.220);
    if (y < 0.82) return path_mix(y, 0.66, 0.82, 0.220, 0.315);
    return path_mix(y, 0.82, 1.00, 0.315, 0.405);
  }

  vec2 cover_uv(vec2 screen_uv) {
    float viewport_aspect = u_resolution.x / max(u_resolution.y, 1.0);
    float texture_aspect = u_texture_size.x / max(u_texture_size.y, 1.0);
    vec2 result = screen_uv;
    if (viewport_aspect > texture_aspect) {
      float visible_height = texture_aspect / viewport_aspect;
      result.y = 0.5 + (screen_uv.y - 0.5) * visible_height;
    } else {
      float visible_width = viewport_aspect / texture_aspect;
      result.x = 0.5 + (screen_uv.x - 0.5) * visible_width;
    }
    return result;
  }

  void main() {
    vec2 screen = vec2(v_uv.x, 1.0 - v_uv.y);
    float center = river_center(screen.y);
    float width = river_width(screen.y);
    float lane = (screen.x - center) / max(width, 0.001);

    // The soft edge is still well inside the hand-traced banks. This is the
    // only region in which any animated layer is allowed to contribute.
    float bank_fade = 1.0 - smoothstep(0.58, 0.80, abs(lane));
    float source_fade = smoothstep(0.10, 0.22, screen.y);
    float river = bank_fade * source_fade;

    float depth = smoothstep(0.12, 1.0, screen.y);
    vec2 scene_uv = cover_uv(v_uv);
    vec3 base_color = texture2D(u_scene, scene_uv).rgb;
    vec2 texel = 1.0 / max(u_texture_size, vec2(1.0));
    float water_luma_base = dot(base_color, vec3(0.299, 0.587, 0.114));
    float luma_left = dot(texture2D(u_scene, scene_uv - vec2(texel.x * 2.0, 0.0)).rgb, vec3(0.299, 0.587, 0.114));
    float luma_right = dot(texture2D(u_scene, scene_uv + vec2(texel.x * 2.0, 0.0)).rgb, vec3(0.299, 0.587, 0.114));
    float luma_up = dot(texture2D(u_scene, scene_uv - vec2(0.0, texel.y * 2.0)).rgb, vec3(0.299, 0.587, 0.114));
    float luma_down = dot(texture2D(u_scene, scene_uv + vec2(0.0, texel.y * 2.0)).rgb, vec3(0.299, 0.587, 0.114));
    float gradient_x = abs(luma_right - luma_left);
    float gradient_y = abs(luma_down - luma_up);
    float horizontal_water_detail = smoothstep(-0.016, 0.034, gradient_y - gradient_x * 0.56);
    float vertical_terrain_ink = smoothstep(0.020, 0.068, gradient_x - gradient_y * 0.28);
    float pale_water_wash = smoothstep(0.48, 0.78, water_luma_base);
    float water_motion_guard = clamp(
      (horizontal_water_detail * 0.72 + pale_water_wash * 0.42)
      * (1.0 - vertical_terrain_ink),
      0.0,
      1.0
    );
    // The traced path is the final safety boundary. Keep a substantial motion
    // floor inside it so the pale middle of the painted river does not make the
    // current disappear, while the bank fade still leaves every mountain still.
    float river_motion = river;

    float main_speed = u_flow_speeds.x;
    float fine_speed = u_flow_speeds.y;
    float foam_speed = u_flow_speeds.z;
    float roll_speed = u_flow_speeds.w;
    float foam_amount = u_river_style.x;
    float roll_strength = u_river_style.y;
    float layer_opacity = u_river_style.z;
    float turbulence = u_river_style.w;
    float surge_strength = u_river_force.x;
    float wave_wall_strength = u_river_force.y;
    float breaker_strength = u_river_force.z;

    // Follow the painted bend instead of translating a rectangular texture.
    float next_center = river_center(min(screen.y + 0.012, 1.0));
    float previous_center = river_center(max(screen.y - 0.012, 0.0));
    float bend = (next_center - previous_center) * 16.0;
    float longitudinal = screen.y
      + lane * bend * 0.045
      + sin(screen.y * 12.0 + lane * 2.4) * 0.006 * turbulence;
    float depth_speed = mix(0.34, 1.76, pow(depth, 1.18));

    // Layer 1: a few broad current corridors. These long ink masses carry the
    // whole river downstream; they are intentionally much larger than surface
    // texture so the motion reads as water volume instead of crawling noise.
    float main_time = u_time * main_speed * depth_speed;
    float main_warp = fbm(vec2(lane * 1.65, longitudinal * 1.45 - main_time * 0.74)) - 0.5;
    float main_field_a = fbm(vec2(
      lane * 2.15 + main_warp * 1.8,
      (longitudinal - main_time) * 1.62 + lane * 0.34
    ));
    float main_field_b = fbm(vec2(
      lane * 2.7 - main_warp * 1.45 + 9.3,
      (longitudinal - main_time * 0.72) * 2.18 - lane * 0.26
    ));
    float main_ribbon = pow(1.0 - abs(main_field_a * 2.0 - 1.0), 1.55);
    float main_shadow = smoothstep(0.50, 0.82, 1.0 - main_field_b);

    // Broad white-water masses travel down the gorge on oblique coordinates.
    // There is deliberately no periodic front here: nested fields make each
    // surge fork, collide and rejoin instead of forming horizontal rows.
    float wall_warp = fbm(vec2(
      lane * 1.42 + 17.0,
      longitudinal * 1.78 - main_time * 0.48
    )) - 0.5;
    float wall_cluster = smoothstep(0.32, 0.68, fbm(vec2(
      lane * 2.25 - 5.0,
      longitudinal * 2.32 - main_time * 0.64
    )));
    float wall_fracture = fbm(vec2(
      lane * 4.1 + longitudinal * 2.6 + wall_warp * 2.8,
      (longitudinal - main_time * 1.12) * 3.25 - lane * 1.35
    ));
    float wall_field = fbm(vec2(
      lane * 2.8 + longitudinal * 2.25 + wall_warp * 2.15,
      (longitudinal - main_time * 1.18) * 2.42 - lane * 1.42 + wall_fracture * 1.65
    ));
    float wall_ridge = 1.0 - abs(wall_field * 2.0 - 1.0);
    float wave_wall = smoothstep(0.54, 0.88, wall_ridge)
      * smoothstep(0.38, 0.72, wall_cluster * 0.68 + wall_fracture * 0.46);
    float undertow_field = fbm(vec2(
      lane * 2.35 - longitudinal * 1.55 + 8.0,
      (longitudinal - main_time * 0.92) * 2.05 + lane * 1.18
    ));
    float wall_undertow = smoothstep(0.57, 0.82, undertow_field) * wall_cluster;

    // Layer 2: finer secondary current. It stays subordinate to the broad
    // surge and travels faster, making the river feel deep rather than busy.
    float fine_time = u_time * fine_speed * depth_speed;
    float fine_warp = fbm(vec2(lane * 7.4 + 12.0, longitudinal * 4.0 - fine_time * 1.7));
    float fine_field = noise(vec2(
      lane * 13.8 + fine_warp * 3.1 + sin(longitudinal * 13.0) * 0.46,
      (longitudinal - fine_time) * 7.8 + lane * 0.72
    ));
    float fine_ribbon = pow(1.0 - abs(fine_field * 2.0 - 1.0), 3.8);
    fine_ribbon *= smoothstep(0.34, 0.81, fbm(vec2(lane * 8.2, longitudinal * 4.4 - fine_time * 2.1)));

    // Layer 3: broken white foam clusters. Density changes the threshold, not
    // the shape, so the foam stays irregular and never becomes oval particles.
    float foam_time = u_time * foam_speed * depth_speed;
    float foam_warp = fbm(vec2(lane * 2.8 - 7.0, longitudinal * 5.2 - foam_time * 1.6));
    float foam_field = fbm(vec2(
      lane * 8.4 + foam_warp * 3.0,
      (longitudinal - foam_time) * 7.2 + lane * 0.58
    ));
    float foam_ridge = 1.0 - abs(foam_field * 2.0 - 1.0);
    float foam_breakup = fbm(vec2(
      lane * 12.4 + sin(longitudinal * 16.0) * 0.78,
      (longitudinal - foam_time * 1.12) * 10.0
    ));
    float foam_threshold = mix(0.87, 0.62, foam_amount);
    float travelling_foam = smoothstep(foam_threshold, 0.96, foam_ridge)
      * smoothstep(0.47, 0.79, foam_breakup);

    // Foam trains are shed from the large surge itself. Their oblique ridges
    // stretch, split and dissolve without ever becoming circles or stripes.
    float foam_train_breakup = smoothstep(0.37, 0.72, fbm(vec2(
      lane * 6.8 + longitudinal * 3.1 + wall_warp * 3.6,
      (longitudinal - foam_time * 1.34) * 4.6 - lane * 1.85
    )));
    float foam_train_ridge = 1.0 - abs(fbm(vec2(
      lane * 5.6 - longitudinal * 2.8 + 2.0,
      (longitudinal - foam_time * 1.22) * 4.1 + lane * 1.65
    )) * 2.0 - 1.0);
    float foam_train = smoothstep(0.56, 0.88, foam_train_ridge)
      * foam_train_breakup
      * mix(0.34, 1.0, wave_wall);

    // Layer 4: localized rolling crests with a darker underside. Their phase
    // follows the path and their cluster envelope appears, breaks and reforms.
    float roll_time = u_time * roll_speed * depth_speed;
    float roll_noise = fbm(vec2(lane * 2.65 + 4.0, longitudinal * 5.0 - roll_time * 1.4));
    float roll_clusters = smoothstep(0.44, 0.74, fbm(vec2(
      lane * 3.1 - 11.0,
      longitudinal * 6.4 - roll_time * 2.1
    )));
    float roll_field = fbm(vec2(
      lane * 3.75 + longitudinal * 3.25 + roll_noise * 2.5,
      (longitudinal - roll_time * 1.16) * 3.05 - lane * 2.15
    ));
    float roll_ridge = 1.0 - abs(roll_field * 2.0 - 1.0);
    float rolling_crest = smoothstep(0.55, 0.88, roll_ridge) * roll_clusters;
    float rolling_shadow = smoothstep(0.58, 0.84, fbm(vec2(
      lane * 3.15 - longitudinal * 2.1 + 19.0,
      (longitudinal - roll_time * 0.84) * 2.75 + lane * 1.7
    ))) * roll_clusters;

    // Near-field breakers rise out of the broad fronts instead of appearing as
    // separate oval particles. The crest grows, overturns, fragments, then its
    // shadow closes behind it as the wave falls back into the river.
    float near_field = smoothstep(0.46, 0.98, depth);
    float breaker_noise = fbm(vec2(
      lane * 4.8 + roll_noise * 2.1,
      longitudinal * 4.6 - roll_time * 2.0
    ));
    float breaker_cluster = smoothstep(0.42, 0.73, breaker_noise);
    float breaker_lift = wave_wall * breaker_cluster * near_field;
    float breaker_fragment = breaker_lift * smoothstep(0.46, 0.82, foam_breakup);
    float breaker_shadow = wall_undertow * breaker_cluster * near_field;

    float source_foam = smoothstep(0.57, 0.80, water_luma_base);
    float motion_mask = river_motion * mix(0.52, 1.0, depth);
    vec3 warm_foam = vec3(0.978, 0.952, 0.890);
    vec3 water_color = base_color;

    float dark_energy = (
      main_shadow * 0.25 * surge_strength
      + wall_undertow * 0.22 * wave_wall_strength
      + rolling_shadow * 0.13 * roll_strength
      + breaker_shadow * 0.18 * breaker_strength
    )
      * motion_mask * layer_opacity;
    water_color *= 1.0 - dark_energy;

    float main_light = main_ribbon * 0.31 * surge_strength;
    float wall_light = wave_wall * 0.48 * wave_wall_strength;
    float fine_light = fine_ribbon * 0.045;
    float foam_light = travelling_foam * mix(0.20, 0.52, source_foam);
    float foam_train_light = foam_train * 0.48 * mix(0.64, 1.0, source_foam);
    float roll_light = rolling_crest * 0.50 * roll_strength * mix(0.52, 1.0, source_foam);
    float breaker_light = (breaker_lift * 0.58 + breaker_fragment * 0.38)
      * breaker_strength
      * mix(0.70, 1.0, source_foam);
    float light_energy = clamp(
      (main_light + wall_light + fine_light + foam_light + foam_train_light + roll_light + breaker_light)
      * motion_mask
      * layer_opacity,
      0.0,
      0.82
    );
    water_color = mix(water_color, warm_foam, light_energy);

    gl_FragColor = vec4(water_color, 1.0);
  }
`;

function compileMethodRiverShader(gl: WebGLRenderingContext, type: number, source: string): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  gl.deleteShader(shader);
  return null;
}

function MethodRiverFlow() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!canvas || motionQuery.matches) return;

    const gl = canvas.getContext("webgl", { alpha: false, antialias: false, powerPreference: "low-power" });
    if (!gl) return;

    const vertexShader = compileMethodRiverShader(gl, gl.VERTEX_SHADER, METHOD_RIVER_VERTEX_SHADER);
    const fragmentShader = compileMethodRiverShader(gl, gl.FRAGMENT_SHADER, METHOD_RIVER_FRAGMENT_SHADER);
    if (!vertexShader || !fragmentShader) return;

    const program = gl.createProgram();
    if (!program) return;
    gl.attachShader(program, vertexShader);
    gl.attachShader(program, fragmentShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return;

    const positionLocation = gl.getAttribLocation(program, "a_position");
    const resolutionLocation = gl.getUniformLocation(program, "u_resolution");
    const textureSizeLocation = gl.getUniformLocation(program, "u_texture_size");
    const timeLocation = gl.getUniformLocation(program, "u_time");
    const flowSpeedsLocation = gl.getUniformLocation(program, "u_flow_speeds");
    const riverStyleLocation = gl.getUniformLocation(program, "u_river_style");
    const riverForceLocation = gl.getUniformLocation(program, "u_river_force");
    const sceneLocation = gl.getUniformLocation(program, "u_scene");
    const buffer = gl.createBuffer();
    const texture = gl.createTexture();
    if (!buffer || !texture || positionLocation < 0) return;

    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    gl.useProgram(program);
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, 1);
    gl.uniform1i(sceneLocation, 0);
    gl.uniform4f(
      flowSpeedsLocation,
      METHOD_RIVER_TUNING.mainFlowSpeed,
      METHOD_RIVER_TUNING.fineFlowSpeed,
      METHOD_RIVER_TUNING.foamSpeed,
      METHOD_RIVER_TUNING.rollSpeed,
    );
    gl.uniform4f(
      riverStyleLocation,
      METHOD_RIVER_TUNING.foamAmount,
      METHOD_RIVER_TUNING.rollStrength,
      METHOD_RIVER_TUNING.opacity,
      METHOD_RIVER_TUNING.turbulence,
    );
    gl.uniform3f(
      riverForceLocation,
      METHOD_RIVER_TUNING.surgeStrength,
      METHOD_RIVER_TUNING.waveWallStrength,
      METHOD_RIVER_TUNING.breakerStrength,
    );

    let animationFrame = 0;
    let textureReady = false;
    let visible = false;
    let accumulatedTime = 0;
    let lastFrameAt = performance.now();
    const mobileQuery = window.matchMedia("(max-width: 900px)");

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);
      const width = Math.max(1, Math.round(bounds.width * pixelRatio));
      const height = Math.max(1, Math.round(bounds.height * pixelRatio));
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
        gl.viewport(0, 0, width, height);
      }
    };

    const draw = (now: number) => {
      if (!textureReady || !visible || document.hidden) {
        animationFrame = window.requestAnimationFrame(draw);
        lastFrameAt = now;
        return;
      }
      const elapsed = Math.min((now - lastFrameAt) / 1000, 0.05);
      accumulatedTime += elapsed;
      lastFrameAt = now;
      resize();
      gl.useProgram(program);
      gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
      gl.uniform1f(timeLocation, accumulatedTime);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      animationFrame = window.requestAnimationFrame(draw);
    };

    let activeImage: HTMLImageElement | null = null;
    const loadScene = () => {
      const image = new Image();
      activeImage = image;
      textureReady = false;
      canvas.classList.remove("is-ready");
      image.onload = () => {
        if (activeImage !== image) return;
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.uniform2f(textureSizeLocation, image.naturalWidth, image.naturalHeight);
        textureReady = true;
        resize();
        gl.uniform2f(resolutionLocation, canvas.width, canvas.height);
        gl.uniform1f(timeLocation, accumulatedTime);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        canvas.classList.add("is-ready");
      };
      image.src = mobileQuery.matches ? "/method-river-mobile-v2.webp" : "/method-river-wide-v2.webp";
    };

    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }, { rootMargin: "12%" });
    const resizeObserver = new ResizeObserver(resize);
    observer.observe(canvas);
    resizeObserver.observe(canvas);
    mobileQuery.addEventListener("change", loadScene);
    loadScene();
    animationFrame = window.requestAnimationFrame((now) => {
      lastFrameAt = now;
      draw(now);
    });

    return () => {
      window.cancelAnimationFrame(animationFrame);
      observer.disconnect();
      resizeObserver.disconnect();
      mobileQuery.removeEventListener("change", loadScene);
      activeImage = null;
      gl.deleteTexture(texture);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
      gl.deleteShader(vertexShader);
      gl.deleteShader(fragmentShader);
    };
  }, []);

  return <canvas ref={canvasRef} className="method-river-flow" aria-hidden="true" />;
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
    {!completed && turn > 1 && <div className="dialogue-compose"><textarea aria-label="回答当前问题" value={draft} maxLength={turn === 6 ? 300 : 1200} onChange={(event) => setDraft(event.target.value)} placeholder="点击这里，回答上面这一问……" /><button type="button" disabled={!draft.trim()} onClick={() => record(draft)}><span>这一问回答好了<br />继续下一问</span></button></div>}
    {!completed && <div className="discernment-controls"><button type="button" onClick={() => record("暂不回答")}>这一问暂时不知道</button><button type="button" onClick={finishEarly}>我已经说清，可以结束辨识</button></div>}
    {completed && <div className="dialogue-review discernment-complete"><p className="eyebrow">清空杂念，拨开迷雾</p><h3>你的思路已经慢慢清晰</h3><p>接下来，我们一起定下真正要问的事。</p><div className="dialogue-review-actions"><button type="button" onClick={finish}>进入第三步：定问</button><button type="button" className="text-button" onClick={reset}>重新辨识</button></div></div>}
  </div>;
}

function GuidedIntake(props: GuidedIntakeProps) {
  const { question, onFacts, onUnknowns, onActions, onObservableResponses, onSuggestion, onStructured, onCompletionReason, onComplete, onContinue } = props;
  const [mode, setMode] = useState<"ASKING" | "REVIEW" | "FALLBACK" | "STOPPED">("ASKING");
  const [sessionId] = useState(() => `intake-${crypto.randomUUID()}`);
  const [turns, setTurns] = useState<IntakeAnswer[]>([]);
  const [currentPrompt, setCurrentPrompt] = useState(FIRST_DISCERNMENT_QUESTION);
  const [assistantMessage, setAssistantMessage] = useState("不必在意说得是否清楚\n杂念会自然在倾诉中渐渐清空");
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
    const combined = `${question}\n${turns.map((item) => item.answer).join("\n")}`;
    const domain = inferDomain(combined);
    const desiredGoal = inferGoal(turns[turns.length - 1]?.answer ?? question);
    const allowed = GOALS_BY_DOMAIN[domain] ?? [];
    onStructured({
      domain,
      goal: allowed.includes(desiredGoal) ? desiredGoal : allowed[0] ?? "PLAN_NEXT_STEP",
      horizon: "CURRENT",
      stage: "EXPLORING",
      uncertainty: inferUncertainty(combined),
    });
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
      <div className="discernment-chrysanthemum-progress" role="img" aria-label={`还剩 ${Math.max(0, 8 - turns.length)} 朵菊花`}>
        {Array.from({ length: Math.max(0, 8 - turns.length) }, (_, index) => <span key={`chrysanthemum-${index}`} aria-hidden="true"><ChrysanthemumMark /></span>)}
      </div>
      {!busy && !error && <p className="discernment-understanding">{assistantMessage.split("\n").map((line, index) => <span key={`${line}-${index}`}>{index > 0 && <br />}{line}</span>)}</p>}
      {currentPrompt && !busy && !error && <div className="discernment-current" key={currentPrompt}><img src="/fuxi-bagua-taiji.svg" alt="" /><p>{currentPrompt}</p></div>}
      {busy && <div className="discernment-working" role="status"><span>不怕念起，只怕觉迟<br />这一问已记下，下一问正在浮现</span><span className="discernment-mist-scroll" aria-hidden="true"><img src="/discernment-mist-scroll-v1.png" alt="" /></span></div>}
      {error && <div className="discernment-recovery" role="alert"><span>前 {turns.length} 个回答都还在</span><p>{error.replace(/[。！？]+$/, "")}。不需要从头再答，只要从这里继续。</p><div><button type="button" disabled={busy} onClick={retryTurn}>继续这一轮</button><button type="button" className="text-button" onClick={() => setMode("FALLBACK")}>改用基础引导</button></div></div>}
    </div>}
    {mode === "ASKING" && !error && <div className="dialogue-compose"><textarea aria-label="回答当前问题" value={draft} maxLength={1200} disabled={busy || !currentPrompt} onChange={(event) => setDraft(event.target.value)} placeholder="点击这里，回答上面这一问……" /><button type="button" disabled={busy || !draft.trim() || !currentPrompt} onClick={answer}>{busy ? "这一问已记下" : <span>这一问回答好了<br />继续下一问</span>}</button></div>}
    {mode === "ASKING" && !error && <div className="discernment-controls"><button type="button" disabled={busy || !currentPrompt} onClick={() => answerWithValue("暂不回答")}>这一问暂时不知道</button><button type="button" disabled={busy} onClick={() => setMode("STOPPED")}>我已经说清，可以结束辨识</button></div>}
    {mode === "REVIEW" && review && <div className="dialogue-review discernment-complete"><p className="eyebrow">清空杂念，拨开迷雾</p><h3>你的思路已经慢慢清晰</h3><p>接下来，我们一起定下真正要问的事。</p><div className="dialogue-review-actions"><button type="button" onClick={completeDiscernment}>进入第三步：定问</button></div></div>}
    {mode === "STOPPED" && <div className="dialogue-review discernment-complete discernment-classic"><p className="eyebrow">《周易·系辞下》</p><blockquote>穷则变，变则通，通则久。</blockquote><div className="dialogue-review-actions"><button type="button" onClick={finishWithoutSuggestion}>进入第三步：定问</button></div></div>}
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
  return <section id="final-question" className="inquiry-step inquiry-panel final-question-step viewport-page flow-lock-screen" hidden={hidden} aria-labelledby="final-question-title">
    <div className="final-question-backdrop" aria-hidden="true">
      <span className="final-question-sky-drift" />
      <span className="final-question-bird" />
    </div>
    <VerticalBrand />
    <div className="final-question-heading flow-title-heading">
      <p className="eyebrow">观象之法 · 叁</p>
      <h3 id="final-question-title" tabIndex={-1}>定问</h3>
      <p>第三步：定问<br />收回纷乱的念头<br />确认你真正想问的事</p>
    </div>

    <div className="final-question-workspace">
      {suggestionChangesQuestion && !decisionMade && <div className="question-change-proposal">
        <p>根据刚才的回答<br />你真正想确认的，也许更接近这一问：</p>
        <blockquote>{suggestedQuestion}</blockquote>
        <p>如果这句话更贴近你的心意，请采用这一问。<br />如果没有，请保留你最初的问题。</p>
        <div><button type="button" onClick={onChooseSuggestion}>采用建议</button><button type="button" className="text-button" onClick={onChooseOriginal}>保留原问</button></div>
      </div>}

      {ready && <div className="final-question-ready" role="status" aria-live="polite">
        <p>{earlyExit ? "我感受到你想尽快进入取数卜卦的环节。" : <span>最终问题已经定下<br />接下来，请把注意力重新放回这一问</span>}</p>
        <strong className="final-question-breathing"><span>请在心中再默念一遍最终问题</span><span>缓缓深呼吸</span></strong>
      </div>}

      {ready && <div className="final-question-readiness">
        <button type="button" className="method-cta final-question-cta" aria-pressed={confirmed} onClick={onConfirm}><BaguaMark className="final-question-bagua" /><span className="method-cta-label">{confirmed ? "已经开始" : <span>我已定问<br />进入第四步：成卦</span>}</span></button>
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

type KoiMotion = {
  x: number;
  y: number;
  heading: number;
  speed: number;
  baseSpeed: number;
  turnRate: number;
  targetX: number;
  targetY: number;
  retargetAt: number;
  phase: number;
  phaseRate: number;
  scale: number;
  alpha: number;
};

function ResultKoiPond() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    let frame = 0;
    let lastTime = performance.now();
    let visible = true;
    let width = 1;
    let height = 1;
    let redraw: (() => void) | null = null;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    const loadImage = (src: string) => new Promise<HTMLImageElement>((resolve, reject) => {
      const image = new Image();
      image.decoding = "async";
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });

    const randomTarget = (motion: KoiMotion, now: number) => {
      const marginX = Math.max(70, width * .08);
      const marginY = Math.max(60, height * .1);
      motion.targetX = marginX + Math.random() * Math.max(1, width - marginX * 2);
      motion.targetY = marginY + Math.random() * Math.max(1, height - marginY * 2);
      motion.retargetAt = now + 5200 + Math.random() * 6200;
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(1, bounds.width);
      height = Math.max(1, bounds.height);
      const deviceScale = Math.min(window.devicePixelRatio || 1, 1.75);
      canvas.width = Math.round(width * deviceScale);
      canvas.height = Math.round(height * deviceScale);
      context.setTransform(deviceScale, 0, 0, deviceScale, 0, 0);
      redraw?.();
    };

    const normalizeAngle = (angle: number) => {
      let value = angle;
      while (value > Math.PI) value -= Math.PI * 2;
      while (value < -Math.PI) value += Math.PI * 2;
      return value;
    };

    const drawKoi = (image: HTMLImageElement, motion: KoiMotion) => {
      const compact = width < 760;
      const drawWidth = (compact ? Math.min(138, width * .37) : Math.min(258, width * .15)) * motion.scale;
      const drawHeight = drawWidth * image.height / image.width;
      const slices = compact ? 36 : 52;
      const destinationSlice = drawWidth / slices;
      const tailAmplitude = drawWidth * (compact ? .052 : .045);
      const breath = 1 + Math.sin(motion.phase * .45) * .012;

      context.save();
      context.translate(motion.x, motion.y);
      context.rotate(motion.heading + Math.sin(motion.phase * .34) * .018);
      context.scale(breath, 1 / breath);
      context.globalAlpha = motion.alpha;

      for (let index = 0; index < slices; index += 1) {
        const progress = (index + .5) / slices;
        const tailWeight = .14 + Math.pow(1 - progress, 1.75) * .86;
        const wave = Math.sin(motion.phase - progress * 5.2);
        const localY = wave * tailAmplitude * tailWeight;
        const nextProgress = Math.min(1, progress + 1 / slices);
        const nextTailWeight = .14 + Math.pow(1 - nextProgress, 1.75) * .86;
        const nextY = Math.sin(motion.phase - nextProgress * 5.2) * tailAmplitude * nextTailWeight;
        const localAngle = Math.atan2(nextY - localY, destinationSlice) * .72;
        const localX = -drawWidth / 2 + (index + .5) * drawWidth / slices;
        const clipX = -drawWidth / 2 + index * destinationSlice;

        context.save();
        context.beginPath();
        context.rect(clipX - .08, -drawHeight * 1.35, destinationSlice + .16, drawHeight * 2.7);
        context.clip();
        context.translate(localX, localY);
        context.rotate(localAngle);
        context.translate(-localX, 0);
        context.drawImage(image, -drawWidth / 2, -drawHeight / 2, drawWidth, drawHeight);
        context.restore();
      }
      context.restore();
    };

    const updateMotion = (motion: KoiMotion, now: number, delta: number) => {
      const distance = Math.hypot(motion.targetX - motion.x, motion.targetY - motion.y);
      const edge = Math.max(42, Math.min(width, height) * .055);
      const nearEdge = motion.x < edge || motion.x > width - edge || motion.y < edge || motion.y > height - edge;
      if (now >= motion.retargetAt || distance < Math.max(70, width * .055) || nearEdge) randomTarget(motion, now);

      const desiredHeading = Math.atan2(motion.targetY - motion.y, motion.targetX - motion.x);
      const headingDelta = normalizeAngle(desiredHeading - motion.heading);
      const turn = Math.max(-motion.turnRate * delta, Math.min(motion.turnRate * delta, headingDelta));
      motion.heading += turn;
      const glide = motion.baseSpeed * (.9 + Math.sin(motion.phase * .24) * .1);
      motion.speed += (glide - motion.speed) * Math.min(1, delta * .55);
      motion.x += Math.cos(motion.heading) * motion.speed * delta;
      motion.y += Math.sin(motion.heading) * motion.speed * delta;
      motion.phase += motion.phaseRate * delta;
    };

    resize();
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(canvas);
    const visibilityObserver = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }, { rootMargin: "12%" });
    visibilityObserver.observe(canvas);

    let disposed = false;
    Promise.all([
      loadImage("/page7-koi-cinnabar-v1.png"),
      loadImage("/page7-koi-ink-v1.png"),
    ]).then(([cinnabarKoi, inkKoi]) => {
      if (disposed) return;
      const now = performance.now();
      const motions: KoiMotion[] = [
        { x: width * .23, y: height * .78, heading: -.12, speed: 24, baseSpeed: 27, turnRate: .33, targetX: width * .7, targetY: height * .62, retargetAt: now + 4300, phase: .8, phaseRate: 3.35, scale: 1, alpha: .64 },
        { x: width * .78, y: height * .24, heading: Math.PI + .1, speed: 21, baseSpeed: 24, turnRate: .29, targetX: width * .34, targetY: height * .35, retargetAt: now + 6600, phase: 3.7, phaseRate: 3.05, scale: .88, alpha: .57 },
      ];

      redraw = () => {
        context.clearRect(0, 0, width, height);
        drawKoi(cinnabarKoi, motions[0]);
        drawKoi(inkKoi, motions[1]);
      };

      const draw = (time: number) => {
        if (disposed) return;
        const delta = Math.min(.04, Math.max(0, (time - lastTime) / 1000));
        lastTime = time;
        if (visible && !document.hidden) {
          if (!reducedMotion.matches) motions.forEach((motion) => updateMotion(motion, time, delta));
          redraw?.();
        }
        if (!reducedMotion.matches) frame = window.requestAnimationFrame(draw);
      };

      if (reducedMotion.matches) {
        motions[0].x = width * .2;
        motions[0].y = height * .78;
        motions[0].heading = -.1;
        motions[1].x = width * .8;
        motions[1].y = height * .25;
        motions[1].heading = Math.PI - .12;
        draw(now);
      } else {
        frame = window.requestAnimationFrame(draw);
      }
    }).catch(() => context.clearRect(0, 0, width, height));

    return () => {
      disposed = true;
      redraw = null;
      window.cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      visibilityObserver.disconnect();
    };
  }, []);

  return <div className="result-koi-layer" aria-hidden="true"><canvas ref={canvasRef} className="result-koi-pond" /></div>;
}

function BrushHexagram({ hexagram }: { hexagram: Hexagram }) {
  const bottomUp = KING_WEN_LINES_BOTTOM_UP[hexagram.king_wen_number - 1] ?? KING_WEN_LINES_BOTTOM_UP[0];
  const topDown = [...bottomUp].reverse();
  return <div className="brush-hexagram" role="img" aria-label={`${hexagram.name}卦象`}>
    {topDown.map((line, index) => <span key={`${hexagram.king_wen_number}-${index}`} className={`brush-yao ${line === "1" ? "is-yang" : "is-yin"}`} aria-hidden="true">
      {line === "1"
        ? <img src="/page7-yao-brush-v1.png" alt="" />
        : <><img src="/page7-yao-brush-short-v1.png" alt="" /><img src="/page7-yao-brush-short-v1.png" alt="" /></>}
    </span>)}
  </div>;
}

function Page8ModelReview({ reading }: { reading: Page8Reading }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const scene = reading.scenes[activeIndex];
  const isLast = activeIndex === reading.scenes.length - 1;

  useEffect(() => {
    setActiveIndex(0);
  }, [reading.template_version, reading.user_question]);

  useEffect(() => {
    titleRef.current?.focus({ preventScroll: true });
  }, [activeIndex]);

  if (!scene) return <section className="page8-model-review viewport-page"><p>第八页数据模型不完整，本次不展示。</p></section>;

  return <section id="page8-model-review" className="page8-model-review viewport-page" aria-labelledby="page8-model-review-title">
    <div className="page8-model-progress" aria-label={`第八页数据模型，第 ${scene.sequence} 幕，共 ${reading.scenes.length} 幕`}>
      <span>数据模型审核版</span>
      <b>{String(scene.sequence).padStart(2, "0")} / {String(reading.scenes.length).padStart(2, "0")}</b>
      <ol aria-hidden="true">{reading.scenes.map((item, index) => <li key={item.scene_id} className={index <= activeIndex ? "is-reached" : ""}>{item.title}</li>)}</ol>
    </div>
    <div className="page8-model-content">
      <header>
        <p className="eyebrow">第八页 · 读卦</p>
        <h2 id="page8-model-review-title" ref={titleRef} tabIndex={-1}>{scene.title}</h2>
        <p className="page8-model-purpose">{scene.purpose}</p>
        <p className="page8-model-question"><b>本次所问</b>{reading.user_question}</p>
      </header>
      <div className="page8-model-columns">
        <article className="page8-model-evidence">
          <span>卦象依据</span>
          <h3>{scene.deterministic.symbol && <i aria-hidden="true">{scene.deterministic.symbol}</i>}{scene.deterministic.king_wen_number ? `第 ${scene.deterministic.king_wen_number} 卦 · ` : ""}{scene.deterministic.primary_name}</h3>
          <p><b>如何形成</b>{scene.deterministic.formation}</p>
          <p><b>这一层看什么</b>{scene.deterministic.reading_role}</p>
          {scene.deterministic.canonical_text && <blockquote><b>{scene.deterministic.canonical_label}</b>{scene.deterministic.canonical_text}</blockquote>}
          {scene.deterministic.plain_note && <p className="page8-model-plain-note">{scene.deterministic.plain_note}</p>}
          {scene.deterministic.facts.length > 0 && <dl>{scene.deterministic.facts.map((fact) => <div key={`${scene.scene_id}-${fact.label}`}><dt>{fact.label}</dt><dd>{fact.value}</dd></div>)}</dl>}
          <small>来源：{scene.deterministic.source_name} · {scene.deterministic.source_reference}</small>
        </article>
        <article className="page8-model-interpretation">
          <span>结合所问</span>
          <h3>{scene.interpretation.layer_summary}</h3>
          <p>{scene.interpretation.reality_connection}</p>
          <div className="page8-model-boundary"><b>仍不能据此断定</b><p>{scene.interpretation.uncertainty_boundary}</p></div>
          <small>现实依据：{scene.interpretation.reality_refs.join("、")}　卦象依据：{scene.interpretation.evidence_refs.join("、")}</small>
        </article>
      </div>
      <footer>
        <p>{isLast ? "五幕数据已经展示完毕。此处停止，不进入第九页，也不展示行动建议。" : reading.epistemic_boundary}</p>
        {isLast
          ? <span className="page8-model-review-end">请审核五幕内容、顺序与解释边界</span>
          : <button type="button" onClick={() => setActiveIndex((index) => Math.min(index + 1, reading.scenes.length - 1))}>继续看{reading.scenes[activeIndex + 1]?.title}</button>}
      </footer>
    </div>
  </section>;
}

function ResultView({ response, onEdit, onClear, onSave, saving, saved }: { response: ApiResponse; onEdit: () => void; onClear: () => void; onSave: (action: string, reviewOn: string | null) => Promise<void>; saving: boolean; saved: boolean }) {
  const result = response.deterministic_result;
  const initialAction = response.personalized_reading?.action ?? result?.personalized_reading?.action ?? result?.clarity_report.next_action ?? "";
  const [action, setAction] = useState(`我准备这样做：${initialAction}`);
  const [reviewOn, setReviewOn] = useState(defaultReviewDate());
  const [readingStarted, setReadingStarted] = useState(false);
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

  function openDetailedReading() {
    setReadingStarted(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      document.getElementById("page8-model-review")?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      document.querySelector<HTMLElement>("#page8-model-review h2")?.focus({ preventScroll: true });
    }));
  }

  return <section id="result" className="result-shell flow-lock-screen" aria-labelledby="result-title">
    <section className="result-overview scroll-section viewport-page" data-reveal>
      <ResultKoiPond />
      <div className="result-verdict">
        <BrushHexagram hexagram={result.base_hexagram} />
      </div>
      <div className="result-summary">
        <span className="result-number">第 {result.base_hexagram.king_wen_number} 卦</span>
        <h2 id="result-title" tabIndex={-1}>{result.base_hexagram.name}</h2>
        {baseClassic && <blockquote className="result-canonical"><b>卦辞</b><span>{baseClassic.canonical_text}</span></blockquote>}
        <button type="button" className="result-detail-button" aria-controls="result-reading" aria-expanded={readingStarted} aria-disabled={!response.page8_reading} disabled={!response.page8_reading} onClick={openDetailedReading}>查看详细解卦</button>
      </div>
    </section>

    <div id="result-reading" hidden={!readingStarted}>
    {response.page8_reading ? <Page8ModelReview reading={response.page8_reading} /> : <section className="page8-model-review viewport-page"><p>第八页数据模型尚未生成，本次不展示。</p></section>}
    <div className="future-result-sections" hidden aria-hidden="true">
    <section id="why-reading" className="reading-scroll layered-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第一章 · 读卦</p><h2 tabIndex={-1}>本卦、互卦与变卦</h2><p>本卦看眼下的主要局面，互卦看内部怎样发展，变卦看变化之后重点转向哪里。先把三者逐一看清，再谈这件事应当如何判断。</p></header>
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
    </div>
    </div>
  </section>;
}

function EntryArtwork({ className, imgRef }: { className: string; imgRef?: RefObject<HTMLImageElement | null> }) {
  return <picture className={className}>
    <source media="(max-aspect-ratio: 3 / 4)" srcSet="/hero-entry-mobile-v7.webp" />
    <source media="(max-aspect-ratio: 4 / 3)" srcSet="/hero-entry-square-v7.webp" />
    <img ref={imgRef} src="/hero-entry-wide-v7.webp" alt="" loading="eager" decoding="async" fetchPriority="high" />
  </picture>;
}

function EntrySideButterfly({ className = "" }: { className?: string }) {
  const rigClassName = `entry-side-butterfly${className ? ` ${className}` : ""}`;
  return <span className={rigClassName}>
    <img className="entry-side-butterfly-wing" src="/hero-butterfly-perched-v3.png" alt="" />
    <img className="entry-side-butterfly-body" src="/hero-butterfly-perched-v3.png" alt="" />
  </span>;
}

function EntryButterflyFlight({ sequenceStarted }: { sequenceStarted: boolean }) {
  const cameraRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!sequenceStarted || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const camera = cameraRef.current;
    const wing = camera?.querySelector<HTMLElement>(".entry-side-butterfly-wing");
    if (!camera || !wing) return;
    let animationFrame = 0;
    let startTimer = 0;
    let previous = 0;
    let wingPhase = 0;
    const duration = 6600;

    const animate = (now: number) => {
      if (!previous) previous = now;
      const delta = Math.min(.034, (now - previous) / 1000);
      previous = now;
      const started = Number(camera.dataset.started || now);
      if (!camera.dataset.started) camera.dataset.started = String(now);
      const t = Math.min(1, (now - started) / duration);
      const eased = Math.min(1, t + .13 * Math.sin(Math.PI * t));
      const paced = Math.min(1, Math.max(0, eased + .022 * Math.sin(Math.PI * 2 * eased) * Math.sin(Math.PI * eased)));
      const parent = camera.offsetParent as HTMLElement | null;
      const width = parent?.clientWidth || window.innerWidth;
      const height = parent?.clientHeight || window.innerHeight;
      const endX = camera.offsetLeft;
      const endY = camera.offsetTop;
      const p0 = { x: width + Math.max(24, width * .018), y: height * .22 };
      const p1 = { x: width * .88, y: height * .56 };
      const p2 = { x: width * .63, y: height * .17 };
      const p3 = { x: endX, y: endY };
      const inv = 1 - paced;
      const x = inv ** 3 * p0.x + 3 * inv ** 2 * paced * p1.x + 3 * inv * paced ** 2 * p2.x + paced ** 3 * p3.x;
      const y = inv ** 3 * p0.y + 3 * inv ** 2 * paced * p1.y + 3 * inv * paced ** 2 * p2.y + paced ** 3 * p3.y;
      const dx = 3 * inv ** 2 * (p1.x - p0.x) + 6 * inv * paced * (p2.x - p1.x) + 3 * paced ** 2 * (p3.x - p2.x);
      const dy = 3 * inv ** 2 * (p1.y - p0.y) + 6 * inv * paced * (p2.y - p1.y) + 3 * paced ** 2 * (p3.y - p2.y);
      const spatialSpeed = Math.hypot(dx, dy) / Math.max(width, height);
      const flapRate = 2.25 + Math.min(2.7, spatialSpeed * 3.35);
      wingPhase += delta * flapRate * Math.PI * 2;
      const wingAngle = -32 - 32 * Math.sin(wingPhase);
      const heading = Math.max(-5.5, Math.min(5.5, Math.atan2(dy, Math.abs(dx)) * 180 / Math.PI * .22));
      const scale = .9 + paced * .1;
      const opacity = Math.min(1, t / .075) * (t < .965 ? 1 : Math.max(0, (1 - t) / .035));
      camera.style.opacity = String(opacity);
      camera.style.filter = `blur(${Math.max(0, .42 - paced * .42)}px)`;
      camera.style.transform = `translate3d(${x - endX}px, ${y - endY}px, 0) translate(-24%, -100%) scale(${scale}) rotate(${heading - 2}deg)`;
      wing.style.transform = `perspective(160px) rotateY(${wingAngle}deg)`;
      wing.style.filter = `brightness(${.82 + (wingAngle + 64) / 178})`;
      if (t < 1) animationFrame = window.requestAnimationFrame(animate);
      else camera.style.opacity = "0";
    };

    startTimer = window.setTimeout(() => {
      delete camera.dataset.started;
      previous = 0;
      animationFrame = window.requestAnimationFrame(animate);
    }, 800);
    return () => {
      window.clearTimeout(startTimer);
      window.cancelAnimationFrame(animationFrame);
    };
  }, [sequenceStarted]);

  return <span ref={cameraRef} className="entry-butterfly-camera"><EntrySideButterfly className="entry-butterfly-flight" /></span>;
}

type DissolveParticle = {
  x: number;
  y: number;
  r: number;
  g: number;
  b: number;
  alpha: number;
  size: number;
  velocityX: number;
  velocityY: number;
  sway: number;
  trail: number;
  stretch: number;
  phase: number;
  trigger: number;
  life: number;
};

function EntryWindDissolve({ sequenceStarted }: { sequenceStarted: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!sequenceStarted || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    let timer = 0;
    let animationFrame = 0;
    let dissolveLayer: HTMLElement | null = null;
    const duration = 5600;

    const begin = () => {
      const hero = canvas.closest<HTMLElement>(".entry-hero");
      dissolveLayer = hero?.querySelector<HTMLElement>(".entry-dissolve-layer") || null;
      const paper = hero?.querySelector<HTMLElement>(".entry-paper-surface");
      const branch = hero?.querySelector<HTMLImageElement>(".entry-plum-branch");
      const butterfly = hero?.querySelector<HTMLElement>(".entry-butterfly-perched");
      const butterflyImage = butterfly?.querySelector<HTMLImageElement>(".entry-side-butterfly-wing");
      if (!hero || !dissolveLayer || !paper || !branch || !butterfly || !butterflyImage || !branch.complete || !butterflyImage.complete) return;

      const heroRect = hero.getBoundingClientRect();
      const branchRect = branch.getBoundingClientRect();
      const butterflyRect = butterfly.getBoundingClientRect();
      const width = Math.max(1, heroRect.width);
      const height = Math.max(1, heroRect.height);
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * pixelRatio);
      canvas.height = Math.round(height * pixelRatio);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

      const sampleScale = .35;
      const sampleCanvas = document.createElement("canvas");
      sampleCanvas.width = Math.max(1, Math.round(width * sampleScale));
      sampleCanvas.height = Math.max(1, Math.round(height * sampleScale));
      const sampleContext = sampleCanvas.getContext("2d", { willReadFrequently: true });
      if (!sampleContext) return;
      sampleContext.fillStyle = getComputedStyle(paper).backgroundColor || "#e8ddca";
      sampleContext.fillRect(0, 0, sampleCanvas.width, sampleCanvas.height);
      const drawSource = (image: HTMLImageElement, rect: DOMRect) => {
        sampleContext.drawImage(
          image,
          (rect.left - heroRect.left) * sampleScale,
          (rect.top - heroRect.top) * sampleScale,
          rect.width * sampleScale,
          rect.height * sampleScale,
        );
      };
      drawSource(branch, branchRect);
      drawSource(butterflyImage, butterflyRect);

      const pixels = sampleContext.getImageData(0, 0, sampleCanvas.width, sampleCanvas.height).data;
      const maxParticles = Math.max(2600, Math.min(7600, Math.round(width * 3.8)));
      const particles: DissolveParticle[] = [];
      let seed = 0x7a4f2d;
      let seen = 0;
      const random = () => {
        seed = (seed * 1664525 + 1013904223) >>> 0;
        return seed / 4294967296;
      };

      for (let originY = 3; originY < height; originY += 7) {
        for (let originX = 3; originX < width; originX += 7) {
          if (random() > .5) continue;
          const sampleX = Math.min(sampleCanvas.width - 1, Math.max(0, Math.round(originX * sampleScale)));
          const sampleY = Math.min(sampleCanvas.height - 1, Math.max(0, Math.round(originY * sampleScale)));
          const index = (sampleY * sampleCanvas.width + sampleX) * 4;
          const normalizedX = originX / width;
          const normalizedY = originY / height;
          const erosionNoise =
            Math.sin(normalizedX * 19.7 + normalizedY * 8.3 + .4) * .055
            + Math.sin(normalizedX * 47.3 - normalizedY * 23.1 + 1.8) * .027
            + (random() - .5) * .052;
          const surfaceScore = normalizedX + normalizedY + erosionNoise;
          const timeProgress = Math.max(0, Math.min(1, (2.045 - surfaceScore) / 2.12));
          const fragmentScale = random() < .1 ? 1.45 : 1;
          const toneShift = 7 + random() * 18;
          const particle: DissolveParticle = {
            x: originX + (random() - .5) * 8,
            y: originY + (random() - .5) * 8,
            r: Math.max(0, pixels[index] - toneShift),
            g: Math.max(0, pixels[index + 1] - toneShift * .84),
            b: Math.max(0, pixels[index + 2] - toneShift * .62),
            alpha: .42 + random() * .4,
            size: (.9 + random() * 3.1) * fragmentScale,
            velocityX: 52 + random() * 110,
            velocityY: -46 + random() * 62,
            sway: 4 + random() * 15,
            trail: random() < .38 ? 6 + random() * 16 : 0,
            stretch: .65 + random() * 1.08,
            phase: random() * Math.PI * 2,
            trigger: Math.max(0, timeProgress * duration + (random() - .5) * 240),
            life: 1080 + random() * 880,
          };
          seen += 1;
          if (particles.length < maxParticles) particles.push(particle);
          else {
            const replacement = Math.floor(random() * seen);
            if (replacement < maxParticles) particles[replacement] = particle;
          }
        }
      }

      const startedAt = performance.now();
      const draw = (now: number) => {
        const elapsed = now - startedAt;
        const progress = Math.min(1, elapsed / duration);
        const sceneFade = elapsed <= duration ? 1 : Math.max(0, 1 - (elapsed - duration) / 650);
        const smooth = progress * progress * (3 - 2 * progress);
        const eased = progress * .7 + smooth * .3;
        const threshold = 2.055 - eased * 2.15;
        const boundaryPoints: string[] = ["0% 0%", "100% 0%"];
        for (let index = 120; index >= 0; index -= 1) {
          const normalizedX = index / 120;
          const staticErosion =
            Math.sin(normalizedX * 7.6 + .45) * .055
            + Math.sin(normalizedX * 17.9 + 1.9) * .03
            + Math.sin(normalizedX * 39.3 + 3.2) * .014
            + Math.sin(normalizedX * 83.7 + .7) * .006;
          const movingErosion =
            (Math.sin(normalizedX * 29 - progress * 7.2) * .016
              + Math.sin(normalizedX * 53 + progress * 4.6) * .007)
            * Math.sin(Math.PI * progress);
          const normalizedY = Math.max(0, Math.min(1, threshold - normalizedX + staticErosion + movingErosion));
          boundaryPoints.push(`${(normalizedX * 100).toFixed(2)}% ${(normalizedY * 100).toFixed(2)}%`);
        }
        dissolveLayer?.style.setProperty("clip-path", `polygon(${boundaryPoints.join(", ")})`);

        context.clearRect(0, 0, width, height);
        for (const particle of particles) {
          const age = elapsed - particle.trigger;
          if (age < 0 || age > particle.life) continue;
          const lifeProgress = age / particle.life;
          const driftX = particle.velocityX * age / 1000 + 42 * lifeProgress * lifeProgress;
          const driftY = particle.velocityY * age / 1000 + Math.sin(particle.phase + lifeProgress * 7) * particle.sway;
          const opacity = Math.sin(Math.PI * Math.min(1, lifeProgress * 1.18)) * (1 - lifeProgress * .42) * particle.alpha * sceneFade;
          const size = particle.size * (1 + lifeProgress * .58);
          const particleX = particle.x + driftX;
          const particleY = particle.y + driftY;
          if (particle.trail > 0) {
            context.beginPath();
            context.strokeStyle = `rgba(${particle.r},${particle.g},${particle.b},${opacity * .42})`;
            context.lineWidth = Math.max(.55, size * .42);
            context.moveTo(particleX - particle.trail * (.42 + lifeProgress), particleY + particle.trail * .08);
            context.lineTo(particleX, particleY);
            context.stroke();
          }
          context.beginPath();
          context.fillStyle = `rgba(${particle.r},${particle.g},${particle.b},${opacity})`;
          context.ellipse(particleX, particleY, size * particle.stretch, Math.max(.5, size * .56), Math.sin(particle.phase) * .34, 0, Math.PI * 2);
          context.fill();
        }

        if (elapsed < duration + 680) animationFrame = window.requestAnimationFrame(draw);
        else context.clearRect(0, 0, width, height);
      };
      animationFrame = window.requestAnimationFrame(draw);
    };

    timer = window.setTimeout(begin, 9300);
    return () => {
      window.clearTimeout(timer);
      window.cancelAnimationFrame(animationFrame);
      dissolveLayer?.style.removeProperty("clip-path");
    };
  }, [sequenceStarted]);

  return <canvas ref={canvasRef} className="entry-wind-dissolve" />;
}

function EntryOpening({ sequenceStarted }: { sequenceStarted: boolean }) {
  return <div className="entry-opening" aria-hidden="true">
    <span className="entry-dissolve-layer">
      <span className="entry-paper-surface" />
      <span className="entry-dissolve-subject">
        <img className="entry-plum-branch entry-critical-asset" src="/hero-plum-branch-cinematic-v2.webp" alt="" loading="eager" decoding="async" fetchPriority="high" />
        <span className="entry-butterfly-perched">
          <EntrySideButterfly className="entry-butterfly-perch-profile" />
        </span>
      </span>
      <EntryButterflyFlight sequenceStarted={sequenceStarted} />
    </span>
    <img className="entry-vfx-preload entry-critical-asset" src="/hero-butterfly-perched-v3.png" alt="" loading="eager" decoding="async" fetchPriority="high" />
    <EntryWindDissolve sequenceStarted={sequenceStarted} />
  </div>;
}

function InquiryInkScene() {
  return <div className="inquiry-ink-scene" aria-hidden="true">
    <img className="inquiry-ink-layer inquiry-ink-base" src="/question-pine-cloud-base-v2.webp" alt="" loading="eager" decoding="async" />
    <InquiryCloudfallCanvas layer="back" />
    <img className="inquiry-ink-layer inquiry-mountain-occluder" src="/question-cloudfall-mountain-v5.png" alt="" loading="eager" decoding="async" />
    <InquiryCloudfallCanvas layer="front" />
    <img className="inquiry-ink-layer inquiry-pine-tree" src="/question-pine-tree-v2.png" alt="" loading="eager" decoding="async" />
  </div>;
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
  const [flowPage, setFlowPage] = useState(1);
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
  const methodAdvanceTimerRef = useRef<number | null>(null);
  const activePersonalizedRequestRef = useRef<string | null>(null);
  const flowPageRef = useRef(1);

  function advanceFlow(nextPage: number, focusId?: string) {
    if (nextPage <= flowPageRef.current || nextPage > 7) return;
    flowPageRef.current = nextPage;
    setFlowPage(nextPage);
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    if (focusId) {
      window.requestAnimationFrame(() => document.getElementById(focusId)?.focus({ preventScroll: true }));
    }
  }

  useLayoutEffect(() => {
    if (!finalQuestionConfirmed) return;
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    const focusFrame = window.requestAnimationFrame(() => {
      document.getElementById("casting-title")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(focusFrame);
  }, [finalQuestionConfirmed]);

  useEffect(() => {
    const openingSavedReading = Boolean(sessionStorage.getItem(JOURNAL_OPEN_KEY));
    if (!openingSavedReading) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    let cancelled = false;
    let frame = 0;
    let fallbackTimer = 0;
    const criticalImages = [
      entryHeroImageRef.current,
      ...Array.from(document.querySelectorAll<HTMLImageElement>(".entry-critical-asset")),
    ];
    const criticalArtworkReady = Promise.all(criticalImages.map((image) => image?.decode().catch(() => undefined)));
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
    const root = document.documentElement;
    const body = document.body;
    const previousRestoration = window.history.scrollRestoration;
    root.classList.add("flow-scroll-locked");
    body.classList.add("flow-scroll-locked");
    window.history.scrollRestoration = "manual";
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });

    const blockScroll = (event: Event) => event.preventDefault();
    const blockScrollKeys = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const isInteractive = Boolean(target?.closest("input, textarea, select, button, [contenteditable='true']"));
      if (!isInteractive && ["ArrowDown", "ArrowUp", "End", "Home", "PageDown", "PageUp", " "].includes(event.key)) {
        event.preventDefault();
      }
    };
    const holdFlowPosition = () => {
      if (window.scrollX !== 0 || window.scrollY !== 0) window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    };
    window.addEventListener("wheel", blockScroll, { passive: false });
    window.addEventListener("touchmove", blockScroll, { passive: false });
    window.addEventListener("keydown", blockScrollKeys);
    window.addEventListener("scroll", holdFlowPosition, { passive: true });
    return () => {
      root.classList.remove("flow-scroll-locked");
      body.classList.remove("flow-scroll-locked");
      window.history.scrollRestoration = previousRestoration;
      window.removeEventListener("wheel", blockScroll);
      window.removeEventListener("touchmove", blockScroll);
      window.removeEventListener("keydown", blockScrollKeys);
      window.removeEventListener("scroll", holdFlowPosition);
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
    advanceFlow(2, "method-title");
  }

  function confirmMethodReady() {
    if (methodReady) return;
    setMethodReady(true);
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    methodAdvanceTimerRef.current = window.setTimeout(() => {
      advanceFlow(3, "inquiry-title");
      methodAdvanceTimerRef.current = null;
    }, reducedMotion ? 0 : 780);
  }

  function writeMethodLine(index: number) {
    setPreviewMethodLine(null);
    setActiveMethodLine(index);
    setMethodWritingRun((run) => run + 1);
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
    advanceFlow(4);
  }

  function continueToFinalQuestion() {
    advanceFlow(5, "final-question-title");
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
    advanceFlow(6, "casting-title");
  }

  function finishPersonalizedRequest(payload: ApiResponse, requestId: string): void {
    if (activePersonalizedRequestRef.current !== requestId) return;
    activePersonalizedRequestRef.current = null;
    sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
    if (payload.status !== "SUCCESS" || !payload.personalized_reading || !payload.page8_reading || !payload.deterministic_result?.clarity_report) {
      throw new Error(payload.error || "本次解读没有通过检查，也不会自动重新生成。");
    }
    setResponse(payload);
    setProgress("");
  }

  async function pollPersonalizedRequest(requestId: string, cancelled: () => boolean = () => false): Promise<void> {
    try {
      const payload = await pollPersonalizedTask(requestId, {
        fetchResult: () => fetch(`/api/v4/meihua?request_id=${encodeURIComponent(requestId)}`, { cache: "no-store" }),
        sleep,
        cancelled,
      });
      if (payload) finishPersonalizedRequest(payload as ApiResponse, requestId);
    } catch (caught) {
      if (caught instanceof PersonalizedPollError && caught.terminal) sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
      throw caught;
    }
  }

  useEffect(() => {
    const activeRequestId = sessionStorage.getItem(ACTIVE_REQUEST_KEY);
    if (!activeRequestId || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$/.test(activeRequestId)) return;
    activePersonalizedRequestRef.current = activeRequestId;
    let cancelled = false;
    const resumeTimer = window.setTimeout(() => {
      void pollPersonalizedRequest(activeRequestId, () => cancelled)
        .catch(() => { if (!cancelled) sessionStorage.removeItem(ACTIVE_REQUEST_KEY); });
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
      setQuestion(record.question); setDomain(record.structured_intake.question_domain); setGoal(record.structured_intake.decision_goal); setHorizon(record.structured_intake.time_horizon); setStage(record.structured_intake.decision_stage); setUncertainty(record.structured_intake.key_uncertainty); setRiskProfile(record.structured_intake.decision_risk_profile ?? "STANDARD"); setNumbers(record.numbers.map(String)); setDiscernmentCompletionReason("ENOUGH"); setIntakeComplete(true); setSavedRecordId(record.id);
      setResponse({ status: "SUCCESS", user_question: record.question, structured_intake: record.structured_intake, deterministic_result: record.result, personalized_reading: record.result.personalized_reading ?? null });
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!response) return;
    const frame = window.requestAnimationFrame(() => {
      advanceFlow(7, "result-title");
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
    setNumbers(["", "", ""]); setIntakeComplete(false); setDiscernmentCompletionReason("ENOUGH"); setFinalQuestionDecisionMade(false); setFinalQuestionConfirmed(false); setResponse(null); setError(""); setSavedRecordId(null);
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
    if (activeRequestId) {
      activePersonalizedRequestRef.current = null;
      sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
    }

    const factLines = nonemptyLines(facts);
    const unknownLines = nonemptyLines(unknowns);
    const actionLines = nonemptyLines(actions);
    const responseLines = nonemptyLines(observableResponses);
    const parsed = numbers.map(Number);
    const textLists = [factLines, unknownLines, actionLines, responseLines];
    const earlyExit = discernmentCompletionReason === "USER_EARLY";
    const useDeterministicOnly = earlyExit || factLines.length < 1 || unknownLines.length < 1;
    if (question.trim().length < 6 || question.trim().length > 160 || !intakeComplete || !domain || !goal || !horizon || !stage || !uncertainty || !riskProfile || factLines.length > 8 || unknownLines.length > 6 || actionLines.length > 6 || responseLines.length > 6 || textLists.some((items) => items.some((item) => item.length > 400)) || parsed.some((n, index) => !numbers[index] || !Number.isInteger(n) || n < 1 || n > 999)) {
      setError("请在右侧三个位置，各输入一个1–999的整数。"); return;
    }
    setLoading(true); setProgress("正在按三数成卦……");
    const deterministicRequest = fetch("/api/v3/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({
        contract_version: "SITES_MEIHUA_API_CONTRACT_V3",
        request_id: `sites-${crypto.randomUUID()}`,
        question_text: question.trim(), question_domain: domain, decision_goal: goal,
        time_horizon: horizon, decision_stage: stage, key_uncertainty: uncertainty,
        numbers: parsed, locale: "zh-CN", client_timestamp: new Date().toISOString(),
        user_acknowledgements: { deterministic_only: true, narrative_unverified: true, question_text_not_evidence: true },
      }),
    });

    if (!useDeterministicOnly) {
      const requestId = `sites-${crypto.randomUUID()}`;
      activePersonalizedRequestRef.current = requestId;
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
      void (async () => {
        try {
          let accepted = false;
          for (let attempt = 0; attempt < 3 && !accepted; attempt += 1) {
            try {
              const request = await fetch("/api/v4/meihua", { method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store", body });
              const payload = await request.json() as ApiResponse;
              if (request.status === 202) { accepted = true; break; }
              if (request.ok) { finishPersonalizedRequest(payload, requestId); return; }
              if (request.status !== 503) {
                sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
                return;
              }
            } catch (caught) {
              if (caught instanceof Error && !/Failed to fetch|fetch failed|network/i.test(caught.message)) return;
            }
            await sleep(1_500);
          }
          if (accepted) await pollPersonalizedRequest(requestId);
        } catch {
          sessionStorage.removeItem(ACTIVE_REQUEST_KEY);
        }
      })();
    }

    try {
      const request = await deterministicRequest;
      const payload = await request.json() as ApiResponse;
      if (!request.ok || payload.status !== "SUCCESS" || !payload.deterministic_result?.clarity_report) {
        throw new Error(payload.error || payload.errors?.[0]?.message || "本次未能完成排盘。");
      }
      setResponse(payload);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "本次未能完成排盘。"); }
    finally { setLoading(false); setProgress(""); }
  }

  const emphasizedMethodLine = activeMethodLine ?? previewMethodLine;
  return <>
    <header className={`site-header home-header${homeNavigationVisible ? " is-visible" : ""}`} aria-hidden="true" hidden>
      <a className="wordmark" href="#top" tabIndex={homeNavigationVisible ? undefined : -1}>观象</a>
      <nav><a href="#method" tabIndex={homeNavigationVisible ? undefined : -1}>如何观</a><a href={methodReady ? "#inquiry" : "#method"} onClick={(event) => { if (!methodReady) { event.preventDefault(); document.getElementById("method-ready")?.focus(); } }} tabIndex={homeNavigationVisible ? undefined : -1}>开始问</a><a href="/journal" tabIndex={homeNavigationVisible ? undefined : -1}>观事簿</a></nav>
      <small>确定性排盘 · 个性化解读</small>
    </header>
    <main id="top" className="scroll-canvas flow-shell" data-flow-page={flowPage}>
      <section className={`hero entry-hero scroll-section flow-lock-screen${entrySequenceStarted ? " is-sequence-started" : ""}${titleAwake ? " is-title-awake" : ""}`} hidden={flowPage !== 1} aria-labelledby="hero-title">
        <EntryArtwork className="entry-hero-final" imgRef={entryHeroImageRef} />
        <EntryOpening sequenceStarted={entrySequenceStarted} />
        <EntryArtwork className="entry-title-focus" />
        <img className="entry-name-seal" src="/hero-yuanshuai-seal-v1.webp" alt="" aria-hidden="true" />
        <img className="entry-classic-calligraphy" src="/hero-classic-calligraphy-v1.webp" alt="" aria-hidden="true" />
        <div className="entry-birds-life" aria-hidden="true">
          {["a", "b"].map((flock) => <div className={`entry-bird-flock entry-bird-flock-${flock}`} key={flock}>
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
          </div>)}
        </div>
        <h1 id="hero-title" className="sr-only">观象</h1>
        <p className="sr-only">心有所问 静观其象</p>
        <button type="button" className="hero-title-hotspot" aria-pressed={titleAwake} aria-label="让观象题字与水墨太极浮现" onPointerEnter={() => setTitleAwake(true)} onPointerLeave={() => setTitleAwake(false)} onFocus={() => setTitleAwake(true)} onBlur={() => setTitleAwake(false)} onClick={() => setTitleAwake((current) => !current)}><span className="sr-only">观象</span></button>
        <blockquote className="sr-only">寂然不动，感而遂通天下之故。</blockquote>
        <span className="sr-only">《周易·系辞上》</span>
        <audio ref={audioRef} src="/audio/guqin-zheng-diao.ogg" preload="none" loop />
        <button type="button" className="hero-sound-control" aria-pressed={soundOn} aria-label={soundOn ? "暂停古琴音乐" : "播放古琴音乐"} onClick={toggleSound}><span className="hero-sound-label" aria-hidden="true">闻琴</span><img src="/hero-guqin-horizontal-v2.webp" alt="" aria-hidden="true" /><span className="sr-only">{soundOn ? "暂停古琴音乐" : "播放古琴音乐"}</span></button>
        <button type="button" className="hero-scroll-cue" aria-label="进入观象之法" onClick={enterMethod}><img className="entry-boat-life" src="/hero-boat-v1.png" alt="" aria-hidden="true" /><img className="entry-down-cue" src="/hero-down-cue-v1.png" alt="" aria-hidden="true" /></button>
      </section>

      <section id="method" className={`method scroll-section flow-lock-screen${methodReady ? " is-ready" : ""}`} hidden={flowPage !== 2} data-reveal aria-labelledby="method-title">
        <MethodRiverFlow />
        <picture className="method-landscape">
          <source media="(max-width: 900px)" srcSet="/method-river-mobile-v2.webp" />
          <img src="/method-river-wide-v2.webp" alt="" />
        </picture>
        <VerticalBrand />
        <div className="method-stage">
          <div className="method-quote"><h2 id="method-title" aria-label="在天成象 在地成形 变化见矣" className={emphasizedMethodLine === null ? undefined : "has-active"}>{METHOD_CLASSIC_LINES.map((line, index) => <button key={line} type="button" className={`method-ink-line${emphasizedMethodLine === index ? " is-active" : ""}${activeMethodLine === index ? " is-writing" : ""}`} aria-pressed={activeMethodLine === index} aria-label={`${line} 点击观看整句书写过程`} onPointerEnter={(event) => { if (event.pointerType !== "touch" && activeMethodLine === null) setPreviewMethodLine(index); }} onPointerLeave={(event) => { if (event.pointerType !== "touch") setPreviewMethodLine(null); }} onFocus={() => { if (activeMethodLine === null) setPreviewMethodLine(index); }} onBlur={() => setPreviewMethodLine(null)} onClick={() => writeMethodLine(index)}><span className="method-line-label">{line}</span>{activeMethodLine === index && <span key={`${line}-${methodWritingRun}`} className="method-writing-layer" aria-hidden="true">{Array.from(line).map((character, characterIndex) => <i key={`${character}-${characterIndex}`} style={{ "--char-index": characterIndex } as CSSProperties}>{character}</i>)}</span>}</button>)}</h2><cite>《周易·系辞上》</cite></div>
          <div className="method-explainer">
            <p className="method-lead">炁是流动的<br />也带动象的变化</p>
            <p className="method-breath"><span>请先放下急于知道答案的心<br />让我用四个步骤<br />带你进入观象的状态<br />现在缓缓做三次深呼吸<br />然后</span><b>进入第一步：正问</b></p>
          </div>
        </div>
        <div className="method-readiness"><button id="method-ready" className="method-cta" type="button" aria-label="进入正问" aria-pressed={methodReady} aria-describedby="method-ready-status" onClick={confirmMethodReady}><span className="method-cta-label">进入正问</span></button><p id="method-ready-status" className="method-ready-status" role="status" aria-live="polite">{methodReady ? "准备状态已确认，正在进入正问。" : ""}</p></div>
      </section>

      <section id="inquiry" className={`inquiry scroll-section flow-lock-screen${flowPage >= 4 ? " is-nested-flow-page" : ""}${finalQuestionConfirmed ? " has-casting-step" : ""}`} data-reveal hidden={!methodReady || flowPage < 3 || flowPage > 6} aria-labelledby="inquiry-title">
        <InquiryInkScene />
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <div className="inquiry-stage" hidden={flowPage !== 3}>
            <header className="inquiry-heading flow-title-heading">
              <p className="eyebrow">观象之法 · 壹</p>
              <h2 id="inquiry-title" tabIndex={-1}>正问</h2>
            </header>

            <div className="inquiry-writing">
              <label className="question-label" htmlFor="primary-question"><span>此刻，你想问的是什么？</span></label>
              <textarea id="primary-question" aria-label="你想问的问题" aria-describedby="question-guidance question-count" placeholder="请把你的问题写在这里……" value={question} maxLength={160} onChange={(event) => { setQuestion(event.target.value); setQuestionConfirmed(false); setIntakeComplete(false); setDiscernmentCompletionReason("ENOUGH"); setFinalQuestionDecisionMade(false); setFinalQuestionConfirmed(false); }} />
              <div className="question-meta"><p id="question-guidance">不必担心问得是否准确。<br />先把心里的话写下来，下一步，我会陪你慢慢辨清。</p><span id="question-count" aria-live="polite">{question.trim().length} / 160</span></div>

              <div className="inquiry-advance"><button type="button" disabled={question.trim().length < 6} onClick={confirmQuestion}><span>{questionConfirmed ? "这一问已写下" : <span>问题已经写好<br />进入第二步：辨识</span>}</span></button><p role="status" aria-live="polite">{question.trim().length > 0 && question.trim().length < 6 ? "请再写详细一点，让我更清楚你想问的是什么。" : ""}</p></div>
            </div>
          </div>

          <div className="inquiry-future-flow" hidden={!questionConfirmed || flowPage < 4 || flowPage > 6}>
          <section id="discernment" className="discernment scroll-section flow-lock-screen" hidden={flowPage !== 4} aria-labelledby="discernment-title">
            <div className="discernment-artwork" aria-hidden="true">
              <img src="/discernment-chrysanthemum-mountains-v2.png" alt="" />
            </div>
            <VerticalBrand />
            <div className="discernment-stage">
              <header className="discernment-heading flow-title-heading">
                <p className="eyebrow">观象之法 · 贰</p>
                <h2 id="discernment-title" tabIndex={-1}>辨识</h2>
                <p>卜卦之前<br />我还有一些问题<br />帮助你把纷繁的念头慢慢理清</p>
              </header>
              <div className="discernment-dialogue">
                <div className="discernment-cranes" aria-hidden="true">
                  <span className="discernment-crane discernment-crane-leading">
                    <i className="discernment-crane-bank">
                      <span className="discernment-crane-facing discernment-crane-facing-right" />
                      <span className="discernment-crane-facing discernment-crane-facing-left" />
                      <span className="discernment-crane-turn discernment-crane-turn-right" />
                      <span className="discernment-crane-turn discernment-crane-turn-left" />
                    </i>
                  </span>
                  <span className="discernment-crane discernment-crane-following">
                    <i className="discernment-crane-bank">
                      <span className="discernment-crane-facing discernment-crane-facing-right" />
                      <span className="discernment-crane-facing discernment-crane-facing-left" />
                      <span className="discernment-crane-turn discernment-crane-turn-right" />
                      <span className="discernment-crane-turn discernment-crane-turn-left" />
                    </i>
                  </span>
                </div>
                {originalQuestion.length >= 6 ? <GuidedIntake key={originalQuestion} question={originalQuestion} onFacts={setFacts} onUnknowns={setUnknowns} onActions={setActions} onObservableResponses={setObservableResponses} onSuggestion={receiveQuestionSuggestion} onStructured={({ domain: nextDomain, goal: nextGoal, horizon: nextHorizon, stage: nextStage, uncertainty: nextUncertainty, riskProfile: nextRiskProfile }) => { setDomain(nextDomain); setGoal(nextGoal); setHorizon(nextHorizon); setStage(nextStage); setUncertainty(nextUncertainty); if (nextRiskProfile) setRiskProfile(nextRiskProfile); }} onCompletionReason={setDiscernmentCompletionReason} onComplete={setIntakeComplete} onContinue={continueToFinalQuestion} /> : <p className="dialogue-prerequisite">先在上一步写下至少六个字的具体问题，辨识对话才会开始。</p>}
              </div>
            </div>
          </section>



          <FinalQuestion hidden={!intakeComplete || flowPage !== 5} originalQuestion={originalQuestion} suggestedQuestion={suggestedQuestion} earlyExit={discernmentCompletionReason === "USER_EARLY"} decisionMade={finalQuestionDecisionMade} confirmed={finalQuestionConfirmed} onChooseOriginal={chooseOriginalQuestion} onChooseSuggestion={chooseSuggestedQuestion} onConfirm={confirmFinalQuestion} />

          <section id="casting" className="inquiry-step inquiry-panel number-step casting-number-step viewport-page flow-lock-screen" hidden={!finalQuestionConfirmed || flowPage !== 6} aria-labelledby="casting-title">
            <div className="casting-peony-scene" aria-hidden="true">
              <div className="casting-peony-backdrop" />
              {PEONY_BREATHS.map((breath, index) => <span
                className={`peony-bloom peony-bloom-scene-${index + 1}`}
                key={breath.numeral}
              >
                <img className="peony-bloom-image" src={breath.flower} alt="" />
              </span>)}
              <div className="peony-petal-layer">
                {PEONY_BREATHS.map((breath, index) => <span
                  className={`peony-petal-origin peony-bloom-scene-${index + 1}`}
                  key={`petals-${breath.numeral}`}
                  style={{ "--breath-delay": `${index * -1.6}s` } as CSSProperties}
                >
                  {PEONY_PETAL_MOTIONS.map((motion, petalIndex) => <img
                    className="peony-falling-petal"
                    src="/casting-peony-petal-v1.png"
                    alt=""
                    key={`${breath.numeral}-${petalIndex}`}
                    style={{
                      "--petal-delay": `${motion.delay}s`,
                      "--petal-left": `${motion.left}%`,
                      "--petal-quarter-x": `${motion.midX * .45}vw`,
                      "--petal-mid-x": `${motion.midX}vw`,
                      "--petal-late-x": `${motion.travelX * .62}vw`,
                      "--petal-travel-x": `${motion.travelX}vw`,
                      "--petal-quarter-y": `${motion.travelY * .17}vh`,
                      "--petal-mid-y": `${motion.travelY * .4}vh`,
                      "--petal-late-y": `${motion.travelY * .7}vh`,
                      "--petal-travel-y": `${motion.travelY}vh`,
                      "--petal-quarter-spin": `${motion.spin * .18}deg`,
                      "--petal-mid-spin": `${motion.spin * .43}deg`,
                      "--petal-late-spin": `${motion.spin * .72}deg`,
                      "--petal-spin": `${motion.spin}deg`,
                      "--petal-quarter-flip-x": `${motion.flipX * .23}deg`,
                      "--petal-mid-flip-x": `${motion.flipX * .48}deg`,
                      "--petal-late-flip-x": `${motion.flipX * .76}deg`,
                      "--petal-flip-x": `${motion.flipX}deg`,
                      "--petal-quarter-flip-y": `${motion.flipY * .2}deg`,
                      "--petal-mid-flip-y": `${motion.flipY * .46}deg`,
                      "--petal-late-flip-y": `${motion.flipY * .74}deg`,
                      "--petal-flip-y": `${motion.flipY}deg`,
                      "--petal-size": `${motion.size}px`,
                      "--petal-duration": `${motion.duration}s`,
                    } as CSSProperties}
                  />)}
                </span>)}
              </div>
            </div>
            <VerticalBrand />
            <header className="final-question-heading casting-heading flow-title-heading">
              <p className="eyebrow">观象之法 · 肆</p>
              <h3 id="casting-title" tabIndex={-1}>成卦</h3>
              <p className="casting-contemplation">
                <span>第四步：成卦</span>
                <span>心中默念最终确认的问题</span>
                <span>缓缓做三次呼吸</span>
                <span>每一息结束，凭第一直觉写下一个数</span>
              </p>
              <fieldset className="peony-number-field">
                <legend className="sr-only">依三次呼吸取三个整数</legend>
                {PEONY_BREATHS.map((breath, index) => <label
                  className={`peony-number peony-number-${index + 1}`}
                  key={breath.numeral}
                >
                  <span className="peony-number-copy"><b>{breath.numeral}</b><small>{breath.guidance}</small></span>
                  <input aria-label={`第${index + 1}个数字`} aria-describedby="casting-range-note" placeholder={breath.placeholder} type="number" inputMode="numeric" min="1" max="999" value={numbers[index]} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} />
                </label>)}
              </fieldset>
              <p className="casting-range-note" id="casting-range-note">每次呼吸结束后，在右侧输入一个1–999的整数</p>
              {progress && <span className="sr-only" role="status" aria-live="polite">{progress}</span>}
              {error && <p className="error casting-submit-error" role="alert">{error}</p>}
              <button type="submit" className="cast-button casting-submit" disabled={loading}><BaguaMark />{loading ? <span>正在成卦，请稍候<br />完成后将自动进入卦象页</span> : <span>三个数已经取好<br />开始成卦</span>}</button>
            </header>

            <div className="casting-number-workspace" aria-hidden="true">
              <img className="peony-number-petal peony-number-petal-1" src="/casting-peony-petal-v1.png" alt="" />
              <img className="peony-number-petal peony-number-petal-2" src="/casting-peony-petal-v1.png" alt="" />
              <img className="peony-number-petal peony-number-petal-3" src="/casting-peony-petal-v1.png" alt="" />
            </div>
          </section>

          </div>
        </form>
      </section>

      {response && flowPage === 7 && <ResultView response={response} onEdit={editQuestion} onClear={clearQuestion} onSave={saveObservation} saving={savingRecord} saved={savedRecordId !== null} />}
      <aside className="version-note" hidden>卦象不是预先写好的判词，而是对当下结构的一次照见。所谓“穷则变，变则通”，心念与行动一变，后续条件也会随之改变。得顺势之象，不可因此停步；见阻力之象，也不必自弃。观象的意义，是让我们看见照旧前行可能抵达之处，从而及早准备、修正与行动。</aside>
    </main>
    <footer className="site-footer" hidden><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span><nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私说明</a></nav></footer>
  </>;
}
