"""
Configuración del buzón de correo (IMAP) que el tenant quiere que NOVA
vigile para recibir facturas de proveedores directamente por email — ver
app/services/correo_watcher.py. Alternativa a subir el PDF/XML a mano: ni el
portal de la DIAN ni Factus (PST) exponen el archivo por API (confirmado en
vivo, ver docstring de app/services/pst/factus_connector.py), así que si un
proveedor puede enviarlo por correo, este es el único canal 100% automático
disponible hoy.

La contraseña se guarda en texto plano en este MVP — igual que
`SesionDian.cookies`, `ConfiguracionPst.credenciales` y
`ConfiguracionErp.credenciales` — es un secreto real y debe cifrarse en
reposo (KMS/HSM) antes de cualquier despliegue que no sea desarrollo local.
Por eso lo mismo que con esas otras credenciales, la contraseña nunca se
devuelve en las respuestas de la API (ver ConfiguracionCorreoOut).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConfiguracionCorreoFacturas(Base):
    __tablename__ = "configuraciones_correo_facturas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    host: Mapped[str] = mapped_column(String(255), nullable=False)
    puerto: Mapped[int] = mapped_column(Integer, default=993, nullable=False)
    usuario: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    carpeta: Mapped[str] = mapped_column(String(120), default="INBOX", nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
