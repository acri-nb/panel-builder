import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm


raw_folder = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\blueprint_genetics_UPDATED"
)

output_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\blueprint_processednew.json"
)


def process_gene(gene):

    phenotypes = gene.get("phenotypes")

    if phenotypes:
        phenotypes = [
            p.strip()
            for p in phenotypes.split(",")
            if p.strip()
        ]
    else:
        phenotypes = None


    return {
        "gene_symbol": gene.get("gene_symbol"),

        "confidence_level": None,

        "phenotypes": phenotypes
    }



def process_panel(panel):

    return {

        "panel_id": None,

        "panel_name": panel.get("panel_name"),

        "disease_group": panel.get("category"),

        "disease_sub_group": None,

        "relevant_diseases": None,

        "source": panel.get("source"),

        "version": None,

        "last_updated": panel.get("content_last_modified"),

        "processed_date": datetime.today().strftime("%Y-%m-%d"),

        "genes": [
            process_gene(gene)
            for gene in panel.get("genes", [])
        ],

        "strs": []

    }



# Get all Blueprint panel files
files = list(raw_folder.glob("*.json"))


processed_panels = []


for file in tqdm(files, desc="Processing Blueprint panels"):

    with open(file, "r", encoding="utf-8") as f:

        panel = json.load(f)


    processed_panel = process_panel(panel)

    processed_panels.append(processed_panel)



# Save all processed panels together
with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        processed_panels,
        f,
        indent=4,
        ensure_ascii=False
    )


print(f"Processed {len(processed_panels)} Blueprint panels")