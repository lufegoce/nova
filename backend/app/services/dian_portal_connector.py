"""
Conector REAL (no simulado) al Catálogo de Visualización de Documentos de la DIAN
(catalogo-vpfe.dian.gov.co), verificado contra el portal de producción.

Alcance verificado manualmente (ver README backend, sección "Integración DIAN"):
  1. `vincular_sesion`: sigue el magic-link que la DIAN envía por correo
     (`/User/AuthToken?pk=...&rk=...&token=...`) y captura las cookies de sesión
     resultantes (.AspNet.ApplicationCookie + ARRAffinity*). Confirmado con una
     petición real: responde 302 y setea las cookies.
  2. `listar_documentos_recibidos`: reproduce el POST que hace la grilla
     DataTables de `/Document/Received` contra `/Document/GetDocumentsPageToken`.
     CONFIRMADO con una llamada real (incluido el token anti-forgery): la
     respuesta trae la forma `{token, start, draw, recordsTotal,
     recordsFiltered, data: [...]}`. La app es ASP.NET con protección
     anti-forgery: cada carga de `/Document/Received` genera un
     `__RequestVerificationToken` (hidden input + cookie pareja) que debe
     reenviarse en el body del POST o la DIAN responde 500. Por eso esta
     función primero hace un GET de "precarga" a `/Document/Received` para
     obtener un token fresco antes de cada listado. El esquema exacto de los
     nombres de columna DENTRO de cada fila de `data[]` sigue sin confirmar
     (ver TODO en `mapear_fila_documento`).

Deliberadamente NO se automatiza la descarga de PDFs: cada acción de descarga
(`/Document/GetFilePdf`, `/Document/DownloadZipFiles`, etc.) exige un token de
Cloudflare Turnstile resuelto en el navegador del usuario. Evadir ese captcha
programáticamente no es algo que este conector haga, así se trate de la propia
cuenta del tenant: es el control anti-automatización que la DIAN puso ahí a
propósito. El flujo soportado es semi-automático: NOVA lista, el humano abre
el portal real, resuelve el captcha y descarga; luego sube el PDF a NOVA
(endpoint /facturas/ingesta-pdf) para que el Agente Receptor lo procese.
"""
import re
from datetime import date
from urllib.parse import parse_qs, urlparse

import httpx

_PATRON_TOKEN_ANTIFORGERY = re.compile(
    r'name="__RequestVerificationToken"[^>]*value="([^"]+)"'
)

DIAN_BASE_URL = "https://catalogo-vpfe.dian.gov.co"
DIAN_AUTH_TOKEN_HOST = "catalogo-vpfe.dian.gov.co"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Nombres de cookie relevantes capturados en una petición real al magic-link.
COOKIES_RELEVANTES = (".AspNet.ApplicationCookie", "ARRAffinity", "ARRAffinitySameSite")


class DianAuthError(Exception):
    pass


def _validar_magic_link(magic_link_url: str) -> None:
    parsed = urlparse(magic_link_url)
    if parsed.hostname != DIAN_AUTH_TOKEN_HOST or not parsed.path.startswith("/User/AuthToken"):
        raise DianAuthError(
            "La URL no corresponde a un magic-link válido del catálogo DIAN "
            f"({DIAN_AUTH_TOKEN_HOST}/User/AuthToken)."
        )


def extraer_nit_del_magic_link(magic_link_url: str) -> str | None:
    """
    El magic-link trae el NIT del titular de la cuenta DIAN en el parámetro
    `rk` (ej. .../User/AuthToken?pk=...|...&rk=901154951&token=...). Se
    confirmó comparando ese valor contra el ReceiverCode real devuelto por
    GetDocumentsPageToken para esa misma sesión — coinciden.

    Esto permite validar, ANTES de guardar la cookie de sesión, que el
    enlace pegado corresponde al NIT de la empresa/tenant que lo está
    vinculando — sin esto, cualquier magic-link (de cualquier empresa) queda
    aceptado silenciosamente para el tenant activo, con el riesgo de que un
    usuario pegue por error (o a propósito) el enlace de otra compañía.
    """
    query = parse_qs(urlparse(magic_link_url).query)
    valores = query.get("rk")
    if not valores or not valores[0].strip():
        return None
    return valores[0].strip()


async def vincular_sesion(magic_link_url: str) -> dict:
    """
    Sigue el magic-link de autenticación y retorna las cookies de sesión
    resultantes como {nombre: valor}. El magic-link es de un solo uso (o de
    vida muy corta): si ya fue abierto antes (por el usuario o por NOVA),
    esta llamada puede fallar o no devolver cookies de sesión válidas.
    """
    _validar_magic_link(magic_link_url)

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT, "Accept": "text/html"},
        timeout=20.0,
    ) as client:
        respuesta = await client.get(magic_link_url)

    cookies_capturadas = {
        nombre: client.cookies.get(nombre)
        for nombre in COOKIES_RELEVANTES
        if client.cookies.get(nombre)
    }

    if ".AspNet.ApplicationCookie" not in cookies_capturadas:
        raise DianAuthError(
            f"El portal no devolvió una cookie de sesión válida (status {respuesta.status_code}). "
            "El magic-link puede haber expirado o ya haber sido usado; solicita uno nuevo."
        )

    return cookies_capturadas


async def listar_documentos_recibidos(
    cookies: dict,
    fecha_inicio: date,
    fecha_fin: date,
    start: int = 0,
    length: int = 25,
) -> dict:
    """
    Reproduce la petición que hace la grilla de "Documentos recibidos".
    Retorna el JSON crudo: {token, start, draw, recordsTotal, recordsFiltered, data: [...]}.
    """
    async with httpx.AsyncClient(
        headers={"User-Agent": _USER_AGENT},
        cookies=cookies,
        timeout=30.0,
    ) as client:
        pagina = await client.get(f"{DIAN_BASE_URL}/Document/Received")
        if pagina.status_code in (401, 403):
            raise DianAuthError("La sesión DIAN expiró o no es válida. Vuelve a vincular con un magic-link nuevo.")

        coincidencia = _PATRON_TOKEN_ANTIFORGERY.search(pagina.text)
        if not coincidencia:
            raise DianAuthError(
                "No se pudo obtener el token anti-forgery del portal DIAN "
                "(la sesión puede haber expirado). Vuelve a vincular con un magic-link nuevo."
            )
        token_antiforgery = coincidencia.group(1)

        payload = {
            "draw": 1,
            "start": start,
            "length": length,
            "DocumentKey": "",
            "SerieAndNumber": "",
            "SenderCode": "",
            "ReceiverCode": "",
            "StartDate": fecha_inicio.isoformat(),
            "EndDate": fecha_fin.isoformat(),
            "DocumentTypeId": "00",
            "Status": "0",
            "IsNextPage": False,
            "FilterType": "3",
            "blockIndex": 0,
            "RadianStatus": "0",
            "__RequestVerificationToken": token_antiforgery,
        }

        respuesta = await client.post(f"{DIAN_BASE_URL}/Document/GetDocumentsPageToken", data=payload)

    if respuesta.status_code in (401, 403):
        raise DianAuthError("La sesión DIAN expiró o no es válida. Vuelve a vincular con un magic-link nuevo.")

    respuesta.raise_for_status()
    return respuesta.json()


def mapear_fila_documento(fila: dict) -> dict:
    """
    Mapea una fila cruda de la respuesta de GetDocumentsPageToken a los campos
    de DocumentoDianListado. Los nombres de clave son MEJOR ESFUERZO (inferidos
    de los `data-*` y `row.X` usados en el JS del portal), no confirmados con
    una respuesta real. Por eso cada valor tiene múltiples candidatos y, si
    ninguno aplica, queda en None sin romper el flujo — la fila cruda completa
    siempre se guarda en `datos_crudos` para poder ajustar el mapeo después.
    """
    def primero(*claves):
        for clave in claves:
            if clave in fila and fila[clave] not in (None, ""):
                return fila[clave]
        return None

    return {
        "cufe": primero("Cufe", "CUFE", "TrackId", "DocumentKey", "Id"),
        "partition_key": primero("PartitionKey", "partitionKey"),
        "nit_emisor": primero("SenderCode", "NitEmisor", "Sender"),
        "razon_social_emisor": primero("SenderName", "RazonSocialEmisor", "SenderFullName"),
        "numero_documento": primero("SerieAndNumber", "Number", "DocumentNumber"),
        "fecha_emision": primero("EmissionDate", "FechaEmision"),
        "total": primero("Total", "PayableAmount", "TotalAmount"),
    }


def url_portal_documentos_recibidos() -> str:
    """
    URL fija para que el humano abra el portal real, ubique el documento
    (por CUFE/número) y complete la descarga resolviendo el captcha él mismo.
    No se puede deep-linkear a un documento específico porque el portal exige
    un token de Turnstile ya resuelto incluso para abrir el detalle.
    """
    return f"{DIAN_BASE_URL}/Document/Received"
