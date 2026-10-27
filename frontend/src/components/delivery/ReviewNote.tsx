"use client";

import { useId, useState } from "react";

import { AlertIcon, CheckIcon, QuestionIcon } from "../icons";
import { SearchBox } from "../SearchBox";
import { buttonClass, Field, inputClass, keepFocus, Notice } from "../ui";
import { ApiError, errorMessage } from "@/lib/api";
import {
  type AuthApi,
  confirmLines,
  countActions,
  formatExpiry,
  formatQuantity,
  initialChoice,
  type LineChoice,
  scanProblem,
} from "@/lib/delivery";
import { formatDose } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import type { ConfirmResult, MedicineSummary, ScanLine, ScanResult } from "@/lib/types";

function medicineName(m: MedicineSummary) {
  return `${titleCase(m.nom_marque)} ${formatDose(m.dosage_norm)}`;
}

/** Text read on the note, then batch, expiry and quantity when they were read. */
function ReadDetails({ line }: { line: ScanLine }) {
  const facts = [
    formatQuantity(line.quantite),
    line.numero_lot && `batch ${line.numero_lot}`,
    formatExpiry(line.date_peremption) && `exp. ${formatExpiry(line.date_peremption)}`,
  ].filter(Boolean);
  return (
    <div className="space-y-0.5">
      <p className="font-mono text-[0.95rem] break-words text-muted">
        “{line.designation}”
        {line.designations_regroupees.length > 0 && " (2 lines of the note, added up)"}
      </p>
      {facts.length > 0 && <p className="text-[0.95rem] text-muted">{facts.join(" · ")}</p>}
    </div>
  );
}

/**
 * Review screen: the pharmacist checks every line before anything is declared.
 * Lines MedRadar is sure about are ticked; lines to check wait for a choice;
 * back orders and products outside the official list are never ticked.
 */
export function ReviewNote({
  result,
  authApi,
  onDone,
  onRestart,
}: {
  result: ScanResult;
  authApi: AuthApi;
  onDone: (result: ConfirmResult) => void;
  onRestart: () => void;
}) {
  const id = useId();
  const [choices, setChoices] = useState<LineChoice[]>(() => result.lignes.map(initialChoice));
  const [supplier, setSupplier] = useState(result.document.fournisseur ?? "");
  const [number, setNumber] = useState(result.document.numero_bon ?? "");
  const [noteDate, setNoteDate] = useState(result.document.date_bon ?? "");
  const [keepHistory, setKeepHistory] = useState(true);
  const [keepPhoto, setKeepPhoto] = useState(false);
  const [searching, setSearching] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const lines = result.lignes;
  const update = (i: number, change: Partial<LineChoice>) =>
    setChoices((all) => all.map((c, k) => (k === i ? { ...c, ...change } : c)));
  const { inStock, outOfStock } = countActions(choices);
  const r = result.resume;
  const recognised = lines.map((l, i) => ({ l, i })).filter(({ l }) => l.correspondance === "exacte" || l.correspondance === "a_verifier");
  const notDelivered = lines.map((l, i) => ({ l, i })).filter(({ l }) => l.correspondance === "non_livre");
  const notFound = lines.filter((l) => l.correspondance === "non_trouve");

  function tickAll(checked: boolean) {
    setChoices((all) => all.map((c, i) => (lines[i].correspondance === "non_livre" || !c.medicine ? c : { ...c, checked })));
  }

  async function submit() {
    const message =
      `Put ${inStock} medicine${inStock === 1 ? "" : "s"} in stock` +
      (outOfStock ? ` and mark ${outOfStock} out of stock` : "") +
      "? Patients will see it at once.";
    if (!window.confirm(message)) return;
    setSaving(true);
    setError(null);
    try {
      const done = await authApi<ConfirmResult>(`/pharmacist/delivery-scan/${result.scan_id}/confirm`, {
        method: "POST",
        body: {
          fournisseur: supplier.trim() || null,
          numero_bon: number.trim() || null,
          date_bon: noteDate || null,
          lignes: confirmLines(lines, choices),
          garder_historique: keepHistory,
          garder_photo: keepHistory && keepPhoto,
        },
      });
      onDone(done);
    } catch (e) {
      // Expired or already confirmed: a clear sentence; otherwise the API's message
      setError(e instanceof ApiError && [409, 410].includes(e.status) ? scanProblem(e) : errorMessage(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-labelledby={`${id}-title`} className="space-y-6">
      <div className="space-y-1">
        <h1 id={`${id}-title`} className="text-[1.9rem] leading-tight font-bold sm:text-4xl">Check the note</h1>
        <p className="text-lg">
          <strong>{r.lignes_lues} lines read</strong>: {r.exactes} recognised, {r.a_verifier} to check,{" "}
          {r.non_livrees} not delivered{r.non_trouvees > 0 && `, ${r.non_trouvees} outside the official list`}.
        </p>
        <p className="text-muted">Nothing is put in stock until you confirm. Prices are never kept.</p>
      </div>

      <fieldset className="grid gap-4 rounded-xl border-2 border-line bg-surface p-4 sm:grid-cols-3">
        <legend className="px-1 font-bold">Delivery note</legend>
        <Field label="Wholesaler">
          {(p) => <input {...p} value={supplier} onChange={(e) => setSupplier(e.target.value)} className={inputClass} maxLength={120} />}
        </Field>
        <Field label="Note number">
          {(p) => <input {...p} value={number} onChange={(e) => setNumber(e.target.value)} className={inputClass} maxLength={60} />}
        </Field>
        <Field label="Date">
          {(p) => <input {...p} type="date" value={noteDate} onChange={(e) => setNoteDate(e.target.value)} className={inputClass} />}
        </Field>
      </fieldset>

      <section aria-labelledby={`${id}-recognised`} className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id={`${id}-recognised`} className="text-xl font-bold">
            Medicines received ({recognised.length})
          </h2>
          <div className="flex gap-2">
            <button type="button" onClick={() => tickAll(true)} className={buttonClass("secondary", "sm")}>
              Tick all
            </button>
            <button type="button" onClick={() => tickAll(false)} className={buttonClass("ghost", "sm")}>
              Untick all
            </button>
          </div>
        </div>
        <ul className="space-y-3">
          {recognised.map(({ l, i }) => {
            const choice = choices[i];
            const toCheck = l.correspondance === "a_verifier";
            return (
              <li
                key={l.index}
                className={`space-y-3 rounded-xl border-2 p-4 ${toCheck && !choice.medicine ? "border-caution-line bg-caution-soft" : "border-line bg-surface"}`}
              >
                <ReadDetails line={l} />
                {choice.medicine ? (
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={choice.checked}
                      onChange={(e) => update(i, { checked: e.target.checked })}
                      className="mt-1 h-6 w-6 shrink-0 accent-[var(--color-brand)]"
                    />
                    <span>
                      <span className="block text-lg font-bold">{medicineName(choice.medicine)}</span>
                      <span className="block text-[0.95rem] text-muted">{formLabel(choice.medicine.forme_groupe)}</span>
                      {toCheck && (
                        <span className="mt-1 inline-flex items-center gap-1 text-[0.95rem] font-semibold text-stock">
                          <CheckIcon className="h-4 w-4" /> Chosen by you
                        </span>
                      )}
                    </span>
                  </label>
                ) : (
                  <fieldset className="space-y-2">
                    <legend className="mb-2 flex items-center gap-1.5 font-bold text-caution">
                      <QuestionIcon className="h-5 w-5" /> To check: which medicine is it?
                    </legend>
                    {l.candidats.map((c) => (
                      <label key={c.id} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border-2 border-line bg-surface px-3">
                        <input
                          type="radio"
                          name={`${id}-line-${i}`}
                          onChange={() => update(i, { medicine: c, checked: true })}
                          className="h-5 w-5 accent-[var(--color-brand)]"
                        />
                        <span>
                          <strong>{medicineName(c)}</strong>{" "}
                          <span className="text-muted">· {formLabel(c.forme_groupe)}</span>
                        </span>
                      </label>
                    ))}
                  </fieldset>
                )}
                {toCheck && (
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    <button type="button" onClick={() => setSearching(searching === i ? null : i)} className="font-semibold text-brand underline">
                      Search another medicine
                    </button>
                    {choice.medicine && (
                      <button type="button" onClick={() => update(i, { medicine: null, checked: false })} className="font-semibold text-brand underline">
                        Choose again
                      </button>
                    )}
                    <button type="button" onClick={() => update(i, { medicine: null, checked: false })} className="font-semibold text-muted underline">
                      Ignore this line
                    </button>
                  </div>
                )}
                {searching === i && (
                  <SearchBox
                    size="md"
                    label="Search the medicine"
                    placeholder="Name on the note"
                    onSelect={(m) => {
                      update(i, { medicine: m, checked: true });
                      setSearching(null);
                    }}
                  />
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {notDelivered.length > 0 && (
        <section aria-labelledby={`${id}-missing`} className="space-y-3">
          <h2 id={`${id}-missing`} className="text-xl font-bold">
            Not delivered ({notDelivered.length})
          </h2>
          <p className="text-muted">Back orders and missing products are not put in stock.</p>
          <ul className="space-y-3">
            {notDelivered.map(({ l, i }) => (
              <li key={l.index} className="space-y-2 rounded-xl border-2 border-line bg-surface p-4">
                <ReadDetails line={l} />
                {l.medicament ? (
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      checked={choices[i].outOfStock}
                      onChange={(e) => update(i, { outOfStock: e.target.checked, checked: false })}
                      className="mt-1 h-6 w-6 shrink-0 accent-[var(--color-out)]"
                    />
                    <span>
                      Mark <strong>{medicineName(l.medicament)}</strong> out of stock
                    </span>
                  </label>
                ) : (
                  <p className="text-muted">Not found in the official list.</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {notFound.length > 0 && (
        <details className="rounded-xl border-2 border-line bg-surface p-4">
          <summary className="cursor-pointer font-bold">
            Products outside the official list, ignored ({notFound.length})
          </summary>
          <ul className="mt-3 list-disc space-y-1 pl-6 text-muted">
            {notFound.map((l) => (
              <li key={l.index} className="font-mono break-words">
                {l.designation}
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="space-y-3 rounded-xl border-2 border-line bg-surface p-4">
        <label className="flex cursor-pointer items-start gap-3">
          <input
            type="checkbox"
            checked={keepHistory}
            onChange={(e) => setKeepHistory(e.target.checked)}
            className="mt-1 h-6 w-6 shrink-0 accent-[var(--color-brand)]"
            aria-describedby={`${id}-history-help`}
          />
          <span>
            <span className="block font-bold">Keep this note in my history</span>
            <span id={`${id}-history-help`} className="block text-muted">
              To find later what you received, when and from which wholesaler. Prices are never kept.
            </span>
          </span>
        </label>
        <label className={`flex items-start gap-3 ${keepHistory && result.photo_possible ? "cursor-pointer" : "opacity-60"}`}>
          <input
            type="checkbox"
            checked={keepHistory && keepPhoto}
            disabled={!keepHistory || !result.photo_possible}
            onChange={(e) => setKeepPhoto(e.target.checked)}
            className="mt-1 h-6 w-6 shrink-0 accent-[var(--color-brand)]"
            aria-describedby={result.photo_possible ? undefined : `${id}-photo-limit`}
          />
          <span>
            <span className="block font-bold">Also keep the photo of the note</span>
            <span className="block text-muted">Visible only to your pharmacy, deleted after 90 days.</span>
            {!result.photo_possible && (
              <span id={`${id}-photo-limit`} className="block font-semibold text-caution">
                Monthly limit of 50 photo pages reached: the note can be kept without its photo.
              </span>
            )}
          </span>
        </label>
      </div>

      {error && (
        <Notice tone="danger" title="Not saved" role="alert">
          <p>{error}</p>
        </Notice>
      )}
      {choices.some((c, i) => lines[i].correspondance === "a_verifier" && !c.medicine) && (
        <p className="flex items-start gap-2 font-semibold text-caution">
          <AlertIcon className="mt-0.5 h-5 w-5" />
          Lines to check without a choice will be ignored.
        </p>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="button"
          onClick={submit}
          disabled={saving || inStock + outOfStock === 0}
          className={buttonClass("primary", "lg", "w-full sm:w-auto")}
          {...keepFocus}
        >
          {saving ? "Saving…" : `Put the ${inStock} ticked medicine${inStock === 1 ? "" : "s"} in stock`}
        </button>
        <button type="button" onClick={onRestart} className={buttonClass("ghost", "md")}>
          Scan another note
        </button>
      </div>
    </section>
  );
}
