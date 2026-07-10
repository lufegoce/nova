# NOVA — Plataforma de Agentes Autónomos para Automatización Financiera y Contable

MVP del ecosistema de agentes de IA descrito en el diseño de arquitectura: Orquestador +
Agente Receptor, Agente Contable, Agente Conciliador, Agente Pagador y Agente Reportero.

## Estructura

```
backend/    FastAPI + SQLAlchemy async + Celery (orquestador y agentes)
frontend/   Next.js 14 (App Router) + Tailwind — Command Center
docker-compose.yml
.env.example
```

## Levantar el entorno local

```bash
cp .env.example .env
# (opcional) completar ANTHROPIC_API_KEY en .env para clasificación real con Claude
docker compose up --build
```

- API: http://localhost:8000 — documentación Swagger en http://localhost:8000/docs
- Frontend (Command Center): http://localhost:3000
- Worker Celery: procesa tareas asíncronas (fin de mes, lotes de facturas)
- Celery Beat: consulta el conector DIAN simulado cada 5 minutos y notifica por WebSocket

## Flujo de la demo

1. Abrir el Command Center en http://localhost:3000.
2. **Vincular sesión DIAN** (panel "Documentos recibidos — DIAN"): pega el magic-link
   que llega al correo desde `catalogo-vpfe.dian.gov.co`. NOVA lo sigue, captura la
   cookie de sesión y a partir de ahí lista automáticamente los documentos recibidos
   (`POST /Document/GetDocumentsPageToken`, ver `app/services/dian_portal_connector.py`).
3. La **descarga del PDF no se automatiza**: el portal exige resolver un captcha de
   Cloudflare Turnstile por cada documento, así que el usuario hace clic en el ícono
   de enlace externo, lo descarga él mismo desde el portal real, y luego usa
   **"Subir PDF"** en la fila correspondiente (o el botón "Subir factura en PDF" del
   header para una carga suelta) para que el Agente Receptor la procese.
4. Al subir el PDF se confirman NIT, total y demás campos clave (la extracción
   automática de un PDF arbitrario no es confiable sin OCR dedicado); el Agente
   Contable sigue el mismo flujo de siempre (cuenta PUC + retenciones).
5. Si la factura queda en estado "Pendiente aprobación", hacer clic en "Revisar" para
   abrir el modal human-in-the-loop y aprobar o rechazar el pago. El PDF queda
   disponible para previsualizar con "Ver PDF" en la tabla de documentos.
6. Preguntar en el chat de trazabilidad, por ejemplo: *"¿por qué no se ha pagado la
   factura FE-1002?"* — reconstruye la cadena de eventos de auditoría.
7. Aparte, Celery Beat simula cada 5 minutos una consulta a la DIAN vía CSV mock
   (`backend/app/services/dian_mock_facturas.csv`) y notifica nuevas facturas en vivo
   por WebSocket — esto es un canal simulado independiente, no reemplaza el flujo real
   del punto 2.

## Pruebas

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```

Las pruebas cubren el cálculo de ReteFuente y ReteICA (`app/services/retenciones.py`),
la función más sensible desde el punto de vista fiscal.

## Notas de arquitectura

- **Multi-tenancy**: en este MVP se usa una columna `tenant_id` (row-level) resuelta
  desde el header `X-Tenant-Id`. Para aislamiento físico por cliente, cambiar la
  estrategia en `app/db/session.py` y `app/api/deps.py`.
- **Trazabilidad**: cada acción de un agente se registra en `EventoAuditoria`
  (tabla append-only), base del chat inteligente y de cualquier auditoría posterior.
- **Human-in-the-loop**: el Agente Pagador (`app/agents/agente_pagador.py`) nunca
  transiciona un documento a `pagado` sin un evento de aprobación humana previo.
- **Escalabilidad**: los agentes son stateless (`app/agents/base.py`); todo el estado
  vive en Postgres, lo que permite escalar el backend y los workers de Celery
  horizontalmente en picos de fin de mes.
- **DIAN — catálogo real vs. simulado**: hay dos integraciones DIAN distintas en el
  código, no confundirlas.
  - `app/services/dian_portal_connector.py` es la integración **real** contra el
    Catálogo de Visualización de Documentos (`catalogo-vpfe.dian.gov.co`), verificada
    manualmente contra producción. El listado es 100% automático; la descarga NO se
    automatiza a propósito porque el portal exige un captcha de Cloudflare Turnstile
    por documento — evadirlo programáticamente no es algo que este proyecto haga,
    aunque sea la propia cuenta del tenant, porque es el control anti-bot que la DIAN
    puso ahí deliberadamente. El esquema exacto del JSON de respuesta de
    `GetDocumentsPageToken` está marcado como TODO en el código: se infirió de los
    nombres usados en el JavaScript del portal, no se confirmó con una respuesta real.
  - `app/services/dian_connector.py` + `dian_mock_facturas.csv` es un conector
    **simulado** e independiente, usado solo para demostrar el patrón de notificación
    periódica por Celery Beat + WebSocket.
  - La cookie de sesión (`SesionDian.cookies`) se guarda en texto plano en Postgres
    en este MVP. Para producción debe cifrarse en reposo (KMS/HSM) — es un secreto
    real de la cuenta DIAN del tenant.
- **Bancos**: `_ejecutar_transferencia_bancaria` en `agente_pagador.py` está simulado
  en el MVP y diseñado como punto de extensión para la integración bancaria real.
