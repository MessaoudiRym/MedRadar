// Delivery notes (pharmacists): the model reads the note, the API matches each
// line to the official list, the pharmacist checks and confirms. Nothing is put
// in stock without the confirmation; prices are never kept.

import { api, ApiError, NETWORK_ERROR } from "./api";
import { compressPhoto } from "./photo";
import type { ConfirmLine, LineAction, MedicineSummary, ScanLine, ScanResult } from "./types";

export const MAX_PAGES = 5;
const MAX_SIDE = 2000;
// Reading a full note can take up to 60 s on the API side
const SCAN_TIMEOUT_MS = 75_000;
export const DEMO_NOTE_URL = "/demo/bon-livraison-demo.png";

export type AuthApi = <T>(path: string, options?: Parameters<typeof api>[1]) => Promise<T>;

export function compressPages(files: Blob[]): Promise<Blob[]> {
  return Promise.all(files.map((file) => compressPhoto(file, MAX_SIDE)));
}

export function scanNote(authApi: AuthApi, pages: Blob[], signal?: AbortSignal): Promise<ScanResult> {
  const form = new FormData();
  pages.forEach((page, i) => form.append("pages", page, `page-${i + 1}.jpg`));
  return authApi<ScanResult>("/pharmacist/delivery-scan", {
    method: "POST",
    body: form,
    signal,
    timeoutMs: SCAN_TIMEOUT_MS,
  });
}

const PROBLEMS: Record<string, string> = {
  pas_un_bon: "This does not look like a delivery note. Take a photo of the note you received with your order.",
  saturee: "Reading is busy right now. Try again in a minute.",
  delai: "Reading the note took too long. Try again with a sharper photo or fewer pages.",
  echec: "We couldn't read this note. Try again with a sharper photo, or update your stock by hand.",
  limite: "You have scanned 20 notes today. Update your stock by hand, or try again tomorrow.",
  desactivee: "Reading delivery notes is not available. Update your stock by hand.",
  trop_lourde: "A photo is too large (8 MB per page). Take a lighter photo.",
  trop_de_pages: "Five pages at most per note.",
  format: "One of the files is not a photo we can read. Use JPEG, PNG or WebP photos.",
};

export function scanProblem(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.isNetwork) return NETWORK_ERROR;
    const known = PROBLEMS[error.code ?? ""];
    if (known) return known;
    if (error.status === 410) return "This reading expired (1 hour). Scan the note again.";
    if (error.status === 409) return "This note was already confirmed.";
    if (error.status === 403) return error.message;
  }
  return PROBLEMS.echec;
}

/** What the pharmacist decided for one line of the note. */
export interface LineChoice {
  medicine: MedicineSummary | null;
  /** Put in stock */
  checked: boolean;
  /** Not delivered: declare out of stock instead */
  outOfStock: boolean;
}

export function initialChoice(line: ScanLine): LineChoice {
  return {
    // A line to check has no medicine until the pharmacist chooses one
    medicine: line.correspondance === "a_verifier" ? null : line.medicament,
    checked: line.coche,
    outOfStock: false,
  };
}

export function lineAction(choice: LineChoice): LineAction {
  if (!choice.medicine) return "ignoree";
  if (choice.checked) return "en_stock";
  return choice.outOfStock ? "rupture" : "ignoree";
}

export function confirmLines(lines: ScanLine[], choices: LineChoice[]): ConfirmLine[] {
  return lines.map((line, i) => ({
    ligne: line.index,
    designation_lue: line.designation,
    medicament_id: choices[i].medicine?.id ?? null,
    quantite: line.quantite,
    numero_lot: line.numero_lot,
    date_peremption: line.date_peremption,
    action: lineAction(choices[i]),
  }));
}

/** Medicines that will be in stock / out of stock (a medicine on two lines counts once). */
export function countActions(choices: LineChoice[]) {
  const inStock = new Set<string>();
  const out = new Set<string>();
  for (const choice of choices) {
    const action = lineAction(choice);
    if (action === "en_stock") inStock.add(choice.medicine!.id);
    else if (action === "rupture") out.add(choice.medicine!.id);
  }
  for (const id of inStock) out.delete(id);
  return { inStock: inStock.size, outOfStock: out.size };
}

/** "2028-05" -> "05/2028" */
export function formatExpiry(value: string | null): string | null {
  return value ? `${value.slice(5, 7)}/${value.slice(0, 4)}` : null;
}

/** "2026-10-22" or an ISO date-time -> "22/10/2026" */
export function formatDay(value: string): string {
  return new Date(value.length === 10 ? `${value}T12:00:00` : value).toLocaleDateString("en-GB");
}

export function formatQuantity(value: number | null): string | null {
  if (value === null) return null;
  return `${Number.isInteger(value) ? value : value.toFixed(1)} box${value === 1 ? "" : "es"}`;
}

export function downloadFile(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function isDemoAccount(email: string | undefined): boolean {
  return Boolean(email?.endsWith("@medradar.demo"));
}
