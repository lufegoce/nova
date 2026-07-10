"""Fábrica de conectores ERP: agregar un ERP nuevo es una entrada más aquí."""
from app.models.erp import TipoErp
from app.services.erp.base import ConectorERP, ErrorConectorErp
from app.services.erp.siigo_connector import SiigoConectorERP
from app.services.erp.simulado_connector import ConectorErpSimulado


def obtener_conector_erp(tipo_erp: TipoErp, credenciales: dict) -> ConectorERP:
    if credenciales.get("modo_simulado"):
        return ConectorErpSimulado()

    if tipo_erp == TipoErp.SIIGO:
        return SiigoConectorERP(credenciales)

    raise ErrorConectorErp(
        f"ERP '{tipo_erp.value}' todavía no tiene conector real implementado "
        "(usa 'modo_simulado' para probar el flujo, o ver app/services/erp/ "
        "para agregar el conector)."
    )
