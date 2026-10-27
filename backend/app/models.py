"""Database tables.

Medicines are not stored here: they stay in memory, loaded from the CSV.
Tables refer to them by their stable id (medicine_id, 12 characters).
"""

from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, LargeBinary,
                        String, Text)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, utcnow

MEDICINE_ID = String(12)

ROLE_PHARMACIST = "pharmacien"
ROLE_ADMIN = "admin"

PHARMACY_PENDING = "en_attente"
PHARMACY_VALIDATED = "validee"
PHARMACY_REJECTED = "refusee"
PHARMACY_SUSPENDED = "suspendue"

STOCK_IN = "en_stock"
STOCK_OUT = "rupture"

# Where a stock declaration comes from
SOURCE_MANUAL = "manuel"
SOURCE_DELIVERY_SCAN = "scan_bl"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    first_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    # Tokens issued before this date are refused (set when the password changes)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime)

    pharmacy: Mapped["Pharmacy | None"] = relationship(
        back_populates="owner", foreign_keys="Pharmacy.owner_id", uselist=False)


class Pharmacy(Base):
    __tablename__ = "pharmacies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(300))
    commune: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    phone: Mapped[str] = mapped_column(String(20))
    professional_number: Mapped[str] = mapped_column(String(50), unique=True)
    opening_hours: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=PHARMACY_PENDING, index=True)
    # Reason given by the admin when the pharmacy is rejected or suspended
    status_reason: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    validated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    owner: Mapped[User | None] = relationship(back_populates="pharmacy", foreign_keys=[owner_id])


class StockDeclaration(Base):
    """Full history: the current status is the most recent declaration."""
    __tablename__ = "stock_declarations"
    __table_args__ = (
        Index("ix_stock_pharmacy_medicine_date", "pharmacy_id", "medicine_id", "declared_at"),
        Index("ix_stock_medicine", "medicine_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("pharmacies.id", ondelete="CASCADE"))
    medicine_id: Mapped[str] = mapped_column(MEDICINE_ID)
    status: Mapped[str] = mapped_column(String(20))
    # Null only for generated demo history
    declared_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    declared_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    # "manuel" (one tap) or "scan_bl" (confirmed delivery note scan)
    source: Mapped[str] = mapped_column(String(10), default=SOURCE_MANUAL,
                                        server_default=SOURCE_MANUAL)
    # The delivery note of the history, when the pharmacist kept it (null otherwise,
    # or once the note is deleted: the declaration itself is never deleted)
    bon_id: Mapped[int | None] = mapped_column(
        ForeignKey("bons_livraison.id", ondelete="SET NULL"), index=True)


class TrackedMedicine(Base):
    """Medicines a pharmacy follows, to update them quickly."""
    __tablename__ = "tracked_medicines"

    pharmacy_id: Mapped[int] = mapped_column(
        ForeignKey("pharmacies.id", ondelete="CASCADE"), primary_key=True)
    medicine_id: Mapped[str] = mapped_column(MEDICINE_ID, primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    medicine_id: Mapped[str] = mapped_column(MEDICINE_ID)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


class Search(Base):
    """Anonymous: no user, no IP, no exact position — only the district, when known."""
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicine_id: Mapped[str] = mapped_column(MEDICINE_ID, index=True)
    district: Mapped[str | None] = mapped_column(String(100))
    searched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class RecognitionAttempt(Base):
    """Statistics only: did a photo lead to a medicine? No image, no text read, no IP."""
    __tablename__ = "recognition_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    succeeded: Mapped[bool] = mapped_column(Boolean)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class InterpretationCache(Base):
    """What the language model understood of a query, so it is never asked twice.

    Only the query text (lowercase, cleaned) and the model's answer: no IP, no user.
    """
    __tablename__ = "interpretations_cache"

    id: Mapped[int] = mapped_column(primary_key=True)
    requete_normalisee: Mapped[str] = mapped_column(String(200), unique=True)
    reponse_json: Mapped[str] = mapped_column(Text)
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# --------------------------------------------------------------------------
# Delivery notes (pharmacists). No price or amount is ever stored.
# --------------------------------------------------------------------------

class DeliveryScan(Base):
    """A delivery note read but not confirmed yet: deleted after 1 hour, or on confirmation."""
    __tablename__ = "delivery_scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    pharmacie_id: Mapped[int] = mapped_column(ForeignKey("pharmacies.id", ondelete="CASCADE"),
                                              index=True)
    cree_par: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expire_le: Mapped[datetime] = mapped_column(DateTime, index=True)
    resultat_json: Mapped[str] = mapped_column(Text)
    photo_possible: Mapped[bool] = mapped_column(Boolean, default=False)
    # Set on confirmation: the content is erased at once, the row stays until it
    # expires so that a second confirmation gets a clear "already confirmed"
    confirme_le: Mapped[datetime | None] = mapped_column(DateTime)

    pages: Mapped[list["DeliveryScanPage"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="DeliveryScanPage.page")


class DeliveryScanPage(Base):
    """Compressed page kept only while the pharmacist may still choose "keep the photo"."""
    __tablename__ = "delivery_scan_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[str] = mapped_column(ForeignKey("delivery_scans.id", ondelete="CASCADE"),
                                         index=True)
    page: Mapped[int] = mapped_column(Integer)
    image: Mapped[bytes] = mapped_column(LargeBinary)


class DeliveryNote(Base):
    """A delivery note the pharmacist chose to keep in the history (traceability)."""
    __tablename__ = "bons_livraison"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Deleting the pharmacy (and its account) deletes its whole history
    pharmacie_id: Mapped[int] = mapped_column(ForeignKey("pharmacies.id", ondelete="CASCADE"),
                                              index=True)
    confirme_par: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    fournisseur: Mapped[str | None] = mapped_column(String(120))
    numero_bon: Mapped[str | None] = mapped_column(String(60))
    date_bon: Mapped[date | None] = mapped_column(Date)
    scanne_le: Mapped[datetime] = mapped_column(DateTime)
    confirme_le: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    duree_secondes: Mapped[int] = mapped_column(Integer)
    nb_lignes_lues: Mapped[int] = mapped_column(Integer)
    nb_mis_en_stock: Mapped[int] = mapped_column(Integer)
    nb_rupture: Mapped[int] = mapped_column(Integer)
    nb_non_livres: Mapped[int] = mapped_column(Integer)
    nb_ignores: Mapped[int] = mapped_column(Integer)
    photo_gardee: Mapped[bool] = mapped_column(Boolean, default=False)
    annule_le: Mapped[datetime | None] = mapped_column(DateTime)

    lignes: Mapped[list["DeliveryLine"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="DeliveryLine.id")
    photos: Mapped[list["DeliveryPhoto"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="DeliveryPhoto.page")


class DeliveryLine(Base):
    __tablename__ = "lignes_bon"

    id: Mapped[int] = mapped_column(primary_key=True)
    bon_id: Mapped[int] = mapped_column(ForeignKey("bons_livraison.id", ondelete="CASCADE"),
                                        index=True)
    designation_lue: Mapped[str] = mapped_column(String(200))
    medicament_id: Mapped[str | None] = mapped_column(MEDICINE_ID, index=True)
    quantite: Mapped[float | None] = mapped_column(Float)
    numero_lot: Mapped[str | None] = mapped_column(String(40))
    date_peremption: Mapped[str | None] = mapped_column(String(7))  # AAAA-MM
    statut_correspondance: Mapped[str] = mapped_column(String(12))
    action: Mapped[str] = mapped_column(String(10))
    corrigee_par_pharmacien: Mapped[bool] = mapped_column(Boolean, default=False)


class DeliveryPhoto(Base):
    """Only when the pharmacist chose "keep the photo"; deleted after 90 days."""
    __tablename__ = "photos_bon"

    id: Mapped[int] = mapped_column(primary_key=True)
    bon_id: Mapped[int] = mapped_column(ForeignKey("bons_livraison.id", ondelete="CASCADE"),
                                        index=True)
    page: Mapped[int] = mapped_column(Integer)
    image: Mapped[bytes] = mapped_column(LargeBinary)  # JPEG, 300 KB max
    cree_le: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
