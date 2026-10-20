import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible_Next } from "next/font/google";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

// Designed by the Braille Institute for readers with low vision
const atkinson = Atkinson_Hyperlegible_Next({
  variable: "--font-atkinson",
  subsets: ["latin"],
  display: "swap",
  // No metric overrides exist for this font: use ordinary system fonts while it loads
  adjustFontFallback: false,
  fallback: ["system-ui", "Segoe UI", "Arial", "sans-serif"],
});

export const metadata: Metadata = {
  title: {
    default: "MedRadar — find your medicine or an equivalent",
    template: "%s · MedRadar",
  },
  description:
    "Can't find your medicine? MedRadar shows registered equivalents in Algeria and pharmacies that have it, near you.",
};

export const viewport: Viewport = {
  themeColor: "#1d5a72",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${atkinson.variable} h-full`}>
      <body className="flex min-h-full flex-col font-sans">
        <SiteHeader />
        <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 pt-6 pb-4 sm:pt-10">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
