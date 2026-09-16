import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa
from app.db.session import get_db
from app.models.catalogo import TipoMantenimiento, TipoReparacion
from app.schemas.taller import TipoMantenimientoOut, TipoReparacionOut

router = APIRouter()


@router.get("/mantenimiento", response_model=list[TipoMantenimientoOut])
def listar_tipos_mantenimiento(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[TipoMantenimientoOut]:
    tipos = db.scalars(
        select(TipoMantenimiento)
        .where(TipoMantenimiento.empresa_id == empresa_id)
        .order_by(TipoMantenimiento.categoria, TipoMantenimiento.nombre)
    )
    return [TipoMantenimientoOut(categoria=t.categoria, nombre=t.nombre) for t in tipos]


@router.get("/reparacion", response_model=list[TipoReparacionOut])
def listar_tipos_reparacion(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[TipoReparacionOut]:
    tipos = db.scalars(
        select(TipoReparacion)
        .where(TipoReparacion.empresa_id == empresa_id)
        .order_by(TipoReparacion.nombre)
    )
    return [TipoReparacionOut(nombre=t.nombre) for t in tipos]
