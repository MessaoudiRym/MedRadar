import type { Metadata } from "next";
import { cacheLife } from "next/cache";
import { Suspense } from "react";

import { MedicineView } from "@/components/medicine/MedicineView";
import { Loading } from "@/components/ui";
import { api } from "@/lib/api";
import { formatDose } from "@/lib/format";
import { titleCase } from "@/lib/messages";
import type { Medicine } from "@/lib/types";

// The nomenclature changes rarely: the page title can be cached for an hour
async function getMedicineForTitle(id: string) {
  "use cache";
  cacheLife("hours");
  return api<Medicine>(`/medicines/${id}`);
}

export async function generateMetadata({ params }: PageProps<"/medicament/[id]">): Promise<Metadata> {
  const { id } = await params;
  try {
    const m = await getMedicineForTitle(id);
    const name = `${titleCase(m.nom_marque)} ${formatDose(m.dosage_norm)}`.trim();
    return {
      title: name,
      description: `${name} (${titleCase(m.molecule)}): equivalents registered in Algeria and pharmacies that have it near you.`,
    };
  } catch {
    return { title: "Medicine", description: "Equivalents and pharmacies that have this medicine near you." };
  }
}

export default function MedicinePage({ params }: PageProps<"/medicament/[id]">) {
  return (
    <Suspense fallback={<Loading label="Loading the medicine…" />}>
      {params.then(({ id }) => (
        <MedicineView id={id} />
      ))}
    </Suspense>
  );
}
