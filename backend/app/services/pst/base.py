"""
Interfaz genérica de conector PST (Proveedor de Servicios Tecnológicos
autorizado por la DIAN). A diferencia del portal humano de la DIAN, un PST
expone una API pensada para integración de software y no exige captcha.

Cualquier PST soportado implementa esta interfaz; agregar uno nuevo es
escribir una clase más y registrarla en `factory.py`, sin tocar el resto
del sistema.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FiltrosDocumentosRecibidos:
    cufe: str | None = None
    nit_emisor: str | None = None
    fecha_emision: str | None = None  # ISO 8601
    solo_con_eventos_pendientes: bool | None = None  # None = sin filtrar


@dataclass
class DocumentoRecibidoPst:
    """
    Documento recibido según lo devuelve el PST. Los campos base (cufe,
    nit_emisor, razon_social_emisor, numero_documento, fecha_emision) están
    confirmados contra la documentación pública del PST. El resto —
    especialmente si trae el XML/PDF embebido o solo una URL— NO está
    confirmado sin una respuesta real de la API; por eso `datos_crudos`
    conserva el JSON completo tal cual llegó, para no perder información si
    el mapeo de arriba resulta incompleto o cambia.
    """
    cufe: str
    nit_emisor: str | None
    razon_social_emisor: str | None
    numero_documento: str | None
    fecha_emision: str | None
    tiene_eventos_pendientes: bool | None
    datos_crudos: dict = field(default_factory=dict)


class ErrorConectorPst(Exception):
    pass


class ConectorPST(ABC):
    @abstractmethod
    async def listar_recibidos(self, filtros: FiltrosDocumentosRecibidos) -> list[DocumentoRecibidoPst]:
        """Lista/filtra los documentos recibidos por la empresa según el PST."""
        ...

    @abstractmethod
    async def probar_conexion(self) -> None:
        """Verifica que las credenciales sirven (ej. solo obtiene el token). Lanza ErrorConectorPst si falla."""
        ...
