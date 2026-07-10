"""
Canal WebSocket que notifica al Command Center cuando el worker DIAN
(ver app/workers/tasks.py) detecta una factura nueva.

Gestión de conexiones simplificada en memoria (suficiente para el MVP de un
solo proceso; para escalado horizontal real, respaldar con Redis Pub/Sub).
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.conexiones_activas: dict[str, list[WebSocket]] = {}

    async def conectar(self, tenant_id: str, websocket: WebSocket):
        await websocket.accept()
        self.conexiones_activas.setdefault(tenant_id, []).append(websocket)

    def desconectar(self, tenant_id: str, websocket: WebSocket):
        if tenant_id in self.conexiones_activas:
            self.conexiones_activas[tenant_id].remove(websocket)

    async def notificar_tenant(self, tenant_id: str, mensaje: dict):
        for ws in self.conexiones_activas.get(tenant_id, []):
            await ws.send_text(json.dumps(mensaje))


manager = ConnectionManager()


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    await manager.conectar(tenant_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # mantiene viva la conexión (ping/pong del cliente)
    except WebSocketDisconnect:
        manager.desconectar(tenant_id, websocket)
