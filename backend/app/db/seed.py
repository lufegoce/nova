"""
Datos de prueba: un contador con 2 empresas, y un usuario de una de esas
empresas. Idempotente (no duplica si ya existen) para poder llamarse en cada
arranque del backend durante el MVP.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.usuario import Contador, Empresa, UsuarioEmpresa

EMAIL_CONTADOR = "contador@novacontable.co"
EMAIL_USUARIO_EMPRESA = "usuario@empresademo.co"
PASSWORD_PRUEBA = "nova1234"


async def sembrar_datos_prueba(db: AsyncSession) -> None:
    existente = await db.execute(select(Contador).where(Contador.email == EMAIL_CONTADOR))
    if existente.scalar_one_or_none():
        return

    contador = Contador(email=EMAIL_CONTADOR, password_hash=hash_password(PASSWORD_PRUEBA), nombre="Contador Demo")
    db.add(contador)
    await db.flush()

    empresa_demo = Empresa(contador_id=contador.id, nombre="Empresa Demo S.A.S.", nit="900123456", tenant_id="demo")
    empresa_dos = Empresa(contador_id=contador.id, nombre="Comercial Andina S.A.S.", nit="900654321", tenant_id="andina")
    db.add_all([empresa_demo, empresa_dos])
    await db.flush()

    usuario_empresa = UsuarioEmpresa(
        empresa_id=empresa_demo.id,
        email=EMAIL_USUARIO_EMPRESA,
        password_hash=hash_password(PASSWORD_PRUEBA),
        nombre="Usuario Empresa Demo",
    )
    db.add(usuario_empresa)
    await db.commit()
