
SELECT *
FROM sources;

/*see the panels table head 10 */
SELECT * FROM panels LIMIT 10;
/*see the number of genesin genes table*/
SELECT COUNT(*) FROM genes;
/*see head 10 of genes table*/
SELECT * FROM genes LIMIT 10;
/*count of panel gene*/
SELECT COUNT(*) FROM panel_gene;
/*see head 50 of panel gene*/
SELECT * FROM panel_gene LIMIT 50;

/*see which panels have the gene COL7A1, show the panel , disease , gene symbol, confidence level*/
SELECT 
    panels.panel_name,
    panels.disease_group,
    genes.gene_symbol,
    panel_gene.confidence_level
FROM genes
JOIN panel_gene
ON genes.gene_id = panel_gene.gene_id
JOIN panels
ON panel_gene.panel_id = panels.panel_id
WHERE genes.gene_symbol = 'COL7A1';

/*see versions of panels*/
SELECT
    panels.panel_name,
    versions.version_number,
    versions.last_updated
FROM panels
JOIN versions
ON panels.version_id = versions.version_id
LIMIT 20;


/*see from strs table head 20*/
SELECT * FROM strs LIMIT 20;

/*see the panel name , str, confidence level , repeated sequence*/
SELECT
    panels.panel_name,
    strs.entity_name,
    genes.gene_symbol,
    strs.confidence_level,
    strs.repeated_sequence
FROM panel_str
JOIN panels
ON panel_str.panel_id = panels.panel_id
JOIN strs
ON panel_str.str_id = strs.str_id
JOIN genes
ON strs.gene_id = genes.gene_id;

/*see relevant diseases*/
SELECT 
    panel_name,
    relevant_diseases
FROM panels
LIMIT 20;

/*seeing a specific panel ,and its relevant diseases*/
SELECT 
    panel_name,
    relevant_diseases
FROM panels
WHERE panel_name = 'Epidermolysis bullosa';

/*see panel counts*/
SELECT COUNT(*) FROM panels;

/*see number of panels from just panelapp AUS source*/
SELECT 
    COUNT(*)
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp AUS'
);

/*see number of panels in panelapp uk */
SELECT COUNT(*)
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp UK'
);

/*see the panel metadata */
SELECT
    panel_name,
    disease_group,
    disease_subgroup,
    relevant_diseases
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp UK'
)
LIMIT 10;

/*check versions*/
SELECT
    p.panel_name,
    v.version_number,
    v.last_updated
FROM panels p
JOIN versions v
ON p.version_id = v.version_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp UK'
)
LIMIT 10;


/*check genes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.confidence_level
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp UK'
)
LIMIT 20;

/*check phenotypes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.phenotypes
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.panel_name = 'Thoracic aortic aneurysm or dissection'
AND g.gene_symbol = 'ABL1';

/*check str*/
SELECT
    p.panel_name,
    s.entity_name,
    g.gene_symbol,
    s.confidence_level,
    s.repeated_sequence
FROM panel_str ps
JOIN panels p
ON ps.panel_id = p.panel_id
JOIN strs s
ON ps.str_id = s.str_id
JOIN genes g
ON s.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'PanelApp UK'
)
LIMIT 20;

/*check no duplicate genes*/
SELECT
    gene_symbol,
    COUNT(*)
FROM genes
GROUP BY gene_symbol
HAVING COUNT(*) > 1;


/*checking counts of the data*/
SELECT 
    source_name,
    COUNT(*)
FROM panels
JOIN sources USING(source_id)
GROUP BY source_name;

/*see sources*/
SELECT *
FROM sources;


/*see the panel metadata */
SELECT
    panel_name,
    disease_group,
    disease_subgroup,
    relevant_diseases
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'Blueprint Genetics'
)
LIMIT 10;

/*check versions*/
SELECT
    p.panel_name,
    v.version_number,
    v.last_updated
FROM panels p
JOIN versions v
ON p.version_id = v.version_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'Blueprint Genetics'
)
LIMIT 10;


/*check genes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.confidence_level
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'Blueprint Genetics'
)
LIMIT 20;

/*check phenotypes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.phenotypes
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.panel_name = 'Abnormal Genitalia/ Disorders of Sex Development Panel'
AND g.gene_symbol = 'AMH';

/*check str*/
SELECT
    p.panel_name,
    s.entity_name,
    g.gene_symbol,
    s.confidence_level,
    s.repeated_sequence
FROM panel_str ps
JOIN panels p
ON ps.panel_id = p.panel_id
JOIN strs s
ON ps.str_id = s.str_id
JOIN genes g
ON s.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'Blueprint Genetics'
)
LIMIT 20;



/*see the panel metadata */
SELECT
    panel_name,
    disease_group,
    disease_subgroup,
    relevant_diseases
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'ClinGen'
)
LIMIT 10;

/*check versions*/
SELECT
    p.panel_name,
    v.version_number,
    v.last_updated
FROM panels p
JOIN versions v
ON p.version_id = v.version_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'ClinGen'
)
LIMIT 10;


/*check genes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.confidence_level
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'ClinGen'
)
LIMIT 20;

/*check phenotypes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.phenotypes
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.panel_name = 'Charcot-Marie-Tooth disease axonal type 2N'
AND g.gene_symbol = 'AARS1';

/*check str*/
SELECT
    p.panel_name,
    s.entity_name,
    g.gene_symbol,
    s.confidence_level,
    s.repeated_sequence
FROM panel_str ps
JOIN panels p
ON ps.panel_id = p.panel_id
JOIN strs s
ON ps.str_id = s.str_id
JOIN genes g
ON s.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'ClinGen'
)
LIMIT 20;


/*see the panel metadata */
SELECT
    panel_name,
    disease_group,
    disease_subgroup,
    relevant_diseases
FROM panels
WHERE source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'GenCC'
)
LIMIT 10;

/*check versions*/
SELECT
    p.panel_name,
    v.version_number,
    v.last_updated
FROM panels p
JOIN versions v
ON p.version_id = v.version_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'GenCC'
)
LIMIT 10;


/*check genes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.confidence_level
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'GenCC'
)
LIMIT 20;

/*check phenotypes*/
SELECT
    p.panel_name,
    g.gene_symbol,
    pg.phenotypes
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
WHERE p.panel_name = 'Noonan syndrome-like disorder with loose anagen hair 1'
AND g.gene_symbol = 'SHOC2';

/*check str*/
SELECT
    p.panel_name,
    s.entity_name,
    g.gene_symbol,
    s.confidence_level,
    s.repeated_sequence
FROM panel_str ps
JOIN panels p
ON ps.panel_id = p.panel_id
JOIN strs s
ON ps.str_id = s.str_id
JOIN genes g
ON s.gene_id = g.gene_id
WHERE p.source_id = (
    SELECT source_id
    FROM sources
    WHERE source_name = 'GenCC'
)
LIMIT 20;


/*check how many records each source contributed*/
SELECT 
    s.source_name,
    COUNT(p.panel_id) AS panel_count
FROM sources s
LEFT JOIN panels p
ON s.source_id = p.source_id
GROUP BY s.source_name;

/*check genes count*/
SELECT COUNT(*) FROM genes;

/*check total panel-gene rls*/
SELECT COUNT(*) FROM panel_gene;

/*test for a single gene the panel that appears*/
SELECT
    p.panel_name,
    g.gene_symbol,
    s.source_name,
    v.version_number,
    v.last_updated,
    pg.confidence_level,
    pg.phenotypes
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
JOIN sources s
ON p.source_id = s.source_id
LEFT JOIN versions v
ON p.version_id = v.version_id
WHERE g.gene_symbol = 'ABL1';

/*test for the panel what genes it has*/
SELECT
    p.panel_name,
    g.gene_symbol,
    s.source_name
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
JOIN sources s
ON p.source_id = s.source_id
WHERE p.panel_name ILIKE '%breast%';


/*testing */

SELECT
    p.panel_name,
    g.gene_symbol,
    s.source_name,
    v.version_number,
    v.last_updated,
    pg.confidence_level
FROM panel_gene pg
JOIN panels p
ON pg.panel_id = p.panel_id
JOIN genes g
ON pg.gene_id = g.gene_id
JOIN sources s
ON p.source_id = s.source_id
LEFT JOIN versions v
ON p.version_id = v.version_id
WHERE p.panel_name ILIKE '%Charcot-Marie-Tooth%';


/*str retrieval */
SELECT
    p.panel_name,
    s.entity_name,
    g.gene_symbol,
    s.confidence_level,
    s.repeated_sequence
FROM panel_str ps
JOIN panels p
ON ps.panel_id = p.panel_id
JOIN strs s
ON ps.str_id = s.str_id
JOIN genes g
ON s.gene_id = g.gene_id;
