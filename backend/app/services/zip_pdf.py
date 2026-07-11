"""Utilidad compartida: el portal de la DIAN entrega la representación gráfica
de la factura dentro de un .zip (no el PDF suelto). Usada tanto por la ingesta
manual de facturas como por la extracción automática de datos del PDF."""
import io
import zipfile

from fastapi import HTTPException


def extraer_pdf_si_es_zip(nombre_archivo: str, contenido: bytes) -> bytes:
    """Si el archivo subido es un zip, extrae el primer PDF que contenga; si es un PDF normal, lo devuelve tal cual."""
    parece_zip = (nombre_archivo or "").lower().endswith(".zip") or contenido[:4] == b"PK\x03\x04"
    if not parece_zip:
        return contenido

    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as zf:
            nombres_pdf = sorted(
                n for n in zf.namelist() if n.lower().endswith(".pdf") and not n.startswith("__MACOSX")
            )
            if not nombres_pdf:
                raise HTTPException(status_code=422, detail="El .zip no contiene ningún archivo PDF")
            return zf.read(nombres_pdf[0])
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=422, detail="El archivo .zip está dañado o no es un zip válido") from exc
