import csv
import json
from pathlib import Path
from datetime import datetime

def csv_to_json(csv_file, json_file):
    data = []

    with open(csv_file, "r", encoding="utf-8-sig", newline="") as file:

        reader = csv.reader(file)

        headers = None

        for row in reader:

            # Find header
            if headers is None:
                if "sgc_id" in row:
                    headers = row
                continue

            # Skip empty lines
            if not row:
                continue

            # Skip text lines / malformed rows
            if len(row) != len(headers):
                continue

            # Create dictionary
            record = dict(zip(headers, row))

            data.append({
                "panel_id": None,
                "panel_name": record["disease_title"].strip(),
                "disease_group": None,
                "disease_sub_group": None,
                "relevant_diseases": [
                    record["disease_title"].strip()
                ],    
               "source": "GenCC",
                "version": record["version_number"],
                "last_updated": record["submitted_as_date"].split(" ")[0],
                "processed_date": datetime.today().strftime("%Y-%m-%d"),
                "genes": [{
                    "gene_symbol": record["gene_symbol"],
                    "confidence_level": record["classification_title"].strip(),
                    "phenotypes": None,
                    "moi": record["moi_title"].strip(),
                    "submitter": record["submitter_title"].strip(),
                     "sgc_id": record["sgc_id"].strip(),
                    }],
                "strs": []
                           })


    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

csv_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\Gencc-data-1.csv"
)

json_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\Gencc_processed_sgcid_added.json"
)

csv_to_json(csv_file, json_file)