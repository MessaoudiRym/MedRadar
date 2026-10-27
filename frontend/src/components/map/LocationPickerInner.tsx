"use client";

import "leaflet/dist/leaflet.css";

import { useEffect, useMemo } from "react";
import { MapContainer, Marker, TileLayer, useMap, useMapEvents } from "react-leaflet";

import { useFreshMap } from "./useFreshMap";
import { placeIcon, TILE_ATTRIBUTION, TILE_URL } from "./markers";
import type { LatLng } from "@/lib/geo";

export interface LocationPickerProps {
  value: LatLng;
  onChange: (position: LatLng) => void;
  label: string;
  height?: string;
}

function ClickToPlace({ onChange }: { onChange: (p: LatLng) => void }) {
  useMapEvents({
    click(event) {
      onChange({ lat: round(event.latlng.lat), lng: round(event.latlng.lng) });
    },
  });
  return null;
}

function FollowValue({ value }: { value: LatLng }) {
  const map = useMap();
  useEffect(() => {
    if (!map.getBounds().contains([value.lat, value.lng])) map.panTo([value.lat, value.lng]);
  }, [map, value]);
  return null;
}

const round = (n: number) => Math.round(n * 1e6) / 1e6;

/** Click on the map, or drag the marker, to place the pharmacy. */
export default function LocationPickerInner({ value, onChange, label, height = "h-72" }: LocationPickerProps) {
  const mapKey = useFreshMap();
  const handlers = useMemo(
    () => ({
      dragend(event: { target: { getLatLng: () => { lat: number; lng: number } } }) {
        const p = event.target.getLatLng();
        onChange({ lat: round(p.lat), lng: round(p.lng) });
      },
    }),
    [onChange],
  );

  return (
    <MapContainer
      key={mapKey}
      center={[value.lat, value.lng]}
      zoom={15}
      className={`${height} w-full rounded-xl border-2 border-line`}
      aria-label={label}
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <ClickToPlace onChange={onChange} />
      <FollowValue value={value} />
      <Marker
        position={[value.lat, value.lng]}
        icon={placeIcon}
        draggable
        eventHandlers={handlers}
        title="Pharmacy position (drag to move)"
        alt="Pharmacy position"
        keyboard
      />
    </MapContainer>
  );
}
