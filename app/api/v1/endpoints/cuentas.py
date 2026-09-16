import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import require_empresa, require_roles
from app.core.periodo import rango_mes
from app.db.session import get_db
from app.models.cuenta import ParametrosCuenta
from app.models.gasto import Gasto, TipoGasto
from app.models.producto import Producto
from app.models.venta import CobroVenta, DetalleVenta, Venta
from app.schemas.cuenta import (
    CostoVentaItem,
    CuentaPorCobrarItem,
    CuentaPorPagarItem,
    CuentasCobrarPagarOut,
    EntradaCajaItem,
    EstadoResultadosOut,
    FlujoCajaOut,
    ImpuestoIn,
    SaldoInicialIn,
)

router = APIRouter(dependencies=[Depends(require_roles("admin", "super_admin"))])

IGV_TASA = Decimal("0.18")


def _total_ventas(db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str) -> Decimal:
    columna = Venta.total_soles if moneda == "PEN" else Venta.total_dolares
    return (
        db.scalar(
            select(func.coalesce(func.sum(columna), 0)).where(
                Venta.empresa_id == empresa_id, Venta.fecha >= inicio, Venta.fecha < fin
            )
        )
        or Decimal(0)
    )


def _costo_venta(db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str) -> Decimal:
    costo_col = Producto.costo_soles if moneda == "PEN" else Producto.costo_dolares
    return (
        db.scalar(
            select(func.coalesce(func.sum(DetalleVenta.unidades * costo_col), 0))
            .select_from(DetalleVenta)
            .join(Venta, DetalleVenta.venta_id == Venta.id)
            .join(Producto, DetalleVenta.producto_id == Producto.id)
            .where(
                Venta.empresa_id == empresa_id,
                Venta.fecha >= inicio,
                Venta.fecha < fin,
                DetalleVenta.moneda == moneda,
            )
        )
        or Decimal(0)
    )


def _total_gastos(
    db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str, categoria: str | None
) -> Decimal:
    stmt = select(func.coalesce(func.sum(Gasto.costo_total), 0)).where(
        Gasto.empresa_id == empresa_id,
        Gasto.fecha >= inicio,
        Gasto.fecha < fin,
        Gasto.moneda == moneda,
    )
    if categoria:
        stmt = stmt.join(TipoGasto).where(TipoGasto.categoria == categoria)
    return db.scalar(stmt) or Decimal(0)


def _total_compras_credito_fiscal(
    db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str
) -> Decimal:
    """Base para el credito fiscal de IGV: solo los gastos operativos cuyo
    comprobante discrimina IGV (Gasto.aplica_credito_fiscal)."""
    return (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total), 0))
            .join(TipoGasto)
            .where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
                Gasto.moneda == moneda,
                Gasto.aplica_credito_fiscal.is_(True),
                TipoGasto.categoria == "operativo",
            )
        )
        or Decimal(0)
    )


def _parametros(db: Session, empresa_id: uuid.UUID, periodo: str, moneda: str) -> ParametrosCuenta:
    parametros = db.get(ParametrosCuenta, (empresa_id, periodo, moneda))
    if parametros is None:
        parametros = ParametrosCuenta(empresa_id=empresa_id, periodo=periodo, moneda=moneda)
        db.add(parametros)
        db.commit()
        db.refresh(parametros)
    return parametros


@router.get("/estado-resultados", response_model=EstadoResultadosOut)
def estado_resultados(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> EstadoResultadosOut:
    periodo, inicio, fin = rango_mes(mes)
    parametros = _parametros(db, empresa_id, periodo, moneda)

    ingresos = _total_ventas(db, empresa_id, inicio, fin, moneda)
    costo_venta = _costo_venta(db, empresa_id, inicio, fin, moneda)
    utilidad_bruta = ingresos - costo_venta

    gastos_operativos = _total_gastos(db, empresa_id, inicio, fin, moneda, "operativo")
    utilidad_operativa = utilidad_bruta - gastos_operativos

    ingresos_financieros = _total_gastos(
        db, empresa_id, inicio, fin, moneda, "financiero_ingreso"
    )
    gastos_financieros = _total_gastos(db, empresa_id, inicio, fin, moneda, "financiero_egreso")
    utilidad_antes_impuestos = utilidad_operativa + ingresos_financieros - gastos_financieros

    utilidad_neta = utilidad_antes_impuestos - parametros.impuesto

    return EstadoResultadosOut(
        periodo=periodo,
        moneda=moneda,
        ingresos=ingresos,
        costo_venta=costo_venta,
        utilidad_bruta=utilidad_bruta,
        gastos_operativos=gastos_operativos,
        utilidad_operativa=utilidad_operativa,
        ingresos_financieros=ingresos_financieros,
        gastos_financieros=gastos_financieros,
        utilidad_antes_impuestos=utilidad_antes_impuestos,
        impuesto=parametros.impuesto,
        utilidad_neta=utilidad_neta,
    )


@router.get("/estado-resultados/costo-venta", response_model=list[CostoVentaItem])
def costo_venta_detalle(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CostoVentaItem]:
    _, inicio, fin = rango_mes(mes)
    costo_col = Producto.costo_soles if moneda == "PEN" else Producto.costo_dolares
    filas = db.execute(
        select(
            Venta.id,
            Venta.fecha,
            Producto.nombre,
            DetalleVenta.unidades,
            costo_col,
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
        .order_by(Venta.fecha.desc())
    )
    return [
        CostoVentaItem(
            venta_id=venta_id,
            fecha=fecha,
            producto_nombre=nombre,
            unidades=unidades,
            costo_unitario=costo_unitario or Decimal(0),
            subtotal_costo=(costo_unitario or Decimal(0)) * unidades,
        )
        for venta_id, fecha, nombre, unidades, costo_unitario in filas
    ]


@router.put("/estado-resultados/impuesto", response_model=EstadoResultadosOut)
def actualizar_impuesto(
    data: ImpuestoIn,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> EstadoResultadosOut:
    periodo, _, _ = rango_mes(data.mes)
    parametros = _parametros(db, empresa_id, periodo, data.moneda)
    parametros.impuesto = data.monto
    db.commit()
    return estado_resultados(mes=data.mes, moneda=data.moneda, empresa_id=empresa_id, db=db)


def _ingresos_ventas_caja(
    db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str
) -> Decimal:
    """Entradas de caja por ventas: para PEN es lo realmente cobrado en el
    periodo (segun la fecha de cada cobro, no la de la venta - ver
    CobroVenta); para USD, al no rastrearse abonos parciales, se usa el
    total vendido en el periodo."""
    if moneda != "PEN":
        return _total_ventas(db, empresa_id, inicio, fin, moneda)
    return (
        db.scalar(
            select(func.coalesce(func.sum(CobroVenta.monto), 0))
            .select_from(CobroVenta)
            .join(Venta, CobroVenta.venta_id == Venta.id)
            .where(
                Venta.empresa_id == empresa_id,
                CobroVenta.fecha >= inicio,
                CobroVenta.fecha < fin,
            )
        )
        or Decimal(0)
    )


@router.get("/flujo-caja", response_model=FlujoCajaOut)
def flujo_caja(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> FlujoCajaOut:
    periodo, inicio, fin = rango_mes(mes)
    parametros = _parametros(db, empresa_id, periodo, moneda)

    ingresos_ventas = _ingresos_ventas_caja(db, empresa_id, inicio, fin, moneda)
    compras_y_gastos = _total_gastos(db, empresa_id, inicio, fin, moneda, None)
    saldo_final = parametros.saldo_inicial + ingresos_ventas - compras_y_gastos

    return FlujoCajaOut(
        periodo=periodo,
        moneda=moneda,
        saldo_inicial=parametros.saldo_inicial,
        ingresos_ventas=ingresos_ventas,
        compras_y_gastos=compras_y_gastos,
        saldo_final=saldo_final,
    )


@router.put("/flujo-caja/saldo-inicial", response_model=FlujoCajaOut)
def actualizar_saldo_inicial(
    data: SaldoInicialIn,
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> FlujoCajaOut:
    periodo, _, _ = rango_mes(data.mes)
    parametros = _parametros(db, empresa_id, periodo, data.moneda)
    parametros.saldo_inicial = data.monto
    db.commit()
    return flujo_caja(mes=data.mes, moneda=data.moneda, empresa_id=empresa_id, db=db)


@router.get("/flujo-caja/entradas", response_model=list[EntradaCajaItem])
def flujo_caja_entradas(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[EntradaCajaItem]:
    """Detalle de las entradas de caja del periodo: para PEN, cada cobro
    (total o parcial) registrado en el mes, sin importar la fecha de la
    venta; para USD, las ventas del mes (no hay cobro parcial rastreado)."""
    _, inicio, fin = rango_mes(mes)
    if moneda == "PEN":
        filas = db.execute(
            select(CobroVenta, Venta)
            .join(Venta, CobroVenta.venta_id == Venta.id)
            .where(
                Venta.empresa_id == empresa_id,
                CobroVenta.fecha >= inicio,
                CobroVenta.fecha < fin,
            )
            .order_by(CobroVenta.fecha.desc())
        )
        return [
            EntradaCajaItem(
                venta_id=venta.id,
                fecha=cobro.fecha,
                cliente_nombre=venta.cliente_nombre,
                cliente_documento=venta.cliente_documento,
                vendedor_nombre=venta.vendedor.full_name,
                total_venta=venta.total_soles,
                monto_cobro=cobro.monto,
            )
            for cobro, venta in filas
        ]

    ventas = db.scalars(
        select(Venta)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            Venta.total_dolares > 0,
        )
        .order_by(Venta.fecha.desc())
    )
    return [
        EntradaCajaItem(
            venta_id=v.id,
            fecha=v.fecha,
            cliente_nombre=v.cliente_nombre,
            cliente_documento=v.cliente_documento,
            vendedor_nombre=v.vendedor.full_name,
            total_venta=v.total_dolares,
            monto_cobro=v.total_dolares,
        )
        for v in ventas
    ]


@router.get("/cobrar-pagar", response_model=CuentasCobrarPagarOut)
def cobrar_pagar(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> CuentasCobrarPagarOut:
    periodo, inicio, fin = rango_mes(mes)

    total_ventas = _total_ventas(db, empresa_id, inicio, fin, moneda)
    compras = _total_compras_credito_fiscal(db, empresa_id, inicio, fin, moneda)
    igv_ventas = total_ventas * IGV_TASA
    igv_compras = compras * IGV_TASA
    igv_diferencia = igv_ventas - igv_compras

    saldo_por_cobrar = sum(
        (item.saldo for item in _ventas_pendientes(db, empresa_id, inicio, fin, moneda)),
        Decimal(0),
    )
    saldo_por_pagar = (
        db.scalar(
            select(func.coalesce(func.sum(Gasto.costo_total - Gasto.monto_pagado), 0)).where(
                Gasto.empresa_id == empresa_id,
                Gasto.fecha >= inicio,
                Gasto.fecha < fin,
                Gasto.moneda == moneda,
                Gasto.monto_pagado < Gasto.costo_total,
            )
        )
        or Decimal(0)
    )

    return CuentasCobrarPagarOut(
        periodo=periodo,
        moneda=moneda,
        total_ventas=total_ventas,
        saldo_por_cobrar=saldo_por_cobrar,
        saldo_por_pagar=saldo_por_pagar,
        igv_ventas=igv_ventas,
        igv_compras=igv_compras,
        igv_diferencia=igv_diferencia,
    )


def _ventas_pendientes(
    db: Session, empresa_id: uuid.UUID, inicio, fin, moneda: str
) -> list[CuentaPorCobrarItem]:
    filtro_moneda = Venta.total_soles > 0 if moneda == "PEN" else Venta.total_dolares > 0
    ventas = db.scalars(
        select(Venta)
        .where(
            Venta.empresa_id == empresa_id,
            Venta.fecha >= inicio,
            Venta.fecha < fin,
            filtro_moneda,
        )
        .order_by(Venta.fecha.desc())
    )
    items: list[CuentaPorCobrarItem] = []
    for v in ventas:
        if moneda == "PEN":
            abonado = v.monto_abonado or Decimal(0)
            saldo = v.total_soles - abonado
            total = v.total_soles
        else:
            # No se rastrea un abono en dolares independiente: una venta en
            # dolares se considera por cobrar por su total hasta que se
            # construya ese seguimiento (ver nota en CLAUDE.md/monto_abonado).
            abonado = Decimal(0)
            saldo = v.total_dolares
            total = v.total_dolares
        if saldo <= 0:
            continue
        items.append(
            CuentaPorCobrarItem(
                venta_id=v.id,
                fecha=v.fecha,
                cliente_nombre=v.cliente_nombre,
                cliente_documento=v.cliente_documento,
                vendedor_nombre=v.vendedor.full_name,
                total=total,
                abonado=abonado,
                saldo=saldo,
            )
        )
    return items


@router.get("/cobrar-pagar/por-cobrar", response_model=list[CuentaPorCobrarItem])
def detalle_por_cobrar(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CuentaPorCobrarItem]:
    _, inicio, fin = rango_mes(mes)
    return _ventas_pendientes(db, empresa_id, inicio, fin, moneda)


@router.get("/cobrar-pagar/por-pagar", response_model=list[CuentaPorPagarItem])
def detalle_por_pagar(
    mes: str | None = None,
    moneda: str = Query("PEN", pattern="^(PEN|USD)$"),
    empresa_id: uuid.UUID = Depends(require_empresa),
    db: Session = Depends(get_db),
) -> list[CuentaPorPagarItem]:
    _, inicio, fin = rango_mes(mes)
    gastos = db.scalars(
        select(Gasto)
        .where(
            Gasto.empresa_id == empresa_id,
            Gasto.fecha >= inicio,
            Gasto.fecha < fin,
            Gasto.moneda == moneda,
            Gasto.monto_pagado < Gasto.costo_total,
        )
        .order_by(Gasto.fecha.desc())
    )
    return [
        CuentaPorPagarItem(
            gasto_id=g.id,
            fecha=g.fecha,
            tipo_gasto_nombre=g.tipo_gasto.nombre,
            proveedor_colaborador=g.proveedor_colaborador,
            costo_total=g.costo_total,
            monto_pagado=g.monto_pagado,
            saldo=g.costo_total - g.monto_pagado,
        )
        for g in gastos
    ]
