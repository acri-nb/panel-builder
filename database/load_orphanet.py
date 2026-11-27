import argparse
import json
from contextlib import closing
from decimal import Decimal
from getpass import getpass
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


def epidemiology_row(orpha_code, record):
    qualification = record.get("PrevalenceQualification")
    raw_value = record.get("ValMoy")

    reported_value = None
    if (
        (qualification or "").strip().casefold() != "class only"
        and raw_value not in (None, "")
    ):
        reported_value = Decimal(str(raw_value))
        if not reported_value.is_finite():
            raise ValueError(f"Invalid ValMoy for ORPHA:{orpha_code}")

    return (
        orpha_code,
        record.get("PrevalenceType"),
        qualification,
        record.get("PrevalenceGeographic"),
        record.get("PrevalenceClass"),
        reported_value,
        record.get("Source"),
        record.get("PrevalenceValidationStatus"),
    )


def load_orphanet(json_file, dbname):
    with json_file.open(encoding="utf-8") as file:
        diseases = json.load(file)

    if not isinstance(diseases, list) or not diseases:
        raise ValueError("Expected a non-empty list in the normalized JSON.")

    disease_rows = []
    epidemiology_rows = []
    seen_codes = set()

    for disease in diseases:
        code = disease["orpha_code"]
        if code in seen_codes:
            raise ValueError(f"Duplicate ORPHAcode in the JSON: {code}")
        seen_codes.add(code)

        disease_rows.append((
            code,
            disease["disease_name"],
            disease["source"],
            disease.get("orphanet_url"),
            disease.get("disorder_group"),
            disease.get("age_at_onset") or [],
            disease.get("inheritance") or [],
        ))

        for record in disease["epidemiology"]:
            epidemiology_rows.append(epidemiology_row(code, record))

    # Process disease updates in a consistent order across imports.
    disease_rows.sort(key=lambda row: row[0])

    with closing(psycopg2.connect(
        dbname=dbname,
        user="postgres",
        password=getpass("PostgreSQL password: "),
        host="localhost",
        port=5432,
    )) as conn:
        with conn, conn.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO orphanet_diseases (
                    orpha_code, disease_name, source, orphanet_url,
                    disorder_group, age_at_onset, inheritance
                )
                VALUES %s
                ON CONFLICT (orpha_code) DO UPDATE SET
                    disease_name = EXCLUDED.disease_name,
                    source = EXCLUDED.source,
                    orphanet_url = EXCLUDED.orphanet_url,
                    disorder_group = EXCLUDED.disorder_group,
                    age_at_onset = EXCLUDED.age_at_onset,
                    inheritance = EXCLUDED.inheritance
                """,
                disease_rows,
                page_size=500,
            )

            cursor.execute(
                """
                DELETE FROM orphanet_epidemiology
                WHERE orpha_code = ANY(%s)
                """,
                (sorted(seen_codes),),
            )

            if epidemiology_rows:
                execute_values(
                    cursor,
                    """
                    INSERT INTO orphanet_epidemiology (
                        orpha_code, prevalence_type, prevalence_qualification,
                        prevalence_geography, prevalence_class, reported_value,
                        reference, validation_status
                    )
                    VALUES %s
                    """,
                    epidemiology_rows,
                    page_size=500,
                )

    print(f"Loaded {len(disease_rows)} diseases.")
    print(f"Loaded {len(epidemiology_rows)} epidemiology records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
    "json_file",
    type=Path,
    nargs="?",
    default=Path(
        r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\orphanet_processed.json"
    ),
)
    parser.add_argument("--dbname", default="TEST_Panelbuilder_TEST")
    args = parser.parse_args()

    load_orphanet(args.json_file, args.dbname)