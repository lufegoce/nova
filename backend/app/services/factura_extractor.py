"""
Extracción de los datos clave de una factura a partir de su representación
gráfica en PDF, usando Claude con soporte nativo de documentos (sin OCR ni
parsing manual). Reemplaza la digitación manual del formulario de "Subir
factura en PDF": el resultado es una propuesta que el usuario revisa/corrige
antes de confirmar — nunca se ingesta la factura directamente desde aquí.

Si ANTHROPIC_API_KEY no está configurada, retorna una propuesta vacía marcada
como no extraída automáticamente, para que el usuario pueda diligenciar el
formulario a mano sin que el flujo se rompa.
"""
import base64
import json

from anthropic import Anthropic

from app.core.config import get_settings

settings = get_settings()

PROMPT_SISTEMA = """Eres un asistente experto en facturas electrónicas de venta \
colombianas (representación gráfica en PDF, formato DIAN). Se te entrega el PDF \
de una factura. Extrae los datos en JSON con EXACTAMENTE estas claves (usa null \
si un dato no aparece en el documento):

{
  "nit_emisor": string,              // NIT de quien EMITE/VENDE la factura, con dígito de verificación si aparece (ej. "811028650-1")
  "razon_social_emisor": string,     // nombre o razón social de quien emite
  "numero_factura": string,          // número/consecutivo de la factura
  "fecha_emision": string,           // formato YYYY-MM-DD
  "total": number,                   // valor neto/total a pagar de la factura (el total final, no el subtotal)
  "cufe": string                     // Código Único de Factura Electrónica (cadena hexadecimal larga)
}

Responde SIEMPRE solo con ese JSON, sin texto adicional."""


def _propuesta_vacia(razon: str) -> dict:
    return {
        "extraido_automaticamente": False,
        "razon": razon,
        "nit_emisor": None,
        "razon_social_emisor": None,
        "numero_factura": None,
        "fecha_emision": None,
        "total": None,
        "cufe": None,
    }


def extraer_datos_factura(contenido_pdf: bytes) -> dict:
    if not settings.ANTHROPIC_API_KEY:
        return _propuesta_vacia("ANTHROPIC_API_KEY no configurada; diligencia el formulario manualmente.")

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    pdf_base64 = base64.standard_b64encode(contenido_pdf).decode("utf-8")

    respuesta = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=1024,
        system=PROMPT_SISTEMA,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_base64},
                    },
                    {"type": "text", "text": "Extrae los datos de esta factura según el formato indicado."},
                ],
            }
        ],
    )

    texto = respuesta.content[0].text if respuesta.content else "{}"
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        return _propuesta_vacia("No se pudo interpretar la respuesta del modelo; revisa el formulario manualmente.")

    datos["extraido_automaticamente"] = True
    datos["razon"] = None
    return datos
