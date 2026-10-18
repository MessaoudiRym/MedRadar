"""Shapes of the API responses (Pydantic models)."""

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    medicines: int


class SearchResult(BaseModel):
    id: str
    nom_marque: str
    molecule: str
    dosage_norm: str
    forme_groupe: str
    nb_equivalents: int


class Medicine(BaseModel):
    id: str
    num_enregistrement: str
    nom_marque: str
    dci: str
    dci_cle: str
    molecule: str
    forme: str
    forme_groupe: str
    voie: str
    dosage: str
    dosage_norm: str
    dosage_verifie: bool
    conditionnement: str
    laboratoire: str
    pays_laboratoire: str
    type: str
    origine: str
    liste: str
    disponible_officine: bool
    exclu: bool
    equivalence_key: str
    nb_equivalents: int


class Equivalents(BaseModel):
    medicine: Medicine
    dosage_verifie: bool
    count: int
    equivalents: list[Medicine]
    notice: str
