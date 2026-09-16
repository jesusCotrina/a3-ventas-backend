-- 015_empresas_plan.sql
-- Plan comercial de cada empresa (free / basico / premium), usado para
-- limitar cuantos usuarios activos puede tener (ver empresas.py:
-- _LIMITE_USUARIOS_POR_PLAN) y, si es "free", hasta cuando dura el acceso
-- de nivel premium sin costo.
--
-- `plan_vence_en` es NULL por defecto (sin fecha de vencimiento) para no
-- afectar retroactivamente a las empresas que ya existian antes de este
-- cambio: quedan en plan "free" pero sin vencimiento hasta que un
-- super_admin les asigne uno desde Administracion. Las empresas nuevas
-- (crear_empresa en empresas.py) si arrancan con una fecha de vencimiento
-- calculada (hoy + 2 meses por defecto), que luego se puede editar
-- libremente por empresa -- acortarla, extenderla o quitarla.

BEGIN;

ALTER TABLE empresas
    ADD COLUMN plan text NOT NULL DEFAULT 'free',
    ADD CONSTRAINT empresas_plan_check CHECK (plan IN ('free', 'basico', 'premium'));

ALTER TABLE empresas
    ADD COLUMN plan_vence_en date;

INSERT INTO schema_migrations (version) VALUES ('015_empresas_plan');

COMMIT;
