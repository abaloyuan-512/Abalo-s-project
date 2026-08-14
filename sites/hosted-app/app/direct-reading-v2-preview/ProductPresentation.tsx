import SafeDirectReadingMarkdown from "./SafeDirectReadingMarkdown";

type SourceSection = {
  heading: string;
  markdown: string;
  start_offset: number;
  end_offset: number;
  sha256: string;
};

type HexagramScene = {
  program_fact: {
    role: "BASE" | "MUTUAL" | "CHANGED";
    king_wen_number: number;
    name: string;
    upper_trigram: string;
    lower_trigram: string;
  };
  model_section: SourceSection;
};

type MovingScene = {
  program_fact: {
    position: number;
    name: string;
    canonical_line_text: string;
  };
  model_section: SourceSection;
};

export type ProductPresentation = {
  contract_version: "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1";
  source_reading_sha256: string;
  reconstructed_reading_sha256: string;
  reconstructed_equals_source: true;
  page8: {
    responsibility: "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH";
    base_hexagram: HexagramScene;
    mutual_hexagram: HexagramScene;
    moving_line: MovingScene;
    changed_hexagram: HexagramScene;
    program_strength: {
      source: "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH";
      body_trigram: string;
      initial_use_trigram: string;
      changed_use_trigram: string;
      initial_relation: string;
      changed_relation: string;
      body_strength: string;
    };
  };
  page9: {
    responsibility: "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS";
    judgment: SourceSection;
    suitable_actions: SourceSection;
    unsuitable_actions: SourceSection;
    reverse_risk: SourceSection;
    change_signals: SourceSection;
  };
};

function HexagramCard({ label, scene }: { label: string; scene: HexagramScene }) {
  return (
    <article className="productScene">
      <header>
        <span>{label} · 程序盘面</span>
        <strong>{scene.program_fact.name}</strong>
        <small>第 {scene.program_fact.king_wen_number} 卦 · 上{scene.program_fact.upper_trigram}下{scene.program_fact.lower_trigram}</small>
      </header>
      <SafeDirectReadingMarkdown source={scene.model_section.markdown} />
    </article>
  );
}

export default function ProductPresentationView({ presentation }: { presentation: ProductPresentation }) {
  const { page8, page9 } = presentation;
  return (
    <>
      <section className="productPage" aria-labelledby="p8-title">
        <p className="eyebrow">P8 · 读卦五幕</p>
        <h2 id="p8-title">卦盘结构与四层解读</h2>
        <p className="productBoundary">四层解读逐字来自本次九章正文；第五幕只呈现同一次程序排盘的体用与旺衰，不承载建议或现实判断。</p>
        <div className="productScenes">
          <HexagramCard label="本卦" scene={page8.base_hexagram} />
          <HexagramCard label="互卦" scene={page8.mutual_hexagram} />
          <article className="productScene">
            <header>
              <span>动爻 · 程序盘面</span>
              <strong>{page8.moving_line.program_fact.name}</strong>
              <small>第 {page8.moving_line.program_fact.position} 爻 · {page8.moving_line.program_fact.canonical_line_text}</small>
            </header>
            <SafeDirectReadingMarkdown source={page8.moving_line.model_section.markdown} />
          </article>
          <HexagramCard label="变卦" scene={page8.changed_hexagram} />
          <article className="productScene programOnly">
            <header>
              <span>旺衰 · 仅程序事实</span>
              <strong>体卦 {page8.program_strength.body_trigram}</strong>
              <small>{page8.program_strength.source}</small>
            </header>
            <dl className="strengthGrid">
              <div><dt>初始用卦</dt><dd>{page8.program_strength.initial_use_trigram}</dd></div>
              <div><dt>变化用卦</dt><dd>{page8.program_strength.changed_use_trigram}</dd></div>
              <div><dt>初始体用</dt><dd>{page8.program_strength.initial_relation}</dd></div>
              <div><dt>变化体用</dt><dd>{page8.program_strength.changed_relation}</dd></div>
              <div><dt>体卦旺衰</dt><dd>{page8.program_strength.body_strength}</dd></div>
            </dl>
          </article>
        </div>
      </section>
      <section className="productPage" aria-labelledby="p9-title">
        <p className="eyebrow">P9 · 决策落地</p>
        <h2 id="p9-title">判断、行动边界与转向信号</h2>
        <p className="productBoundary">以下五节均为本次已通过安全核验的九章原文切片；页面没有摘要、补写或二次模型调用。</p>
        <div className="page9Sections">
          {[page9.judgment, page9.suitable_actions, page9.unsuitable_actions, page9.reverse_risk, page9.change_signals].map((section) => (
            <article key={section.heading} data-source-sha256={section.sha256}>
              <SafeDirectReadingMarkdown source={section.markdown} />
            </article>
          ))}
        </div>
      </section>
      <p className="lineage">正文 SHA：{presentation.source_reading_sha256} · 机械重建一致</p>
    </>
  );
}
