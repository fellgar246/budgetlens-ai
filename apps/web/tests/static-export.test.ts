import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

function walkPages(dir: string): string[] {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const next = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkPages(next));
    } else if (entry.name === "page.tsx" || entry.name === "layout.tsx") {
      files.push(next);
    }
  }
  return files;
}

describe("static production build", () => {
  it("keeps Next.js on static export", () => {
    const config = readFileSync(path.join(process.cwd(), "next.config.ts"), "utf8");
    expect(config).toContain('output: "export"');
    expect(config).not.toContain("getServerSideProps");
    expect(config).not.toContain("force-dynamic");
  });

  it("does not register a service worker that could cache tenant responses", () => {
    const root = path.join(process.cwd(), "src");
    const files = walkPages(root);
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/serviceWorker|navigator\.serviceWorker/);
    }
  });

  it("does not declare server-only data functions in app routes", () => {
    const pages = walkPages(path.join(process.cwd(), "src/app"));
    expect(pages.length).toBeGreaterThan(5);
    for (const file of pages) {
      const source = readFileSync(file, "utf8");
      expect(source, file).not.toMatch(/getServerSideProps|cookies\(|headers\(|unstable_noStore/);
      expect(source, file).not.toMatch(/export const dynamic\s*=\s*["']force-dynamic["']/);
    }
  });
});
