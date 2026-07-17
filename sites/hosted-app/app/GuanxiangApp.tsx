"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Image from "next/image";

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
      <p>{label}</p>
      <strong aria-label={`${value.name}卦象`}>{value.symbol}</strong>
      <div>
        <h4>{value.name}</h4>
        <small>文王卦序 · 第 {value.king_wen_number} 卦</small>
      </div>
    </article>
  );
}

function ResultSection({ eyebrow, title, children, className = "" }: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`result-section ${className}`} data-reveal>
      <header>
        <p>{eyebrow}</p>
        <h3>{title}</h3>
      </header>
      {children}
    </section>
  );
}

function ResultView({ response, onRestart }: { response: ApiResponse; onRestart: () => void }) {
  const result = response.deterministic_result;
  if (!result) return null;
  const mentor = result.mentor_report;
  const conclusion = CONCLUSIONS[result.deterministic_conclusion.conclusion_level] ?? "证据不足";

  return (
    <section id="result" className="result-shell" aria-labelledby="result-title">
      <header className="result-heading" data-reveal>
        <p className="eyebrow">观象 · INSIGHT</p>
        <h2 id="result-title" tabIndex={-1}>{response.normalized_question}</h2>
        <div className="gold-thread" aria-hidden="true" />
      </header>

      <section className="insight-opening" aria-labelledby="insight-opening-title" data-reveal>
        <div>
          <p className="eyebrow">核心倾向 · ORIENTATION</p>
          <h3 id="insight-opening-title">{conclusion}</h3>
          <blockquote>“{mentor.opening}”</blockquote>
          <small>这是一份基于固定规则的结构化参考，不代表现实事件的必然结果。</small>
        </div>
        <div className="hexagram-flow" aria-label="本卦、互卦和变卦">
          <HexagramCard label="本卦 · BEN GUA" value={result.base_hexagram} />
          <HexagramCard label="互卦 · HU GUA" value={result.mutual_hexagram} />
          <HexagramCard label="变卦 · BIAN GUA" value={result.changed_hexagram} />
        </div>
      </section>

      <ResultSection eyebrow="智者式导读 · READING" title="先看清这组卦在说什么" className="reading-section">
        <div className="guide-grid">
          {mentor.reading_guide.map((item, index) => (
            <article className="guide-item" key={item.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><h4>{item.title}</h4><p>{item.text}</p></div>
            </article>
          ))}
        </div>
      </ResultSection>

      <ResultSection eyebrow="卦理溯源 · REASONING" title="为什么会得到这个判断" className="reasoning-section">
        <div className="reasoning-list">
          {mentor.reasoning.map((item) => (
            <article key={item.title}><h4>{item.title}</h4><p>{item.text}</p></article>
          ))}
        </div>
      </ResultSection>

      <ResultSection eyebrow="智行指南 · ACTION" title="接下来怎样做，为什么这样做" className="action-section">
        <ol className="action-list">
          {mentor.action_plan.map((item, index) => (
            <li key={item.title}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><h4>{item.title}</h4><p>{item.action}</p><small>为何如此：{item.why}</small></div>
            </li>
          ))}
        </ol>
      </ResultSection>

      <ResultSection eyebrow="行有所戒 · CAUTION" title="过程中留意这些信号" className="caution-section">
        <div className="caution-layout">
          <ul>{mentor.cautions.map((item) => <li key={item}>{item}</li>)}</ul>
          <div>
            <h4>给自己的复盘问题</h4>
            <ol>{mentor.review_questions.map((item) => <li key={item}>{item}</li>)}</ol>
          </div>
        </div>
        <p className="boundary">{mentor.boundary_note}</p>
      </ResultSection>

      <details className="technical">
        <summary>查看排盘结构详情</summary>
        <dl>
          <div><dt>动爻</dt><dd>第 {result.moving_line} 爻</dd></div>
          <div><dt>体卦</dt><dd>{result.body_use.body_trigram}</dd></div>
          <div><dt>初始体用</dt><dd>{RELATIONS[result.body_use.initial_relation] ?? result.body_use.initial_relation}</dd></div>
          <div><dt>变化体用</dt><dd>{RELATIONS[result.body_use.changed_relation] ?? result.body_use.changed_relation}</dd></div>
          <div><dt>体卦旺衰</dt><dd>{STRENGTHS[result.seasonal_strength.body] ?? result.seasonal_strength.body}</dd></div>
          <div><dt>节气 / 月支</dt><dd>{result.seasonal_strength.solar_term} / {result.seasonal_strength.month_branch}</dd></div>
        </dl>
      </details>

      <footer className="result-footer">
        <p>动而有节，守正观时。</p>
        <button type="button" onClick={onRestart}>重新起卦</button>
      </footer>
    </section>
  );
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

  useEffect(() => {
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-reveal]"));
    if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -6%" });

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [response]);

  function changeDomain(value: string) {
    setDomain(value);
    setGoal("");
    setNumbers(["", "", ""]);
    setResponse(null);
    setError("");
  }

  function restart() {
    setResponse(null);
    setError("");
    window.setTimeout(() => document.getElementById("question")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setResponse(null);
    const parsed = numbers.map(Number);
    if (!domain || !goal || !horizon || parsed.some((n, index) => !numbers[index] || !Number.isInteger(n) || n < 1 || n > 999) || !acknowledged) {
      setError("请完整选择问题范围、填写三个 1—999 的整数，并确认使用边界。");
      return;
    }
    setLoading(true);
    try {
      const request = await fetch("/api/v2/meihua", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          contract_version: "SITES_MEIHUA_API_CONTRACT_V2",
          request_id: `sites-${crypto.randomUUID()}`,
          question_domain: domain,
          decision_goal: goal,
          time_horizon: horizon,
          numbers: parsed,
          locale: "zh-CN",
          client_timestamp: new Date().toISOString(),
          user_acknowledgements: { deterministic_only: true, narrative_unverified: true, structured_question_confirmed: true },
        }),
      });
      const payload = await request.json() as ApiResponse;
      if (!request.ok || payload.status !== "SUCCESS" || !payload.deterministic_result?.mentor_report) {
        throw new Error(payload.error || "本次未能生成结果，请稍后重试。");
      }
      setResponse(payload);
      window.setTimeout(() => {
        document.getElementById("result")?.scrollIntoView({ behavior: "smooth" });
        document.getElementById("result-title")?.focus({ preventScroll: true });
      }, 0);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "暂时无法连接排盘服务，请稍后再试。";
      setError(message.includes("尚未连接")
        ? "你的填写没有问题。当前私有链接正在进行视觉验收，云端排盘尚未接通；视觉确认后，这里会呈现完整卦象与详细解读。"
        : message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="观象首页"><span>观</span><b>观象</b></a>
        <nav aria-label="页面导航"><a href="#about">关于</a><a href="#question">起卦</a></nav>
        <small>PRIVATE PREVIEW · 私有预览</small>
      </header>

      <main id="top">
        <section className="hero" data-reveal>
          <h1 className="sr-only">观象：在变化之中，看见清晰的方向</h1>
          <div className="hero-frame">
            <Image src="/og.png" width={1536} height={1024} priority alt="宋代水墨山水意境中的观象：在变化之中，看见清晰的方向。" />
          </div>
          <div className="hero-after">
            <div className="hero-copy">
              <p className="eyebrow">东方智慧 · 温和观照</p>
              <p>以确定性排盘呈现卦象结构，再像一位温和的智者，陪你理解原因、影响与可以落实的下一步。</p>
            </div>
            <a className="primary-action" href="#question">
              <Image src="/bagua-seal.png" width={42} height={42} alt="" aria-hidden="true" />
              <span>开始起卦</span>
            </a>
            <blockquote><span>“</span>不替你决定答案，只陪你看清局势。<span>”</span></blockquote>
          </div>
        </section>

        <section id="about" className="principle" data-reveal>
          <p className="eyebrow">观象之道 · METHOD</p>
          <div><h2>先看结构，<br />再回到现实。</h2><p>卦象不是对未来的承诺。我们把固定规则形成的结构，翻译成可以理解、核实和调整的现实参考：看见此刻的力量，也保留自己的判断。</p></div>
          <ol><li><span>一</span>明确关注的问题</li><li><span>二</span>完成确定性排盘</li><li><span>三</span>理解依据与行动</li></ol>
        </section>

        <section id="question" className="question-shell" data-reveal>
          <header>
            <p className="eyebrow">起卦问询 · INQUIRY</p>
            <h2>此刻，你想看清什么？</h2>
            <p>请在心中安静地想一遍你的问题，再依次完成以下选择。三个数字应来自你此刻自然想到的第一反应。</p>
          </header>

          <form onSubmit={submit} className="question-form" noValidate>
            <p className="preview-note"><strong>当前为视觉验收版</strong><span>可以完整填写并体验交互；云端排盘接通后，此处会生成正式解读。</span></p>
            <div className="form-step">
              <span>01</span>
              <div><h3>确定问题边界</h3><p>范围越清楚，结果越容易回到现实中理解。</p></div>
            </div>
            <div className="form-grid">
              <label><span>关注领域</span><select value={domain} onChange={(event) => changeDomain(event.target.value)}><option value="">请选择领域</option>{Object.entries(DOMAINS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              <label><span>希望看清</span><select value={goal} disabled={!domain} onChange={(event) => { setGoal(event.target.value); setNumbers(["", "", ""]); }}><option value="">{domain ? "请选择目标" : "请先选择领域"}</option>{allowedGoals.map((value) => <option key={value} value={value}>{GOALS[value]}</option>)}</select></label>
              <label><span>观察时间</span><select value={horizon} onChange={(event) => setHorizon(event.target.value)}><option value="">请选择时间</option>{Object.entries(HORIZONS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            </div>

            <div className="form-step number-step">
              <span>02</span>
              <div><h3>写下三个数字</h3><p>每个数字为 1—999 的整数，不需要计算或刻意挑选。</p></div>
            </div>
            <fieldset>
              <legend className="sr-only">三个起卦数字</legend>
              <div className="number-grid">
                {numbers.map((value, index) => (
                  <label key={index}>
                    <span>数字{["一", "二", "三"][index]}</span>
                    <input aria-label={`数字${["一", "二", "三"][index]}`} inputMode="numeric" type="number" min="1" max="999" value={value} onChange={(event) => setNumbers(numbers.map((item, itemIndex) => itemIndex === index ? event.target.value : item))} placeholder="—" />
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /><span>我理解结果来自固定规则，是思考参考而非确定事实；重要决定仍以现实反馈为准。</span></label>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="submit-button" disabled={loading}><span>{loading ? "正在观象" : "查看卦象与建议"}</span><small>{loading ? "请稍候片刻" : "DECODE THE MOMENT"}</small></button>
          </form>
        </section>

        {response && <ResultView response={response} onRestart={restart} />}

        <aside className="version-note" data-reveal>
          <p className="eyebrow">当前版本 · BOUNDARY</p>
          <h2>清晰，也有边界。</h2>
          <p>当前版本提供确定性排盘、规则型智者导读与现实行动建议；不保存你的输入，不收费，也不把卦象包装成必然结论。</p>
        </aside>
      </main>

      <footer className="site-footer"><span>观象 · 私有产品预览</span><span>传统文化结构参考 · 重要决定请结合现实信息</span></footer>
    </>
  );
}
