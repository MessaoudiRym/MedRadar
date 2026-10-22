// The only place that talks to the MedRadar API.
// Every call returns the JSON body, or throws an ApiError with an English message.

import { translateApiMessage } from "./messages";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

const TIMEOUT_MS = 15_000;

export class ApiError extends Error {
  // 0 means the API could not be reached (offline, server down, timeout)
  constructor(
    public status: number,
    message: string,
    public fieldErrors: Record<string, string> = {},
    /** Machine-readable reason sent by some routes, e.g. "ordonnance" */
    public code: string | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get isNetwork() {
    return this.status === 0;
  }
}

export const NETWORK_ERROR =
  "We can't reach MedRadar right now. Check your internet connection and try again.";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  /** Sent as JSON, or as multipart when it is a FormData (file upload) */
  body?: unknown;
  token?: string | null;
  query?: Record<string, string | number | undefined | null>;
  signal?: AbortSignal;
  timeoutMs?: number;
}

interface ValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(API_URL + path);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }

  const isForm = options.body instanceof FormData;
  const headers: Record<string, string> = { Accept: "application/json" };
  // For a FormData, the browser sets the multipart Content-Type itself
  if (options.body !== undefined && !isForm) headers["Content-Type"] = "application/json";
  if (options.token) headers.Authorization = `Bearer ${options.token}`;

  const timeout = AbortSignal.timeout(options.timeoutMs ?? TIMEOUT_MS);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: isForm ? (options.body as FormData) : options.body === undefined ? undefined : JSON.stringify(options.body),
      signal,
    });
  } catch (error) {
    if (options.signal?.aborted) throw error; // cancelled on purpose: let the caller ignore it
    throw new ApiError(0, NETWORK_ERROR);
  }

  if (response.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    // empty or non-JSON body
  }

  if (!response.ok) throw toApiError(response.status, data);
  return data as T;
}

function toApiError(status: number, data: unknown): ApiError {
  const detail = (data as { detail?: unknown } | null)?.detail;
  const code = (data as { code?: unknown } | null)?.code;

  // 422: a list of { loc, msg } — keep one message per field
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const item of detail as ValidationItem[]) {
      const field = (item.loc ?? []).filter((p) => p !== "body").join(".");
      if (field && !fieldErrors[field]) fieldErrors[field] = translateApiMessage(item.msg ?? "");
    }
    const first = Object.values(fieldErrors)[0];
    return new ApiError(status, first ?? "Some information is not valid.", fieldErrors);
  }

  if (typeof detail === "string")
    return new ApiError(status, translateApiMessage(detail), {}, typeof code === "string" ? code : null);
  if (status >= 500) return new ApiError(status, "Something went wrong on our side. Please try again.");
  return new ApiError(status, "Something went wrong. Please try again.");
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong. Please try again.";
}

/** A file from a protected route (photo, CSV export): never a public link. */
export async function apiFile(path: string, token: string | null, signal?: AbortSignal): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(API_URL + path, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(TIMEOUT_MS)]) : AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(0, NETWORK_ERROR);
  }
  if (!response.ok) {
    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      // not JSON
    }
    throw toApiError(response.status, data);
  }
  return response.blob();
}
