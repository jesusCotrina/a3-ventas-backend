import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(32), unique=True)
    nombre: Mapped[str] = mapped_column(String(120))
    ruc: Mapped[str | None] = mapped_column(String(20))
    direccion: Mapped[str | None] = mapped_column(String(255))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan: Mapped[str] = mapped_column(String(16), default="free")
    """'free' | 'basico' | 'premium' (ver empresas.py::_LIMITE_USUARIOS_POR_PLAN)."""
    plan_vence_en: Mapped[date | None] = mapped_column(Date, default=None)
    """Solo aplica al plan 'free': hasta cuando dura el acceso de nivel
    premium sin costo. NULL = sin vencimiento (empresas 'basico'/'premium'
    pagas, o un 'free' sin limite de tiempo asignado todavia)."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
