"""
Almacenamiento en disco de los PDF (representación gráfica) subidos manualmente.

MVP: disco local del contenedor backend, organizado por tenant. Para producción
multi-instancia, reemplazar por almacenamiento compartido (volumen de red o
object storage) para que cualquier réplica del backend pueda servir el archivo.
"""
import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def guardar_pdf(tenant_id: str, documento_id: uuid.UUID, contenido: bytes) -> str:
    """Guarda el PDF y retorna la ruta relativa (la que se persiste en la BD)."""
    directorio = Path(settings.PDF_STORAGE_DIR) / tenant_id
    directorio.mkdir(parents=True, exist_ok=True)

    ruta_relativa = f"{settings.PDF_STORAGE_DIR}/{tenant_id}/{documento_id}.pdf"
    Path(ruta_relativa).write_bytes(contenido)
    return ruta_relativa


def ruta_absoluta(ruta_relativa: str) -> Path:
    return Path(ruta_relativa).resolve()
