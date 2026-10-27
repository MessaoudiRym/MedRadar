"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { buttonClass, Card, Notice } from "../ui";
import { api, errorMessage } from "@/lib/api";
import { login } from "@/lib/auth";
import { EXAMPLES } from "@/lib/examples";
import type { Features } from "@/lib/types";
import { useAsync } from "@/lib/useAsync";

// Public on purpose: these are the fictional demo accounts (never a real pharmacy)
const DEMO_EMAIL = process.env.NEXT_PUBLIC_DEMO_PHARMACIST_EMAIL ?? "";
const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PHARMACIST_PASSWORD ?? "";
const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL ?? "";
const VIDEO_URL = process.env.NEXT_PUBLIC_VIDEO_URL ?? "";

const GLUCOPHAGE_850 = EXAMPLES[0].id;

type Lang = "en" | "fr";

const TEXT = {
  en: {
    tab: "English",
    intro: [
      "When a medicine is out of stock in Algeria, MedRadar shows its registered equivalents (same active ingredient, same dose, same form) from the official national nomenclature.",
      "It also shows the pharmacies near you that have the medicine or an equivalent in stock, as declared by pharmacists.",
    ],
    tryTitle: "Try it in 3 minutes",
    steps: [
      { title: "Search a medicine that is out of stock", body: "Type it with a typo: “glucofage”.", link: "Search “glucofage”" },
      { title: "See its equivalents and the map", body: "13 equivalents, and the pharmacies that have it nearby.", link: "Open Glucophage 850" },
      { title: "Be a pharmacist and change a stock", body: "Log in with the demo account, then mark a medicine in or out of stock: patients see it at once.", link: "Open the pharmacist login" },
    ],
    examplesTitle: "Out of stock in many demo pharmacies",
    accountTitle: "Demo pharmacist account",
    email: "Email",
    password: "Password",
    oneClick: "Log in in one click",
    loggingIn: "Logging in…",
    noAccount: "The demo account is not configured on this site.",
    realTitle: "What is real, what is simulated",
    real: "Real: the medicines and their equivalents, from the official national nomenclature of the Ministry of Pharmaceutical Industry (August 2026).",
    simulated: "Simulated: the pharmacies, their addresses, phone numbers and stock levels. They are fictional, for the demo, and reset every night.",
    aiTitle: "AI features on this site",
    aiLoading: "Checking…",
    aiNone: "No AI feature is turned on right now: everything else works.",
    ai: {
      photo_recognition: "Photo of a medicine box: the app reads the name (home page, “Take a photo of the box”).",
      multilingual_search: "Search in Arabic, Darija, arabizi or English, then press Enter.",
      delivery_scan: "Pharmacists: scan a delivery note to update the stock (“Scan a note”, try the demo note).",
      email_alerts: "Email alert when a medicine is back in stock nearby (bottom of a medicine page).",
    },
    linksTitle: "Links",
    github: "Source code on GitHub",
    video: "Demo video",
    wake: "The first page can take up to a minute to load if nobody visited the site for a while: the free server is starting.",
  },
  fr: {
    tab: "Français",
    intro: [
      "Quand un médicament est en rupture en Algérie, MedRadar montre ses équivalents enregistrés (même substance active, même dosage, même forme), tirés de la nomenclature nationale officielle.",
      "Il montre aussi les pharmacies proches qui ont le médicament ou un équivalent en stock, déclaré par les pharmaciens.",
    ],
    tryTitle: "À tester en 3 minutes",
    steps: [
      { title: "Chercher un médicament en rupture", body: "Tapez-le avec une faute : « glucofage ».", link: "Chercher « glucofage »" },
      { title: "Voir ses équivalents et la carte", body: "13 équivalents, et les pharmacies proches qui l’ont.", link: "Ouvrir Glucophage 850" },
      { title: "Être pharmacien et changer un stock", body: "Connectez-vous avec le compte de démo, puis marquez un médicament en stock ou en rupture : les patients le voient tout de suite.", link: "Ouvrir la connexion pharmacien" },
    ],
    examplesTitle: "En rupture dans beaucoup de pharmacies de démo",
    accountTitle: "Compte pharmacien de démo",
    email: "Email",
    password: "Mot de passe",
    oneClick: "Se connecter en un clic",
    loggingIn: "Connexion…",
    noAccount: "Le compte de démo n’est pas configuré sur ce site.",
    realTitle: "Ce qui est réel, ce qui est simulé",
    real: "Réel : les médicaments et leurs équivalents, issus de la nomenclature nationale officielle du ministère de l’Industrie pharmaceutique (août 2026).",
    simulated: "Simulé : les pharmacies, leurs adresses, téléphones et stocks. Ils sont fictifs, pour la démo, et remis à zéro chaque nuit.",
    aiTitle: "Fonctionnalités d’IA sur ce site",
    aiLoading: "Vérification…",
    aiNone: "Aucune fonctionnalité d’IA n’est active en ce moment : tout le reste fonctionne.",
    ai: {
      photo_recognition: "Photo d’une boîte de médicament : l’application lit le nom (accueil, « Take a photo of the box »).",
      multilingual_search: "Recherche en arabe, darija, arabizi ou anglais, puis touche Entrée.",
      delivery_scan: "Pharmaciens : scanner un bon de livraison pour mettre le stock à jour (« Scan a note », essayez le bon de démo).",
      email_alerts: "Alerte par email quand un médicament revient en stock à proximité (bas de la fiche d’un médicament).",
    },
    linksTitle: "Liens",
    github: "Code source sur GitHub",
    video: "Vidéo de démonstration",
    wake: "La première page peut mettre jusqu’à une minute à s’afficher si personne n’a visité le site depuis un moment : le serveur gratuit démarre.",
  },
} as const;

const STEP_LINKS = [`/recherche?q=glucofage`, `/medicament/${GLUCOPHAGE_850}`, "/pharmacien/connexion"];
const AI_ORDER = ["photo_recognition", "multilingual_search", "delivery_scan", "email_alerts"] as const;

export function DemoGuide() {
  const [lang, setLang] = useState<Lang>("en");
  const id = useId();
  const t = TEXT[lang];

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const next = lang === "en" ? "fr" : "en";
      setLang(next);
      document.getElementById(`${id}-tab-${next}`)?.focus();
    }
  }

  return (
    <div className="space-y-6">
      <div role="tablist" aria-label="Language / Langue" className="flex gap-2" onKeyDown={onKeyDown}>
        {(["en", "fr"] as const).map((l) => (
          <button
            key={l}
            id={`${id}-tab-${l}`}
            type="button"
            role="tab"
            lang={l}
            aria-selected={lang === l}
            aria-controls={`${id}-panel`}
            tabIndex={lang === l ? 0 : -1}
            onClick={() => setLang(l)}
            className={buttonClass(lang === l ? "primary" : "secondary", "sm")}
          >
            {TEXT[l].tab}
          </button>
        ))}
      </div>

      <div id={`${id}-panel`} role="tabpanel" aria-labelledby={`${id}-tab-${lang}`} lang={lang} className="space-y-8">
        <section className="space-y-2 text-lg">
          {t.intro.map((p) => (
            <p key={p}>{p}</p>
          ))}
          <p className="text-base text-muted">{t.wake}</p>
        </section>

        <section aria-labelledby={`${id}-try`} className="space-y-3">
          <h2 id={`${id}-try`} className="text-2xl font-bold">
            {t.tryTitle}
          </h2>
          <ol className="space-y-3">
            {t.steps.map((step, i) => (
              <li key={step.title}>
                <Card className="flex gap-4">
                  <span
                    aria-hidden
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand text-lg font-bold text-white"
                  >
                    {i + 1}
                  </span>
                  <div className="space-y-2">
                    <h3 className="text-lg font-bold">{step.title}</h3>
                    <p className="text-muted">{step.body}</p>
                    <Link href={STEP_LINKS[i]} className="font-semibold text-brand underline">
                      {step.link}
                    </Link>
                  </div>
                </Card>
              </li>
            ))}
          </ol>
        </section>

        <DemoAccount lang={lang} />

        <section aria-labelledby={`${id}-examples`} className="space-y-3">
          <h2 id={`${id}-examples`} className="text-2xl font-bold">
            {t.examplesTitle}
          </h2>
          <ul className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            {EXAMPLES.map((example) => (
              <li key={example.id}>
                <Link
                  href={`/medicament/${example.id}`}
                  className="flex min-h-11 items-center rounded-lg border-2 border-line bg-surface px-4 py-2 font-semibold text-ink hover:border-brand"
                >
                  {example.name}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section aria-labelledby={`${id}-real`} className="space-y-3">
          <h2 id={`${id}-real`} className="text-2xl font-bold">
            {t.realTitle}
          </h2>
          <ul className="list-disc space-y-2 pl-6">
            <li>{t.real}</li>
            <li>{t.simulated}</li>
          </ul>
        </section>

        <AiFeatures lang={lang} />

        {(GITHUB_URL || VIDEO_URL) && (
          <section aria-labelledby={`${id}-links`} className="space-y-3">
            <h2 id={`${id}-links`} className="text-2xl font-bold">
              {t.linksTitle}
            </h2>
            <ul className="space-y-2">
              {GITHUB_URL && <ExternalLink href={GITHUB_URL}>{t.github}</ExternalLink>}
              {VIDEO_URL && <ExternalLink href={VIDEO_URL}>{t.video}</ExternalLink>}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function ExternalLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <li>
      <a href={href} target="_blank" rel="noopener noreferrer" className="font-semibold text-brand underline">
        {children}
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    </li>
  );
}

function DemoAccount({ lang }: { lang: Lang }) {
  const t = TEXT[lang];
  const router = useRouter();
  const [state, setState] = useState<{ status: "idle" | "sending" } | { status: "error"; message: string }>({
    status: "idle",
  });

  async function oneClick() {
    setState({ status: "sending" });
    try {
      await login(DEMO_EMAIL, DEMO_PASSWORD);
      router.push("/pharmacien");
    } catch (e) {
      setState({ status: "error", message: errorMessage(e) });
    }
  }

  return (
    <section aria-labelledby="demo-account" className="space-y-3">
      <h2 id="demo-account" className="text-2xl font-bold">
        {t.accountTitle}
      </h2>
      {DEMO_EMAIL && DEMO_PASSWORD ? (
        <Card className="space-y-4">
          <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[auto_1fr]">
            <dt className="font-semibold text-muted">{t.email}</dt>
            <dd className="font-mono break-all">{DEMO_EMAIL}</dd>
            <dt className="font-semibold text-muted">{t.password}</dt>
            <dd className="font-mono break-all">{DEMO_PASSWORD}</dd>
          </dl>
          <button
            type="button"
            onClick={oneClick}
            disabled={state.status === "sending"}
            className={buttonClass("primary", "lg")}
          >
            {state.status === "sending" ? t.loggingIn : t.oneClick}
          </button>
          {state.status === "error" && (
            <Notice tone="danger" role="alert">
              <p>{state.message}</p>
            </Notice>
          )}
        </Card>
      ) : (
        <p className="text-muted">{t.noAccount}</p>
      )}
    </section>
  );
}

function AiFeatures({ lang }: { lang: Lang }) {
  const t = TEXT[lang];
  const features = useAsync((signal) => api<Features>("/features", { signal }), []);
  const on = features.status === "success" ? AI_ORDER.filter((name) => features.data[name]) : [];

  return (
    <section aria-labelledby="demo-ai" className="space-y-3">
      <h2 id="demo-ai" className="text-2xl font-bold">
        {t.aiTitle}
      </h2>
      {features.status === "loading" && <p className="text-muted">{t.aiLoading}</p>}
      {features.status === "error" && <p className="text-muted">{errorMessage(features.error)}</p>}
      {features.status === "success" &&
        (on.length ? (
          <ul className="list-disc space-y-2 pl-6">
            {on.map((name) => (
              <li key={name}>{t.ai[name]}</li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">{t.aiNone}</p>
        ))}
    </section>
  );
}
