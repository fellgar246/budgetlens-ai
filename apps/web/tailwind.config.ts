import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bl-bg-canvas)",
        surface: "var(--bl-bg-surface)",
        primary: "var(--bl-text-primary)",
        secondary: "var(--bl-text-secondary)",
        border: "var(--bl-border)",
        brand: {
          700: "var(--bl-brand-700)",
          600: "var(--bl-brand-600)",
        },
        info: "var(--bl-info-700)",
        success: "var(--bl-success-700)",
        warning: "var(--bl-warning-700)",
        danger: "var(--bl-danger-700)",
        focus: "var(--bl-focus)",
      },
      borderRadius: {
        control: "var(--bl-radius-control)",
        surface: "var(--bl-radius-surface)",
      },
      fontFamily: {
        sans: [
          "var(--font-inter)",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
