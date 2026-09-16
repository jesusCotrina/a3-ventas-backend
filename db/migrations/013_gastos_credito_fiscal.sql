-- 013_gastos_credito_fiscal.sql
-- Cada gasto puede marcar si su comprobante da derecho a credito fiscal de
-- IGV (la compra trae IGV discriminado en una factura, no todos los gastos
-- lo tienen -- p.ej. un colaborador informal sin factura). Antes,
-- Cuentas > Cuentas por cobrar y pagar sumaba el 18%% de TODOS los gastos
-- operativos como credito fiscal sin distinguir esto; ahora ese calculo
-- solo suma los gastos marcados aqui.
--
-- Nace en true (el comportamiento anterior, todo sumaba) para no alterar
-- retroactivamente el credito fiscal ya calculado de gastos existentes.

BEGIN;

ALTER TABLE gastos
    ADD COLUMN aplica_credito_fiscal boolean NOT NULL DEFAULT true;

INSERT INTO schema_migrations (version) VALUES ('013_gastos_credito_fiscal');

COMMIT;
