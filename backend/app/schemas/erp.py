from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.erp import TipoErp


class ConfiguracionErpRequest(BaseModel):
    tipo_erp: TipoErp
    credenciales: dict
    activo: bool = True


class ConfiguracionErpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo_erp: TipoErp
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    # Las credenciales NUNCA se devuelven completas; solo qué campos están seteados.
    campos_configurados: list[str]
