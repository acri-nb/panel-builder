
/*creating tables for : source, versions, panels,genes,panel_genes, strs,panel_str*/
CREATE TABLE sources (
    source_id SERIAL PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE
);

CREATE TABLE versions (
    version_id SERIAL PRIMARY KEY,

    source_id INTEGER REFERENCES sources(source_id),

    version_number TEXT,
    last_updated DATE
);

CREATE TABLE panels (
    panel_id SERIAL PRIMARY KEY,

    panel_name TEXT NOT NULL,

    disease_group TEXT,
    disease_subgroup TEXT,
	relevant_diseases TEXT,

    source_id INTEGER REFERENCES sources(source_id),

    version_id INTEGER REFERENCES versions(version_id)
);


CREATE TABLE genes (
    gene_id SERIAL PRIMARY KEY,

    gene_symbol TEXT NOT NULL UNIQUE
);

CREATE TABLE panel_gene (
    panel_gene_id SERIAL PRIMARY KEY,

    panel_id INTEGER REFERENCES panels(panel_id),

    gene_id INTEGER REFERENCES genes(gene_id),

    confidence_level TEXT,

    phenotypes TEXT[]
);

CREATE TABLE strs (
    str_id SERIAL PRIMARY KEY,

    entity_name TEXT,

    gene_id INTEGER REFERENCES genes(gene_id),

    confidence_level TEXT,

    phenotypes TEXT[],

    repeated_sequence TEXT
);

CREATE TABLE panel_str (
    panel_str_id SERIAL PRIMARY KEY,

    panel_id INTEGER REFERENCES panels(panel_id),

    str_id INTEGER REFERENCES strs(str_id)
);


SELECT table_name
FROM information_schema.tables
WHERE table_schema='public';


/*inserting sources into sources table*/
INSERT INTO sources (source_name)
VALUES
('PanelApp AUS'),
('PanelApp UK'),
('Blueprint Genetics'),
('Ontario Health'),
('GenCC'),
('ClinGen');


INSERT INTO sources (source_name)
VALUES ('Laboratory');
