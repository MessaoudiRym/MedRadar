"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CameraIcon, CheckIcon, ImageIcon } from "../icons";
import { PharmacistNav } from "../pharmacist/PharmacistNav";
import { buttonClass, Loading, Notice, PageTitle } from "../ui";
import { ReviewNote } from "./ReviewNote";
import { api } from "@/lib/api";
import { useAuthedApi } from "@/lib/auth";
import {
  compressPages,
  DEMO_NOTE_URL,
  isDemoAccount,
  MAX_PAGES,
  scanNote,
  scanProblem,
} from "@/lib/delivery";
import type { ConfirmResult, Features, Me, ScanResult } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

type Step =
  | { name: "choose" }
  | { name: "reading" }
  | { name: "review"; result: ScanResult }
  | { name: "done"; result: ConfirmResult }
  | { name: "error"; message: string };

interface Page {
  blob: Blob;
  url: string;
}

/**
 * Scan a wholesaler's delivery note: photos of up to 5 pages, reading by the
 * API, then the review screen. Nothing is put in stock before the confirmation.
 */
export function DeliveryScan() {
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const me = useAsync(
    (signal) => (session && !wrongRole ? authApi<Me>("/auth/me", { signal }) : new Promise<Me>(() => {})),
    [session?.token, wrongRole],
  );
  const features = useAsync((signal) => api<Features>("/features", { signal }), []);
  const [pages, setPages] = useState<Page[]>([]);
  const [step, setStep] = useState<Step>({ name: "choose" });
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);

  // Previews stay in this page only: freed when removed, and when leaving the page
  const urls = useRef<Set<string>>(new Set());
  useEffect(() => {
    const all = urls.current;
    return () => all.forEach((url) => URL.revokeObjectURL(url));
  }, []);
  useEffect(() => heading.current?.focus(), [step.name]);

  if (!ready || me.status === "loading" || features.status === "loading") return <Loading />;
  if (wrongRole) return <Notice tone="info" title="This page is for pharmacists" />;
  const pharmacy = me.status === "success" ? me.data.pharmacie : null;
  const demo = me.status === "success" && isDemoAccount(me.data.utilisateur.email);

  async function addFiles(files: Blob[]) {
    const room = MAX_PAGES - pages.length;
    const compressed = await compressPages(files.slice(0, room));
    const added = compressed.map((blob) => ({ blob, url: URL.createObjectURL(blob) }));
    added.forEach((p) => urls.current.add(p.url));
    setPages((current) => [...current, ...added]);
  }

  async function choose(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (files.length) await addFiles(files);
  }

  async function useDemoNote() {
    const response = await fetch(DEMO_NOTE_URL);
    await addFiles([await response.blob()]);
  }

  async function read() {
    setStep({ name: "reading" });
    try {
      const result = await scanNote(authApi, pages.map((p) => p.blob));
      setStep({ name: "review", result });
    } catch (error) {
      setStep({ name: "error", message: scanProblem(error) });
    }
  }

  function remove(page: Page) {
    URL.revokeObjectURL(page.url);
    urls.current.delete(page.url);
    setPages((all) => all.filter((p) => p !== page));
  }

  function restart() {
    pages.forEach(remove);
    setStep({ name: "choose" });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PharmacistNav />

      {pharmacy?.statut !== "validee" ? (
        <Notice tone="info" title="Available once your pharmacy is approved">
          <p>
            <Link href="/pharmacien" className="font-semibold text-brand underline">
              Back to the dashboard
            </Link>
          </p>
        </Notice>
      ) : !features.data?.delivery_scan ? (
        <Notice tone="info" title="Reading delivery notes is not available">
          <p>Update your stock by hand from the dashboard. Your history of delivery notes is still available.</p>
        </Notice>
      ) : step.name === "review" ? (
        <ReviewNote
          result={step.result}
          authApi={authApi}
          onDone={(result) => setStep({ name: "done", result })}
          onRestart={restart}
        />
      ) : step.name === "done" ? (
        <Success result={step.result} heading={heading} />
      ) : (
        <>
          <PageTitle lead="MedRadar reads the note, you check it, then everything goes in stock in one tap.">
            Scan a delivery note
          </PageTitle>

          <input ref={camera} type="file" accept="image/*" capture="environment" hidden onChange={choose} data-testid="note-camera" />
          <input ref={gallery} type="file" accept="image/*" multiple hidden onChange={choose} data-testid="note-gallery" />

          {step.name === "reading" ? (
            <div className="space-y-2 rounded-xl border-2 border-line bg-surface p-5">
              <Loading label="Reading the note… (this can take up to 30 seconds)" />
            </div>
          ) : (
            <>
              {step.name === "error" && (
                <div role="alert" className="space-y-3 rounded-xl border-2 border-out-line bg-out-soft p-4">
                  <h2 ref={heading} tabIndex={-1} className="font-bold outline-none">
                    The note could not be read
                  </h2>
                  <p>{step.message}</p>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={read} className={buttonClass("primary", "md")} disabled={!pages.length}>
                      Try again
                    </button>
                    <Link href="/pharmacien" className={buttonClass("secondary", "md")}>
                      Update by hand
                    </Link>
                  </div>
                </div>
              )}

              <Notice tone="info">
                <p>Lay the note flat, in good light, with the whole page visible. Up to {MAX_PAGES} pages.</p>
              </Notice>

              {pages.length > 0 && (
                <ul aria-label="Pages of the note" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {pages.map((p, i) => (
                    <li key={p.url} className="space-y-2 rounded-xl border-2 border-line bg-surface p-2">
                      {/* eslint-disable-next-line @next/next/no-img-element -- local preview */}
                      <img src={p.url} alt={`Page ${i + 1} of the delivery note`} className="h-40 w-full rounded object-contain" />
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold">Page {i + 1}</span>
                        <button
                          type="button"
                          onClick={() => remove(p)}
                          className="font-semibold text-out underline"
                        >
                          Remove
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              <div className="space-y-3">
                {pages.length < MAX_PAGES && (
                  <button type="button" onClick={() => camera.current?.click()} className={buttonClass(pages.length ? "secondary" : "primary", "lg", "w-full")}>
                    <CameraIcon className="h-6 w-6" />
                    {pages.length ? "Add a page" : "Scan a delivery note"}
                  </button>
                )}
                {pages.length < MAX_PAGES && (
                  <button type="button" onClick={() => gallery.current?.click()} className="inline-flex min-h-11 items-center gap-2 font-semibold text-brand underline underline-offset-4">
                    <ImageIcon className="h-5 w-5" />
                    Choose photos on this device
                  </button>
                )}
                {pages.length > 0 && (
                  <button type="button" onClick={read} className={buttonClass("primary", "lg", "w-full")}>
                    Read the note ({pages.length} page{pages.length > 1 ? "s" : ""})
                  </button>
                )}
                {demo && pages.length === 0 && (
                  <p>
                    No note at hand?{" "}
                    <button type="button" onClick={useDemoNote} className="font-semibold text-brand underline">
                      Try with a demo delivery note
                    </button>
                  </p>
                )}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Success({ result, heading }: { result: ConfirmResult; heading: React.RefObject<HTMLHeadingElement | null> }) {
  const updated = result.nb_en_stock + result.nb_rupture;
  return (
    <section aria-labelledby="success" className="space-y-5">
      <div className="space-y-3 rounded-xl border-2 border-stock-line bg-stock-soft p-5">
        <h1 id="success" ref={heading} tabIndex={-1} className="flex items-center gap-2 text-2xl font-bold outline-none">
          <CheckIcon className="h-7 w-7 text-stock" />
          Stock updated
        </h1>
        <p className="text-lg">
          {updated} medicine{updated > 1 ? "s" : ""} updated in {result.duree_secondes} seconds.
          {result.bon_id !== null && " Note saved in your history."}
        </p>
        {result.nb_rupture > 0 && <p>{result.nb_rupture} marked out of stock.</p>}
        {result.message_photo && <p className="font-semibold">The note was kept without its photo: the monthly limit of 50 photo pages is reached.</p>}
      </div>
      <div className="flex flex-col gap-2 sm:flex-row">
        {result.bon_id !== null && (
          <Link href={`/pharmacien/historique/${result.bon_id}`} className={buttonClass("primary", "lg")}>
            See this note
          </Link>
        )}
        <Link href="/pharmacien" className={buttonClass("secondary", "lg")}>
          Back to the dashboard
        </Link>
      </div>
    </section>
  );
}
