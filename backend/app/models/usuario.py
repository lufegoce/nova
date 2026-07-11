"""
Modelo de identidad de NOVA: un Contador (firma contable, cliente de NOVA) que
administra N Empresas (tenants). Cada Empresa puede tener sus propios
UsuarioEmpresa, que solo ven la información de esa empresa.

`Empresa.tenant_id` reemplaza al header libre "X-Tenant-Id" usado antes del
sistema de autenticación: sigue siendo el mismo string usado por el resto de
la app (documentos, storage de PDFs, etc.), pero ahora se resuelve desde la
sesión autenticada (ver app/api/deps.py) en vez de confiar en un header.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Contador(Base):
    __tablename__ = "contadores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresas: Mapped[list["Empresa"]] = relationship(back_populates="contador")


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contador_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contadores.id"), index=True, nullable=False)

    # Identificador de tenant usado en el resto de la app (documentos, PDFs, etc.)
    tenant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    nit: Mapped[str] = mapped_column(String(20), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Datos extraídos del RUT (ver app/services/rut_extractor.py). Todos opcionales:
    # la empresa se puede crear solo con nombre/nit y completarse después.
    digito_verificacion: Mapped[str] = mapped_column(String(2), nullable=True)
    tipo_persona: Mapped[str] = mapped_column(String(20), nullable=True)  # "natural" | "juridica"
    responsabilidades_tributarias: Mapped[list] = mapped_column(JSONB, nullable=True)  # [{codigo, descripcion}]
    actividad_economica_codigo: Mapped[str] = mapped_column(String(10), nullable=True)
    actividad_economica_descripcion: Mapped[str] = mapped_column(String(255), nullable=True)
    direccion: Mapped[str] = mapped_column(String(255), nullable=True)
    departamento: Mapped[str] = mapped_column(String(100), nullable=True)
    municipio: Mapped[str] = mapped_column(String(100), nullable=True)
    correo_electronico: Mapped[str] = mapped_column(String(255), nullable=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=True)
    representante_legal_nombre: Mapped[str] = mapped_column(String(255), nullable=True)
    representante_legal_identificacion: Mapped[str] = mapped_column(String(20), nullable=True)
    estado_rut: Mapped[str] = mapped_column(String(30), nullable=True)
    ruta_rut: Mapped[str] = mapped_column(String(500), nullable=True)

    contador: Mapped["Contador"] = relationship(back_populates="empresas")
    usuarios: Mapped[list["UsuarioEmpresa"]] = relationship(
        back_populates="empresa", cascade="all, delete-orphan"
    )


class RolUsuarioEmpresa(str, enum.Enum):
    ADMINISTRADOR = "administrador"  # todo, incluida gestión de usuarios de su empresa
    APROBADOR = "aprobador"  # aprueba/rechaza pagos y corrige cuenta PUC
    OPERADOR = "operador"  # sube facturas, vincula DIAN; no aprueba pagos
    CONSULTA = "consulta"  # solo lectura


class UsuarioEmpresa(Base):
    """Usuario final de una empresa cliente: solo ve/opera la información de su empresa."""
    __tablename__ = "usuarios_empresa"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("empresas.id"), index=True, nullable=False)

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=True)
    rol: Mapped[RolUsuarioEmpresa] = mapped_column(
        Enum(RolUsuarioEmpresa), default=RolUsuarioEmpresa.OPERADOR, nullable=False
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    empresa: Mapped["Empresa"] = relationship(back_populates="usuarios")
