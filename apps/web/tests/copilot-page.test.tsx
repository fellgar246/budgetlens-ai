import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CopilotPage } from "@/features/copilot/CopilotPage";
import { SessionProvider } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

vi.mock("next/navigation", () => ({
  usePathname: () => "/copilot",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("CopilotPage", () => {
  it("asks for a local session before showing conversations", () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    });
    render(
      <SessionProvider>
        <CopilotPage />
      </SessionProvider>,
    );
    expect(screen.getByText(copy.sessionNeededGeneric)).toBeInTheDocument();
  });
});
