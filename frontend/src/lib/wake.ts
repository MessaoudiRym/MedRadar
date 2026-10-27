"use client";

// Waking the API up. On the free plan of Render the API sleeps after 15 minutes
// without visits and needs up to a minute to start again (the Neon database too,
// for a few seconds). While it starts, the site shows one banner with a progress
// bar instead of errors, and read requests are tried again (see api.ts).

import { useSyncExternalStore } from "react";

/** How long the API may take to wake up before an error is shown */
export const WAKE_WINDOW_MS = 60_000;

let since: number | null = null;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

/** The API is slow or not answering yet: show the banner. */
export function markWaking() {
  if (since === null) {
    since = Date.now();
    emit();
  }
}

/** The API answered, or we gave up (the page shows its own error): hide the banner. */
export function markAwake() {
  if (since !== null) {
    since = null;
    emit();
  }
}

/** When the API started to be slow (milliseconds), or null when it is awake. */
export function useWakingSince() {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => since,
    () => null,
  );
}
