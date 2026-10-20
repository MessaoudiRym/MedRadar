import type { Metadata } from "next";

import { Dashboard } from "@/components/pharmacist/Dashboard";

export const metadata: Metadata = {
  title: "Pharmacist dashboard",
  description: "See the status of your pharmacy and update your stock in one tap.",
  robots: { index: false },
};

export default function PharmacistPage() {
  return <Dashboard />;
}
