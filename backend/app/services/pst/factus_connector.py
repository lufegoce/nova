"""
Conector para Factus API (PST autorizado por la DIAN) — módulo "Recepción de
documentos": permite consultar las facturas electrónicas que le llegaron a la
empresa de sus proveedores, sin pasar por el portal humano de la DIAN y por
lo tanto sin el captcha de Cloudflare Turnstile que bloquea la automatización
del Catálogo de Visualización (ver dian_portal_connector.py).

✅ ESTADO: verificado en vivo contra el sandbox (2026-07-15) con credenciales
reales de Factus:
  - Autenticación: POST {base}/oauth/token (form-data: grant_type=password,
    client_id, client_secret, username, password) -> {access_token,
    refresh_token, expires_in, token_type}. Confirmado, funciona.
  - Listado: GET {base}/v1/receptions/bills (NO /v2 — ese endpoint responde
    500 "Ha ocurrido un error inesperado" en este sandbox) con filtros
    filter[cufe], filter[company_nit], filter[company_name], filter[number],
    filter[issue_date], filter[completed_events] (1 = sin eventos RADIAN
    pendientes, 0 = con eventos pendientes), header Authorization: Bearer.
  - Forma real de la respuesta: {"status": "OK", "message": "...",
    "data": {"data": [ {...factura...} ], "pagination": {...}}} — la lista
    de facturas va anidada en data.data, no en data directamente.
  - Campos confirmados en cada factura: id, number, issue_date, issue_time,
    cufe, company_nit, company_name, payment_details, total, created_at.
    completed_events no apareció en la muestra real (queda None/sin filtrar
    cuando falta).
  - CONFIRMADO (2026-07-15): ni el listado ni el detalle traen el XML/PDF del
    documento, y no existe un endpoint de descarga para el módulo de
    recepción — se probaron GET /v1/receptions/bills/{id} (200, solo
    metadata: fecha, forma de pago, eventos RADIAN) y variantes
    /{id}/download, /download-pdf/{id} (ambas 500). Aunque Factus no exige
    captcha como el portal de la DIAN, tampoco expone el archivo por API:
    igual que con la DIAN, alguien tiene que conseguir el PDF/XML por fuera
    (el emisor, o el propio portal de la DIAN) y subirlo a NOVA a mano.
  - La URL base de producción (api.factus.com.co, sin "sandbox") sigue sin
    confirmar — se usa por inferencia del patrón de nombres.

`datos_crudos` en cada `DocumentoRecibidoPst` conserva el JSON tal cual llegó
para no perder nada si el mapeo de campos de abajo resulta incompleto.
"""
from datetime import datetime, timedelta

import httpx

from app.services.pst.base import (
    ConectorPST,
    DocumentoRecibidoPst,
    ErrorConectorPst,
    FiltrosDocumentosRecibidos,
)

FACTUS_BASE_URL_SANDBOX = "https://api-sandbox.factus.com.co"
FACTUS_BASE_URL_PRODUCCION = "https://api.factus.com.co"  # sin confirmar


class FactusConectorPST(ConectorPST):
    def __init__(self, credenciales: dict):
        self.client_id = credenciales.get("client_id")
        self.client_secret = credenciales.get("client_secret")
        self.username = credenciales.get("username")
        self.password = credenciales.get("password")
        self.base_url = (
            FACTUS_BASE_URL_PRODUCCION if credenciales.get("entorno") == "produccion" else FACTUS_BASE_URL_SANDBOX
        )

        if not all([self.client_id, self.client_secret, self.username, self.password]):
            raise ErrorConectorPst(
                "Configuración de Factus incompleta: se requieren client_id, client_secret, username y password."
            )

        self._token: str | None = None
        self._token_expira_en: datetime | None = None

    async def _obtener_token(self, client: httpx.AsyncClient) -> str:
        if self._token and self._token_expira_en and datetime.utcnow() < self._token_expira_en:
            return self._token

        respuesta = await client.post(
            f"{self.base_url}/oauth/token",
            headers={"Accept": "application/json"},
            data={
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password,
            },
        )
        if respuesta.status_code != 200:
            raise ErrorConectorPst(
                f"Autenticación con Factus falló (status {respuesta.status_code}): {respuesta.text[:300]}"
            )

        cuerpo = respuesta.json()
        token = cuerpo.get("access_token")
        if not token:
            raise ErrorConectorPst("Factus no devolvió access_token en la respuesta de autenticación.")

        expira_en_segundos = cuerpo.get("expires_in", 600)
        # Margen de 60s para renovar antes de que el token expire realmente.
        self._token = token
        self._token_expira_en = datetime.utcnow() + timedelta(seconds=max(expira_en_segundos - 60, 0))
        return token

    def _mapear_factura(self, item: dict) -> DocumentoRecibidoPst:
        completed_events = item.get("completed_events")
        return DocumentoRecibidoPst(
            cufe=item.get("cufe") or item.get("unique_code") or "",
            nit_emisor=item.get("company_nit") or (item.get("company") or {}).get("nit"),
            razon_social_emisor=item.get("company_name") or (item.get("company") or {}).get("name"),
            numero_documento=item.get("number"),
            fecha_emision=item.get("issue_date") or item.get("date"),
            tiene_eventos_pendientes=(not bool(completed_events)) if completed_events is not None else None,
            datos_crudos=item,
        )

    async def listar_recibidos(self, filtros: FiltrosDocumentosRecibidos) -> list[DocumentoRecibidoPst]:
        params = {}
        if filtros.cufe:
            params["filter[cufe]"] = filtros.cufe
        if filtros.nit_emisor:
            params["filter[company_nit]"] = filtros.nit_emisor
        if filtros.fecha_emision:
            params["filter[issue_date]"] = filtros.fecha_emision
        if filtros.solo_con_eventos_pendientes is not None:
            params["filter[completed_events]"] = "0" if filtros.solo_con_eventos_pendientes else "1"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._obtener_token(client)
                respuesta = await client.get(
                    f"{self.base_url}/v1/receptions/bills",
                    params=params,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            raise ErrorConectorPst(f"Error de red hacia Factus: {exc}") from exc

        if respuesta.status_code != 200:
            raise ErrorConectorPst(f"Factus respondió {respuesta.status_code}: {respuesta.text[:500]}")

        cuerpo = respuesta.json()
        # No usar "cuerpo.get('data') or {}": si el nivel externo ya trae la
        # lista vacía (0 resultados representados como "data": [] en vez del
        # anidamiento data.data), "or {}" lo trata como ausente y lanza el
        # error de "forma inesperada" en vez de devolver una lista vacía.
        nivel_externo = cuerpo.get("data") if isinstance(cuerpo, dict) else None
        items = nivel_externo.get("data") if isinstance(nivel_externo, dict) else nivel_externo
        if not isinstance(items, list):
            raise ErrorConectorPst(
                "La respuesta de Factus no tiene la forma esperada (se esperaba una lista en 'data.data'); "
                "revisar _mapear_factura contra la respuesta real."
            )
        return [self._mapear_factura(item) for item in items]

    async def probar_conexion(self) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await self._obtener_token(client)
