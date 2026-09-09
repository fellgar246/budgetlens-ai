import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { MembersPage } from "@/features/settings/MembersPage";
import { copy } from "@/lib/copy";

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/members",
  useRouter: () => ({ replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const patchMembership = vi.fn().mockResolvedValue({ data: {} });

vi.mock("@budgetlens/api-client", async () => {
  const actual =
    await vi.importActual<typeof import("@budgetlens/api-client")>("@budgetlens/api-client");
  return {
    ...actual,
    listMemberships: vi.fn().mockResolvedValue({
      data: {
        items: [
          {
            id: "m-1",
            organization_id: "org-1",
            user_id: "user-2",
            role: "viewer",
            status: "active",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ],
        page: { next_cursor: null, has_more: false },
      },
    }),
    createMembership: vi.fn(),
    patchMembership: (...args: unknown[]) => patchMembership(...args),
  };
});

vi.mock("@/features/session/SessionProvider", () => ({
  useSession: () => ({
    userId: "admin-1",
    organizationId: "org-1",
    authMode: "dev",
    users: [{ id: "user-2", display_name: "Pat Dual", email: "pat@example.com" }],
    capabilities: { can_manage_members: true },
    generation: 1,
  }),
}));

describe("MembersPage", () => {
  it("asks for confirmation before disabling a member", async () => {
    const user = userEvent.setup();
    render(<MembersPage />);
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: copy.disableMember }));
    expect(screen.getByText(copy.confirmDisableMember)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: copy.confirmDisableMemberAction }));
    expect(patchMembership).toHaveBeenCalledWith(expect.any(String), expect.anything(), "m-1", {
      status: "disabled",
    });
  });
});
