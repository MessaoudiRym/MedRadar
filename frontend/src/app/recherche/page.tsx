import type { Metadata } from "next";
import { Suspense } from "react";

import { SearchResults } from "@/components/search/SearchResults";
import { Loading } from "@/components/ui";

export const metadata: Metadata = {
  title: "Search",
  description: "Find a medicine by its name, in French, Arabic, Darija or English.",
};

export default function SearchPage() {
  return (
    <Suspense fallback={<Loading label="Searching…" />}>
      <SearchResults />
    </Suspense>
  );
}
