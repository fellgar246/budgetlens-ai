"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

const AUTH_ROUTES = new Set(["/login", "/select-organization"]);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const normalizedPath = (pathname ?? "/").replace(/\/$/, "") || "/";
  const isAuth = AUTH_ROUTES.has(normalizedPath);

  if (isAuth) {
    return (
      <div className="flex min-h-screen flex-col">
        <header className="flex h-14 items-center border-b border-border bg-surface px-4 md:h-16 md:px-8">
          <p className="text-lg font-semibold text-brand-700">BudgetLens</p>
        </header>
        <main id="contenido" tabIndex={-1} className="mx-auto w-full max-w-xl flex-1 px-4 py-8">
          {children}
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <AppSidebar
        open={open}
        collapsed={collapsed}
        onClose={() => setOpen(false)}
        onToggleCollapsed={() => setCollapsed((current) => !current)}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onOpenNavigation={() => setOpen(true)} />
        <main
          id="contenido"
          tabIndex={-1}
          className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-4 md:px-6 md:py-6 lg:px-8 lg:py-8"
        >
          {children}
        </main>
      </div>
    </div>
  );
}
