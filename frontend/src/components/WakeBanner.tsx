"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { markAwake, markWaking, useWakingSince, WAKE_WINDOW_MS } from "@/lib/wake";

// The health check answers at once when the API is awake: slower means it is starting
const SLOW_MS = 3_000;

/**
 * Wakes the API up as soon as a page opens (a light call to /health), and shows
 * a banner while it starts, instead of errors.
 */
export function WakeBanner() {
  const since = useWakingSince();
  const [now, setNow] = useState(0);

  useEffect(() => {
    const slow = setTimeout(markWaking, SLOW_MS);
    api("/health")
      .catch(() => {
        // the page shows its own error and "Try again" button
      })
      .finally(() => {
        clearTimeout(slow);
        markAwake();
      });
    return () => clearTimeout(slow);
  }, []);

  useEffect(() => {
    if (since === null) return;
    const timer = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(timer);
  }, [since]);

  if (since === null) return null;
  // Never shows 100 % before the API really answered
  const percent = Math.min(95, Math.max(5, Math.round(((now - since) / WAKE_WINDOW_MS) * 100)));

  return (
    <div role="status" className="border-b border-line bg-brand-soft">
      <div className="mx-auto max-w-5xl space-y-2 px-4 py-3">
        <p className="font-semibold text-ink">
          Starting the service, a few seconds…{" "}
          <span lang="fr" className="font-normal text-muted">
            Démarrage du service, quelques secondes…
          </span>
        </p>
        <div
          role="progressbar"
          aria-label="Starting the service"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          className="h-2 overflow-hidden rounded-full bg-surface"
        >
          <div className="h-full rounded-full bg-brand transition-[width] duration-500" style={{ width: `${percent}%` }} />
        </div>
      </div>
    </div>
  );
}
