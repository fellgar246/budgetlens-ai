export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export function appEnvLabel(): string {
  const value = process.env.NEXT_PUBLIC_APP_ENV ?? "local";
  if (value === "test") {
    return "Pruebas";
  }
  if (value === "dev") {
    return "Desarrollo";
  }
  return "Local";
}
