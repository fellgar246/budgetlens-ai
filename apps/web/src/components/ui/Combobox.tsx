"use client";

import { useMemo, useState } from "react";

import { copy } from "@/lib/copy";
import { cn } from "@/lib/cn";

type Item = { id: string; code: string; name: string };

export function Combobox({
  label,
  value,
  items,
  onChange,
  emptyLabel = copy.chooseAll,
}: {
  label: string;
  value: string;
  items: Item[];
  onChange: (value: string) => void;
  emptyLabel?: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const selected = items.find((item) => item.id === value);
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return items;
    return items.filter(
      (item) => item.code.toLowerCase().includes(term) || item.name.toLowerCase().includes(term),
    );
  }, [items, query]);
  const listId = `${label.replace(/\s+/g, "-").toLowerCase()}-list`;

  return (
    <div className="relative flex min-w-0 flex-col gap-1 text-xs">
      <span className="font-medium text-secondary">{label}</span>
      <input
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        className="h-10 rounded-control border border-border bg-white px-3 text-sm text-primary"
        value={open ? query : selected ? `${selected.code} — ${selected.name}` : ""}
        placeholder={emptyLabel}
        onFocus={() => {
          setOpen(true);
          setQuery("");
        }}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
      />
      {open ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute top-full z-20 mt-1 max-h-56 w-full overflow-auto rounded-control border border-border bg-surface shadow-overlay"
        >
          <li>
            <button
              type="button"
              className="flex h-10 w-full items-center px-3 text-left text-sm text-secondary hover:bg-canvas"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => {
                onChange("");
                setQuery("");
                setOpen(false);
              }}
            >
              {emptyLabel}
            </button>
          </li>
          {filtered.map((item) => (
            <li key={item.id} role="option" aria-selected={item.id === value}>
              <button
                type="button"
                className={cn(
                  "flex h-10 w-full items-center px-3 text-left text-sm hover:bg-canvas",
                  item.id === value ? "bg-canvas text-primary" : "text-primary",
                )}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(item.id);
                  setQuery("");
                  setOpen(false);
                }}
              >
                {item.code} — {item.name}
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
