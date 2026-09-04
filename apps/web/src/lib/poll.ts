export type PollOptions = {
  initialDelayMs?: number;
  maxDelayMs?: number;
  maxWaitMs?: number;
  factor?: number;
  signal?: AbortSignal;
  onWait?: (elapsedMs: number) => void;
};

export const IMPORT_SETTLED = new Set(["ready", "invalid", "applied", "cancelled", "failed"]);

export function isImportJobSettled(status: string): boolean {
  return IMPORT_SETTLED.has(status);
}

export async function pollWithBackoff<T>(
  load: () => Promise<T>,
  isDone: (value: T) => boolean,
  options: PollOptions = {},
): Promise<T> {
  const initial = options.initialDelayMs ?? 400;
  const maxDelay = options.maxDelayMs ?? 4000;
  const maxWait = options.maxWaitMs ?? 120_000;
  const factor = options.factor ?? 2;
  const started = Date.now();
  let delay = initial;
  let value = await load();
  if (isDone(value)) {
    return value;
  }
  while (Date.now() - started < maxWait) {
    if (options.signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }
    options.onWait?.(Date.now() - started);
    await sleep(delay, options.signal);
    value = await load();
    if (isDone(value)) {
      return value;
    }
    delay = Math.min(maxDelay, Math.round(delay * factor));
  }
  throw new Error("POLL_TIMEOUT");
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(resolve, ms);
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}
