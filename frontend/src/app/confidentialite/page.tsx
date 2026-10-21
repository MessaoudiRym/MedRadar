import type { Metadata } from "next";

import { PageTitle } from "@/components/ui";

export const metadata: Metadata = {
  title: "Privacy",
  description: "What MedRadar stores, why, how patient searches stay anonymous, and what happens to box photos.",
};

// Same content as docs/privacy.md
export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-8">
      <PageTitle lead="MedRadar stores only the data it needs to work.">Privacy</PageTitle>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Patients</h2>
        <p>Patients do not need an account.</p>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            <strong>Searches are anonymous.</strong> We keep the medicine searched and, at most, the district
            (for example “USTO”). No name, no account, no IP address, no exact position.
          </li>
          <li>
            <strong>Your position</strong> is used to sort pharmacies by distance, then forgotten. It is only
            asked when you press “Use my position”.
          </li>
          <li>
            <strong>Alerts</strong> keep your email, the medicine and the area, rounded to about 1 km, so we can
            tell you when the medicine is back nearby. At most 5 active alerts per email.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Photos of medicine boxes</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            <strong>Your photo is sent to Google</strong> (Gemini API, free tier) <strong>only to read the box</strong>:
            brand name, active ingredient, dose and form. Before sending, it is made smaller and its hidden
            information, such as the GPS position, is removed.
          </li>
          <li>
            <strong>MedRadar does not keep your photo.</strong> It is never saved: not on disk, not in the
            database, not in the logs. We only count, anonymously, whether a photo led to a medicine.
          </li>
          <li>
            <strong>Google may use it</strong> to improve its services, as data sent to the free tier of the
            Gemini API can be.
          </li>
          <li>
            That is why only medicine boxes are accepted. <strong>Do not photograph your prescription</strong>: it
            contains your name and your health information. If the photo shows a prescription, MedRadar stops and
            reads nothing from it.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Searches in Arabic, Darija or English</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            When you <strong>validate</strong> a search (Enter or the Search button) written in Arabic, Darija or
            English, or a French search that MedRadar is unsure about, the text is sent to{" "}
            <strong>Google (Gemini API, free tier) only to understand the name of the medicine</strong>. Suggestions
            shown while you type are never sent.
          </li>
          <li>
            <strong>No personal data</strong> is sent: only the words of the search. No name, no account, no IP
            address, no position.
          </li>
          <li>
            What was understood is kept 30 days, so the same search is never sent twice, without anything that
            links it to you.
          </li>
          <li>
            <strong>Google may use it</strong> to improve its services, as data sent to the free tier of the Gemini
            API can be. Do not type personal information in the search.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Pharmacists</h2>
        <ul className="list-disc space-y-2 pl-6">
          <li>
            <strong>Email, password, name and phone</strong>: to log in, and so that the MedRadar team can reach
            the pharmacist during verification.
          </li>
          <li>
            <strong>Name, address, position, phone and opening hours of the pharmacy</strong>: shown to patients.
          </li>
          <li>
            <strong>Professional number</strong>: to check that the pharmacy is real. Never shown to patients.
          </li>
          <li>
            <strong>Stock declarations</strong> (who, when, what): to show availability. The history helps detect
            errors or abuse.
          </li>
        </ul>
        <p>
          Passwords are never stored: only a secure fingerprint (bcrypt hash) is kept, and passwords are never
          sent back by MedRadar.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">What patients can see</h2>
        <p>
          Only verified pharmacies, with their business details (name, address, phone, opening hours). Never an
          email, a professional number or the account behind a pharmacy.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-2xl font-bold">Demo data</h2>
        <p>The demo pharmacies, accounts and stock levels are fictional and contain no real personal data.</p>
      </section>
    </article>
  );
}
