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
type ProductResult = {
  base_hexagram: Hexagram;
  mutual_hexagram: Hexagram;
  changed_hexagram: Hexagram;
  moving_line: number;
  body_use: { body_trigram: string; initial_relation: string; changed_relation: string };
  seasonal_strength: { body: string; solar_term: string; month_branch: string };
  deterministic_conclusion: { conclusion_level: string };
  clarity_report: ClarityReport;
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
const RELATIONS: Record<string, string> = { USE_GENERATES_BODY: "用生体", BODY_CONTROLS_USE: "体克用", SAME_ELEMENT: "体用比和", BODY_GENERATES_USE: "体生用", USE_CONTROLS_BODY: "用克体" };
const STRENGTHS: Record<string, string> = { PROSPEROUS: "旺", SUPPORTED: "相", RESTING: "休", CONFINED: "囚", DEAD: "死" };
const LINE_NAMES = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"];

function VerticalBrand() {
  return <div className="vertical-brand" aria-label="观象"><b>观</b><b>象</b><i aria-hidden="true">观</i></div>;
}

function OptionList({ name, value, options, onChange }: { name: string; value: string; options: Record<string, string>; onChange: (value: string) => void }) {
  return <div className="option-list" role="radiogroup" aria-label={name}>{Object.entries(options).map(([key, label]) => (
    <label key={key} className={value === key ? "selected" : ""}>
      <input type="radio" name={name} value={key} checked={value === key} onChange={() => onChange(key)} />
      <span aria-hidden="true" />{label}
    </label>
  ))}</div>;
}

function HexagramNode({ label, value, moving }: { label: string; value: Hexagram; moving?: number }) {
  return <article className="hexagram-node">
    <div><p>{label}</p><h4>{value.name}</h4><small>第 {value.king_wen_number} 卦{moving ? ` · ${LINE_NAMES[moving - 1]}动` : ""}</small></div>
    <strong aria-label={`${value.name}卦象`}>{value.symbol}</strong>
  </article>;
}

function ResultView({ response, onRestart }: { response: ApiResponse; onRestart: () => void }) {
  const result = response.deterministic_result;
  if (!result) return null;
  const report = result.clarity_report;
  const question = response.user_question ?? "你所问之事";
  return <section id="result" className="result-shell" aria-labelledby="result-title">
    <section className="result-overview art-panel" data-reveal>
      <VerticalBrand />
      <div className="result-question">所问：{question}</div>
      <div className="result-answer">
        <p className="eyebrow">先说方向</p>
        <h2 id="result-title" tabIndex={-1}>{report.answer}</h2>
      </div>
      <aside className="result-aside">
        <section><h3>现实中看什么</h3><ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul></section>
        <section><h3>此刻做什么</h3><p>{report.next_action}</p></section>
        <a href="#clarity">继续往下看</a>
      </aside>
    </section>

    <section id="clarity" className="clarity-scroll art-panel" data-reveal>
      <VerticalBrand />
      <p className="clarity-question">你问的是：{question}</p>
      <h2>{report.answer}</h2>
      <div className="clarity-columns">
        <section>
          <h3>卦象给出的方向</h3>
          <p>{report.what_it_means}</p>
          <small>此刻最重要：{report.priority}</small>
        </section>
        <section>
          <h3>现实中要验证的事</h3>
          <ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      </div>
      <div className="action-line"><span>你的下一步</span><p>{report.next_action}</p></div>
      <details className="pause-line"><summary>什么情况下应该先停一停</summary><ul>{report.pause_signals.map((item) => <li key={item}>{item}</li>)}</ul></details>
      <p className="clarity-boundary">现实情况不是卦象证据，而是你做决定时必须核验的事实。</p>
    </section>

    <details className="evidence-scroll art-panel" data-reveal>
      <summary><span>卦象依据</span><small>展开查看为什么得到这个方向</small></summary>
      <div className="evidence-inner">
        <VerticalBrand />
        <header><h2>卦象依据</h2><p>为什么得到这个方向</p></header>
        <div className="evidence-route">
          <HexagramNode label="本卦" value={result.base_hexagram} moving={result.moving_line} />
          <HexagramNode label="互卦" value={result.mutual_hexagram} />
          <HexagramNode label="变卦" value={result.changed_hexagram} />
        </div>
        <aside className="evidence-facts">
          <div><span>动爻</span><b>{LINE_NAMES[result.moving_line - 1]}</b></div>
          <div><span>体用关系</span><b>{RELATIONS[result.body_use.initial_relation] ?? result.body_use.initial_relation}</b></div>
          <div><span>旺衰</span><b>{STRENGTHS[result.seasonal_strength.body] ?? result.seasonal_strength.body}</b></div>
        </aside>
        <ol className="evidence-notes">{report.evidence_path.map((item) => <li key={item.title}><h3>{item.title}</h3><p>{item.text}</p></li>)}</ol>
        <p className="evidence-boundary">{report.boundary_note}</p>
      </div>
    </details>

    <footer className="result-footer"><p>以象观机，以事验证。</p><button type="button" onClick={onRestart}>再问一事</button></footer>
  </section>;
}

function CastingLoader() {
  return <div className="casting" role="status"><div className="ink-ripples" aria-hidden="true"><i /><i /><i /></div><p><b>正在观象</b><span>排定本卦 · 察看变化 · 整理方向</span></p></div>;
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
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); } }), { threshold: .1, rootMargin: "0px 0px -4%" });
    elements.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
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
      window.setTimeout(() => { document.getElementById("result")?.scrollIntoView({ behavior: "smooth" }); document.getElementById("result-title")?.focus({ preventScroll: true }); }, 0);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "暂时无法连接排盘服务，请稍后再试。"); }
    finally { setLoading(false); }
  }

  return <>
    <header className="site-header">
      <a className="wordmark" href="#top">观象</a>
      <nav><a href="#method">如何观</a><a href="#inquiry">开始问</a></nav>
      <small>确定性排盘 · 私有体验</small>
    </header>
    <main id="top">
      <section className="hero art-panel" data-reveal>
        <VerticalBrand />
        <p className="hero-motto">心有所问，静观其象。</p>
        <div className="hero-copy">
          <p className="eyebrow">观乎天文，以察时变 · 观乎人文，以化成天下</p>
          <h1>把心里的疑问，<br />问得更清楚一点。</h1>
          <p>不急着预言结局。先把问题说清，再从确定性的卦象结构里，看方向、看变化，也看现实中该验证什么。</p>
          <a className="seal-button" href="#inquiry">开始问一件具体的事</a>
        </div>
      </section>

      <section id="method" className="method" data-reveal>
        <p className="eyebrow">观象之法</p>
        <h2>不问宿命，<br />只辨此刻的局势。</h2>
        <div><p>卦象给你变化结构，现实给你判断依据。</p><ol><li><span>一</span>写下真正所问</li><li><span>二</span>依规则完成排盘</li><li><span>三</span>用行动验证方向</li></ol></div>
      </section>

      <section id="inquiry" className="inquiry art-panel" data-reveal>
        <VerticalBrand />
        <form onSubmit={submit} noValidate>
          <header>
            <p className="eyebrow">所问</p>
            <textarea aria-label="你真正想问的问题" value={question} maxLength={160} onChange={(event) => setQuestion(event.target.value)} placeholder="这次合作，我还应该继续投入吗？" />
            <small>{question.trim().length} / 160 · 问题原文只用于理解与呈现，不参与排盘</small>
          </header>

          <div className="context-line">
            <label><span>事情属于</span><select aria-label="事情属于" value={domain} onChange={(event) => { setDomain(event.target.value); setGoal(""); }}><option value="">请选择</option>{Object.entries(DOMAINS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
            <label><span>最想看清</span><select aria-label="最想看清" value={goal} disabled={!domain} onChange={(event) => setGoal(event.target.value)}><option value="">请选择</option>{allowedGoals.map((key) => <option key={key} value={key}>{GOALS[key]}</option>)}</select></label>
            <label><span>观察范围</span><select aria-label="观察范围" value={horizon} onChange={(event) => setHorizon(event.target.value)}><option value="">请选择</option>{Object.entries(HORIZONS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          </div>

          <div className="hanging-slips">
            <fieldset><legend>进程</legend><OptionList name="进程" value={stage} options={STAGES} onChange={setStage} /></fieldset>
            <fieldset><legend>所忧</legend><OptionList name="所忧" value={uncertainty} options={UNCERTAINTIES} onChange={setUncertainty} /></fieldset>
            <fieldset className="numbers-slip"><legend>取数</legend>{numbers.map((value, index) => <label key={index}><span>{["一", "二", "三"][index]}</span><input aria-label={`第${index + 1}个数字`} type="number" inputMode="numeric" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} placeholder="—" /></label>)}</fieldset>
          </div>

          <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解：结果是思考参考，不是确定事实；问题原文不参与排盘，重要决定仍以现实反馈为准。</span></label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="cast-button" disabled={loading}>{loading ? "正在观象" : "观卦"}</button>
          {loading && <CastingLoader />}
        </form>
      </section>

      {response && <ResultView response={response} onRestart={restart} />}
      <aside className="version-note">观象当前不收费、不保存你的问题，也不把卦象包装成必然结论。解释来自版本化规则与结构化模板。</aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span></footer>
  </>;
}
