import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.db.session import get_db
from app.models.cliente import Cliente
from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.vehiculo import Vehiculo
from app.schemas.taller import (
    EstadisticasTallerOut,
    HistorialItemOut,
    HistoricoMantenimientoOut,
    HistoricoReparacionOut,
    VehiculoBusquedaOut,
    VehiculoCreate,
    VehiculoOut,
    VehiculoUpdate,
)

router = APIRouter()

_EDITORES = ("super_admin", "admin")
_LIMITE_RESULTADOS = 10


def _like(termino: str) -> str:
    return f"%{termino.strip().lower()}%"


def _resolver_cliente(
    db: Session, empresa_id: uuid.UUID, tip_documento: str, num_documento: str
) -> Cliente:
    cliente = db.scalar(
        select(Cliente).where(
            Cliente.empresa_id == empresa_id,
            Cliente.tip_documento == tip_documento,
            Cliente.num_documento == num_documento,
        )
    )
    if cliente is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No existe un cliente con ese tipo y numero de documento en esta empresa. "
            "Crea el cliente primero.",
        )
    return cliente


def _find_vehiculo(db: Session, empresa_id: uuid.UUID, placa: str) -> Vehiculo:
    placa_normalizada = placa.strip().upper()
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.empresa_id == empresa_id,
            Vehiculo.placa == placa_normalizada,
        )
    )
    if vehiculo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "No se encontro un vehiculo con esa placa"
        )
    return vehiculo


def _ultimo_mantenimiento(
    db: Session, vehiculo_id: uuid.UUID
) -> HistoricoMantenimiento | None:
    return db.scalar(
        select(HistoricoMantenimiento)
        .where(HistoricoMantenimiento.vehiculo_id == vehiculo_id)
        .order_by(
            HistoricoMantenimiento.fec_mantenimiento.desc(),
            HistoricoMantenimiento.created_at.desc(),
        )
        .limit(1)
    )


def _ultima_reparacion(
    db: Session, vehiculo_id: uuid.UUID
) -> HistoricoReparacion | None:
    return db.scalar(
        select(HistoricoReparacion)
        .where(HistoricoReparacion.vehiculo_id == vehiculo_id)
        .order_by(
            HistoricoReparacion.fec_reparacion.desc(),
            HistoricoReparacion.created_at.desc(),
        )
        .limit(1)
    )


@router.get("/buscar", response_model=VehiculoBusquedaOut)
def buscar_por_placa(
    placa: str = Query(..., min_length=1),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> VehiculoBusquedaOut:
    vehiculo = _find_vehiculo(db, empresa_id, placa)
    ultimo_mant = _ultimo_mantenimiento(db, vehiculo.id)
    ultima_rep = _ultima_reparacion(db, vehiculo.id)
    return VehiculoBusquedaOut(
        vehiculo=VehiculoOut.from_model(vehiculo),
        ultimo_mantenimiento=(
            HistoricoMantenimientoOut.from_model(ultimo_mant) if ultimo_mant else None
        ),
        ultima_reparacion=(
            HistoricoReparacionOut.from_model(ultima_rep) if ultima_rep else None
        ),
    )


@router.get("/estadisticas", response_model=EstadisticasTallerOut)
def estadisticas_taller(
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> EstadisticasTallerOut:
    """Totales de la empresa (todos los vehiculos): cantidad de mantenimientos,
    de reparaciones, y costo acumulado de ambos. Sirve como vista por defecto
    del modulo de Mantenimiento/Reparacion antes de filtrar por placa."""
    total_mantenimientos = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoMantenimiento)
            .where(HistoricoMantenimiento.empresa_id == empresa_id)
        )
        or 0
    )
    total_reparaciones = (
        db.scalar(
            select(func.count())
            .select_from(HistoricoReparacion)
            .where(HistoricoReparacion.empresa_id == empresa_id)
        )
        or 0
    )
    costo_mantenimientos = db.scalar(
        select(func.coalesce(func.sum(HistoricoMantenimiento.costo), 0)).where(
            HistoricoMantenimiento.empresa_id == empresa_id
        )
    )
    costo_reparaciones = db.scalar(
        select(func.coalesce(func.sum(HistoricoReparacion.costo), 0)).where(
            HistoricoReparacion.empresa_id == empresa_id
        )
    )
    return EstadisticasTallerOut(
        total_mantenimientos=total_mantenimientos,
        total_reparaciones=total_reparaciones,
        costo_total=Decimal(costo_mantenimientos) + Decimal(costo_reparaciones),
    )


@router.get("/{vehiculo_id}/historial", response_model=list[HistorialItemOut])
def historial_vehiculo(
    vehiculo_id: uuid.UUID,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[HistorialItemOut]:
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.id == vehiculo_id, Vehiculo.empresa_id == empresa_id
        )
    )
    if vehiculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no encontrado")

    mantenimientos = db.scalars(
        select(HistoricoMantenimiento).where(
            HistoricoMantenimiento.vehiculo_id == vehiculo_id
        )
    )
    reparaciones = db.scalars(
        select(HistoricoReparacion).where(
            HistoricoReparacion.vehiculo_id == vehiculo_id
        )
    )

    items = [
        HistorialItemOut(
            tipo="mantenimiento",
            id=m.id,
            fecha=m.fec_mantenimiento,
            kilometraje=m.kilometraje,
            costo=m.costo,
            detalle=m.tipo_mantenimiento,
            cambios=m.cambios_realizados,
            creado_por=m.usuario.full_name,
        )
        for m in mantenimientos
    ] + [
        HistorialItemOut(
            tipo="reparacion",
            id=r.id,
            fecha=r.fec_reparacion,
            kilometraje=r.kilometraje,
            costo=r.costo,
            detalle=r.nota or "",
            cambios=r.reparaciones_realizadas,
            creado_por=r.usuario.full_name,
        )
        for r in reparaciones
    ]
    items.sort(key=lambda i: i.fecha, reverse=True)
    return items


@router.get("", response_model=list[VehiculoOut])
def buscar_vehiculos(
    placa: str | None = None,
    modelo: str | None = None,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VehiculoOut]:
    """Busca por placa y/o modelo (coincidencia parcial, combinados con AND
    si se dan ambos). Sin filtros, lista los vehiculos de la empresa en
    orden alfabetico (vista por defecto). Sirve tanto para el modulo de
    Vehiculos como para el autocompletado de placa del modulo de
    Mantenimiento."""
    stmt = select(Vehiculo).where(Vehiculo.empresa_id == empresa_id)
    if placa:
        stmt = stmt.where(func.lower(Vehiculo.placa).like(_like(placa)))
    if modelo:
        stmt = stmt.where(func.lower(Vehiculo.modelo).like(_like(modelo)))

    vehiculos = db.scalars(
        stmt.order_by(Vehiculo.placa).limit(_LIMITE_RESULTADOS)
    )
    return [VehiculoOut.from_model(v) for v in vehiculos]


@router.post("", response_model=VehiculoOut, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    data: VehiculoCreate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> VehiculoOut:
    cliente = _resolver_cliente(db, empresa_id, data.tip_documento, data.num_documento)

    placa_normalizada = data.placa.strip().upper()
    existe = db.scalar(
        select(Vehiculo).where(
            Vehiculo.empresa_id == empresa_id, Vehiculo.placa == placa_normalizada
        )
    )
    if existe is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un vehiculo con esa placa"
        )

    vehiculo = Vehiculo(
        empresa_id=empresa_id,
        cliente_id=cliente.id,
        placa=placa_normalizada,
        marca=data.marca,
        modelo=data.modelo,
        carroceria=data.carroceria,
        num_motor=data.num_motor,
        vin_serie=data.vin_serie,
    )
    db.add(vehiculo)
    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut.from_model(vehiculo)


@router.patch("/{vehiculo_id}", response_model=VehiculoOut)
def actualizar_vehiculo(
    vehiculo_id: uuid.UUID,
    data: VehiculoUpdate,
    empresa_id: uuid.UUID = Depends(require_empresa),
    _: object = Depends(require_roles(*_EDITORES)),
    db: Session = Depends(get_db),
) -> VehiculoOut:
    vehiculo = db.scalar(
        select(Vehiculo).where(
            Vehiculo.id == vehiculo_id, Vehiculo.empresa_id == empresa_id
        )
    )
    if vehiculo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehiculo no encontrado")

    cliente = _resolver_cliente(db, empresa_id, data.tip_documento, data.num_documento)

    placa_normalizada = data.placa.strip().upper()
    if placa_normalizada != vehiculo.placa:
        existe = db.scalar(
            select(Vehiculo).where(
                Vehiculo.empresa_id == empresa_id,
                Vehiculo.placa == placa_normalizada,
                Vehiculo.id != vehiculo_id,
            )
        )
        if existe is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya existe un vehiculo con esa placa"
            )

    vehiculo.placa = placa_normalizada
    vehiculo.marca = data.marca
    vehiculo.modelo = data.modelo
    vehiculo.carroceria = data.carroceria
    vehiculo.num_motor = data.num_motor
    vehiculo.vin_serie = data.vin_serie
    vehiculo.cliente_id = cliente.id
    db.commit()
    db.refresh(vehiculo)
    return VehiculoOut.from_model(vehiculo)
