"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { LocationPicker } from "../map";
import { buttonClass, ErrorState, Field, inputClass, keepFocus, Loading, Notice, PageTitle } from "../ui";
import { errorMessage } from "@/lib/api";
import { useAuthedApi } from "@/lib/auth";
import type { LatLng } from "@/lib/geo";
import type { Me, OwnPharmacy } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";
import { normalizePhone, phoneError, requiredError } from "@/lib/validation";

export function EditPharmacy() {
  const { ready, wrongRole, authApi, session } = useAuthedApi("pharmacien");
  const me = useAsync(
    (signal) => (session && !wrongRole ? authApi<Me>("/auth/me", { signal }) : new Promise<Me>(() => {})),
    [session?.token, wrongRole],
  );

  if (!ready || me.status === "loading") return <Loading />;
  if (wrongRole) return <Notice tone="info" title="This page is for pharmacists." />;
  if (me.status === "error") return <ErrorState message={errorMessage(me.error)} onRetry={me.reload} />;
  if (!me.data.pharmacie) return <Notice tone="danger" title="No pharmacy is linked to this account." />;

  return <EditForm pharmacy={me.data.pharmacie} authApi={authApi} />;
}

type AuthApi = ReturnType<typeof useAuthedApi>["authApi"];

function EditForm({ pharmacy, authApi }: { pharmacy: OwnPharmacy; authApi: AuthApi }) {
  const [phone, setPhone] = useState(pharmacy.telephone);
  const [hours, setHours] = useState(pharmacy.horaires ?? "");
  const [address, setAddress] = useState(pharmacy.adresse);
  const [position, setPosition] = useState<LatLng>({ lat: pharmacy.latitude, lng: pharmacy.longitude });
  const [submitted, setSubmitted] = useState(false);
  const [state, setState] = useState<
    { status: "idle" | "saving" } | { status: "saved"; pharmacy: OwnPharmacy } | { status: "error"; message: string }
  >({ status: "idle" });
  const onPosition = useCallback((p: LatLng) => setPosition(p), []);

  const moved =
    address.trim() !== pharmacy.adresse || position.lat !== pharmacy.latitude || position.lng !== pharmacy.longitude;
  const errors = { phone: phoneError(phone), address: requiredError(address, "The address") };

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSubmitted(true);
    if (errors.phone || errors.address) return;
    setState({ status: "saving" });
    try {
      const saved = await authApi<OwnPharmacy>("/pharmacist/pharmacy", {
        method: "PATCH",
        body: {
          telephone: normalizePhone(phone),
          horaires: hours.trim(),
          adresse: address.trim(),
          latitude: position.lat,
          longitude: position.lng,
        },
      });
      setState({ status: "saved", pharmacy: saved });
    } catch (e) {
      setState({ status: "error", message: errorMessage(e) });
    }
  }

  if (state.status === "saved") {
    const pending = state.pharmacy.statut === "en_attente" && pharmacy.statut !== "en_attente";
    return (
      <div className="mx-auto max-w-xl space-y-6">
        <PageTitle>Changes saved</PageTitle>
        {pending ? (
          <Notice tone="caution" title="Your pharmacy will be verified again" role="status">
            <p>You changed its address or position. Until our team checks it, patients do not see it.</p>
          </Notice>
        ) : (
          <Notice tone="success" title="Patients now see the new information" role="status" />
        )}
        <Link href="/pharmacien" className={buttonClass("primary", "lg")}>
          Back to my dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <PageTitle lead={pharmacy.nom}>Edit my pharmacy</PageTitle>

      <form onSubmit={save} noValidate className="space-y-5 rounded-xl border border-line bg-surface p-5">
        <Field label="Phone of the pharmacy" error={submitted ? errors.phone : null}>
          {(p) => (
            <input {...p} type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className={inputClass} />
          )}
        </Field>

        <Field label="Opening hours" hint="For example: 8:00 – 20:00, closed on Friday">
          {(p) => <input {...p} value={hours} onChange={(e) => setHours(e.target.value)} className={inputClass} />}
        </Field>

        <Field label="Address" error={submitted ? errors.address : null}>
          {(p) => (
            <input {...p} autoComplete="street-address" value={address} onChange={(e) => setAddress(e.target.value)} className={inputClass} />
          )}
        </Field>

        <fieldset className="space-y-3">
          <legend className="font-semibold">Position on the map</legend>
          <LocationPicker value={position} onChange={onPosition} label="Map to move the pharmacy" height="h-64" />
        </fieldset>

        {moved && pharmacy.statut === "validee" && (
          <Notice tone="caution" title="A new address or position must be checked again">
            <p>After saving, your pharmacy will be hidden from patients until our team verifies it.</p>
          </Notice>
        )}

        {state.status === "error" && (
          <Notice tone="danger" role="alert">
            <p>{state.message}</p>
          </Notice>
        )}

        <div className="flex flex-col-reverse gap-3 sm:flex-row">
          <Link href="/pharmacien" className={buttonClass("secondary", "lg")}>
            Cancel
          </Link>
          <button type="submit" {...keepFocus} disabled={state.status === "saving"} className={buttonClass("primary", "lg", "flex-1")}>
            {state.status === "saving" ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
