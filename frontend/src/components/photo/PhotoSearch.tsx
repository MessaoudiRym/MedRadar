"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import { AlertIcon, ArrowRightIcon, CameraIcon, CheckIcon, ImageIcon, InfoIcon, QuestionIcon } from "../icons";
import { buttonClass, Loading, Notice } from "../ui";
import { api } from "@/lib/api";
import { formatDose } from "@/lib/format";
import { formLabel, titleCase } from "@/lib/messages";
import { compressPhoto, describeReading, photoProblem, recognizePhoto, type PhotoProblem } from "@/lib/photo";
import type { Correspondence, Features, Recognition } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

type Step =
  | { name: "idle" }
  | { name: "preview"; photo: Blob; url: string }
  | { name: "reading"; url: string }
  | { name: "result"; url: string; data: Recognition }
  | { name: "error"; url: string | null; problem: PhotoProblem };

const BADGES: Record<Correspondence, { label: string; className: string; icon: React.ReactNode }> = {
  exacte: {
    label: "Exact match",
    className: "bg-stock-soft text-stock border-stock-line",
    icon: <CheckIcon className="h-4 w-4" />,
  },
  probable: {
    label: "Likely match",
    className: "bg-brand-soft text-brand border-brand/40",
    icon: <InfoIcon className="h-4 w-4" />,
  },
  "à vérifier": {
    label: "Check the box",
    className: "bg-caution-soft text-caution border-caution-line",
    icon: <QuestionIcon className="h-4 w-4" />,
  },
};

const REMINDER = "Photograph the box, not the prescription.";

/**
 * Find a medicine from a photo of its box. MedRadar reads the box and proposes
 * medicines from the official list: the patient always confirms. Hidden when
 * the API has photo recognition turned off.
 */
export function PhotoSearch({ onTypeName }: { onTypeName: () => void }) {
  const features = useAsync((signal) => api<Features>("/features", { signal }), []);
  if (features.status !== "success" || !features.data.photo_recognition) return null;
  return <PhotoFlow onTypeName={onTypeName} />;
}

function PhotoFlow({ onTypeName }: { onTypeName: () => void }) {
  const id = useId();
  const [step, setStep] = useState<Step>({ name: "idle" });
  const camera = useRef<HTMLInputElement>(null);
  const gallery = useRef<HTMLInputElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const request = useRef<AbortController | null>(null);

  const url = step.name === "idle" ? null : step.url;

  // The photo stays in this page only: its preview is freed as soon as it changes
  useEffect(() => {
    if (!url) return;
    return () => URL.revokeObjectURL(url);
  }, [url]);

  // Each new step is announced to screen readers and keyboard users
  useEffect(() => {
    if (step.name !== "idle" && step.name !== "reading") heading.current?.focus();
  }, [step.name]);

  useEffect(() => () => request.current?.abort(), []);

  async function choose(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same photo can be chosen again
    if (!file) return;
    const photo = await compressPhoto(file);
    setStep({ name: "preview", photo, url: URL.createObjectURL(photo) });
  }

  async function read(photo: Blob, url: string) {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setStep({ name: "reading", url });
    try {
      const data = await recognizePhoto(photo, controller.signal);
      setStep({ name: "result", url, data });
    } catch (error) {
      if (controller.signal.aborted) return;
      setStep({ name: "error", url, problem: photoProblem(error) });
    }
  }

  function cancel() {
    request.current?.abort();
    setStep({ name: "idle" });
  }

  function retake() {
    setStep({ name: "idle" });
    camera.current?.click();
  }

  const inputs = (
    <>
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        aria-hidden="true"
        tabIndex={-1}
        onChange={choose}
        data-testid="photo-camera"
      />
      <input
        ref={gallery}
        type="file"
        accept="image/*"
        hidden
        aria-hidden="true"
        tabIndex={-1}
        onChange={choose}
        data-testid="photo-gallery"
      />
    </>
  );

  const typeNameButton = (
    <button type="button" onClick={onTypeName} className={buttonClass("secondary", "md", "w-full sm:w-auto")}>
      None of these, I’ll type the name
    </button>
  );

  return (
    <section aria-labelledby={`${id}-title`} className="space-y-4">
      {inputs}
      <div className="flex items-center gap-3 text-muted" aria-hidden="true">
        <span className="h-px flex-1 bg-line" />
        <span className="font-semibold">or</span>
        <span className="h-px flex-1 bg-line" />
      </div>
      <h2 id={`${id}-title`} className="sr-only">
        Find a medicine from a photo of its box
      </h2>

      {step.name === "idle" && (
        <div className="space-y-3">
          <button
            type="button"
            onClick={() => camera.current?.click()}
            className={buttonClass("secondary", "lg", "w-full")}
          >
            <CameraIcon className="h-6 w-6" />
            Take a photo of the box
          </button>
          <div className="flex flex-col items-center gap-1 text-center">
            <button
              type="button"
              onClick={() => gallery.current?.click()}
              className="inline-flex min-h-11 items-center gap-2 font-semibold text-brand underline underline-offset-4"
            >
              <ImageIcon className="h-5 w-5" />
              Choose a photo from the gallery
            </button>
            <p className="text-[0.95rem] text-muted">{REMINDER}</p>
          </div>
        </div>
      )}

      {step.name !== "idle" && (
        <div className="space-y-4 rounded-xl border-2 border-line bg-surface p-4 sm:p-5">
          {step.url && (
            // eslint-disable-next-line @next/next/no-img-element -- a local photo, never sent to an image service
            <img
              src={step.url}
              alt="Your photo of the medicine box"
              className="mx-auto max-h-56 w-auto rounded-lg border border-line object-contain"
            />
          )}

          {step.name === "preview" && (
            <>
              <h3 ref={heading} tabIndex={-1} className="text-xl font-bold">
                Is the name of the medicine easy to read?
              </h3>
              <Notice tone="caution">
                <p className="font-semibold">{REMINDER}</p>
                <p>The photo is only used to read the box. MedRadar does not keep it.</p>
              </Notice>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => read(step.photo, step.url)}
                  className={buttonClass("primary", "lg", "w-full sm:w-auto")}
                >
                  Read this box
                </button>
                <button type="button" onClick={retake} className={buttonClass("ghost", "md", "w-full sm:w-auto")}>
                  Take another photo
                </button>
              </div>
            </>
          )}

          {step.name === "reading" && (
            <div className="space-y-2">
              <Loading label="Reading the box…" />
              <button type="button" onClick={cancel} className={buttonClass("ghost", "sm")}>
                Cancel
              </button>
            </div>
          )}

          {step.name === "result" && (
            <Result data={step.data} heading={heading} typeNameButton={typeNameButton} onRetake={retake} />
          )}

          {step.name === "error" && (
            <div className="space-y-4">
              <div role="alert" className="flex gap-3 rounded-xl border-2 border-out-line bg-out-soft p-4">
                <AlertIcon className="mt-0.5 h-6 w-6 text-out" />
                <div className="space-y-1">
                  <h3 ref={heading} tabIndex={-1} className="font-bold">
                    {step.problem.title}
                  </h3>
                  <p>{step.problem.text}</p>
                </div>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button type="button" onClick={onTypeName} className={buttonClass("primary", "md", "w-full sm:w-auto")}>
                  Type the name instead
                </button>
                {step.problem.retry && (
                  <button type="button" onClick={retake} className={buttonClass("secondary", "md", "w-full sm:w-auto")}>
                    Take another photo
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function Result({
  data,
  heading,
  typeNameButton,
  onRetake,
}: {
  data: Recognition;
  heading: React.RefObject<HTMLHeadingElement | null>;
  typeNameButton: React.ReactNode;
  onRetake: () => void;
}) {
  const read = describeReading(data.texte_lu);
  return (
    <div className="space-y-4">
      <p className="text-lg">
        We read: <strong className="break-words">{read}</strong>
      </p>

      {data.resultats.length === 0 ? (
        <Notice tone="info" title="No medicine in the official list matches">
          <p>Check the name on the box and type it in the search.</p>
        </Notice>
      ) : (
        <>
          <h3 ref={heading} tabIndex={-1} className="text-xl font-bold">
            Is this your medicine?
          </h3>
          <ul className="space-y-3">
            {data.resultats.map((m) => {
              const badge = BADGES[m.correspondance];
              return (
                <li key={m.id}>
                  <Link
                    href={`/medicament/${m.id}`}
                    className="flex min-h-20 items-center justify-between gap-3 rounded-xl border-2 border-line bg-surface p-4 text-ink no-underline hover:border-brand"
                  >
                    <span className="min-w-0 space-y-1.5">
                      <span className="block text-lg font-bold">
                        {titleCase(m.nom_marque)}{" "}
                        <span className="font-semibold text-muted">{formatDose(m.dosage_norm)}</span>
                      </span>
                      <span className="block text-[0.95rem] text-muted">
                        {formLabel(m.forme_groupe)} · {titleCase(m.molecule)}
                      </span>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[0.95rem] font-bold ${badge.className}`}
                      >
                        {badge.icon}
                        {badge.label}
                      </span>
                    </span>
                    <ArrowRightIcon className="h-6 w-6 text-brand" />
                  </Link>
                </li>
              );
            })}
          </ul>
          <p className="text-muted">Compare with your box: the name, the dose and the form must be the same.</p>
        </>
      )}

      {data.resultats.length === 0 && (
        <h3 ref={heading} tabIndex={-1} className="sr-only">
          No match for this photo
        </h3>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        {typeNameButton}
        <button type="button" onClick={onRetake} className={buttonClass("ghost", "md", "w-full sm:w-auto")}>
          Take another photo
        </button>
      </div>
    </div>
  );
}
