import type { Config } from "tailwindcss";
import designTokens from "../docs/design-system/design-tokens.json";

// Helper to extract values from design tokens
function extractTokenValues(obj: any): any {
  if (typeof obj !== 'object' || obj === null) return obj;
  if ('value' in obj) return obj.value;

  const result: any = {};
  for (const key in obj) {
    result[key] = extractTokenValues(obj[key]);
  }
  return result;
}

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: extractTokenValues(designTokens.colors),
      fontFamily: {
        sans: designTokens.typography.fontFamily.primary.value.split(", "),
      },
      fontSize: extractTokenValues(designTokens.typography.fontSize),
      spacing: extractTokenValues(designTokens.spacing),
      borderRadius: extractTokenValues(designTokens.borderRadius),
      blur: extractTokenValues(designTokens.effects.blur),
      boxShadow: extractTokenValues(designTokens.effects.shadow),
      transitionDuration: {
        ...extractTokenValues(designTokens.animation.duration),
        "very-slow": designTokens.animation.duration.verySlow.value,
      },
      transitionTimingFunction: extractTokenValues(designTokens.animation.easing),
      backdropBlur: extractTokenValues(designTokens.effects.blur),
      keyframes: {
        elasticBounceIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "50%": { transform: "scale(1.05)" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        ambientSway: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-4px)" },
        },
        meshGradientShift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        particleDrift: {
          "0%": { transform: "translateY(0) translateX(0)" },
          "100%": { transform: "translateY(-100vh) translateX(50px)" },
        },
        glowBreathe: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "elastic-bounce-in": "elasticBounceIn 800ms cubic-bezier(0.68, -0.6, 0.32, 1.6)",
        "ambient-sway": "ambientSway 6000ms ease-in-out infinite",
        "mesh-gradient-shift": "meshGradientShift 20000ms ease infinite",
        "particle-drift": "particleDrift linear infinite",
        "glow-breathe": "glowBreathe 3000ms ease-in-out infinite",
      },
      screens: extractTokenValues(designTokens.breakpoints),
    },
  },
  plugins: [],
};

export default config;
