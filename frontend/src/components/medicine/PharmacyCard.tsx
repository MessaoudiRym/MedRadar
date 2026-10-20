import { AlertIcon, ClockIcon, PhoneIcon, RouteIcon } from "../icons";
import { buttonClass, StatusBadge } from "../ui";
import { formatDistance, formatPhone, updatedAgo } from "@/lib/format";
import { directionsUrls, type LatLng } from "@/lib/geo";
import type { PharmacyAvailability } from "@/lib/types";

export function PharmacyCard({ pharmacy, from }: { pharmacy: PharmacyAvailability; from: LatLng }) {
  const directions = directionsUrls({ lat: pharmacy.latitude, lng: pharmacy.longitude }, from);

  return (
    <li className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-lg font-bold">{pharmacy.nom}</h3>
          <p className="text-muted">
            {pharmacy.quartier} · <strong className="text-ink">{formatDistance(pharmacy.distance_km)}</strong>
          </p>
        </div>
        <StatusBadge status={pharmacy.statut} />
      </div>

      <div className="space-y-0.5 text-[0.95rem] text-muted">
        <p className="flex items-center gap-2">
          <ClockIcon className="h-4 w-4" />
          Updated {updatedAgo(pharmacy.derniere_mise_a_jour)}
        </p>
        {pharmacy.horaires && <p className="pl-6">Opening hours: {pharmacy.horaires}</p>}
      </div>

      {pharmacy.a_confirmer && (
        <p className="flex items-start gap-2 rounded-lg bg-caution-soft px-3 py-2 font-semibold text-caution">
          <AlertIcon className="mt-0.5 h-5 w-5" />
          To be confirmed by phone: this information is more than 7 days old.
        </p>
      )}

      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
        <a href={`tel:${pharmacy.telephone}`} className={buttonClass("primary", "md", "w-full sm:w-auto")}>
          <PhoneIcon />
          Call {formatPhone(pharmacy.telephone)}
        </a>
        <a
          href={directions.google}
          target="_blank"
          rel="noopener noreferrer"
          className={buttonClass("secondary", "md", "w-full sm:w-auto")}
        >
          <RouteIcon />
          Directions<span className="sr-only"> (Google Maps, opens in a new tab)</span>
        </a>
        <a
          href={directions.osm}
          target="_blank"
          rel="noopener noreferrer"
          className="self-start px-1 py-1 font-semibold text-brand underline sm:self-center"
        >
          OpenStreetMap<span className="sr-only"> directions (opens in a new tab)</span>
        </a>
      </div>
    </li>
  );
}
