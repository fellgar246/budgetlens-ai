import { describe, expect, it, vi } from "vitest";

import { requiredMappingComplete, sampleValuesForHeader } from "@/lib/import-mapping";
import { isImportJobSettled, pollWithBackoff } from "@/lib/poll";

describe("import mapping helpers", () => {
  it("requires every canonical required field", () => {
    expect(
      requiredMappingComplete({
        period: "period",
        account_code: "account",
        department_code: "dept",
        amount: "amount",
        currency: "currency",
      }),
    ).toBe(true);
    expect(requiredMappingComplete({ period: "period", amount: "amount" })).toBe(false);
  });

  it("shows distinct sample values from the uploaded rows", () => {
    const sample = sampleValuesForHeader(
      [{ account_code: "0610" }, { account_code: "0610" }, { account_code: "6100" }],
      "account_code",
    );
    expect(sample).toBe("0610, 6100");
  });
});

describe("import polling", () => {
  it("returns immediately when the job is already settled", async () => {
    const load = vi.fn().mockResolvedValue({ status: "ready" });
    const result = await pollWithBackoff(load, (job: { status: string }) =>
      isImportJobSettled(job.status),
    );
    expect(result.status).toBe("ready");
    expect(load).toHaveBeenCalledTimes(1);
  });

  it("backs off until the job leaves processing", async () => {
    const load = vi
      .fn()
      .mockResolvedValueOnce({ status: "processing" })
      .mockResolvedValueOnce({ status: "applied" });
    const result = await pollWithBackoff(
      load,
      (job: { status: string }) => isImportJobSettled(job.status),
      { initialDelayMs: 5, maxDelayMs: 5 },
    );
    expect(result.status).toBe("applied");
    expect(load).toHaveBeenCalledTimes(2);
  });
});
