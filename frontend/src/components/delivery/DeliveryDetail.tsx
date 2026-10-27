"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CheckIcon, CrossIcon } from "../icons";
import { PharmacistNav } from "../pharmacist/PharmacistNav";
import { buttonClass, ErrorState, Field, inputClass, keepFocus, Loading, Notice } from "../ui";
import { apiFile, errorMessage } from "@/lib/api";
import { useAuthedApi } from "@/lib/auth";
import { formatDay, formatExpiry, formatQuantity } from "@/lib/delivery";
import { formatDose } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import type { CancelResult, LineAction, NoteDetail, NoteLine } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

const ACTIONS: Record<LineAction, { label: string; className: string }> = {
  en_stock: { label: "Put in stock", className: "bg-stock-soft text-stock border-stock-line" },
  rupture: { label: "Marked out of stock", className: "bg-out-soft text-out border-out-line" },
  ignoree: { label: "Ignored", className: "bg-unknown-soft text-unknown border-unknown-line" },
};

/** Detail of a kept delivery note: lines, photos, corrections, deletion, cancellation. */
export function DeliveryDetail({ id }: { id: string }) {
  const router = useRouter();
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const note = useAsync(
    (signal) =>
      session && !wrongRole ? authApi<NoteDetail>(`/pharmacist/deliveries/${id}`, { signal }) : new Promise<NoteDetail>(() => {}),
    [session?.token, wrongRole, id],
  );
  const [message, setMessage] = useState<{ tone: "success" | "danger"; text: string } | null>(null);
  const [cancelled, setCancelled] = useState<CancelResult | null>(null);

  if (!ready) return <Loading />;
  if (wrongRole) return <Notice tone="info" title="This page is for pharmacists" />;
  if (note.status === "loading") return <Loading label="Loading the delivery note…" />;
  if (note.status === "error") return <ErrorState message={errorMessage(note.error)} onRetry={note.reload} />;
  const data = note.data;

  async function act(run: () => Promise<unknown>, done: string) {
    setMessage(null);
    try {
      await run();
      setMessage({ tone: "success", text: done });
      note.reload();
    } catch (error) {
      setMessage({ tone: "danger", text: errorMessage(error) });
    }
  }

  async function cancel() {
    const ok = window.confirm(
      "Cancel this note? The medicines it put in stock go back to their previous status " +
        "(or to “no information”). Medicines you declared again since are left as they are. " +
        "The note stays in your history, marked “Cancelled”.",
    );
    if (!ok) return;
    setMessage(null);
    try {
      setCancelled(await authApi<CancelResult>(`/pharmacist/deliveries/${id}/cancel`, { method: "POST" }));
      note.reload();
    } catch (error) {
      setMessage({ tone: "danger", text: errorMessage(error) });
    }
  }

  async function remove() {
    if (!window.confirm("Delete this note from your history, with its lines and photos? Your stock is not changed.")) return;
    try {
      await authApi(`/pharmacist/deliveries/${id}`, { method: "DELETE" });
      router.push("/pharmacien/historique");
    } catch (error) {
      setMessage({ tone: "danger", text: errorMessage(error) });
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PharmacistNav />
      <Link href="/pharmacien/historique" className="font-semibold text-brand underline">
        ← All delivery notes
      </Link>

      <div className="space-y-2">
        <h1 className="flex flex-wrap items-center gap-3 text-[1.9rem] leading-tight font-bold sm:text-4xl">
          {data.fournisseur ?? "Delivery note"} — {formatDay(data.date_bon ?? data.confirme_le)}
          {data.annule_le && (
            <span className="rounded-full border border-out-line bg-out-soft px-3 py-0.5 text-lg font-bold text-out">Cancelled</span>
          )}
        </h1>
        <p className="text-lg">
          {data.nb_mis_en_stock} put in stock · {data.nb_rupture} out of stock · {data.nb_non_livres} not delivered ·{" "}
          {data.nb_ignores} ignored — confirmed in {data.duree_secondes} s
        </p>
      </div>

      {message && (
        <Notice tone={message.tone} role={message.tone === "danger" ? "alert" : "status"}>
          <p>{message.text}</p>
        </Notice>
      )}
      {cancelled && <CancelReport result={cancelled} />}

      <EditNote note={data} onSave={(body) => act(() => authApi(`/pharmacist/deliveries/${id}`, { method: "PATCH", body }), "Saved.")} />

      <section aria-labelledby="lines" className="space-y-3">
        <h2 id="lines" className="text-xl font-bold">
          Lines of the note ({data.lignes.length})
        </h2>
        <ul className="space-y-3">
          {data.lignes.map((line) => (
            <LineItem key={line.id} line={line} />
          ))}
        </ul>
      </section>

      {data.pages_photos.length > 0 && (
        <section aria-labelledby="photos" className="space-y-3">
          <h2 id="photos" className="text-xl font-bold">
            Photo of the note
          </h2>
          <p className="text-muted">Visible only to your pharmacy. Deleted automatically after 90 days.</p>
          <div className="grid gap-3 sm:grid-cols-2">
            {data.pages_photos.map((p) => (
              <NotePhoto key={p} noteId={data.id} page={p} token={session?.token ?? null} />
            ))}
          </div>
          <button
            type="button"
            onClick={() =>
              window.confirm("Delete the photo of this note? The detail of the lines is kept.") &&
              act(() => authApi(`/pharmacist/deliveries/${id}/photos`, { method: "DELETE" }), "Photo deleted.")
            }
            className={buttonClass("secondary", "md")}
          >
            Delete the photo
          </button>
        </section>
      )}

      <section aria-labelledby="actions" className="space-y-3 border-t border-line pt-6">
        <h2 id="actions" className="sr-only">
          Actions
        </h2>
        {data.annulable && (
          <Notice tone="caution" title="Confirmed by mistake?">
            <p>Within 24 hours, you can cancel this note: the medicines go back to their previous status.</p>
            <button type="button" onClick={cancel} className={buttonClass("danger", "md")}>
              Cancel this note
            </button>
          </Notice>
        )}
        <button type="button" onClick={remove} className={buttonClass("ghost", "md", "text-out")}>
          Delete this note from my history
        </button>
      </section>
    </div>
  );
}

function LineItem({ line }: { line: NoteLine }) {
  const action = ACTIONS[line.action];
  const facts = [
    formatQuantity(line.quantite),
    line.numero_lot && `batch ${line.numero_lot}`,
    formatExpiry(line.date_peremption) && `exp. ${formatExpiry(line.date_peremption)}`,
  ].filter(Boolean);
  return (
    <li className="space-y-1.5 rounded-xl border-2 border-line bg-surface p-4">
      <p className="font-mono text-[0.95rem] break-words text-muted">“{line.designation_lue}”</p>
      {line.medicament ? (
        <p>
          <Link href={`/medicament/${line.medicament.id}`} className="text-lg font-bold text-ink">
            {titleCase(line.medicament.nom_marque)} {formatDose(line.medicament.dosage_norm)}
          </Link>{" "}
          <span className="text-muted">· {formLabel(line.medicament.forme_groupe)}</span>
        </p>
      ) : (
        <p className="text-muted">No medicine of the official list</p>
      )}
      {facts.length > 0 && <p className="text-[0.95rem]">{facts.join(" · ")}</p>}
      <p className="flex flex-wrap gap-2">
        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[0.9rem] font-bold ${action.className}`}>
          {line.action === "en_stock" ? <CheckIcon className="h-4 w-4" /> : line.action === "rupture" ? <CrossIcon className="h-4 w-4" /> : null}
          {action.label}
        </span>
        {line.corrigee_par_pharmacien && (
          <span className="rounded-full border border-brand/40 bg-brand-soft px-2.5 py-0.5 text-[0.9rem] font-bold text-brand">
            Corrected by you
          </span>
        )}
      </p>
    </li>
  );
}

function EditNote({ note, onSave }: { note: NoteDetail; onSave: (body: object) => void }) {
  const [supplier, setSupplier] = useState(note.fournisseur ?? "");
  const [number, setNumber] = useState(note.numero_bon ?? "");
  const [noteDate, setNoteDate] = useState(note.date_bon ?? "");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSave({ fournisseur: supplier.trim() || null, numero_bon: number.trim() || null, date_bon: noteDate || null });
      }}
      className="space-y-4 rounded-xl border-2 border-line bg-surface p-4"
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Wholesaler">
          {(p) => <input {...p} value={supplier} onChange={(e) => setSupplier(e.target.value)} maxLength={120} className={inputClass} />}
        </Field>
        <Field label="Note number">
          {(p) => <input {...p} value={number} onChange={(e) => setNumber(e.target.value)} maxLength={60} className={inputClass} />}
        </Field>
        <Field label="Date">
          {(p) => <input {...p} type="date" value={noteDate} onChange={(e) => setNoteDate(e.target.value)} className={inputClass} />}
        </Field>
      </div>
      <button type="submit" className={buttonClass("secondary", "md")} {...keepFocus}>
        Save the corrections
      </button>
    </form>
  );
}

/** A photo from a protected route: loaded with the token, never a public link. */
function NotePhoto({ noteId, page, token }: { noteId: number; page: number; token: string | null }) {
  const [url, setUrl] = useState<string | null>(null);
  const [large, setLarge] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    apiFile(`/pharmacist/deliveries/${noteId}/photos/${page}`, token, controller.signal)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {});
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [noteId, page, token]);
  if (!url) return <Loading label={`Loading page ${page}…`} />;
  return (
    <button
      type="button"
      onClick={() => setLarge(!large)}
      aria-expanded={large}
      className={`rounded-xl border-2 border-line bg-surface p-2 ${large ? "sm:col-span-2" : ""}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- private photo, loaded with the token */}
      <img src={url} alt={`Photo of the delivery note, page ${page}${large ? "" : " (tap to enlarge)"}`} className={`w-full rounded object-contain ${large ? "" : "max-h-72"}`} />
    </button>
  );
}

function CancelReport({ result }: { result: CancelResult }) {
  const name = (m: CancelResult["retablis"][number]) => `${titleCase(m.nom_marque ?? m.medicament_id)} ${formatDose(m.dosage_norm ?? "")}`;
  return (
    <Notice tone="success" title="Note cancelled" role="status">
      <p>
        {result.retablis.length} medicine{result.retablis.length === 1 ? " is" : "s are"} back to their previous status.
      </p>
      {result.laisses.length > 0 && (
        <p>
          Left as you declared them since: <strong>{result.laisses.map(name).join(", ")}</strong>.
        </p>
      )}
    </Notice>
  );
}
