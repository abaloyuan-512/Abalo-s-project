"use client";

import { Page8KunStory, type Page8Reading } from "../GuanxiangApp";
import { p9OfflineFixture } from "../direct-reading-v2-preview/p9OfflineFixture";
import styles from "./page.module.css";

export type P8Direction = "web-copy" | "web-near" | "web-air";

const acts = p9OfflineFixture.export_bundle.page8_acts;
const sceneIds = [
  "BASE_HEXAGRAM",
  "MUTUAL_HEXAGRAM",
  "MOVING_LINE",
  "CHANGED_HEXAGRAM",
  "BODY_USE_STRENGTH",
] as const;
const symbols = ["䷔", "䷦", null, "䷚", null] as const;
const primaryNames = ["火雷噬嗑", "水山蹇", "九四", "山雷颐", "体卦震"] as const;
const formations = [
  "第一数定上卦，第二数定下卦；上下相叠形成本卦。",
  "取本卦中间四爻重新组合，形成互卦。",
  "第三数按六数之余确定本次动爻。",
  "本次动爻变化后形成变卦。",
  "体用与旺衰由确定性程序依据同一次排盘计算。",
] as const;
const roles = [
  "本卦呈现当前局面的主要结构。",
  "互卦呈现事情内部的结构变化。",
  "动爻标记本次卦象中发生结构变化的位置。",
  "变卦呈现变化后的结构重点，不代表必然未来。",
  "帮助观察当前结构的承接关系，不单独生成吉凶总评。",
] as const;

const reading: Page8Reading = {
  template_version: "SITES_PAGE8_READING_V1",
  stage_title: "读卦",
  user_question: p9OfflineFixture.question,
  scenes: acts.map((act, index) => ({
    scene_id: sceneIds[index],
    sequence: index + 1,
    title: index === 4 ? "体用与旺衰" : act.title,
    purpose: act.subtitle.split(" · ").slice(1).join(" · ") || act.subtitle,
    deterministic: {
      primary_name: primaryNames[index],
      symbol: symbols[index],
      king_wen_number: index === 0 ? 21 : index === 1 ? 39 : index === 3 ? 27 : null,
      formation: formations[index],
      reading_role: roles[index],
      canonical_label: index === 2 ? "爻辞原文" : null,
      canonical_text: index === 2 ? p9OfflineFixture.export_bundle.cast.canonical_line : null,
      facts: index === 2
        ? [{ label: "动爻位置", value: "4" }]
        : index === 4
          ? [
            { label: "初始体用", value: "体生用" },
            { label: "变化体用", value: "体克用" },
            { label: "体卦旺衰", value: "死" },
          ]
          : [],
      source_name: "同一次确定性排盘",
      source_reference: "P8-WEB-REFERENCE",
    },
    interpretation: {
      scene_id: sceneIds[index],
      layer_summary: act.body[0],
      reality_connection: act.body.slice(1).join(""),
      uncertainty_boundary: "仅用于隔离本地视觉对照。",
      reality_refs: [],
      evidence_refs: [],
      interpretation_hypothesis: true,
    },
  })),
  epistemic_boundary: "P8 只组合同一次程序排盘与已经核验的 Direct Reading 正文。",
  page9_reserved: true,
};

export default function P8MobileLab({ direction, motion, reference = false, chrome = false, embedded = false }: {
  direction: P8Direction;
  motion: boolean;
  reference?: boolean;
  chrome?: boolean;
  embedded?: boolean;
}) {
  const directionClass = reference ? styles.reference : styles[direction];
  const directionName = reference
    ? "网页端原版"
    : direction === "web-copy"
      ? "网页原样复刻"
      : direction === "web-near"
      ? "网页近读版"
      : "网页留白版";

  if (!embedded) {
    const previewParams = new URLSearchParams({
      direction,
      motion: motion ? "on" : "off",
      embedded: "1",
    });
    if (reference) previewParams.set("reference", "web");
    if (chrome) previewParams.set("chrome", "1");

    return <main className={styles.previewShell}>
      <section className={styles.previewColumn} aria-label="P8 手机端 430×932 仿真预览">
        <header className={styles.previewHeader}>
          <span>手机端仿真预览</span>
          <b>430 × 932</b>
        </header>
        <div className={styles.deviceFrame}>
          <iframe
            className={styles.deviceViewport}
            title="P8 手机端 430×932 预览"
            src={`/p8-mobile-art-lab?${previewParams.toString()}`}
          />
        </div>
        <p className={styles.previewNote}>华为 Pura 70 Ultra 尺寸仿真，待产品负责人真机验收</p>
      </section>
    </main>;
  }

  return <main
    className={`${styles.lab} ${directionClass} ${motion ? styles.motionOn : styles.motionOff}`}
    data-direction={reference ? "web-reference" : direction}
    data-motion={motion ? "on" : "off"}
  >
    {chrome && <aside className={styles.labBadge}>
      <b>{directionName}</b>
      <span>仿真，待产品负责人真机验收</span>
    </aside>}
    <Page8KunStory reading={reading} task={{ phase: "SUCCESS", message: "详细解卦已经生成。" }} />
  </main>;
}
