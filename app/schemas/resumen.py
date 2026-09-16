from decimal import Decimal

from pydantic import BaseModel


class ResumenVentasOut(BaseModel):
    cantidad: int
    total: Decimal
    cobrado: Decimal


class ResumenGastosOut(BaseModel):
    cantidad: int
    total: Decimal


class ResumenSerieItem(BaseModel):
    periodo: str
    ventas: Decimal
    gastos: Decimal


class ResumenOut(BaseModel):
    periodo: str
    moneda: str
    ventas: ResumenVentasOut
    gastos: ResumenGastosOut
    utilidad: Decimal
    saldo_por_cobrar: Decimal
    serie_mensual: list[ResumenSerieItem]
