export type PreviewTaskPayload = {
  status?: string;
  error?: string | null;
  personalized_reading?: unknown;
  [key: string]: unknown;
};

type PreviewTaskResponse = {
  ok: boolean;
  status: number;
  json(): Promise<PreviewTaskPayload>;
};

export class PreviewPollError extends Error {
  readonly requestId: string;
  readonly terminal: boolean;

  constructor(message: string, requestId: string, terminal: boolean) {
    super(message);
    this.name = "PreviewPollError";
    this.requestId = requestId;
    this.terminal = terminal;
  }
}

const RUNNING_STATUSES = new Set(["PENDING", "QUEUED", "RUNNING"]);

export async function pollPreviewTask(
  requestId: string,
  {
    fetchResult,
    sleep,
    cancelled = () => false,
    maxAttempts = 144,
    intervalMs = 2_500,
  }: {
    fetchResult: () => Promise<PreviewTaskResponse>;
    sleep: (milliseconds: number) => Promise<void>;
    cancelled?: () => boolean;
    maxAttempts?: number;
    intervalMs?: number;
  },
): Promise<PreviewTaskPayload | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (cancelled()) return null;
    if (attempt > 0) await sleep(intervalMs);

    let response: PreviewTaskResponse;
    try {
      response = await fetchResult();
    } catch {
      throw new PreviewPollError(
        "查询连接暂时中断。任务仍保留，刷新页面会继续查询，不会重复生成。",
        requestId,
        false,
      );
    }

    if (response.status === 202 || response.status === 503) continue;

    let payload: PreviewTaskPayload;
    try {
      payload = await response.json();
    } catch {
      throw new PreviewPollError("查询生成结果时收到异常响应。", requestId, false);
    }

    if (response.status === 404) {
      throw new PreviewPollError(
        "生成任务尚未建立，请重新填写后再次点击生成；未找到任务不会产生模型费用。",
        requestId,
        true,
      );
    }
    if (!response.ok) {
      throw new PreviewPollError(payload.error || "查询生成结果时出现异常。", requestId, response.status < 500);
    }

    const status = String(payload.status || "").toUpperCase();
    if (RUNNING_STATUSES.has(status)) continue;
    if (status !== "SUCCESS" || !payload.personalized_reading) {
      throw new PreviewPollError(
        payload.error || "本次新版解读没有通过检查，也不会自动重试。",
        requestId,
        true,
      );
    }
    return payload;
  }

  throw new PreviewPollError(
    "生成时间超过六分钟。任务仍保留，刷新页面会继续查询，不会重复生成。",
    requestId,
    false,
  );
}
