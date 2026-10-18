"""Database tables.

Medicines are not stored here: they stay in memory, loaded from the CSV.
Tables refer to them by their stable id (medicine_id, 12 characters).
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
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
