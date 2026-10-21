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
}

export type Correspondence = "exacte" | "probable" | "à vérifier";

export interface RecognizedMedicine extends MedicineSummary {
  correspondance: Correspondence;
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

export interface TrackedStock {
  medicament: MedicineSummary;
  statut: StockStatus | null;
  date_declaration: string | null;
  a_confirmer: boolean;
}

export interface Declaration {
  medicament_id: string;
  statut: StockStatus;
  date_declaration: string;
}
