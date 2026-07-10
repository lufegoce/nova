"""
Dependencias comunes de la API: resolución de tenant y sesión de BD.

Multi-tenancy: todo request debe traer X-Tenant-Id. En este MVP no se valida
contra una tabla de tenants (se asume confianza del gateway/API key); en
producción esto debe resolverse desde el JWT/API key, no desde un header libre.
"""
import re

from fastapi import Header, HTTPException

# tenant_id se usa para construir rutas de archivo (ver app/services/pdf_storage.py),
# así que se restringe a un formato seguro para evitar path traversal (ej. "../../etc").
_PATRON_TENANT_ID_VALIDO = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


async def get_tenant_id(x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id")) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Falta el header X-Tenant-Id")
    if not _PATRON_TENANT_ID_VALIDO.match(x_tenant_id):
        raise HTTPException(
            status_code=400,
            detail="X-Tenant-Id inválido: solo se permiten letras, números, guiones y guion bajo (máx. 64 caracteres)",
        )
    return x_tenant_id
