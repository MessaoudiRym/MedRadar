import type { Metadata } from "next";
import { Suspense } from "react";

import { DeliveryDetail } from "@/components/delivery/DeliveryDetail";
import { Loading } from "@/components/ui";

export const metadata: Metadata = {
  title: "Delivery note",
  robots: { index: false },
};

async function Detail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <DeliveryDetail id={id} />;
}

export default function DeliveryNotePage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<Loading />}>
      <Detail params={params} />
    </Suspense>
  );
}
