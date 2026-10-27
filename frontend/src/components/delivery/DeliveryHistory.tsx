"use client";

import Link from "next/link";
import { useState } from "react";

import { ArrowRightIcon, CameraIcon, SearchIcon } from "../icons";
import { PharmacistNav } from "../pharmacist/PharmacistNav";
import { buttonClass, ErrorState, Field, inputClass, Loading, Notice, PageTitle } from "../ui";
import { apiFile, errorMessage } from "@/lib/api";
import { useAuthedApi } from "@/lib/auth";
import { downloadFile, formatDay } from "@/lib/delivery";
import type { NoteList, NoteSummary } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

interface Filters {
  du: string;
  au: string;
  fournisseur: string;
  q: string;
}

const EMPTY: Filters = { du: "", au: "", fournisseur: "", q: "" };

/** Delivery notes kept by the pharmacist: search, filters and CSV export. */
export function DeliveryHistory() {
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const [draft, setDraft] = useState<Filters>(EMPTY);
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [page, setPage] = useState(1);
  const [exportError, setExportError] = useState<string | null>(null);
  const list = useAsync(
    (signal) =>
      session && !wrongRole
        ? authApi<NoteList>("/pharmacist/deliveries", { query: { ...filters, page }, signal })
        : new Promise<NoteList>(() => {}),
    [session?.token, wrongRole, filters.du, filters.au, filters.fournisseur, filters.q, page],
  );

  if (!ready) return <Loading />;
  if (wrongRole) return <Notice tone="info" title="This page is for pharmacists" />;

  function apply(event: React.FormEvent) {
    event.preventDefault();
    setPage(1);
    setFilters({ ...draft, q: draft.q.trim(), fournisseur: draft.fournisseur.trim() });
  }

  async function exportCsv() {
    setExportError(null);
    try {
      const query = new URLSearchParams(Object.entries({ du: filters.du, au: filters.au }).filter(([, v]) => v));
      const blob = await apiFile(`/pharmacist/deliveries/export?${query}`, session?.token ?? null);
      downloadFile(blob, `medradar-delivery-notes-${filters.du || "start"}-${filters.au || "today"}.csv`);
    } catch (error) {
      setExportError(errorMessage(error));
    }
  }

  const filtered = Object.values(filters).some(Boolean);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PharmacistNav />
      <PageTitle lead="What you received, when, and from which wholesaler. Prices are never kept.">
        Delivery notes
      </PageTitle>

      <form onSubmit={apply} className="space-y-4 rounded-xl border-2 border-line bg-surface p-4" role="search">
        <Field label="When did I receive…?" hint="A medicine, e.g. Glucophage 850">
          {(p) => (
            <div className="relative">
              <SearchIcon className="pointer-events-none absolute top-1/2 left-3.5 h-5 w-5 -translate-y-1/2 text-muted" />
              <input {...p} type="search" dir="auto" value={draft.q} onChange={(e) => setDraft({ ...draft, q: e.target.value })} className={`${inputClass} pl-11`} />
            </div>
          )}
        </Field>
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="From">
            {(p) => <input {...p} type="date" value={draft.du} onChange={(e) => setDraft({ ...draft, du: e.target.value })} className={inputClass} />}
          </Field>
          <Field label="To">
            {(p) => <input {...p} type="date" value={draft.au} onChange={(e) => setDraft({ ...draft, au: e.target.value })} className={inputClass} />}
          </Field>
          <Field label="Wholesaler">
            {(p) => <input {...p} value={draft.fournisseur} onChange={(e) => setDraft({ ...draft, fournisseur: e.target.value })} className={inputClass} />}
          </Field>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="submit" className={buttonClass("primary", "md")}>
            Search
          </button>
          {filtered && (
            <button
              type="button"
              onClick={() => {
                setDraft(EMPTY);
                setFilters(EMPTY);
                setPage(1);
              }}
              className={buttonClass("ghost", "md")}
            >
              Clear
            </button>
          )}
          <button type="button" onClick={exportCsv} className={buttonClass("secondary", "md", "sm:ml-auto")}>
            Export (CSV){filters.du || filters.au ? " for this period" : ""}
          </button>
        </div>
        {exportError && <p className="font-semibold text-out">{exportError}</p>}
      </form>

      {list.status === "loading" && <Loading label="Loading your delivery notes…" />}
      {list.status === "error" && <ErrorState message={errorMessage(list.error)} onRetry={list.reload} />}
      {list.status === "success" &&
        (list.data.bons.length === 0 ? (
          <Notice tone="info" title={filtered ? "No delivery note matches" : "No delivery note yet"}>
            <p>
              {filtered ? "Try another medicine or period." : "Notes you scan and keep appear here."}{" "}
              <Link href="/pharmacien/scanner" className="font-semibold text-brand underline">
                Scan a delivery note
              </Link>
            </p>
          </Notice>
        ) : (
          <section aria-label="Delivery notes" className="space-y-3">
            <p className="text-muted" aria-live="polite">
              {list.data.total} note{list.data.total > 1 ? "s" : ""}
            </p>
            <ul className="space-y-3">
              {list.data.bons.map((note) => (
                <NoteItem key={note.id} note={note} />
              ))}
            </ul>
            {list.data.pages > 1 && (
              <nav aria-label="Pages" className="flex items-center justify-between gap-2">
                <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)} className={buttonClass("secondary", "md")}>
                  Newer
                </button>
                <span>
                  Page {list.data.page} of {list.data.pages}
                </span>
                <button type="button" disabled={page >= list.data.pages} onClick={() => setPage(page + 1)} className={buttonClass("secondary", "md")}>
                  Older
                </button>
              </nav>
            )}
          </section>
        ))}
    </div>
  );
}

function NoteItem({ note }: { note: NoteSummary }) {
  return (
    <li>
      <Link
        href={`/pharmacien/historique/${note.id}`}
        className="flex items-center justify-between gap-3 rounded-xl border-2 border-line bg-surface p-4 text-ink no-underline hover:border-brand"
      >
        <span className="min-w-0 space-y-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-bold">{formatDay(note.date_bon ?? note.confirme_le)}</span>
            {note.annule_le && (
              <span className="rounded-full border border-out-line bg-out-soft px-2.5 py-0.5 text-[0.9rem] font-bold text-out">
                Cancelled
              </span>
            )}
            {note.photo_gardee && (
              <span className="inline-flex items-center gap-1 text-muted" title="Photo kept">
                <CameraIcon className="h-5 w-5" />
                <span className="sr-only">Photo kept</span>
              </span>
            )}
          </span>
          <span className="block font-semibold">
            {note.fournisseur ?? "Unknown wholesaler"}
            {note.numero_bon && <span className="font-normal text-muted"> · N° {note.numero_bon}</span>}
          </span>
          <span className="block text-[0.95rem] text-muted">
            {note.nb_mis_en_stock} medicine{note.nb_mis_en_stock === 1 ? "" : "s"} put in stock
            {note.nb_non_livres > 0 && ` · ${note.nb_non_livres} back order${note.nb_non_livres === 1 ? "" : "s"}`}
          </span>
        </span>
        <ArrowRightIcon className="h-6 w-6 text-brand" />
      </Link>
    </li>
  );
}
