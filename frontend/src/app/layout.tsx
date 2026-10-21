import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Sans_Arabic } from "next/font/google";

import { SiteFooter } from "@/components/SiteFooter";
import { SiteHeader } from "@/components/SiteHeader";
import "./globals.css";

// Very legible, with plain digits (phone numbers, doses, distances), and the
// same family exists in Arabic for a future Arabic version
const noto = Noto_Sans({
  variable: "--font-main",
  subsets: ["latin"],
  display: "swap",
});

// Same family for Arabic letters (searches in Arabic or Darija): the browser
// takes each Arabic letter from this font
const notoArabic = Noto_Sans_Arabic({
  variable: "--font-arabic",
  subsets: ["arabic"],
  display: "swap",
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
    <html lang="en" className={`${noto.variable} ${notoArabic.variable} h-full`}>
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
