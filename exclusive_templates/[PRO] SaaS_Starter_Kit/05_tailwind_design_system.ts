// ============================================================
// 🎨 TAILWIND CSS DESIGN SYSTEM — Complete Configuration
// DevVault Pro 2026 — Drop this into any Next.js/Vite project
// ============================================================
// This config gives you a PREMIUM design system out of the box.
// Includes: custom colors, typography, animations, shadows,
// breakpoints, and utility classes used by top SaaS products.
// ============================================================

import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: "class",
    content: [
        "./src/**/*.{ts,tsx,js,jsx,mdx}",
        "./app/**/*.{ts,tsx,js,jsx,mdx}",
        "./components/**/*.{ts,tsx,js,jsx,mdx}",
    ],
    theme: {
        extend: {
            // ── Premium Color Palette ──────────────────
            colors: {
                brand: {
                    50: "#f5f3ff",
                    100: "#ede9fe",
                    200: "#ddd6fe",
                    300: "#c4b5fd",
                    400: "#a78bfa",
                    500: "#8b5cf6",  // Primary
                    600: "#7c3aed",
                    700: "#6d28d9",
                    800: "#5b21b6",
                    900: "#4c1d95",
                    950: "#2e1065",
                },
                success: { 50: "#f0fdf4", 500: "#22c55e", 700: "#15803d" },
                warning: { 50: "#fffbeb", 500: "#f59e0b", 700: "#b45309" },
                danger: { 50: "#fef2f2", 500: "#ef4444", 700: "#b91c1c" },
                info: { 50: "#eff6ff", 500: "#3b82f6", 700: "#1d4ed8" },
                // Neutral gray that works in both light and dark
                surface: {
                    50: "#fafafa",
                    100: "#f4f4f5",
                    200: "#e4e4e7",
                    300: "#d4d4d8",
                    400: "#a1a1aa",
                    500: "#71717a",
                    600: "#52525b",
                    700: "#3f3f46",
                    800: "#27272a",
                    850: "#1f1f23",
                    900: "#18181b",
                    950: "#09090b",
                },
            },

            // ── Typography ─────────────────────────────
            fontFamily: {
                sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
                mono: ["JetBrains Mono", "Fira Code", "monospace"],
                display: ["Cal Sans", "Inter", "sans-serif"],
            },
            fontSize: {
                "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
                "display-lg": ["3.5rem", { lineHeight: "1.1", letterSpacing: "-0.02em" }],
                "display-md": ["2.5rem", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
                "display-sm": ["1.875rem", { lineHeight: "1.2", letterSpacing: "-0.01em" }],
            },

            // ── Spacing ────────────────────────────────
            spacing: {
                "4.5": "1.125rem",
                "18": "4.5rem",
                "88": "22rem",
                "128": "32rem",
            },

            // ── Border Radius ──────────────────────────
            borderRadius: {
                "4xl": "2rem",
                "5xl": "2.5rem",
            },

            // ── Premium Shadows ────────────────────────
            boxShadow: {
                "glass": "0 0 0 1px rgba(255,255,255,0.05), 0 1px 2px rgba(0,0,0,0.4)",
                "glow-sm": "0 0 15px rgba(139,92,246,0.15)",
                "glow-md": "0 0 30px rgba(139,92,246,0.2)",
                "glow-lg": "0 0 60px rgba(139,92,246,0.25)",
                "card": "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)",
                "card-hover": "0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22)",
                "inner-glow": "inset 0 1px 0 rgba(255,255,255,0.05)",
            },

            // ── Animations ─────────────────────────────
            animation: {
                "fade-in": "fadeIn 0.3s ease-out",
                "fade-up": "fadeUp 0.4s ease-out",
                "fade-down": "fadeDown 0.4s ease-out",
                "scale-in": "scaleIn 0.2s ease-out",
                "slide-left": "slideLeft 0.3s ease-out",
                "slide-right": "slideRight 0.3s ease-out",
                "slide-up": "slideUp 0.3s ease-out",
                "slide-down": "slideDown 0.3s ease-out",
                "spin-slow": "spin 3s linear infinite",
                "pulse-glow": "pulseGlow 2s ease-in-out infinite",
                "shimmer": "shimmer 2s linear infinite",
                "bounce-soft": "bounceSoft 0.6s ease-out",
                "wiggle": "wiggle 0.5s ease-in-out",
                "float": "float 6s ease-in-out infinite",
            },
            keyframes: {
                fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
                fadeUp: { "0%": { opacity: "0", transform: "translateY(10px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
                fadeDown: { "0%": { opacity: "0", transform: "translateY(-10px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
                scaleIn: { "0%": { opacity: "0", transform: "scale(0.95)" }, "100%": { opacity: "1", transform: "scale(1)" } },
                slideLeft: { "0%": { transform: "translateX(100%)" }, "100%": { transform: "translateX(0)" } },
                slideRight: { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(0)" } },
                slideUp: { "0%": { transform: "translateY(100%)" }, "100%": { transform: "translateY(0)" } },
                slideDown: { "0%": { transform: "translateY(-100%)" }, "100%": { transform: "translateY(0)" } },
                pulseGlow: { "0%, 100%": { boxShadow: "0 0 15px rgba(139,92,246,0.1)" }, "50%": { boxShadow: "0 0 30px rgba(139,92,246,0.3)" } },
                shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
                bounceSoft: { "0%": { transform: "translateY(0)" }, "40%": { transform: "translateY(-8px)" }, "100%": { transform: "translateY(0)" } },
                wiggle: { "0%, 100%": { transform: "rotate(0)" }, "25%": { transform: "rotate(-3deg)" }, "75%": { transform: "rotate(3deg)" } },
                float: { "0%, 100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-10px)" } },
            },

            // ── Backdrop Blur ──────────────────────────
            backdropBlur: {
                xs: "2px",
            },

            // ── Background Image (for gradient text, shimmer) ──
            backgroundImage: {
                "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
                "gradient-text": "linear-gradient(135deg, #a78bfa 0%, #6366f1 50%, #3b82f6 100%)",
                "shimmer": "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.05) 50%, transparent 100%)",
            },
            backgroundSize: {
                "shimmer": "200% 100%",
            },
        },
    },
    plugins: [
        // Utility: .text-gradient (gradient text effect)
        function ({ addUtilities }: any) {
            addUtilities({
                ".text-gradient": {
                    "background": "linear-gradient(135deg, #a78bfa, #6366f1, #3b82f6)",
                    "-webkit-background-clip": "text",
                    "-webkit-text-fill-color": "transparent",
                    "background-clip": "text",
                },
                ".glass": {
                    "background": "rgba(255,255,255,0.03)",
                    "backdrop-filter": "blur(12px)",
                    "border": "1px solid rgba(255,255,255,0.06)",
                },
                ".glass-hover": {
                    "&:hover": {
                        "background": "rgba(255,255,255,0.05)",
                        "border-color": "rgba(255,255,255,0.1)",
                    },
                },
                ".scrollbar-hide": {
                    "-ms-overflow-style": "none",
                    "scrollbar-width": "none",
                    "&::-webkit-scrollbar": { display: "none" },
                },
                ".scrollbar-thin": {
                    "scrollbar-width": "thin",
                    "&::-webkit-scrollbar": { width: "6px" },
                    "&::-webkit-scrollbar-thumb": {
                        "background": "rgba(255,255,255,0.08)",
                        "border-radius": "3px",
                    },
                },
            });
        },
    ],
};

export default config;

// ============================================================
// USAGE EXAMPLES:
// ============================================================
//
// <h1 className="text-display-lg font-display text-gradient">
//   Build faster.
// </h1>
//
// <div className="glass glass-hover rounded-2xl p-6 animate-fade-up">
//   <p className="text-surface-400">Glassmorphism card</p>
// </div>
//
// <button className="bg-brand-500 hover:bg-brand-600 shadow-glow-sm
//   hover:shadow-glow-md transition-all rounded-xl px-6 py-3">
//   Get Started
// </button>
//
// <div className="bg-shimmer bg-shimmer animate-shimmer rounded-lg h-4">
//   <!-- Skeleton loader -->
// </div>
// ============================================================
