-- migration_v31.sql: Track template image on nodes

ALTER TABLE nodes ADD COLUMN template_id VARCHAR(36);
-- FOREIGN KEY defined in db.py, sqlite might not enforce it on ALTER but tracking is essential.
