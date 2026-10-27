"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { CameraIcon } from "../icons";
import { buttonClass, ErrorState, Loading, Notice } from "../ui";
import { PharmacistNav } from "./PharmacistNav";
import { StatusPanel } from "./StatusPanel";
import { StockList } from "./StockList";
import { api, errorMessage } from "@/lib/api";
import { LOGIN_PATH, logout, useAuthedApi } from "@/lib/auth";
import type { Features, Me } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

export function Dashboard() {
  const router = useRouter();
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const me = useAsync(
    (signal) => (session && !wrongRole ? authApi<Me>("/auth/me", { signal }) : new Promise<Me>(() => {})),
    [session?.token, wrongRole],
  );

  const features = useAsync((signal) => api<Features>("/features", { signal }), []);

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
      {pharmacie?.statut === "validee" && <PharmacistNav />}
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
          {pharmacie.statut === "validee" && features.data?.delivery_scan && (
            <section aria-labelledby="scan-title" className="space-y-2 rounded-xl border-2 border-brand/40 bg-brand-soft p-4">
              <h2 id="scan-title" className="text-xl font-bold">
                Just received an order?
              </h2>
              <p>Take a photo of the delivery note: everything goes in stock in less than a minute, after you check it.</p>
              <Link href="/pharmacien/scanner" className={buttonClass("primary", "lg", "w-full sm:w-auto")}>
                <CameraIcon className="h-6 w-6" />
                Scan a delivery note
              </Link>
            </section>
          )}
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
