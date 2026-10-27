"use client";

import { useState } from "react";

import { BellIcon } from "../icons";
import { buttonClass, Field, inputClass, keepFocus, Notice } from "../ui";
import { api, errorMessage } from "@/lib/api";
import type { LatLng } from "@/lib/geo";
import { titleCase } from "@/lib/messages";
import { emailError } from "@/lib/validation";

interface Props {
  medicineId: string;
  medicineName: string;
  position: LatLng;
  radiusKm: number;
}

export function AlertForm({ medicineId, medicineName, position, radiusKm }: Props) {
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState(false);
  const [state, setState] = useState<{ status: "idle" | "sending" | "done" } | { status: "error"; message: string }>({
    status: "idle",
  });

  const error = touched ? emailError(email) : null;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (emailError(email)) return;
    setState({ status: "sending" });
    try {
      await api("/alerts", {
        method: "POST",
        body: { email: email.trim(), medicament_id: medicineId, lat: position.lat, lng: position.lng, rayon_km: radiusKm },
      });
      setState({ status: "done" });
    } catch (e) {
      setState({ status: "error", message: errorMessage(e) });
    }
  }

  return (
    <section aria-labelledby="alert" className="space-y-4 rounded-xl border border-line bg-surface p-4 sm:p-6">
      <h2 id="alert" className="flex items-center gap-2 text-2xl font-bold">
        <BellIcon className="h-6 w-6 text-brand" />
        Tell me when it’s back
      </h2>

      {state.status === "done" ? (
        <Notice tone="success" title="Your alert is saved" role="status">
          <p>
            We will email <strong>{email.trim()}</strong> once, when {titleCase(medicineName)} or an exact equivalent is
            declared in stock within {radiusKm} km.
          </p>
        </Notice>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-4">
          <p className="text-muted">
            Leave your email and we will tell you when a pharmacy near you has {titleCase(medicineName)} in stock.
            Your email is only used for this alert.
          </p>
          <Field label="Your email" error={error}>
            {(props) => (
              <input
                {...props}
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                onBlur={() => setTouched(true)}
                className={inputClass}
              />
            )}
          </Field>
          {state.status === "error" && (
            <Notice tone="danger" role="alert">
              <p>{state.message}</p>
            </Notice>
          )}
          <button type="submit" {...keepFocus} disabled={state.status === "sending"} className={buttonClass("primary", "lg")}>
            {state.status === "sending" ? "Saving…" : "Notify me"}
          </button>
        </form>
      )}
    </section>
  );
}
