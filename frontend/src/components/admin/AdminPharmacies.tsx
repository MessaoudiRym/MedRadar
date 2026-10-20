"use client";

import { useState } from "react";

import { MiniMap } from "../map";
import { buttonClass, ErrorState, Field, inputClass, keepFocus, Loading, Notice, PageTitle } from "../ui";
import { errorMessage } from "@/lib/api";
import { useAuthedApi } from "@/lib/auth";
import { formatDate, formatPhone } from "@/lib/format";
import { PHARMACY_STATUS_LABELS } from "@/lib/messages";
import type { AdminPharmacy, PharmacyStatus } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

type AuthApi = ReturnType<typeof useAuthedApi>["authApi"];

const TABS: { key: string; label: string; statuses: PharmacyStatus[] }[] = [
  { key: "pending", label: "Waiting for verification", statuses: ["en_attente"] },
  { key: "approved", label: "Approved", statuses: ["validee"] },
  { key: "stopped", label: "Not approved or suspended", statuses: ["refusee", "suspendue"] },
];

export function AdminPharmacies() {
  const { ready, wrongRole, authApi } = useAuthedApi("admin");
  const [tab, setTab] = useState(TABS[0]);
  const [done, setDone] = useState<string | null>(null);

  const list = useAsync(
    async (signal) => {
      if (!ready || wrongRole) return new Promise<AdminPharmacy[]>(() => {});
      const lists = await Promise.all(
        tab.statuses.map((statut) => authApi<AdminPharmacy[]>("/admin/pharmacies", { query: { statut }, signal })),
      );
      return lists.flat();
    },
    [tab.key, ready, wrongRole],
  );

  if (!ready) return <Loading />;
  if (wrongRole) {
    return <Notice tone="danger" title="This page is for administrators only." />;
  }

  function finished(pharmacy: AdminPharmacy, text: string) {
    list.setData((items) => items.filter((p) => p.id !== pharmacy.id));
    setDone(`${pharmacy.nom}: ${text}`);
  }

  return (
    <div className="space-y-6">
      <PageTitle lead="Check each pharmacy before patients can see it: does it exist, at this address, with this phone and professional number?">
        Pharmacies to verify
      </PageTitle>

      <div role="group" aria-label="Show pharmacies by status" className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            aria-pressed={tab.key === t.key}
            onClick={() => {
              setTab(t);
              setDone(null);
            }}
            className={buttonClass(tab.key === t.key ? "primary" : "secondary", "md")}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div aria-live="polite">
        {done && (
          <Notice tone="success" role="status">
            <p className="font-semibold">{done}</p>
          </Notice>
        )}
      </div>

      {list.status === "loading" && <Loading label="Loading pharmacies…" />}
      {list.status === "error" && <ErrorState message={errorMessage(list.error)} onRetry={list.reload} />}
      {list.status === "success" && list.data.length === 0 && (
        <Notice tone="info" title="Nothing here">
          <p>No pharmacy has this status.</p>
        </Notice>
      )}
      {list.status === "success" && list.data.length > 0 && (
        <ul className="space-y-5">
          {list.data.map((p) => (
            <PharmacyReview key={p.id} pharmacy={p} authApi={authApi} onDone={finished} />
          ))}
        </ul>
      )}
    </div>
  );
}

function PharmacyReview({ pharmacy: p, authApi, onDone }: {
  pharmacy: AdminPharmacy;
  authApi: AuthApi;
  onDone: (pharmacy: AdminPharmacy, text: string) => void;
}) {
  const [reasonFor, setReasonFor] = useState<"reject" | "suspend" | null>(null);
  const [reason, setReason] = useState("");
  const [tried, setTried] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(action: "approve" | "reject" | "suspend") {
    if (action !== "approve") {
      setTried(true);
      if (reason.trim().length < 3) return;
    }
    setBusy(true);
    setError(null);
    try {
      await authApi(`/admin/pharmacies/${p.id}/${action}`, {
        method: "POST",
        body: action === "approve" ? undefined : { motif: reason.trim() },
      });
      onDone(p, { approve: "approved", reject: "not approved", suspend: "suspended" }[action]);
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  const rows: [string, React.ReactNode][] = [
    ["Address", `${p.adresse} — ${p.quartier}, ${p.commune}`],
    ["Phone", formatPhone(p.telephone)],
    ["Professional number", p.numero_professionnel],
    ["Opening hours", p.horaires ?? "Not given"],
    ["Registered on", formatDate(p.cree_le)],
    [
      "Pharmacist",
      p.proprietaire
        ? `${p.proprietaire.prenom} ${p.proprietaire.nom} · ${p.proprietaire.email} · ${formatPhone(p.proprietaire.telephone)}`
        : "No account",
    ],
  ];

  return (
    <li className="space-y-4 rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-bold">{p.nom}</h2>
        <span className="flex gap-2">
          {p.est_demo && <span className="rounded-full bg-caution-soft px-2.5 py-0.5 font-semibold text-caution">Demo</span>}
          <span className="rounded-full bg-unknown-soft px-2.5 py-0.5 font-semibold">{PHARMACY_STATUS_LABELS[p.statut]}</span>
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-[1fr_18rem]">
        <dl className="space-y-2">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt className="text-[0.95rem] text-muted">{label}</dt>
              <dd className="font-semibold break-words">{value}</dd>
            </div>
          ))}
          {p.motif && (
            <div>
              <dt className="text-[0.95rem] text-muted">Reason given</dt>
              <dd className="font-semibold">{p.motif}</dd>
            </div>
          )}
        </dl>
        <MiniMap position={{ lat: p.latitude, lng: p.longitude }} label={`Position of ${p.nom}`} />
      </div>

      {reasonFor && (
        <Field
          label={reasonFor === "reject" ? "Why is it not approved?" : "Why is it suspended?"}
          hint="The pharmacist will see this reason."
          error={tried && reason.trim().length < 3 ? "Write a reason (at least 3 characters)." : null}
        >
          {(props) => (
            <textarea {...props} rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
              className={`${inputClass} py-2`} />
          )}
        </Field>
      )}

      {error && (
        <Notice tone="danger" role="alert">
          <p>{error}</p>
        </Notice>
      )}

      <div className="flex flex-wrap gap-2">
        {p.statut !== "validee" && !reasonFor && (
          <button type="button" disabled={busy} onClick={() => act("approve")} className={buttonClass("primary", "lg")}>
            {p.statut === "en_attente" ? "Approve" : "Approve again"}
          </button>
        )}
        {p.statut === "en_attente" && reasonFor !== "reject" && (
          <button type="button" disabled={busy} onClick={() => setReasonFor("reject")} className={buttonClass("secondary", "lg")}>
            Reject
          </button>
        )}
        {p.statut === "validee" && reasonFor !== "suspend" && (
          <button type="button" disabled={busy} onClick={() => setReasonFor("suspend")} className={buttonClass("secondary", "lg")}>
            Suspend
          </button>
        )}
        {reasonFor && (
          <>
            <button type="button" {...keepFocus} disabled={busy} onClick={() => act(reasonFor)} className={buttonClass("danger", "lg")}>
              {reasonFor === "reject" ? "Confirm the rejection" : "Confirm the suspension"}
            </button>
            <button type="button" onClick={() => { setReasonFor(null); setTried(false); }} className={buttonClass("ghost", "lg")}>
              Cancel
            </button>
          </>
        )}
      </div>
    </li>
  );
}
