import type { Metadata } from "next";

import { DemoGuide } from "@/components/demo/DemoGuide";
import { PageTitle } from "@/components/ui";

export const metadata: Metadata = {
  title: "Testing guide · Guide pour tester",
  description:
    "Test MedRadar in 3 minutes: search an out-of-stock medicine, see its equivalents and the map, then update a stock as a demo pharmacist.",
};

export default function DemoPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-8">
      <PageTitle lead="For the jury: everything to try MedRadar in a few minutes.">
        Testing guide · <span lang="fr">Guide pour tester</span>
      </PageTitle>
      <DemoGuide />
    </article>
  );
}
