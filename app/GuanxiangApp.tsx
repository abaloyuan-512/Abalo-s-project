"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

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
};
type StructuredIntake = {
  question_domain: string;
  decision_goal: string;
  time_horizon: string;
  decision_stage: string;
  key_uncertainty: string;
};
type ApiResponse = {
  status?: string;
  user_question?: string;
  structured_intake?: StructuredIntake;
  deterministic_result?: ProductResult | null;
  error?: string;
  errors?: { message?: string }[];
};
type JournalRecord = {
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
type JournalDraft = Pick<JournalRecord, "action_text" | "review_on" | "reality_text" | "learning_text" | "status">;

const DOMAINS = {
  WORK_CAREER: "工作与职业",
  PROJECT_COOPERATION: "项目与合作",
  RELATIONSHIP_COMMUNICATION: "关系与沟通",
  PERSONAL_PLANNING: "个人规划",
} as const;
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
const UNCERTAINTIES = { CONDITIONS: "还缺哪些条件", OTHER_RESPONSE: "对方是否回应", OWN_COMMITMENT: "自己投入多少", TIMING: "现在是否合适" } as const;

const QUESTION_EXAMPLES = [
  { topic: "工作", domain: "WORK_CAREER", text: "这份工作已经让我很疲惫，我还应该继续留下吗？" },
  { topic: "工作", domain: "WORK_CAREER", text: "面对现在的工作机会，我下一步最该先确认什么？" },
  { topic: "合作", domain: "PROJECT_COOPERATION", text: "这次合作，我还应该继续投入吗？" },
  { topic: "合作", domain: "PROJECT_COOPERATION", text: "对方迟迟没有明确回应，我还要继续推进这个项目吗？" },
  { topic: "关系", domain: "RELATIONSHIP_COMMUNICATION", text: "这段关系一直没有进展，我还要继续主动吗？" },
  { topic: "关系", domain: "RELATIONSHIP_COMMUNICATION", text: "我们最近反复争执，我应该先沟通还是先冷静一段时间？" },
  { topic: "规划", domain: "PERSONAL_PLANNING", text: "我现在开始这项长期计划，最需要先准备什么？" },
  { topic: "规划", domain: "PERSONAL_PLANNING", text: "这项计划投入越来越多，我是否应该先停下来调整？" },
] as const;

const JOURNAL_KEY = "guanxiang-observation-key-v1";

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
    src="/fuxi-bagua-taiji.png"
    alt={decorative ? "" : "完整八卦与太极图"}
    aria-hidden={decorative ? "true" : undefined}
  />;
}

function ChoiceMenu({ label, value, options, disabled = false, onChange }: {
  label: string;
  value: string;
  options: Record<string, string>;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const selected = options[value] ?? "请选择";
  return <div className={`choice-field ${disabled ? "is-disabled" : ""}`}>
    <span>{label}</span>
    <details className="choice-menu">
      <summary aria-label={`${label}：${selected}`} aria-disabled={disabled} onClick={(event) => { if (disabled) event.preventDefault(); }}>
        <BaguaMark />
        <b>{selected}</b>
      </summary>
      <div role="listbox" aria-label={label}>
        {Object.entries(options).map(([key, text]) => <button
          key={key}
          type="button"
          role="option"
          aria-selected={value === key}
          onClick={(event) => {
            onChange(key);
            event.currentTarget.closest("details")?.removeAttribute("open");
          }}
        ><BaguaMark />{text}</button>)}
      </div>
    </details>
  </div>;
}

function OptionList({ name, value, options, onChange }: { name: string; value: string; options: Record<string, string>; onChange: (value: string) => void }) {
  return <div className="option-list" role="radiogroup" aria-label={name}>{Object.entries(options).map(([key, label]) => (
    <label key={key} className={value === key ? "selected" : ""}>
      <input type="radio" name={name} value={key} checked={value === key} onChange={() => onChange(key)} />
      <BaguaMark />
      <span>{label}</span>
    </label>
  ))}</div>;
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

function JournalSection({ records, loading, message, hasUnsavedResult, onOpen, onUpdate, onDelete, onExport, onSaveCurrent }: {
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
  if (!result) return null;
  const report = result.clarity_report;
  const cultural = result.cultural_reading;
  const question = response.user_question ?? "你所问之事";
  const [action, setAction] = useState(`我准备这样做：${report.next_action}`);
  const [reviewOn, setReviewOn] = useState(defaultReviewDate());
  const quickSignals = [report.continue_signals[0], report.continue_signals[1], report.pause_signals[0]].filter(Boolean);
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
        <p className="eyebrow">现在先看</p>
        <div className="hexagram-title"><strong>{result.base_hexagram.symbol}</strong><span>第 {result.base_hexagram.king_wen_number} 卦</span><h2>{result.base_hexagram.name}</h2></div>
        <p className="eyebrow conclusion-label">核心判断</p>
        <h3 id="result-title" tabIndex={-1}>{report.answer}</h3>
      </div>
      <aside className="result-aside">
        <span>眼下可做的一步</span><b>{report.priority}</b><p>{report.next_action}</p><a href="#result-signals">再看三个观察信号</a>
      </aside>
    </section>

    <section id="result-signals" className="quick-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">先带走最有用的部分</p><h2>先做一件事，再看三个迹象</h2><p>不用急着把整份解读都记住。先确定眼前准备做的事，再留意下面三个迹象；它们出现或没有出现，会帮助你判断接下来该继续、调整，还是停一停。</p></header>
      <div className="quick-signal-list">{quickSignals.map((signal, index) => <article key={signal}><span>{["壹", "贰", "叁"][index]}</span><p>{signal}</p></article>)}</div>
      <nav className="result-jump"><a href="#why-reading">为什么这样判断</a><a href="#deep-reading">深入了解排盘</a><a href="#save-current-reading">读完后保存这次观象</a></nav>
    </section>

    <section id="why-reading" className="reading-scroll layered-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第二层 · 为什么</p><h2>从卦象回到所问之事</h2><p>这一层说明判断依据。若你只需要行动方向，可以先跳过，等现实出现新证据后再回来对照。</p></header>
      <div className="detailed-conclusion">
        <span>回到你所问之事</span><h3>{report.what_it_means}</h3>
        <ol>{report.evidence_path.map((item) => <li key={item.title}><b>{item.title}</b><p>{item.text}</p></li>)}</ol>
      </div>
      {cultural ? <div className="canonical-grid">{cultural.hexagrams.map((item) => <article key={item.role} className="canonical-card">
        <header><span>{item.role}</span><strong>{item.symbol}</strong><div><small>第 {item.king_wen_number} 卦</small><h3>{item.name}</h3></div></header>
        <p className="reading-role">{item.reading_role}</p>
        <blockquote><b>《易》曰</b>{item.canonical_text}</blockquote>
        <p className="plain-note">{item.plain_note}</p>
      </article>)}</div> : <p className="compatibility-note">经典原文正在随排盘引擎同步，请稍后重新观卦。</p>}
    </section>

    <section id="deep-reading" className="evidence-scroll layered-reading scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">第三层 · 深入理解</p><h2>卦从何来，变化落在哪里</h2><p>这里我们为你保留完整的三数成卦、动爻、体用和旺衰解释。如果你对这些内容感兴趣，想进一步了解卦象是怎样一步步形成的，可以展开阅读。</p></header>
      <details className="reading-disclosure"><summary><span>三数如何成卦</span><small>第一数定上卦 · 第二数定下卦 · 第三数定动爻</small></summary>{cultural && <><div className="concept-explainer"><h3>先分清三个容易混在一起的概念</h3><p><b>上卦和下卦</b>都是由三条爻组成的“八经卦”，例如“离”。上下两个三爻卦叠在一起，才组成一个六爻的<b>本卦</b>，例如“离为火”。所以“离”与“离为火”不是同一个层级：前者是组成部分，后者是完整卦象。</p><p>本次上卦为<b>{upperPath?.result_name}</b>，下卦为<b>{lowerPath?.result_name}</b>，两者相叠得到本卦<b>{result.base_hexagram.name}</b>；第三个数字再确定其中哪一条爻发生变化。</p></div><div className="number-path">{cultural.number_path.map((item, index) => <article key={item.role}><span>{["壹", "贰", "叁"][index]}</span><b>{item.input_number}</b><i aria-hidden="true">→</i><strong>{item.role} · {item.result_name}</strong><small>{item.explanation}</small></article>)}</div></>}</details>
      <details className="reading-disclosure"><summary><span>本卦、互卦与变卦</span><small>眼下的局面 · 内部的发展 · 变化后的方向</small></summary><div className="concept-explainer"><h3>三个卦各自看什么</h3><p><b>本卦</b>看眼下最主要的局面；<b>互卦</b>从本卦中间四爻重新组合，帮助看事情内部怎样发展；<b>变卦</b>由动爻变化后形成，帮助看局面改变后会把重点带向哪里。</p></div><div className="hexagram-route">{[{ label: "本卦", value: result.base_hexagram, note: cultural?.hexagrams[0]?.reading_role }, { label: "互卦", value: result.mutual_hexagram, note: cultural?.hexagrams[1]?.reading_role }, { label: "变卦", value: result.changed_hexagram, note: cultural?.hexagrams[2]?.reading_role }].map(({ label, value, note }) => <article key={label}><span>{label}</span><strong>{value.symbol}</strong><h3>{value.name}</h3><small>第 {value.king_wen_number} 卦</small><p>{note}</p></article>)}</div></details>
      {cultural && <details className="reading-disclosure"><summary><span>本次动爻</span><small>{cultural.moving_line.line_name} · {cultural.moving_line.stage}</small></summary><article className="moving-line-reading"><header><span>什么是动爻</span><h3>{cultural.moving_line.line_name}</h3><p>一卦共有六条爻。动爻就是这次发生变化的那一条；它一变，本卦便随之成为变卦。</p></header><div className="moving-change"><section><span>变化之前</span><b>{result.base_hexagram.symbol} {result.base_hexagram.name}</b><p>这是没有发生本次变化前，事情眼下呈现的主要局面。</p></section><section><span>发生了什么</span><b>{cultural.moving_line.line_name}发生变化</b><p>变化落在“{cultural.moving_line.stage}”，说明这一处是本次最需要留意的转折。</p></section><section><span>变化之后</span><b>{result.changed_hexagram.symbol} {result.changed_hexagram.name}</b><p>这一爻改变后形成变卦，局面的重点也随之转向。</p></section></div><blockquote><b>爻辞原文</b>{cultural.moving_line.canonical_text}</blockquote><p className="moving-reality"><b>落到你所问的这件事上</b>{movingTerm?.current_effect}</p></article></details>}
      <details className="reading-disclosure"><summary><span>体用关系与旺衰</span><small>双方关系 · 变化方向 · 当前承接能力</small></summary><div className="term-grid">{cultural?.terms.map((term) => <article key={term.title}><span>{term.title}</span><h3>{term.current_value}</h3><p>{term.meaning}</p><strong>本次影响</strong><p>{term.current_effect}</p></article>)}</div></details>
      <p className="evidence-boundary">{report.boundary_note}</p>
    </section>

    <section className="final-guidance scroll-section" data-reveal>
      <VerticalBrand />
      <p className="final-question">你问的是：{question}</p>
      <header className="section-heading"><p className="eyebrow">看清之后，回到当下</p><h2>可借之力，与当慎之处</h2></header>
      <div className="guidance-columns"><article><span>当下有利</span><ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul></article><article><span>尤其注意</span><ul>{report.pause_signals.map((item) => <li key={item}>{item}</li>)}</ul></article></div>
      <div className="next-action"><span>眼下可做的一步</span><p>{report.next_action}</p></div>
      <section id="save-current-reading" className="save-current-reading"><p className="eyebrow">解读至此</p><h3>把这次所见留到以后再看</h3><p>到这里，这次卦象的解读就完成了。希望它已经帮你理清方向，也让你更清楚下一步准备怎么做。如果你想在事情有了进展后回来复盘，可以在下面写下准备采取的行动，并选择一个回看日期。</p><div className="save-observation">
        <label><span>我准备采取的行动</span><textarea aria-describedby="action-help" placeholder="请用自己的话写下：我接下来准备做什么、先观察什么，什么情况出现时会调整。" value={action} maxLength={500} onChange={(event) => setAction(event.target.value)} /></label>
        <label><span>我准备回来复盘的日期</span><input type="date" value={reviewOn} onChange={(event) => setReviewOn(event.target.value)} /></label>
        <button type="button" disabled={saving || saved || !action.trim()} onClick={() => onSave(action, reviewOn || null)}>{saved ? "已经存入观事簿" : saving ? "正在保存" : "存入观事簿"}</button>
        <small id="action-help">保存后，你可以在观事簿里重新打开本次卦象，记录后来实际发生了什么，并据此修正自己的判断。记录可以导出，也可以随时删除。</small>
      </div></section>
      <div className="result-actions"><button type="button" className="restart-button secondary" onClick={onEdit}>回到本题修改</button><button type="button" className="restart-button" onClick={onClear}>清空并再问一事</button></div>
      <blockquote className="classic-counsel"><p>{counsel.quote}</p><cite>{counsel.source}</cite></blockquote>
    </section>
  </section>;
}

function CastingLoader() {
  return <div className="casting" role="status"><BaguaMark /><p><b>正在观象</b><span>排定本卦 · 察看变化 · 整理方向</span></p></div>;
}

export function GuanxiangApp() {
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("");
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [stage, setStage] = useState("");
  const [uncertainty, setUncertainty] = useState("");
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [records, setRecords] = useState<JournalRecord[]>([]);
  const [journalLoading, setJournalLoading] = useState(true);
  const [journalMessage, setJournalMessage] = useState("");
  const [savingRecord, setSavingRecord] = useState(false);
  const [savedRecordId, setSavedRecordId] = useState<string | null>(null);
  const allowedGoals = useMemo(() => GOALS_BY_DOMAIN[domain] ?? [], [domain]);

  function useQuestionExample(example: typeof QUESTION_EXAMPLES[number]) {
    setQuestion(example.text);
    setDomain(example.domain);
    setGoal("");
  }

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { elements.forEach((item) => item.classList.add("is-visible")); return; }
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); } }), { threshold: .08, rootMargin: "0px 0px -3%" });
    elements.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, [response, records]);

  useEffect(() => {
    let cancelled = false;
    async function loadJournal() {
      try {
        const request = await fetch("/api/journal", { headers: journalHeaders(), cache: "no-store" });
        const payload = await request.json() as { records?: JournalRecord[]; error?: string };
        if (!request.ok) throw new Error(payload.error || "观事簿暂时无法打开。");
        if (!cancelled) setRecords(payload.records ?? []);
      } catch (caught) {
        if (!cancelled) setJournalMessage(caught instanceof Error ? caught.message : "观事簿暂时无法打开。");
      } finally { if (!cancelled) setJournalLoading(false); }
    }
    loadJournal();
    return () => { cancelled = true; };
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
    setQuestion(""); setDomain(""); setGoal(""); setHorizon(""); setStage(""); setUncertainty("");
    setNumbers(["", "", ""]); setAcknowledged(false); setResponse(null); setError(""); setSavedRecordId(null);
    window.setTimeout(() => document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  async function saveObservation(actionText: string, reviewOn: string | null) {
    if (!response?.deterministic_result) return;
    setSavingRecord(true); setJournalMessage("");
    const id = crypto.randomUUID();
    try {
      const request = await fetch("/api/journal", { method: "POST", headers: journalHeaders(), body: JSON.stringify({
        id, question: response.user_question ?? question.trim(), structured_intake: response.structured_intake ?? { question_domain: domain, decision_goal: goal, time_horizon: horizon, decision_stage: stage, key_uncertainty: uncertainty },
        numbers: response.deterministic_result.input_numbers, result: response.deterministic_result, action_text: actionText, review_on: reviewOn,
      }) });
      const payload = await request.json() as { record?: JournalRecord; error?: string };
      if (!request.ok || !payload.record) throw new Error(payload.error || "这次观象暂时没有保存成功。");
      setRecords((current) => [payload.record!, ...current]); setSavedRecordId(id); setJournalMessage("已经存入观事簿。等现实出现新证据后，再回来复盘。");
    } catch (caught) { setJournalMessage(caught instanceof Error ? caught.message : "这次观象暂时没有保存成功。"); }
    finally { setSavingRecord(false); }
  }

  async function updateObservation(id: string, draft: JournalDraft) {
    setJournalMessage("");
    try {
      const request = await fetch("/api/journal", { method: "PATCH", headers: journalHeaders(), body: JSON.stringify({ id, ...draft }) });
      const payload = await request.json() as { record?: JournalRecord; error?: string };
      if (!request.ok || !payload.record) throw new Error(payload.error || "复盘暂时没有保存成功。");
      setRecords((current) => current.map((record) => record.id === id ? payload.record! : record)); setJournalMessage("复盘已经保存。新的现实证据，已经回到这次判断之中。");
    } catch (caught) { setJournalMessage(caught instanceof Error ? caught.message : "复盘暂时没有保存成功。"); }
  }

  async function deleteObservation(id: string) {
    if (!window.confirm("这条观象与复盘将被永久删除，且无法恢复。确定删除吗？")) return;
    setJournalMessage("");
    try {
      const request = await fetch(`/api/journal?id=${encodeURIComponent(id)}`, { method: "DELETE", headers: journalHeaders() });
      const payload = await request.json() as { error?: string };
      if (!request.ok) throw new Error(payload.error || "暂时无法删除。");
      setRecords((current) => current.filter((record) => record.id !== id)); setJournalMessage("这条记录已经永久删除。");
    } catch (caught) { setJournalMessage(caught instanceof Error ? caught.message : "暂时无法删除。"); }
  }

  function openObservation(record: JournalRecord) {
    setQuestion(record.question); setDomain(record.structured_intake.question_domain); setGoal(record.structured_intake.decision_goal); setHorizon(record.structured_intake.time_horizon); setStage(record.structured_intake.decision_stage); setUncertainty(record.structured_intake.key_uncertainty); setNumbers(record.numbers.map(String)); setAcknowledged(true); setSavedRecordId(record.id);
    setResponse({ status: "SUCCESS", user_question: record.question, structured_intake: record.structured_intake, deterministic_result: record.result });
    window.setTimeout(() => document.getElementById("result")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  function exportJournal() {
    const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), product: "观象", records }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `观象-观事簿-${new Date().toISOString().slice(0, 10)}.json`; anchor.click(); URL.revokeObjectURL(url);
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResponse(null); setSavedRecordId(null);
    const parsed = numbers.map(Number);
    if (question.trim().length < 6 || question.trim().length > 160 || !domain || !goal || !horizon || !stage || !uncertainty || parsed.some((n, index) => !numbers[index] || !Number.isInteger(n) || n < 1 || n > 999) || !acknowledged) {
      setError("请写下具体问题，并完整选择当前处境、填写三个 1–999 的整数，再确认使用边界。"); return;
    }
    setLoading(true);
    try {
      const request = await fetch("/api/v3/meihua", {
        method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store",
        body: JSON.stringify({ contract_version: "SITES_MEIHUA_API_CONTRACT_V3", request_id: `sites-${crypto.randomUUID()}`, question_text: question.trim(), question_domain: domain, decision_goal: goal, time_horizon: horizon, decision_stage: stage, key_uncertainty: uncertainty, numbers: parsed, locale: "zh-CN", client_timestamp: new Date().toISOString(), user_acknowledgements: { deterministic_only: true, narrative_unverified: true, question_text_not_evidence: true } }),
      });
      const payload = await request.json() as ApiResponse;
      if (!request.ok || payload.status !== "SUCCESS" || !payload.deterministic_result?.clarity_report) throw new Error(payload.error || payload.errors?.[0]?.message || "本次未能生成结果，请稍后重试。");
      setResponse(payload);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "暂时无法连接排盘服务，请稍后再试。"); }
    finally { setLoading(false); }
  }

  return <>
    <header className="site-header">
      <a className="wordmark" href="#top">观象</a>
      <nav><a href="#method">如何观</a><a href="#inquiry">开始问</a><a href="#journal">观事簿</a></nav>
      <small>约三分钟 · 确定性排盘</small>
    </header>
    <main id="top" className="scroll-canvas">
      <section className="hero scroll-section" data-reveal>
        <VerticalBrand />
        <p className="hero-motto">心有所问，静观其象。</p>
        <div className="hero-copy">
          <p className="eyebrow">《周易·系辞上》</p>
          <h1>寂然不动，<br />感而遂通天下之故。</h1>
          <p className="hero-value">用三分钟，把一件拿不准的事理清方向，也看清下一步该留意什么。</p>
          <p>观象不替你决定，也不预先写好结果。它把卦象的结构、变化与现实中该观察的条件一层层展开，并让你在后来回来复盘。</p>
          <a className="seal-button" href="#method"><BaguaMark /><span>遇事不决，可问春风</span><img className="seal-dot" src="/bagua-seal.png" alt="" aria-hidden="true" /></a>
        </div>
      </section>

      <section id="method" className="method scroll-section" data-reveal>
        <VerticalBrand />
        <div className="method-quote"><p className="eyebrow">观象之法</p><h2>在天成象，<br />在地成形，变化见矣。</h2><cite>《周易·系辞上》</cite></div>
        <div className="method-explainer"><p>所谓观象的意思，就是观察身边的现象，由可见之形察其关系，由变化之中辨其趋向。它不是一句含混的预言，而是一条从所问、取数、成卦到现实验证的观察路径。</p>
          <ol><li><span>壹</span><b>正问</b><p>写下一件具体而真实的事。</p></li><li><span>贰</span><b>取数</b><p>凭当下所感，取三个整数。</p></li><li><span>叁</span><b>成卦</b><p>程序按照三数起卦的排盘规则，排定本卦、互卦与变卦。</p></li><li><span>肆</span><b>验事</b><p>把方向放回现实，以行动和反馈复核。</p></li></ol>
          <div className="input-roles"><h3>卦从数起，意随事明</h3><p><b>三个数字</b>用来起卦；你写下的<b>问题和现实处境</b>，帮助我们从卦象中找到与眼前这件事有关的重点，并整理出可以采取的应对方法。</p><a href="/about">查看完整方法与规则版本</a></div>
          <a className="method-cta" href="#inquiry">已明其法，开始正问</a>
        </div>
      </section>

      <section id="inquiry" className="inquiry scroll-section" data-reveal>
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <header className="inquiry-heading"><p className="eyebrow">正问</p><h2>一次只问一件具体的事</h2><p>不要把许多选择揉成一个大问题。所问越具体，越容易从卦象中看清眼前真正需要处理的部分。整个过程约三分钟，带星号的内容需要填写。</p></header>

          <section className="inquiry-step"><div className="step-heading"><span>壹</span><div><h3>写清所问</h3><p>尽量写清对象、当前选择和现实范围。</p></div></div>
            <label className="question-label"><span>你真正想问的问题 *</span><textarea aria-label="你真正想问的问题" placeholder="例如：这次合作，我还应该继续投入吗？" value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} /><small>{question.trim().length} / 160 · 请用清晰具体的文字说出你想弄明白的事，这会帮助我们把抽象的卦意落到现实处境中。</small></label>
            <div className="question-examples"><header><span>不知怎样开口，可以从这些问题开始</span><small>点击任意一句，会自动填入上方</small></header><div>{QUESTION_EXAMPLES.map((example) => <button type="button" key={example.text} onClick={() => useQuestionExample(example)}><span>{example.topic}</span><b>{example.text}</b></button>)}</div></div>
          </section>

          <section className="inquiry-step"><div className="step-heading"><span>贰</span><div><h3>说明现实处境</h3><p>告诉我们事情属于哪一类、走到哪一步、你最在意什么。这样解读时，卦象中的方向才能落到你真正关心的地方。</p></div></div>
            <div className="context-line"><ChoiceMenu label="事情属于 *" value={domain} options={DOMAINS} onChange={(value) => { setDomain(value); setGoal(""); }} /><ChoiceMenu label="这次最想看清 *" value={goal} options={Object.fromEntries(allowedGoals.map((key) => [key, GOALS[key]]))} disabled={!domain} onChange={setGoal} /><ChoiceMenu label="观察范围 *" value={horizon} options={HORIZONS} onChange={setHorizon} /></div>
            <div className="hanging-slips context-slips"><fieldset><legend>事情走到哪一步 *</legend><OptionList name="进程" value={stage} options={STAGES} onChange={setStage} /></fieldset><fieldset><legend>最需要确认的变量 *</legend><OptionList name="所忧" value={uncertainty} options={UNCERTAINTIES} onChange={setUncertainty} /></fieldset></div>
          </section>

          <section className="inquiry-step number-step"><div className="step-heading"><span>叁</span><div><h3>静心取数</h3><p>三个数字没有吉凶，也没有选对选错。凭当下所感，各写一个 1—999 的整数。</p></div></div>
            <fieldset className="numbers-slip"><legend className="sr-only">取三个整数</legend>{numbers.map((value, index) => <label key={index}><span>{["壹 · 上卦", "贰 · 下卦", "叁 · 动爻"][index]}</span><input aria-label={`第${index + 1}个数字`} placeholder="1—999" type="number" inputMode="numeric" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>)}</fieldset>
            <p className="number-note">第一数定上卦，第二数定下卦，第三数定动爻。程序随后依规则排定本卦、互卦与变卦。</p>
          </section>

          <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：卦象提供一种观察角度，文字帮助解读落到具体事情；重要决定仍要结合现实中的回应、资源与行动。</span></label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="cast-button" disabled={loading}><BaguaMark />{loading ? "正在观象" : "观卦"}</button>
          {loading && <CastingLoader />}
        </form>
      </section>

      {response && <ResultView response={response} onEdit={editQuestion} onClear={clearQuestion} onSave={saveObservation} saving={savingRecord} saved={savedRecordId !== null} />}
      <JournalSection records={records} loading={journalLoading} message={journalMessage} hasUnsavedResult={Boolean(response?.deterministic_result) && savedRecordId === null} onOpen={openObservation} onUpdate={updateObservation} onDelete={deleteObservation} onExport={exportJournal} onSaveCurrent={() => document.getElementById("save-current-reading")?.scrollIntoView({ behavior: "smooth", block: "start" })} />
      <aside className="version-note">卦象不是预先写好的判词，而是对当下结构的一次照见。所谓“穷则变，变则通”，心念与行动一变，后续条件也会随之改变。得顺势之象，不可因此停步；见阻力之象，也不必自弃。观象的意义，是让我们看见照旧前行可能抵达之处，从而及早准备、修正与行动。</aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span><nav><a href="/guide">如何使用</a><a href="/about">方法与边界</a><a href="/privacy">隐私说明</a></nav></footer>
  </>;
}
