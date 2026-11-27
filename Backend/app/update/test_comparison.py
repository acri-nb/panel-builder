from datetime import datetime
import json
from pathlib import Path
from db_SQLAlchemy import SessionLocal
from update.comparison import compare_source_data
from update.test_on_source import print_comparison_summary



db = SessionLocal()

try:
    database_name = db.get_bind().url.database
    print("Database:", database_name)

    if database_name != "TEST_Panelbuilder_TEST":
        raise ValueError("Please connect to the test database.")

    print("\nLoading edited Ontario test data...")

    test_file = Path(
        r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\ontario normalised test copy.json"
    )

    with open(test_file, "r", encoding="utf-8") as file:
        normalized_data = json.load(file)

    for panel in normalized_data:
        last_updated = panel.get("last_updated")

        if "disease_subgroup" not in panel:
            panel["disease_subgroup"] = panel.get(
                "disease_sub_group"
            )

        if last_updated:
            try:
                # Already formatted as YYYY-MM-DD.
                datetime.strptime(last_updated, "%Y-%m-%d")
            except ValueError:
                panel["last_updated"] = datetime.strptime(
                    last_updated,
                    "%B %d, %Y"
                ).strftime("%Y-%m-%d")

    print(f"Loaded {len(normalized_data)} panels.")

    comparison_results = compare_source_data(
        db,
        normalized_data
    )

    print_comparison_summary(
        "Ontario Health",
        comparison_results
    )

finally:
    db.close()


