"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

export type AsyncState<T> =
  | { status: "loading"; data?: undefined; error?: undefined }
  | { status: "error"; data?: undefined; error: unknown }
  | { status: "success"; data: T; error?: undefined };

type Settled<T> = { key: string; state: AsyncState<T> };

/**
 * Runs an async loader and tracks loading / error / success, so every screen
 * can show a clear state instead of a blank page. Re-runs when `deps` change
 * (they must be simple values); an older request never overwrites a newer one.
 */
export function useAsync<T>(loader: (signal: AbortSignal) => Promise<T>, deps: unknown[]) {
  const [attempt, setAttempt] = useState(0);
  const key = JSON.stringify([...deps, attempt]);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const load = useEffectEvent(loader);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setSettled({ key, state: { status: "success", data } });
      })
      .catch((error) => {
        if (!controller.signal.aborted) setSettled({ key, state: { status: "error", error } });
      });
    return () => controller.abort();
  }, [key]);

  const state: AsyncState<T> = settled?.key === key ? settled.state : { status: "loading" };

  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  /** Change the loaded data locally (optimistic updates). */
  const setData = useCallback((update: (data: T) => T) => {
    setSettled((previous) =>
      previous && previous.state.status === "success"
        ? { ...previous, state: { status: "success", data: update(previous.state.data) } }
        : previous,
    );
  }, []);

  return { ...state, reload, setData };
}
