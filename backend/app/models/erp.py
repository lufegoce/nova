"""
Configuración del ERP contable del tenant (SIIGO, Odoo, SAP Business One,
Alegra, Loggro, ContaPyme, Siesa, Defontana...).

Las credenciales se guardan en JSONB en texto plano en este MVP — igual que
`SesionDian.cookies`, es un secreto real y debe cifrarse en reposo (KMS/HSM)
antes de cualquier despliegue que no sea desarrollo local.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoErp(str, enum.Enum):
    SIIGO = "siigo"
    ODOO = "odoo"
    SAP_BUSINESS_ONE = "sap_business_one"
    ALEGRA = "alegra"
    LOGGRO = "loggro"
    CONTAPYME = "contapyme"
    SIESA = "siesa"
    DEFONTANA = "defontana"


class ConfiguracionErp(Base):
    __tablename__ = "configuraciones_erp"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    tipo_erp: Mapped[TipoErp] = mapped_column(Enum(TipoErp), nullable=False)
    credenciales: Mapped[dict] = mapped_column(JSONB, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
