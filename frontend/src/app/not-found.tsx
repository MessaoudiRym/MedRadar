import Link from "next/link";

import { buttonClass, PageTitle } from "@/components/ui";

export default function NotFound() {
  return (
    <div className="max-w-2xl space-y-6">
      <PageTitle lead="The page or the medicine you are looking for does not exist, or is no longer listed.">
        Page not found
      </PageTitle>
      <Link href="/" className={buttonClass("primary", "lg")}>
        Search for a medicine
      </Link>
    </div>
  );
}
