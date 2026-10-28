import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line bg-surface">
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-8 text-[0.95rem] text-muted">
        <p className="text-base font-bold text-ink">
          MedRadar does not replace the advice of your pharmacist or doctor.
        </p>
        <p>
          Medicines and equivalents come from the national nomenclature of pharmaceutical products
          (August 2026), published by the{" "}
          <a
            href="https://www.miph.gov.dz/fr/nomenclature-nationale-des-produits-pharmaceutiques/"
            className="font-semibold text-brand underline"
            rel="noopener noreferrer"
            target="_blank"
          >
            Ministry of Pharmaceutical Industry
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          .
        </p>
        <p className="flex flex-wrap gap-x-6 gap-y-2">
          <Link href="/demo" className="font-semibold text-brand underline">
            Testing guide · <span lang="fr">Guide pour tester</span>
          </Link>
          <Link href="/confidentialite" className="font-semibold text-brand underline">
            Privacy policy
          </Link>
        </p>
      </div>
    </footer>
  );
}
