from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field


class LoginContadorRequest(BaseModel):
    email: EmailStr
    password: str


class LoginEmpresaRequest(BaseModel):
    email: EmailStr
    password: str


class ResponsabilidadTributaria(BaseModel):
    codigo: str
    descripcion: str


class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nombre: str
    nit: str | None
    tenant_id: str
    digito_verificacion: str | None = None
    tipo_persona: str | None = None
    responsabilidades_tributarias: list[ResponsabilidadTributaria] | None = None
    actividad_economica_codigo: str | None = None
    actividad_economica_descripcion: str | None = None
    direccion: str | None = None
    departamento: str | None = None
    municipio: str | None = None
    correo_electronico: str | None = None
    telefono: str | None = None
    representante_legal_nombre: str | None = None
    representante_legal_identificacion: str | None = None
    estado_rut: str | None = None
    creado_en: datetime
    ruta_rut: str | None = Field(default=None, exclude=True)

    @computed_field
    @property
    def tiene_rut(self) -> bool:
        return bool(self.ruta_rut)


class EmpresaActualOut(BaseModel):
    id: UUID
    nombre: str
    tenant_id: str


class MeOut(BaseModel):
    rol: str
    nombre: str
    email: str
    rol_empresa: str | None = None
    empresa_actual: EmpresaActualOut | None = None


class RutExtraidoOut(BaseModel):
    extraido_automaticamente: bool
    razon: str | None = None
    nombre: str | None = None
    nit: str | None = None
    digito_verificacion: str | None = None
    tipo_persona: str | None = None
    responsabilidades_tributarias: list[ResponsabilidadTributaria] | None = None
    actividad_economica_codigo: str | None = None
    actividad_economica_descripcion: str | None = None
    direccion: str | None = None
    departamento: str | None = None
    municipio: str | None = None
    correo_electronico: str | None = None
    telefono: str | None = None
    representante_legal_nombre: str | None = None
    representante_legal_identificacion: str | None = None
    estado_rut: str | None = None


class UsuarioEmpresaOut(BaseModel):
    id: UUID
    empresa_id: UUID
    email: str
    nombre: str
    telefono: str | None
    rol: str
    activo: bool
    creado_en: datetime

    class Config:
        from_attributes = True


class CrearUsuarioEmpresaRequest(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    rol: str
    telefono: str | None = None
