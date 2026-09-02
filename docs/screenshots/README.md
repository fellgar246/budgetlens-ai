# Optional demo screenshots

Screenshots are optional. If you add any, use only the synthetic seed (Ana Analyst / Alpha, or Pat Dual for the tenant switch). Do not capture account IDs, CloudFront URLs from a private account, secrets, or real ledgers.

Suggested frames, in product Spanish:

1. `login.png` — **Iniciar sesión** with the local user list
2. `resumen.png` — **Resumen** for Alpha after seed
3. `variaciones.png` — **Variaciones** showing `N/A` on a zero-budget row
4. `copiloto.png` — **Copiloto** answer for Maintenance January with evidence open
5. `cambio-organizacion.png` — Pat Dual after switching to Beta

Capture from a running local stack (`make dev` + `make seed`) at http://localhost:3000. Prefer 1280×800. Store PNG files next to this README only if they stay synthetic and secret-free.

```text
# Example after the stack is up and Playwright browsers are installed:
pnpm --filter web exec playwright screenshot --viewport-size=1280,800 \
  http://localhost:3000/login/ docs/screenshots/login.png
```

Sign-in is required for the other routes; capture those manually or with the existing Playwright journeys as a reference, not as a secret store.
