export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export function appEnv(): string {
  return process.env.NEXT_PUBLIC_APP_ENV ?? "local";
}

export function isProductionApp(): boolean {
  return appEnv() === "production";
}

export function appEnvLabel(): string {
  const value = appEnv();
  if (value === "test") {
    return "Pruebas";
  }
  if (value === "dev") {
    return "Desarrollo";
  }
  if (value === "production") {
    return "Producción";
  }
  return "Local";
}
