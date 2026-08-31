import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { SessionProvider } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("DashboardPage", () => {
  it("asks for a local session before showing the summary", () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    });
    render(
      <SessionProvider>
        <DashboardPage />
      </SessionProvider>,
    );
    expect(screen.getByText(copy.sessionNeededGeneric)).toBeInTheDocument();
  });
});
