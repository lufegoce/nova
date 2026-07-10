"""
Interfaz genérica de conector ERP.

Cualquier ERP soportado (SIIGO, Odoo, SAP Business One...) implementa esta
interfaz. El resto del sistema (AgentePagador, orquestador) solo conoce
`ConectorERP` — agregar un ERP nuevo es escribir una clase más y registrarla
en `factory.py`, sin tocar el flujo de aprobación/pago.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DocumentoParaErp:
    """Datos mínimos que cualquier conector ERP necesita para causar un documento."""
    documento_id: str
    tipo: str  # "factura_compra" | "factura_venta" | ...
    nit_emisor: str
    razon_social_emisor: str | None
    numero_factura: str | None
    fecha_emision: str | None  # ISO 8601
    total: float
    cuenta_puc: str
    retenciones: dict


@dataclass
class ResultadoEnvioErp:
    exitoso: bool
    referencia_erp: str | None = None
    detalle_error: str | None = None


class ErrorConectorErp(Exception):
    pass


class ConectorERP(ABC):
    @abstractmethod
    async def enviar_causacion(self, documento: DocumentoParaErp) -> ResultadoEnvioErp:
        """Envía la causación/compra al ERP y retorna la referencia o el error."""
        ...
