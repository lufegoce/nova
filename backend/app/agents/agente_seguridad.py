"""
Agente de Seguridad: vigila el registro de auditoría (EventoAuditoria) en
busca de patrones anómalos y genera AlertaSeguridad. Es el punto de apoyo
del pilar "Zero Trust" del diseño de NOVA — no reemplaza controles de
infraestructura (firewall, WAF, gestión de secretos), sino que da visibilidad
sobre comportamientos sospechosos en la capa de negocio, sobre datos que el
resto de agentes ya audita.

Reglas implementadas (deliberadamente simples, basadas en umbrales — no ML):
  A. Aprobaciones rápidas: un mismo usuario aprueba varios documentos en muy
     poco tiempo (posible aprobación sin revisión real).
  B. Pago de alto valor aprobado casi inmediatamente tras la ingesta (posible
     bypass del flujo de revisión).
  C. Fallos repetidos de sincronización con el ERP (posible credencial
     revocada/comprometida, o intento de exfiltración fallido).
  D. Correcciones de cuenta PUC inestables para el mismo NIT (posible
     manipulación de las reglas aprendidas del Agente Contable).

Cada regla es independiente y fácil de ajustar/agregar: no dependen entre sí.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.models.documento import DocumentoFinanciero, EventoAuditoria
from app.models.seguridad import AlertaSeguridad, SeveridadAlerta

UMBRAL_APROBACIONES_RAPIDAS = 3  # aprobaciones del mismo usuario
VENTANA_APROBACIONES_RAPIDAS = timedelta(minutes=5)

UMBRAL_VALOR_ALTO = 5_000_000.0  # COP
VENTANA_INGESTA_A_PAGO_SOSPECHOSA = timedelta(minutes=2)

UMBRAL_FALLOS_ERP = 3
VENTANA_FALLOS_ERP = timedelta(hours=1)

UMBRAL_CORRECCIONES_PUC = 3
VENTANA_CORRECCIONES_PUC = timedelta(hours=24)

VENTANA_ESCANEO_POR_DEFECTO = timedelta(hours=24)


class AgenteSeguridad:
    nombre = "agente_seguridad"

    def __init__(self, db, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def _crear_alerta_si_no_existe(
        self,
        tipo: str,
        severidad: SeveridadAlerta,
        detalle: str,
        contexto: dict,
        documento_id: UUID | None = None,
    ) -> bool:
        """Evita duplicar la misma alerta sin resolver. Retorna True si creó una nueva."""
        result = await self.db.execute(
            select(AlertaSeguridad).where(
                AlertaSeguridad.tenant_id == self.tenant_id,
                AlertaSeguridad.tipo == tipo,
                AlertaSeguridad.documento_id == documento_id,
                AlertaSeguridad.resuelta.is_(False),
            )
        )
        if result.scalar_one_or_none() is not None:
            return False

        self.db.add(
            AlertaSeguridad(
                tenant_id=self.tenant_id,
                tipo=tipo,
                severidad=severidad,
                detalle=detalle,
                contexto=contexto,
                documento_id=documento_id,
            )
        )
        return True

    async def _eventos_recientes(self, desde: datetime, accion: str | None = None) -> list[EventoAuditoria]:
        condiciones = [EventoAuditoria.tenant_id == self.tenant_id, EventoAuditoria.creado_en >= desde]
        if accion:
            condiciones.append(EventoAuditoria.accion == accion)
        result = await self.db.execute(select(EventoAuditoria).where(*condiciones))
        return list(result.scalars().all())

    async def _regla_aprobaciones_rapidas(self, desde: datetime) -> int:
        eventos = await self._eventos_recientes(desde, accion="pago_ejecutado")
        por_usuario: dict[str, list[datetime]] = defaultdict(list)

        for evento in eventos:
            usuario = (evento.detalle or "").replace("Aprobado por ", "").strip()
            if usuario:
                por_usuario[usuario].append(evento.creado_en)

        creadas = 0
        for usuario, marcas in por_usuario.items():
            marcas.sort()
            for i in range(len(marcas) - UMBRAL_APROBACIONES_RAPIDAS + 1):
                ventana = marcas[i : i + UMBRAL_APROBACIONES_RAPIDAS]
                if ventana[-1] - ventana[0] <= VENTANA_APROBACIONES_RAPIDAS:
                    creada = await self._crear_alerta_si_no_existe(
                        tipo="aprobaciones_rapidas",
                        severidad=SeveridadAlerta.MEDIA,
                        detalle=(
                            f"{usuario} aprobó {UMBRAL_APROBACIONES_RAPIDAS} o más documentos en menos de "
                            f"{int(VENTANA_APROBACIONES_RAPIDAS.total_seconds() // 60)} minutos."
                        ),
                        contexto={"usuario": usuario, "cantidad": len(ventana)},
                    )
                    creadas += int(creada)
                    break  # una alerta por usuario por escaneo es suficiente

        return creadas

    async def _regla_pago_rapido_alto_valor(self, desde: datetime) -> int:
        eventos = await self._eventos_recientes(desde, accion="pago_ejecutado")
        creadas = 0

        for evento in eventos:
            documento = await self.db.get(DocumentoFinanciero, evento.documento_id)
            if documento is None or float(documento.total) < UMBRAL_VALOR_ALTO:
                continue

            tiempo_hasta_pago = evento.creado_en - documento.creado_en
            if tiempo_hasta_pago <= VENTANA_INGESTA_A_PAGO_SOSPECHOSA:
                creada = await self._crear_alerta_si_no_existe(
                    tipo="pago_rapido_alto_valor",
                    severidad=SeveridadAlerta.ALTA,
                    detalle=(
                        f"Factura {documento.numero_factura or documento.id} por "
                        f"${float(documento.total):,.0f} fue aprobada y pagada "
                        f"{int(tiempo_hasta_pago.total_seconds())}s después de ingresar — "
                        "revisar que hubo revisión humana real."
                    ),
                    contexto={"total": float(documento.total), "segundos_hasta_pago": tiempo_hasta_pago.total_seconds()},
                    documento_id=documento.id,
                )
                creadas += int(creada)

        return creadas

    async def _regla_fallos_erp_repetidos(self, desde: datetime) -> int:
        eventos = await self._eventos_recientes(desde, accion="sincronizacion_erp")
        fallos = [e for e in eventos if (e.resultado or {}).get("erp_estado") == "error"]

        if len(fallos) >= UMBRAL_FALLOS_ERP:
            creada = await self._crear_alerta_si_no_existe(
                tipo="fallos_erp_repetidos",
                severidad=SeveridadAlerta.ALTA,
                detalle=(
                    f"{len(fallos)} sincronizaciones con el ERP fallaron en las últimas "
                    f"{int(VENTANA_FALLOS_ERP.total_seconds() // 3600)} horas — "
                    "posible credencial inválida o revocada."
                ),
                contexto={"cantidad_fallos": len(fallos)},
            )
            return int(creada)

        return 0

    async def _regla_correcciones_puc_inestables(self, desde: datetime) -> int:
        eventos = await self._eventos_recientes(desde, accion="correccion_humana_cuenta_puc")
        por_nit: dict[str, set[str]] = defaultdict(set)

        for evento in eventos:
            documento = await self.db.get(DocumentoFinanciero, evento.documento_id)
            if documento is None:
                continue
            cuenta_nueva = (evento.resultado or {}).get("cuenta_nueva")
            if cuenta_nueva:
                por_nit[documento.nit_emisor].add(cuenta_nueva)

        creadas = 0
        for nit, cuentas in por_nit.items():
            if len(cuentas) >= UMBRAL_CORRECCIONES_PUC:
                creada = await self._crear_alerta_si_no_existe(
                    tipo="correcciones_puc_inestables",
                    severidad=SeveridadAlerta.MEDIA,
                    detalle=(
                        f"El NIT {nit} recibió {len(cuentas)} cuentas PUC distintas por corrección humana "
                        f"en las últimas {int(VENTANA_CORRECCIONES_PUC.total_seconds() // 3600)} horas."
                    ),
                    contexto={"nit_emisor": nit, "cuentas": list(cuentas)},
                )
                creadas += int(creada)

        return creadas

    async def ejecutar_escaneo(self, ventana: timedelta = VENTANA_ESCANEO_POR_DEFECTO) -> dict:
        desde = datetime.utcnow() - ventana

        resultado = {
            "aprobaciones_rapidas": await self._regla_aprobaciones_rapidas(desde),
            "pago_rapido_alto_valor": await self._regla_pago_rapido_alto_valor(desde),
            "fallos_erp_repetidos": await self._regla_fallos_erp_repetidos(desde),
            "correcciones_puc_inestables": await self._regla_correcciones_puc_inestables(desde),
        }

        await self.db.commit()
        resultado["total_alertas_nuevas"] = sum(resultado.values())
        return resultado
