// Places and distances (same values as backend/app/geo.py).

export interface LatLng {
  lat: number;
  lng: number;
}

export const ORAN_CENTER: LatLng = { lat: 35.697, lng: -0.633 };

export const ORAN_DISTRICTS: { name: string; position: LatLng }[] = [
  { name: "Centre-ville", position: { lat: 35.697, lng: -0.633 } },
  { name: "Akid Lotfi", position: { lat: 35.703, lng: -0.598 } },
  { name: "Bir El Djir", position: { lat: 35.72, lng: -0.555 } },
  { name: "Canastel", position: { lat: 35.732, lng: -0.582 } },
  { name: "El Hamri", position: { lat: 35.688, lng: -0.62 } },
  { name: "Es Senia", position: { lat: 35.648, lng: -0.623 } },
  { name: "Gambetta", position: { lat: 35.7, lng: -0.612 } },
  { name: "Hai Sabah", position: { lat: 35.705, lng: -0.545 } },
  { name: "Maraval", position: { lat: 35.69, lng: -0.65 } },
  { name: "USTO", position: { lat: 35.705, lng: -0.585 } },
];

export function haversineKm(a: LatLng, b: LatLng): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

export function directionsUrls(to: LatLng, from?: LatLng) {
  const destination = `${to.lat},${to.lng}`;
  return {
    google: `https://www.google.com/maps/dir/?api=1&destination=${destination}`,
    osm: from
      ? `https://www.openstreetmap.org/directions?route=${from.lat},${from.lng};${destination}`
      : `https://www.openstreetmap.org/?mlat=${to.lat}&mlon=${to.lng}#map=17/${destination.replace(",", "/")}`,
  };
}
