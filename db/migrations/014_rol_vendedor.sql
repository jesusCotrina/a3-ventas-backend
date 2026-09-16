-- 014_rol_vendedor.sql
-- El rol "mecanico" (id 3, sembrado por 001_init.sql) pasa a llamarse
-- "vendedor": la app dejo de ser exclusiva de talleres mecanicos y ese
-- rol siempre fue, en la practica, quien vende (ver _VENDEDORES_ROLES en
-- ventas.py, que ya lo trataba asi desde antes). No se toca el id (3) ni
-- las filas de `users` que ya apuntan a el via role_id: solo cambia como
-- se llama.

BEGIN;

UPDATE roles SET code = 'vendedor', name = 'Vendedor' WHERE code = 'mecanico';

INSERT INTO schema_migrations (version) VALUES ('014_rol_vendedor');

COMMIT;
