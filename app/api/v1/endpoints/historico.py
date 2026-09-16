import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.user import User
from app.models.vehiculo import Vehiculo
from app.schemas.taller import (
    HistoricoMantenimientoCreate,
    HistoricoMantenimientoOut,
    HistoricoMantenimientoUpdate,
    HistoricoReparacionCreate,
    HistoricoReparacionOut,
    HistoricoReparacionUpdate,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")
_CREADORES = ("super_admin", "admin", "vendedor")


def _check_tenant(user: User, empresa_id: uuid.UUID) -> None:
    if user.empresa_id != empresa_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")


def _resolver_vehiculo_por_placa(
    db: Session, empresa_id: uuid.UUID, placa: str
) -> Vehiculo:
    placa_normalizada = placa.strip().upper()
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.empresa_id == empresa_id, Vehiculo.placa == placa_normalizada
        )
    )
    if vehiculo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No existe un vehiculo con esa placa"
        )
    return vehiculo


@router.post(
    "/mantenimiento", response_model=HistoricoMantenimientoOut, status_code=status.HTTP_201_CREATED
)
def crear_mantenimiento(
    data: HistoricoMantenimientoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_CREADORES)),
    db: Session = Depends(get_db),
) -> HistoricoMantenimientoOut:
    vehiculo = _resolver_vehiculo_por_placa(db, empresa_id, data.placa)
    registro = HistoricoMantenimiento(
        empresa_id=empresa_id,
        vehiculo_id=vehiculo.id,
        usuario_id=user.id,
        fec_mantenimiento=data.fec_mantenimiento,
        kilometraje=data.kilometraje,
        tipo_mantenimiento=data.tipo_mantenimiento,
        cambios_realizados=data.cambios_realizados,
        costo=data.costo,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return HistoricoMantenimientoOut.from_model(registro)


@router.post(
    "/reparaciones", response_model=HistoricoReparacionOut, status_code=status.HTTP_201_CREATED
)
def crear_reparacion(
    data: HistoricoReparacionCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    user: User = Depends(require_roles(*_CREADORES)),
    db: Session = Depends(get_db),
) -> HistoricoReparacionOut:
    vehiculo = _resolver_vehiculo_por_placa(db, empresa_id, data.placa)
    registro = HistoricoReparacion(
        empresa_id=empresa_id,
        vehiculo_id=vehiculo.id,
        usuario_id=user.id,
        fec_reparacion=data.fec_reparacion,
        kilometraje=data.kilometraje,
        reparaciones_realizadas=data.reparaciones_realizadas,
        nota=data.nota,
        costo=data.costo,
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return HistoricoReparacionOut.from_model(registro)


@router.patch("/mantenimiento/{historico_id}", response_model=HistoricoMantenimientoOut)
def actualizar_mantenimiento(
    historico_id: uuid.UUID,
    data: HistoricoMantenimientoUpdate,
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> HistoricoMantenimientoOut:
    registro = db.get(HistoricoMantenimiento, historico_id)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    _check_tenant(user, registro.empresa_id)

    registro.fec_mantenimiento = data.fec_mantenimiento
    registro.kilometraje = data.kilometraje
    registro.tipo_mantenimiento = data.tipo_mantenimiento
    registro.cambios_realizados = data.cambios_realizados
    registro.costo = data.costo
    db.commit()
    db.refresh(registro)
    return HistoricoMantenimientoOut.from_model(registro)


@router.patch("/reparaciones/{historico_id}", response_model=HistoricoReparacionOut)
def actualizar_reparacion(
    historico_id: uuid.UUID,
    data: HistoricoReparacionUpdate,
    user: User = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> HistoricoReparacionOut:
    registro = db.get(HistoricoReparacion, historico_id)
    if registro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registro no encontrado")
    _check_tenant(user, registro.empresa_id)

    registro.fec_reparacion = data.fec_reparacion
    registro.kilometraje = data.kilometraje
    registro.reparaciones_realizadas = data.reparaciones_realizadas
    registro.nota = data.nota
    registro.costo = data.costo
    db.commit()
    db.refresh(registro)
    return HistoricoReparacionOut.from_model(registro)
