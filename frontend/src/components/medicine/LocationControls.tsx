"use client";

import { useId } from "react";

import { LocateIcon, PinIcon } from "../icons";
import { buttonClass, inputClass, Notice } from "../ui";
import { ORAN_DISTRICTS } from "@/lib/geo";
import type { useLocation } from "@/lib/location";

export const RADIUS_OPTIONS = [3, 5, 10, 20];

interface Props {
  geo: ReturnType<typeof useLocation>;
  radiusKm: number;
  onRadiusChange: (km: number) => void;
}

export function LocationControls({ geo, radiusKm, onRadiusChange }: Props) {
  const id = useId();
  const { location } = geo;

  return (
    <div className="space-y-3 rounded-xl border border-line bg-surface p-4">
      <p className="flex items-start gap-2 text-lg">
        <PinIcon className="mt-1 h-5 w-5 text-brand" />
        <span>
          Pharmacies around <strong>{location.label}</strong>
        </span>
      </p>

      <div className="grid gap-3 sm:grid-cols-[auto_1fr_auto] sm:items-end">
        <button
          type="button"
          onClick={geo.locate}
          disabled={geo.locating}
          className={buttonClass(location.source === "gps" ? "secondary" : "primary", "md")}
        >
          <LocateIcon />
          {geo.locating ? "Finding your position…" : location.source === "gps" ? "Update my position" : "Use my position"}
        </button>

        <div className="space-y-1">
          <label htmlFor={`${id}-district`} className="block font-semibold">
            Or choose a district in Oran
          </label>
          <select
            id={`${id}-district`}
            className={inputClass}
            value={location.source === "district" ? ORAN_DISTRICTS.find((d) => d.name === location.label)?.name ?? "" : ""}
            onChange={(e) => geo.chooseDistrict(e.target.value)}
          >
            <option value="" disabled>
              Choose a district
            </option>
            {ORAN_DISTRICTS.map((d) => (
              <option key={d.name} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label htmlFor={`${id}-radius`} className="block font-semibold">
            Distance
          </label>
          <select
            id={`${id}-radius`}
            className={inputClass}
            value={radiusKm}
            onChange={(e) => onRadiusChange(Number(e.target.value))}
          >
            {RADIUS_OPTIONS.map((km) => (
              <option key={km} value={km}>
                Within {km} km
              </option>
            ))}
          </select>
        </div>
      </div>

      {geo.problem && (
        <Notice tone="caution" role="status">
          <p>{geo.problem}</p>
        </Notice>
      )}
    </div>
  );
}
