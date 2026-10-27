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
async function getMedicineForTitle(id: string): Promise<Medicine | null> {
  "use cache";
  cacheLife("hours");
  try {
    return await api<Medicine>(`/medicines/${id}`);
  } catch {
    return null; // unknown medicine or API down: a generic title is used
  }
}

export async function generateMetadata({ params }: PageProps<"/medicament/[id]">): Promise<Metadata> {
  const { id } = await params;
  const m = await getMedicineForTitle(id);
  if (!m) return { title: "Medicine", description: "Equivalents and pharmacies that have this medicine near you." };
  const name = `${titleCase(m.nom_marque)} ${formatDose(m.dosage_norm)}`.trim();
  return {
    title: name,
    description: `${name} (${titleCase(m.molecule)}): equivalents registered in Algeria and pharmacies that have it near you.`,
  };
}

export default function MedicinePage({ params }: PageProps<"/medicament/[id]">) {
  return (
    // The loading state takes the height of the screen: the footer does not jump when the page appears
    <Suspense
      fallback={
        <div className="min-h-screen">
          <Loading label="Loading the medicine…" />
        </div>
      }
    >
      {params.then(({ id }) => (
        <MedicineView id={id} />
      ))}
    </Suspense>
  );
}
