import Link from "next/link";

import { ArrowRightIcon, CheckIcon } from "../icons";
import { ErrorState, Loading, Notice } from "../ui";
import { errorMessage } from "@/lib/api";
import { formatDose } from "@/lib/format";
import { formLabel, originLabel, titleCase, translateApiMessage, typeLabel } from "@/lib/messages";
import type { Equivalents } from "@/lib/types";
import type { AsyncState } from "@/lib/useAsync";

interface Props {
  equivalents: AsyncState<Equivalents> & { reload: () => void };
  /** Brand name -> number of nearby pharmacies with it in stock (null while loading) */
  stockByBrand: Map<string, number> | null;
}

export function EquivalentsSection({ equivalents, stockByBrand }: Props) {
  return (
    <section aria-labelledby="equivalents" className="scroll-mt-6 space-y-4">
      <h2 id="equivalents" className="text-2xl font-bold">
        Equivalents registered in Algeria
      </h2>

      {equivalents.status === "loading" && <Loading label="Looking for equivalents…" />}
      {equivalents.status === "error" && (
        <ErrorState message={errorMessage(equivalents.error)} onRetry={equivalents.reload} />
      )}

      {equivalents.status === "success" && (
        <>
          <Notice tone="caution" title="Ask your pharmacist or doctor first">
            <p className="text-lg">{translateApiMessage(equivalents.data.notice)}</p>
          </Notice>

          {!equivalents.data.dosage_verifie && (
            <Notice tone="danger" title="Dose not checked automatically">
              <p>
                The dose of this medicine is written in an unusual way in the official list, so MedRadar could not
                check it automatically. Ask your pharmacist to confirm that the dose of an equivalent is the same.
              </p>
            </Notice>
          )}

          {equivalents.data.count === 0 ? (
            <Notice tone="info" title="No equivalent registered">
              <p>
                No other medicine registered in Algeria has the same active ingredient, dose and form. Talk to
                your doctor: they may suggest another treatment.
              </p>
            </Notice>
          ) : (
            <>
              <p className="text-lg">
                <strong>{equivalents.data.count}</strong> medicine{equivalents.data.count > 1 ? "s have" : " has"} the
                same active ingredient, dose and form.
              </p>
              <ul className="space-y-3">
                {[...equivalents.data.equivalents]
                  .sort((a, b) => (stockByBrand?.get(b.nom_marque) ?? 0) - (stockByBrand?.get(a.nom_marque) ?? 0))
                  .map((m) => {
                    const inStock = stockByBrand?.get(m.nom_marque) ?? 0;
                    const facts = [formLabel(m.forme_groupe), titleCase(m.laboratoire), originLabel(m.origine), typeLabel(m.type)];
                    return (
                      <li key={m.id}>
                        <Link
                          href={`/medicament/${m.id}`}
                          className="flex items-center justify-between gap-3 rounded-xl border-2 border-line bg-surface p-4 text-ink no-underline hover:border-brand"
                        >
                          <span className="min-w-0 space-y-1">
                            <span className="block text-lg font-bold">
                              {titleCase(m.nom_marque)}{" "}
                              <span className="font-semibold text-muted">{formatDose(m.dosage_norm)}</span>
                            </span>
                            <span className="block text-[0.95rem] text-muted">{facts.filter(Boolean).join(" · ")}</span>
                            <span className="block font-semibold">
                              {stockByBrand === null ? (
                                <span className="text-muted">Checking nearby stock…</span>
                              ) : inStock > 0 ? (
                                <span className="inline-flex items-center gap-1.5 text-stock">
                                  <CheckIcon className="h-5 w-5" />
                                  In stock in {inStock} {inStock > 1 ? "pharmacies" : "pharmacy"} near you
                                </span>
                              ) : (
                                <span className="text-muted">No stock declared near you</span>
                              )}
                            </span>
                          </span>
                          <ArrowRightIcon className="h-6 w-6 text-brand" />
                        </Link>
                      </li>
                    );
                  })}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
