import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.empresa import Empresa

PLANES = ("free", "basico", "premium")

# Cuantos usuarios activos puede tener una empresa segun su plan. "free" es
# un trial de nivel premium por tiempo limitado (ver Empresa.plan_vence_en):
# mientras dura, comparte el limite de "premium".
LIMITE_USUARIOS_POR_PLAN: dict[str, int] = {
    "free": 10,
    "basico": 3,
    "premium": 10,
}


def plan_vencido(plan: str, plan_vence_en: date | None) -> bool:
    """El plan 'free' vence en la fecha indicada (si tiene una asignada);
    'basico'/'premium' no vencen por tiempo, se gestionan activando o
    desactivando la empresa."""
    if plan != "free" or plan_vence_en is None:
        return False
    return plan_vence_en < date.today()


def empresa_habilitada(empresa: Empresa) -> bool:
    """Si una empresa desactivada bloquea el login (`is_active`), un plan
    'free' vencido lo bloquea igual: se trata como si estuviera desactivada
    hasta que un super_admin extienda la fecha o le asigne otro plan (ver
    PATCH /empresas/{id}/plan)."""
    return empresa.is_active and not plan_vencido(empresa.plan, empresa.plan_vence_en)


class EmpresaOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    logo_url: str | None

    @classmethod
    def from_model(cls, empresa: Empresa) -> "EmpresaOut":
        return cls(
            id=empresa.id,
            codigo=empresa.codigo,
            nombre=empresa.nombre,
            logo_url=empresa.logo_url,
        )


class EmpresaAdminOut(BaseModel):
    """Vista de una empresa para el modulo de Administracion (super_admin ve
    todas; admin ve solo la suya, ver GET /empresas en empresas.py)."""

    id: uuid.UUID
    codigo: str
    nombre: str
    ruc: str | None
    direccion: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    total_usuarios: int
    usuarios_activos: int
    plan: str
    plan_vence_en: date | None
    plan_vencido: bool
    limite_usuarios: int

    @classmethod
    def from_model(
        cls, empresa: Empresa, total_usuarios: int, usuarios_activos: int
    ) -> "EmpresaAdminOut":
        return cls(
            id=empresa.id,
            codigo=empresa.codigo,
            nombre=empresa.nombre,
            ruc=empresa.ruc,
            direccion=empresa.direccion,
            logo_url=empresa.logo_url,
            is_active=empresa.is_active,
            created_at=empresa.created_at,
            total_usuarios=total_usuarios,
            usuarios_activos=usuarios_activos,
            plan=empresa.plan,
            plan_vence_en=empresa.plan_vence_en,
            plan_vencido=plan_vencido(empresa.plan, empresa.plan_vence_en),
            limite_usuarios=LIMITE_USUARIOS_POR_PLAN.get(empresa.plan, 3),
        )


class EmpresaUsuarioCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    password: str = Field(min_length=8)
    role_code: str


class EmpresaCreate(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    nombre: str = Field(min_length=1, max_length=120)
    ruc: str | None = None
    direccion: str | None = None
    logo_url: str | None = None
    usuarios: list[EmpresaUsuarioCreate]


class EmpresaUpdate(BaseModel):
    codigo: str = Field(min_length=1, max_length=32)
    nombre: str = Field(min_length=1, max_length=120)
    ruc: str | None = None
    direccion: str | None = None
    logo_url: str | None = None


class EmpresaEstadoUpdate(BaseModel):
    is_active: bool


class EmpresaPlanUpdate(BaseModel):
    plan: str = Field(pattern="^(free|basico|premium)$")
    plan_vence_en: date | None = None
    """Solo tiene efecto si `plan == 'free'`. Se puede mandar cualquier
    fecha (pasada, presente o futura) o `null` para quitar el vencimiento:
    asi un super_admin puede acortar, extender o eliminar el limite de
    tiempo del trial de una empresa en cualquier momento."""


class EmpresaUsuarioOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    role_code: str
    role_name: str
    is_active: bool


class UsuarioEstadoUpdate(BaseModel):
    is_active: bool


class EmpresaUsuarioUpdate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1)
    role_code: str
