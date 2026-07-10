"""
Enriquecimiento de facturas con Claude: clasificación contable (PUC) y
categorización del gasto. Esta es la parte "IA" del Agente Receptor/Contable.

Si ANTHROPIC_API_KEY no está configurada, retorna una sugerencia por defecto
para que el flujo del MVP no se rompa en entornos sin credenciales.
"""
import json

from anthropic import Anthropic

from app.core.config import get_settings

settings = get_settings()

PROMPT_SISTEMA = """Eres un contador público colombiano experto en el Plan Único de \
Cuentas (PUC) y en normativa DIAN. Dada la información de una factura, responde \
SIEMPRE en JSON con las claves: cuenta_puc (código de 6 dígitos), \
categoria_gasto (texto corto), justificacion (1 frase), requiere_revision_humana (booleano).
No incluyas texto fuera del JSON."""


def clasificar_factura_con_claude(
    razon_social_emisor: str | None,
    items: list[dict],
    total: float,
) -> dict:
    if not settings.ANTHROPIC_API_KEY:
        return {
            "cuenta_puc": "519999",
            "categoria_gasto": "Gastos diversos (pendiente de clasificación)",
            "justificacion": "ANTHROPIC_API_KEY no configurada; clasificación por defecto.",
            "requiere_revision_humana": True,
        }

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    descripcion_items = "\n".join(
        f"- {it.get('descripcion', 'N/A')} (valor: {it.get('valor', 'N/A')})" for it in items
    ) or "Sin ítems detallados"

    mensaje_usuario = (
        f"Emisor: {razon_social_emisor or 'Desconocido'}\n"
        f"Total factura: {total}\n"
        f"Ítems:\n{descripcion_items}\n\n"
        "Clasifica esta factura en la cuenta PUC correcta y sugiere la categoría de gasto."
    )

    respuesta = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=512,
        system=PROMPT_SISTEMA,
        messages=[{"role": "user", "content": mensaje_usuario}],
    )

    texto = respuesta.content[0].text if respuesta.content else "{}"
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {
            "cuenta_puc": "519999",
            "categoria_gasto": "Gastos diversos",
            "justificacion": "No se pudo interpretar la respuesta del modelo; revisar manualmente.",
            "requiere_revision_humana": True,
        }
