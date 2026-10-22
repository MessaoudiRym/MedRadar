"use client";

import Link from "next/link";
import { useState } from "react";

import { AlertIcon, CheckIcon, ClockIcon, CrossIcon } from "../icons";
import { SearchBox } from "../SearchBox";
import { buttonClass, ErrorState, Loading, Notice, StatusBadge } from "../ui";
import { errorMessage } from "@/lib/api";
import { formatDay, formatExpiry, formatQuantity } from "@/lib/delivery";
import { formatDose, updatedAgo } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import type { Declaration, LastReception, MedicineSummary, StockStatus, TrackedStock } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

type AuthApi = <T>(path: string, options?: Parameters<typeof import("@/lib/api").api>[1]) => Promise<T>;

interface Message {
  tone: "success" | "danger";
  text: string;
  /** Medicine row the message belongs to (shown inside it), or none */
  id?: string;
}

export function StockList({ authApi }: { authApi: AuthApi }) {
  const stock = useAsync((signal) => authApi<TrackedStock[]>("/pharmacist/stock", { signal }), []);
  const [saving, setSaving] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState<Message | null>(null);
  const [adding, setAdding] = useState<MedicineSummary | null>(null);

  const setBusy = (id: string, busy: boolean) =>
    setSaving((s) => {
      const next = new Set(s);
      if (busy) next.add(id);
      else next.delete(id);
      return next;
    });

  /** Show the new status at once; put the old one back if the API refuses. */
  async function declare(medicine: MedicineSummary, statut: StockStatus) {
    const id = medicine.id;
    const previous = stock.data?.find((item) => item.medicament.id === id);
    const optimistic: TrackedStock = { medicament: medicine, statut, date_declaration: new Date().toISOString(), a_confirmer: false };
    stock.setData((items) =>
      items.some((i) => i.medicament.id === id)
        ? items.map((i) => (i.medicament.id === id ? optimistic : i))
        : [optimistic, ...items],
    );
    setBusy(id, true);
    setMessage(null);
    try {
      const saved = await authApi<Declaration>("/pharmacist/stock", {
        method: "POST",
        body: { medicament_id: id, statut },
      });
      stock.setData((items) =>
        items.map((i) => (i.medicament.id === id ? { ...i, date_declaration: saved.date_declaration } : i)),
      );
      setMessage({
        id,
        tone: "success",
        text: `Saved: ${statut === "en_stock" ? "in stock" : "out of stock"}.`,
      });
    } catch (error) {
      stock.setData((items) =>
        previous
          ? items.map((i) => (i.medicament.id === id ? previous : i))
          : items.filter((i) => i.medicament.id !== id),
      );
      setMessage({ id: previous ? id : undefined, tone: "danger", text: `Not saved for ${titleCase(medicine.nom_marque)}: ${errorMessage(error)}` });
    } finally {
      setBusy(id, false);
    }
  }

  async function untrack(medicine: MedicineSummary) {
    if (!window.confirm(`Stop following ${titleCase(medicine.nom_marque)}? Patients will no longer see its stock here.`)) return;
    try {
      await authApi(`/pharmacist/tracked/${medicine.id}`, { method: "DELETE" });
      stock.setData((items) => items.filter((i) => i.medicament.id !== medicine.id));
      setMessage({ tone: "success", text: `${titleCase(medicine.nom_marque)} removed from your list.` });
    } catch (error) {
      setMessage({ tone: "danger", text: errorMessage(error) });
    }
  }

  return (
    <section aria-labelledby="stock" className="space-y-5">
      <h2 id="stock" className="text-2xl font-bold">
        Your stock
      </h2>

      {/* Saved / not saved, read out by screen readers */}
      <div aria-live="polite" role="status">
        {message && !message.id && (
          <Notice tone={message.tone}>
            <p className="font-semibold">{message.text}</p>
          </Notice>
        )}
      </div>

      <div className="space-y-3 rounded-xl border border-line bg-surface p-4">
        <SearchBox
          size="md"
          label="Add a medicine to follow"
          placeholder="Brand name or active ingredient"
          onSelect={setAdding}
        />
        {adding && (
          <div className="space-y-3 rounded-lg bg-brand-soft p-4">
            <p className="font-semibold">
              {titleCase(adding.nom_marque)} {formatDose(adding.dosage_norm)}: is it in stock now?
            </p>
            <div className="grid grid-cols-2 gap-2 sm:flex">
              <button type="button" className={buttonClass("stock", "lg")}
                onClick={() => { declare(adding, "en_stock"); setAdding(null); }}>
                <CheckIcon /> In stock
              </button>
              <button type="button" className={buttonClass("out", "lg")}
                onClick={() => { declare(adding, "rupture"); setAdding(null); }}>
                <CrossIcon /> Out of stock
              </button>
              <button type="button" className={buttonClass("ghost", "md", "col-span-2")} onClick={() => setAdding(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {stock.status === "loading" && <Loading label="Loading your stock…" />}
      {stock.status === "error" && <ErrorState message={errorMessage(stock.error)} onRetry={stock.reload} />}
      {stock.status === "success" && stock.data.length === 0 && (
        <Notice tone="info" title="You don't follow any medicine yet">
          <p>Search for a medicine above, then say if it is in stock. It will stay in your list.</p>
        </Notice>
      )}
      {stock.status === "success" && stock.data.length > 0 && (
        <>
          <StaleSummary items={stock.data} />
          <ul className="space-y-3">
            {stock.data.map((item) => (
              <StockRow
                key={item.medicament.id}
                item={item}
                busy={saving.has(item.medicament.id)}
                message={message?.id === item.medicament.id ? message : null}
                onDeclare={(statut) => declare(item.medicament, statut)}
                onUntrack={() => untrack(item.medicament)}
              />
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function StaleSummary({ items }: { items: TrackedStock[] }) {
  const stale = items.filter((i) => i.a_confirmer).length;
  if (stale === 0) return <p className="text-lg">All {items.length} medicines are up to date. Thank you!</p>;
  return (
    <p className="text-lg">
      <strong>
        {stale} medicine{stale > 1 ? "s need" : " needs"} an update
      </strong>{" "}
      (not updated for more than 7 days). They are at the top of the list.
    </p>
  );
}

function StockRow({ item, busy, message, onDeclare, onUntrack }: {
  item: TrackedStock;
  busy: boolean;
  message: Message | null;
  onDeclare: (statut: StockStatus) => void;
  onUntrack: () => void;
}) {
  const m = item.medicament;
  const name = `${titleCase(m.nom_marque)} ${formatDose(m.dosage_norm)}`;
  return (
    <li className={`space-y-3 rounded-xl border-2 bg-surface p-4 ${item.a_confirmer ? "border-caution-line" : "border-line"}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-lg font-bold">{name}</h3>
          <p className="text-[0.95rem] text-muted">{formLabel(m.forme_groupe)} · {titleCase(m.molecule)}</p>
        </div>
        <StatusBadge status={item.statut ?? "unknown"} />
      </div>

      <p className={`flex items-center gap-2 text-[0.95rem] ${item.a_confirmer ? "font-semibold text-caution" : "text-muted"}`}>
        {item.a_confirmer ? <AlertIcon className="h-4 w-4" /> : <ClockIcon className="h-4 w-4" />}
        {item.date_declaration ? `Updated ${updatedAgo(item.date_declaration)}` : "Never updated"}
        {item.a_confirmer && " — please update"}
      </p>

      {item.derniere_reception && <LastReceived reception={item.derniere_reception} />}

      <div className="grid grid-cols-2 gap-2" role="group" aria-label={`Stock of ${name}`}>
        <button
          type="button"
          disabled={busy}
          aria-pressed={item.statut === "en_stock"}
          onClick={() => onDeclare("en_stock")}
          className={buttonClass("stock", "lg", `px-2 text-base whitespace-nowrap sm:text-lg ${item.statut === "en_stock" ? "!bg-stock !text-white" : ""}`)}
        >
          <CheckIcon /> In stock
        </button>
        <button
          type="button"
          disabled={busy}
          aria-pressed={item.statut === "rupture"}
          onClick={() => onDeclare("rupture")}
          className={buttonClass("out", "lg", `px-2 text-base whitespace-nowrap sm:text-lg ${item.statut === "rupture" ? "!bg-out !text-white" : ""}`)}
        >
          <CrossIcon /> Out of stock
        </button>
      </div>

      <div aria-live="polite">
        {message && (
          <p className={`flex items-center gap-2 font-semibold ${message.tone === "success" ? "text-stock" : "text-out"}`}>
            {message.tone === "success" ? <CheckIcon className="h-5 w-5" /> : <AlertIcon className="h-5 w-5" />}
            {message.text}
          </p>
        )}
      </div>

      <button type="button" onClick={onUntrack} className="text-[0.95rem] font-semibold text-muted underline">
        Stop following this medicine
      </button>
    </li>
  );
}

/** "Last received: 22/10/2026, Grossiste X, 30 boxes, batch ABC123, exp. 05/2028", from the history. */
function LastReceived({ reception }: { reception: LastReception }) {
  const facts = [
    formatDay(reception.date),
    reception.fournisseur,
    formatQuantity(reception.quantite),
    reception.numero_lot && `batch ${reception.numero_lot}`,
    formatExpiry(reception.date_peremption) && `exp. ${formatExpiry(reception.date_peremption)}`,
  ].filter(Boolean);
  return (
    <p className="text-[0.95rem] text-muted">
      Last received: {facts.join(", ")} ·{" "}
      <Link href={`/pharmacien/historique/${reception.bon_id}`} className="font-semibold text-brand underline">
        See the note
      </Link>
    </p>
  );
}
