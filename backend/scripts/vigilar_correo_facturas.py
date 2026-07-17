"""
Vigilante local de un buzón de correo para el flujo de facturas de compra.

Por qué existe: ni el portal de la DIAN ni Factus (el PST integrado, ver
app/services/pst/factus_connector.py) exponen el PDF/XML de una factura por
API — está confirmado en vivo contra ambos. Si un proveedor está dispuesto a
enviar la factura por correo directamente, este script evita que un humano
tenga que abrir el modal de NOVA y subir el archivo a mano.

NOVA no tiene un dominio público expuesto, así que no puede recibir correo
entrante directamente (eso requeriría un webhook de un proveedor tipo
SendGrid/Mailgun con MX propio). En su lugar, este script se conecta por IMAP
a un buzón que TÚ controlas (ej. facturas@tuempresa.co) y hace de puente:

  1. Revisa periódicamente los correos no leídos de la carpeta configurada.
  2. Por cada adjunto .xml, lo sube tal cual a NOVA (POST /facturas/ingesta):
     es el canal "automático y confiable" del Agente Receptor (ver
     app/agents/agente_receptor.py) — si es una factura UBL válida, queda
     causada sin intervención humana.
  3. Por cada adjunto .pdf o .zip, primero le pide a NOVA que lo lea con IA
     (POST /facturas/extraer-datos-pdf). Solo si la lectura automática
     encontró NIT y total con confianza lo sube (POST /facturas/ingesta-pdf);
     si no, el script NO adivina los campos — dejar pasar una factura con NIT
     o total mal leídos sería peor que no automatizarla. Se deja el correo
     sin marcar como leído y se reporta para subirlo a mano desde el panel de
     Documentos, con los mismos controles de revisión que ya existen ahí.
  4. Solo se marca como leído lo que efectivamente se pudo resolver (subido,
     o rechazado por NOVA por venir mal formado — ahí ya no hay nada más que
     intentar). Lo que quedó pendiente de revisión humana se deja sin leer
     para que la próxima corrida lo vuelva a reportar.

Si el proveedor de correo exige 2FA (Gmail, Outlook), --imap-password debe
ser una contraseña de aplicación, no la contraseña normal de la cuenta.

Uso:
    python vigilar_correo_facturas.py --rol contador --email contador@novacontable.co \
        --password nova1234 --empresa-id <uuid> \
        --imap-host imap.gmail.com --imap-usuario facturas@tuempresa.co \
        --imap-password <contraseña-de-aplicación>
"""
import argparse
import email
import imaplib
import time
from email.message import Message

import requests

from _cliente_nova import ClienteNovaBase, iniciar_sesion

_EXTENSIONES_XML = ("xml",)
_EXTENSIONES_PDF_O_ZIP = ("pdf", "zip")


def log(msg: str) -> None:
    print(f"[vigilante-correo] {msg}", flush=True)


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


def _subir_xml(cliente: ClienteNovaBase, nombre: str, contenido: bytes, remitente: str) -> bool:
    """True si quedó resuelto (subido o descartado por formato inválido)."""
    try:
        doc = cliente.subir_xml(nombre, contenido)
        log(f"  XML '{nombre}' de {remitente} subido: factura {doc.get('numero_factura')} · {doc.get('estado')}")
        return True
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 422:
            log(f"  XML '{nombre}' de {remitente} rechazado por NOVA (formato inválido); se descarta.")
            return True
        log(f"  Error subiendo XML '{nombre}': {exc}")
        return False


def _subir_pdf_o_zip(cliente: ClienteNovaBase, nombre: str, contenido: bytes, remitente: str, asunto: str) -> bool:
    """True si quedó resuelto (subido, o descartado tras avisar que necesita revisión humana)."""
    content_type = "application/zip" if nombre.lower().endswith(".zip") else "application/pdf"

    try:
        propuesta = cliente.extraer_datos_pdf(nombre, contenido, content_type=content_type)
    except requests.HTTPError as exc:
        log(f"  No se pudo leer '{nombre}' de {remitente} con IA: {exc}")
        return False

    tiene_datos_confiables = (
        propuesta.get("extraido_automaticamente") and propuesta.get("nit_emisor") and propuesta.get("total") is not None
    )
    if not tiene_datos_confiables:
        log(
            f"  '{nombre}' de {remitente} (asunto: {asunto!r}) no se pudo leer con confianza; "
            "súbelo a mano desde el panel de Documentos. El correo queda sin marcar como leído."
        )
        return False

    datos = {"nit_emisor": propuesta["nit_emisor"], "total": propuesta["total"]}
    for campo_propuesta, campo_form in (
        ("razon_social_emisor", "razon_social_emisor"),
        ("numero_factura", "numero_factura"),
        ("cufe", "cufe"),
    ):
        if propuesta.get(campo_propuesta):
            datos[campo_form] = propuesta[campo_propuesta]

    try:
        doc = cliente.subir_pdf(nombre, contenido, datos, content_type=content_type)
        log(f"  '{nombre}' de {remitente} subido: factura {doc.get('numero_factura')} · {doc.get('estado')}")
        return True
    except requests.HTTPError as exc:
        log(f"  Error subiendo '{nombre}': {exc}")
        return False


def _procesar_correo(cliente: ClienteNovaBase, remitente: str, asunto: str, msg: Message) -> bool:
    """
    True si el correo se puede marcar como leído: todos sus adjuntos
    relevantes quedaron subidos o descartados por error de formato. False si
    algo quedó pendiente de revisión humana (se reintenta en la próxima corrida).
    """
    relevantes = [
        (nombre, contenido)
        for nombre, contenido in _adjuntos(msg)
        if nombre.lower().rsplit(".", 1)[-1] in (_EXTENSIONES_XML + _EXTENSIONES_PDF_O_ZIP)
    ]
    if not relevantes:
        log(f"  Correo de {remitente} (asunto: {asunto!r}) sin adjuntos .xml/.pdf/.zip; se ignora.")
        return True

    todo_resuelto = True
    for nombre, contenido in relevantes:
        extension = nombre.lower().rsplit(".", 1)[-1]
        if extension in _EXTENSIONES_XML:
            resuelto = _subir_xml(cliente, nombre, contenido, remitente)
        else:
            resuelto = _subir_pdf_o_zip(cliente, nombre, contenido, remitente, asunto)
        todo_resuelto = todo_resuelto and resuelto

    return todo_resuelto


def vigilar(cliente: ClienteNovaBase, conexion: imaplib.IMAP4_SSL, carpeta: str, intervalo: float) -> None:
    log(f"Vigilando el buzón ({carpeta}) cada {intervalo:.0f}s. Solo se procesan correos no leídos.")
    while True:
        conexion.select(carpeta)
        _, datos = conexion.search(None, "UNSEEN")
        ids = datos[0].split()

        if ids:
            log(f"{len(ids)} correo(s) sin leer.")

        for id_correo in ids:
            _, datos_msg = conexion.fetch(id_correo, "(RFC822)")
            msg = email.message_from_bytes(datos_msg[0][1])
            remitente = msg.get("From", "desconocido")
            asunto = msg.get("Subject", "(sin asunto)")

            if _procesar_correo(cliente, remitente, asunto, msg):
                conexion.store(id_correo, "+FLAGS", "\\Seen")

        time.sleep(intervalo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rol", choices=["contador", "empresa"], required=True)
    parser.add_argument("--email", required=True, help="Email de NOVA (no el del buzón vigilado)")
    parser.add_argument("--password", required=True, help="Password de NOVA")
    parser.add_argument("--empresa-id", help="Requerido si --rol contador y administras más de una empresa")
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1")
    parser.add_argument("--imap-host", required=True, help="ej. imap.gmail.com, outlook.office365.com")
    parser.add_argument("--imap-port", type=int, default=993)
    parser.add_argument("--imap-usuario", required=True, help="Buzón a vigilar, ej. facturas@tuempresa.co")
    parser.add_argument("--imap-password", required=True, help="Contraseña de aplicación, no la normal de la cuenta")
    parser.add_argument("--imap-carpeta", default="INBOX")
    parser.add_argument("--intervalo", type=float, default=60.0, help="Segundos entre revisiones del buzón")
    args = parser.parse_args()

    cliente = ClienteNovaBase(args.api_base)
    iniciar_sesion(cliente, args.rol, args.email, args.password, args.empresa_id, log)

    conexion = imaplib.IMAP4_SSL(args.imap_host, args.imap_port)
    conexion.login(args.imap_usuario, args.imap_password)
    log(f"Conectado al buzón {args.imap_usuario} en {args.imap_host}.")

    try:
        vigilar(cliente, conexion, args.imap_carpeta, args.intervalo)
    finally:
        conexion.logout()


if __name__ == "__main__":
    main()
