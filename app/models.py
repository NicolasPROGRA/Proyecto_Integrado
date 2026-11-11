"""Modelos iniciales. Se ampliarán al esquema ER definitivo en fases sucesivas."""
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Unit(Base):
    __tablename__ = 'units'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), default='')
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Staff(Base):
    __tablename__ = 'staff'
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey('units.id'), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    unit: Mapped[Unit] = relationship()

class Case(Base):
    __tablename__ = 'cases'
    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    tracking_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    case_type: Mapped[str] = mapped_column(String(30), nullable=False)
    facility: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(70), nullable=False)
    source_area: Mapped[str] = mapped_column(String(100), nullable=False, default='Sin especificar')
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default='Recibido')
    unit_id: Mapped[int] = mapped_column(ForeignKey('units.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    unit: Mapped[Unit] = relationship()
    events: Mapped[list['CaseEvent']] = relationship(back_populates='case', order_by='CaseEvent.created_at', cascade='all, delete-orphan')

class CaseEvent(Base):
    __tablename__ = 'case_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('cases.id'), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('staff.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(180), nullable=False)
    note: Mapped[str] = mapped_column(String(500), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    case: Mapped[Case] = relationship(back_populates='events')
    actor: Mapped[Staff | None] = relationship()

class Survey(Base):
    __tablename__ = 'surveys'
    id: Mapped[int] = mapped_column(primary_key=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    facility: Mapped[str] = mapped_column(String(100), nullable=False)
    aspect: Mapped[str] = mapped_column(String(70), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (CheckConstraint('rating >= 1 AND rating <= 5', name='survey_rating_range'),)

class Notice(Base):
    __tablename__ = 'notices'
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(500), default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    editor_id: Mapped[int | None] = mapped_column(ForeignKey('staff.id'))
