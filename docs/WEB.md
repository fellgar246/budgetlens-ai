# Web app

The web app is a Next.js static export. The browser talks to `NEXT_PUBLIC_API_BASE_URL`. There is no required server-side rendering: `apps/web/next.config.ts` sets `output: "export"`. `make build` and the web unit suite check that app routes do not introduce `getServerSideProps` or `force-dynamic`.

User-visible labels are Spanish and live in `apps/web/src/lib/copy.ts`. Code, tests, and this document are English.

## Session and filters

`NEXT_PUBLIC_AUTH_MODE` selects the browser identity adapter. The default `dev` picker is for local and test only. `oidc` starts Authorization Code with PKCE against `NEXT_PUBLIC_OIDC_ISSUER` and `NEXT_PUBLIC_OIDC_CLIENT_ID`. Those values are public client configuration. Do not put a client secret in any `NEXT_PUBLIC_*` variable.

OIDC routes: `/login/` starts the redirect, `/callback/` exchanges the code, `/logout/` clears the in-memory token, and `/auth/error/` explains a failed sign-in. The access token stays in memory. PKCE `state` and `verifier` live in `sessionStorage` only for the round trip. After a reload without a token, the session is empty.

Local identity is selected on **Iniciar sesión** and **Seleccionar organización**. The header keeps the active organization visible. Changing organization clears stored filters, query parameters, copilot conversations, and in-memory view state before the next tenant loads. Capability gates hide unauthorized navigation; the API still authorizes every request.

Analysis filters live in the query string (`version`, `period_from`, `period_to`, `department`, `account`, `cost_center`, `group_by`, `sort`, `cursor`). An empty URL restores the last filters for that organization, then selects the active budget version when none is present. Refresh and back keep the same scope.

Export confirms the visible currency, period, group-by, and sort. The summary exports the department breakdown shown on that page. The download uses the current session; expired links are regenerated from the same dialog.

## Keyboard and accessibility

Automated checks cover `lang=es`, labelled controls, skip-link, favorability text (not color alone), `N/A` for a zero budget, and dialog Escape. Playwright also covers export-dialog close, table **Abrir detalle**, and the import stepper.

Manual walkthrough after `make dev` and `make seed`, signed in as Ana Analyst / Alpha:

1. Tab from the address bar: **Saltar al contenido** is first, Enter moves focus to `#contenido`.
2. Sidebar and header: organization, profile, and primary nav are reachable without a pointer. Focus ring is a 2px offset outline.
3. **Resumen**: version and period apply immediately; KPIs and the trend table stay readable at 360, 768, 1024, and 1440 px and at 200% zoom.
4. **Variaciones**: **Abrir detalle** is a button. Breadcrumb links return without dropping version or period. Sort is announced as text, not only by color.
5. **Exportar vista**: dialog traps Tab, Escape closes it, and focus returns to the trigger. The body states the exact scope.
6. **Importar archivo**: stepper, mapping selects, and the sticky footer work with the keyboard. Errors move focus to the validation summary. Commit stays disabled while `error_count > 0`.
7. **Escenarios**: fields, rule reorder buttons, and save are keyboard-operable. Preview updates are announced politely.
8. **Copiloto**: suggested-prompt buttons, the question field, and **Preguntar** are keyboard-operable. Evidence is a complementary panel on desktop and a drawer on smaller viewports. Progress uses `aria-live="polite"`.
9. VoiceOver or another screen reader: favorability includes the word Favorable/Desfavorable; compact money still exposes the exact amount.

Do not log tokens, access headers, or financial rows in the browser console. Product telemetry stores event names and dimension *names* only.

## Performance baseline

Target: first usable summary under 2.5 s p75 on a reference desktop connection after sign-in, with seed data.

```text
make dev
# other terminal
make seed
bash scripts/web-perf-baseline.sh
```

`scripts/web-perf-baseline.sh` writes HTML/JSON under `var/lighthouse/` for `/login/` and `/dashboard/`. The dashboard URL without a session measures the shell. For the seeded summary, sign in and rerun Lighthouse from Chrome DevTools on the live `/dashboard/` URL (throttling: desktop). Record the date and scores here when you capture a run; do not invent figures.

| Date | Surface | Performance | Accessibility | Notes |
|---|---|---|---|---|
| 2026-09-03 | `/login/` (desktop preset) | 86 | 100 | `make web-perf`; FCP 0.3 s, LCP 0.7 s, TTI 2.5 s |
| 2026-09-03 | `/dashboard/` shell, no session | 85 | 100 | Same run; FCP 0.3 s, LCP 0.5 s, TTI 2.6 s. Signed-in seeded summary still needs a DevTools capture before claiming the 2.5 s target |

## Responsive smoke

Playwright `e2e/responsive.spec.ts` covers 390×844 and 768×1024: navigation drawer, summary heading, and the import wizard. Tables become record lists below the `md` breakpoint.

## Screenshots

Optional synthetic frames: [screenshots/README.md](screenshots/README.md).
