"""
Conector para SIIGO API (Siigo Nube), uno de los ERPs contables más usados
por contadores y pymes en Colombia.

⚠️ ESTADO: NO VERIFICADO CONTRA UNA CUENTA REAL. A diferencia del conector de
la DIAN (que sí se probó contra el portal de producción), este conector se
construyó siguiendo la documentación pública de SIIGO API de memoria, sin una
cuenta de prueba disponible en este momento. Antes de usarlo contra datos
reales, hay que validar con una cuenta sandbox/real:
  1. Que el endpoint y el formato exacto de /v1/purchases sean correctos.
  2. Que "cuenta_puc" pueda enviarse tal cual, o si SIIGO requiere mapear
     primero la cuenta PUC a un `product`/`account_group` propio de SIIGO
     (su API suele modelar los ítems de compra contra un catálogo de
     productos/servicios de la cuenta SIIGO, no contra códigos PUC libres).
  3. Que el `document.id` (tipo de comprobante) y el `cost_center` por
     defecto que se usan aquí existan en la cuenta del cliente.

Lo que SÍ está documentado de forma estable en la API pública de SIIGO:
  - Autenticación: POST /auth con {username, access_key} -> {access_token}.
  - Todas las peticiones subsiguientes requieren los headers
    `Authorization: Bearer <token>` y `Partner-Id: <partner_id>` (el Partner-Id
    lo asigna SIIGO al registrar la integración como partner tecnológico).
"""
from datetime import datetime

import httpx

from app.services.erp.base import (
    ConectorERP,
    DocumentoParaErp,
    ErrorConectorErp,
    ResultadoEnvioErp,
)

SIIGO_BASE_URL = "https://api.siigo.com"


class SiigoConectorERP(ConectorERP):
    def __init__(self, credenciales: dict):
        self.username = credenciales.get("username")
        self.access_key = credenciales.get("access_key")
        self.partner_id = credenciales.get("partner_id")
        self.document_id_compra = credenciales.get("document_id_compra")  # tipo de comprobante en SIIGO
        self.cost_center = credenciales.get("cost_center")

        if not all([self.username, self.access_key, self.partner_id]):
            raise ErrorConectorErp(
                "Configuración SIIGO incompleta: se requieren username, access_key y partner_id."
            )

    async def _autenticar(self, client: httpx.AsyncClient) -> str:
        respuesta = await client.post(
            f"{SIIGO_BASE_URL}/auth",
            json={"username": self.username, "access_key": self.access_key},
        )
        if respuesta.status_code != 200:
            raise ErrorConectorErp(
                f"Autenticación con SIIGO falló (status {respuesta.status_code}): {respuesta.text[:300]}"
            )
        token = respuesta.json().get("access_token")
        if not token:
            raise ErrorConectorErp("SIIGO no devolvió access_token en la respuesta de autenticación.")
        return token

    async def enviar_causacion(self, documento: DocumentoParaErp) -> ResultadoEnvioErp:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                token = await self._autenticar(client)

                headers = {
                    "Authorization": f"Bearer {token}",
                    "Partner-Id": self.partner_id,
                    "Content-Type": "application/json",
                }

                fecha = documento.fecha_emision or datetime.utcnow().date().isoformat()

                # TODO (sin verificar): estructura de payload de /v1/purchases.
                payload = {
                    "document": {"id": self.document_id_compra},
                    "date": fecha,
                    "supplier": {"identification": documento.nit_emisor},
                    "cost_center": self.cost_center,
                    "observations": f"Causado automáticamente por NOVA — factura {documento.numero_factura or documento.documento_id}",
                    "items": [
                        {
                            "description": documento.razon_social_emisor or "Compra",
                            "account_code": documento.cuenta_puc,
                            "quantity": 1,
                            "price": documento.total,
                        }
                    ],
                    "payments": [],
                }

                respuesta = await client.post(
                    f"{SIIGO_BASE_URL}/v1/purchases", json=payload, headers=headers
                )

                if respuesta.status_code not in (200, 201):
                    return ResultadoEnvioErp(
                        exitoso=False,
                        detalle_error=f"SIIGO respondió {respuesta.status_code}: {respuesta.text[:500]}",
                    )

                cuerpo = respuesta.json()
                referencia = str(cuerpo.get("id") or cuerpo.get("number") or "")
                return ResultadoEnvioErp(exitoso=True, referencia_erp=referencia)

        except ErrorConectorErp as exc:
            return ResultadoEnvioErp(exitoso=False, detalle_error=str(exc))
        except httpx.HTTPError as exc:
            return ResultadoEnvioErp(exitoso=False, detalle_error=f"Error de red hacia SIIGO: {exc}")
