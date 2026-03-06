import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        nova: {
          purple: "#8b5cf6",
          blue:   "#3b82f6",
          teal:   "#14b8a6",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float":      "float 6s ease-in-out infinite",
        "waveform":   "waveform 0.8s ease-in-out infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%":      { transform: "translateY(-8px)" },
        },
        waveform: {
          "0%, 100%": { transform: "scaleY(0.3)" },
          "50%":      { transform: "scaleY(1)" },
        },
      },
      backdropBlur: { xl: "20px" },
      backgroundImage: {
        "nova-gradient": "linear-gradient(135deg, #8b5cf6, #3b82f6)",
        "nova-radial":   "radial-gradient(ellipse at center, #8b5cf610, transparent)",
      },
    },
  },
  plugins: [],
};

export default config;