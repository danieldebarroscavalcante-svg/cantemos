import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--color-${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: token("bg"),
        surface: token("surface"),
        fg: token("fg"),
        muted: token("muted"),
        border: token("border"),
        primary: { DEFAULT: token("primary"), fg: token("primary-fg") },
        accent: token("accent"),
        success: token("success"),
        warning: token("warning"),
        danger: token("danger"),
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      minHeight: { touch: "44px" },
    },
  },
  plugins: [],
};

export default config;
