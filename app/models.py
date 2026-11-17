"""Modelo relacional de 14 entidades previsto en la ES2.

Los nombres de las tablas siguen el modelo ER. Los nombres de las clases
conservan la terminología del portal existente.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON,
    String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(Base):
    __tablename__ = 'rol'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Unit(Base):
    __tablename__ = 'unidad'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False, default='')
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Staff(Base):
    __tablename__ = 'usuario_admin'
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey('rol.id', ondelete='RESTRICT'), nullable=False)
    unit_id: Mapped[int] = mapped_column(ForeignKey('unidad.id', ondelete='RESTRICT'), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    role_record: Mapped[Role] = relationship()
    unit: Mapped[Unit] = relationship()

    @property
    def role(self):
        return self.role_record.code


class RecordType(Base):
    __tablename__ = 'tipo_registro'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Channel(Base):
    __tablename__ = 'canal'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class Category(Base):
    __tablename__ = 'categoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(70), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CaseStatus(Base):
    __tablename__ = 'estado_caso'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Citizen(Base):
    __tablename__ = 'ciudadano'
    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255))
    contact_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)


class Case(Base):
    __tablename__ = 'registro'
    id: Mapped[int] = mapped_column(primary_key=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    tracking_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    record_type_id: Mapped[int] = mapped_column(ForeignKey('tipo_registro.id', ondelete='RESTRICT'), nullable=False)
    channel_id: Mapped[int] = mapped_column(ForeignKey('canal.id', ondelete='RESTRICT'), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey('categoria.id', ondelete='RESTRICT'))
    status_id: Mapped[int | None] = mapped_column(ForeignKey('estado_caso.id', ondelete='RESTRICT'))
    citizen_id: Mapped[int | None] = mapped_column(ForeignKey('ciudadano.id', ondelete='SET NULL'))
    unit_id: Mapped[int | None] = mapped_column(ForeignKey('unidad.id', ondelete='RESTRICT'))
    facility: Mapped[str] = mapped_column(String(100), nullable=False)
    source_area: Mapped[str] = mapped_column(String(100), nullable=False, default='Sin especificar')
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    record_type: Mapped[RecordType] = relationship()
    channel: Mapped[Channel] = relationship()
    category_record: Mapped[Category | None] = relationship()
    status_record: Mapped[CaseStatus | None] = relationship()
    citizen: Mapped[Citizen | None] = relationship()
    unit: Mapped[Unit | None] = relationship()
    events: Mapped[list['CaseEvent']] = relationship(back_populates='case', order_by='CaseEvent.created_at', cascade='all, delete-orphan')
    attachments: Mapped[list['Attachment']] = relationship(back_populates='record', cascade='all, delete-orphan')

    @property
    def case_type(self):
        return self.record_type.name

    @property
    def category(self):
        return self.category_record.name if self.category_record else None

    @property
    def status(self):
        return self.status_record.name if self.status_record else None

    __table_args__ = (
        Index('ix_registro_unidad_estado_fecha', 'unit_id', 'status_id', 'created_at'),
        Index('ix_registro_tipo_categoria_fecha', 'record_type_id', 'category_id', 'created_at'),
        CheckConstraint('length(tracking_hmac) = 64', name='tracking_hmac_length'),
    )


class CaseEvent(Base):
    __tablename__ = 'seguimiento'
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey('registro.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('usuario_admin.id', ondelete='SET NULL'))
    status_id: Mapped[int | None] = mapped_column(ForeignKey('estado_caso.id', ondelete='RESTRICT'))
    target_unit_id: Mapped[int | None] = mapped_column(ForeignKey('unidad.id', ondelete='RESTRICT'))
    action: Mapped[str] = mapped_column(String(180), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    case: Mapped[Case] = relationship(back_populates='events')
    actor: Mapped[Staff | None] = relationship()


class SurveyQuestion(Base):
    __tablename__ = 'pregunta_encuesta'
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    text: Mapped[str] = mapped_column(String(240), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Survey(Base):
    __tablename__ = 'respuesta_encuesta'
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey('registro.id', ondelete='CASCADE'), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey('pregunta_encuesta.id', ondelete='RESTRICT'), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    record: Mapped[Case] = relationship()
    question: Mapped[SurveyQuestion] = relationship()
    __table_args__ = (
        CheckConstraint('rating BETWEEN 1 AND 5', name='survey_rating_range'),
        UniqueConstraint('record_id', 'question_id', name='uq_respuesta_registro_pregunta'),
        Index('ix_respuesta_pregunta_fecha', 'question_id', 'created_at'),
    )


class Attachment(Base):
    __tablename__ = 'adjunto'
    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey('registro.id', ondelete='CASCADE'), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    record: Mapped[Case] = relationship(back_populates='attachments')
    __table_args__ = (CheckConstraint('size_bytes >= 0', name='attachment_nonnegative_size'),)


class Audit(Base):
    __tablename__ = 'auditoria'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('usuario_admin.id', ondelete='SET NULL'))
    record_id: Mapped[int | None] = mapped_column(ForeignKey('registro.id', ondelete='SET NULL'))
    event_type: Mapped[str] = mapped_column(String(70), nullable=False)
    details: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, 'postgresql'), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    __table_args__ = (Index('ix_auditoria_evento_fecha', 'event_type', 'created_at'),)
