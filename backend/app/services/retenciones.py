"""
Cálculo de retenciones colombianas (ReteFuente, ReteICA).

Función crítica del Agente Contable: es la lógica que más impacto fiscal tiene
y por eso está aislada en un módulo puro (sin efectos secundarios) fácil de
probar unitariamente. Tarifas configurables, no hardcodeadas en el flujo.

Nota: las tarifas de ejemplo son ilustrativas para el MVP. Para producción,
deben parametrizarse por concepto/tenant y actualizarse según normativa DIAN vigente.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptoRetencion:
    nombre: str
    tarifa: float  # porcentaje, ej. 0.025 = 2.5%
    base_minima_uvt: float  # base mínima sujeta a retención, en UVT


# Tabla simplificada de ReteFuente por concepto (compras, servicios, honorarios)
CONCEPTOS_RETEFUENTE: dict[str, ConceptoRetencion] = {
    "compras_generales": ConceptoRetencion("Compras generales", 0.025, 27),
    "servicios_generales": ConceptoRetencion("Servicios generales", 0.04, 4),
    "honorarios": ConceptoRetencion("Honorarios", 0.11, 0),
}

VALOR_UVT_COP = 47065  # UVT vigente de referencia (parametrizar por año fiscal)


def calcular_retefuente(base_gravable: float, concepto: str) -> dict:
    """
    Calcula la retención en la fuente para un concepto dado.
    Retorna 0 si la base no supera el mínimo sujeto a retención.
    """
    if concepto not in CONCEPTOS_RETEFUENTE:
        raise ValueError(f"Concepto de ReteFuente no soportado: {concepto}")

    info = CONCEPTOS_RETEFUENTE[concepto]
    base_minima_cop = info.base_minima_uvt * VALOR_UVT_COP

    if base_gravable < base_minima_cop:
        valor = 0.0
    else:
        valor = round(base_gravable * info.tarifa, 2)

    return {
        "concepto": "reteFuente",
        "detalle_concepto": info.nombre,
        "base_gravable": base_gravable,
        "tarifa": info.tarifa,
        "valor": valor,
    }


def calcular_reteica(base_gravable: float, tarifa_por_mil: float) -> dict:
    """
    Calcula ReteICA. La tarifa varía por municipio y actividad económica,
    se expresa en 'por mil' (ej. 6.9 x mil en Bogotá para algunas actividades).
    """
    if tarifa_por_mil < 0:
        raise ValueError("La tarifa de ReteICA no puede ser negativa")

    tarifa_decimal = tarifa_por_mil / 1000
    valor = round(base_gravable * tarifa_decimal, 2)

    return {
        "concepto": "reteICA",
        "base_gravable": base_gravable,
        "tarifa": tarifa_decimal,
        "valor": valor,
    }
