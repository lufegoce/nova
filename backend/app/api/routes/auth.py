"""
Autenticación de NOVA: dos flujos de login (contador y usuario de empresa)
que emiten la misma cookie de sesión httpOnly, y la gestión de la empresa
activa para el contador (que puede administrar varias empresas).

TODO 2FA: insertar aquí un paso intermedio (código OTP) antes de emitir el
JWT final; la cookie httpOnly + JWT de vida corta ya están pensados para
soportar ese flujo sin rediseñar el resto de la app.
"""
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_sesion
from app.core.config import get_settings
from app.core.security import crear_token_sesion, hash_password, verificar_password
from app.db.session import get_db
from app.models.usuario import Contador, Empresa, RolUsuarioEmpresa, UsuarioEmpresa
from app.schemas.auth import (
    CrearUsuarioEmpresaRequest,
    EmpresaActualOut,
    EmpresaOut,
    LoginContadorRequest,
    LoginEmpresaRequest,
    MeOut,
    RutExtraidoOut,
    UsuarioEmpresaOut,
)
from app.services.rut_extractor import extraer_datos_rut

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

_DIRECTORIO_RUTS = "storage/ruts"


def _guardar_rut(empresa_id: uuid.UUID, contenido: bytes) -> str:
    from pathlib import Path

    directorio = Path(_DIRECTORIO_RUTS)
    directorio.mkdir(parents=True, exist_ok=True)
    ruta_relativa = f"{_DIRECTORIO_RUTS}/{empresa_id}.pdf"
    Path(ruta_relativa).write_bytes(contenido)
    return ruta_relativa


def _set_cookie_sesion(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_SESION,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=settings.JWT_EXPIRA_MINUTOS * 60,
        path="/",
    )


@router.post("/login/contador", response_model=MeOut)
async def login_contador(datos: LoginContadorRequest, response: Response, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Contador).where(Contador.email == datos.email))
    contador = resultado.scalar_one_or_none()
    if not contador or not contador.activo or not verificar_password(datos.password, contador.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    claims = {"rol": "contador", "sub": str(contador.id), "nombre": contador.nombre, "email": contador.email}

    # Si ya administra alguna empresa, se selecciona la primera automáticamente
    # para no obligarlo a elegir en cada login; puede cambiarla luego desde el
    # selector de la barra superior (POST /auth/empresas/{id}/seleccionar).
    resultado = await db.execute(
        select(Empresa).where(Empresa.contador_id == contador.id, Empresa.activo.is_(True)).order_by(Empresa.nombre)
    )
    empresa_por_defecto = resultado.scalars().first()

    empresa_actual = None
    if empresa_por_defecto is not None:
        claims.update(
            {
                "empresa_id": str(empresa_por_defecto.id),
                "empresa_nombre": empresa_por_defecto.nombre,
                "tenant_id": empresa_por_defecto.tenant_id,
            }
        )
        empresa_actual = EmpresaActualOut(
            id=empresa_por_defecto.id, nombre=empresa_por_defecto.nombre, tenant_id=empresa_por_defecto.tenant_id
        )

    token = crear_token_sesion(claims)
    _set_cookie_sesion(response, token)
    return MeOut(rol="contador", nombre=contador.nombre, email=contador.email, empresa_actual=empresa_actual)


@router.post("/login/empresa", response_model=MeOut)
async def login_empresa(datos: LoginEmpresaRequest, response: Response, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(UsuarioEmpresa).where(UsuarioEmpresa.email == datos.email))
    usuario = resultado.scalar_one_or_none()
    if not usuario or not usuario.activo or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    empresa = await db.get(Empresa, usuario.empresa_id)
    if not empresa or not empresa.activo:
        raise HTTPException(status_code=403, detail="La empresa asociada está inactiva")

    token = crear_token_sesion(
        {
            "rol": "empresa",
            "sub": str(usuario.id),
            "nombre": usuario.nombre,
            "email": usuario.email,
            "rol_empresa": usuario.rol.value,
            "empresa_id": str(empresa.id),
            "empresa_nombre": empresa.nombre,
            "tenant_id": empresa.tenant_id,
        }
    )
    _set_cookie_sesion(response, token)
    return MeOut(
        rol="empresa",
        nombre=usuario.nombre,
        email=usuario.email,
        rol_empresa=usuario.rol.value,
        empresa_actual=EmpresaActualOut(id=empresa.id, nombre=empresa.nombre, tenant_id=empresa.tenant_id),
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(settings.COOKIE_SESION, path="/")
    return {"status": "ok"}


@router.get("/me", response_model=MeOut)
async def me(sesion: dict[str, Any] = Depends(get_sesion)):
    empresa_actual = None
    if sesion.get("tenant_id"):
        empresa_actual = EmpresaActualOut(
            id=uuid.UUID(sesion["empresa_id"]), nombre=sesion["empresa_nombre"], tenant_id=sesion["tenant_id"]
        )
    return MeOut(
        rol=sesion["rol"],
        nombre=sesion["nombre"],
        email=sesion["email"],
        rol_empresa=sesion.get("rol_empresa"),
        empresa_actual=empresa_actual,
    )


def _requerir_contador(sesion: dict[str, Any]) -> uuid.UUID:
    if sesion.get("rol") != "contador":
        raise HTTPException(status_code=403, detail="Solo un contador puede realizar esta acción")
    return uuid.UUID(sesion["sub"])


@router.get("/empresas", response_model=list[EmpresaOut])
async def listar_empresas(sesion: dict[str, Any] = Depends(get_sesion), db: AsyncSession = Depends(get_db)):
    contador_id = _requerir_contador(sesion)
    resultado = await db.execute(
        select(Empresa).where(Empresa.contador_id == contador_id, Empresa.activo.is_(True)).order_by(Empresa.nombre)
    )
    return resultado.scalars().all()


@router.post("/empresas/extraer-rut", response_model=RutExtraidoOut)
async def extraer_rut(
    archivo: UploadFile = File(...),
    sesion: dict[str, Any] = Depends(get_sesion),
):
    """
    Propuesta de datos leída del RUT con IA (ver app/services/rut_extractor.py).
    No crea ni modifica nada: el contador revisa/corrige esto en el formulario
    de creación de empresa antes de enviarlo a POST /auth/empresas.
    """
    _requerir_contador(sesion)
    if archivo.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=422, detail="El RUT debe subirse en PDF")

    contenido = await archivo.read()
    return extraer_datos_rut(contenido)


@router.post("/empresas", response_model=EmpresaOut, status_code=201)
async def crear_empresa(
    nombre: str = Form(...),
    nit: str | None = Form(None),
    digito_verificacion: str | None = Form(None),
    tipo_persona: str | None = Form(None),
    responsabilidades_tributarias: str | None = Form(None),  # JSON: [{"codigo","descripcion"}]
    actividad_economica_codigo: str | None = Form(None),
    actividad_economica_descripcion: str | None = Form(None),
    direccion: str | None = Form(None),
    departamento: str | None = Form(None),
    municipio: str | None = Form(None),
    correo_electronico: str | None = Form(None),
    telefono: str | None = Form(None),
    representante_legal_nombre: str | None = Form(None),
    representante_legal_identificacion: str | None = Form(None),
    estado_rut: str | None = Form(None),
    archivo_rut: UploadFile | None = File(None),
    sesion: dict[str, Any] = Depends(get_sesion),
    db: AsyncSession = Depends(get_db),
):
    contador_id = _requerir_contador(sesion)

    responsabilidades = None
    if responsabilidades_tributarias:
        try:
            responsabilidades = json.loads(responsabilidades_tributarias)
        except json.JSONDecodeError:
            raise HTTPException(status_code=422, detail="responsabilidades_tributarias debe ser JSON válido")

    empresa = Empresa(
        contador_id=contador_id,
        nombre=nombre,
        nit=nit,
        tenant_id=f"emp-{uuid.uuid4().hex[:12]}",
        digito_verificacion=digito_verificacion,
        tipo_persona=tipo_persona,
        responsabilidades_tributarias=responsabilidades,
        actividad_economica_codigo=actividad_economica_codigo,
        actividad_economica_descripcion=actividad_economica_descripcion,
        direccion=direccion,
        departamento=departamento,
        municipio=municipio,
        correo_electronico=correo_electronico,
        telefono=telefono,
        representante_legal_nombre=representante_legal_nombre,
        representante_legal_identificacion=representante_legal_identificacion,
        estado_rut=estado_rut,
    )
    db.add(empresa)
    await db.flush()

    if archivo_rut is not None:
        contenido = await archivo_rut.read()
        empresa.ruta_rut = _guardar_rut(empresa.id, contenido)

    await db.commit()
    await db.refresh(empresa)
    return empresa


def _requerir_administrador_o_contador(sesion: dict[str, Any]) -> None:
    if sesion.get("rol") == "contador":
        return
    if sesion.get("rol") == "empresa" and sesion.get("rol_empresa") == RolUsuarioEmpresa.ADMINISTRADOR.value:
        return
    raise HTTPException(status_code=403, detail="No tienes permisos para gestionar usuarios de esta empresa")


@router.get("/empresas/{empresa_id}/usuarios", response_model=list[UsuarioEmpresaOut])
async def listar_usuarios_empresa(
    empresa_id: uuid.UUID,
    sesion: dict[str, Any] = Depends(get_sesion),
    db: AsyncSession = Depends(get_db),
):
    _requerir_administrador_o_contador(sesion)
    if sesion.get("rol") == "contador":
        empresa = await db.get(Empresa, empresa_id)
        if not empresa or empresa.contador_id != uuid.UUID(sesion["sub"]):
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
    elif sesion.get("empresa_id") != str(empresa_id):
        raise HTTPException(status_code=403, detail="No puedes ver usuarios de otra empresa")

    resultado = await db.execute(
        select(UsuarioEmpresa).where(UsuarioEmpresa.empresa_id == empresa_id).order_by(UsuarioEmpresa.nombre)
    )
    return resultado.scalars().all()


@router.post("/empresas/{empresa_id}/usuarios", response_model=UsuarioEmpresaOut, status_code=201)
async def crear_usuario_empresa(
    empresa_id: uuid.UUID,
    datos: CrearUsuarioEmpresaRequest,
    sesion: dict[str, Any] = Depends(get_sesion),
    db: AsyncSession = Depends(get_db),
):
    _requerir_administrador_o_contador(sesion)
    if sesion.get("rol") == "contador":
        empresa = await db.get(Empresa, empresa_id)
        if not empresa or empresa.contador_id != uuid.UUID(sesion["sub"]):
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
    elif sesion.get("empresa_id") != str(empresa_id):
        raise HTTPException(status_code=403, detail="No puedes crear usuarios para otra empresa")

    try:
        rol = RolUsuarioEmpresa(datos.rol)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Rol inválido. Usa uno de: {[r.value for r in RolUsuarioEmpresa]}"
        )

    usuario = UsuarioEmpresa(
        empresa_id=empresa_id,
        email=datos.email,
        password_hash=hash_password(datos.password),
        nombre=datos.nombre,
        telefono=datos.telefono,
        rol=rol,
    )
    db.add(usuario)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email") from exc
    await db.refresh(usuario)
    return usuario


@router.post("/empresas/{empresa_id}/seleccionar", response_model=MeOut)
async def seleccionar_empresa(
    empresa_id: uuid.UUID,
    response: Response,
    sesion: dict[str, Any] = Depends(get_sesion),
    db: AsyncSession = Depends(get_db),
):
    contador_id = _requerir_contador(sesion)
    empresa = await db.get(Empresa, empresa_id)
    if not empresa or empresa.contador_id != contador_id or not empresa.activo:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    token = crear_token_sesion(
        {
            "rol": "contador",
            "sub": str(contador_id),
            "nombre": sesion["nombre"],
            "email": sesion["email"],
            "empresa_id": str(empresa.id),
            "empresa_nombre": empresa.nombre,
            "tenant_id": empresa.tenant_id,
        }
    )
    _set_cookie_sesion(response, token)
    return MeOut(
        rol="contador",
        nombre=sesion["nombre"],
        email=sesion["email"],
        empresa_actual=EmpresaActualOut(id=empresa.id, nombre=empresa.nombre, tenant_id=empresa.tenant_id),
    )
