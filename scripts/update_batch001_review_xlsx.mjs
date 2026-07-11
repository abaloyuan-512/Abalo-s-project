import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.env.ABALO_ROOT || process.cwd();
const inputPath = `${root}/docs/knowledge_reviews/batch_001/MEIHUA_KNOWLEDGE_BATCH_001_REVIEW.xlsx`;
const jsonPath = `${root}/review_data/meihua/batch_001/batch_001_review_drafts.json`;
const previewDir = process.env.ABALO_XLSX_PREVIEW || `${root}/.tmp_batch001_xlsx_preview`;
const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 5000 });
console.log(sheets.ndjson);
await fs.mkdir(previewDir, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const used = sheet.getUsedRange();
  console.log(`SHEET=${sheet.name} USED=${used.address}`);
  const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${sheet.name}.png`, new Uint8Array(await preview.arrayBuffer()));
}

if (process.argv.includes("--write")) {
  const payload = JSON.parse(await fs.readFile(jsonPath, "utf8"));
  const records = payload.records;
  const overview = workbook.worksheets.getItem("批次说明");
  overview.getRange("B3:B4").values = [["AI 编辑 DRAFT 待人工审核；不是人工签核"], ["生产导入禁用；仅内部 DRAFT 预览"]];
  overview.getRange("B8:B10").values = [[0], ["DRAFT=16；CANONICAL_ONLY=432"], ["16 条 AI 编辑提案已写入，等待人工审核"]];
  const headerMap = {
    "白话直译": "literal_paraphrase", "爻位阶段关系": "moving_stage_relationship",
    "核心主题": "core_theme", "情境模式": "situation_pattern", "有利条件": "favorable_conditions",
    "风险条件": "risk_conditions", "行动倾向": "action_tendency", "感情边界": "relationship_boundaries",
    "职业边界": "career_boundaries", "合作边界": "cooperation_boundaries", "禁止推断": "prohibited_inferences",
    "证据方向": "evidence_direction", "证据强度": "evidence_strength", "审核备注": "reviewer_notes",
    "审核决定": "review_decision",
  };
  for (const sheetName of ["卦级审核", "爻级审核"]) {
    const sheet = workbook.worksheets.getItem(sheetName);
    const values = sheet.getUsedRange().values;
    const headers = values[0];
    for (let row = 1; row < values.length; row++) {
      const record = records.find((item) => item.item_id === values[row][0]);
      if (!record) continue;
      sheet.getCell(row, headers.indexOf("正式状态")).values = [["DRAFT"]];
      sheet.getCell(row, headers.indexOf("工作台状态")).values = [["READY_FOR_CONTENT_REVIEW"]];
      if (record.item_id === "H12") {
        sheet.getCell(row, headers.indexOf("项目冻结卦辞")).values = [[record.canonical_text_from_project]];
        sheet.getCell(row, headers.indexOf("实质异文")).values = [["否"]];
        sheet.getCell(row, headers.indexOf("异文说明")).values = [[record.source_comparison.variant_notes]];
      }
      for (const [label, field] of Object.entries(headerMap)) {
        const col = headers.indexOf(label);
        if (col < 0) continue;
        const value = record.review_fields[field];
        sheet.getCell(row, col).values = [[Array.isArray(value) ? value.join("；") : (value ?? "")]];
      }
    }
  }
  const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, maxChars: 3000 });
  console.log(errors.ndjson);
  for (const check of [["批次说明", "A1:B12"], ["卦级审核", "A1:AE3"], ["爻级审核", "A1:AH3"]]) {
    const inspected = await workbook.inspect({ kind: "table", sheetId: check[0], range: check[1], include: "values,formulas", tableMaxRows: 3, tableMaxCols: 40, tableMaxCellChars: 80, maxChars: 8000 });
    console.log(inspected.ndjson);
  }
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(inputPath);
  for (const sheet of workbook.worksheets.items) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(`${previewDir}/${sheet.name}_after.png`, new Uint8Array(await preview.arrayBuffer()));
  }
  console.log("XLSX_WRITEBACK=PASS");
}
