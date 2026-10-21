"""Shapes of the API requests and responses (Pydantic models).

The API speaks French (field names and messages), the database speaks English:
validation_alias maps one to the other.
Request models forbid unknown fields, so that a client can never send
"role" or "statut" to change what it is not allowed to change.
"""

import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import (AfterValidator, BaseModel, ConfigDict, EmailStr, Field,
                      StringConstraints, field_validator, model_validator)

from .geo import in_algeria

# --------------------------------------------------------------------------
# Reusable types and rules
# --------------------------------------------------------------------------

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
MedicineId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12)]
StockStatus = Literal["en_stock", "rupture"]

PASSWORD_MIN = 8
PASSWORD_MAX = 72  # bcrypt only uses the first 72 bytes


def _as_utc(value):
    """Dates are stored in UTC without time zone; the API returns them with "+00:00"."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]


def check_password(password):
    if not PASSWORD_MIN <= len(password.encode("utf-8")) <= PASSWORD_MAX:
        raise ValueError(f"Le mot de passe doit contenir entre {PASSWORD_MIN} "
                         f"et {PASSWORD_MAX} caractères.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Le mot de passe doit contenir au moins une lettre et un chiffre.")
    return password


def normalize_phone(phone):
    """Algerian phone: mobile 05/06/07 + 8 digits, or landline 0XX + 6 digits.

    "+213 550 12 34 56" and "0550-12-34-56" are both stored as "0550123456".
    """
    digits = re.sub(r"[\s.\-()]", "", phone)
    digits = re.sub(r"^(\+|00)213", "0", digits)
    if re.fullmatch(r"0[567]\d{8}", digits) or re.fullmatch(r"0[2-4]\d{7}", digits):
        return digits
    raise ValueError("Numéro de téléphone algérien invalide (ex. 0550 12 34 56 ou 041 23 45 67).")


def check_coordinates(lat, lng):
    if not in_algeria(lat, lng):
        raise ValueError("Les coordonnées doivent être situées en Algérie.")


Phone = Annotated[str, AfterValidator(normalize_phone)]
Password = Annotated[str, AfterValidator(check_password)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Output(BaseModel):
    # Built from a database object (English names) or from a dict (French names)
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --------------------------------------------------------------------------
# Medicines (unchanged)
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Photo recognition
# --------------------------------------------------------------------------

class Features(BaseModel):
    photo_recognition: bool


class TextRead(BaseModel):
    """What the model read on the box, shown to the patient as is."""
    nom_marque: str | None
    dci: str | None
    dosage: str | None
    forme: str | None


class RecognizedMedicine(SearchResult):
    correspondance: Literal["exacte", "probable", "à vérifier"]


class RecognitionResult(BaseModel):
    texte_lu: TextRead
    resultats: list[RecognizedMedicine]
    message: str | None


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

class PharmacyRegistration(Input):
    nom: Text
    adresse: LongText
    commune: Text
    quartier: Text
    latitude: float
    longitude: float
    telephone: Phone
    numero_professionnel: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=3, max_length=50)]
    horaires: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None

    @model_validator(mode="after")
    def _in_algeria(self):
        check_coordinates(self.latitude, self.longitude)
        return self


class PharmacistRegistration(Input):
    email: EmailStr
    mot_de_passe: Password
    nom: Text
    prenom: Text
    telephone: Phone
    pharmacie: PharmacyRegistration

    @field_validator("email")
    @classmethod
    def _lowercase(cls, email):
        return email.lower()


class LoginRequest(Input):
    # Plain text on purpose: a badly formed email gets the same answer as a wrong password
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=254)]
    mot_de_passe: Annotated[str, StringConstraints(max_length=200)]


class ChangePasswordRequest(Input):
    ancien_mot_de_passe: Annotated[str, StringConstraints(max_length=200)]
    nouveau_mot_de_passe: Password


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


class UserView(Output):
    id: int
    email: str
    nom: str = Field(validation_alias="last_name")
    prenom: str = Field(validation_alias="first_name")
    telephone: str = Field(validation_alias="phone")
    role: str
    cree_le: UTCDateTime = Field(validation_alias="created_at")
    derniere_connexion: UTCDateTime | None = Field(validation_alias="last_login_at")


class OwnPharmacy(Output):
    """What a pharmacist sees about their own pharmacy."""
    id: int
    nom: str = Field(validation_alias="name")
    adresse: str = Field(validation_alias="address")
    commune: str
    quartier: str = Field(validation_alias="district")
    latitude: float
    longitude: float
    telephone: str = Field(validation_alias="phone")
    numero_professionnel: str = Field(validation_alias="professional_number")
    horaires: str | None = Field(validation_alias="opening_hours")
    statut: str = Field(validation_alias="status")
    motif: str | None = Field(validation_alias="status_reason")
    cree_le: UTCDateTime = Field(validation_alias="created_at")
    validee_le: UTCDateTime | None = Field(validation_alias="validated_at")


class RegisterResponse(BaseModel):
    message: str
    pharmacie: OwnPharmacy


class Me(BaseModel):
    utilisateur: UserView
    pharmacie: OwnPharmacy | None


class Message(BaseModel):
    message: str


# --------------------------------------------------------------------------
# Pharmacist space
# --------------------------------------------------------------------------

class PharmacyUpdate(Input):
    telephone: Phone | None = None
    horaires: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None = None
    adresse: LongText | None = None
    latitude: float | None = None
    longitude: float | None = None

    @model_validator(mode="after")
    def _position(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("La latitude et la longitude doivent être envoyées ensemble.")
        if self.latitude is not None:
            check_coordinates(self.latitude, self.longitude)
        return self


class StockDeclarationIn(Input):
    medicament_id: MedicineId
    statut: StockStatus


class StockBulkIn(Input):
    declarations: list[StockDeclarationIn] = Field(min_length=1, max_length=50)


class DeclarationOut(BaseModel):
    medicament_id: str
    statut: str
    date_declaration: UTCDateTime


class TrackedStock(BaseModel):
    medicament: SearchResult
    statut: str | None
    date_declaration: UTCDateTime | None
    a_confirmer: bool


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------

class ReasonIn(Input):
    motif: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class AdminPharmacy(OwnPharmacy):
    est_demo: bool = Field(validation_alias="is_demo")
    validee_par: int | None = Field(validation_alias="validated_by")
    proprietaire: UserView | None = Field(validation_alias="owner")


# --------------------------------------------------------------------------
# Public (patients)
# --------------------------------------------------------------------------

class PublicPharmacy(Output):
    """No personal data: no email, no professional number, no owner."""
    id: int
    nom: str = Field(validation_alias="name")
    adresse: str = Field(validation_alias="address")
    commune: str
    quartier: str = Field(validation_alias="district")
    latitude: float
    longitude: float
    telephone: str = Field(validation_alias="phone")
    horaires: str | None = Field(validation_alias="opening_hours")
    est_demo: bool = Field(validation_alias="is_demo")


class PharmacyAvailability(PublicPharmacy):
    statut: str
    distance_km: float
    derniere_mise_a_jour: UTCDateTime
    a_confirmer: bool


class MedicineAvailability(BaseModel):
    medicament: SearchResult
    est_demande: bool  # True for the medicine searched, False for an equivalent
    en_stock: list[PharmacyAvailability]
    rupture: list[PharmacyAvailability]


class Availability(BaseModel):
    medicament: SearchResult
    latitude: float
    longitude: float
    rayon_km: float
    nb_pharmacies_en_stock: int
    resultats: list[MedicineAvailability]
    demo_data: bool
    demo_message: str | None
    notice: str


class AlertIn(Input):
    email: EmailStr
    medicament_id: MedicineId
    lat: float | None = None
    lng: float | None = None
    rayon_km: float | None = Field(default=None, gt=0, le=50)

    @field_validator("email")
    @classmethod
    def _lowercase(cls, email):
        return email.lower()

    @model_validator(mode="after")
    def _position(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat et lng doivent être envoyés ensemble.")
        if self.lat is not None:
            check_coordinates(self.lat, self.lng)
        return self


class AlertOut(BaseModel):
    id: int
    medicament_id: str
    message: str
