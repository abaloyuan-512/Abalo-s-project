"use strict";

const CONTRACT_VERSION = "SITES_MEIHUA_API_CONTRACT_V1";
const ERROR_MESSAGES = {
  INVALID_REQUEST: ["输入未通过校验", "请检查问题长度、时间与确认项后重试。"],
  EMPTY_QUESTION: ["还没有具体问题", "请输入一个非空白问题。"],
  INVALID_NUMBER_COUNT: ["数字数量不正确", "请完整输入三个数字。"],
  INVALID_NUMBER_TYPE: ["数字不在有效范围", "三个数字都必须是 1 至 999 的整数。"],
  MULTIPLE_QUESTIONS_NOT_ALLOWED: ["一次只处理一个问题", "请保留一个最想厘清的问题。"],
  CLIENT_CALCULATION_NOT_ACCEPTED: ["请求包含不受支持内容", "浏览器只提交原始输入，卦象由 Python 引擎计算。"],
  ENGINE_ERROR: ["确定性引擎暂时未完成计算", "当前没有生成结果，请稍后在本机重试。"],
};
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

const byId = (id) => document.getElementById(id);
const form = byId("question-form");
const question = byId("question");
const submitButton = byId("submit-button");
const loadingStatus = byId("loading-status");

function setText(id, value) { byId(id).textContent = String(value); }
function show(element, visible) { element.hidden = !visible; }

function createRequestId() {
  const random = globalThis.crypto && typeof globalThis.crypto.randomUUID === "function"
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  return `phase3b-local-${random}`;
}

function rawNumbers() {
  return [1, 2, 3].map((index) => byId(`number-${index}`).value);
}

function validateInput() {
  const rawQuestion = question.value;
  if (rawQuestion.length < 1 || rawQuestion.length > 500 || rawQuestion.trim().length === 0) {
    return "问题必须包含 1 至 500 个原始字符，且不能只有空白。";
  }
  const numbers = rawNumbers().map(Number);
  if (numbers.some((value) => !Number.isInteger(value) || value < 1 || value > 999)) {
    return "请填写三个 1 至 999 的整数。";
  }
  if (!byId("ack-deterministic").checked || !byId("ack-narrative").checked) {
    return "请先确认确定性结果与 AI 解释未验证边界。";
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

function renderError(code, fallbackTitle) {
  const mapped = ERROR_MESSAGES[code] || [fallbackTitle || "响应格式异常", "未展示任何确定性结果，请检查本地服务后重试。"];
  show(byId("result-placeholder"), false);
  show(byId("result-content"), false);
  show(byId("result-error"), true);
  setText("result-error-title", mapped[0]);
  setText("result-error-text", mapped[1]);
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
  setText(`${prefix}-number`, `第 ${item.king_wen_number} 卦`);
}

function renderSuccess(response) {
  if (!response.deterministic_result || !Array.isArray(response.errors) || response.errors.length !== 0) {
    renderError(null, "响应格式异常");
    return;
  }
  const result = response.deterministic_result;
  show(byId("result-placeholder"), false);
  show(byId("result-error"), false);
  show(byId("result-content"), true);
  setText("result-question", response.question_text);
  hexagram("base", result.base_hexagram);
  hexagram("mutual", result.mutual_hexagram);
  hexagram("changed", result.changed_hexagram);
  const conclusion = result.deterministic_conclusion.conclusion_level;
  setText("conclusion-level", CONCLUSION_LABELS[conclusion] || conclusion);
  setText("conclusion-code", conclusion);
  byId("detail-list").replaceChildren();
  addDetail("输入数字", result.input_numbers.join(" · "));
  addDetail("动爻", `第 ${result.moving_line} 爻`);
  addDetail("体卦", result.body_use.body_trigram);
  addDetail("初始用卦", result.body_use.initial_use_trigram);
  addDetail("变化用卦", result.body_use.changed_use_trigram);
  addDetail("初始体用关系", RELATION_LABELS[result.body_use.initial_relation] || result.body_use.initial_relation);
  addDetail("变化体用关系", RELATION_LABELS[result.body_use.changed_relation] || result.body_use.changed_relation);
  addDetail("五行", `体 ${result.five_elements.body} · 初用 ${result.five_elements.initial_use} · 变用 ${result.five_elements.changed_use}`);
  addDetail("旺衰", `体 ${STRENGTH_LABELS[result.seasonal_strength.body]} · 初用 ${STRENGTH_LABELS[result.seasonal_strength.initial_use]} · 变用 ${STRENGTH_LABELS[result.seasonal_strength.changed_use]}`);
  addDetail("节气 / 月支", `${result.seasonal_strength.solar_term} / ${result.seasonal_strength.month_branch}`);
  const evidence = result.evidence_summary;
  setText("evidence-summary", `${evidence.count} 条程序 Evidence · ${evidence.evidence_types.join("、")} · 知识模式 ${evidence.knowledge_mode} · 已批准知识 ${evidence.approved_knowledge_items_used} 条`);
}

async function submit(event) {
  event.preventDefault();
  show(byId("form-error"), false);
  const error = validateInput();
  if (error) {
    setText("form-error", error);
    show(byId("form-error"), true);
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
      const errorCode = Array.isArray(payload.errors) && payload.errors[0] ? payload.errors[0].error_code : null;
      renderError(errorCode, "计算未完成");
    }
  } catch (_error) {
    renderError(null, "本地服务暂不可用");
  } finally {
    submitButton.disabled = false;
    show(loadingStatus, false);
  }
}

question.addEventListener("input", () => setText("question-count", `${question.value.length} / 500`));
form.addEventListener("submit", submit);

const preview = new URLSearchParams(window.location.search).get("preview");
if (preview === "engine-error") {
  renderError("ENGINE_ERROR");
} else if (preview === "validation-error") {
  question.value = "   ";
  setText("question-count", "3 / 500");
  setText("form-error", "问题必须包含 1 至 500 个原始字符，且不能只有空白。");
  show(byId("form-error"), true);
}
