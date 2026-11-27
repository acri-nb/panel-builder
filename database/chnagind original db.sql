
SELECT current_database();



BEGIN;

ALTER TABLE panels
    ADD COLUMN source_panel_id INTEGER,
    ADD COLUMN child_panel_ids INTEGER[];

ALTER TABLE panel_gene
    ADD COLUMN origin_panel_id INTEGER;

ALTER TABLE panel_str
    ADD COLUMN origin_panel_id INTEGER;




SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (
      (table_name = 'panels'
       AND column_name IN ('source_panel_id', 'child_panel_ids'))
      OR
      (table_name IN ('panel_gene', 'panel_str')
       AND column_name = 'origin_panel_id')
  )
ORDER BY table_name, column_name;



COMMIT;


SELECT
    conrelid::regclass AS referencing_table,
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE contype = 'f'
  AND confrelid = 'public.panels'::regclass
ORDER BY conrelid::regclass::text;


SELECT COUNT(*) AS aus_panel_count
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp AUS';







BEGIN;

-- Remember exactly which AUS panels we are deleting.
CREATE TEMP TABLE aus_panels_to_delete ON COMMIT DROP AS
SELECT p.panel_id
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp AUS';

-- Remove changes linked to AUS panels or their versions.
DELETE FROM panel_changes
WHERE panel_id IN (
    SELECT panel_id FROM aus_panels_to_delete
)
OR change_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM aus_panels_to_delete
    )
);

-- Remove version contents.
DELETE FROM panel_version_gene
WHERE panel_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM aus_panels_to_delete
    )
);

DELETE FROM panel_version_str
WHERE panel_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM aus_panels_to_delete
    )
);

DELETE FROM panel_versions
WHERE panel_id IN (
    SELECT panel_id FROM aus_panels_to_delete
);

-- Remove current gene and STR associations.
DELETE FROM panel_gene
WHERE panel_id IN (
    SELECT panel_id FROM aus_panels_to_delete
);

DELETE FROM panel_str
WHERE panel_id IN (
    SELECT panel_id FROM aus_panels_to_delete
);

-- Remove AUS panels.
DELETE FROM panels
WHERE panel_id IN (
    SELECT panel_id FROM aus_panels_to_delete
);

-- Verify: this should return 0.
SELECT COUNT(*) AS remaining_aus_panels
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp AUS';

COMMIT;

SELECT
    p.panel_id,
    p.panel_name,
    p.source_panel_id,
    p.child_panel_ids
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp AUS'
ORDER BY p.panel_id
LIMIT 200;



BEGIN;

CREATE TEMP TABLE uk_panels_to_delete ON COMMIT DROP AS
SELECT p.panel_id
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp UK';

DELETE FROM panel_changes
WHERE panel_id IN (
    SELECT panel_id FROM uk_panels_to_delete
)
OR change_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM uk_panels_to_delete
    )
);

DELETE FROM panel_version_gene
WHERE panel_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM uk_panels_to_delete
    )
);

DELETE FROM panel_version_str
WHERE panel_version_id IN (
    SELECT panel_version_id
    FROM panel_versions
    WHERE panel_id IN (
        SELECT panel_id FROM uk_panels_to_delete
    )
);

DELETE FROM panel_versions
WHERE panel_id IN (
    SELECT panel_id FROM uk_panels_to_delete
);

DELETE FROM panel_gene
WHERE panel_id IN (
    SELECT panel_id FROM uk_panels_to_delete
);

DELETE FROM panel_str
WHERE panel_id IN (
    SELECT panel_id FROM uk_panels_to_delete
);

DELETE FROM panels
WHERE panel_id IN (
    SELECT panel_id FROM uk_panels_to_delete
);

SELECT COUNT(*) AS remaining_uk_panels
FROM panels p
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp UK';
COMMIT;





SELECT pc.change_id, pc.status, pc.proposed_data
FROM panel_changes pc
LEFT JOIN panel_versions pv
    ON pv.panel_version_id = pc.change_version_id
JOIN panels p
    ON p.panel_id = pc.panel_id
    OR p.panel_id = pv.panel_id
JOIN sources s ON s.source_id = p.source_id
WHERE s.source_name = 'PanelApp UK';

SELECT change_id, status, proposed_data
FROM panel_changes
WHERE proposed_data ->> 'source' = 'PanelApp UK'
   OR proposed_data -> 'data' ->> 'source' = 'PanelApp UK';