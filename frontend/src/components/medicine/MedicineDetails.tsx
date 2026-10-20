import { formatDose } from "@/lib/format";
import { formLabel, isModifiedRelease, originLabel, titleCase, typeLabel } from "@/lib/messages";
import type { Medicine } from "@/lib/types";

export function MedicineDetails({ medicine }: { medicine: Medicine }) {
  const facts: [string, string | null][] = [
    ["Active ingredient", titleCase(medicine.molecule)],
    ["Dose", formatDose(medicine.dosage_norm) || medicine.dosage],
    ["Form", formLabel(medicine.forme_groupe)],
    ["Laboratory", `${titleCase(medicine.laboratoire)}${medicine.pays_laboratoire ? ` (${titleCase(medicine.pays_laboratoire)})` : ""}`],
    ["Origin", originLabel(medicine.origine)],
    ["Type", typeLabel(medicine.type)],
  ];

  return (
    <section aria-labelledby="medicine-name" className="space-y-4">
      <div>
        <p className="font-semibold text-muted">Medicine</p>
        <h1 id="medicine-name" className="text-[2rem] leading-tight font-bold sm:text-4xl">
          {titleCase(medicine.nom_marque)}{" "}
          <span className="text-brand">{formatDose(medicine.dosage_norm)}</span>
        </h1>
      </div>

      <dl className="grid grid-cols-2 gap-x-5 gap-y-3 rounded-xl border border-line bg-surface p-4 sm:p-5">
        {facts
          .filter((fact): fact is [string, string] => Boolean(fact[1]))
          .map(([label, value]) => (
            <div key={label}>
              <dt className="text-[0.95rem] text-muted">{label}</dt>
              <dd className="font-semibold">{value}</dd>
            </div>
          ))}
      </dl>

      {isModifiedRelease(medicine.forme_groupe) && (
        <p className="text-muted">
          This is a <strong className="text-ink">modified-release</strong> form: only other modified-release
          medicines are shown as equivalents.
        </p>
      )}
    </section>
  );
}
