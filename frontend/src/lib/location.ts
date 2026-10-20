"use client";

import { useEffect, useState } from "react";

import { type LatLng, ORAN_CENTER, ORAN_DISTRICTS } from "./geo";
import { createSessionStore } from "./sessionStore";

export interface ChosenLocation {
  position: LatLng;
  label: string;
  source: "gps" | "district";
}

// The position is only kept for this browser tab, never sent anywhere except
// in the availability request
const store = createSessionStore<ChosenLocation>("medradar.location");

export const DEFAULT_LOCATION: ChosenLocation = {
  position: ORAN_CENTER,
  label: "Oran city centre",
  source: "district",
};

export function useLocation() {
  const chosen = store.useValue();
  const location = chosen ?? DEFAULT_LOCATION;
  const [locating, setLocating] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function locate() {
    if (!("geolocation" in navigator)) {
      setProblem("Your browser cannot share your position. Choose your district instead.");
      return;
    }
    setLocating(true);
    setProblem(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        store.set({
          position: { lat: pos.coords.latitude, lng: pos.coords.longitude },
          label: "your position",
          source: "gps",
        });
      },
      (error) => {
        setLocating(false);
        setProblem(
          error.code === error.PERMISSION_DENIED
            ? "You did not share your position. We show pharmacies around Oran city centre: choose your district below."
            : "We could not find your position. Choose your district below.",
        );
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 5 * 60_000 },
    );
  }

  function chooseDistrict(name: string) {
    const district = ORAN_DISTRICTS.find((d) => d.name === name);
    if (district) store.set({ position: district.position, label: district.name, source: "district" });
    setProblem(null);
  }

  // If the user already allowed it before, use the position without asking again
  useEffect(() => {
    if (store.get() || !navigator.permissions) return;
    let cancelled = false;
    navigator.permissions
      .query({ name: "geolocation" })
      .then((status) => {
        if (!cancelled && status.state === "granted") locate();
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return { location, locating, problem, locate, chooseDistrict };
}
