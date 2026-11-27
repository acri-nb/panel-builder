import json
import psycopg2
from pathlib import Path
from datetime import datetime



# Database connection

conn = psycopg2.connect(
    dbname="Panelbuilder",
    user="postgres",
    host="localhost",
    port="5432"
)

cursor = conn.cursor()


# Paths

json_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\blueprint_processednew.json"
)

# -----------------------------
# Helper functions
# -----------------------------

def get_source_id(source_name):
    cursor.execute(
        """
        SELECT source_id 
        FROM sources
        WHERE source_name = %s;
        """,
        (source_name,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]

    raise Exception(f"Source {source_name} not found")


def insert_version(source_id, panel):

    cursor.execute(
        """
        INSERT INTO versions
        (
            source_id,
            version_number,
            last_updated
            
        )
        VALUES (%s,%s,%s)
        RETURNING version_id
        """,
        (
            source_id,
            panel.get("version"),
            panel.get("last_updated")
        )
    )

    return cursor.fetchone()[0]


def get_or_create_gene(gene_symbol):

    cursor.execute(
        """
        SELECT gene_id
        FROM genes
        WHERE gene_symbol = %s
        """,
        (gene_symbol,)
    )

    result = cursor.fetchone()

    if result:
        return result[0]


    cursor.execute(
        """
        INSERT INTO genes(gene_symbol)
        VALUES (%s)
        RETURNING gene_id
        """,
        (gene_symbol,)
    )

    return cursor.fetchone()[0]



def insert_panel(panel, source_id, version_id):

    relevant = panel.get("relevant_diseases")

    if relevant:
        relevant = ", ".join(relevant)

    cursor.execute(
        """
        INSERT INTO panels
        (
            panel_name,
            disease_group,
            disease_subgroup,
            relevant_diseases,
            source_id,
            version_id
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING panel_id
        """,
        (
            panel.get("panel_name"),
            panel.get("disease_group"),
            panel.get("disease_sub_group"),
            relevant,
            source_id,
            version_id
        )
    )

    return cursor.fetchone()[0]



def insert_panel_gene(panel_id, gene_id, gene):

    cursor.execute(
        """
        INSERT INTO panel_gene
        (
            panel_id,
            gene_id,
            confidence_level,
            phenotypes
        )
        VALUES (%s,%s,%s,%s)
        """,
        (
            panel_id,
            gene_id,
            gene.get("confidence_level"),
            gene.get("phenotypes")
        )
    )



def insert_str(panel_id, str_data):

    gene_symbol = str_data.get("gene_symbol")

    gene_id = get_or_create_gene(gene_symbol)


    cursor.execute(
        """
        INSERT INTO strs
        (
            entity_name,
            gene_id,
            confidence_level,
            phenotypes,
            repeated_sequence
        )
        VALUES (%s,%s,%s,%s,%s)
        RETURNING str_id
        """,
        (
            str_data.get("entity_name"),
            gene_id,
            str_data.get("confidence_level"),
            str_data.get("phenotypes"),
            str_data.get("repeated_sequence")
        )
    )

    str_id = cursor.fetchone()[0]


    cursor.execute(
        """
        INSERT INTO panel_str
        (
            panel_id,
            str_id
        )
        VALUES (%s,%s)
        """,
        (
            panel_id,
            str_id
        )
    )


# -----------------------------
# Main loading
# -----------------------------

with open(json_file, "r", encoding="utf-8") as file:
    panels = json.load(file)


source_id = get_source_id("Blueprint Genetics")


for panel in panels:

    print("Loading:", panel["panel_name"])


    version_id = insert_version(
        source_id,
        panel
    )


    panel_id = insert_panel(
        panel,
        source_id,
        version_id
    )


    for gene in panel.get("genes", []):

        gene_id = get_or_create_gene(
            gene["gene_symbol"]
        )


        insert_panel_gene(
            panel_id,
            gene_id,
            gene
        )


    for str_data in panel.get("strs", []):

        insert_str(
            panel_id,
            str_data
        )


conn.commit()

cursor.close()
conn.close()


print("Blueprint Genetics loading finished successfully")