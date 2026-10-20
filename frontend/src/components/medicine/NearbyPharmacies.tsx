"use client";

import { useMemo, useState } from "react";

import { type MapPharmacy, PharmacyMap } from "../map";
import { buttonClass, ErrorState, Loading, Notice } from "../ui";
import { LocationControls } from "./LocationControls";
import { MapLegend } from "./MapLegend";
import { PharmacyCard } from "./PharmacyCard";
import { errorMessage } from "@/lib/api";
import { formatDistance } from "@/lib/format";
import { haversineKm } from "@/lib/geo";
import type { useLocation } from "@/lib/location";
import { translateApiMessage } from "@/lib/messages";
import type { Availability, PharmacyAvailability, PublicPharmacy } from "@/lib/types";
import type { AsyncState } from "@/lib/useAsync";

const FIRST_SHOWN = 5;

interface Props {
  geo: ReturnType<typeof useLocation>;
  radiusKm: number;
  onRadiusChange: (km: number) => void;
  availability: AsyncState<Availability> & { reload: () => void };
  pharmacies: AsyncState<PublicPharmacy[]>;
  equivalentStockCount: number;
}

export function NearbyPharmacies({ geo, radiusKm, onRadiusChange, availability, pharmacies, equivalentStockCount }: Props) {
  const [showAll, setShowAll] = useState(false);
  // The searched medicine can have several packs: merge them, nearest first
  const { inStock, outOfStock } = useMemo(() => {
    const groups = availability.data?.resultats.filter((g) => g.est_demande) ?? [];
    const merge = (lists: PharmacyAvailability[][]) =>
      [...new Map(lists.flat().map((p) => [p.id, p])).values()].sort((a, b) => a.distance_km - b.distance_km);
    const stock = merge(groups.map((g) => g.en_stock));
    const stockIds = new Set(stock.map((p) => p.id));
    return { inStock: stock, outOfStock: merge(groups.map((g) => g.rupture)).filter((p) => !stockIds.has(p.id)) };
  }, [availability.data]);
  const center = geo.location.position;

  // Map: in stock, out of stock, and validated pharmacies nearby with no information
  const markers = useMemo<MapPharmacy[]>(() => {
    const known = new Set([...inStock, ...outOfStock].map((p) => p.id));
    const toMarker = (kind: MapPharmacy["kind"]) => (p: PublicPharmacy & { distance_km?: number }) => ({
      id: p.id,
      name: p.nom,
      position: { lat: p.latitude, lng: p.longitude },
      kind,
      details: `${p.quartier} · ${formatDistance(p.distance_km ?? haversineKm(center, { lat: p.latitude, lng: p.longitude }))}`,
    });
    const unknown = (pharmacies.data ?? []).filter(
      (p) => !known.has(p.id) && haversineKm(center, { lat: p.latitude, lng: p.longitude }) <= radiusKm,
    );
    return [...inStock.map(toMarker("stock")), ...outOfStock.map(toMarker("out")), ...unknown.map(toMarker("unknown"))];
  }, [inStock, outOfStock, pharmacies.data, center, radiusKm]);

  const counts = {
    stock: inStock.length,
    out: outOfStock.length,
    unknown: markers.filter((m) => m.kind === "unknown").length,
  };
  const shown = showAll ? inStock : inStock.slice(0, FIRST_SHOWN);

  return (
    <section aria-labelledby="nearby" className="space-y-4">
      <h2 id="nearby" className="text-2xl font-bold">
        Available near you
      </h2>

      <LocationControls geo={geo} radiusKm={radiusKm} onRadiusChange={onRadiusChange} />

      {availability.status === "loading" && <Loading label="Looking for pharmacies…" />}
      {availability.status === "error" && (
        <ErrorState message={errorMessage(availability.error)} onRetry={availability.reload} />
      )}

      {availability.status === "success" && (
        <>
          {availability.data.demo_data && (
            <Notice tone="caution" title={translateApiMessage(availability.data.demo_message ?? "")}>
              <p>These pharmacies and their stock are fictional. Only medicines and equivalents are real data.</p>
            </Notice>
          )}

          {inStock.length > 0 ? (
            <>
              <p className="text-lg" role="status">
                <strong>
                  {inStock.length} {inStock.length > 1 ? "pharmacies have" : "pharmacy has"} it
                </strong>{" "}
                within {radiusKm} km, nearest first.
              </p>
              <ul className="space-y-3">
                {shown.map((p) => (
                  <PharmacyCard key={p.id} pharmacy={p} from={center} />
                ))}
              </ul>
              {inStock.length > FIRST_SHOWN && !showAll && (
                <button type="button" onClick={() => setShowAll(true)} className={buttonClass("secondary", "md")}>
                  Show all {inStock.length} pharmacies
                </button>
              )}
            </>
          ) : (
            <Notice tone="info" title={`No pharmacy within ${radiusKm} km has declared it in stock`} role="status">
              {equivalentStockCount > 0 ? (
                <p>
                  But <strong>{equivalentStockCount}</strong>{" "}
                  {equivalentStockCount > 1 ? "pharmacies have" : "pharmacy has"} an equivalent in stock: see{" "}
                  <a href="#equivalents" className="font-semibold text-brand underline">
                    the equivalents below
                  </a>
                  .
                </p>
              ) : (
                <p>Try a larger distance, or ask to be told when it is back (at the bottom of this page).</p>
              )}
            </Notice>
          )}

          <div className="space-y-3">
            <h3 className="text-lg font-bold">Map</h3>
            {pharmacies.status === "error" && (
              <p className="text-muted">Pharmacies without information could not be loaded.</p>
            )}
            <PharmacyMap
              center={center}
              radiusKm={radiusKm}
              pharmacies={markers}
              label="Map of pharmacies near you. The same pharmacies are listed on this page."
            />
            <MapLegend counts={counts} />
          </div>
        </>
      )}
    </section>
  );
}
