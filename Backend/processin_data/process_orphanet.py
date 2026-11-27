import json
from pathlib import Path


def normalize_disease(raw):
    epidemiology = raw["epidemiology"]["data"]["results"]
    history_response = raw.get("natural_history")
    natural_history = (
        history_response["data"]["results"] if history_response else {}
    )

    return {
        "orpha_code": raw["orpha_code"],
        "source": raw["source"],
        "orphanet_url": epidemiology.get("OrphanetURL"),
        "disease_name": epidemiology["Preferred term"],
        "epidemiology": epidemiology.get("Prevalence") or [],
        "age_at_onset": natural_history.get("AverageAgeOfOnset") or [],
        "disorder_group": (
            natural_history.get("DisorderGroup")
            or epidemiology.get("DisorderGroup")
        ),
        "inheritance": natural_history.get("TypeOfInheritance") or [],
    }


def main():
    input_path = Path(r"C:\Users\emnab\Desktop\Panelbuilder\Backend\raw_data\all_raw_data\orphanet.json")
    output_path = Path(r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\orphanet_processed.json")

    with input_path.open(encoding="utf-8") as file:
        raw_records = json.load(file)

    normalized_records = [normalize_disease(record) for record in raw_records]

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(normalized_records, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Saved {len(normalized_records)} records to {output_path}")


if __name__ == "__main__":
    main()