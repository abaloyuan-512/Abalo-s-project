import { writeFile } from "node:fs/promises";

const pages = await fetch("http://127.0.0.1:9225/json").then((response) => response.json());
const page = pages.find((entry) => entry.type === "page" && entry.url.includes("127.0.0.1:4177"));
if (!page) throw new Error("Local preview page was not found on the approved Chrome debugging port.");

const socket = new WebSocket(page.webSocketDebuggerUrl);
const pending = new Map();
let nextId = 1;
const runtimeErrors = [];
const logErrors = [];

socket.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  }
  if (message.method === "Runtime.exceptionThrown") runtimeErrors.push(message.params);
  if (message.method === "Log.entryAdded" && message.params?.entry?.level === "error") {
    logErrors.push(message.params.entry);
  }
});

await new Promise((resolve, reject) => {
  socket.addEventListener("open", resolve, { once: true });
  socket.addEventListener("error", reject, { once: true });
});

function command(method, params = {}) {
  const id = nextId++;
  socket.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

await command("Page.enable");
await command("Runtime.enable");
await command("Log.enable");
await command("Emulation.setDeviceMetricsOverride", {
  width: 1914,
  height: 1018,
  deviceScaleFactor: 1,
  mobile: false,
});
await command("Page.reload", { ignoreCache: true });
await wait(2600);
await command("Runtime.evaluate", {
  expression: `(() => {
    document.documentElement.classList.remove('entry-scroll-locked');
    document.body.classList.remove('entry-scroll-locked');
    const inquiry = document.querySelector('#inquiry');
    if (!inquiry) return { ok: false };
    inquiry.hidden = false;
    inquiry.classList.add('is-visible');
    inquiry.scrollIntoView({ block: 'start' });
    window.scrollBy(0, -68);
    return {
      ok: true,
      top: Math.round(inquiry.getBoundingClientRect().top),
      canvases: [...inquiry.querySelectorAll('canvas')].map((canvas) => ({
        width: canvas.width,
        height: canvas.height,
        webgl: Boolean(canvas.getContext('webgl')),
      })),
    };
  })()`,
  returnByValue: true,
});
await wait(5600);

async function capture(path) {
  const result = await command("Page.captureScreenshot", {
    format: "png",
    captureBeyondViewport: false,
    fromSurface: true,
  });
  await writeFile(path, Buffer.from(result.data, "base64"));
}

await capture("qa/inquiry-cloudfall-v6-browser-t1.png");
await wait(8000);
await capture("qa/inquiry-cloudfall-v6-browser-t2.png");

const state = await command("Runtime.evaluate", {
  expression: `(() => {
    const inquiry = document.querySelector('#inquiry');
    return {
      hash: location.hash,
      scrollY: Math.round(scrollY),
      inquiryTop: inquiry ? Math.round(inquiry.getBoundingClientRect().top) : null,
      canvasCount: inquiry ? inquiry.querySelectorAll('canvas').length : 0,
      textareaVisible: Boolean(document.querySelector('#primary-question')?.offsetParent),
    };
  })()`,
  returnByValue: true,
});

const interaction = await command("Runtime.evaluate", {
  expression: `(async () => {
    const textarea = document.querySelector('#primary-question');
    const advance = document.querySelector('.inquiry-advance button');
    const count = document.querySelector('#question-count');
    if (!textarea || !advance || !count) return { ok: false };
    const setValue = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setValue.call(textarea, '我是否应该继续投入这次合作？');
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    const result = {
      ok: true,
      value: textarea.value,
      count: count.textContent,
      advanceDisabled: advance.disabled,
      advanceLabel: advance.textContent.trim(),
    };
    setValue.call(textarea, '');
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    return result;
  })()`,
  awaitPromise: true,
  returnByValue: true,
});

process.stdout.write(JSON.stringify({
  state: state.result.value,
  interaction: interaction.result.value,
  runtimeErrorCount: runtimeErrors.length,
  logErrorCount: logErrors.length,
}, null, 2));
socket.close();
