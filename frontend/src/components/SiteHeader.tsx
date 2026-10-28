import Link from "next/link";

export function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true" focusable="false">
      <rect width="32" height="32" rx="8" fill="#1d5a72" />
      <path d="M16 23a7 7 0 110-14" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" opacity=".55" />
      <path d="M16 19.5a3.5 3.5 0 110-7" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" />
      <circle cx="16" cy="16" r="1.9" fill="#fff" />
      <path d="M21 10.5h4M23 8.5v4" stroke="#9fd3b0" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-surface">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-brand focus:px-4 focus:py-2 focus:text-white"
      >
        Skip to main content
      </a>
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="flex items-center gap-2.5 rounded-lg text-xl font-bold text-ink no-underline">
          <Logo />
          MedRadar
        </Link>
        <nav aria-label="Main" className="flex items-center gap-2">
          <Link
            href="/demo"
            lang="fr"
            className="hidden rounded-lg px-2 py-2 font-semibold text-brand underline decoration-2 hover:text-brand-dark sm:inline"
          >
            Guide pour tester
          </Link>
          <Link
            href="/pharmacien"
            className="rounded-lg px-2 py-2 font-semibold text-brand underline decoration-2 hover:text-brand-dark"
          >
            Pharmacist area
          </Link>
        </nav>
      </div>
    </header>
  );
}
