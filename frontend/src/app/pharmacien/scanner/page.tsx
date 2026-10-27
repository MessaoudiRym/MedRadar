import type { Metadata } from "next";

import { DeliveryScan } from "@/components/delivery/DeliveryScan";

export const metadata: Metadata = {
  title: "Scan a delivery note",
  description: "Put a whole delivery note in stock in less than a minute.",
  robots: { index: false },
};

export default function ScannerPage() {
  return <DeliveryScan />;
}
