import calendar
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.producto import Producto
from app.models.user import User
from app.models.venta import DetalleVenta, Venta
from app.schemas.reportes import (
    ClienteTopItem,
    ProductoTopItem,
    VendedorVentaItem,
    VentaDiariaItem,
)

router = APIRouter(dependencies=[Depends(require_roles("admin", "super_admin"))])


@router.get("/ventas-diarias", response_model=list[VentaDiariaItem])
def ventas_diarias(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VentaDiariaItem]:
    """Total vendido de cada dia del mes (con ceros en los dias sin venta),
    para el grafico de Reportes de ventas por dia."""
    _, inicio, fin = rango_mes(mes)
    columna = Venta.total_soles if moneda == "PEN" else Venta.total_dolares
    filas = db.execute(
        select(func.extract("day", Venta.fecha), func.coalesce(func.sum(columna), 0))
        .where(Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin)
        .group_by(func.extract("day", Venta.fecha))
    ).all()
    totales_por_dia = {int(dia): Decimal(total) for dia, total in filas}
    _, dias_del_mes = calendar.monthrange(inicio.year, inicio.month)
    return [
        VentaDiariaItem(dia=d, total=totales_por_dia.get(d, Decimal(0)))
        for d in range(1, dias_del_mes + 1)
    ]


@router.get("/ventas-por-vendedor", response_model=list[VendedorVentaItem])
def ventas_por_vendedor(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[VendedorVentaItem]:
    _, inicio, fin = rango_mes(mes)
    columna = Venta.total_soles if moneda == "PEN" else Venta.total_dolares
    filas = db.execute(
        select(User.full_name, func.coalesce(func.sum(columna), 0))
        .select_from(Venta)
        .join(User, Venta.vendedor_id == User.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            columna > 0,
        )
        .group_by(User.full_name)
        .order_by(func.sum(columna).desc())
    ).all()
    return [VendedorVentaItem(vendedor_nombre=nombre, total=total) for nombre, total in filas]


@router.get("/productos-mas-vendidos", response_model=list[ProductoTopItem])
def productos_mas_vendidos(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    limit: int = Query(10, ge=1, le=50),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ProductoTopItem]:
    _, inicio, fin = rango_mes(mes)
    filas = db.execute(
        select(
            Producto.nombre,
            func.coalesce(func.sum(DetalleVenta.unidades), 0),
            func.coalesce(func.sum(DetalleVenta.subtotal), 0),
        )
        .select_from(DetalleVenta)
        .join(Venta, DetalleVenta.venta_id == Venta.id)
        .join(Producto, DetalleVenta.producto_id == Producto.id)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            DetalleVenta.moneda == moneda,
        )
        .group_by(Producto.nombre)
        .order_by(func.sum(DetalleVenta.unidades).desc())
        .limit(limit)
    ).all()
    return [
        ProductoTopItem(producto_nombre=nombre, unidades=unidades, monto=monto)
        for nombre, unidades, monto in filas
    ]


@router.get("/top-clientes", response_model=list[ClienteTopItem])
def top_clientes(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    limit: int = Query(10, ge=1, le=50),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[ClienteTopItem]:
    _, inicio, fin = rango_mes(mes)
    columna = Venta.total_soles if moneda == "PEN" else Venta.total_dolares
    etiqueta = func.coalesce(Venta.cliente_nombre, Venta.cliente_documento, "Cliente sin nombre")
    filas = db.execute(
        select(etiqueta, func.coalesce(func.sum(columna), 0))
        .where(
            Venta.empresa_id == empresa_id,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            columna > 0,
        )
        .group_by(etiqueta)
        .order_by(func.sum(columna).desc())
        .limit(limit)
    ).all()
    return [ClienteTopItem(cliente_nombre=nombre, total=total) for nombre, total in filas]
