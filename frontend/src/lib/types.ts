// Shapes of the MedRadar API responses (see backend/app/schemas.py).
// Field names are the API's (French); the interface shows English text.

export type StockStatus = "en_stock" | "rupture";
export type PharmacyStatus = "en_attente" | "validee" | "refusee" | "suspendue";
export type Role = "pharmacien" | "admin";

export interface MedicineSummary {
  id: string;
  nom_marque: string;
  molecule: string;
  dosage_norm: string;
  forme_groupe: string;
  nb_equivalents: number;
}

export type SearchMethod = "recherche" | "regles" | "llm" | "cache";
export type QueryKind = "nom_marque" | "molecule" | "marque_etrangere" | "maladie_ou_symptome" | "inconnu";

/** GET /medicines/search?interpret=true: results and how the query was understood */
export interface SmartSearch {
  results: MedicineSummary[];
  interpretation: {
    requete_originale: string;
    langue_detectee: "fr" | "ar" | "darija" | "arabizi" | "en";
    methode: SearchMethod;
    compris_comme: string | null;
    type: QueryKind | null;
    a_verifier: boolean;
  };
  message: string | null;
}

export interface Medicine extends MedicineSummary {
  num_enregistrement: string;
  dci: string;
  dci_cle: string;
  forme: string;
  voie: string;
  dosage: string;
  dosage_verifie: boolean;
  conditionnement: string;
  laboratoire: string;
  pays_laboratoire: string;
  type: string;
  origine: string;
  liste: string;
  disponible_officine: boolean;
  exclu: boolean;
  equivalence_key: string;
}

export interface Equivalents {
  medicine: Medicine;
  dosage_verifie: boolean;
  count: number;
  equivalents: Medicine[];
  notice: string;
}

export interface Features {
  photo_recognition: boolean;
  delivery_scan: boolean;
  email_alerts: boolean;
  multilingual_search: boolean;
}

export type RecognitionMatch = "exacte" | "probable" | "à vérifier";

export interface RecognizedMedicine extends MedicineSummary {
  correspondance: RecognitionMatch;
}

export interface Recognition {
  /** What the model read on the box, as printed */
  texte_lu: { nom_marque: string | null; dci: string | null; dosage: string | null; forme: string | null };
  resultats: RecognizedMedicine[];
  message: string | null;
}

export interface PublicPharmacy {
  id: number;
  nom: string;
  adresse: string;
  commune: string;
  quartier: string;
  latitude: number;
  longitude: number;
  telephone: string;
  horaires: string | null;
  est_demo: boolean;
}

export interface PharmacyAvailability extends PublicPharmacy {
  statut: StockStatus;
  distance_km: number;
  derniere_mise_a_jour: string;
  a_confirmer: boolean;
}

export interface MedicineAvailability {
  medicament: MedicineSummary;
  est_demande: boolean;
  en_stock: PharmacyAvailability[];
  rupture: PharmacyAvailability[];
}

export interface Availability {
  medicament: MedicineSummary;
  latitude: number;
  longitude: number;
  rayon_km: number;
  nb_pharmacies_en_stock: number;
  resultats: MedicineAvailability[];
  demo_data: boolean;
  demo_message: string | null;
  notice: string;
}

export interface Token {
  access_token: string;
  token_type: string;
  role: Role;
  expires_in: number;
}

export interface UserView {
  id: number;
  email: string;
  nom: string;
  prenom: string;
  telephone: string;
  role: Role;
  cree_le: string;
  derniere_connexion: string | null;
}

export interface OwnPharmacy {
  id: number;
  nom: string;
  adresse: string;
  commune: string;
  quartier: string;
  latitude: number;
  longitude: number;
  telephone: string;
  numero_professionnel: string;
  horaires: string | null;
  statut: PharmacyStatus;
  motif: string | null;
  cree_le: string;
  validee_le: string | null;
}

export interface AdminPharmacy extends OwnPharmacy {
  est_demo: boolean;
  validee_par: number | null;
  proprietaire: UserView | null;
}

export interface Me {
  utilisateur: UserView;
  pharmacie: OwnPharmacy | null;
}

export interface LastReception {
  bon_id: number;
  date: string;
  fournisseur: string | null;
  quantite: number | null;
  numero_lot: string | null;
  date_peremption: string | null;
}

export interface TrackedStock {
  medicament: MedicineSummary;
  statut: StockStatus | null;
  date_declaration: string | null;
  a_confirmer: boolean;
  derniere_reception?: LastReception | null;
}

// Delivery notes (pharmacists). No price anywhere.
export type Correspondence = "exacte" | "a_verifier" | "non_trouve" | "non_livre";
export type LineAction = "en_stock" | "rupture" | "ignoree";

export interface ScanLine {
  index: number;
  designation: string;
  designations_regroupees: string[];
  quantite: number | null;
  numero_lot: string | null;
  date_peremption: string | null;
  statut_ligne: string;
  correspondance: Correspondence;
  medicament: MedicineSummary | null;
  candidats: MedicineSummary[];
  coche: boolean;
}

export interface ScanResult {
  scan_id: string;
  expire_le: string;
  document: { type_document: string; fournisseur: string | null; numero_bon: string | null; date_bon: string | null };
  lignes: ScanLine[];
  resume: {
    lignes_lues: number;
    exactes: number;
    a_verifier: number;
    non_trouvees: number;
    non_livrees: number;
    regroupees: number;
  };
  photo_possible: boolean;
  message_photo: string | null;
}

export interface ConfirmLine {
  ligne: number;
  designation_lue: string;
  medicament_id: string | null;
  quantite: number | null;
  numero_lot: string | null;
  date_peremption: string | null;
  action: LineAction;
}

export interface ConfirmResult {
  nb_en_stock: number;
  nb_rupture: number;
  duree_secondes: number;
  bon_id: number | null;
  photo_gardee: boolean;
  message_photo: string | null;
}

export interface NoteSummary {
  id: number;
  fournisseur: string | null;
  numero_bon: string | null;
  date_bon: string | null;
  scanne_le: string;
  confirme_le: string;
  duree_secondes: number;
  nb_lignes_lues: number;
  nb_mis_en_stock: number;
  nb_rupture: number;
  nb_non_livres: number;
  nb_ignores: number;
  photo_gardee: boolean;
  annule_le: string | null;
  annulable: boolean;
}

export interface NoteLine {
  id: number;
  designation_lue: string;
  medicament_id: string | null;
  medicament: MedicineSummary | null;
  quantite: number | null;
  numero_lot: string | null;
  date_peremption: string | null;
  statut_correspondance: Correspondence;
  action: LineAction;
  corrigee_par_pharmacien: boolean;
}

export interface NoteDetail extends NoteSummary {
  lignes: NoteLine[];
  pages_photos: number[];
}

export interface NoteList {
  page: number;
  pages: number;
  total: number;
  bons: NoteSummary[];
}

export interface CancelResult {
  annule_le: string;
  retablis: { medicament_id: string; nom_marque: string | null; dosage_norm: string | null }[];
  laisses: { medicament_id: string; nom_marque: string | null; dosage_norm: string | null }[];
}

export interface Declaration {
  medicament_id: string;
  statut: StockStatus;
  date_declaration: string;
}
