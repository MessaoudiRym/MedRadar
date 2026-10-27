"use client";

import { useEffect, useState } from "react";

import { haversineKm, type LatLng, ORAN_CENTER, ORAN_DISTRICTS } from "./geo";
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

// Pharmacies are only in Oran for now: a position further away would show an empty map
const COVERED_KM = 60;

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
        const position = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (haversineKm(position, ORAN_CENTER) > COVERED_KM) {
          store.set(DEFAULT_LOCATION);
          setProblem("You are far from Oran. MedRadar only covers Oran for now: we show pharmacies around Oran city centre.");
          return;
        }
        store.set({ position, label: "your position", source: "gps" });
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
