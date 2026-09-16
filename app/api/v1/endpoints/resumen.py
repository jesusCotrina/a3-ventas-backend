import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.cuentas import _total_gastos, _total_ventas, _ventas_pendientes
from app.core.deps import require_empresa
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.gasto import Gasto
from app.models.venta import Venta
from app.schemas.resumen import ResumenGastosOut, ResumenOut, ResumenSerieItem, ResumenVentasOut

router = APIRouter()


def _periodos_previos(periodo: str, cantidad: int) -> list[str]:
    anio, mes = (int(p) for p in periodo.split("-"))
    periodos = []
    for _ in range(cantidad):
        periodos.append(f"{anio:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            mes = 12
            anio -= 1
    return list(reversed(periodos))


@router.get("", response_model=ResumenOut)
def resumen(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> ResumenOut:
    periodo, inicio, fin = rango_mes(mes)

    total_ventas = _total_ventas(db, empresa_id, inicio, fin, moneda)
    total_gastos = _total_gastos(db, empresa_id, inicio, fin, moneda, None)
    cantidad_ventas = (
        db.scalar(
            select(func.count()).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
        or 0
    )
    saldo_por_cobrar = sum(
        (item.saldo for item in _ventas_pendientes(db, empresa_id, inicio, fin, moneda)),
        Decimal(0),
    )
    cantidad_gastos = (
        db.scalar(
            select(func.count()).where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
                Gasto.moneda == moneda,
            )
        )
        or 0
    )

    serie_mensual = []
    for p in _periodos_previos(periodo, 6):
        _, p_inicio, p_fin = rango_mes(p)
        serie_mensual.append(
            ResumenSerieItem(
                periodo=p,
                ventas=_total_ventas(db, empresa_id, p_inicio, p_fin, moneda),
                gastos=_total_gastos(db, empresa_id, p_inicio, p_fin, moneda, None),
            )
        )

    return ResumenOut(
        periodo=periodo,
        moneda=moneda,
        ventas=ResumenVentasOut(
            cantidad=cantidad_ventas,
            total=total_ventas,
            cobrado=total_ventas - saldo_por_cobrar,
        ),
        gastos=ResumenGastosOut(cantidad=cantidad_gastos, total=total_gastos),
        utilidad=total_ventas - total_gastos,
        saldo_por_cobrar=saldo_por_cobrar,
        serie_mensual=serie_mensual,
    )
