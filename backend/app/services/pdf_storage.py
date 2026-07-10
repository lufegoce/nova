"""
Almacenamiento en disco de los PDF (representación gráfica) subidos manualmente.

MVP: disco local del contenedor backend, organizado por tenant. Para producción
multi-instancia, reemplazar por almacenamiento compartido (volumen de red o
object storage) para que cualquier réplica del backend pueda servir el archivo.
"""
import re
import uuid
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

# tenant_id ya se valida en app/api/deps.py (get_tenant_id) antes de llegar aquí,
# pero se revalida en este punto porque es el que realmente escribe al disco:
# cualquier llamador nuevo (ej. una tarea de Celery) que no pase por esa
# dependencia HTTP debe seguir estando protegido contra path traversal.
_PATRON_TENANT_ID_VALIDO = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def guardar_pdf(tenant_id: str, documento_id: uuid.UUID, contenido: bytes) -> str:
    """Guarda el PDF y retorna la ruta relativa (la que se persiste en la BD)."""
    if not _PATRON_TENANT_ID_VALIDO.match(tenant_id):
        raise ValueError(f"tenant_id inválido para almacenamiento: {tenant_id!r}")

    directorio = Path(settings.PDF_STORAGE_DIR) / tenant_id
    directorio.mkdir(parents=True, exist_ok=True)

    ruta_relativa = f"{settings.PDF_STORAGE_DIR}/{tenant_id}/{documento_id}.pdf"
    Path(ruta_relativa).write_bytes(contenido)
    return ruta_relativa


def ruta_absoluta(ruta_relativa: str) -> Path:
    return Path(ruta_relativa).resolve()
