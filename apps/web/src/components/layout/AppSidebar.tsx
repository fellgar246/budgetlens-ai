"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useSession } from "@/features/session/SessionProvider";
import { readStoredFilters, withPathFilters, withTrailingSlash } from "@/lib/analysis-filters";
import { visibleNavGroups } from "@/lib/capabilities";
import { cn } from "@/lib/cn";
import { copy } from "@/lib/copy";

function navHref(href: string, organizationId: string): string {
  if (href === "/dashboard" || href === "/variances" || href === "/copilot") {
    return withPathFilters(href, readStoredFilters(organizationId || null));
  }
  return withTrailingSlash(href);
}

export function AppSidebar({
  open,
  collapsed,
  onClose,
  onToggleCollapsed,
}: {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapsed: () => void;
}) {
  const pathname = usePathname();
  const { capabilities, organizationId } = useSession();
  const groups = visibleNavGroups(capabilities);

  return (
    <>
      <div
        className={cn("fixed inset-0 z-30 bg-[#17202a]/40 lg:hidden", open ? "block" : "hidden")}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col bg-brand-700 text-white transition-[width,transform] duration-200 lg:static lg:translate-x-0",
          collapsed ? "lg:w-[72px]" : "lg:w-[248px]",
          open ? "w-[248px] translate-x-0" : "-translate-x-full w-[248px] lg:translate-x-0",
        )}
      >
        <div className="flex h-14 items-center px-4 md:h-16">
          <p className={cn("text-lg font-semibold tracking-tight", collapsed && "lg:sr-only")}>
            {copy.appName}
          </p>
          {collapsed ? (
            <p
              className="hidden w-full text-center text-lg font-semibold lg:block"
              aria-hidden="true"
            >
              B
            </p>
          ) : null}
        </div>
        <nav aria-label="Principal" className="flex-1 space-y-6 overflow-y-auto px-3 pb-6">
          {groups.map((group) => (
            <div key={group.id}>
              <p
                className={cn(
                  "px-3 text-xs font-medium uppercase tracking-wide text-white/60",
                  collapsed && "lg:sr-only",
                )}
              >
                {group.label}
              </p>
              <ul className="mt-2 space-y-1">
                {group.items.map((item) => {
                  const active =
                    pathname === item.href ||
                    pathname === `${item.href}/` ||
                    (item.href !== "/" && pathname.startsWith(`${item.href}/`));
                  return (
                    <li key={item.href}>
                      <Link
                        href={navHref(item.href, organizationId)}
                        title={item.label}
                        onClick={onClose}
                        className={cn(
                          "flex h-10 items-center rounded-control px-3 text-sm font-medium",
                          active
                            ? "bg-white/15 text-white"
                            : "text-white/80 hover:bg-white/10 hover:text-white",
                          collapsed && "lg:justify-center lg:px-0",
                        )}
                      >
                        <span className={cn(collapsed && "lg:sr-only")}>{item.label}</span>
                        {collapsed ? (
                          <span className="hidden lg:inline" aria-hidden="true">
                            {item.label.slice(0, 1)}
                          </span>
                        ) : null}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
        <button
          type="button"
          className="hidden h-12 border-t border-white/15 px-4 text-left text-xs font-medium text-white/80 hover:bg-white/10 lg:block"
          onClick={onToggleCollapsed}
        >
          {collapsed ? copy.expandNavigation : copy.collapseNavigation}
        </button>
      </aside>
    </>
  );
}
