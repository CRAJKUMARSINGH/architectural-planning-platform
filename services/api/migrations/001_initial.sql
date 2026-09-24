-- E02 initial metadata migration.
-- The canonical migration body is kept in schema.sql so local SQLite and
-- deployed PostgreSQL environments share the same table contract.
\i services/api/schema.sql
