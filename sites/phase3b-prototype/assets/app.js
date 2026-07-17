"use strict";

const CONTRACT_VERSION = "SITES_MEIHUA_API_CONTRACT_V2";
const GOALS_BY_DOMAIN = {
  WORK_CAREER: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "OBSERVE_VERIFY_SIGNALS"],
  PROJECT_COOPERATION: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  RELATIONSHIP_COMMUNICATION: ["PLAN_NEXT_STEP", "PREPARE_COMMUNICATION", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
  PERSONAL_PLANNING: ["IDENTIFY_OBSTACLES", "PLAN_NEXT_STEP", "ADJUST_COMMITMENT_BOUNDARIES", "OBSERVE_VERIFY_SIGNALS"],
};
const DOMAIN_LABELS = {
  WORK_CAREER: "工作与职业发展",
  PROJECT_COOPERATION: "项目与合作推进",
  RELATIONSHIP_COMMUNICATION: "关系与沟通",
  PERSONAL_PLANNING: "个人规划",
};
const GOAL_LABELS = {
  IDENTIFY_OBSTACLES: "识别阻力与支持",
  PLAN_NEXT_STEP: "规划下一步行动",
  PREPARE_COMMUNICATION: "准备现实沟通",
  ADJUST_COMMITMENT_BOUNDARIES: "调整投入与边界",
  OBSERVE_VERIFY_SIGNALS: "观察并核实现实信号",
};
const HORIZON_LABELS = {
  CURRENT: "当前阶段",
  NEXT_30_DAYS: "未来30天",
  NEXT_QUARTER: "未来一个季度",
  NEXT_6_MONTHS: "未来6个月",
};
const ERROR_MESSAGES = {
  INVALID_REQUEST: ["结构化选择未通过校验", "请检查领域、目标、时间、三个数字和确认项。"],
  INVALID_NUMBER_COUNT: ["数字尚未填写完整", "请完整输入三个数字。"],
  INVALID_NUMBER_TYPE: ["数字不在有效范围", "三个数字都必须是 1 至 999 的整数。"],
  CLIENT_INPUT_NOT_ACCEPTED: ["请求包含不受支持的内容", "页面只提交结构化选择和原始数字。"],
  ENGINE_ERROR: ["暂时无法生成结构", "当前没有生成结果，请稍后在本机重试。"],
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
const KNOWLEDGE_MODE_LABELS = {
  PROGRAM_ONLY: "仅依据程序规则",
  PROGRAM_AND_APPROVED_KNOWLEDGE: "程序规则与已批准知识",
};

const byId = (id) => document.getElementById(id);
const form = byId("question-form");
const domain = byId("question-domain");
const goal = byId("decision-goal");
const horizon = byId("time-horizon");
const submitButton = byId("submit-button");
const loadingStatus = byId("loading-status");
const resultPanel = byId("result-panel");
const formError = byId("form-error");
const structuredFields = [domain, goal, horizon];
const numberFields = [1, 2, 3].map((index) => byId(`number-${index}`));
const acknowledgementFields = [byId("ack-deterministic"), byId("ack-narrative"), byId("ack-structured")];
const validatedFields = [...structuredFields, ...numberFields, ...acknowledgementFields];

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
  return `phase3g-local-${random}`;
}

function rawNumbers() { return numberFields.map((field) => field.value); }
function clearNumbers() { numberFields.forEach((field) => { field.value = ""; }); }

function errorDescriptionIds(field) {
  return (field.getAttribute("aria-describedby") || "").split(/\s+/).filter((id) => id && id !== formError.id);
}

function clearFieldError(field) {
  field.setAttribute("aria-invalid", "false");
  const ids = errorDescriptionIds(field);
  if (ids.length) field.setAttribute("aria-describedby", ids.join(" "));
  else field.removeAttribute("aria-describedby");
}

function clearInvalidState() { validatedFields.forEach(clearFieldError); }

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

function refreshSummary() {
  setText("summary-domain", DOMAIN_LABELS[domain.value] || "尚未选择");
  setText("summary-goal", GOAL_LABELS[goal.value] || "尚未选择");
  setText("summary-horizon", HORIZON_LABELS[horizon.value] || "尚未选择");
  submitButton.disabled = !domain.value || !goal.value || !horizon.value;
}

function populateGoals() {
  const allowed = GOALS_BY_DOMAIN[domain.value] || [];
  goal.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = allowed.length ? "请选择决策目标" : "请先选择领域";
  goal.append(placeholder);
  allowed.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = GOAL_LABELS[value];
    goal.append(option);
  });
  goal.disabled = allowed.length === 0;
}

function validateInput() {
  clearInvalidState();
  const missingStructured = structuredFields.find((field) => !field.value);
  if (missingStructured) {
    markFieldInvalid(missingStructured);
    return { message: "请完整选择领域、决策目标和时间窗口。", focus: missingStructured };
  }
  const numbers = rawNumbers().map(Number);
  const invalidIndex = numbers.findIndex((value, index) => rawNumbers()[index] === "" || !Number.isInteger(value) || value < 1 || value > 999);
  if (invalidIndex !== -1) {
    markFieldInvalid(numberFields[invalidIndex]);
    return { message: "请完整填写三个 1 至 999 的整数。", focus: numberFields[invalidIndex] };
  }
  const missingAck = acknowledgementFields.find((field) => !field.checked);
  if (missingAck) {
    markFieldInvalid(missingAck);
    return { message: "请先确认结构化问题、结果边界与当前版本的解读范围。", focus: missingAck };
  }
  return null;
}

function buildRequest() {
  return {
    contract_version: CONTRACT_VERSION,
    request_id: createRequestId(),
    question_domain: domain.value,
    decision_goal: goal.value,
    time_horizon: horizon.value,
    numbers: rawNumbers().map(Number),
    locale: "zh-CN",
    client_timestamp: new Date().toISOString(),
    user_acknowledgements: {
      deterministic_only: true,
      narrative_unverified: true,
      structured_question_confirmed: true,
    },
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

function renderError(code, fallbackTitle) {
  const mapped = ERROR_MESSAGES[code] || [fallbackTitle || "响应格式异常", "未展示任何结果，请检查本地服务后重试。"];
  show(byId("result-placeholder"), false);
  show(byId("result-content"), false);
  show(byId("result-error"), true);
  setText("result-error-title", mapped[0]);
  setText("result-error-text", mapped[1]);
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

function renderTextItems(targetId, items) {
  const target = byId(targetId);
  target.replaceChildren();
  items.forEach((item) => {
    const article = document.createElement("article");
    const title = document.createElement("h4");
    const text = document.createElement("p");
    title.textContent = item.title;
    text.textContent = item.text;
    article.append(title, text);
    target.append(article);
  });
}

function renderActions(items) {
  const target = byId("action-plan");
  target.replaceChildren();
  items.forEach((item) => {
    const row = document.createElement("li");
    const title = document.createElement("h4");
    const action = document.createElement("p");
    const why = document.createElement("small");
    title.textContent = item.title;
    action.textContent = item.action;
    why.textContent = `为什么：${item.why}`;
    row.append(title, action, why);
    target.append(row);
  });
}

function renderStringList(targetId, items) {
  const target = byId(targetId);
  target.replaceChildren();
  items.forEach((item) => {
    const row = document.createElement("li");
    row.textContent = item;
    target.append(row);
  });
}

function validMentorReport(report) {
  return report && report.template_version === "SITES_MENTOR_REPORT_V1"
    && typeof report.opening === "string"
    && Array.isArray(report.reading_guide)
    && Array.isArray(report.reasoning)
    && Array.isArray(report.action_plan)
    && Array.isArray(report.cautions)
    && Array.isArray(report.review_questions)
    && typeof report.boundary_note === "string";
}

function hexagram(prefix, item) {
  setText(`${prefix}-symbol`, item.symbol);
  setText(`${prefix}-name`, item.name);
  setText(`${prefix}-number`, `文王卦序 · 第 ${item.king_wen_number} 卦`);
}

function renderSuccess(response) {
  if (!response.deterministic_result || !validMentorReport(response.deterministic_result.mentor_report) || typeof response.normalized_question !== "string" || !Array.isArray(response.errors) || response.errors.length !== 0) {
    renderError(null, "响应格式异常");
    return;
  }
  const result = response.deterministic_result;
  const mentor = result.mentor_report;
  const conclusion = result.deterministic_conclusion.conclusion_level;
  const evidence = result.evidence_summary;
  show(byId("result-placeholder"), false);
  show(byId("result-error"), false);
  show(byId("result-content"), true);
  setText("result-question", `服务端规范化问题：“${response.normalized_question}”`);
  setText("conclusion-level", CONCLUSION_LABELS[conclusion] || "证据不足");
  setText("mentor-opening", mentor.opening);
  renderTextItems("reading-guide", mentor.reading_guide);
  renderTextItems("reasoning-list", mentor.reasoning);
  renderActions(mentor.action_plan);
  renderStringList("caution-list", mentor.cautions);
  renderStringList("review-list", mentor.review_questions);
  setText("mentor-boundary", mentor.boundary_note);
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
  populateGoals();
  clearNumbers();
  clearFormError();
  refreshSummary();
  show(byId("result-content"), false);
  show(byId("result-error"), false);
  show(resultPanel, false);
  byId("technical-details").open = false;
  scrollToElement(byId("question-section"));
  domain.focus({ preventScroll: true });
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
    const response = await fetch("/api/v2/meihua", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildRequest()),
      cache: "no-store",
    });
    const payload = await response.json();
    if (!validEnvelope(payload)) renderError(null, "响应格式异常");
    else if (payload.status === "SUCCESS") renderSuccess(payload);
    else renderError(Array.isArray(payload.errors) && payload.errors[0] ? payload.errors[0].error_code : null, "计算未完成");
  } catch (_error) {
    renderError(null, "本地服务暂不可用");
  } finally {
    show(loadingStatus, false);
    refreshSummary();
  }
}

domain.addEventListener("change", () => {
  populateGoals();
  clearNumbers();
  clearFormError();
  refreshSummary();
});
[goal, horizon].forEach((field) => field.addEventListener("change", () => {
  clearNumbers();
  clearFormError();
  refreshSummary();
}));
numberFields.forEach((field) => field.addEventListener("input", clearFormError));
acknowledgementFields.forEach((field) => field.addEventListener("change", clearFormError));
form.addEventListener("submit", submit);
byId("reset-button").addEventListener("click", resetExperience);
byId("error-back-button").addEventListener("click", () => {
  scrollToElement(byId("question-section"));
  domain.focus({ preventScroll: true });
});

populateGoals();
refreshSummary();

const preview = new URLSearchParams(window.location.search).get("preview");
if (preview === "engine-error") {
  renderError("ENGINE_ERROR");
} else if (preview === "validation-error") {
  markFieldInvalid(domain);
  setText("form-error", "请完整选择领域、决策目标和时间窗口。");
  show(byId("form-error"), true);
}
