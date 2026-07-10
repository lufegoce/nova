"""
Memoria de aprendizaje simple del Agente Contable.

Cuando un humano corrige la cuenta PUC sugerida al aprobar una factura, esa
corrección se guarda como regla por NIT del emisor. La próxima factura del
mismo proveedor usa la regla directamente (sin pasar por el enriquecimiento
genérico de Claude), reduciendo la necesidad de revisión humana con el tiempo.

Es intencionalmente simple (una regla por NIT, no por categoría de gasto ni
por ítem); ver AgenteContable para el punto de extensión si se necesita algo
más granular más adelante.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReglaClasificacionPuc(Base):
    __tablename__ = "reglas_clasificacion_puc"
    __table_args__ = (UniqueConstraint("tenant_id", "nit_emisor", name="uq_regla_puc_tenant_nit"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    nit_emisor: Mapped[str] = mapped_column(String(20), nullable=False)

    cuenta_puc: Mapped[str] = mapped_column(String(20), nullable=False)
    veces_aplicada: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
