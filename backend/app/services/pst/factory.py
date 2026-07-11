from app.models.pst import TipoPst
from app.services.pst.base import ConectorPST, ErrorConectorPst
from app.services.pst.factus_connector import FactusConectorPST
from app.services.pst.simulado_connector import ConectorPstSimulado


def obtener_conector_pst(tipo_pst: TipoPst, credenciales: dict) -> ConectorPST:
    if credenciales.get("modo_simulado"):
        return ConectorPstSimulado()
    if tipo_pst == TipoPst.FACTUS:
        return FactusConectorPST(credenciales)
    raise ErrorConectorPst(f"PST '{tipo_pst.value}' todavía no tiene conector real implementado.")
