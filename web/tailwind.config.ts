import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        bg2: "var(--bg2)",
        panel: "var(--panel)",
        panel2: "var(--panel2)",
        elev: "var(--elev)",
        line: "var(--line)",
        "line-strong": "var(--line2)",
        fg: "var(--text)",
        fg2: "var(--text2)",
        fg3: "var(--text3)",
        cyan: "var(--cyan)",
        "cyan-ink": "var(--cyanInk)",
        positive: "var(--green)",
        warning: "var(--amber)",
        critical: "var(--red)",
        "header-bg": "var(--headerBg)",
      },
      fontFamily: {
        sans: ["'Space Grotesk'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        card: "14px",
        "card-lg": "16px",
        inner: "12px",
        pill: "8px",
      },
      animation: {
        rise: "rise 0.5s ease-out both",
        "rise-slow": "rise 0.6s ease-out both",
        ringhero: "ringhero 1.6s cubic-bezier(.22,1,.36,1) both",
        ringkpi: "ringkpi 1.4s cubic-bezier(.22,1,.36,1) 0.2s both",
        pulseonce: "pulseonce 0.6s ease-out",
        blink: "blink 1.1s step-end infinite",
        wirein: "wirein 0.4s ease-out both",
        twinkle: "twinkle 8s ease-in-out infinite",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        ringhero: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        ringkpi: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        pulseonce: {
          "0%": { boxShadow: "inset 0 0 18px rgba(255,92,114,.45)" },
          "100%": { boxShadow: "inset 0 0 0 transparent" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
        wirein: {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        twinkle: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
