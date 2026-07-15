"use strict";

const CONTRACT_VERSION = "SITES_MEIHUA_API_CONTRACT_V1";
const ERROR_MESSAGES = {
  INVALID_REQUEST: ["输入未通过校验", "请检查问题长度、三个数字和确认项。"],
  EMPTY_QUESTION: ["还没有具体问题", "请输入一个非空白问题。"],
  INVALID_NUMBER_COUNT: ["数字尚未填写完整", "请完整输入三个数字。"],
  INVALID_NUMBER_TYPE: ["数字不在有效范围", "三个数字都必须是 1 至 999 的整数。"],
  MULTIPLE_QUESTIONS_NOT_ALLOWED: ["一次只处理一个问题", "请保留一个最想厘清的问题。"],
  CLIENT_CALCULATION_NOT_ACCEPTED: ["请求包含不受支持的内容", "页面只提交原始输入，结构由本地服务生成。"],
  UNSUPPORTED_PREDICTION_REQUEST: ["这个问题不适合生成结果", "请改为询问当前条件、行动或观察信号。"],
  UNSUPPORTED_THIRD_PARTY_INFERENCE: ["无法判断他人的内心或隐私", "请改为关注自己的行动、边界和可观察信号。"],
  UNSUPPORTED_HIGH_RISK_REQUEST: ["这个问题需要现实中的专业判断", "本页面没有生成卦象，请依据可靠信息寻求合适的专业支持。"],
  IMMEDIATE_SAFETY_RISK: ["请优先处理现实中的安全", "请不要等待预测结果；如存在迫近危险，请立即联系当地紧急服务和可信任的人。"],
  ENGINE_ERROR: ["暂时无法生成结构", "当前没有生成结果，请稍后在本机重试。"],
};
const SAFE_SERVER_MESSAGE_CODES = new Set([
  "UNSUPPORTED_PREDICTION_REQUEST",
  "UNSUPPORTED_THIRD_PARTY_INFERENCE",
  "UNSUPPORTED_HIGH_RISK_REQUEST",
  "IMMEDIATE_SAFETY_RISK",
]);
const CONCLUSION_LABELS = {
  CLEARLY_FAVORABLE: "明显有利",
  CONDITIONALLY_FAVORABLE: "有条件有利",
  MIXED_OR_UNSETTLED: "交错未定",
  CLEARLY_UNFAVORABLE: "明显不利",
  INSUFFICIENT_EVIDENCE: "证据不足",
};
const STRENGTH_LABELS = { PROSPEROUS: "旺", SUPPORTED: "相", RESTING: "休", CONFINED: "囚", DEAD: "死" };
const RELATION_LABELS = {
  USE_GENERATES_BODY: "用生体",
  BODY_CONTROLS_USE: "体克用",
  SAME_ELEMENT: "体用比和",
  BODY_GENERATES_USE: "体生用",
  USE_CONTROLS_BODY: "用克体",
};
const KNOWLEDGE_MODE_LABELS = {
  PROGRAM_ONLY: "仅依据程序规则",
  PROGRAM_AND_APPROVED_KNOWLEDGE: "程序规则与已批准知识",
};

const byId = (id) => document.getElementById(id);
const form = byId("question-form");
const question = byId("question");
const submitButton = byId("submit-button");
const loadingStatus = byId("loading-status");
const resultPanel = byId("result-panel");
const formError = byId("form-error");
const validatedFields = [question, ...[1, 2, 3].map((index) => byId(`number-${index}`)), byId("ack-deterministic"), byId("ack-narrative")];

function setText(id, value) { byId(id).textContent = String(value); }
function show(element, visible) { element.hidden = !visible; }
function scrollToElement(element) {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  element.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}

function createRequestId() {
  const random = globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `phase3b-local-${random}`;
}

function rawNumbers() {
  return [1, 2, 3].map((index) => byId(`number-${index}`).value);
}

function errorDescriptionIds(field) {
  return (field.getAttribute("aria-describedby") || "").split(/\s+/).filter((id) => id && id !== formError.id);
}

function clearFieldError(field) {
  field.setAttribute("aria-invalid", "false");
  const ids = errorDescriptionIds(field);
  if (ids.length) field.setAttribute("aria-describedby", ids.join(" "));
  else field.removeAttribute("aria-describedby");
}

function clearInvalidState() {
  validatedFields.forEach(clearFieldError);
}

function clearFormError() {
  clearInvalidState();
  setText("form-error", "");
  show(formError, false);
}

function markFieldInvalid(field) {
  clearInvalidState();
  field.setAttribute("aria-invalid", "true");
  field.setAttribute("aria-describedby", [...errorDescriptionIds(field), formError.id].join(" "));
}

function validateInput() {
  clearInvalidState();
  const rawQuestion = question.value;
  if (rawQuestion.length < 1 || rawQuestion.length > 500 || rawQuestion.trim().length === 0) {
    markFieldInvalid(question);
    return { message: "请输入一个 1 至 500 个字符的具体问题，不能只填写空格。", focus: question };
  }
  const numbers = rawNumbers().map(Number);
  const invalidIndex = numbers.findIndex((value, index) => rawNumbers()[index] === "" || !Number.isInteger(value) || value < 1 || value > 999);
  if (invalidIndex !== -1) {
    const input = byId(`number-${invalidIndex + 1}`);
    markFieldInvalid(input);
    return { message: "请完整填写三个 1 至 999 的整数。", focus: input };
  }
  if (!byId("ack-deterministic").checked || !byId("ack-narrative").checked) {
    const input = byId("ack-deterministic").checked ? byId("ack-narrative") : byId("ack-deterministic");
    markFieldInvalid(input);
    return { message: "请先确认结果边界与当前版本的解读范围。", focus: input };
  }
  return null;
}

function buildRequest() {
  return {
    contract_version: CONTRACT_VERSION,
    request_id: createRequestId(),
    question_text: question.value,
    numbers: rawNumbers().map(Number),
    locale: "zh-CN",
    client_timestamp: new Date().toISOString(),
    user_acknowledgements: { deterministic_only: true, narrative_unverified: true },
  };
}

function validEnvelope(response) {
  const knownStatus = ["SUCCESS", "VALIDATION_ERROR", "ENGINE_ERROR", "RELEASE_BLOCKED"];
  return response && response.contract_version === CONTRACT_VERSION
    && knownStatus.includes(response.status)
    && response.narrative && response.narrative.status === "UNVERIFIED"
    && response.release_gate
    && response.release_gate.should_charge === false
    && response.release_gate.formal_report_persistence_allowed === false
    && response.release_gate.closed_beta_allowed === false
    && response.release_gate.narrative_release_status === "UNVERIFIED";
}

function revealResult() {
  show(resultPanel, true);
  scrollToElement(resultPanel);
}

function renderError(code, fallbackTitle, safeMessage) {
  const mapped = ERROR_MESSAGES[code] || [fallbackTitle || "响应格式异常", "未展示任何结果，请检查本地服务后重试。"];
  const message = SAFE_SERVER_MESSAGE_CODES.has(code) && typeof safeMessage === "string" && safeMessage.length > 0
    ? safeMessage
    : mapped[1];
  show(byId("result-placeholder"), false);
  show(byId("result-content"), false);
  show(byId("result-error"), true);
  setText("result-error-title", mapped[0]);
  setText("result-error-text", message);
  revealResult();
  byId("result-error-title").focus({ preventScroll: true });
}

function addDetail(label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const detail = document.createElement("dd");
  term.textContent = label;
  detail.textContent = value;
  wrapper.append(term, detail);
  byId("detail-list").append(wrapper);
}

function hexagram(prefix, item) {
  setText(`${prefix}-symbol`, item.symbol);
  setText(`${prefix}-name`, item.name);
  setText(`${prefix}-number`, `文王卦序 · 第 ${item.king_wen_number} 卦`);
}

function renderSuccess(response) {
  if (!response.deterministic_result || !Array.isArray(response.errors) || response.errors.length !== 0) {
    renderError(null, "响应格式异常");
    return;
  }
  const result = response.deterministic_result;
  const conclusion = result.deterministic_conclusion.conclusion_level;
  const evidence = result.evidence_summary;
  show(byId("result-placeholder"), false);
  show(byId("result-error"), false);
  show(byId("result-content"), true);
  setText("result-question", `“${response.question_text}”`);
  setText("conclusion-level", CONCLUSION_LABELS[conclusion] || "证据不足");
  setText("conclusion-code", conclusion);
  setText("engine-source", response.audit.calculation_source);
  setText("knowledge-mode", evidence.knowledge_mode);
  setText("evidence-types", evidence.evidence_types.join("、"));
  hexagram("base", result.base_hexagram);
  hexagram("mutual", result.mutual_hexagram);
  hexagram("changed", result.changed_hexagram);
  byId("detail-list").replaceChildren();
  addDetail("动爻", `第 ${result.moving_line} 爻`);
  addDetail("体卦", result.body_use.body_trigram);
  addDetail("初始用卦", result.body_use.initial_use_trigram);
  addDetail("变化用卦", result.body_use.changed_use_trigram);
  addDetail("初始体用关系", RELATION_LABELS[result.body_use.initial_relation] || result.body_use.initial_relation);
  addDetail("变化体用关系", RELATION_LABELS[result.body_use.changed_relation] || result.body_use.changed_relation);
  addDetail("五行", `体：${result.five_elements.body}　初用：${result.five_elements.initial_use}　变用：${result.five_elements.changed_use}`);
  addDetail("旺衰", `体：${STRENGTH_LABELS[result.seasonal_strength.body]}　初用：${STRENGTH_LABELS[result.seasonal_strength.initial_use]}　变用：${STRENGTH_LABELS[result.seasonal_strength.changed_use]}`);
  addDetail("节气 / 月支", `${result.seasonal_strength.solar_term} / ${result.seasonal_strength.month_branch}`);
  setText("evidence-count", `${evidence.count} 条`);
  setText("knowledge-count", `${evidence.approved_knowledge_items_used} 条`);
  setText("knowledge-label", KNOWLEDGE_MODE_LABELS[evidence.knowledge_mode] || "仅依据程序规则");
  setText("evidence-summary", `程序规则证据 ${evidence.count} 条，已批准知识 ${evidence.approved_knowledge_items_used} 条。`);
  byId("technical-details").open = false;
  revealResult();
  byId("result-title").focus({ preventScroll: true });
}

function resetExperience() {
  form.reset();
  question.value = "";
  setText("question-count", "0 / 500");
  clearFormError();
  show(byId("result-content"), false);
  show(byId("result-error"), false);
  show(resultPanel, false);
  byId("technical-details").open = false;
  scrollToElement(byId("question-section"));
  question.focus({ preventScroll: true });
}

async function submit(event) {
  event.preventDefault();
  clearFormError();
  const error = validateInput();
  if (error) {
    setText("form-error", error.message);
    show(byId("form-error"), true);
    error.focus.focus();
    return;
  }
  submitButton.disabled = true;
  show(loadingStatus, true);
  try {
    const response = await fetch("/api/v1/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRequest()),
      cache: "no-store",
    });
    const payload = await response.json();
    if (!validEnvelope(payload)) {
      renderError(null, "响应格式异常");
    } else if (payload.status === "SUCCESS") {
      renderSuccess(payload);
    } else {
      const responseError = Array.isArray(payload.errors) && payload.errors[0] ? payload.errors[0] : null;
      renderError(responseError && responseError.error_code, "计算未完成", responseError && responseError.message);
    }
  } catch (_error) {
    renderError(null, "本地服务暂不可用");
  } finally {
    submitButton.disabled = false;
    show(loadingStatus, false);
  }
}

question.addEventListener("input", () => {
  setText("question-count", `${question.value.length} / 500`);
  if (question.getAttribute("aria-invalid") === "true") clearFormError();
});
[1, 2, 3].forEach((index) => byId(`number-${index}`).addEventListener("input", (event) => {
  if (event.currentTarget.getAttribute("aria-invalid") === "true") clearFormError();
}));
["ack-deterministic", "ack-narrative"].forEach((id) => byId(id).addEventListener("change", (event) => {
  if (event.currentTarget.getAttribute("aria-invalid") === "true") clearFormError();
}));
form.addEventListener("submit", submit);
byId("reset-button").addEventListener("click", resetExperience);
byId("error-back-button").addEventListener("click", () => {
  scrollToElement(byId("question-section"));
  question.focus({ preventScroll: true });
});

const preview = new URLSearchParams(window.location.search).get("preview");
if (preview === "engine-error") {
  renderError("ENGINE_ERROR");
} else if (preview === "validation-error") {
  question.value = "   ";
  markFieldInvalid(question);
  setText("question-count", "3 / 500");
  setText("form-error", "请输入一个 1 至 500 个字符的具体问题，不能只填写空格。");
  show(byId("form-error"), true);
}
