"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { buttonClass, ErrorState, Loading, Notice } from "../ui";
import { StatusPanel } from "./StatusPanel";
import { StockList } from "./StockList";
import { errorMessage } from "@/lib/api";
import { LOGIN_PATH, logout, useAuthedApi } from "@/lib/auth";
import type { Me } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

export function Dashboard() {
  const router = useRouter();
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const me = useAsync(
    (signal) => (session && !wrongRole ? authApi<Me>("/auth/me", { signal }) : new Promise<Me>(() => {})),
    [session?.token, wrongRole],
  );

  function signOut() {
    logout("You are logged out.");
    router.replace(LOGIN_PATH);
  }

  if (!ready) return <Loading />;

  if (wrongRole) {
    return (
      <Notice tone="info" title="You are logged in as an administrator">
        <p>
          <Link href="/admin" className="font-semibold text-brand underline">Go to the admin page</Link>
        </p>
      </Notice>
    );
  }

  if (me.status === "loading") return <Loading label="Loading your pharmacy…" />;
  if (me.status === "error") return <ErrorState message={errorMessage(me.error)} onRetry={me.reload} />;

  const { utilisateur, pharmacie } = me.data;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-1">
          <p className="font-semibold text-muted">Hello {utilisateur.prenom}</p>
          <h1 className="text-[1.9rem] leading-tight font-bold sm:text-4xl">{pharmacie?.nom ?? "Your pharmacy"}</h1>
          {pharmacie && <p className="text-muted">{pharmacie.adresse}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {pharmacie && (
            <Link href="/pharmacien/pharmacie" className={buttonClass("secondary", "md")}>
              Edit my pharmacy
            </Link>
          )}
          <button type="button" onClick={signOut} className={buttonClass("ghost", "md")}>
            Log out
          </button>
        </div>
      </div>

      {pharmacie ? (
        <>
          <StatusPanel pharmacy={pharmacie} />
          {pharmacie.statut === "validee" && <StockList authApi={authApi} />}
        </>
      ) : (
        <Notice tone="danger" title="No pharmacy is linked to this account">
          <p>Contact the MedRadar team.</p>
        </Notice>
      )}
    </div>
  );
}
