export type PersonalizedTaskPayload = {
  status?: string;
  error?: string | null;
  personalized_reading?: unknown;
  [key: string]: unknown;
};

type PersonalizedTaskResponse = {
  ok: boolean;
  status: number;
  json(): Promise<PersonalizedTaskPayload>;
};

export class PersonalizedPollError extends Error {
  readonly requestId: string;
  readonly terminal: boolean;

  constructor(message: string, requestId: string, terminal: boolean) {
    super(message);
    this.name = "PersonalizedPollError";
    this.requestId = requestId;
    this.terminal = terminal;
  }
}

const RUNNING_STATUSES = new Set(["PENDING", "QUEUED", "RUNNING"]);

export async function pollPersonalizedTask(
  requestId: string,
  {
    fetchResult,
    sleep,
    cancelled = () => false,
    maxAttempts = 720,
    intervalMs = 2_500,
  }: {
    fetchResult: () => Promise<PersonalizedTaskResponse>;
    sleep: (milliseconds: number) => Promise<void>;
    cancelled?: () => boolean;
    maxAttempts?: number;
    intervalMs?: number;
  },
): Promise<PersonalizedTaskPayload | null> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (cancelled()) return null;
    if (attempt > 0) await sleep(intervalMs);

    let response: PersonalizedTaskResponse;
    try {
      response = await fetchResult();
    } catch {
      throw new PersonalizedPollError(
        "查询连接暂时中断。任务仍保留，刷新页面会继续查询，不会重复生成。",
        requestId,
        false,
      );
    }

    if (response.status === 202 || response.status === 503) continue;

    let payload: PersonalizedTaskPayload;
    try {
      payload = await response.json();
    } catch {
      throw new PersonalizedPollError("查询生成结果时收到异常响应。", requestId, false);
    }

    if (response.status === 404) {
      throw new PersonalizedPollError(
        "生成任务尚未建立，请重新填写后再次点击观卦；未找到任务不会产生模型费用。",
        requestId,
        true,
      );
    }
    if (!response.ok) {
      throw new PersonalizedPollError(payload.error || "查询生成结果时出现异常。", requestId, response.status < 500);
    }

    const status = String(payload.status || "").toUpperCase();
    if (RUNNING_STATUSES.has(status)) continue;
    if (status !== "SUCCESS" || !payload.personalized_reading) {
      throw new PersonalizedPollError(
        payload.error || "本次解读没有通过检查，也不会自动重新生成。",
        requestId,
        true,
      );
    }
    return payload;
  }

  throw new PersonalizedPollError(
    "生成时间超过三十分钟。任务仍保留，刷新页面会继续查询，不会重复生成。",
    requestId,
    false,
  );
}
