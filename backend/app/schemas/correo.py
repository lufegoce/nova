from datetime import datetime

from pydantic import BaseModel


class ConfiguracionCorreoRequest(BaseModel):
    host: str
    puerto: int = 993
    usuario: str
    # Opcional solo al actualizar una configuración existente (se mantiene la
    # contraseña guardada si se omite); obligatoria al crear una nueva — ver
    # guardar_configuracion_correo en app/api/routes/configuracion.py.
    password: str | None = None
    carpeta: str = "INBOX"
    activo: bool = True


class ConfiguracionCorreoOut(BaseModel):
    """Nunca incluye `password` — ver docstring de ConfiguracionCorreoFacturas."""

    host: str
    puerto: int
    usuario: str
    carpeta: str
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    class Config:
        from_attributes = True
