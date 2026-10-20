import type { Metadata } from "next";

import { EditPharmacy } from "@/components/pharmacist/EditPharmacy";

export const metadata: Metadata = {
  title: "Edit my pharmacy",
  description: "Change the phone, opening hours or address of your pharmacy.",
  robots: { index: false },
};

export default function EditPharmacyPage() {
  return <EditPharmacy />;
}
