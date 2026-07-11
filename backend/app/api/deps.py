"""
Dependencias comunes de la API: sesión autenticada y sesión de BD.

Multi-tenancy: el tenant_id ya NO se lee de un header libre (X-Tenant-Id).
Se resuelve a partir de la cookie de sesión httpOnly emitida en el login
(ver app/api/routes/auth.py y app/core/security.py):
- Usuario de empresa: el tenant_id queda fijo al que le asignó su empresa.
- Contador: el tenant_id es el de la empresa que haya seleccionado
  (POST /auth/empresas/{id}/seleccionar); si no ha seleccionado ninguna,
  cualquier endpoint que dependa de get_tenant_id responde 400.
"""
from typing import Any

from fastapi import Cookie, Depends, HTTPException

from app.core.config import get_settings
from app.core.security import TokenInvalidoError, decodificar_token_sesion

settings = get_settings()


async def get_sesion(
    nova_session: str | None = Cookie(default=None, alias="nova_session"),
) -> dict[str, Any]:
    if not nova_session:
        raise HTTPException(status_code=401, detail="No autenticado")
    try:
        return decodificar_token_sesion(nova_session)
    except TokenInvalidoError as exc:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada") from exc


async def get_tenant_id(sesion: dict[str, Any] = Depends(get_sesion)) -> str:
    tenant_id = sesion.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Selecciona una empresa antes de continuar")
    return tenant_id


def requerir_permiso_empresa(*roles_permitidos: str):
    """
    Restringe una acción a ciertos roles de UsuarioEmpresa (ver
    app/models/usuario.py::RolUsuarioEmpresa). El contador siempre pasa: es
    dueño de la empresa, no está sujeto a los roles internos de esa empresa.
    """

    async def dependencia(sesion: dict[str, Any] = Depends(get_sesion)) -> None:
        if sesion.get("rol") == "contador":
            return
        if sesion.get("rol_empresa") not in roles_permitidos:
            raise HTTPException(status_code=403, detail="Tu rol no tiene permiso para realizar esta acción")

    return dependencia
