"use client";

import { FormEvent, useMemo, useState } from "react";

type TextItem = { title: string; text: string };
type ActionItem = { title: string; action: string; why: string };
type MentorReport = {
  opening: string;
  reading_guide: TextItem[];
  reasoning: TextItem[];
  action_plan: ActionItem[];
  cautions: string[];
  review_questions: string[];
  boundary_note: string;
};
type Hexagram = { king_wen_number: number; name: string; symbol: string };
type ProductResult = {
  base_hexagram: Hexagram;
  mutual_hexagram: Hexagram;
  changed_hexagram: Hexagram;
  moving_line: number;
  body_use: {
    body_trigram: string;
    initial_use_trigram: string;
    changed_use_trigram: string;
    initial_relation: string;
    changed_relation: string;
  };
  seasonal_strength: {
    body: string;
    initial_use: string;
    changed_use: string;
    solar_term: string;
    month_branch: string;
  };
  deterministic_conclusion: { conclusion_level: string };
  mentor_report: MentorReport;
};
type ApiResponse = {
  status?: string;
  normalized_question?: string;
  deterministic_result?: ProductResult | null;
  error?: string;
};

const DOMAINS = {
  WORK_CAREER: "工作与职业发展",
  PROJECT_COOPERATION: "项目与合作推进",
  RELATIONSHIP_COMMUNICATION: "关系与沟通",
  PERSONAL_PLANNING: "个人规划",
} as const;

const GOALS = {
  IDENTIFY_OBSTACLES: "识别阻力与支持",
  PLAN_NEXT_STEP: "规划下一步行动",
  PREPARE_COMMUNICATION: "准备现实沟通",
  ADJUST_COMMITMENT_BOUNDARIES: "调整投入与边界",
  OBSERVE_VERIFY_SIGNALS: "观察并核实现实信号",
} as const;

const GOALS_BY_DOMAIN: Record<string, (keyof typeof GOALS)[]> = {
  WORK_CAREER: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "OBSERVE_VERIFY_SIGNALS"],
  PROJECT_COOPERATION: Object.keys(GOALS) as (keyof typeof GOALS)[],
  RELATIONSHIP_COMMUNICATION: ["PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  PERSONAL_PLANNING: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
};

const HORIZONS = {
  CURRENT: "当前阶段",
  NEXT_30_DAYS: "未来30天",
  NEXT_QUARTER: "未来一个季度",
  NEXT_6_MONTHS: "未来6个月",
} as const;

const CONCLUSIONS: Record<string, string> = {
  CLEARLY_FAVORABLE: "明显有利",
  CONDITIONALLY_FAVORABLE: "有条件有利",
  MIXED_OR_UNSETTLED: "交错未定",
  CLEARLY_UNFAVORABLE: "阻力较强",
  INSUFFICIENT_EVIDENCE: "证据不足",
};

const RELATIONS: Record<string, string> = {
  USE_GENERATES_BODY: "用生体",
  BODY_CONTROLS_USE: "体克用",
  SAME_ELEMENT: "体用比和",
  BODY_GENERATES_USE: "体生用",
  USE_CONTROLS_BODY: "用克体",
};

const STRENGTHS: Record<string, string> = {
  PROSPEROUS: "旺",
  SUPPORTED: "相",
  RESTING: "休",
  CONFINED: "囚",
  DEAD: "死",
};

function HexagramCard({ label, value }: { label: string; value: Hexagram }) {
  return (
    <article className="hexagram-card">
      <span>{label}</span><strong>{value.symbol}</strong><h4>{value.name}</h4>
      <small>文王卦序 · 第 {value.king_wen_number} 卦</small>
    </article>
  );
}

function ResultView({ response }: { response: ApiResponse }) {
  const result = response.deterministic_result;
  if (!result) return null;
  const mentor = result.mentor_report;
  const conclusion = CONCLUSIONS[result.deterministic_conclusion.conclusion_level] ?? "证据不足";
  return (
    <section className="result-shell" aria-labelledby="result-title">
      <header className="result-heading">
        <div><p className="eyebrow">02 / 结果</p><h2 id="result-title">本次卦象与行动建议</h2></div>
        <p>{response.normalized_question}</p>
      </header>
      <section className="tendency"><span>核心倾向</span><h3>{conclusion}</h3><p>{mentor.opening}</p><small>这是结构化参考，不代表事件必然结果。</small></section>

      <ResultSection eyebrow="导师式导读" title="先知道这组卦该怎么看">
        <div className="guide-grid">{mentor.reading_guide.map((item) => <TextCard key={item.title} item={item} />)}</div>
      </ResultSection>
      <ResultSection eyebrow="判断依据" title="为什么会得到这个倾向">
        <div className="text-list">{mentor.reasoning.map((item) => <TextCard key={item.title} item={item} />)}</div>
      </ResultSection>
      <ResultSection eyebrow="现实行动" title="接下来可以怎样做">
        <ol className="action-list">{mentor.action_plan.map((item) => <li key={item.title}><h4>{item.title}</h4><p>{item.action}</p><small>为什么：{item.why}</small></li>)}</ol>
      </ResultSection>
      <ResultSection eyebrow="使用提醒" title="怎样做会更稳妥">
        <ul className="bullet-list">{mentor.cautions.map((item) => <li key={item}>{item}</li>)}</ul>
        <h4 className="review-title">给自己的复盘问题</h4>
        <ul className="review-list">{mentor.review_questions.map((item) => <li key={item}>{item}</li>)}</ul>
        <p className="boundary">{mentor.boundary_note}</p>
      </ResultSection>
      <ResultSection eyebrow="三卦结构" title="结构如何展开">
        <div className="hexagram-grid">
          <HexagramCard label="本卦" value={result.base_hexagram} />
          <HexagramCard label="互卦" value={result.mutual_hexagram} />
          <HexagramCard label="变卦" value={result.changed_hexagram} />
        </div>
      </ResultSection>
      <details className="technical">
        <summary>查看结构详情</summary>
        <dl>
          <div><dt>动爻</dt><dd>第 {result.moving_line} 爻</dd></div>
          <div><dt>体卦</dt><dd>{result.body_use.body_trigram}</dd></div>
          <div><dt>初始体用</dt><dd>{RELATIONS[result.body_use.initial_relation] ?? result.body_use.initial_relation}</dd></div>
          <div><dt>变化体用</dt><dd>{RELATIONS[result.body_use.changed_relation] ?? result.body_use.changed_relation}</dd></div>
          <div><dt>旺衰</dt><dd>体：{STRENGTHS[result.seasonal_strength.body] ?? result.seasonal_strength.body}</dd></div>
          <div><dt>节气 / 月支</dt><dd>{result.seasonal_strength.solar_term} / {result.seasonal_strength.month_branch}</dd></div>
        </dl>
      </details>
    </section>
  );
}

function ResultSection({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return <section className="result-section"><header><p>{eyebrow}</p><h3>{title}</h3></header>{children}</section>;
}

function TextCard({ item }: { item: TextItem }) {
  return <article className="text-card"><h4>{item.title}</h4><p>{item.text}</p></article>;
}

export function GuanxiangApp() {
  const [domain, setDomain] = useState("");
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState("");
  const [numbers, setNumbers] = useState(["", "", ""]);
  const [acknowledged, setAcknowledged] = useState(false);
  const [response, setResponse] = useState<ApiResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const allowedGoals = useMemo(() => GOALS_BY_DOMAIN[domain] ?? [], [domain]);

  function changeDomain(value: string) {
    setDomain(value); setGoal(""); setNumbers(["", "", ""]); setResponse(null); setError("");
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setResponse(null);
    const parsed = numbers.map(Number);
    if (!domain || !goal || !horizon || parsed.some((n, index) => !numbers[index] || !Number.isInteger(n) || n < 1 || n > 999) || !acknowledged) {
      setError("请完整选择问题范围、填写三个 1—999 的整数，并确认使用边界。"); return;
    }
    setLoading(true);
    try {
      const request = await fetch("/api/v2/meihua", {
        method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store",
        body: JSON.stringify({
          contract_version: "SITES_MEIHUA_API_CONTRACT_V2",
          request_id: `sites-${crypto.randomUUID()}`,
          question_domain: domain, decision_goal: goal, time_horizon: horizon,
          numbers: parsed, locale: "zh-CN", client_timestamp: new Date().toISOString(),
          user_acknowledgements: { deterministic_only: true, narrative_unverified: true, structured_question_confirmed: true },
        }),
      });
      const payload = await request.json() as ApiResponse;
      if (!request.ok || payload.status !== "SUCCESS" || !payload.deterministic_result?.mentor_report) {
        throw new Error(payload.error || "本次未能生成结果，请稍后重试。");
      }
      setResponse(payload);
      window.setTimeout(() => document.getElementById("result-title")?.focus(), 0);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "暂时无法连接排盘服务，请稍后再试。");
    } finally { setLoading(false); }
  }

  return (
    <>
      <header className="site-header"><a className="brand" href="#top"><span>观</span>观象</a><small>私有预览</small></header>
      <main id="top">
        <section className="hero"><p className="eyebrow">传统文化 · 决策辅助</p><h1>把纷杂的问题，<br />放回清晰的结构里。</h1><p>选择关注领域、目标与时间范围，再输入三个当下想到的数字。系统会呈现卦象，并带你理解判断依据、现实影响和下一步行动。</p><a href="#question">开始起卦 ↓</a></section>
        <section className="value"><p className="eyebrow">如何使用</p><div><h2>先理解，再行动</h2><p>观象不替你作决定，也不宣称预知未来。它把固定规则形成的结构翻译成一份温和、可核实、可调整的行动参考。</p></div></section>
        <section id="question" className="question-shell">
          <header><p className="eyebrow">01 / 提问</p><h2>此刻，你想关注什么？</h2></header>
          <form onSubmit={submit} className="question-form">
            <label><span>关注领域</span><select value={domain} onChange={(e) => changeDomain(e.target.value)}><option value="">请选择领域</option>{Object.entries(DOMAINS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label><span>决策目标</span><select value={goal} disabled={!domain} onChange={(e) => { setGoal(e.target.value); setNumbers(["", "", ""]); }}><option value="">{domain ? "请选择目标" : "请先选择领域"}</option>{allowedGoals.map((value) => <option key={value} value={value}>{GOALS[value]}</option>)}</select></label>
            <label><span>时间窗口</span><select value={horizon} onChange={(e) => setHorizon(e.target.value)}><option value="">请选择时间</option>{Object.entries(HORIZONS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <fieldset><legend>三个数字 <small>每个数字为 1—999 的整数</small></legend><div className="number-grid">{numbers.map((value, index) => <label key={index}><span>数字{["一", "二", "三"][index]}</span><input aria-label={`数字${["一", "二", "三"][index]}`} type="number" min="1" max="999" value={value} onChange={(e) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? e.target.value : item))} /></label>)}</div></fieldset>
            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /><span>我理解结果来自固定规则，是思考参考而非确定事实；重要决定仍以现实反馈为准。</span></label>
            {error && <p className="error" role="alert">{error}</p>}
            <button disabled={loading}>{loading ? "正在生成…" : "查看卦象与建议 →"}</button>
          </form>
        </section>
        {response && <ResultView response={response} />}
        <aside className="version-note"><div><p className="eyebrow">当前版本</p><h2>边界清晰的私有预览</h2></div><p>提供确定性排盘、规则型导师导读与现实行动建议；暂不保存输入、不收费，也不提供个性化 AI 深度解读。</p></aside>
      </main>
      <footer>观象 · 私有产品预览 <span>仅作传统文化结构参考</span></footer>
    </>
  );
}
