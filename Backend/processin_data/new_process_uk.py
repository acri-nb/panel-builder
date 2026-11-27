import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm


raw_folder = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\new_detailled_panel_uk"
)

output_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\new_panelapp_uk_processed.json"
)


def process_gene(gene):

    gene_data = gene.get("gene_data", {})
    origin_panel = gene.get("panel") or {}

    return {
        "gene_symbol": gene_data.get("gene_symbol"),
        
        "origin_panel_id": origin_panel.get("id"),

        "confidence_level": gene.get("confidence_level"),

        "phenotypes": gene.get("phenotypes", [])
    }



def process_str(str_entity):

    gene_data = str_entity.get("gene_data", {})
    origin_panel = str_entity.get("panel") or {}

    return {
        "entity_name": str_entity.get("entity_name"),

        "gene_symbol": gene_data.get("gene_symbol"),

        "origin_panel_id": origin_panel.get("id"),

        "confidence_level": str_entity.get("confidence_level"),

        "phenotypes": str_entity.get("phenotypes", []),

        "repeated_sequence": str_entity.get("repeated_sequence")
    }



def process_panel(panel):

    processed_panel = {

        "source_panel_id": panel.get("id"),

        "panel_name": panel.get("name"),

        "disease_group": panel.get("disease_group"),

        "disease_sub_group": panel.get("disease_sub_group"),

        "relevant_diseases": panel.get("relevant_disorders", []),

        "source": "PanelApp UK",

        "version": panel.get("version"),

        "last_updated": None,


        "processed_date": datetime.today().strftime("%Y-%m-%d"),

        "genes": [],

        "strs": []
    }


    # genes
    for gene in panel.get("genes", []):

        if gene.get("entity_type") == "gene":

            processed_panel["genes"].append(
                process_gene(gene)
            )


    # strs
    for str_entity in panel.get("strs", []):

        if str_entity.get("entity_type") == "str":

            processed_panel["strs"].append(
                process_str(str_entity)
            )


    return processed_panel



# Get all panel files
files = list(raw_folder.glob("panel_uk_*.json"))


processed_panels = []


for file in tqdm(files, desc="Processing Panels"):

    with open(file, "r", encoding="utf-8") as f:

        panel = json.load(f)


    processed_panel = process_panel(panel)


    processed_panels.append(processed_panel)



# Save all processed panels in one file
with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        processed_panels,
        f,
        indent=4,
        ensure_ascii=False
    )


print(f"Processed {len(processed_panels)} panels")
