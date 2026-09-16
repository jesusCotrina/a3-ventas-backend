-- 012_cobros_venta.sql
-- Historial de cobros de una venta (pagos parciales), para que el Flujo de
-- caja muestre las "entradas" del mes en que el dinero realmente se cobro,
-- no el mes en que se realizo la venta.
--
-- Ejemplo: una venta de S/135 el 15 de marzo se paga con un abono de S/100
-- ese mismo dia (queda un saldo por cobrar de S/35, ver Cuentas por cobrar).
-- Si el cliente paga esos S/35 recien en abril, ese cobro debe sumar a las
-- entradas de abril, no a las de marzo. Por eso cada abono se registra como
-- una fila aparte con su propia fecha, en vez de solo actualizar
-- ventas.monto_abonado.
--
-- Solo se usa para ventas en soles (moneda PEN): igual que
-- ventas.monto_abonado, no existe todavia seguimiento de abonos en dolares
-- independiente del total (ver nota en app/models/venta.py).

BEGIN;

CREATE TABLE cobros_venta (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id  uuid        NOT NULL REFERENCES empresas(id),
    venta_id    uuid        NOT NULL REFERENCES ventas(id),
    usuario_id  uuid        NOT NULL REFERENCES users(id),
    fecha       date        NOT NULL,
    monto       numeric(10, 2) NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX cobros_venta_venta_id_idx ON cobros_venta (venta_id);
CREATE INDEX cobros_venta_empresa_fecha_idx ON cobros_venta (empresa_id, fecha);

-- Backfill: el abono ya registrado en cada venta existente se toma como
-- cobrado el mismo dia de la venta (es la unica fecha que se conoce para
-- ese dinero, al no haberse rastreado antes de esta migracion).
INSERT INTO cobros_venta (id, empresa_id, venta_id, usuario_id, fecha, monto, created_at)
SELECT gen_random_uuid(), v.empresa_id, v.id, v.vendedor_id, v.fecha, v.monto_abonado, v.created_at
FROM ventas v
WHERE v.monto_abonado IS NOT NULL AND v.monto_abonado > 0;

INSERT INTO schema_migrations (version) VALUES ('012_cobros_venta');

COMMIT;
