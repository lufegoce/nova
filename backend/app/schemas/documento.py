"""Esquemas Pydantic (contratos de entrada/salida de la API)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.documento import EstadoDocumento, TipoDocumento


class RetencionCalculada(BaseModel):
    concepto: str  # "reteFuente" | "reteICA" | "reteIVA"
    base_gravable: float
    tarifa: float
    valor: float


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: TipoDocumento
    estado: EstadoDocumento
    nit_emisor: str
    razon_social_emisor: str | None = None
    numero_factura: str | None = None
    fecha_emision: datetime | None = None
    total: float
    cuenta_puc_sugerida: str | None = None
    retenciones: dict | None = None
    origen_canal: str
    erp_estado: str
    erp_referencia: str | None = None
    erp_detalle_error: str | None = None
    creado_en: datetime
    actualizado_en: datetime
    ruta_pdf: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def tiene_pdf(self) -> bool:
        return bool(self.ruta_pdf)


class EventoAuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agente: str
    accion: str
    detalle: str | None = None
    resultado: dict | None = None
    creado_en: datetime


class AprobacionRequest(BaseModel):
    aprobado: bool
    comentario: str | None = None
    aprobado_por: str
    cuenta_puc_corregida: str | None = None
