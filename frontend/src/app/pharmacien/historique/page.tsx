import type { Metadata } from "next";

import { DeliveryHistory } from "@/components/delivery/DeliveryHistory";

export const metadata: Metadata = {
  title: "Delivery notes",
  description: "The delivery notes kept by your pharmacy: what you received, when and from which wholesaler.",
  robots: { index: false },
};

export default function HistoryPage() {
  return <DeliveryHistory />;
}
