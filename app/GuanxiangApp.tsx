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

function VerticalBrand() {
  return <div className="vertical-brand" aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>;
}

function BaguaMark({ className = "", decorative = true }: { className?: string; decorative?: boolean }) {
  return <img
    className={`bagua-mark ${className}`}
    src="/fuxi-bagua-taiji.png"
    alt={decorative ? "" : "伏羲先天八卦图"}
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

function ResultView({ response, onRestart }: { response: ApiResponse; onRestart: () => void }) {
  const result = response.deterministic_result;
  if (!result) return null;
  const report = result.clarity_report;
  const cultural = result.cultural_reading;
  const question = response.user_question ?? "你所问之事";
  return <section id="result" className="result-shell" aria-labelledby="result-title">
    <section className="result-overview scroll-section" data-reveal>
      <VerticalBrand />
      <p className="result-question">所问：{question}</p>
      <div className="result-verdict">
        <p className="eyebrow">卦象是</p>
        <div className="hexagram-title"><strong>{result.base_hexagram.symbol}</strong><span>第 {result.base_hexagram.king_wen_number} 卦</span><h2>{result.base_hexagram.name}</h2></div>
        <p className="eyebrow conclusion-label">结论是</p>
        <h3 id="result-title" tabIndex={-1}>{report.answer}</h3>
      </div>
      <aside className="result-aside">
        <span>此刻最重要</span><b>{report.priority}</b><p>{report.next_action}</p><a href="#reading">细看卦从何来</a>
      </aside>
    </section>

    <section id="reading" className="reading-scroll scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">数有所指，卦有所成</p><h2>三数如何成卦</h2><p>第一数定上卦，第二数定下卦，第三数定动爻。上下相合成本卦，中爻相参成互卦，动爻变化成变卦。</p></header>
      {cultural ? <>
        <div className="number-path">{cultural.number_path.map((item, index) => <article key={item.role}>
          <span>{["壹", "贰", "叁"][index]}</span><b>{item.input_number}</b><i aria-hidden="true">→</i><strong>{item.role} · {item.result_name}</strong><small>{item.explanation}</small>
        </article>)}</div>
        <div className="canonical-grid">{cultural.hexagrams.map((item) => <article key={item.role} className="canonical-card">
          <header><span>{item.role}</span><strong>{item.symbol}</strong><div><small>第 {item.king_wen_number} 卦</small><h3>{item.name}</h3></div></header>
          <p className="reading-role">{item.reading_role}</p>
          <blockquote><b>《易》曰</b>{item.canonical_text}</blockquote>
          <small className="source">{item.source_name} · <a href={item.source_reference} target="_blank" rel="noreferrer">查看底本</a></small>
        </article>)}</div>
        <article className="moving-line-reading">
          <div><span>本次动爻</span><h3>{cultural.moving_line.line_name}</h3><small>{cultural.moving_line.stage}</small></div>
          <blockquote>{cultural.moving_line.canonical_text}</blockquote>
          <p>这条爻辞是本次变化最直接的经典依据；它与本卦、体用和旺衰共同构成判断，不单独等同于现实结论。</p>
        </article>
        {cultural.knowledge_notice && <p className="knowledge-notice">校勘说明：{cultural.knowledge_notice}</p>}
      </> : <p className="compatibility-note">经典原文正在随排盘引擎同步，请稍后重新观卦。</p>}
      <div className="detailed-conclusion">
        <span>回到你所问之事</span><h3>{report.what_it_means}</h3>
        <ol>{report.evidence_path.map((item) => <li key={item.title}><b>{item.title}</b><p>{item.text}</p></li>)}</ol>
      </div>
    </section>

    <section className="evidence-scroll scroll-section" data-reveal>
      <VerticalBrand />
      <header className="section-heading"><p className="eyebrow">读懂卦象，不只看见符号</p><h2>动爻、体用与旺衰</h2><p>下面分别说明这些词是什么意思，以及它们在本次排盘中如何影响判断。</p></header>
      <div className="hexagram-route">
        {[{ label: "本卦", value: result.base_hexagram }, { label: "互卦", value: result.mutual_hexagram }, { label: "变卦", value: result.changed_hexagram }].map(({ label, value }) => <article key={label}><span>{label}</span><strong>{value.symbol}</strong><h3>{value.name}</h3><small>第 {value.king_wen_number} 卦</small></article>)}
      </div>
      <div className="term-grid">{cultural?.terms.map((term) => <article key={term.title}><span>{term.title}</span><h3>{term.current_value}</h3><p>{term.meaning}</p><strong>本次影响</strong><p>{term.current_effect}</p></article>)}</div>
      <p className="evidence-boundary">{report.boundary_note}</p>
    </section>

    <section className="final-guidance scroll-section" data-reveal>
      <VerticalBrand />
      <p className="final-question">你问的是：{question}</p>
      <header className="section-heading"><p className="eyebrow">看清之后，回到当下</p><h2>可借之力，与当慎之处</h2></header>
      <div className="guidance-columns">
        <article><span>当下有利</span><ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul></article>
        <article><span>尤其注意</span><ul>{report.pause_signals.map((item) => <li key={item}>{item}</li>)}</ul></article>
      </div>
      <div className="next-action"><span>眼下可做的一步</span><p>{report.next_action}</p></div>
      {cultural && <blockquote className="classic-counsel"><p>{cultural.classic_counsel.quote}</p><cite>{cultural.classic_counsel.source}</cite></blockquote>}
      <button type="button" className="restart-button" onClick={onRestart}>再问一事</button>
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
  const allowedGoals = useMemo(() => GOALS_BY_DOMAIN[domain] ?? [], [domain]);

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) { elements.forEach((item) => item.classList.add("is-visible")); return; }
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); } }), { threshold: .08, rootMargin: "0px 0px -3%" });
    elements.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, [response]);

  useEffect(() => {
    if (!response) return;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" });
      document.getElementById("result-title")?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [response]);

  function restart() {
    setResponse(null); setError("");
    window.setTimeout(() => document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResponse(null);
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
      <nav><a href="#method">如何观</a><a href="#inquiry">开始问</a></nav>
      <small>确定性排盘 · 私有体验</small>
    </header>
    <main id="top" className="scroll-canvas">
      <section className="hero scroll-section" data-reveal>
        <VerticalBrand />
        <p className="hero-motto">心有所问，静观其象。</p>
        <div className="hero-copy">
          <p className="eyebrow">《周易·系辞上》</p>
          <h1>寂然不动，<br />感而遂通天下之故。</h1>
          <p>先让心绪静下来，再把真正想问的事写清楚。观象不替你决定，而是把卦象的结构、变化与现实中该验证的方向，一层层展开。</p>
          <a className="seal-button" href="#inquiry"><BaguaMark /><span>遇事不决，可问春风</span></a>
        </div>
      </section>

      <section id="method" className="method scroll-section" data-reveal>
        <VerticalBrand />
        <div className="method-quote"><p className="eyebrow">观象之法</p><h2>在天成象，<br />在地成形，变化见矣。</h2><cite>《周易·系辞上》</cite></div>
        <div className="method-explainer"><h3>何为观象</h3><p>观象，是由可见之形察其关系，由变化之中辨其趋向。它不是一句含混的预言，而是一条从所问、取数、成卦到现实验证的观察路径。</p>
          <ol><li><span>壹</span><b>正问</b><p>写下一件具体而真实的事。</p></li><li><span>贰</span><b>取数</b><p>凭当下所感，取三个整数。</p></li><li><span>叁</span><b>成卦</b><p>程序依冻结规则排定本、互、变卦。</p></li><li><span>肆</span><b>验事</b><p>把方向放回现实，以行动和反馈复核。</p></li></ol>
        </div>
      </section>

      <section id="inquiry" className="inquiry scroll-section" data-reveal>
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <header>
            <p className="eyebrow">所问</p>
            <textarea aria-label="你真正想问的问题" value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} />
            <small>{question.trim().length} / 160 · 问题原文只用于理解与呈现，不参与排盘</small>
          </header>

          <div className="context-line">
            <ChoiceMenu label="事情属于" value={domain} options={DOMAINS} onChange={(value) => { setDomain(value); setGoal(""); }} />
            <ChoiceMenu label="最想看清" value={goal} options={Object.fromEntries(allowedGoals.map((key) => [key, GOALS[key]]))} disabled={!domain} onChange={setGoal} />
            <ChoiceMenu label="观察范围" value={horizon} options={HORIZONS} onChange={setHorizon} />
          </div>

          <div className="hanging-slips">
            <fieldset><legend>进程</legend><OptionList name="进程" value={stage} options={STAGES} onChange={setStage} /></fieldset>
            <fieldset><legend>所忧</legend><OptionList name="所忧" value={uncertainty} options={UNCERTAINTIES} onChange={setUncertainty} /></fieldset>
            <fieldset className="numbers-slip"><legend>取数</legend>{numbers.map((value, index) => <label key={index}><span>{["壹", "贰", "叁"][index]}</span><input aria-label={`第${index + 1}个数字`} type="number" inputMode="numeric" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} /></label>)}</fieldset>
          </div>

          <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：结果是思考参考，不是确定事实；问题原文不参与排盘，重要决定仍以现实反馈为准。</span></label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="cast-button" disabled={loading}><BaguaMark />{loading ? "正在观象" : "观卦"}</button>
          {loading && <CastingLoader />}
        </form>
      </section>

      {response && <ResultView response={response} onRestart={restart} />}
      <aside className="version-note">观象当前不收费、不保存你的问题，也不把卦象包装成必然结论。解释来自版本化规则、经典原文与结构化模板。</aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span><a href="https://commons.wikimedia.org/wiki/File:Bagua-x2di.svg">先天八卦图来源</a></footer>
  </>;
}
