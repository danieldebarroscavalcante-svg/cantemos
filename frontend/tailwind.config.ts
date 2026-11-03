import type { Config } from "tailwindcss";

/** Cores, raios, sombras e fonte vêm dos tokens (styles/tokens.css + canais em app/globals.css). */
const rgb = (name: string) => `rgb(var(--rgb-${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./app/**/*.{ts,tsx,mdx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: rgb("bg"),
        surface: { DEFAULT: rgb("surface"), 1: rgb("surface-1"), 3: rgb("surface-3") },
        strong: rgb("strong"),
        fg: rgb("fg"),
        soft: rgb("soft"),
        muted: rgb("muted"),
        subtle: rgb("subtle"),
        line: rgb("line"),
        border: { DEFAULT: "var(--border-default)", subtle: "var(--border-subtle)" },
        primary: { DEFAULT: rgb("brand"), light: rgb("brand-light"), fg: rgb("on-brand") },
        lavender: rgb("lavender"),
        lime: rgb("lime"),
        peach: rgb("peach"),
        sand: rgb("sand"),
        success: rgb("success"),
        warning: rgb("warning"),
        danger: rgb("danger"),
      },
      fontFamily: { sans: ["var(--font-sans)"] },
      fontSize: {
        display: ["var(--fs-display)", { lineHeight: "var(--lh-display)" }],
        title: ["var(--fs-title)", { lineHeight: "var(--lh-title)", letterSpacing: "var(--ls-title)" }],
        "2xs": "var(--fs-2xs)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        xl: "var(--radius-lg)", // botões e campos (9px)
        "2xl": "var(--radius-xl)", // cartões (12px)
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        card: "var(--inset-highlight), var(--shadow-md)",
        lg: "var(--shadow-lg)",
        cta: "var(--shadow-sm), var(--glow-brand)",
      },
      backgroundImage: {
        brand: "var(--brand-gradient)",
        glow: "var(--bg-glow)",
      },
      minHeight: { touch: "44px" },
    },
  },
  plugins: [],
};

export default config;
