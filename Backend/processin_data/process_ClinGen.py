import csv
import json
from pathlib import Path
from datetime import datetime


def csv_to_json(csv_file, json_file):
    data = []

    with open(csv_file, "r", encoding="utf-8-sig", newline="") as file:

        reader = csv.reader(file)

        # Find the header row
        for row in reader:
            if "GENE SYMBOL" in row:
                headers = row
                break

        # Skip +++++ separator row
        next(reader)

        # Process data rows
        for row in reader:

            if not row:
                continue

            record = dict(zip(headers, row))

            data.append({

                "panel_id": None,
                "panel_name":  record["DISEASE LABEL"].strip(),
                "disease_group": None,
                "disease_sub_group": None,
                "relevant_diseases": [
                    record["DISEASE LABEL"].strip(),
                ],
                "source": "ClinGen",
                "version": None,
                "last_updated": record["CLASSIFICATION DATE"].split("T")[0],
                "processed_date": "2026-07-24",
                "genes":[{
                    "gene_symbol": record["GENE SYMBOL"].strip(),
                    "confidence_level": record["CLASSIFICATION"].strip(),
                    "phenotypes": None,
                    "moi": record["MOI"].strip(),
                    "assertion_url":record["ONLINE REPORT"].strip(),

                }],
                "strs": []
                })

    with open(json_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


csv_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\Clingen_data_1.csv"
)

json_file = Path(
    r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\ClinGen_processed_url_added.json"
)

csv_to_json(csv_file, json_file)