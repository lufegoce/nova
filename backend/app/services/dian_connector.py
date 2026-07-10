"""
Conector DIAN (simulado en el MVP).

En producción, `consultar_facturas_nuevas` debe reemplazarse por una llamada
real al Web Service de Facturación Electrónica de la DIAN (autenticación con
certificado digital + envío automático de Acuse de Recibo). Aquí se simula
leyendo un CSV de ejemplo, para poder probar el flujo de notificación en
tiempo real (WebSocket) sin credenciales DIAN reales.
"""
import csv
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


def consultar_facturas_nuevas() -> list[dict]:
    """Simula la consulta a la DIAN. Retorna la lista de facturas del CSV mock."""
    csv_path = Path(settings.DIAN_MOCK_CSV_PATH)
    if not csv_path.exists():
        return []

    with csv_path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def enviar_acuse_recibo(numero_factura: str) -> dict:
    """
    Simula el envío automático del Acuse de Recibo a la DIAN.
    En producción: POST firmado al endpoint oficial de la DIAN.
    """
    return {"numero_factura": numero_factura, "acuse_enviado": True, "simulado": settings.DIAN_SIMULATED}
