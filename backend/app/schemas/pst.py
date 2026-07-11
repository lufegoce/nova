from datetime import datetime

from pydantic import BaseModel

from app.models.pst import TipoPst


class ConfiguracionPstRequest(BaseModel):
    tipo_pst: TipoPst
    credenciales: dict
    activo: bool = True


class ConfiguracionPstOut(BaseModel):
    tipo_pst: TipoPst
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    campos_configurados: list[str]

    class Config:
        from_attributes = True


class DocumentoRecibidoPstOut(BaseModel):
    cufe: str
    nit_emisor: str | None
    razon_social_emisor: str | None
    numero_documento: str | None
    fecha_emision: str | None
    tiene_eventos_pendientes: bool | None
