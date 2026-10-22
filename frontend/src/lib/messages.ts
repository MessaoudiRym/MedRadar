// The API answers in French; the interface is in English.
// Known API texts and labels are translated here, in one place.

const API_MESSAGES: Record<string, string> = {
  "Ces médicaments contiennent la même substance active, au même dosage et sous la même forme. Demandez toujours l'avis de votre pharmacien ou de votre médecin avant de changer de médicament.":
    "These medicines contain the same active ingredient, at the same dose and in the same form. Always ask your pharmacist or doctor before changing medicine.",
  "Disponibilités simulées pour la démonstration.": "Simulated availability, for the demo.",
  "Email ou mot de passe incorrect": "Incorrect email or password.",
  "Un compte existe déjà avec cet email.": "An account already exists with this email.",
  "Une pharmacie est déjà inscrite avec ce numéro professionnel.":
    "A pharmacy is already registered with this professional number.",
  "Votre pharmacie est en cours de vérification.": "Your pharmacy is being verified.",
  "Votre pharmacie a été refusée. Consultez le motif dans votre espace.":
    "Your pharmacy was not approved. See the reason in your dashboard.",
  "Votre pharmacie est suspendue. Consultez le motif dans votre espace.":
    "Your pharmacy is suspended. See the reason in your dashboard.",
  "Trop de tentatives. Réessayez dans une minute.": "Too many attempts. Please try again in a minute.",
  "Authentification requise.": "Please log in.",
  "Session invalide ou expirée. Veuillez vous reconnecter.": "Your session has expired. Please log in again.",
  "Accès réservé aux administrateurs.": "This page is for administrators only.",
  "Accès réservé aux pharmaciens.": "This page is for pharmacists only.",
  "Aucune pharmacie liée à ce compte.": "No pharmacy is linked to this account.",
  "Médicament introuvable.": "This medicine was not found.",
  "Pharmacie introuvable.": "This pharmacy was not found.",
  "Ce médicament n'est pas dans votre liste.": "This medicine is not in your list.",
  "Mot de passe actuel incorrect.": "Your current password is incorrect.",
  "Le nouveau mot de passe doit être différent de l'ancien.":
    "The new password must be different from the current one.",
  "Une alerte existe déjà pour ce médicament.": "You already have an alert for this medicine.",
  "Limite de 5 alertes atteinte pour cet email.": "You already have 5 alerts with this email.",
  "Erreur interne du serveur.": "Something went wrong on our side. Please try again.",
  "Le mot de passe doit contenir entre 8 et 72 caractères.": "Use 8 to 72 characters.",
  "Le mot de passe doit contenir au moins une lettre et un chiffre.":
    "Use at least one letter and one number.",
  "Numéro de téléphone algérien invalide (ex. 0550 12 34 56 ou 041 23 45 67).":
    "Enter an Algerian number, e.g. 0550 12 34 56 or 041 23 45 67.",
  "Les coordonnées doivent être situées en Algérie.": "The position must be in Algeria.",
  "Field required": "This field is required.",
  "Bon introuvable.": "This delivery note was not found.",
  "Pas de photo pour ce bon.": "There is no photo for this note.",
  "Un bon ne peut être annulé que dans les 24 heures après sa confirmation.":
    "A note can only be cancelled within 24 hours of its confirmation.",
  "Ce bon est déjà annulé.": "This note is already cancelled.",
  "Analyse introuvable.": "This reading was not found. Scan the note again.",
  "Ce bon a déjà été confirmé.": "This note was already confirmed.",
  "Cette analyse a expiré (1 heure). Scannez le bon à nouveau.": "This reading expired (1 hour). Scan the note again.",
  "Choisissez un médicament, ou ignorez la ligne.": "Choose a medicine, or ignore the line.",
};

export function translateApiMessage(message: string): string {
  if (API_MESSAGES[message]) return API_MESSAGES[message];
  if (message.startsWith("Médicament introuvable")) return "This medicine was not found.";
  if (message.startsWith("Impossible de")) return "This action is not possible for this pharmacy's current status.";
  if (message.includes("email")) return "Enter a valid email address.";
  return "Some information is not valid.";
}

// Labels computed by scripts/clean_nomenclature.py
const FORM_GROUPS: Record<string, string> = {
  "comprimé": "Tablet",
  "comprimé orodispersible": "Orally disintegrating tablet",
  effervescent: "Effervescent tablet",
  dispersible: "Dispersible tablet",
  "à croquer": "Chewable tablet",
  "à sucer": "Lozenge",
  "gélule": "Capsule",
  "capsule molle": "Soft capsule",
  sirop: "Syrup",
  "solution buvable": "Oral solution",
  "suspension buvable": "Oral suspension",
  "poudre ou granulés oraux": "Oral powder or granules",
  injectable: "Injection",
  ophtalmique: "Eye drops or eye ointment",
  "voie nasale": "Nasal",
  inhalation: "Inhaler",
  auriculaire: "Ear drops",
  "suppositoire ou voie rectale": "Suppository or rectal",
  "voie vaginale": "Vaginal",
  "crème": "Cream",
  pommade: "Ointment",
  gel: "Gel",
  "usage cutané": "For the skin",
  "bouche et gorge": "Mouth and throat",
  "voie sublinguale": "Under the tongue",
  autre: "Other",
};

const FORM_MODIFIERS: Record<string, string> = {
  "libération modifiée": "modified release",
  "gastro-résistant": "gastro-resistant",
};

export function formLabel(group: string): string {
  const [base, modifier] = group.split(" — ");
  const label = FORM_GROUPS[base] ?? base;
  return modifier ? `${label}, ${FORM_MODIFIERS[modifier] ?? modifier}` : label;
}

export function isModifiedRelease(group: string): boolean {
  return group.includes("libération modifiée");
}

export function typeLabel(type: string): string | null {
  return (
    { "générique": "Generic", "référence": "Brand-name (reference)", biosimilaire: "Biosimilar" }[type] ??
    null
  );
}

export function originLabel(origin: string): string | null {
  return { "fabriqué en Algérie": "Made in Algeria", "importé": "Imported" }[origin] ?? null;
}

export const STOCK_LABELS = {
  en_stock: "In stock",
  rupture: "Out of stock",
  unknown: "No information",
} as const;

export const PHARMACY_STATUS_LABELS: Record<string, string> = {
  en_attente: "Being verified",
  validee: "Approved",
  refusee: "Not approved",
  suspendue: "Suspended",
};

// Brand names and substances are written in capitals in the nomenclature
export function titleCase(text: string): string {
  return text
    .toLowerCase()
    .replace(/(^|[\s(/+-])(\p{L})/gu, (_, sep: string, letter: string) => sep + letter.toUpperCase());
}
