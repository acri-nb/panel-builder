import json
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def extract_genes(gene_string):

    if not gene_string:
        return []

    genes = []

    for gene in gene_string.split(","):

        gene = gene.strip()

        if gene:

            genes.append({
                "gene_symbol": gene,

                "confidence_level": None,

                "phenotypes": None
            })

    return genes



def process_ontario_record(record):

    url = record.get("url") or ""
    query_parameters = parse_qs(urlparse(url).query)
    ontario_id = query_parameters.get("cf", [None])[0]

    return {

        "panel_id": None,

        "panel_name": record.get("title"),

        "disease_group": record.get("category"),

        "disease_sub_group": record.get("subcategory"),
        "lab_name": record.get("lab"),
        "ontario_id": ontario_id,


        "relevant_diseases": [
          disease.strip()
          for disease in (record.get("disease_condition") or "").split(",")
          if disease.strip()
        ],

        "source": record.get("source"),

        "version": None,

        "last_updated": record.get("last_updated"),

        "processed_date": datetime.today().strftime("%Y-%m-%d"),


        "genes": extract_genes(
            record.get("gene_platform_region")
        ),

        "strs": []
    }



# -----------------------------
# Process file
# -----------------------------

input_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\ontario_health_details.json"
)

output_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\newontario_processed14_09_2026.json"
)


with open(input_file, "r", encoding="utf-8") as f:
    raw_data = json.load(f)


processed_data = []


for record in raw_data:

    processed_data.append(
        process_ontario_record(record)
    )


with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        processed_data,
        f,
        indent=4,
        ensure_ascii=False
    )


print(
    f"Processed {len(processed_data)} Ontario records"
)