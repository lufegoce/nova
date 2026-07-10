"""
Modelos para la integración con el Catálogo de Visualización de Documentos de la DIAN.

IMPORTANTE — naturaleza de esta integración: el catálogo de la DIAN
(catalogo-vpfe.dian.gov.co) es un portal pensado para uso humano, autenticado
por un magic-link enviado a correo. No es una API pública de terceros.
- El LISTADO de documentos (POST /Document/GetDocumentsPageToken) funciona con
  solo la cookie de sesión, confirmado con una petición real.
- La DESCARGA de cada documento exige resolver un captcha de Cloudflare
  Turnstile en el navegador del usuario. Por eso NO se automatiza la descarga:
  el humano abre el portal, resuelve el captcha, descarga el PDF, y luego lo
  sube a NOVA (ver AgenteReceptor / endpoint /facturas/ingesta-pdf).

SesionDian guarda la cookie de sesión (secreto sensible) por tenant. En este
MVP se almacena en texto plano en Postgres; para producción debe cifrarse en
reposo (KMS/HSM) según el pilar Zero Trust del diseño de NOVA.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SesionDian(Base):
    __tablename__ = "sesiones_dian"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Pares nombre/valor de todas las cookies necesarias (.AspNet.ApplicationCookie,
    # ARRAffinity, ARRAffinitySameSite) capturadas al seguir el magic-link de autenticación.
    cookies: Mapped[dict] = mapped_column(JSONB, nullable=False)

    nit_vinculado: Mapped[str] = mapped_column(String(20), nullable=True)
    vinculado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DocumentoDianListado(Base):
    """
    Entrada "liviana" de un documento visto en el listado de /Document/Received.
    Todavía NO es un DocumentoFinanciero procesado: solo se convierte en uno
    cuando el humano descarga el PDF manualmente (resolviendo el captcha) y lo
    sube a NOVA. `documento_financiero_id` se completa en ese momento.
    """
    __tablename__ = "documentos_dian_listados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    cufe: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    partition_key: Mapped[str] = mapped_column(String(120), nullable=True)
    nit_emisor: Mapped[str] = mapped_column(String(20), nullable=True)
    razon_social_emisor: Mapped[str] = mapped_column(String(255), nullable=True)
    numero_documento: Mapped[str] = mapped_column(String(50), nullable=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    total: Mapped[str] = mapped_column(String(30), nullable=True)  # texto crudo: formato exacto del portal sin confirmar

    estado_descarga: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente | descargado
    documento_financiero_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)

    datos_crudos: Mapped[dict] = mapped_column(JSONB, nullable=True)
    visto_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
