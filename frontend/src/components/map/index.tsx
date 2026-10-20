"use client";

// Leaflet needs the browser (window, document): the maps are loaded on the
// client only, with a placeholder of the same size while they load.

import dynamic from "next/dynamic";

function MapPlaceholder({ height = "h-80 sm:h-[26rem]" }: { height?: string }) {
  return (
    <div
      className={`${height} flex w-full items-center justify-center rounded-xl border border-line bg-unknown-soft text-muted`}
    >
      Loading the map…
    </div>
  );
}

export const PharmacyMap = dynamic(() => import("./PharmacyMapInner"), {
  ssr: false,
  loading: () => <MapPlaceholder />,
});

export const LocationPicker = dynamic(() => import("./LocationPickerInner"), {
  ssr: false,
  loading: () => <MapPlaceholder height="h-72" />,
});

export const MiniMap = dynamic(() => import("./MiniMapInner"), {
  ssr: false,
  loading: () => <MapPlaceholder height="h-48" />,
});

export type { MapPharmacy } from "./PharmacyMapInner";
