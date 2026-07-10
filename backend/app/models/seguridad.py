"""
Alertas generadas por el Agente de Seguridad al escanear el registro de
auditoría en busca de patrones anómalos (ver app/agents/agente_seguridad.py).

No reemplaza un SIEM real: es un primer nivel de detección basado en reglas,
pensado para el pilar "Zero Trust" del diseño de NOVA — hacer visibles
comportamientos sospechosos sobre datos que el sistema ya audita, no para
prevenir intrusiones a nivel de red/infraestructura.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SeveridadAlerta(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class AlertaSeguridad(Base):
    __tablename__ = "alertas_seguridad"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    tipo: Mapped[str] = mapped_column(String(60), nullable=False)  # ej. "aprobaciones_rapidas"
    severidad: Mapped[SeveridadAlerta] = mapped_column(Enum(SeveridadAlerta), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    contexto: Mapped[dict] = mapped_column(JSONB, nullable=True)
    documento_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    resuelta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
