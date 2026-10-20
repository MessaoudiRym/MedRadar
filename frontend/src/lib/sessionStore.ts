"use client";

import { useSyncExternalStore } from "react";

/**
 * A value kept in memory and in sessionStorage (cleared when the tab is closed).
 * On the server, and before the page is hydrated, the value is null, so the
 * server HTML and the first browser render always match.
 */
export function createSessionStore<T>(key: string) {
  let cache: { raw: string | null; value: T | null } | null = null;
  const listeners = new Set<() => void>();

  function read(): T | null {
    let raw: string | null = null;
    try {
      raw = window.sessionStorage.getItem(key);
    } catch {
      raw = cache?.raw ?? null; // storage blocked (private mode): memory only
    }
    if (!cache || cache.raw !== raw) {
      let value: T | null = null;
      try {
        value = raw ? (JSON.parse(raw) as T) : null;
      } catch {
        value = null;
      }
      cache = { raw, value };
    }
    return cache.value;
  }

  function set(value: T | null) {
    const raw = value === null ? null : JSON.stringify(value);
    try {
      if (raw === null) window.sessionStorage.removeItem(key);
      else window.sessionStorage.setItem(key, raw);
    } catch {
      // storage blocked: keep it in memory for this page
    }
    cache = { raw, value };
    listeners.forEach((listener) => listener());
  }

  function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  }

  function useValue(): T | null {
    return useSyncExternalStore(subscribe, read, () => null);
  }

  /** True once the page runs in the browser (the stored value is then known). */
  function useHydrated(): boolean {
    return useSyncExternalStore(
      subscribe,
      () => true,
      () => false,
    );
  }

  return { get: read, set, subscribe, useValue, useHydrated };
}
