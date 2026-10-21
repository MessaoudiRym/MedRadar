import type { Metadata } from "next";
import Link from "next/link";

import { ArrowRightIcon } from "@/components/icons";
import { HomeSearch } from "@/components/HomeSearch";
import { EXAMPLES } from "@/lib/examples";

export const metadata: Metadata = {
  title: { absolute: "MedRadar — can't find your medicine?" },
  description:
    "Search a medicine to see registered equivalents in Algeria (same active ingredient, same dose, same form) and pharmacies that have it near you.",
};

export default function Home() {
  return (
    <div className="mx-auto max-w-2xl space-y-10">
      <section className="space-y-6 pt-2 sm:pt-6">
        <h1 className="text-[2rem] leading-tight font-bold sm:text-[2.6rem]">
          Can’t find your medicine?
          <span className="block text-brand">Find an equivalent, or a pharmacy that has it.</span>
        </h1>

        <HomeSearch />

        <div className="space-y-2">
          <p className="font-semibold text-muted">Try:</p>
          <ul className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            {EXAMPLES.map((example) => (
              <li key={example.id}>
                <Link
                  href={`/medicament/${example.id}`}
                  className="flex min-h-11 items-center justify-between gap-3 rounded-lg border-2 border-line bg-surface px-4 py-2 font-semibold text-ink hover:border-brand sm:justify-start"
                >
                  <span>
                    {example.name} <span className="font-normal text-muted">· {example.use}</span>
                  </span>
                  <ArrowRightIcon className="h-5 w-5 text-brand" />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="how" className="space-y-3 border-t border-line pt-8">
        <h2 id="how" className="text-xl font-bold">
          How equivalents are found
        </h2>
        <p>
          An equivalent is another medicine registered in Algeria with the{" "}
          <strong>same active ingredient</strong>, the <strong>same dose</strong> and the{" "}
          <strong>same form</strong>. A modified-release tablet is never replaced by an ordinary one.
        </p>
        <p className="text-muted">
          Medicines come from the official national nomenclature. Pharmacy stock shown in this demo is
          simulated. Always check with your pharmacist or doctor before changing medicine.
        </p>
      </section>
    </div>
  );
}
