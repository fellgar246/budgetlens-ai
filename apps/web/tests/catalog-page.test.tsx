import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CatalogPage } from "@/features/catalog/CatalogPage";
import { copy } from "@/lib/copy";

describe("CatalogPage", () => {
  it("asks for a local session before loading data", () => {
    vi.stubGlobal("sessionStorage", {
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
    });
    render(<CatalogPage />);
    expect(screen.getByRole("heading", { name: copy.catalogTitle })).toBeInTheDocument();
    expect(screen.getByText(copy.sessionNeeded)).toBeInTheDocument();
  });
});
