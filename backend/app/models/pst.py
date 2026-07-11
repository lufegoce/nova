"""
Configuración del PST (Proveedor de Servicios Tecnológicos autorizado por la
DIAN) del tenant. A diferencia del portal de la DIAN (ver dian_portal_connector.py),
un PST expone una API pensada para integración de software: no exige captcha,
porque no es la interfaz humana de la DIAN sino un canal autorizado para
terceros. Esto reemplaza al flujo semi-manual (humano resuelve captcha) por
consulta automática de documentos recibidos.

Las credenciales se guardan en JSONB en texto plano en este MVP — igual que
`SesionDian.cookies` y `ConfiguracionErp.credenciales` — es un secreto real y
debe cifrarse en reposo (KMS/HSM) antes de cualquier despliegue que no sea
desarrollo local.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TipoPst(str, enum.Enum):
    FACTUS = "factus"


class ConfiguracionPst(Base):
    __tablename__ = "configuraciones_pst"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    tipo_pst: Mapped[TipoPst] = mapped_column(Enum(TipoPst), nullable=False)
    credenciales: Mapped[dict] = mapped_column(JSONB, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
