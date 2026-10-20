"use client";

// Login session of pharmacists and admins.
//
// The JWT is kept in memory and in sessionStorage: it survives a page reload
// but is erased when the tab is closed, and it is never put in localStorage.
// When the token expires, or when the API answers 401, the user is logged out
// and sent back to the login page with a short explanation.

import { useRouter } from "next/navigation";
import { useCallback, useEffect } from "react";

import { api, ApiError } from "./api";
import { createSessionStore } from "./sessionStore";
import type { Role, Token } from "./types";

export interface Session {
  token: string;
  role: Role;
  /** Expiry, in milliseconds since 1970 (read from the token) */
  expiresAt: number;
}

const sessionStore = createSessionStore<Session>("medradar.session");
const noticeStore = createSessionStore<string>("medradar.notice");

export const LOGIN_PATH = "/pharmacien/connexion";
export const EXPIRED_NOTICE = "Your session has ended. Please log in again.";

/** Read the expiry date written inside the token (it is not secret, only signed). */
function tokenExpiry(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp * 1000 : 0;
  } catch {
    return 0;
  }
}

export async function login(email: string, password: string): Promise<Session> {
  const token = await api<Token>("/auth/login", { method: "POST", body: { email: email.trim(), mot_de_passe: password } });
  const session = { token: token.access_token, role: token.role, expiresAt: tokenExpiry(token.access_token) };
  sessionStore.set(session);
  noticeStore.set(null);
  return session;
}

export function logout(notice?: string) {
  sessionStore.set(null);
  noticeStore.set(notice ?? null);
}

export function useSession() {
  const session = sessionStore.useValue();
  const hydrated = sessionStore.useHydrated();
  const valid = session && session.expiresAt > Date.now() ? session : null;
  return { session: valid, hydrated };
}

/** A message to show on the login page (for example "your session has ended"), read once. */
export function useLoginNotice() {
  return noticeStore.useValue();
}

/**
 * For pages that need a login: returns the session (null until known) and an
 * `authApi` function that adds the token and logs out on 401.
 */
export function useAuthedApi(requiredRole?: Role) {
  const router = useRouter();
  const { session, hydrated } = useSession();

  // Not logged in (or the token expired): back to the login page
  useEffect(() => {
    if (hydrated && !session) {
      if (sessionStore.get()) logout(EXPIRED_NOTICE);
      router.replace(LOGIN_PATH);
    }
  }, [hydrated, session, router]);

  // Log out exactly when the token expires, even if the page stays open
  useEffect(() => {
    if (!session) return;
    const timer = setTimeout(() => logout(EXPIRED_NOTICE), Math.max(0, session.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [session]);

  const token = session?.token ?? null;
  const authApi = useCallback(
    async <T,>(path: string, options: Parameters<typeof api>[1] = {}): Promise<T> => {
      try {
        return await api<T>(path, { ...options, token });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          logout(EXPIRED_NOTICE);
          router.replace(LOGIN_PATH);
        }
        throw error;
      }
    },
    [token, router],
  );

  const wrongRole = Boolean(session && requiredRole && session.role !== requiredRole);
  return { session, ready: hydrated && Boolean(session), wrongRole, authApi };
}
