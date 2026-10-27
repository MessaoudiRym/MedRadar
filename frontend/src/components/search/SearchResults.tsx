"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ArrowRightIcon, QuestionIcon } from "../icons";
import { PhotoSearch } from "../photo/PhotoSearch";
import { MAX_QUERY_LENGTH, SearchBox } from "../SearchBox";
import { ErrorState, Loading, Notice } from "../ui";
import { api, errorMessage } from "@/lib/api";
import { formatDose } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import type { SmartSearch } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

const SLOW_AFTER_MS = 1000;
const ARABIC = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;

/** The patient's own words, shown as typed: right to left and lang="ar" when Arabic. */
function Typed({ text }: { text: string }) {
  const arabic = ARABIC.test(text);
  return (
    <bdi lang={arabic ? "ar" : undefined} dir="auto" className="font-semibold">
      {text}
    </bdi>
  );
}

/**
 * Full search (Enter or the Search button). The API may ask the language
 * model to understand an Arabic, Darija or English name; results always come
 * from the official list, and the patient checks them.
 */
export function SearchResults() {
  // A link can carry a longer text than the search box allows
  const q = (useSearchParams().get("q") ?? "").slice(0, MAX_QUERY_LENGTH).trim();
  const input = useRef<HTMLInputElement>(null);
  const search = useAsync(
    (signal) =>
      q.length >= 2
        ? api<SmartSearch>("/medicines/search", { query: { q, interpret: "true", limit: 10 }, signal })
        : Promise.resolve(null),
    [q],
  );

  function typeName() {
    input.current?.scrollIntoView({ block: "center", behavior: "smooth" });
    input.current?.focus({ preventScroll: true });
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <SearchBox key={q} initialQuery={q} inputRef={input} />

      {search.status === "loading" && <Searching />}
      {search.status === "error" && <ErrorState message={errorMessage(search.error)} onRetry={search.reload} />}
      {search.status === "success" && search.data && <Answer data={search.data} onTypeName={typeName} />}
      {search.status === "success" && !search.data && (
        <Notice tone="info" title="Type the name of a medicine">
          <p>At least 2 letters, in French, Arabic, Darija or English.</p>
        </Notice>
      )}
    </div>
  );
}

/** "Searching…", then "Broader search…" when the search takes longer (the model is asked). */
function Searching() {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);
  return <Loading label={slow ? "Broader search…" : "Searching…"} />;
}

function Answer({ data, onTypeName }: { data: SmartSearch; onTypeName: () => void }) {
  const { interpretation, results } = data;
  const heading = useRef<HTMLHeadingElement>(null);
  const understood = interpretation.methode !== "recherche" && interpretation.compris_comme;

  // The results are announced and reachable at once with the keyboard
  useEffect(() => heading.current?.focus(), []);

  if (interpretation.type === "maladie_ou_symptome") {
    return (
      <section aria-labelledby="answer" className="space-y-4">
        <h1 id="answer" ref={heading} tabIndex={-1} className="sr-only">
          No medicine from a disease or a symptom
        </h1>
        <Notice tone="caution" title="MedRadar does not choose a medicine from a disease or a symptom">
          <p>
            Type the name written on the box or on the prescription, or ask your pharmacist for advice.
          </p>
        </Notice>
        <PhotoSearch onTypeName={onTypeName} />
      </section>
    );
  }

  if (results.length === 0) {
    return (
      <section aria-labelledby="answer" className="space-y-4">
        <Notice tone="info">
          <h1 id="answer" ref={heading} tabIndex={-1} className="font-bold outline-none">
            No medicine found for “<Typed text={interpretation.requete_originale} />”
          </h1>
          <p>Try the name written on the box, or take a photo of the box.</p>
        </Notice>
        <PhotoSearch onTypeName={onTypeName} />
      </section>
    );
  }

  return (
    <section aria-labelledby="answer" className="space-y-4">
      <h1 id="answer" ref={heading} tabIndex={-1} className="text-2xl font-bold outline-none">
        {results.length} result{results.length > 1 ? "s" : ""}
      </h1>

      {understood && (
        <Notice tone="info">
          <p className="text-lg">
            You wrote “<Typed text={interpretation.requete_originale} />” — we understood:{" "}
            <strong>{interpretation.compris_comme}</strong>.
          </p>
        </Notice>
      )}

      {interpretation.type === "marque_etrangere" && (
        <Notice tone="caution" title="Not sold in Algeria under this name">
          <p>
            “<Typed text={interpretation.requete_originale} />” is not sold in Algeria under this name. It contains{" "}
            <strong>{titleCase(interpretation.compris_comme ?? "")}</strong>: here are the medicines registered in
            Algeria that contain it. Ask your pharmacist for advice.
          </p>
        </Notice>
      )}

      {interpretation.a_verifier && (
        <p className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-caution-line bg-caution-soft px-2.5 py-0.5 font-bold text-caution">
            <QuestionIcon className="h-4 w-4" />
            To check
          </span>
          <span>Check that this is your medicine before continuing.</span>
        </p>
      )}

      <ul className="space-y-3">
        {results.map((m) => (
          <li key={m.id}>
            <Link
              href={`/medicament/${m.id}`}
              className="flex items-center justify-between gap-3 rounded-xl border-2 border-line bg-surface p-4 text-ink no-underline hover:border-brand"
            >
              <span className="min-w-0 space-y-1">
                <span className="block text-lg font-bold">
                  {titleCase(m.nom_marque)}{" "}
                  <span className="font-semibold text-muted">{formatDose(m.dosage_norm)}</span>
                </span>
                <span className="block text-[0.95rem] text-muted">
                  {formLabel(m.forme_groupe)} · {titleCase(m.molecule)}
                </span>
              </span>
              <ArrowRightIcon className="h-6 w-6 text-brand" />
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
