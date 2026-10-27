"use client";

import "leaflet/dist/leaflet.css";

import { MapContainer, Marker, TileLayer } from "react-leaflet";

import { useFreshMap } from "./useFreshMap";
import { placeIcon, TILE_ATTRIBUTION, TILE_URL } from "./markers";
import type { LatLng } from "@/lib/geo";

export interface MiniMapProps {
  position: LatLng;
  label: string;
}

/** A small map with one marker (admin: where is this pharmacy?). */
export default function MiniMapInner({ position, label }: MiniMapProps) {
  const mapKey = useFreshMap();
  return (
    <MapContainer
      key={mapKey}
      center={[position.lat, position.lng]}
      zoom={15}
      scrollWheelZoom={false}
      className="h-48 w-full rounded-lg border border-line"
      aria-label={label}
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <Marker position={[position.lat, position.lng]} icon={placeIcon} title={label} alt={label} />
    </MapContainer>
  );
}
