import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.seguridad import SeveridadAlerta


class AlertaSeguridadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    severidad: SeveridadAlerta
    detalle: str
    contexto: dict | None = None
    documento_id: uuid.UUID | None = None
    resuelta: bool
    creado_en: datetime


class ResultadoEscaneoOut(BaseModel):
    aprobaciones_rapidas: int
    pago_rapido_alto_valor: int
    fallos_erp_repetidos: int
    correcciones_puc_inestables: int
    total_alertas_nuevas: int
