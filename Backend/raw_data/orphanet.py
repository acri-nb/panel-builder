import argparse
import json
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.orphadata.com"
EPIDEMIOLOGY_PATH = "/rd-epidemiology/orphacodes"
NATURAL_HISTORY_PATH = "/rd-natural_history/orphacodes"


def fetch_response(session, path, *, allow_missing=False):
    response = session.get(
        f"{BASE_URL}{path}",
        params={"lang": "en"},
        timeout=(10, 60),
    )

    if allow_missing and response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def acquire_orphanet(output_path, limit=None):
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={"GET"},
        respect_retry_after_header=True,
    )

    with requests.Session() as session:
        session.mount(BASE_URL + "/", HTTPAdapter(max_retries=retries))

        disease_list = fetch_response(session, EPIDEMIOLOGY_PATH)
        diseases_by_code = {
            disease["ORPHAcode"]: disease
            for disease in disease_list["data"]["results"]
        }
        selected_diseases = list(diseases_by_code.values())[:limit]

        if not selected_diseases:
            raise ValueError("The epidemiology endpoint returned no diseases.")

        print(f"Found {len(diseases_by_code)} distinct ORPHAcodes.")
        print(f"Fetching details for {len(selected_diseases)} diseases.")

        records = []
        for index, disease in enumerate(selected_diseases, start=1):
            code = disease["ORPHAcode"]
            print(
                f"[{index}/{len(selected_diseases)}] ORPHA:{code}",
                flush=True,
            )

            epidemiology = fetch_response(
                session, f"{EPIDEMIOLOGY_PATH}/{code}"
            )
            natural_history = fetch_response(
                session,
                f"{NATURAL_HISTORY_PATH}/{code}",
                allow_missing=True,
            )

            records.append({
                "disease_list_entry": disease,
                "source": "Orphanet",
                "epidemiology": epidemiology,
                "natural_history": natural_history,
            })

    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)
        file.write("\n")
    temporary_path.replace(output_path)

    print(f"Saved {len(records)} diseases to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acquire raw Orphadata records.")
    parser.add_argument("--limit", type=int, help="Fetch only the first N diseases.")
    parser.add_argument("--output", type=Path, default=Path("orphanet_raw.json"))
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    acquire_orphanet(args.output, args.limit)