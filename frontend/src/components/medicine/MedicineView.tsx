"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { buttonClass, ErrorState, Loading, PageTitle } from "../ui";
import { AlertForm } from "./AlertForm";
import { EquivalentsSection } from "./EquivalentsSection";
import { MedicineDetails } from "./MedicineDetails";
import { NearbyPharmacies } from "./NearbyPharmacies";
import { api, ApiError, errorMessage } from "@/lib/api";
import { useLocation } from "@/lib/location";
import type { Availability, Equivalents, Medicine, PublicPharmacy } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

/** The medicine page: details, pharmacies nearby, equivalents and alert. */
export function MedicineView({ id }: { id: string }) {
  const geo = useLocation();
  const [radiusKm, setRadiusKm] = useState(10);
  const { lat, lng } = geo.location.position;

  const medicine = useAsync((signal) => api<Medicine>(`/medicines/${id}`, { signal }), [id]);
  const equivalents = useAsync((signal) => api<Equivalents>(`/medicines/${id}/equivalents`, { signal }), [id]);
  const availability = useAsync(
    (signal) =>
      api<Availability>(`/medicines/${id}/availability`, { query: { lat, lng, radius_km: radiusKm }, signal }),
    [id, lat, lng, radiusKm],
  );
  const pharmacies = useAsync((signal) => api<PublicPharmacy[]>("/pharmacies", { signal }), []);

  // Number of nearby pharmacies with each equivalent brand in stock
  const stockByBrand = useMemo(() => {
    if (availability.status !== "success") return null;
    const byBrand = new Map<string, Set<number>>();
    for (const group of availability.data.resultats) {
      const set = byBrand.get(group.medicament.nom_marque) ?? new Set<number>();
      group.en_stock.forEach((p) => set.add(p.id));
      byBrand.set(group.medicament.nom_marque, set);
    }
    return new Map([...byBrand].map(([brand, set]) => [brand, set.size]));
  }, [availability]);

  const equivalentStockCount = useMemo(() => {
    if (availability.status !== "success") return 0;
    const ids = new Set<number>();
    availability.data.resultats.filter((g) => !g.est_demande).forEach((g) => g.en_stock.forEach((p) => ids.add(p.id)));
    return ids.size;
  }, [availability]);

  if (medicine.status === "loading") return <Loading label="Loading the medicine…" />;
  if (medicine.status === "error") {
    if (medicine.error instanceof ApiError && medicine.error.status === 404) {
      return (
        <div className="max-w-2xl space-y-6">
          <PageTitle lead="This medicine is not in the list of medicines sold in pharmacies, or it was withdrawn.">
            Medicine not found
          </PageTitle>
          <Link href="/" className={buttonClass("primary", "lg")}>
            Search for another medicine
          </Link>
        </div>
      );
    }
    return <ErrorState message={errorMessage(medicine.error)} onRetry={medicine.reload} />;
  }

  const count = equivalents.status === "success" ? equivalents.data.count : null;

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <MedicineDetails medicine={medicine.data} />

      <nav aria-label="On this page" className="flex flex-wrap gap-2">
        <a href="#nearby" className={buttonClass("secondary", "sm")}>
          Pharmacies near you
        </a>
        <a href="#equivalents" className={buttonClass("secondary", "sm")}>
          Equivalents{count !== null ? ` (${count})` : ""}
        </a>
        <a href="#alert" className={buttonClass("secondary", "sm")}>
          Get an alert
        </a>
      </nav>

      <NearbyPharmacies
        geo={geo}
        radiusKm={radiusKm}
        onRadiusChange={setRadiusKm}
        availability={availability}
        pharmacies={pharmacies}
        equivalentStockCount={equivalentStockCount}
      />

      <EquivalentsSection equivalents={equivalents} stockByBrand={stockByBrand} />

      <AlertForm
        medicineId={medicine.data.id}
        medicineName={medicine.data.nom_marque}
        position={geo.location.position}
        radiusKm={radiusKm}
      />
    </div>
  );
}
