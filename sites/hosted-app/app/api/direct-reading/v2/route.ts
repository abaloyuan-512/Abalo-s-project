import {
  finalizeDirectReadingPreviewJob,
  markDirectReadingPreviewJobLost,
  readDirectReadingPreviewJob,
  reserveDirectReadingPreviewJob,
} from "../../../../db/direct-reading-preview-jobs";

const MAX_REQUEST_BYTES = 8 * 1024;
const MAX_RESPONSE_BYTES = 128 * 1024;
const POLL_TIMEOUT_MS = 15_000;
const SUBMIT_TIMEOUT_MS = 90_000;
const REQUEST_ID_PATTERN = /^drv2-[a-f0-9]{16,64}$/;
const PUBLIC_CONTRACT_VERSION = "SITES_DIRECT_READING_V2_PREVIEW_PUBLIC_V1";
const UPSTREAM_CONTRACT_VERSION = "SITES_DIRECT_READING_V2_NONPROD_V2";
const PROMPT_VERSION = "GUANXIANG_DIRECT_READING_PROMPT_V3_P9_FINALE_SAME_CALL_V1";

type Payload = {
  contract_version?: unknown;
  request_id?: unknown;
  question_text?: unknown;
  numbers?: unknown;
  status?: unknown;
  stage?: unknown;
  chart_facts?: unknown;
  direct_reading?: unknown;
  page9_finale?: unknown;
  product_presentation?: unknown;
  direct_high?: unknown;
  entry_mode?: unknown;
  intake_id?: unknown;
  clarification_answer?: unknown;
  error_code?: unknown;
  error_message?: unknown;
  retryable?: unknown;
  failure_stage?: unknown;
  [key: string]: unknown;
};

function safeJson(body: unknown, status: number): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
      "Referrer-Policy": "no-referrer",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function isAuthenticatedOwner(request: Request): boolean {
  const url = new URL(request.url);
  const localBypass = process.env.ABALO_LOCAL_PREVIEW_BYPASS_AUTH?.trim().toLowerCase() === "true";
  if (localBypass && ["127.0.0.1", "localhost"].includes(url.hostname)) return true;
  const email = request.headers.get("oai-authenticated-user-email")?.trim();
  const owner = process.env.ABALO_PREVIEW_OWNER_EMAIL?.trim();
  return Boolean(
    email && owner && email.length <= 320 && owner.length <= 320 &&
    email.toLowerCase() === owner.toLowerCase()
  );
}

function previewEnabled(): boolean {
  return process.env.ABALO_DIRECT_READING_V2_PREVIEW_ENABLED?.trim().toLowerCase() === "true";
}

function upstreamUrl(path: string): URL | null {
  const raw = process.env.PYTHON_ENGINE_URL?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
    if (url.protocol !== "https:" && !(local && url.protocol === "http:")) return null;
    url.pathname = `${url.pathname.replace(/\/$/, "")}${path}`;
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonical(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function sha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("").toUpperCase();
}

function validNumbers(value: unknown): value is [number, number, number] {
  return Array.isArray(value) && value.length === 3 && value.every(
    (item) => Number.isInteger(item) && item >= 1 && item <= 999,
  );
}

function validQuestion(value: unknown): value is string {
  return typeof value === "string" && value === value.trim() && value.length >= 6 && value.length <= 160 && !/[\r\n]/.test(value);
}

async function readUpstream(upstream: Response): Promise<Payload | null> {
  const text = await upstream.text();
  if (new TextEncoder().encode(text).byteLength > MAX_RESPONSE_BYTES) return null;
  try {
    const payload = JSON.parse(text) as Payload;
    if (
      payload.contract_version !== PUBLIC_CONTRACT_VERSION ||
      typeof payload.request_id !== "string" ||
      typeof payload.status !== "string"
    ) return null;
    return payload;
  } catch {
    return null;
  }
}

const SHA256_PATTERN = /^[0-9A-F]{64}$/;

function record(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

async function publicAllowList(payload: Payload): Promise<Payload> {
  const success = payload.status === "SUCCESS";
  const reading = record(payload.direct_reading);
  const facts = record(reading?.chart_facts) ?? record(payload.chart_facts);
  const hexagram = (value: unknown, role: "BASE" | "MUTUAL" | "CHANGED") => {
    const item = record(value);
    if (
      !item || item.role !== role || !Number.isInteger(item.king_wen_number) ||
      Number(item.king_wen_number) < 1 || Number(item.king_wen_number) > 64 ||
      !nonEmptyString(item.name) || !nonEmptyString(item.upper_trigram) ||
      !nonEmptyString(item.lower_trigram)
    ) return null;
    return {
      role,
      king_wen_number: item.king_wen_number,
      name: item.name,
      upper_trigram: item.upper_trigram,
      lower_trigram: item.lower_trigram,
    };
  };
  const baseFact = hexagram(facts?.base_hexagram, "BASE");
  const mutualFact = hexagram(facts?.mutual_hexagram, "MUTUAL");
  const changedFact = hexagram(facts?.changed_hexagram, "CHANGED");
  const movingLine = record(facts?.moving_line);
  const safeMovingLine = movingLine && Number.isInteger(movingLine.position) &&
    Number(movingLine.position) >= 1 && Number(movingLine.position) <= 6 &&
    nonEmptyString(movingLine.name) && nonEmptyString(movingLine.canonical_line_text) &&
    nonEmptyString(movingLine.canonical_data_version)
    ? {
      position: movingLine.position,
      name: movingLine.name,
      canonical_line_text: movingLine.canonical_line_text,
      canonical_data_version: movingLine.canonical_data_version,
    }
    : null;
  const safeFacts = baseFact && mutualFact && changedFact && safeMovingLine &&
    nonEmptyString(facts?.rule_version) && nonEmptyString(facts?.engine_version)
    ? {
        base_hexagram: baseFact,
        mutual_hexagram: mutualFact,
        changed_hexagram: changedFact,
        moving_line: safeMovingLine,
        rule_version: facts.rule_version,
        engine_version: facts.engine_version,
      }
    : null;
  const safeReading = success && reading && safeFacts && nonEmptyString(reading.text) &&
    nonEmptyString(reading.version) && reading.content_format === "MARKDOWN" &&
    reading.validation_status === "PASSED"
    ? {
        version: reading.version,
        content_format: "MARKDOWN",
        text: reading.text,
        validation_status: "PASSED",
        chart_facts: safeFacts,
      }
    : null;
  const presentation = success ? record(payload.product_presentation) : null;
  const directHigh = success ? record(payload.direct_high) : null;
  const finale = success ? record(payload.page9_finale) : null;
  const finaleAnswer = Array.isArray(finale?.answer) ? finale.answer : null;
  const safeFinale = finale?.content_version === "GUANXIANG_P9_FINALE_V1" &&
    finale?.source === "SAME_PROVIDER_OUTPUT" && finale?.additional_model_calls === 0 &&
    finaleAnswer?.length === 2 && finaleAnswer.every((line) => (
      typeof line === "string" && line.length >= 4 && line.length <= 40 && !/[\r\n<>`#*]/.test(line)
    )) && finaleAnswer.reduce((total, line) => total + String(line).length, 0) <= 72
    ? {
        content_version: "GUANXIANG_P9_FINALE_V1",
        source: "SAME_PROVIDER_OUTPUT",
        answer: [String(finaleAnswer[0]), String(finaleAnswer[1])],
        additional_model_calls: 0,
      }
    : null;
  const section = (value: unknown, expectedHeading: string) => {
    const item = record(value);
    if (
      !item || item.heading !== expectedHeading || !nonEmptyString(item.markdown) ||
      !item.markdown.startsWith(`## ${expectedHeading}\n`) ||
      !Number.isInteger(item.start_offset) || !Number.isInteger(item.end_offset) ||
      Number(item.start_offset) < 0 || Number(item.end_offset) <= Number(item.start_offset) ||
      typeof item.sha256 !== "string" || !SHA256_PATTERN.test(item.sha256)
    ) return null;
    return {
      heading: expectedHeading,
      markdown: item.markdown,
      start_offset: item.start_offset,
      end_offset: item.end_offset,
      sha256: item.sha256,
    };
  };
  const hexagramScene = (
    value: unknown,
    expectedFact: ReturnType<typeof hexagram>,
    headingPrefix: "本卦" | "互卦" | "变卦",
  ) => {
    const item = record(value);
    const fact = record(item?.program_fact);
    const heading = expectedFact ? `${headingPrefix}：${expectedFact.name}` : "";
    const modelSection = section(item?.model_section, heading);
    if (
      !item || !fact || !expectedFact || !modelSection ||
      fact.source !== "SAME_PREPARED_CHART" ||
      fact.role !== expectedFact.role || fact.king_wen_number !== expectedFact.king_wen_number ||
      fact.name !== expectedFact.name || fact.upper_trigram !== expectedFact.upper_trigram ||
      fact.lower_trigram !== expectedFact.lower_trigram
    ) return null;
    return {
      program_fact: { ...expectedFact, source: "SAME_PREPARED_CHART" },
      model_section: modelSection,
    };
  };
  const page8 = record(presentation?.page8);
  const page9 = record(presentation?.page9);
  const baseScene = hexagramScene(page8?.base_hexagram, baseFact, "本卦");
  const mutualScene = hexagramScene(page8?.mutual_hexagram, mutualFact, "互卦");
  const changedScene = hexagramScene(page8?.changed_hexagram, changedFact, "变卦");
  const moving = record(page8?.moving_line);
  const movingFact = record(moving?.program_fact);
  const movingSection = section(moving?.model_section, safeMovingLine ? `动爻：${safeMovingLine.name}` : "");
  const safeMovingScene = movingFact && movingSection && safeMovingLine &&
    movingFact.source === "SAME_PREPARED_CHART" &&
    movingFact.position === safeMovingLine.position && movingFact.name === safeMovingLine.name &&
    movingFact.canonical_line_text === safeMovingLine.canonical_line_text &&
    movingFact.canonical_data_version === safeMovingLine.canonical_data_version
    ? { program_fact: { ...safeMovingLine, source: "SAME_PREPARED_CHART" }, model_section: movingSection }
    : null;
  const strength = record(page8?.program_strength);
  const safeStrength = strength && strength.source === "PROGRAM_ONLY_BODY_USE_AND_SEASONAL_STRENGTH" &&
    [strength.body_trigram, strength.initial_use_trigram, strength.changed_use_trigram,
      strength.initial_relation, strength.changed_relation, strength.body_strength].every(nonEmptyString) &&
    typeof strength.program_fact_sha256 === "string" && SHA256_PATTERN.test(strength.program_fact_sha256)
    ? {
        source: strength.source,
        body_trigram: strength.body_trigram,
        initial_use_trigram: strength.initial_use_trigram,
        changed_use_trigram: strength.changed_use_trigram,
        initial_relation: strength.initial_relation,
        changed_relation: strength.changed_relation,
        body_strength: strength.body_strength,
        program_fact_sha256: strength.program_fact_sha256,
      }
    : null;
  const judgment = section(page9?.judgment, "判断");
  const suitable = section(page9?.suitable_actions, "适合做什么");
  const unsuitable = section(page9?.unsuitable_actions, "不适合做什么");
  const reverseRisk = section(page9?.reverse_risk, "反向风险");
  const changeSignals = section(page9?.change_signals, "哪些现实信号会改变判断");
  const orderedSections = [judgment, baseScene?.model_section, mutualScene?.model_section,
    safeMovingScene?.model_section, changedScene?.model_section, suitable, unsuitable,
    reverseRisk, changeSignals];
  const sourceText = safeReading?.text;
  const spansExact = typeof sourceText === "string" && orderedSections.every((item) => item !== null && item !== undefined) &&
    orderedSections.every((item, index) => {
      if (!item) return false;
      const previousEnd = index === 0 ? 0 : Number(orderedSections[index - 1]?.end_offset);
      return item.start_offset === previousEnd && sourceText.slice(item.start_offset, item.end_offset) === item.markdown;
    }) && orderedSections.at(-1)?.end_offset === sourceText.length &&
    orderedSections.map((item) => item?.markdown ?? "").join("") === sourceText;
  const sourceDigest = typeof sourceText === "string" ? await sha256(sourceText) : null;
  const sectionDigestsExact = orderedSections.every((item) => item !== null && item !== undefined) &&
    (await Promise.all(orderedSections.map(async (item) => item ? await sha256(item.markdown) === item.sha256 : false))).every(Boolean);
  const chartDigest = safeFacts ? await sha256(canonical(safeFacts)) : null;
  const strengthDigest = safeStrength ? await sha256(canonical({
    source: safeStrength.source,
    body_trigram: safeStrength.body_trigram,
    initial_use_trigram: safeStrength.initial_use_trigram,
    changed_use_trigram: safeStrength.changed_use_trigram,
    initial_relation: safeStrength.initial_relation,
    changed_relation: safeStrength.changed_relation,
    body_strength: safeStrength.body_strength,
  })) : null;
  const safePresentation = presentation?.contract_version === "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1" &&
    presentation.reconstructed_equals_source === true &&
    typeof presentation.source_reading_sha256 === "string" && SHA256_PATTERN.test(presentation.source_reading_sha256) &&
    presentation.source_reading_sha256 === sourceDigest && sectionDigestsExact &&
    presentation.reconstructed_reading_sha256 === presentation.source_reading_sha256 &&
    typeof presentation.prepared_chart_sha256 === "string" && SHA256_PATTERN.test(presentation.prepared_chart_sha256) &&
    presentation.prepared_chart_sha256 === chartDigest && strengthDigest === safeStrength?.program_fact_sha256 &&
    page8?.responsibility === "BASE_MUTUAL_MOVING_CHANGED_PROGRAM_STRENGTH" &&
    page9?.responsibility === "JUDGMENT_ACTIONS_RISK_CHANGE_SIGNALS" &&
    page8.model_calls_for_mapping === 0 && page8.additional_casts_for_mapping === 0 &&
    page9.model_calls_for_mapping === 0 && page9.additional_casts_for_mapping === 0 &&
    baseScene && mutualScene && safeMovingScene && changedScene && safeStrength &&
    judgment && suitable && unsuitable && reverseRisk && changeSignals && spansExact
    ? {
        contract_version: "SITES_DIRECT_HIGH_P8_P9_PRODUCT_V1",
        source_reading_sha256: presentation.source_reading_sha256,
        reconstructed_reading_sha256: presentation.reconstructed_reading_sha256,
        reconstructed_equals_source: true,
        prepared_chart_sha256: presentation.prepared_chart_sha256,
        page8: {
          responsibility: page8.responsibility,
          base_hexagram: baseScene,
          mutual_hexagram: mutualScene,
          moving_line: safeMovingScene,
          changed_hexagram: changedScene,
          program_strength: safeStrength,
          model_calls_for_mapping: 0,
          additional_casts_for_mapping: 0,
        },
        page9: {
          responsibility: page9.responsibility,
          judgment, suitable_actions: suitable, unsuitable_actions: unsuitable,
          reverse_risk: reverseRisk, change_signals: changeSignals,
          model_calls_for_mapping: 0,
          additional_casts_for_mapping: 0,
        },
      }
    : null;
  const routerAttempts = directHigh?.router_attempts;
  const intakeStatus = directHigh?.intake_status;
  const directRoute = directHigh?.route === "DIRECT_HIGH" && routerAttempts === 0 && intakeStatus === "BYPASSED";
  const conditionalRoute = directHigh?.route === "CONDITIONAL_INTAKE_THEN_HIGH" && routerAttempts === 1 &&
    ["PASSED", "ASKED_ONCE_ANSWERED", "ASKED_ONCE_SKIPPED"].includes(String(intakeStatus));
  const safeDirectHigh = directHigh &&
    (directRoute || conditionalRoute) &&
    ["CLEAR", "CONFIRMED", "SKIP"].includes(String(directHigh.entry_mode)) &&
    directHigh.automatic_retries === 0
    ? {
        route: directHigh.route,
        entry_mode: directHigh.entry_mode,
        router_attempts: routerAttempts,
        intake_status: intakeStatus,
        router_failure_code: typeof directHigh.router_failure_code === "string" ? directHigh.router_failure_code : null,
        automatic_retries: 0,
      }
    : null;
  const releaseReady = !success || Boolean(safeReading && safePresentation && safeDirectHigh && safeFinale);
  return {
    contract_version: PUBLIC_CONTRACT_VERSION,
    request_id: payload.request_id,
    status: releaseReady ? payload.status : "BLOCKED_OUTPUT",
    ...(typeof payload.stage === "string" ? { stage: payload.stage } : {}),
    chart_facts: safeFacts,
    direct_reading: releaseReady ? safeReading : null,
    page9_finale: releaseReady ? safeFinale : null,
    product_presentation: releaseReady ? safePresentation : null,
    direct_high: releaseReady ? safeDirectHigh : null,
    error_code: releaseReady ? (typeof payload.error_code === "string" ? payload.error_code : null) : "PRODUCT_PRESENTATION_REJECTED",
    error_message: releaseReady ? (typeof payload.error_message === "string" ? payload.error_message : null) : "P8/P9 release payload failed the public schema boundary.",
    retryable: payload.retryable === true,
    failure_stage: typeof payload.failure_stage === "string" ? payload.failure_stage : null,
  };
}

function preflight(request: Request): Response | null {
  if (!isAuthenticatedOwner(request)) return safeJson({ error: "请先登录私有预览。", terminal: true }, 403);
  if (!previewEnabled()) return safeJson({ error: "Direct Reading V2 私有预览尚未开启。", terminal: true }, 503);
  return null;
}

export async function GET(request: Request): Promise<Response> {
  const blocked = preflight(request);
  if (blocked) return blocked;
  const requestId = new URL(request.url).searchParams.get("request_id")?.trim() ?? "";
  if (!REQUEST_ID_PATTERN.test(requestId)) return safeJson({ error: "请求编号无效。" }, 400);
  const job = await readDirectReadingPreviewJob(requestId);
  if (!job) return safeJson({ error: "任务不存在。" }, 404);
  if (job.state === "LOST") {
    return safeJson({ error: "任务在服务恢复过程中失去，系统没有自动重复生成。" }, 410);
  }
  const url = upstreamUrl(`/api/preview/v2/direct-reading/jobs/${encodeURIComponent(requestId)}`);
  const key = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !key) return safeJson({ error: "Direct Reading V2 引擎尚未连接。" }, 503);
  try {
    const upstream = await fetch(url, {
      headers: { "X-Abalo-Engine-Key": key },
      cache: "no-store",
      signal: AbortSignal.timeout(POLL_TIMEOUT_MS),
    });
    if (upstream.status === 404) {
      if (job.state === "RUNNING") await markDirectReadingPreviewJobLost(requestId, "ENGINE_JOB_LOST");
      return safeJson({ error: "任务在引擎重启后无法恢复，系统没有自动重复生成。" }, 410);
    }
    const payload = await readUpstream(upstream);
    if (!payload || payload.request_id !== requestId) return safeJson({ error: "解卦响应异常。" }, 502);
    if (upstream.status === 202) return safeJson(await publicAllowList(payload), 202);
    if (!upstream.ok) return safeJson({ error: "解卦响应异常。" }, 502);
    const safePayload = await publicAllowList(payload);
    await finalizeDirectReadingPreviewJob(requestId, String(safePayload.status));
    return safeJson(safePayload, 200);
  } catch {
    return safeJson({ error: "任务状态暂时无法确认；系统不会自动重复生成。" }, 503);
  }
}

export async function POST(request: Request): Promise<Response> {
  const blocked = preflight(request);
  if (blocked) return blocked;
  if (request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase() !== "application/json") {
    return safeJson({ error: "请求格式不受支持。" }, 415);
  }
  const body = await request.text();
  if (new TextEncoder().encode(body).byteLength > MAX_REQUEST_BYTES) return safeJson({ error: "请求内容过大。" }, 413);
  let payload: Payload;
  try { payload = JSON.parse(body) as Payload; } catch { return safeJson({ error: "请求内容不是有效JSON。" }, 400); }
  const requestId = typeof payload.request_id === "string" ? payload.request_id.trim() : "";
  const entryMode = payload.entry_mode ?? "CLEAR";
  const intakeId = payload.intake_id;
  const clarificationAnswer = payload.clarification_answer;
  const intakeValid = intakeId === undefined || (typeof intakeId === "string" && /^intake-[a-f0-9]{16,64}$/.test(intakeId));
  const answerValid = clarificationAnswer === undefined || (
    typeof clarificationAnswer === "string" && clarificationAnswer === clarificationAnswer.trim() &&
    clarificationAnswer.length >= 1 && clarificationAnswer.length <= 400 && !/[\r\n]/.test(clarificationAnswer)
  );
  if (
    payload.contract_version !== PUBLIC_CONTRACT_VERSION ||
    !REQUEST_ID_PATTERN.test(requestId) ||
    !validQuestion(payload.question_text) ||
    !validNumbers(payload.numbers) ||
    !["CLEAR", "CONFIRMED", "SKIP"].includes(String(entryMode)) ||
    !intakeValid || !answerValid
  ) return safeJson({ error: "问题、三个数字或请求版本无效。" }, 400);

  const digest = await sha256(canonical({
    question_text: payload.question_text,
    numbers: payload.numbers,
    entry_mode: entryMode,
    ...(typeof intakeId === "string" ? { intake_id: intakeId } : {}),
    ...(typeof clarificationAnswer === "string" ? { clarification_answer: clarificationAnswer } : {}),
  }));
  const reservation = await reserveDirectReadingPreviewJob(requestId, digest, PROMPT_VERSION);
  if (reservation.state === "CONFLICT") return safeJson({ error: "请求编号与已有内容冲突。" }, 409);
  if (reservation.state === "FINALIZED" || reservation.state === "LOST") {
    return safeJson({ error: "这个任务已经结束，系统不会重复生成。" }, 409);
  }
  if (reservation.state === "RUNNING") {
    return safeJson({
      contract_version: PUBLIC_CONTRACT_VERSION,
      request_id: requestId,
      status: "RUNNING",
      stage: "SUBMITTED",
      direct_reading: null,
    }, 202);
  }

  const url = upstreamUrl("/api/preview/v2/direct-reading/jobs");
  const key = process.env.PYTHON_ENGINE_KEY?.trim();
  if (!url || !key) {
    await markDirectReadingPreviewJobLost(requestId, "ENGINE_NOT_CONNECTED");
    return safeJson({ error: "Direct Reading V2 引擎尚未连接，未自动重复生成。" }, 503);
  }
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Abalo-Engine-Key": key },
      body: JSON.stringify({
        contract_version: UPSTREAM_CONTRACT_VERSION,
        request_id: requestId,
        question_text: payload.question_text,
        numbers: payload.numbers,
        entry_mode: entryMode,
        ...(typeof intakeId === "string" ? { intake_id: intakeId } : {}),
        ...(typeof clarificationAnswer === "string" ? { clarification_answer: clarificationAnswer } : {}),
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(SUBMIT_TIMEOUT_MS),
    });
    if (upstream.status === 409) {
      await finalizeDirectReadingPreviewJob(requestId, "REQUEST_ID_CONFLICT");
      return safeJson({ error: "请求编号与引擎中的已有任务冲突。" }, 409);
    }
    const result = await readUpstream(upstream);
    if (!result || result.request_id !== requestId) return safeJson({ error: "解卦响应异常。" }, 502);
    if (upstream.status === 202) return safeJson(await publicAllowList(result), 202);
    if (!upstream.ok) {
      await finalizeDirectReadingPreviewJob(requestId, String(result.status));
      return safeJson({ error: "解卦任务未能启动。" }, 502);
    }
    const safeResult = await publicAllowList(result);
    await finalizeDirectReadingPreviewJob(requestId, String(safeResult.status));
    return safeJson(safeResult, 200);
  } catch {
    return safeJson({ error: "提交状态暂时无法确认；请使用同一编号查询，系统不会自动重复生成。" }, 503);
  }
}
