import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.models.historico import HistoricoMantenimiento, HistoricoReparacion
from app.models.vehiculo import Vehiculo
from app.schemas.cliente import ClienteOut


class VehiculoOut(BaseModel):
    id: uuid.UUID
    placa: str
    marca: str | None
    modelo: str | None
    carroceria: str | None
    num_motor: str | None
    vin_serie: str | None
    cliente: ClienteOut

    @classmethod
    def from_model(cls, vehiculo: Vehiculo) -> "VehiculoOut":
        return cls(
            id=vehiculo.id,
            placa=vehiculo.placa,
            marca=vehiculo.marca,
            modelo=vehiculo.modelo,
            carroceria=vehiculo.carroceria,
            num_motor=vehiculo.num_motor,
            vin_serie=vehiculo.vin_serie,
            cliente=ClienteOut.from_model(vehiculo.cliente),
        )


class VehiculoResumenOut(BaseModel):
    """Version minima de un vehiculo: solo placa y marca (para listarlo bajo
    la ficha de un cliente, que puede tener varios)."""

    id: uuid.UUID
    placa: str
    marca: str | None

    @classmethod
    def from_model(cls, vehiculo: Vehiculo) -> "VehiculoResumenOut":
        return cls(id=vehiculo.id, placa=vehiculo.placa, marca=vehiculo.marca)


class VehiculoCreate(BaseModel):
    placa: str
    marca: str | None = None
    modelo: str | None = None
    carroceria: str | None = None
    num_motor: str | None = None
    vin_serie: str | None = None
    tip_documento: str
    """Documento del dueno: se usa para resolver el cliente ya existente."""
    num_documento: str


class VehiculoUpdate(VehiculoCreate):
    pass


class HistoricoMantenimientoOut(BaseModel):
    id: uuid.UUID
    placa: str
    fec_mantenimiento: date
    kilometraje: int
    tipo_mantenimiento: str
    cambios_realizados: list[str]
    costo: Decimal | None
    creado_por: str

    @classmethod
    def from_model(cls, h: HistoricoMantenimiento) -> "HistoricoMantenimientoOut":
        return cls(
            id=h.id,
            placa=h.vehiculo.placa,
            fec_mantenimiento=h.fec_mantenimiento,
            kilometraje=h.kilometraje,
            tipo_mantenimiento=h.tipo_mantenimiento,
            cambios_realizados=h.cambios_realizados,
            costo=h.costo,
            creado_por=h.usuario.full_name,
        )


class HistoricoReparacionOut(BaseModel):
    id: uuid.UUID
    placa: str
    fec_reparacion: date
    kilometraje: int
    reparaciones_realizadas: list[str]
    nota: str | None
    costo: Decimal | None
    creado_por: str

    @classmethod
    def from_model(cls, h: HistoricoReparacion) -> "HistoricoReparacionOut":
        return cls(
            id=h.id,
            placa=h.vehiculo.placa,
            fec_reparacion=h.fec_reparacion,
            kilometraje=h.kilometraje,
            reparaciones_realizadas=h.reparaciones_realizadas,
            nota=h.nota,
            costo=h.costo,
            creado_por=h.usuario.full_name,
        )


class VehiculoBusquedaOut(BaseModel):
    vehiculo: VehiculoOut
    ultimo_mantenimiento: HistoricoMantenimientoOut | None
    ultima_reparacion: HistoricoReparacionOut | None


class HistorialItemOut(BaseModel):
    tipo: Literal["mantenimiento", "reparacion"]
    id: uuid.UUID
    fecha: date
    kilometraje: int
    costo: Decimal | None
    detalle: str
    """Tipo de mantenimiento, o nota de la reparacion (recortada)."""
    cambios: list[str]
    creado_por: str


class HistoricoMantenimientoUpdate(BaseModel):
    fec_mantenimiento: date
    kilometraje: int
    tipo_mantenimiento: str
    cambios_realizados: list[str]
    costo: Decimal | None = None


class HistoricoMantenimientoCreate(HistoricoMantenimientoUpdate):
    placa: str
    """Placa del vehiculo ya existente al que pertenece el mantenimiento."""


class HistoricoReparacionUpdate(BaseModel):
    fec_reparacion: date
    kilometraje: int
    reparaciones_realizadas: list[str]
    nota: str | None = None
    costo: Decimal | None = None


class HistoricoReparacionCreate(HistoricoReparacionUpdate):
    placa: str
    """Placa del vehiculo ya existente al que pertenece la reparacion."""


class TipoMantenimientoOut(BaseModel):
    categoria: str
    nombre: str


class TipoReparacionOut(BaseModel):
    nombre: str


class EstadisticasTallerOut(BaseModel):
    total_mantenimientos: int
    total_reparaciones: int
    costo_total: Decimal
