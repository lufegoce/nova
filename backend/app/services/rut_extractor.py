"""
Extracción de datos de una empresa a partir de su RUT (PDF de la DIAN) usando
Claude con soporte nativo de documentos (sin OCR/parsing manual).

El resultado es SIEMPRE una propuesta: el contador la revisa y corrige en el
formulario de "Nueva empresa" antes de guardar nada (ver /auth/empresas/extraer-rut
y el flujo de creación de empresa). Nunca se crea una empresa directamente desde
este extractor.

Si ANTHROPIC_API_KEY no está configurada, retorna una propuesta vacía marcada
como no extraída automáticamente, para que el contador pueda diligenciar el
formulario a mano sin que el flujo se rompa.
"""
import base64
import json

from anthropic import Anthropic

from app.core.config import get_settings

settings = get_settings()

PROMPT_SISTEMA = """Eres un asistente experto en el Registro Único Tributario (RUT) \
colombiano emitido por la DIAN. Se te entrega el PDF de un RUT. Extrae los datos \
en JSON con EXACTAMENTE estas claves (usa null si un dato no aparece en el documento):

{
  "nombre": string,                          // razón social o nombre completo
  "nit": string,                             // solo dígitos, sin el DV
  "digito_verificacion": string,             // 1 dígito
  "tipo_persona": "natural" | "juridica",
  "responsabilidades_tributarias": [{"codigo": string, "descripcion": string}],
  "actividad_economica_codigo": string,      // código CIIU principal
  "actividad_economica_descripcion": string,
  "direccion": string,
  "departamento": string,
  "municipio": string,
  "correo_electronico": string,
  "telefono": string,
  "representante_legal_nombre": string,
  "representante_legal_identificacion": string,
  "estado_rut": string                       // ej. "Activo", "Cancelado"
}

Responde SIEMPRE solo con ese JSON, sin texto adicional."""


def _propuesta_vacia(razon: str) -> dict:
    return {
        "extraido_automaticamente": False,
        "razon": razon,
        "nombre": None,
        "nit": None,
        "digito_verificacion": None,
        "tipo_persona": None,
        "responsabilidades_tributarias": None,
        "actividad_economica_codigo": None,
        "actividad_economica_descripcion": None,
        "direccion": None,
        "departamento": None,
        "municipio": None,
        "correo_electronico": None,
        "telefono": None,
        "representante_legal_nombre": None,
        "representante_legal_identificacion": None,
        "estado_rut": None,
    }


def extraer_datos_rut(contenido_pdf: bytes) -> dict:
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
                    {"type": "text", "text": "Extrae los datos de este RUT según el formato indicado."},
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
