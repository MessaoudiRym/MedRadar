// Photo of a medicine box: compressed in the browser, then read by the API.
// The API reads the box with a vision model, searches the official list and
// proposes medicines; the patient chooses. The photo is never stored.

import { api, ApiError, NETWORK_ERROR } from "./api";
import type { Recognition } from "./types";

export const MAX_SIDE = 1600;
const JPEG_QUALITY = 0.85;
// The model can take up to 30 s; the upload on a slow connection takes time too
const RECOGNIZE_TIMEOUT_MS = 45_000;

/**
 * JPEG, at most maxSide px (1600 by default) on the longest side, upright. Drawing on a canvas also
 * drops the metadata (a phone photo can contain the GPS position).
 * A file the browser cannot draw is sent as is: the API checks its real type.
 */
export async function compressPhoto(file: Blob, maxSide = MAX_SIDE): Promise<Blob> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    return file;
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const context = canvas.getContext("2d");
  if (!context) {
    bitmap.close();
    return file;
  }
  context.fillStyle = "#ffffff"; // transparent parts become white, not black
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob ?? file), "image/jpeg", JPEG_QUALITY));
}

export function recognizePhoto(photo: Blob, signal?: AbortSignal): Promise<Recognition> {
  const form = new FormData();
  form.append("photo", photo, "boite.jpg");
  return api<Recognition>("/medicines/recognize", {
    method: "POST",
    body: form,
    signal,
    timeoutMs: RECOGNIZE_TIMEOUT_MS,
  });
}

export interface PhotoProblem {
  title: string;
  text: string;
  /** false when another photo cannot help (prescription aside, the patient can always retry) */
  retry: boolean;
}

const PROBLEMS: Record<string, PhotoProblem> = {
  ordonnance: {
    title: "This looks like a prescription",
    text: "To protect your privacy, photograph the medicine box, not the prescription.",
    retry: true,
  },
  illisible: {
    title: "We can’t read this box",
    text: "Try a sharper photo, in good light, with the name of the medicine facing you. Or type the name.",
    retry: true,
  },
  trop_lourde: {
    title: "This photo is too large",
    text: "Photos can be up to 5 MB. Take another photo, or type the name.",
    retry: true,
  },
  format: {
    title: "This file is not a photo we can read",
    text: "Use a JPEG, PNG or WebP photo, or type the name.",
    retry: true,
  },
  limite: {
    title: "Photo limit reached",
    text: "You can send 10 photos per hour. Type the name of the medicine, or try again later.",
    retry: false,
  },
  saturee: {
    title: "Photo reading is busy",
    text: "Photo reading is busy right now. Type the name of the medicine, or try again in a minute.",
    retry: true,
  },
  delai: {
    title: "Reading took too long",
    text: "Try again, or type the name of the medicine.",
    retry: true,
  },
  echec: {
    title: "We couldn’t read this photo",
    text: "Try again, or type the name of the medicine.",
    retry: true,
  },
  desactivee: {
    title: "Photo reading is not available",
    text: "Type the name of the medicine.",
    retry: false,
  },
};

const BY_STATUS: Record<number, string> = { 413: "trop_lourde", 415: "format", 429: "limite", 503: "saturee", 504: "delai" };

export function photoProblem(error: unknown): PhotoProblem {
  if (error instanceof ApiError) {
    if (error.isNetwork) return { title: "No connection", text: NETWORK_ERROR, retry: true };
    const problem = PROBLEMS[error.code ?? ""] ?? PROBLEMS[BY_STATUS[error.status] ?? ""];
    if (problem) return problem;
  }
  return PROBLEMS.echec;
}

/** "GLUCOPHAGE 850 mg, comprimé pelliculé": what was read, as printed on the box. */
export function describeReading(read: Recognition["texte_lu"]): string {
  const name = [read.nom_marque ?? read.dci, read.dosage].filter(Boolean).join(" ");
  return [name, read.forme].filter(Boolean).join(", ");
}
