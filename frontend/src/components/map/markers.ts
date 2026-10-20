import L from "leaflet";

export type MarkerKind = "stock" | "out" | "unknown";

const SYMBOLS: Record<MarkerKind, string> = { stock: "✓", out: "✕", unknown: "?" };

// A coloured circle WITH a symbol: the colour is never the only signal
export function pharmacyIcon(kind: MarkerKind) {
  return L.divIcon({
    className: "",
    html: `<span class="marker-pin marker-pin--${kind}" aria-hidden="true">${SYMBOLS[kind]}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    popupAnchor: [0, -14],
  });
}

export const youIcon = L.divIcon({
  className: "",
  html: '<span class="marker-pin marker-pin--you" aria-hidden="true"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

export const placeIcon = L.divIcon({
  className: "",
  html: '<span class="marker-pin marker-pin--you" style="width:30px;height:30px" aria-hidden="true"></span>',
  iconSize: [30, 30],
  iconAnchor: [15, 15],
});

export const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
