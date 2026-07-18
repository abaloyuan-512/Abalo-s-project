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
type ApiResponse = {
  status?: string;
  user_question?: string;
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
const STAGES = { EXPLORING: "还在了解，还没有行动", PREPARING: "正在准备第一次行动", ALREADY_ACTING: "已经投入或正在推进", WAITING_FEEDBACK: "已经行动，正在等反馈" } as const;
const UNCERTAINTIES = { CONDITIONS: "还缺哪些关键条件", OTHER_RESPONSE: "对方会不会有实际回应", OWN_COMMITMENT: "自己还该投入多少", TIMING: "现在是不是合适时机" } as const;
const RELATIONS: Record<string, string> = { USE_GENERATES_BODY: "用生体", BODY_CONTROLS_USE: "体克用", SAME_ELEMENT: "体用比和", BODY_GENERATES_USE: "体生用", USE_CONTROLS_BODY: "用克体" };
const STRENGTHS: Record<string, string> = { PROSPEROUS: "旺", SUPPORTED: "相", RESTING: "休", CONFINED: "囚", DEAD: "死" };

function Chapter({ number, title }: { number: string; title: string }) {
  return <div className="chapter"><span>{number}</span><b>{title}</b></div>;
}

function HexagramColumn({ label, value, moving }: { label: string; value: Hexagram; moving?: number }) {
  return (
    <article className="gua-column">
      <p>{label}</p>
      <strong aria-label={`${value.name}卦象`}>{value.symbol}</strong>
      <div><h4>{value.name}</h4><small>第 {value.king_wen_number} 卦{moving ? ` · ${moving}爻动` : ""}</small></div>
    </article>
  );
}

function ResultView({ response, onRestart }: { response: ApiResponse; onRestart: () => void }) {
  const result = response.deterministic_result;
  if (!result) return null;
  const report = result.clarity_report;
  return (
    <section id="result" className="result-page" aria-labelledby="result-title">
      <aside className="result-rail" aria-label="解读章节">
        <Chapter number="一" title="所问" /><Chapter number="二" title="观势" /><Chapter number="三" title="行动" />
      </aside>
      <div className="result-content">
        <header className="asked" data-reveal>
          <p className="section-kicker">你问</p>
          <h2 id="result-title" tabIndex={-1}>{response.user_question}</h2>
          <div className="answer-mark"><i aria-hidden="true" /><p>{report.answer}</p></div>
        </header>

        <section className="meaning" data-reveal>
          <Chapter number="一" title="先看结论" />
          <div className="meaning-grid">
            <div><p className="section-kicker">此刻最重要</p><h3>{report.priority}</h3></div>
            <p>{report.what_it_means}</p>
          </div>
        </section>

        <section className="signals" data-reveal>
          <Chapter number="二" title="再看现实信号" />
          <div className="signal-columns">
            <div><h3>出现这些，可以继续</h3><ul>{report.continue_signals.map((item) => <li key={item}>{item}</li>)}</ul></div>
            <div className="pause-signals"><h3>出现这些，应当暂停</h3><ul>{report.pause_signals.map((item) => <li key={item}>{item}</li>)}</ul></div>
          </div>
        </section>

        <section className="next-step" data-reveal>
          <Chapter number="三" title="最后只做一步" />
          <div className="next-line" aria-hidden="true" />
          <p>{report.next_action}</p>
          <small>先做可逆的小动作，让现实给你下一条信息。</small>
        </section>

        <section className="evidence" data-reveal>
          <header><p className="section-kicker">卦象依据</p><h3>为什么会得到这个方向</h3></header>
          <div className="gua-strip">
            <GuaFlow result={result} />
          </div>
          <ol>{report.evidence_path.map((item, index) => <li key={item.title}><span>{String(index + 1).padStart(2, "0")}</span><div><h4>{item.title}</h4><p>{item.text}</p></div></li>)}</ol>
        </section>

        <details className="technical">
          <summary>查看排盘技术信息</summary>
          <dl>
            <div><dt>动爻</dt><dd>第 {result.moving_line} 爻</dd></div>
            <div><dt>体卦</dt><dd>{result.body_use.body_trigram}</dd></div>
            <div><dt>起始关系</dt><dd>{RELATIONS[result.body_use.initial_relation] ?? result.body_use.initial_relation}</dd></div>
            <div><dt>变化关系</dt><dd>{RELATIONS[result.body_use.changed_relation] ?? result.body_use.changed_relation}</dd></div>
            <div><dt>体卦旺衰</dt><dd>{STRENGTHS[result.seasonal_strength.body] ?? result.seasonal_strength.body}</dd></div>
            <div><dt>节气 / 月支</dt><dd>{result.seasonal_strength.solar_term} / {result.seasonal_strength.month_branch}</dd></div>
          </dl>
        </details>
        <p className="boundary">{report.boundary_note}</p>
        <footer className="result-footer"><p>以象观机，以事验证。</p><button type="button" onClick={onRestart}>再问一事</button></footer>
      </div>
    </section>
  );
}

function GuaFlow({ result }: { result: ProductResult }) {
  return <><HexagramColumn label="本卦" value={result.base_hexagram} moving={result.moving_line} /><span className="flow-arrow" aria-hidden="true">→</span><HexagramColumn label="互卦" value={result.mutual_hexagram} /><span className="flow-arrow" aria-hidden="true">→</span><HexagramColumn label="变卦" value={result.changed_hexagram} /></>;
}

function CastingLoader() {
  return <div className="casting" role="status"><img src="/bagua-seal.png" width="58" height="58" alt="" /><div><b>正在观象</b><span>排定本卦 · 察看变化 · 整理方向</span></div></div>;
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
    const observer = new IntersectionObserver((entries) => entries.forEach((entry) => { if (entry.isIntersecting) { entry.target.classList.add("is-visible"); observer.unobserve(entry.target); } }), { threshold: .12, rootMargin: "0px 0px -5%" });
    elements.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, [response]);

  function restart() { setResponse(null); setError(""); window.setTimeout(() => document.getElementById("inquiry")?.scrollIntoView({ behavior: "smooth" }), 0); }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setResponse(null);
    const parsed = numbers.map(Number);
    if (question.trim().length < 6 || question.trim().length > 160 || !domain || !goal || !horizon || !stage || !uncertainty || parsed.some((n, i) => !numbers[i] || !Number.isInteger(n) || n < 1 || n > 999) || !acknowledged) {
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
    <header className="site-header"><a className="brand" href="#top"><img src="/bagua-seal.png" width="34" height="34" alt="" /><b>观象</b></a><nav><a href="#method">如何观</a><a href="#inquiry">开始问</a></nav><small>确定性排盘 · 私有体验</small></header>
    <main id="top">
      <section className="hero" data-reveal>
        <div className="hero-seal"><img src="/bagua-seal.png" width="96" height="96" alt="易经八卦印记" /></div>
        <div><p className="section-kicker">观乎天文，以察时变 · 观乎人文，以化成天下</p><h1>把心里的疑问，<br />问得更清楚一点。</h1><p>观象不替你预言结局。它把确定性排盘翻译成方向、信号与下一步，让你带着更清醒的判断回到现实。</p><a href="#inquiry">开始问一件具体的事<span>↓</span></a></div>
      </section>

      <section id="method" className="method" data-reveal><Chapter number="序" title="观象之法" /><div><h2>不急着问吉凶，<br />先辨清局势。</h2><p>一件事是否值得继续，往往不只取决于“好或不好”，还取决于条件是否具备、投入是否对等、现实有没有回应。观象先给方向，再给你可以验证的信号。</p></div><ol><li><span>一</span>写下真正所问</li><li><span>二</span>依规则完成排盘</li><li><span>三</span>带着信号回到现实</li></ol></section>

      <section id="inquiry" className="inquiry" data-reveal>
        <header><p className="section-kicker">起卦问询</p><h2>此刻，你真正想问什么？</h2><p>不要只在心里想。把问题明确写下来，结果才有一个清楚的落点。</p></header>
        <form onSubmit={submit} noValidate>
          <section className="form-section"><Chapter number="一" title="写下所问" /><label className="question-label"><span>用一句完整的话写下问题</span><textarea value={question} maxLength={160} onChange={(e) => setQuestion(e.target.value)} placeholder="例如：这次合作，我还应该继续投入吗？" /><small>{question.trim().length} / 160 · 问题原文只用于呈现，不参与排盘</small></label></section>
          <section className="form-section"><Chapter number="二" title="说明处境" /><div className="form-grid">
            <label><span>事情属于</span><select value={domain} onChange={(e) => { setDomain(e.target.value); setGoal(""); }}><option value="">请选择</option>{Object.entries(DOMAINS).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label><span>最想看清</span><select value={goal} disabled={!domain} onChange={(e) => setGoal(e.target.value)}><option value="">请选择</option>{allowedGoals.map((v) => <option key={v} value={v}>{GOALS[v]}</option>)}</select></label>
            <label><span>观察范围</span><select value={horizon} onChange={(e) => setHorizon(e.target.value)}><option value="">请选择</option>{Object.entries(HORIZONS).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label><span>现在处于</span><select value={stage} onChange={(e) => setStage(e.target.value)}><option value="">请选择</option>{Object.entries(STAGES).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label className="wide"><span>最不确定的是</span><select value={uncertainty} onChange={(e) => setUncertainty(e.target.value)}><option value="">请选择</option>{Object.entries(UNCERTAINTIES).map(([v,l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          </div></section>
          <section className="form-section"><Chapter number="三" title="写下三数" /><p className="number-intro">安静片刻，写下最先想到的三个 1–999 整数，不必计算。</p><div className="number-grid">{numbers.map((value,index) => <label key={index}><span>{["初数","中数","末数"][index]}</span><input type="number" inputMode="numeric" min="1" max="999" value={value} onChange={(e) => setNumbers(numbers.map((item,i) => i === index ? e.target.value : item))} placeholder="—" /></label>)}</div></section>
          <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /><span>我理解：结果来自固定规则，是思考参考而非确定事实；问题原文不参与排盘，重要决定仍以现实反馈为准。</span></label>
          {error && <p className="error" role="alert">{error}</p>}
          <button className="submit-button" disabled={loading}>{loading ? "正在观象，请稍候" : "查看方向与行动"}<span>→</span></button>
          {loading && <CastingLoader />}
        </form>
      </section>
      {response && <ResultView response={response} onRestart={restart} />}
      <aside className="version-note"><p>观象当前不收费、不保存你的问题，也不把卦象包装成必然结论。AI 个性化叙事尚未开放；本页解释来自已版本化规则与谨慎的结构化模板。</p></aside>
    </main>
    <footer className="site-footer"><b>观象</b><span>传统文化结构参考 · 以现实验证更新判断</span></footer>
  </>;
}
