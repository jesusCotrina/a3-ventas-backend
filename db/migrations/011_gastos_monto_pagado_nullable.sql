-- 011_gastos_monto_pagado_nullable.sql
-- Este proyecto (Kaudal / a3-gestion-ventas-app) y el proyecto original
-- a1-gestion-talleres-app comparten, por un choque de nombres accidental,
-- el mismo contenedor Docker y el mismo volumen de Postgres: ambos tienen
-- su backend en una carpeta llamada "back" con el mismo docker-compose.yml
-- (container_name: taller_db, volumen taller_pgdata) y Docker Compose
-- deriva el nombre del volumen del nombre de esa carpeta -> mismo volumen
-- ("back_taller_pgdata") para los dos proyectos. No son bases de datos
-- separadas.
--
-- La migracion 010_cuentas.sql dejo `gastos.monto_pagado` como NOT NULL
-- sin DEFAULT. El backend de a1-gestion-talleres-app (que no conoce esta
-- columna) inserta gastos sin especificarla, lo que rompe su endpoint
-- POST /gastos contra esta base compartida. Se relaja a nullable: NULL
-- significa "pagado por completo" (igual que si monto_pagado == costo_total),
-- que es como toda la app interpreta ahora los gastos creados por codigo
-- que no conoce este campo.

BEGIN;

ALTER TABLE gastos
    ALTER COLUMN monto_pagado DROP NOT NULL;

INSERT INTO schema_migrations (version) VALUES ('011_gastos_monto_pagado_nullable');

COMMIT;
