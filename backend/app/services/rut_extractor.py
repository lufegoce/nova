"""
Extracción de datos de una empresa a partir de su RUT (PDF de la DIAN), en
tres niveles que se intentan en orden — cada uno solo si el anterior no
alcanzó a ubicar ni el nombre ni el NIT:

  1. Parseo por patrones sobre el TEXTO NATIVO del PDF (pdfplumber), sin
     llamar a ningún modelo ni motor de OCR — gratis, determinista e
     instantáneo. Funciona porque el RUT que emite la DIAN es un formulario
     con layout consistente (etiquetas numeradas seguidas de su valor en la
     misma línea o en la siguiente), confirmado contra un RUT real de
     prueba con texto seleccionable.
  2. Si el PDF es un escaneo sin texto (común en RUT viejos o subidos como
     imagen), se renderiza cada página a imagen (pdfplumber + pypdfium2, sin
     Poppler) y se le pasa OCR local con Tesseract (ver TESSERACT_CMD /
     TESSDATA_PREFIX en la config) — gratis, corre en esta máquina, sin
     depender de ninguna API. El MISMO parser por patrones del punto 1 se
     reutiliza sobre el texto que devuelve el OCR, con un par de ayudantes
     tolerantes al ruido típico de OCR (dígitos pegados en vez de separados
     por espacio, caracteres de ruido "|", "_", etc. alrededor de nombres de
     lugar). Confirmado contra un RUT real escaneado: acertó nombre, NIT,
     tipo de persona, departamento y municipio; el dígito de verificación se
     verificó además contra el algoritmo oficial de cálculo de DV del NIT.
  3. Si tampoco así se ubican nombre+NIT (o Tesseract no está instalado),
     se cae a Claude con soporte nativo de documentos — solo si
     ANTHROPIC_API_KEY está configurada.

Si ninguno de los tres funciona, se devuelve una propuesta vacía marcada
como no extraída, para que el contador diligencie el formulario a mano sin
que el flujo se rompa.

El resultado es SIEMPRE una propuesta: el contador la revisa y corrige en el
formulario de "Nueva empresa" antes de guardar nada (ver /auth/empresas/extraer-rut
y el flujo de creación de empresa). Nunca se crea una empresa directamente desde
este extractor.
"""
import base64
import io
import json
import logging
import os
import re

import pdfplumber
from anthropic import Anthropic

from app.core.config import get_settings
from app.services.ciiu import descripcion_ciiu

settings = get_settings()
logger = logging.getLogger(__name__)

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

_CAMPOS_PROPUESTA = (
    "nombre",
    "nit",
    "digito_verificacion",
    "tipo_persona",
    "responsabilidades_tributarias",
    "actividad_economica_codigo",
    "actividad_economica_descripcion",
    "direccion",
    "departamento",
    "municipio",
    "correo_electronico",
    "telefono",
    "representante_legal_nombre",
    "representante_legal_identificacion",
    "estado_rut",
)

# Umbral bajo de propósito: un PDF escaneado sin capa de texto da 0 caracteres
# (o unos pocos de ruido); uno nativo da miles. No hace falta ser preciso, solo
# distinguir "no hay texto que parsear" de "sí hay".
_MIN_CHARS_TEXTO_NATIVO = 200


def _propuesta_vacia(razon: str) -> dict:
    datos = {campo: None for campo in _CAMPOS_PROPUESTA}
    datos["extraido_automaticamente"] = False
    datos["razon"] = razon
    return datos


def _extraer_texto_pdf(contenido_pdf: bytes) -> str:
    with pdfplumber.open(io.BytesIO(contenido_pdf)) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _extraer_correo(linea: str | None) -> str | None:
    """
    Caso normal: el "@" se leyó bien, se extrae directo.

    Respaldo para OCR sobre un escaneo: el "@" a veces se confunde con una o
    dos letras (visto en la práctica: "Q" y también "QC" en
    "infoQCdominio.com"). La señal usada para detectarlo con confianza —no
    una adivinanza genérica— es que esa corrida de 1-2 letras queda en
    MAYÚSCULA en medio de un token que por lo demás es todo minúscula: un
    correo real casi nunca tiene mayúsculas sueltas ahí. Si hay más de una
    corrida candidata, es ambiguo y se descarta en vez de arriesgar un
    correo incorrecto.
    """
    if not linea:
        return None
    coincidencia = re.search(r"[\w.\-]+@[\w.\-]+\.\w{2,}", linea)
    if coincidencia:
        return coincidencia.group(0)

    coincidencia_dominio = re.search(r"\b([A-Za-z][\w.\-]*\.[A-Za-z]{2,})\b", linea)
    if not coincidencia_dominio:
        return None
    token = coincidencia_dominio.group(1)
    candidatos = list(re.finditer(r"(?<=[a-z0-9])[A-Z]{1,2}(?=[a-z0-9])", token))
    if len(candidatos) != 1:
        return None
    inicio, fin = candidatos[0].span()
    reconstruido = f"{token[:inicio]}@{token[fin:]}".lower()
    return reconstruido if re.fullmatch(r"[\w.\-]+@[\w.\-]+\.\w{2,}", reconstruido) else None


def _valor_tras_etiqueta(lineas: list[str], patron_etiqueta: str) -> str | None:
    """Busca la línea que matchea el patrón de etiqueta y devuelve la siguiente línea no vacía."""
    regex = re.compile(patron_etiqueta, re.IGNORECASE)
    for i, linea in enumerate(lineas):
        if regex.search(linea):
            for siguiente in lineas[i + 1 :]:
                siguiente = siguiente.strip()
                if siguiente:
                    return siguiente
            return None
    return None


def _linea_con_etiqueta(lineas: list[str], patron_etiqueta: str) -> str | None:
    regex = re.compile(patron_etiqueta, re.IGNORECASE)
    for linea in lineas:
        if regex.search(linea):
            return linea
    return None


def _digitos_iniciales(linea: str | None, cantidad: int) -> list[str]:
    """
    El RUT dibuja el NIT/DV y códigos como casillas de un dígito separadas por
    espacios en el texto nativo (ej. "9 0 0 9 4 0 3 0 0 2 Impuestos de
    Medellín"), pero el OCR sobre un escaneo suele leerlas pegadas sin
    espacio (ej. "901154951| g |Impuestos..."). Se recorre la línea
    caracter por caracter acumulando dígitos y se corta al toparse con dos
    letras seguidas (inicio de una palabra real); así sirve para ambos
    casos y se degrada con gracia si el OCR se comió algún dígito suelto
    (ej. el DV mal leído como letra) en vez de fallar todo o nada.
    """
    if not linea:
        return []
    digitos: list[str] = []
    letras_seguidas = 0
    for caracter in linea.strip():
        if caracter.isdigit():
            digitos.append(caracter)
            letras_seguidas = 0
            if len(digitos) >= cantidad:
                break
        elif caracter.isalpha():
            letras_seguidas += 1
            if letras_seguidas >= 2:
                break
        else:
            letras_seguidas = 0
    return digitos


def _extraer_departamento_municipio(linea: str | None) -> tuple[str | None, str | None]:
    """
    La línea de ubicación mezcla nombres (varias palabras) y códigos
    numéricos sin separador claro, ej. "COLOMBIA 1 6 9 Antioquia 0 5 Bello 0
    8 8". Se agrupan las corridas de tokens no numéricos consecutivos: el
    primer grupo es el país, el segundo el departamento, el tercero el
    municipio.
    """
    if not linea:
        return None, None
    grupos: list[str] = []
    actual: list[str] = []
    for token in linea.split():
        # El OCR sobre un escaneo suele meter caracteres de ruido ("|", "_",
        # guiones largos) pegados a las palabras reales; se descartan como
        # separador puro en vez de dejarlos ensuciar el nombre del lugar.
        limpio = token.strip("|_—–-.,;:()[]")
        if not limpio:
            continue
        if limpio.isdigit():
            if actual:
                grupos.append(" ".join(actual))
                actual = []
        else:
            actual.append(limpio)
    if actual:
        grupos.append(" ".join(actual))
    departamento = grupos[1] if len(grupos) > 1 else None
    municipio = grupos[2] if len(grupos) > 2 else None
    return departamento, municipio


def _extraer_telefono(lineas: list[str]) -> str | None:
    """
    El campo de teléfono es atípico: a diferencia de los demás, la etiqueta
    ("44. Teléfono 1") y su valor quedan en la MISMA línea, seguidos de la
    etiqueta "45. Teléfono 2" y su valor — sin separador claro entre
    etiqueta y número. Se toma el primer teléfono (44). El regex tolera
    ruido de OCR en las palabras "Código"/"Teléfono" (ej. "Teléfond" en vez
    de "Teléfono").
    """
    linea = _linea_con_etiqueta(lineas, r"44[.,]?\s*Tel[eé]fon\w{0,2}\s*1")
    if not linea:
        return None
    coincidencia = re.search(
        r"44[.,]?\s*Tel[eé]fon\w{0,2}\s*1\s*(.+?)(?:45[.,]?\s*Tel[eé]fon\w{0,2}\s*2|$)",
        linea,
        re.IGNORECASE,
    )
    if not coincidencia:
        return None
    digitos = re.sub(r"\D", "", coincidencia.group(1))
    # Celular colombiano: 10 dígitos. Fijo con indicativo: 7-10. Fuera de ese
    # rango es más probable que sea ruido que un teléfono real.
    return digitos if 7 <= len(digitos) <= 10 else None


def _parsear_por_patrones(texto: str) -> dict:
    lineas = texto.splitlines()
    datos: dict = {campo: None for campo in _CAMPOS_PROPUESTA}

    datos["nombre"] = _valor_tras_etiqueta(lineas, r"35[.,]?\s*Raz[oó]n social")

    linea_nit = _linea_con_etiqueta(lineas, r"N[uú]mero de Identificaci[oó]n Tributaria \(NIT\)")
    valor_nit = None
    if linea_nit:
        idx = lineas.index(linea_nit)
        for siguiente in lineas[idx + 1 :]:
            if siguiente.strip():
                valor_nit = siguiente.strip()
                break
    digitos_nit = _digitos_iniciales(valor_nit, 10)
    if len(digitos_nit) >= 9:
        datos["nit"] = "".join(digitos_nit[:9])
    if len(digitos_nit) >= 10:
        datos["digito_verificacion"] = digitos_nit[9]

    linea_tipo = _valor_tras_etiqueta(lineas, r"24[.,]?\s*Tipo de contribuyente")
    if linea_tipo:
        coincidencia = re.match(r"(Persona\s+\w+)", linea_tipo, re.IGNORECASE)
        if coincidencia:
            tipo = coincidencia.group(1).lower()
            if "jur" in tipo:
                datos["tipo_persona"] = "juridica"
            elif "natural" in tipo:
                datos["tipo_persona"] = "natural"

    datos["direccion"] = _valor_tras_etiqueta(lineas, r"41[.,]?\s*Direcci[oó]n principal")

    linea_ubicacion = _valor_tras_etiqueta(lineas, r"38[.,]?\s*Pa[ií]s\s+39[,.]?\s*Departamento")
    datos["departamento"], datos["municipio"] = _extraer_departamento_municipio(linea_ubicacion)

    linea_correo = _linea_con_etiqueta(lineas, r"42[.,]?\s*Correo electr[oó]nico")
    datos["correo_electronico"] = _extraer_correo(linea_correo)

    datos["telefono"] = _extraer_telefono(lineas)

    linea_actividad = _valor_tras_etiqueta(lineas, r"46[.,]?\s*C[oó]digo\s+47[.,]?\s*Fecha inicio actividad")
    digitos_actividad = _digitos_iniciales(linea_actividad, 4)
    if len(digitos_actividad) == 4:
        codigo_ciiu = "".join(digitos_actividad)
        descripcion = descripcion_ciiu(codigo_ciiu)
        # Solo se registra el código si existe en la tabla oficial CIIU (ver
        # app/services/ciiu.py): un código que no aparece ahí es evidencia de
        # que el parser (o el OCR, sobre un escaneo) leyó mal esa zona del
        # RUT — mejor dejarlo vacío para revisión manual que guardar un dato
        # falso. Un código inválido-pero-existente (leído mal y que por
        # coincidencia cae en otra actividad real) no se puede detectar así;
        # por eso el aviso de "revisa todos los campos" en el camino OCR
        # sigue aplicando.
        if descripcion:
            datos["actividad_economica_codigo"] = codigo_ciiu
            datos["actividad_economica_descripcion"] = descripcion

    datos["representante_legal_nombre"] = _valor_tras_etiqueta(
        lineas, r"104[.,]?\s*Primer apellido\s+105[.,]?\s*Segundo apellido\s+106[.,]?"
    )

    return datos


def _extraer_texto_ocr(contenido_pdf: bytes) -> str:
    """
    Respaldo para PDFs escaneados (sin capa de texto): renderiza cada página
    a imagen con pdfplumber (usa pypdfium2 internamente, sin depender de
    Poppler) y le pasa OCR local con Tesseract. Si Tesseract no está
    instalado o falla, se registra el motivo y se retorna cadena vacía para
    que el flujo siga hacia el siguiente nivel de respaldo (Claude o
    propuesta vacía) sin romper la petición.
    """
    try:
        import pytesseract
    except ImportError:
        logger.warning("pytesseract no está instalado; se omite el respaldo de OCR para el RUT.")
        return ""

    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    if settings.TESSDATA_PREFIX:
        os.environ["TESSDATA_PREFIX"] = settings.TESSDATA_PREFIX

    try:
        textos = []
        with pdfplumber.open(io.BytesIO(contenido_pdf)) as pdf:
            for pagina in pdf.pages:
                imagen = pagina.to_image(resolution=300).original
                textos.append(pytesseract.image_to_string(imagen, lang="spa"))
        return "\n".join(textos)
    except Exception:
        logger.exception("Falló el OCR local sobre el RUT; se omite este respaldo.")
        return ""


def _extraer_con_claude(contenido_pdf: bytes) -> dict:
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
    datos = json.loads(texto)
    datos["extraido_automaticamente"] = True
    datos["razon"] = None
    return datos


def extraer_datos_rut(contenido_pdf: bytes) -> dict:
    texto_nativo = _extraer_texto_pdf(contenido_pdf)
    es_escaneo = len(texto_nativo.strip()) < _MIN_CHARS_TEXTO_NATIVO

    if not es_escaneo:
        datos = _parsear_por_patrones(texto_nativo)
        if datos["nombre"] and datos["nit"]:
            datos["extraido_automaticamente"] = True
            datos["razon"] = (
                "Extraído por patrones de texto (sin usar IA); revisa los campos que hayan quedado vacíos."
            )
            return datos

    texto_ocr = _extraer_texto_ocr(contenido_pdf)
    if texto_ocr.strip():
        datos = _parsear_por_patrones(texto_ocr)
        if datos["nombre"] and datos["nit"]:
            datos["extraido_automaticamente"] = True
            datos["razon"] = (
                "Extraído por OCR local sobre un PDF escaneado (sin usar IA); el reconocimiento de "
                "texto puede tener errores — revisa TODOS los campos con más cuidado que de costumbre."
            )
            return datos

    if not settings.ANTHROPIC_API_KEY:
        if es_escaneo:
            motivo = (
                "El PDF es un escaneo sin texto seleccionable y el OCR local no logró ubicar el nombre "
                "y el NIT; diligencia el formulario manualmente."
            )
        else:
            motivo = "No se pudieron ubicar los datos con el parser por patrones; diligencia el formulario manualmente."
        return _propuesta_vacia(motivo)

    try:
        return _extraer_con_claude(contenido_pdf)
    except json.JSONDecodeError:
        return _propuesta_vacia("No se pudo interpretar la respuesta del modelo; revisa el formulario manualmente.")
