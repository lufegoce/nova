import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VincularSesionRequest(BaseModel):
    magic_link_url: str


class SesionDianOut(BaseModel):
    nit_vinculado: str | None = None
    vinculado_en: datetime
    actualizado_en: datetime


class DocumentoDianListadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cufe: str
    nit_emisor: str | None = None
    razon_social_emisor: str | None = None
    numero_documento: str | None = None
    fecha_emision: datetime | None = None
    total: str | None = None
    estado_descarga: str
    documento_financiero_id: uuid.UUID | None = None
    visto_en: datetime
