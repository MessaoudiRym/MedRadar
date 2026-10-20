"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";

import { CheckIcon, LocateIcon } from "../icons";
import { LocationPicker } from "../map";
import { buttonClass, Field, inputClass, keepFocus, Notice } from "../ui";
import { api, ApiError, errorMessage } from "@/lib/api";
import { type LatLng, ORAN_CENTER, ORAN_DISTRICTS } from "@/lib/geo";
import { emailError, normalizePhone, passwordError, phoneError, requiredError } from "@/lib/validation";

type Account = { email: string; password: string; lastName: string; firstName: string; phone: string };
type Pharmacy = {
  name: string;
  address: string;
  commune: string;
  district: string;
  phone: string;
  professionalNumber: string;
  hours: string;
  position: LatLng;
};
type Errors = Record<string, string | null>;

function accountErrors(a: Account): Errors {
  return {
    email: emailError(a.email),
    password: passwordError(a.password),
    lastName: requiredError(a.lastName, "Your last name"),
    firstName: requiredError(a.firstName, "Your first name"),
    phone: phoneError(a.phone),
  };
}

function pharmacyErrors(p: Pharmacy): Errors {
  return {
    name: requiredError(p.name, "The name of the pharmacy"),
    address: requiredError(p.address, "The address"),
    commune: requiredError(p.commune, "The commune"),
    district: requiredError(p.district, "The district"),
    phone: phoneError(p.phone),
    professionalNumber:
      p.professionalNumber.trim().length >= 3 ? null : "Enter the professional number of the pharmacy.",
  };
}

const hasErrors = (errors: Errors) => Object.values(errors).some(Boolean);

function without(errors: Record<string, string>, key: string) {
  if (!(key in errors)) return errors;
  const copy = { ...errors };
  delete copy[key];
  return copy;
}

// API field name -> [step, form field]
const API_FIELDS: Record<string, [1 | 2, string]> = {
  email: [1, "email"],
  mot_de_passe: [1, "password"],
  nom: [1, "lastName"],
  prenom: [1, "firstName"],
  telephone: [1, "phone"],
  "pharmacie.nom": [2, "name"],
  "pharmacie.adresse": [2, "address"],
  "pharmacie.commune": [2, "commune"],
  "pharmacie.quartier": [2, "district"],
  "pharmacie.telephone": [2, "phone"],
  "pharmacie.numero_professionnel": [2, "professionalNumber"],
  "pharmacie.latitude": [2, "position"],
  pharmacie: [2, "position"],
};

export function RegisterForm() {
  const id = useId();
  const [step, setStep] = useState<1 | 2 | "done">(1);
  const [account, setAccount] = useState<Account>({ email: "", password: "", lastName: "", firstName: "", phone: "" });
  const [pharmacy, setPharmacy] = useState<Pharmacy>({
    name: "",
    address: "",
    commune: "Oran",
    district: "",
    phone: "",
    professionalNumber: "",
    hours: "",
    position: ORAN_CENTER,
  });
  // Errors are shown once a field was left, or after pressing Continue
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitted, setSubmitted] = useState<Record<number, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => headingRef.current?.focus(), [step]);

  const aErrors = accountErrors(account);
  const pErrors = pharmacyErrors(pharmacy);

  const shown = (stepNumber: 1 | 2, field: string, errors: Errors) => {
    const key = `${stepNumber}.${field}`;
    if (serverErrors[key]) return serverErrors[key];
    return touched[key] || submitted[stepNumber] ? errors[field] : null;
  };

  const touch = (stepNumber: 1 | 2, field: string) => () => setTouched((t) => ({ ...t, [`${stepNumber}.${field}`]: true }));

  function updateAccount(field: keyof Account, value: string) {
    setAccount((a) => ({ ...a, [field]: value }));
    setServerErrors((errors) => without(errors, `1.${field}`));
  }

  function updatePharmacy<K extends keyof Pharmacy>(field: K, value: Pharmacy[K]) {
    setPharmacy((p) => ({ ...p, [field]: value }));
    setServerErrors((errors) => without(errors, `2.${String(field)}`));
  }

  const setPosition = useCallback((position: LatLng) => updatePharmacy("position", position), []);

  function next(event: React.FormEvent) {
    event.preventDefault();
    setSubmitted((s) => ({ ...s, 1: true }));
    if (!hasErrors(aErrors)) setStep(2);
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitted((s) => ({ ...s, 2: true }));
    if (hasErrors(pErrors)) return;
    setSending(true);
    setFormError(null);
    try {
      await api("/auth/register-pharmacist", {
        method: "POST",
        body: {
          email: account.email.trim(),
          mot_de_passe: account.password,
          nom: account.lastName.trim(),
          prenom: account.firstName.trim(),
          telephone: normalizePhone(account.phone),
          pharmacie: {
            nom: pharmacy.name.trim(),
            adresse: pharmacy.address.trim(),
            commune: pharmacy.commune.trim(),
            quartier: pharmacy.district.trim(),
            latitude: pharmacy.position.lat,
            longitude: pharmacy.position.lng,
            telephone: normalizePhone(pharmacy.phone),
            numero_professionnel: pharmacy.professionalNumber.trim(),
            horaires: pharmacy.hours.trim() || null,
          },
        },
      });
      setStep("done");
    } catch (e) {
      handleServerError(e);
    } finally {
      setSending(false);
    }
  }

  function handleServerError(e: unknown) {
    if (!(e instanceof ApiError)) return setFormError(errorMessage(e));
    if (e.status === 409 && e.message.includes("email")) {
      setServerErrors({ "1.email": e.message });
      setStep(1);
      return;
    }
    if (e.status === 409) return setServerErrors({ "2.professionalNumber": e.message });
    const mapped: Record<string, string> = {};
    let firstStep: 1 | 2 | null = null;
    for (const [apiField, message] of Object.entries(e.fieldErrors)) {
      const target = API_FIELDS[apiField];
      if (!target) continue;
      mapped[`${target[0]}.${target[1]}`] = message;
      firstStep = firstStep === 1 ? 1 : target[0];
    }
    if (firstStep) {
      setServerErrors(mapped);
      setStep(firstStep);
    } else {
      setFormError(e.message);
    }
  }

  function locate() {
    navigator.geolocation?.getCurrentPosition(
      (pos) => setPosition({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => setFormError("We could not get your position. Place the marker on the map instead."),
      { timeout: 10_000 },
    );
  }

  if (step === "done") {
    return (
      <div className="mx-auto max-w-xl space-y-6">
        <h1 ref={headingRef} tabIndex={-1} className="text-[1.9rem] leading-tight font-bold sm:text-4xl">
          Your account has been created
        </h1>
        <Notice tone="success" title="Your pharmacy is waiting for verification" role="status">
          <p>
            It will be visible to patients once our team has checked it (name, address, phone and professional
            number). We may call you at {account.phone}.
          </p>
          <p>Meanwhile, you can log in and see the status of your pharmacy.</p>
        </Notice>
        <Link href="/pharmacien/connexion" className={buttonClass("primary", "lg")}>
          Go to the login page
        </Link>
      </div>
    );
  }

  const passwordRules = [
    { ok: new TextEncoder().encode(account.password).length >= 8, label: "At least 8 characters" },
    { ok: /[A-Za-z]/.test(account.password), label: "At least one letter" },
    { ok: /\d/.test(account.password), label: "At least one number" },
  ];

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="space-y-2">
        <p className="font-semibold text-brand">Step {step} of 2</p>
        <h1 ref={headingRef} tabIndex={-1} className="text-[1.9rem] leading-tight font-bold sm:text-4xl">
          {step === 1 ? "Create your account" : "Your pharmacy"}
        </h1>
        <p className="text-lg text-muted">
          {step === 1
            ? "Register your pharmacy so patients can see what you have in stock."
            : "Patients will see this information once your pharmacy is verified."}
        </p>
      </div>

      {formError && (
        <Notice tone="danger" role="alert">
          <p>{formError}</p>
        </Notice>
      )}

      {step === 1 ? (
        <form onSubmit={next} noValidate className="space-y-5 rounded-xl border border-line bg-surface p-5">
          <Field label="Email" error={shown(1, "email", aErrors)}>
            {(p) => (
              <input {...p} type="email" inputMode="email" autoComplete="email" value={account.email}
                onChange={(e) => updateAccount("email", e.target.value)} onBlur={touch(1, "email")} className={inputClass} />
            )}
          </Field>

          <Field label="Password" error={shown(1, "password", aErrors)}>
            {(p) => (
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input {...p} type={showPassword ? "text" : "password"} autoComplete="new-password" value={account.password}
                    onChange={(e) => updateAccount("password", e.target.value)} onBlur={touch(1, "password")} className={inputClass} />
                  <button type="button" onClick={() => setShowPassword((v) => !v)} aria-pressed={showPassword}
                    className={buttonClass("secondary", "md", "shrink-0")}>
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
                <ul className="space-y-1 text-[0.95rem]" aria-label="Password rules">
                  {passwordRules.map((rule) => (
                    <li key={rule.label} className={`flex items-center gap-2 ${rule.ok ? "text-stock" : "text-muted"}`}>
                      {rule.ok ? <CheckIcon className="h-4 w-4" /> : <span className="h-4 w-4 rounded-full border-2 border-current" aria-hidden />}
                      {rule.label}
                      <span className="sr-only">{rule.ok ? "(done)" : "(missing)"}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="First name" error={shown(1, "firstName", aErrors)}>
              {(p) => (
                <input {...p} autoComplete="given-name" value={account.firstName}
                  onChange={(e) => updateAccount("firstName", e.target.value)} onBlur={touch(1, "firstName")} className={inputClass} />
              )}
            </Field>
            <Field label="Last name" error={shown(1, "lastName", aErrors)}>
              {(p) => (
                <input {...p} autoComplete="family-name" value={account.lastName}
                  onChange={(e) => updateAccount("lastName", e.target.value)} onBlur={touch(1, "lastName")} className={inputClass} />
              )}
            </Field>
          </div>

          <Field label="Your mobile phone" hint="So that our team can reach you during the verification." error={shown(1, "phone", aErrors)}>
            {(p) => (
              <input {...p} type="tel" inputMode="tel" autoComplete="tel" placeholder="0550 12 34 56" value={account.phone}
                onChange={(e) => updateAccount("phone", e.target.value)} onBlur={touch(1, "phone")} className={inputClass} />
            )}
          </Field>

          <button type="submit" {...keepFocus} className={buttonClass("primary", "lg", "w-full")}>
            Continue
          </button>
          <p className="text-center">
            Already registered?{" "}
            <Link href="/pharmacien/connexion" className="font-semibold text-brand underline">Log in</Link>
          </p>
        </form>
      ) : (
        <form onSubmit={submit} noValidate className="space-y-5 rounded-xl border border-line bg-surface p-5">
          <Field label="Name of the pharmacy" error={shown(2, "name", pErrors)}>
            {(p) => (
              <input {...p} autoComplete="organization" value={pharmacy.name}
                onChange={(e) => updatePharmacy("name", e.target.value)} onBlur={touch(2, "name")} className={inputClass} />
            )}
          </Field>

          <Field label="Address" error={shown(2, "address", pErrors)}>
            {(p) => (
              <input {...p} autoComplete="street-address" value={pharmacy.address}
                onChange={(e) => updatePharmacy("address", e.target.value)} onBlur={touch(2, "address")} className={inputClass} />
            )}
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Commune" error={shown(2, "commune", pErrors)}>
              {(p) => (
                <input {...p} value={pharmacy.commune}
                  onChange={(e) => updatePharmacy("commune", e.target.value)} onBlur={touch(2, "commune")} className={inputClass} />
              )}
            </Field>
            <Field label="District" error={shown(2, "district", pErrors)}>
              {(p) => (
                <>
                  <input {...p} list={`${id}-districts`} value={pharmacy.district}
                    onChange={(e) => updatePharmacy("district", e.target.value)} onBlur={touch(2, "district")} className={inputClass} />
                  <datalist id={`${id}-districts`}>
                    {ORAN_DISTRICTS.map((d) => <option key={d.name} value={d.name} />)}
                  </datalist>
                </>
              )}
            </Field>
          </div>

          <Field label="Phone of the pharmacy" hint="Shown to patients, so they can call before coming." error={shown(2, "phone", pErrors)}>
            {(p) => (
              <input {...p} type="tel" inputMode="tel" placeholder="041 23 45 67" value={pharmacy.phone}
                onChange={(e) => updatePharmacy("phone", e.target.value)} onBlur={touch(2, "phone")} className={inputClass} />
            )}
          </Field>

          <Field label="Professional number" hint="Used only to check that the pharmacy is real. Never shown to patients."
            error={shown(2, "professionalNumber", pErrors)}>
            {(p) => (
              <input {...p} value={pharmacy.professionalNumber}
                onChange={(e) => updatePharmacy("professionalNumber", e.target.value)} onBlur={touch(2, "professionalNumber")} className={inputClass} />
            )}
          </Field>

          <Field label="Opening hours (optional)" hint="For example: 8:00 – 20:00, closed on Friday">
            {(p) => (
              <input {...p} value={pharmacy.hours} onChange={(e) => updatePharmacy("hours", e.target.value)} className={inputClass} />
            )}
          </Field>

          <fieldset className="space-y-3">
            <legend className="font-semibold">Position on the map</legend>
            <p className="text-[0.95rem] text-muted">
              Tap the map where the pharmacy is, or drag the marker. Patients use it to find the nearest pharmacy.
            </p>
            <button type="button" onClick={locate} className={buttonClass("secondary", "md")}>
              <LocateIcon /> I am in the pharmacy: use my position
            </button>
            <LocationPicker value={pharmacy.position} onChange={setPosition} label="Map to place the pharmacy" />
            <p className="text-[0.95rem] text-muted" aria-live="polite">
              Marker at {pharmacy.position.lat.toFixed(5)}, {pharmacy.position.lng.toFixed(5)}
            </p>
            {serverErrors["2.position"] && <p className="font-semibold text-out">{serverErrors["2.position"]}</p>}
          </fieldset>

          <div className="flex flex-col-reverse gap-3 sm:flex-row">
            <button type="button" onClick={() => setStep(1)} className={buttonClass("secondary", "lg")}>
              Back
            </button>
            <button type="submit" {...keepFocus} disabled={sending} className={buttonClass("primary", "lg", "flex-1")}>
              {sending ? "Creating your account…" : "Create my account"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
