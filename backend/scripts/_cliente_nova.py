"""
Cliente HTTP compartido por los scripts de vigilancia (vigilar_descargas_dian.py,
vigilar_correo_facturas.py): ambos necesitan autenticarse contra NOVA con las
mismas credenciales de un usuario real y, si es un contador con varias
empresas, seleccionar cuál usar antes de poder subir nada.
"""
from pathlib import Path

import requests


class ClienteNovaBase:
    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip("/")
        self.sesion = requests.Session()

    def login(self, rol: str, email: str, password: str) -> dict:
        res = self.sesion.post(f"{self.api_base}/auth/login/{rol}", json={"email": email, "password": password})
        res.raise_for_status()
        return res.json()

    def listar_empresas(self) -> list[dict]:
        res = self.sesion.get(f"{self.api_base}/auth/empresas")
        res.raise_for_status()
        return res.json()

    def seleccionar_empresa(self, empresa_id: str) -> dict:
        res = self.sesion.post(f"{self.api_base}/auth/empresas/{empresa_id}/seleccionar")
        res.raise_for_status()
        return res.json()

    def subir_xml(self, ruta_o_nombre, contenido: bytes) -> dict:
        nombre = ruta_o_nombre.name if isinstance(ruta_o_nombre, Path) else str(ruta_o_nombre)
        archivos = {"archivo": (nombre, contenido, "application/xml")}
        res = self.sesion.post(f"{self.api_base}/facturas/ingesta", files=archivos)
        res.raise_for_status()
        return res.json()

    def extraer_datos_pdf(self, nombre: str, contenido: bytes, content_type: str = "application/pdf") -> dict:
        archivos = {"archivo": (nombre, contenido, content_type)}
        res = self.sesion.post(f"{self.api_base}/facturas/extraer-datos-pdf", files=archivos)
        res.raise_for_status()
        return res.json()

    def subir_pdf(self, nombre: str, contenido: bytes, datos: dict, content_type: str = "application/pdf") -> dict:
        archivos = {"archivo": (nombre, contenido, content_type)}
        res = self.sesion.post(f"{self.api_base}/facturas/ingesta-pdf", data=datos, files=archivos)
        res.raise_for_status()
        return res.json()


def iniciar_sesion(cliente: ClienteNovaBase, rol: str, email: str, password: str, empresa_id: str | None, log) -> dict:
    """
    Login + selección de empresa compartidos por ambos vigilantes. Si el
    contador administra varias empresas y no se pasó --empresa-id, se
    imprimen las opciones y se detiene el script (no hay forma segura de
    adivinar en cuál empresa subir las facturas).
    """
    sesion = cliente.login(rol, email, password)
    log(f"Sesión iniciada como {sesion['nombre']} ({sesion['rol']})")

    if sesion["rol"] == "contador":
        if empresa_id:
            sesion = cliente.seleccionar_empresa(empresa_id)
        elif not sesion.get("empresa_actual"):
            empresas = cliente.listar_empresas()
            log("Este contador administra varias empresas. Pasa --empresa-id con una de estas:")
            for e in empresas:
                log(f"  {e['id']}  {e['nombre']}")
            raise SystemExit(1)

    log(f"Empresa activa: {sesion['empresa_actual']['nombre']}")
    return sesion
