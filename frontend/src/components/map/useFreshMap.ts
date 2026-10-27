import { useEffect, useState } from "react";

/**
 * Key for a MapContainer. Next.js keeps visited pages hidden (React Activity) and
 * shows them again on "Back": react-leaflet has then already destroyed its map,
 * and reusing it crashes the page. A new key, set as soon as the page is hidden,
 * makes React draw a new map instead.
 */
export function useFreshMap() {
  const [key, setKey] = useState(0);
  useEffect(() => () => setKey((k) => k + 1), []);
  return key;
}
