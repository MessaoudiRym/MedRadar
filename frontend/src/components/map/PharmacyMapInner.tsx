"use client";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
import { useEffect } from "react";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";

import { type MarkerKind, pharmacyIcon, TILE_ATTRIBUTION, TILE_URL, youIcon } from "./markers";
import type { LatLng } from "@/lib/geo";

export interface MapPharmacy {
  id: number;
  name: string;
  position: LatLng;
  kind: MarkerKind;
  details: string;
}

export interface PharmacyMapProps {
  center: LatLng;
  radiusKm: number;
  pharmacies: MapPharmacy[];
  label: string;
}

const KIND_TEXT: Record<MarkerKind, string> = {
  stock: "In stock",
  out: "Out of stock",
  unknown: "No information",
};

/** Zoom so that the search area and every pharmacy are visible. */
function FitBounds({ center, radiusKm, pharmacies }: Omit<PharmacyMapProps, "label">) {
  const map = useMap();
  useEffect(() => {
    const area = L.latLng(center.lat, center.lng).toBounds(radiusKm * 2000);
    const points = pharmacies.map((p) => L.latLng(p.position.lat, p.position.lng));
    const bounds = points.length ? L.latLngBounds(points).extend(L.latLng(center.lat, center.lng)) : area;
    map.fitBounds(bounds.pad(0.1), { maxZoom: 15 });
  }, [map, center, radiusKm, pharmacies]);
  return null;
}

export default function PharmacyMapInner({ center, radiusKm, pharmacies, label }: PharmacyMapProps) {
  // Pharmacies in stock are drawn last, so they stay on top
  const order: MarkerKind[] = ["unknown", "out", "stock"];
  const sorted = [...pharmacies].sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind));

  return (
    <MapContainer
      center={[center.lat, center.lng]}
      zoom={13}
      scrollWheelZoom={false}
      className="h-80 w-full rounded-xl border border-line sm:h-[26rem]"
      aria-label={label}
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <FitBounds center={center} radiusKm={radiusKm} pharmacies={pharmacies} />
      <Circle
        center={[center.lat, center.lng]}
        radius={radiusKm * 1000}
        pathOptions={{ color: "#1d5a72", weight: 1.5, fillOpacity: 0.04, dashArray: "6 6" }}
      />
      <Marker position={[center.lat, center.lng]} icon={youIcon} title="Your position" alt="Your position">
        <Popup>Your position</Popup>
      </Marker>
      {sorted.map((p) => (
        <Marker
          key={p.id}
          position={[p.position.lat, p.position.lng]}
          icon={pharmacyIcon(p.kind)}
          title={`${p.name}: ${KIND_TEXT[p.kind]}`}
          alt={`${p.name}: ${KIND_TEXT[p.kind]}`}
        >
          <Popup>
            <strong>{p.name}</strong>
            <br />
            {KIND_TEXT[p.kind]}
            <br />
            {p.details}
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
