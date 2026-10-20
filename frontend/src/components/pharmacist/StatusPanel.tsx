import { Notice } from "../ui";
import { formatDate } from "@/lib/format";
import type { OwnPharmacy } from "@/lib/types";

/** The status of the pharmacy, in words, with what it means for the pharmacist. */
export function StatusPanel({ pharmacy }: { pharmacy: OwnPharmacy }) {
  switch (pharmacy.statut) {
    case "validee":
      return (
        <Notice tone="success" title="Approved: patients can see your pharmacy">
          {pharmacy.validee_le && <p>Verified on {formatDate(pharmacy.validee_le)}.</p>}
        </Notice>
      );
    case "en_attente":
      return (
        <Notice tone="caution" title="Your pharmacy is being verified">
          <p>
            Our team checks the name, address, phone and professional number. Until then, patients do not see
            your pharmacy and you cannot update stock. We may call you to confirm.
          </p>
        </Notice>
      );
    case "refusee":
      return (
        <Notice tone="danger" title="Your pharmacy was not approved">
          {pharmacy.motif && (
            <p>
              <strong>Reason:</strong> {pharmacy.motif}
            </p>
          )}
          <p>Correct the information in “Edit my pharmacy” to ask for a new verification.</p>
        </Notice>
      );
    case "suspendue":
      return (
        <Notice tone="danger" title="Your pharmacy is suspended">
          {pharmacy.motif && (
            <p>
              <strong>Reason:</strong> {pharmacy.motif}
            </p>
          )}
          <p>Patients no longer see your pharmacy. Contact the MedRadar team to discuss it.</p>
        </Notice>
      );
  }
}
