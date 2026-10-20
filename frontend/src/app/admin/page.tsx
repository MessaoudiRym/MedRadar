import type { Metadata } from "next";

import { AdminPharmacies } from "@/components/admin/AdminPharmacies";

export const metadata: Metadata = {
  title: "Admin — pharmacies to verify",
  description: "Approve, reject or suspend pharmacies registered on MedRadar.",
  robots: { index: false },
};

export default function AdminPage() {
  return <AdminPharmacies />;
}
