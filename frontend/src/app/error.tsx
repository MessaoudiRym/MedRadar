"use client";

import Link from "next/link";

import { buttonClass, PageTitle } from "@/components/ui";

// Shown instead of a blank page if something breaks while displaying a page
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="max-w-2xl space-y-6">
      <PageTitle lead="This page could not be displayed. Please try again in a moment.">
        Something went wrong
      </PageTitle>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={reset} className={buttonClass("primary", "lg")}>
          Try again
        </button>
        <Link href="/" className={buttonClass("secondary", "lg")}>
          Back to the search
        </Link>
      </div>
    </div>
  );
}
