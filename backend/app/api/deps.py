"""
Dependencias comunes de la API: resolución de tenant y sesión de BD.

Multi-tenancy: todo request debe traer X-Tenant-Id. En este MVP no se valida
contra una tabla de tenants (se asume confianza del gateway/API key); en
producción esto debe resolverse desde el JWT/API key, no desde un header libre.
"""
from fastapi import Header, HTTPException


async def get_tenant_id(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Falta el header X-Tenant-Id")
    return x_tenant_id
