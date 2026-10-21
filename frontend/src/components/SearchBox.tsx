"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { SearchIcon } from "./icons";
import { buttonClass, inputClass, Loading, Notice } from "./ui";
import { api, errorMessage } from "@/lib/api";
import { formatDose } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import type { MedicineSummary } from "@/lib/types";

const DEBOUNCE_MS = 250;
const MIN_LENGTH = 2;

type Results =
  | { status: "idle" }
  | { status: "loading"; query: string }
  | { status: "done"; query: string; items: MedicineSummary[] }
  | { status: "error"; query: string; message: string };

interface SearchBoxProps {
  label?: string;
  placeholder?: string;
  /** Called with the chosen medicine. Without it, the medicine page opens. */
  onSelect?: (medicine: MedicineSummary) => void;
  size?: "lg" | "md";
  /** To focus the field from outside (e.g. "I'll type the name" after a photo) */
  inputRef?: React.Ref<HTMLInputElement>;
  /** Text already searched (results page): no suggestions until it is changed */
  initialQuery?: string;
}

/**
 * Search with suggestions while typing (accessible combobox).
 * The API tolerates typos ("glucofage" finds GLUCOPHAGE) and reads Arabic,
 * Darija and English names. Suggestions never use the language model; Enter
 * or the Search button opens the full search (/recherche), which may.
 * With onSelect (pharmacist's list), Enter picks the first suggestion instead.
 */
export function SearchBox({
  label = "Name of the medicine or active ingredient",
  placeholder = "Medicine name (French, Arabic, Darija…)",
  onSelect,
  size = "lg",
  inputRef,
  initialQuery = "",
}: SearchBoxProps) {
  const router = useRouter();
  const id = useId();
  const listId = `${id}-list`;
  const [query, setQuery] = useState(initialQuery);
  const [edited, setEdited] = useState(!initialQuery);
  const [results, setResults] = useState<Results>({ status: "idle" });
  const [active, setActive] = useState(-1);
  const [retry, setRetry] = useState(0);

  const trimmed = query.trim();

  useEffect(() => {
    if (!edited || trimmed.length < MIN_LENGTH) return;
    const controller = new AbortController();
    // Wait until the user stops typing, then cancel any older request
    const timer = setTimeout(() => {
      setResults({ status: "loading", query: trimmed });
      api<MedicineSummary[]>("/medicines/search", {
        query: { q: trimmed, limit: 8 },
        signal: controller.signal,
      })
        .then((items) => {
          setResults({ status: "done", query: trimmed, items });
          setActive(-1);
        })
        .catch((error) => {
          if (!controller.signal.aborted) setResults({ status: "error", query: trimmed, message: errorMessage(error) });
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [trimmed, retry, edited]);

  const shown = edited && trimmed.length >= MIN_LENGTH ? results : ({ status: "idle" } as Results);
  const items = shown.status === "done" ? shown.items : [];
  const open = items.length > 0;

  function choose(medicine: MedicineSummary) {
    if (onSelect) {
      onSelect(medicine);
      setQuery("");
      setResults({ status: "idle" });
    } else {
      router.push(`/medicament/${medicine.id}`);
    }
  }

  /** Full search: the API may then use the language model (Arabic, Darija, English). */
  function submit() {
    if (trimmed.length < MIN_LENGTH) return;
    setResults({ status: "idle" });
    setEdited(false);
    router.push(`/recherche?q=${encodeURIComponent(trimmed)}`);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" && !onSelect) {
      event.preventDefault();
      if (open && active >= 0) choose(items[active]);
      else submit();
      return;
    }
    if (!open) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (event.key === "Enter") {
      event.preventDefault();
      choose(items[active >= 0 ? active : 0]);
    } else if (event.key === "Escape") {
      setResults({ status: "idle" });
    }
  }

  return (
    <div className="space-y-3">
      <label htmlFor={`${id}-input`} className={`block font-bold ${size === "lg" ? "text-lg" : ""}`}>
        {label}
      </label>
      <div className={onSelect ? "" : "flex gap-2"}>
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-4 h-6 w-6 -translate-y-1/2 text-muted" />
          <input
            ref={inputRef}
            id={`${id}-input`}
            type="search"
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="search"
            value={query}
            placeholder={placeholder}
            dir="auto"
            onChange={(e) => {
              setQuery(e.target.value);
              setEdited(true);
            }}
            onKeyDown={onKeyDown}
            className={`${inputClass} pl-13 ${size === "lg" ? "min-h-15 text-lg shadow-sm" : ""}`}
          />
        </div>
        {!onSelect && (
          <button
            type="button"
            onClick={submit}
            className={buttonClass("primary", size === "lg" ? "lg" : "md", "shrink-0")}
          >
            Search
          </button>
        )}
      </div>

      <div aria-live="polite" className="sr-only">
        {shown.status === "done" &&
          (items.length ? `${items.length} medicines found. Use the arrow keys to choose.` : "No medicine found.")}
      </div>

      {shown.status === "loading" && <Loading label="Searching…" />}

      {shown.status === "error" && (
        <Notice tone="danger" title="The search is not available" role="alert">
          <p>{shown.message}</p>
          <button type="button" className="font-semibold text-brand underline" onClick={() => setRetry((n) => n + 1)}>
            Try again
          </button>
        </Notice>
      )}

      {shown.status === "done" && items.length === 0 && (
        <Notice tone="info" title={`No medicine found for “${shown.query}”`}>
          <p>
            Check the spelling, or search by the active ingredient written on the box, under the
            brand name (for example “metformine” or “amlodipine”).
          </p>
        </Notice>
      )}

      <ul
        id={listId}
        role="listbox"
        aria-label="Suggestions"
        hidden={!open}
        className="divide-y divide-line overflow-hidden rounded-xl border-2 border-line bg-surface"
      >
        {items.map((m, i) => (
          <li
            key={m.id}
            id={`${listId}-${i}`}
            role="option"
            aria-selected={i === active}
            onClick={() => choose(m)}
            onMouseEnter={() => setActive(i)}
            className={`flex cursor-pointer items-center justify-between gap-3 px-4 py-3 ${
              i === active ? "bg-brand-soft" : ""
            }`}
          >
            <span className="min-w-0">
              <span className="block font-bold">
                {titleCase(m.nom_marque)} <span className="font-semibold text-muted">{formatDose(m.dosage_norm)}</span>
              </span>
              <span className="block text-[0.95rem] text-muted">
                {formLabel(m.forme_groupe)} · {titleCase(m.molecule)}
              </span>
            </span>
            <span className="shrink-0 text-right text-[0.9rem] text-muted">
              {m.nb_equivalents > 0
                ? `${m.nb_equivalents} equivalent${m.nb_equivalents > 1 ? "s" : ""}`
                : "No equivalent"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
