"""
Modelo del ciclo de vida del "Documento Financiero" (factura, nómina, cuenta de cobro).

Estados posibles (ver enum EstadoDocumento): reflejan el flujo de valor descrito
en el diseño de NOVA -> Nuevo -> Validado -> Causado -> Pagado / ConError.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EstadoDocumento(str, enum.Enum):
    NUEVO = "nuevo"
    VALIDADO = "validado"
    CAUSADO = "causado"
    APROBACION_PENDIENTE = "aprobacion_pendiente"
    PAGADO = "pagado"
    CON_ERROR = "con_error"
    RECHAZADO = "rechazado"


class TipoDocumento(str, enum.Enum):
    FACTURA_VENTA = "factura_venta"
    FACTURA_COMPRA = "factura_compra"
    NOMINA = "nomina"
    CUENTA_COBRO = "cuenta_cobro"


class DocumentoFinanciero(Base):
    __tablename__ = "documentos_financieros"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    tipo: Mapped[TipoDocumento] = mapped_column(Enum(TipoDocumento), nullable=False)
    estado: Mapped[EstadoDocumento] = mapped_column(
        Enum(EstadoDocumento), default=EstadoDocumento.NUEVO, nullable=False, index=True
    )

    # Datos extraídos del XML/PDF por el Agente Receptor
    nit_emisor: Mapped[str] = mapped_column(String(20), nullable=False)
    razon_social_emisor: Mapped[str] = mapped_column(String(255), nullable=True)
    numero_factura: Mapped[str] = mapped_column(String(50), nullable=True, index=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0)

    # Propuesta del Agente Contable: cuenta PUC sugerida y retenciones calculadas
    cuenta_puc_sugerida: Mapped[str] = mapped_column(String(20), nullable=True)
    retenciones: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Payload crudo (XML parseado / metadata del canal de ingesta)
    datos_extraidos: Mapped[dict] = mapped_column(JSONB, nullable=True)
    origen_canal: Mapped[str] = mapped_column(String(30), nullable=False, default="upload")

    # Ruta en disco del PDF (representación gráfica) cuando la ingesta fue manual por PDF
    ruta_pdf: Mapped[str] = mapped_column(String(500), nullable=True)

    # Sincronización con el ERP contable del tenant (ver app/services/erp/)
    erp_estado: Mapped[str] = mapped_column(String(20), default="no_configurado", nullable=False)
    erp_referencia: Mapped[str] = mapped_column(String(100), nullable=True)
    erp_detalle_error: Mapped[str] = mapped_column(Text, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    eventos: Mapped[list["EventoAuditoria"]] = relationship(
        back_populates="documento", cascade="all, delete-orphan"
    )


class EventoAuditoria(Base):
    """
    Registro inmutable de cada acción ejecutada por un agente sobre un documento.
    Es la base de la trazabilidad: permite responder "¿por qué no se pagó la factura 123?".
    Nunca se actualiza ni se borra un evento, solo se insertan nuevos (append-only).
    """
    __tablename__ = "eventos_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    documento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documentos_financieros.id"), index=True)

    agente: Mapped[str] = mapped_column(String(50), nullable=False)  # ej. "agente_contable"
    accion: Mapped[str] = mapped_column(String(100), nullable=False)  # ej. "calculo_retencion"
    detalle: Mapped[str] = mapped_column(Text, nullable=True)
    resultado: Mapped[dict] = mapped_column(JSONB, nullable=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    documento: Mapped["DocumentoFinanciero"] = relationship(back_populates="eventos")
