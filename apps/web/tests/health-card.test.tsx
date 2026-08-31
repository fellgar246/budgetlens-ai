import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HealthCard } from "@/features/status/HealthCard";
import { copy } from "@/lib/copy";

describe("HealthCard", () => {
  it("renders the loading skeleton", () => {
    render(<HealthCard state={{ kind: "loading" }} onRetry={() => undefined} />);
    expect(screen.getByLabelText(copy.checking)).toBeInTheDocument();
    expect(screen.getByText(copy.checking)).toBeInTheDocument();
  });

  it("renders a successful health summary", () => {
    render(
      <HealthCard
        state={{
          kind: "success",
          live: "ok",
          database: "ok",
          version: { version: "0.1.0", commit: "abcdef123456", build_time: "2026-08-31T00:00:00Z" },
          checkedAt: "2026-08-31T12:00:00.000Z",
        }}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByRole("heading", { name: copy.healthy })).toBeInTheDocument();
    expect(screen.getByText(copy.healthyDetail)).toBeInTheDocument();
    expect(screen.getByText(copy.available)).toBeInTheDocument();
    expect(screen.getByText(copy.ready)).toBeInTheDocument();
    expect(screen.getByText(/0\.1\.0/)).toBeInTheDocument();
  });

  it("renders an error with a copyable trace id", async () => {
    const user = userEvent.setup();
    const onCopyTrace = vi.fn();
    const onRetry = vi.fn();

    render(
      <HealthCard
        state={{
          kind: "error",
          title: copy.unavailable,
          detail: copy.unavailableDetail,
          traceId: "trace-abc-001",
          live: "error",
          database: "unknown",
          version: null,
          checkedAt: "2026-08-31T12:00:00.000Z",
        }}
        onRetry={onRetry}
        onCopyTrace={onCopyTrace}
      />,
    );

    expect(screen.getByRole("heading", { name: copy.unavailable })).toBeInTheDocument();
    expect(screen.getByText("trace-abc-001")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: copy.copyTrace }));
    expect(onCopyTrace).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: copy.retry }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
