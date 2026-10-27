"""Shapes of the delivery note routes. No price or amount anywhere."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

from ..schemas import Input, MedicineId, SearchResult, UTCDateTime

Correspondence = Literal["exacte", "a_verifier", "non_trouve", "non_livre"]
LineAction = Literal["en_stock", "rupture", "ignoree"]
Short = lambda n: Annotated[str, StringConstraints(strip_whitespace=True, max_length=n)]  # noqa: E731
Expiry = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


# --------------------------------------------------------------------------
# Scan (analysis only)
# --------------------------------------------------------------------------

class ScanDocument(BaseModel):
    type_document: str
    fournisseur: str | None
    numero_bon: str | None
    date_bon: date | None


class ScanLine(BaseModel):
    index: int
    designation: str
    designations_regroupees: list[str]
    quantite: float | None
    numero_lot: str | None
    date_peremption: str | None
    statut_ligne: str
    correspondance: Correspondence
    medicament: SearchResult | None
    candidats: list[SearchResult]
    coche: bool


class ScanSummary(BaseModel):
    lignes_lues: int
    exactes: int
    a_verifier: int
    non_trouvees: int
    non_livrees: int
    regroupees: int


class ScanResult(BaseModel):
    scan_id: str
    expire_le: UTCDateTime
    document: ScanDocument
    lignes: list[ScanLine]
    resume: ScanSummary
    photo_possible: bool
    message_photo: str | None


# --------------------------------------------------------------------------
# Confirmation
# --------------------------------------------------------------------------

class ConfirmLine(Input):
    ligne: int | None = Field(None, ge=0, le=500, description="index of the line in the scan")
    designation_lue: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1,
                                                      max_length=200)]
    medicament_id: MedicineId | None = None
    quantite: float | None = Field(None, ge=0, le=100_000)
    numero_lot: Short(40) | None = None
    date_peremption: Expiry | None = None
    action: LineAction

    @model_validator(mode="after")
    def _medicine_needed(self):
        if self.action != "ignoree" and not self.medicament_id:
            raise ValueError("Choisissez un médicament, ou ignorez la ligne.")
        return self


class ConfirmIn(Input):
    fournisseur: Short(120) | None = None
    numero_bon: Short(60) | None = None
    date_bon: date | None = None
    lignes: list[ConfirmLine] = Field(min_length=1, max_length=200)
    garder_historique: bool = True
    garder_photo: bool = False


class ConfirmOut(BaseModel):
    nb_en_stock: int
    nb_rupture: int
    duree_secondes: int
    bon_id: int | None
    photo_gardee: bool
    message_photo: str | None


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------

class NoteSummary(BaseModel):
    id: int
    fournisseur: str | None
    numero_bon: str | None
    date_bon: date | None
    scanne_le: UTCDateTime
    confirme_le: UTCDateTime
    duree_secondes: int
    nb_lignes_lues: int
    nb_mis_en_stock: int
    nb_rupture: int
    nb_non_livres: int
    nb_ignores: int
    photo_gardee: bool
    annule_le: UTCDateTime | None
    annulable: bool


class NoteLineOut(BaseModel):
    id: int
    designation_lue: str
    medicament_id: str | None
    medicament: SearchResult | None
    quantite: float | None
    numero_lot: str | None
    date_peremption: str | None
    statut_correspondance: Correspondence
    action: LineAction
    corrigee_par_pharmacien: bool


class NoteDetail(NoteSummary):
    lignes: list[NoteLineOut]
    pages_photos: list[int]


class NoteList(BaseModel):
    page: int
    pages: int
    total: int
    bons: list[NoteSummary]


class NoteUpdate(Input):
    fournisseur: Short(120) | None = None
    numero_bon: Short(60) | None = None
    date_bon: date | None = None


class MedicineRef(BaseModel):
    medicament_id: str
    nom_marque: str | None
    dosage_norm: str | None


class CancelOut(BaseModel):
    annule_le: UTCDateTime
    retablis: list[MedicineRef]
    laisses: list[MedicineRef]


class Reception(BaseModel):
    bon_id: int
    date: date
    fournisseur: str | None
    numero_bon: str | None
    quantite: float | None
    numero_lot: str | None
    date_peremption: str | None
    annule: bool


class DeliveryStats(BaseModel):
    """For the admin: global counts only, never the content of a note."""
    bons_gardes: int
    lignes: int
    pages_photos: int
    pharmacies_utilisatrices: int
