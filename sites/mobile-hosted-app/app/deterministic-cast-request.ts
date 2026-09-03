export type DeterministicCastAttempt<TPayload> = {
  request: Response;
  payload: TPayload;
};

type DeterministicCastRequestOptions = {
  fetchResult: () => Promise<Response>;
  sleep: (milliseconds: number) => Promise<void>;
  onRetry?: (attempt: number) => void;
  maxAttempts?: number;
};

export async function requestDeterministicCast<TPayload>({
  fetchResult,
  sleep,
  onRetry = () => undefined,
  maxAttempts = 3,
}: DeterministicCastRequestOptions): Promise<DeterministicCastAttempt<TPayload>> {
  const attempts = Math.max(1, Math.floor(maxAttempts));
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const request = await fetchResult();
    const payload = await request.json() as TPayload;
    if (request.status !== 503 || attempt === attempts - 1) return { request, payload };
    onRetry(attempt + 1);
    await sleep(1_500);
  }
  throw new Error("本次未能完成排盘。");
}
