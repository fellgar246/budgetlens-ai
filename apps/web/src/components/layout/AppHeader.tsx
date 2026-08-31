import { copy } from "@/lib/copy";
import { appEnvLabel } from "@/lib/env";

export function AppHeader() {
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-brand-700 px-4 text-white md:px-8">
      <p className="text-lg font-semibold tracking-tight">{copy.appName}</p>
      <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
        {appEnvLabel()}
      </span>
    </header>
  );
}
