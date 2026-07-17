"""
Vigilante local de la carpeta de Descargas para el flujo DIAN.

Qué hace: nada más que reaccionar a archivos que TÚ ya descargaste con tus
propias manos, resolviendo el captcha de Cloudflare Turnstile en tu navegador
igual que siempre. Este script nunca abre el portal de la DIAN, nunca hace
clic en nada de Cloudflare y nunca automatiza el captcha. Solo:

  1. Vigila una carpeta (por defecto tu carpeta de Descargas de Windows).
  2. Cuando aparece un .zip nuevo, busca dentro de él el CUFE de alguno de
     los documentos "pendientes" que NOVA ya listó desde tu sesión DIAN
     (GET /dian/documentos-recibidos).
  3. Si encuentra una coincidencia exacta y sin ambigüedad, sube ese .zip a
     NOVA (POST /facturas/ingesta-pdf, que ya sabe extraer el PDF del zip)
     con los datos que la DIAN ya te había entregado en el listado.

Si no hay coincidencia exacta, el archivo se deja tal cual para que lo subas
manualmente desde el panel de Documentos — el script nunca adivina.

Uso:
    python vigilar_descargas_dian.py --rol contador --email contador@novacontable.co \
        --password nova1234 --empresa-id <uuid> [--carpeta "C:\\Users\\...\\Downloads"]

    python vigilar_descargas_dian.py --rol empresa --email usuario@empresademo.co \
        --password nova1234
"""
import argparse
import re
import sys
import time
import zipfile
from pathlib import Path

import requests

from _cliente_nova import ClienteNovaBase, iniciar_sesion

PATRON_CUFE_CANDIDATO = re.compile(r"[0-9a-fA-F]{40,96}")


def log(msg: str) -> None:
    print(f"[vigilante-dian] {msg}", flush=True)


class ClienteNova(ClienteNovaBase):
    def documentos_pendientes(self) -> list[dict]:
        res = self.sesion.get(f"{self.api_base}/dian/documentos-recibidos")
        res.raise_for_status()
        return [d for d in res.json() if d["estado_descarga"] == "pendiente"]

    def subir_zip(self, ruta_zip: Path, pendiente: dict) -> dict:
        datos = {
            "nit_emisor": pendiente["nit_emisor"],
            "total": pendiente["total"],
            "cufe": pendiente["cufe"],
        }
        if pendiente.get("razon_social_emisor"):
            datos["razon_social_emisor"] = pendiente["razon_social_emisor"]
        if pendiente.get("numero_documento"):
            datos["numero_factura"] = pendiente["numero_documento"]

        with ruta_zip.open("rb") as f:
            return self.subir_pdf(ruta_zip.name, f.read(), datos, content_type="application/zip")


def extraer_texto_zip(ruta_zip: Path) -> str:
    """Concatena nombres de archivo y contenido textual del zip para buscar el CUFE adentro."""
    fragmentos = []
    try:
        with zipfile.ZipFile(ruta_zip) as zf:
            for nombre in zf.namelist():
                fragmentos.append(nombre)
                if nombre.lower().endswith((".xml", ".txt")):
                    try:
                        fragmentos.append(zf.read(nombre).decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
    except zipfile.BadZipFile:
        return ""
    return "\n".join(fragmentos)


def encontrar_pendiente_por_cufe(texto_zip: str, pendientes: list[dict]) -> dict | None:
    coincidencias = [p for p in pendientes if p["cufe"] and p["cufe"] in texto_zip]
    if len(coincidencias) == 1:
        return coincidencias[0]
    if len(coincidencias) > 1:
        log(f"  Coincidencia ambigua ({len(coincidencias)} pendientes contienen el mismo CUFE); se omite.")
    return None


def zip_utilizable(ruta: Path, intentos: int = 5, espera: float = 1.0) -> bool:
    """Espera a que el navegador termine de escribir el archivo (evita leer un .zip a medio bajar)."""
    for _ in range(intentos):
        try:
            with zipfile.ZipFile(ruta):
                return True
        except zipfile.BadZipFile:
            time.sleep(espera)
    return False


def vigilar(cliente: ClienteNova, carpeta: Path, intervalo: float) -> None:
    vistos: set[str] = {p.name for p in carpeta.glob("*.zip")}
    pendientes: list[dict] = []
    log(f"Vigilando {carpeta} cada {intervalo:.0f}s. Archivos .zip ya existentes se ignoran.")

    while True:
        try:
            pendientes = cliente.documentos_pendientes()
            if pendientes:
                log(f"{len(pendientes)} documento(s) pendiente(s) de descarga en la cola DIAN.")
        except requests.exceptions.RequestException as exc:
            # La DIAN falla intermitentemente del lado de ellos (500/502
            # vistos en la práctica en GetDocumentsPageToken), y la red local
            # también puede caerse un momento. No tiene sentido matar el
            # vigilante por ninguno de los dos: se sigue usando la última
            # lista de pendientes conocida y se reintenta refrescarla en el
            # próximo ciclo. RequestException cubre HTTPError, ConnectionError
            # y Timeout — capturar solo HTTPError dejaba pasar los otros dos.
            detalle = f"status {exc.response.status_code}" if exc.response is not None else str(exc)
            log(f"  No se pudo refrescar la lista de pendientes ({detalle}); se reintenta luego.")

        for ruta in sorted(carpeta.glob("*.zip")):
            if ruta.name in vistos:
                continue
            vistos.add(ruta.name)

            log(f"Nuevo archivo detectado: {ruta.name}")
            if not zip_utilizable(ruta):
                log("  No se pudo leer como zip válido (¿descarga incompleta?); se omite.")
                continue

            texto = extraer_texto_zip(ruta)
            pendiente = encontrar_pendiente_por_cufe(texto, pendientes)
            if pendiente is None:
                log("  No coincide con ningún documento pendiente conocido; queda para subida manual.")
                continue

            try:
                doc = cliente.subir_zip(ruta, pendiente)
                log(f"  Subido a NOVA: factura {doc.get('numero_factura')} · {doc.get('razon_social_emisor')}")
            except requests.HTTPError as exc:
                log(f"  Error al subir a NOVA: {exc.response.status_code} {exc.response.text}")

        time.sleep(intervalo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rol", choices=["contador", "empresa"], required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--empresa-id", help="Requerido si --rol contador y administras más de una empresa")
    parser.add_argument("--carpeta", default=str(Path.home() / "Downloads"))
    parser.add_argument("--api-base", default="http://localhost:8000/api/v1")
    parser.add_argument("--intervalo", type=float, default=5.0, help="Segundos entre revisiones de la carpeta")
    args = parser.parse_args()

    carpeta = Path(args.carpeta)
    if not carpeta.is_dir():
        sys.exit(f"La carpeta {carpeta} no existe")

    cliente = ClienteNova(args.api_base)
    iniciar_sesion(cliente, args.rol, args.email, args.password, args.empresa_id, log)
    vigilar(cliente, carpeta, args.intervalo)


if __name__ == "__main__":
    main()
