type TransportPayload = {
  error_code?: string;
  not_submitted?: boolean;
  terminal?: boolean;
  retry_after_seconds?: number;
};

type TransportOptions = {
  request?: typeof fetch;
  wait?: (ms: number) => Promise<void>;
  now?: () => number;
  active?: () => boolean;
  onWaiting?: (seconds: number) => void;
};

function retryDelay(response: Response, payload: TransportPayload, fallback: number, now: number): number {
  const header = response.headers.get("retry-after");
  const seconds = header ? (/^\d+$/.test(header) ? Number(header) : (Date.parse(header) - now) / 1000)
    : payload.retry_after_seconds;
  return typeof seconds === "number" && Number.isFinite(seconds) ? Math.max(1, seconds) : fallback;
}

/** Retry only an explicit pre-dispatch wake-up rejection. Ambiguous POSTs are never replayed. */
export async function submitDirectReading(body: string, options: TransportOptions = {}): Promise<Response> {
  const request = options.request ?? fetch;
  const wait = options.wait ?? (ms => new Promise(resolve => setTimeout(resolve, ms)));
  const now = options.now ?? Date.now;
  const deadline = now() + 150_000;
  for (let attempt = 0; ; attempt++) {
    if (options.active?.() === false) throw new Error("Task changed");
    const response = await request("/api/direct-reading/v2", {
      method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store", body,
      signal: AbortSignal.timeout(100_000),
    });
    const payload = await response.clone().json().catch(() => ({})) as TransportPayload;
    const waking = response.status === 503 && payload.not_submitted === true &&
      ["ENGINE_WAKING", "ENGINE_RATE_LIMITED"].includes(payload.error_code ?? "");
    const seconds = retryDelay(response, payload, 3, now());
    if (!waking || attempt >= 4 || now() + seconds * 1000 >= deadline) return response;
    options.onWaiting?.(seconds);
    await wait(seconds * 1000);
  }
}

/** GET-only recovery preserves the original job and honours upstream backoff. */
export async function queryDirectReading(requestId: string, options: TransportOptions = {}): Promise<Response> {
  const request = options.request ?? fetch;
  const wait = options.wait ?? (ms => new Promise(resolve => setTimeout(resolve, ms)));
  const now = options.now ?? Date.now;
  const deadline = now() + 120_000;
  for (let attempt = 0; ; attempt++) {
    if (options.active?.() === false) throw new Error("Task changed");
    let response: Response | undefined;
    let failure: unknown;
    let seconds = Math.min(12, 3 * 2 ** attempt);
    try {
      response = await request(`/api/direct-reading/v2?request_id=${encodeURIComponent(requestId)}`, {
        cache: "no-store", signal: AbortSignal.timeout(25_000),
      });
      const payload = await response.clone().json().catch(() => null) as TransportPayload | null;
      if (payload?.terminal || (payload && response.status !== 429 && response.status < 500)) return response;
      seconds = retryDelay(response, payload ?? {}, seconds, now());
    } catch (error) { failure = error; }
    if (attempt >= 3 || now() + seconds * 1000 >= deadline) {
      if (response) return response;
      throw failure;
    }
    options.onWaiting?.(seconds);
    await wait(seconds * 1000);
  }
}

export function directReadingProgress(stage: string | undefined): string {
  switch (stage) {
    case "CASTING": return "正在按你取的三个数成卦。";
    case "CAST_READY": return "卦象已成，正在准备详细解卦。";
    case "MODEL_REQUESTED": return "正在结合你的问题梳理解卦，请稍候。";
    case "MODEL_STREAMING": return "正在撰写详细解卦，完成后即可查看。";
    case "MODEL_COMPLETED":
    case "VALIDATING": return "正文已生成，正在核对内容。";
    default: return "卦象已成，详细解卦正在生成。";
  }
}
