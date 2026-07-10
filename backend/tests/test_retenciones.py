"""
Pruebas unitarias de la función crítica: cálculo de retenciones (ReteFuente, ReteICA).
"""
import pytest

from app.services.retenciones import (
    CONCEPTOS_RETEFUENTE,
    VALOR_UVT_COP,
    calcular_reteica,
    calcular_retefuente,
)


class TestCalcularRetefuente:
    def test_compras_generales_por_encima_del_minimo(self):
        base_minima = CONCEPTOS_RETEFUENTE["compras_generales"].base_minima_uvt * VALOR_UVT_COP
        base = base_minima + 1_000_000
        resultado = calcular_retefuente(base, "compras_generales")

        assert resultado["concepto"] == "reteFuente"
        assert resultado["tarifa"] == 0.025
        assert resultado["valor"] == round(base * 0.025, 2)

    def test_por_debajo_del_minimo_no_retiene(self):
        resultado = calcular_retefuente(1000, "compras_generales")
        assert resultado["valor"] == 0.0

    def test_honorarios_sin_base_minima_siempre_retiene(self):
        resultado = calcular_retefuente(50_000, "honorarios")
        assert resultado["valor"] == round(50_000 * 0.11, 2)

    def test_concepto_invalido_lanza_error(self):
        with pytest.raises(ValueError):
            calcular_retefuente(1_000_000, "concepto_inexistente")

    def test_servicios_generales_tarifa_correcta(self):
        base = 5_000_000
        resultado = calcular_retefuente(base, "servicios_generales")
        assert resultado["tarifa"] == 0.04
        assert resultado["valor"] == round(base * 0.04, 2)


class TestCalcularReteica:
    def test_tarifa_bogota_ejemplo(self):
        resultado = calcular_reteica(10_000_000, tarifa_por_mil=6.9)
        assert resultado["concepto"] == "reteICA"
        assert resultado["tarifa"] == pytest.approx(0.0069)
        assert resultado["valor"] == round(10_000_000 * 0.0069, 2)

    def test_tarifa_cero_no_retiene(self):
        resultado = calcular_reteica(1_000_000, tarifa_por_mil=0)
        assert resultado["valor"] == 0.0

    def test_tarifa_negativa_lanza_error(self):
        with pytest.raises(ValueError):
            calcular_reteica(1_000_000, tarifa_por_mil=-1)
