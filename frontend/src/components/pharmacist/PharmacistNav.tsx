"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/pharmacien", label: "My stock" },
  { href: "/pharmacien/scanner", label: "Scan a note" },
  { href: "/pharmacien/historique", label: "Delivery notes" },
];

/** Menu of the pharmacist area. */
export function PharmacistNav() {
  const path = usePathname();
  return (
    <nav aria-label="Pharmacist area" className="-mx-1 flex flex-wrap gap-1">
      {LINKS.map((link) => {
        const current = link.href === "/pharmacien" ? path === link.href : path.startsWith(link.href);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={current ? "page" : undefined}
            className={`rounded-lg px-3 py-2 font-semibold no-underline ${
              current ? "bg-brand text-white" : "text-brand hover:bg-brand-soft"
            }`}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
