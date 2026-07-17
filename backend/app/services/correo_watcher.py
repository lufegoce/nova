"""
Sincronización periódica del buzón de correo configurado por el tenant (ver
ConfiguracionCorreoFacturas). Misma idea que backend/scripts/vigilar_correo_facturas.py
pero corriendo dentro del backend: acceso directo a la base de datos y a
AgentOrchestrator en vez de autenticarse contra NOVA y subir archivos por
HTTP como hace el script local. El script sigue existiendo para quien
prefiera correrlo por su cuenta sin guardar la contraseña del buzón en NOVA;
esta versión es la que corre sola (vía Celery Beat, ver
app/workers/tasks.py::sincronizar_correo_facturas_task) una vez el tenant
configura su buzón desde Configuración → Correo.

Mismos criterios de confianza que el script:
  - .xml: canal "automático y confiable" del Agente Receptor — se sube
    siempre, y si no es un UBL válido se descarta sin bloquear el correo.
  - .pdf/.zip: solo se sube si la lectura con IA encontró NIT y total con
    confianza; si no, el correo se deja sin marcar como leído para que
    alguien lo suba a mano desde el panel de Documentos.

imaplib no tiene API async, así que las llamadas de red IMAP se corren en un
hilo aparte (asyncio.to_thread) para no bloquear el event loop de la tarea
mientras esperan al servidor de correo — igual que se hizo con la extracción
de RUT/factura por IA en las rutas HTTP (ver app/api/routes/auth.py).
"""
import asyncio
import email
import imaplib
from email.message import Message

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import AgentOrchestrator
from app.models.correo import ConfiguracionCorreoFacturas
from app.services.factura_extractor import extraer_datos_factura
from app.services.xml_parser import XMLParseError
from app.services.zip_pdf import extraer_pdf_si_es_zip


class ErrorCorreoFacturas(Exception):
    pass


def _adjuntos(msg: Message) -> list[tuple[str, bytes]]:
    """(nombre_archivo, contenido) de cada adjunto real, ignorando el cuerpo del correo."""
    resultado = []
    for parte in msg.walk():
        if parte.get_content_maintype() == "multipart":
            continue
        nombre = parte.get_filename()
        if not nombre:
            continue
        contenido = parte.get_payload(decode=True)
        if contenido:
            resultado.append((nombre, contenido))
    return resultado


def _conectar(config: ConfiguracionCorreoFacturas) -> imaplib.IMAP4_SSL:
    conexion = imaplib.IMAP4_SSL(config.host, config.puerto)
    conexion.login(config.usuario, config.password)
    conexion.select(config.carpeta)
    return conexion


def _listar_no_leidos(conexion: imaplib.IMAP4_SSL) -> list[bytes]:
    _, datos = conexion.search(None, "UNSEEN")
    return datos[0].split()


def _leer_correo(conexion: imaplib.IMAP4_SSL, id_correo: bytes) -> Message:
    _, datos_msg = conexion.fetch(id_correo, "(RFC822)")
    return email.message_from_bytes(datos_msg[0][1])


async def probar_conexion(config: ConfiguracionCorreoFacturas) -> None:
    """Solo confirma que las credenciales IMAP sirven, sin procesar nada."""
    try:
        conexion = await asyncio.to_thread(_conectar, config)
        await asyncio.to_thread(conexion.logout)
    except Exception as exc:
        raise ErrorCorreoFacturas(f"No se pudo conectar al buzón {config.usuario}: {exc}") from exc


async def _procesar_adjunto_xml(orquestador: AgentOrchestrator, contenido: bytes) -> bool:
    """True si se subió correctamente."""
    try:
        await orquestador.procesar_documento_entrante(contenido, origen_canal="email")
        return True
    except XMLParseError:
        # No es un UBL válido: no hay nada más que intentar con este adjunto.
        return False


async def _procesar_adjunto_pdf_o_zip(orquestador: AgentOrchestrator, nombre: str, contenido: bytes) -> bool | None:
    """True si se subió, False si NOVA lo rechazó, None si necesita revisión humana."""
    contenido_pdf = extraer_pdf_si_es_zip(nombre, contenido)
    propuesta = await asyncio.to_thread(extraer_datos_factura, contenido_pdf)

    tiene_datos_confiables = (
        propuesta.get("extraido_automaticamente") and propuesta.get("nit_emisor") and propuesta.get("total") is not None
    )
    if not tiene_datos_confiables:
        return None

    await orquestador.procesar_pdf_manual(
        contenido_pdf,
        nit_emisor=propuesta["nit_emisor"],
        total=propuesta["total"],
        razon_social_emisor=propuesta.get("razon_social_emisor"),
        numero_factura=propuesta.get("numero_factura"),
        cufe=propuesta.get("cufe"),
    )
    return True


async def _procesar_correo(db: AsyncSession, tenant_id: str, msg: Message) -> tuple[bool, int]:
    """(correo_resuelto, cantidad_subida). correo_resuelto=False deja el correo sin marcar como leído."""
    orquestador = AgentOrchestrator(db, tenant_id)
    todo_resuelto = True
    subidos = 0

    for nombre, contenido in _adjuntos(msg):
        extension = nombre.lower().rsplit(".", 1)[-1] if "." in nombre else ""

        if extension == "xml":
            if await _procesar_adjunto_xml(orquestador, contenido):
                subidos += 1
        elif extension in ("pdf", "zip"):
            resultado = await _procesar_adjunto_pdf_o_zip(orquestador, nombre, contenido)
            if resultado is True:
                subidos += 1
            elif resultado is None:
                todo_resuelto = False

    return todo_resuelto, subidos


async def sincronizar_buzon(db: AsyncSession, config: ConfiguracionCorreoFacturas) -> dict:
    try:
        conexion = await asyncio.to_thread(_conectar, config)
        ids = await asyncio.to_thread(_listar_no_leidos, conexion)
    except Exception as exc:
        raise ErrorCorreoFacturas(f"No se pudo conectar al buzón {config.usuario}: {exc}") from exc

    subidos = 0
    pendientes_revision = 0

    try:
        for id_correo in ids:
            msg = await asyncio.to_thread(_leer_correo, conexion, id_correo)
            resuelto, n_subidos = await _procesar_correo(db, config.tenant_id, msg)
            subidos += n_subidos
            if resuelto:
                await asyncio.to_thread(conexion.store, id_correo, "+FLAGS", "\\Seen")
            else:
                pendientes_revision += 1
    finally:
        await asyncio.to_thread(conexion.logout)

    return {"correos_revisados": len(ids), "facturas_subidas": subidos, "pendientes_revision_manual": pendientes_revision}
