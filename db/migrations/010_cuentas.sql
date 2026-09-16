-- 010_cuentas.sql
-- Modulo Cuentas: estado de resultados, flujo de caja y cuentas por
-- cobrar/pagar, calculados a partir de ventas y gastos.
--
-- - tipos_gasto.categoria clasifica cada tipo de gasto para el estado de
--   resultados: 'operativo' (default, tambien es lo que se toma como
--   "compras y gastos" del flujo de caja y de la base del IGV),
--   'financiero_ingreso' o 'financiero_egreso'.
-- - gastos.monto_pagado espeja gastos.costo_total al momento de crear el
--   registro (todo gasto nace "pagado al contado", igual que el
--   comportamiento actual): si despues se reduce desde el formulario,
--   la diferencia es lo que "Cuentas por pagar" muestra como pendiente.
-- - cuentas_parametros guarda los dos campos editables por el usuario que
--   no se derivan de ventas/gastos: el saldo inicial de caja y el impuesto
--   del estado de resultados, por empresa + periodo (mes) + moneda.

BEGIN;

ALTER TABLE tipos_gasto
    ADD COLUMN categoria text NOT NULL DEFAULT 'operativo';

ALTER TABLE tipos_gasto
    ADD CONSTRAINT tipos_gasto_categoria_check
    CHECK (categoria IN ('operativo', 'financiero_ingreso', 'financiero_egreso'));

ALTER TABLE gastos
    ADD COLUMN monto_pagado numeric(10, 2);

UPDATE gastos SET monto_pagado = costo_total WHERE monto_pagado IS NULL;

ALTER TABLE gastos
    ALTER COLUMN monto_pagado SET NOT NULL;

CREATE TABLE cuentas_parametros (
    empresa_id     uuid        NOT NULL REFERENCES empresas(id),
    periodo        text        NOT NULL,
    moneda         text        NOT NULL,
    saldo_inicial  numeric(12, 2) NOT NULL DEFAULT 0,
    impuesto       numeric(12, 2) NOT NULL DEFAULT 0,
    updated_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (empresa_id, periodo, moneda)
);

INSERT INTO schema_migrations (version) VALUES ('010_cuentas');

COMMIT;
