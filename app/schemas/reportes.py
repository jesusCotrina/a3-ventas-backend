from decimal import Decimal

from pydantic import BaseModel


class VentaDiariaItem(BaseModel):
    dia: int
    total: Decimal


class VendedorVentaItem(BaseModel):
    vendedor_nombre: str
    total: Decimal


class ProductoTopItem(BaseModel):
    producto_nombre: str
    unidades: int
    monto: Decimal


class ClienteTopItem(BaseModel):
    cliente_nombre: str
    total: Decimal
