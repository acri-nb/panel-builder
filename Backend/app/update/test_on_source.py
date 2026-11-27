from datetime import datetime
import json
from pathlib import Path

from db_SQLAlchemy import SessionLocal
from collections import Counter
from update.acquire_data import (
    acquire_panelapp_aus,
    acquire_panelapp_uk,
    acquire_blueprint,
    acquire_ontario, 
    acquire_gencc,
    acquire_clingen,
    normalize_panelapp_aus,
    normalize_panelapp_uk,
    normalize_blueprint,
    normalize_ontario,
    normalize_gencc,
    normalize_clingen,
    acquire_orphanet,
    normalize_orphanet
)

from update.comparison import compare_panel, compare_source_data,compare_orphanet_data
import pandas as pd
from update.comparison import compare_source_data
from update.pending_changes import (create_external_pending_change, create_orphanet_pending_change, withdraw_unneeded_pending_changes ,queue_orphanet_changes )

# ============================================================
# COMPARISON SUMMARY
# ============================================================

def _print_item(item, label="Item"):
    gene_symbol = item.get("gene_symbol")
    entity_name = item.get("entity_name")
    identity = item.get("sgc_id") or item.get("assertion_url")

    if entity_name:
        text = entity_name

        if gene_symbol:
            text += f" (gene: {gene_symbol})"

    elif gene_symbol:
        text = gene_symbol

        if identity:
            text += f" [{identity}]"

    else:
        text = str(item)

    print(f"  - {label}: {text}")


def print_comparison_summary(source_name, comparison_results):
    new_panels = [r for r in comparison_results if r["status"] == "new"]
    changed_panels = [r for r in comparison_results if r["status"] == "changed"]
    unchanged_panels = [r for r in comparison_results if r["status"] == "unchanged"]
    removed_panels = [
    r for r in comparison_results
    if r["status"] == "removed"
    ]  

    print("\n====================================")
    print(f"{source_name} COMPARISON SUMMARY")
    print("====================================")



    incoming_count = (
        len(new_panels)
        + len(changed_panels)
        + len(unchanged_panels)
    )

    print(f"Incoming records compared: {incoming_count}")
    print(f"Total results including removals: {len(comparison_results)}")




    print(f"New: {len(new_panels)}")
    print(f"Changed: {len(changed_panels)}")
    print(f"Unchanged: {len(unchanged_panels)}")
    print(f"Removed: {len(removed_panels)}")


    if changed_panels:
        print("\n====================================")
        print("CHANGES DETECTED")
        print("====================================")

        for result in changed_panels:
            print("\n------------------------------------")
            print(f"Panel: {result['panel_name']}")
            print(f"Source: {result['source']}")
            print("------------------------------------")


            if result["source"] == "Ontario Health":
                data = (
                    result.get("new_data")
                    or result.get("current_data")
                    or {}
                )

                print(f"Ontario ID: {data.get('ontario_id')}")
                print(f"Lab: {data.get('lab_name')}")




            metadata = result.get("metadata_changes", {})
            genes = result.get("gene_changes", {})
            strs = result.get("str_changes", {})

            if metadata:
                print("\nMetadata changes:")
                for field, change in metadata.items():
                    print(f"  - {field}: {change['old']} -> {change['new']}")
            else:
                print("\nMetadata changes: none")

            print("\nGene/assertion changes:")
            if genes.get("added"):
                print(f"  Added: {len(genes['added'])}")
                for item in genes["added"]:
                    _print_item(item, "added")
            else:
                print("  Added: none")

            if genes.get("removed"):
                print(f"  Removed: {len(genes['removed'])}")
                for item in genes["removed"]:
                    _print_item(item, "removed")
            else:
                print("  Removed: none")

            if genes.get("modified"):
                print(f"  Modified: {len(genes['modified'])}")
                for item in genes["modified"]:

                    _print_item(item, "modified")

                    for field, change in item["changes"].items():
                        print(
                            f"      {field}: "
                            f"{change['old']} -> {change['new']}"
                        )
            else:
                print("  Modified: none")

            if strs.get("added") or strs.get("removed") or strs.get("modified"):
                print("\nSTR changes:")
                for item in strs.get("added", []):
                    _print_item(item, "added")
                for item in strs.get("removed", []):
                    _print_item(item, "removed")
                for item in strs.get("modified", []):
                    print(f"  - modified: {item['entity_name']}")
                    for field, change in item["changes"].items():
                        print(
                            f"      {field}: "
                            f"{change['old']} -> {change['new']}"
                        )
            else:
                print("\nSTR changes: none")

    if new_panels:
       print("\n====================================")
       print("NEW PANELS / ASSERTIONS")
       print("====================================")

       for result in new_panels:

           print("\n------------------------------------")
           print(f"Panel: {result['panel_name']}")
           print(f"Source: {result['source']}")


  
           if result["source"] == "Ontario Health":
                data = (
                    result.get("new_data")
                    or result.get("current_data")
                    or {}
                )

                print(f"Ontario ID: {data.get('ontario_id')}")
                print(f"Lab: {data.get('lab_name')}")


           

           data = result.get("new_data") or {}

           genes = data.get("genes") or []
           strs = data.get("strs") or []

           print(f"Genes/assertions: {len(genes)}")
           for item in genes:
               _print_item(item, "gene")

           print(f"STRs: {len(strs)}")
           for item in strs:
               _print_item(item, "STR")

    if removed_panels:
      print("\n====================================")
      print("REMOVED PANELS / ASSERTIONS")
      print("====================================")

      for result in removed_panels:

        print("\n------------------------------------")
        print(f"Panel: {result['panel_name']}")
        print(f"Source: {result['source']}")



        if result["source"] == "Ontario Health":
                data = (
                    result.get("new_data")
                    or result.get("current_data")
                    or {}
                )

                print(f"Ontario ID: {data.get('ontario_id')}")
                print(f"Lab: {data.get('lab_name')}")


        print(f"Panel ID: {result['panel_id']}")

        data = result.get("current_data") or {}

        genes = data.get("genes") or []
        strs = data.get("strs") or []

        print(f"Genes/assertions: {len(genes)}")
        for item in genes:
            _print_item(item, "gene")

        print(f"STRs: {len(strs)}")
        for item in strs:
            _print_item(item, "STR")

    
    print("\n====================================")
    print(f"{source_name} COMPARISON SUMMARY")
    print("====================================")



    incoming_count = (
        len(new_panels)
        + len(changed_panels)
        + len(unchanged_panels)
    )

    print(f"Incoming records compared: {incoming_count}")
    print(f"Total results including removals: {len(comparison_results)}")




    print(f"New: {len(new_panels)}")
    print(f"Changed: {len(changed_panels)}")
    print(f"Unchanged: {len(unchanged_panels)}")
    print(f"Removed: {len(removed_panels)}")







# ============================================================
# PANELAPP AUS
# ============================================================

def run_panelapp_aus_update():

    print("====================================")
    print("PANELAPP AUS EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print("\nAcquiring PanelApp AUS data...")

        raw_data = acquire_panelapp_aus()

        print(
            f"Acquired {len(raw_data)} panels."
        )

        # 2. Normalize
        print(
            "\nNormalizing PanelApp AUS data..."
        )

        normalized_data = normalize_panelapp_aus(
            raw_data
        )

        print(
            f"Normalized "
            f"{len(normalized_data)} panels."
        )

        # 3. Compare
        print("\nComparing with database...")

        comparison_results = compare_source_data(
            db,
            normalized_data
        )
        # Create pending changes for testing
        created_changes = []

        for result in comparison_results:


            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue


            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()

        if not created_changes:
            print(
                "\nNo pending changes were created."
            )
        # 4. Summary
        print_comparison_summary(
            "PanelApp AUS",
            comparison_results
        )

        return comparison_results


    except Exception:
        db.rollback()
        raise


    finally:

        db.close()


# ============================================================
# PANELAPP UK
# ============================================================

def run_panelapp_uk_update():

    print("====================================")
    print("PANELAPP UK EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print(
            "\nAcquiring PanelApp UK data..."
        )

        raw_data = acquire_panelapp_uk()

        print(
            f"Acquired {len(raw_data)} panels."
        )

        # 2. Normalize
        print(
            "\nNormalizing PanelApp UK data..."
        )

        normalized_data = normalize_panelapp_uk(
            raw_data
        )

        print(
            f"Normalized "
            f"{len(normalized_data)} panels."
        )

        # 3. Compare
        print(
            "\nComparing with database..."
        )

        comparison_results = compare_source_data(
            db,
            normalized_data
        )
        # Create pending changes for testing
        created_changes = []

        for result in comparison_results:


            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue

            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()
        if not created_changes:
            print(
                "\nNo pending changes were created."
            )
        # 4. Summary
        print_comparison_summary(
            "PanelApp UK",
            comparison_results
        )

        return comparison_results
    except Exception:
        db.rollback()
        raise


    finally:

        db.close()


# ============================================================
# BLUEPRINT GENETICS
# ============================================================

def run_blueprint_update():

    print("====================================")
    print("BLUEPRINT GENETICS EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print(
            "\nAcquiring Blueprint Genetics data..."
        )

        raw_data = acquire_blueprint()

        print(
            f"Acquired {len(raw_data)} panels."
        )

        # 2. Normalize
        print(
            "\nNormalizing Blueprint Genetics data..."
        )

        normalized_data = normalize_blueprint(
            raw_data
        )

        print(
            f"Normalized "
            f"{len(normalized_data)} panels."
        )

        # 3. Compare
        print(
            "\nComparing with database..."
        )

        comparison_results = compare_source_data(
            db,
            normalized_data
        )
        # Create pending changes for testing
        created_changes = []

        for result in comparison_results:

            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue


            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()
        if not created_changes:
            print(
                "\nNo pending changes were created."
            )
        # 4. Summary
        print_comparison_summary(
            "Blueprint Genetics",
            comparison_results
        )

        return comparison_results


    except Exception:
        db.rollback()
        raise



    finally:

        db.close()


# ============================================================
# ONTARIO HEALTH
# ============================================================

def run_ontario_update():

    print("====================================")
    print("ONTARIO HEALTH EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print(
            "\nAcquiring Ontario Health data..."
        )

        raw_data = acquire_ontario()

        print(
            f"Acquired {len(raw_data)} panels."
        )

        # 2. Normalize
        print(
            "\nNormalizing Ontario Health data..."
        )

        normalized_data = normalize_ontario(
            raw_data
        )

        print(
            f"Normalized "
            f"{len(normalized_data)} panels."
        )

        # 3. Compare
        print(
            "\nComparing with database..."
        )

        comparison_results = compare_source_data(
            db,
            normalized_data
        )

        # Create pending changes for testing
        created_changes = []

        for result in comparison_results:

            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue

            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()
        if not created_changes:
            print(
                "\nNo pending changes were created."
            )


        # 4. Summary
        print_comparison_summary(
            "Ontario Health",
            comparison_results
        )

        return comparison_results


    except Exception:
        db.rollback()
        raise

    finally:

        db.close()











# def run_ontario_file_test():

#     print("====================================")
#     print("ONTARIO HEALTH — LOCAL FILE TEST")
#     print("====================================")

#     db = SessionLocal()

#     try:
#         database_name = db.get_bind().url.database
#         print("Database:", database_name)

#         if database_name != "TEST_Panelbuilder_TEST":
#             raise ValueError(
#                 "This test must use TEST_Panelbuilder_TEST."
#             )

#         # 1. Load the saved normalized data.
#         test_file = Path(
#             r"C:\Users\emnab\Desktop\Panelbuilder\Backend\processin_data\newprocessed_data\ontario normalised test copy.json"
#         )

#         with open(test_file, "r", encoding="utf-8") as file:
#             normalized_data = json.load(file)

#         if not isinstance(normalized_data, list) or not normalized_data:
#             raise ValueError("The test file must contain a non-empty list.")

#         # Handle the older field/date format in your saved test copy.
#         for panel in normalized_data:

#             if panel.get("source") != "Ontario Health":
#                 raise ValueError(
#                     "The test file must contain only Ontario Health records."
#                 )

#             if "disease_subgroup" not in panel:
#                 panel["disease_subgroup"] = panel.get(
#                     "disease_sub_group"
#                 )

#             last_updated = panel.get("last_updated")

#             if last_updated:
#                 last_updated = last_updated.strip()

#                 try:
#                     parsed_date = datetime.strptime(
#                         last_updated,
#                         "%Y-%m-%d"
#                     )
#                 except ValueError:
#                     parsed_date = datetime.strptime(
#                         last_updated,
#                         "%B %d, %Y"
#                     )

#                 panel["last_updated"] = parsed_date.strftime(
#                     "%Y-%m-%d"
#                 )

#         print(f"Loaded {len(normalized_data)} panels.")

#         # 2. Compare with the test database.
#         comparison_results = compare_source_data(
#             db,
#             normalized_data
#         )

#         print_comparison_summary(
#             "Ontario Health",
#             comparison_results
#         )

#         # 3. Process pending proposals.
#         pending_ids = set()
#         withdrawn_ids = []

#         for result in comparison_results:

#             if result["status"] == "unchanged":
#                 ids = withdraw_unneeded_pending_changes(
#                     db,
#                     result
#                 )

#                 withdrawn_ids.extend(ids)

#                 for change_id in ids:
#                     print(
#                         f"Withdrawn request {change_id}: "
#                         f"{result['panel_name']}"
#                     )

#                 continue

#             if result["status"] in ["new", "changed", "removed"]:
#                 change = create_external_pending_change(
#                     db,
#                     result
#                 )

#                 if change is not None:
#                     pending_ids.add(change.change_id)

#                     print("\nPending change (new or existing):")
#                     print("change_id:", change.change_id)
#                     print("panel_id:", change.panel_id)
#                     print("status:", change.status)
#                     print(
#                         "action:",
#                         change.proposed_data.get("action")
#                     )

#         # 4. Save the proposal changes together.
#         db.commit()

#         print("\nTest committed successfully.")
#         print("Pending requests returned:", len(pending_ids))
#         print("Withdrawn requests:", len(withdrawn_ids))

#         return comparison_results

#     except Exception:
#         db.rollback()
#         print("\nTest failed. Uncommitted changes rolled back.")
#         raise

#     finally:
#         db.close()


# if __name__ == "__main__":
#     run_ontario_file_test()









# ============================================================
# CLINGEN
# ============================================================

def run_clingen_update():

    print("====================================")
    print("CLINGEN EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print("\nAcquiring ClinGen data...")

        raw_data = acquire_clingen()

        print(
            f"Acquired {len(raw_data)} records."
        )

        # 2. Normalize
        print("\nNormalizing ClinGen data...")

        normalized_data = normalize_clingen(
            raw_data
        )

        print(
            f"Normalized {len(normalized_data)} records."
        )

        # 3. Compare
        print("\nComparing with database...")

        comparison_results = compare_source_data(
            db,
            normalized_data
        )

        # Check how many panels have each status
        from collections import Counter

        status_counts = Counter(
            result["status"]
            for result in comparison_results
        )

        print("\nComparison status counts:")
        print(status_counts)

        # Create pending changes for testing
        created_changes = []

        for result in comparison_results:

            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue
       



            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()
        if not created_changes:
            print(
                "\nNo pending changes were created."
            )

        # 4. Summary
        print_comparison_summary(
            "ClinGen",
            comparison_results
        )

        return comparison_results

    except Exception:
        db.rollback()
        raise


    finally:
        db.close()


# ============================================================
# GENCC
# ============================================================
    
def run_gencc_update():

    print("====================================")
    print("GENCC EXTERNAL UPDATE")
    print("====================================")

    db = SessionLocal()

    try:

        # 1. Acquire
        print(
            "\nAcquiring GenCC data..."
        )
        raw_data = acquire_gencc()

        print(
            f"Acquired {len(raw_data)} records."
        )

        # 2. Normalize
        print(
            "\nNormalizing GenCC data..."
        )

        normalized_data = normalize_gencc(
            raw_data
        )

        print(
            f"Normalized "
            f"{len(normalized_data)} records."
        )

        # 3. Compare
        print(
            "\nComparing with database..."
        )

        # differences_found = 0

        # for panel in normalized_data:
        #     result = compare_panel(db, panel)

        #     if result["status"] == "unchanged":
        #         continue

        #     differences_found += 1
        #     genes = panel.get("genes") or []
        #     gene = genes[0] if genes else {}

        #     print(f"\nDIFFERENCE {differences_found}")
        #     print("Status:", result["status"])
        #     print("SGC ID:", gene.get("sgc_id"))
        #     print("Panel ID:", result.get("panel_id"))
        #     print("Metadata:", result["metadata_changes"])
        #     print(
        #         "Gene counts:",
        #         {key: len(items) for key, items in result["gene_changes"].items()}
        #     )
        #     print(
        #         "STR counts:",
        #         {key: len(items) for key, items in result["str_changes"].items()}
        #     )

        #     if differences_found == 10:
        #         break

        # print(f"\nInspected {differences_found} differences.")
        # return None


        comparison_results = compare_source_data(
            db,
            normalized_data
        )

        # Create pending changes for testing
        created_changes = []



        for result in comparison_results:

            if result["status"] == "unchanged":
                withdrawn_ids = withdraw_unneeded_pending_changes(
                    db,
                    result
                )

                for change_id in withdrawn_ids:
                    print(
                        f"Withdrawn request {change_id}: "
                        f"{result['panel_name']} now matches the database."
                    )

                continue

            if result["status"] in [
                "new",
                "changed",
                "removed"
            ]:

                change = create_external_pending_change(
                    db,
                    result
                )

                if change:
                    created_changes.append(change)

                    print("\nCreated change:")
                    print("change_id:", change.change_id)
                    print("panel_id:", change.panel_id)
                    print("status:", change.status)
                    print(
                        "action:",
                        change.proposed_data.get("action")
                    )
        db.commit()
        if not created_changes:
            print(
                "\nNo pending changes were created."
            )

        # 4. Summary
        print_comparison_summary(
            "GenCC",
            comparison_results
        )

        return comparison_results


    except Exception:
        db.rollback()
        raise

    finally:

        db.close()



#validaed
# if __name__ == "__main__":
#    run_gencc_update()

#validated
# if __name__ == "__main__":
#     run_clingen_update()

#validated
# if __name__ == "__main__":
#    run_ontario_update()

#validated
# if __name__ == "__main__":
#     run_blueprint_update()

#Validated
# if __name__ == "__main__":
#     run_panelapp_aus_update()

#Validated
# if __name__ == "__main__":
#     run_panelapp_uk_update()































# def run_orphanet_updatetodelete(db, *, limit=None):

#     raw_data = acquire_orphanet(limit=limit)
#     normalized_data = normalize_orphanet(raw_data)

#     results = compare_orphanet_data(
#         db,
#         normalized_data,
#         detect_removals=(limit is None),
#     )

#     counts = Counter(result["status"] for result in results)
#     print(f"Compared {len(normalized_data)} Orphanet diseases.")
#     print(dict(counts))

#     for result in results:
#         if result["status"] != "unchanged":
#             print(result["status"], result["orpha_code"], result["disease_name"])


#     if limit is None:
#      try:
#         pending = queue_orphanet_changes(db, results)
#         created_count = len(pending)
#         db.commit()
    
#      except Exception:
#         db.rollback()
     
#         raise
#      print(f"Created {created_count} new Orphanet pending requests.")


#     else:
#         if db.get_bind().url.database != "TEST_Panelbuilder_TEST":
#             raise RuntimeError("Run this test against TEST_Panelbuilder_TEST.")

#         result = next(
#             (
#                 item for item in results
#                 if item["orpha_code"] == 166024 and item["status"] == "new"
#             ),
#             None,
# )
#         if result is None:
#             raise RuntimeError("Expected ORPHA:166024 to be classified as new.")

#         pending = create_orphanet_pending_change(db, result, {})
#         db.flush()
#         change_id = pending.change_id
#         db.commit()
#         print(f"Queued create for ORPHA:166024 (change_id={change_id}).")

#     return results



def run_orphanet_update(db):
    raw_data = acquire_orphanet()
    normalized_data = normalize_orphanet(raw_data)

    try:
        results = compare_orphanet_data(
            db,
            normalized_data,
            detect_removals=True,
        )
        pending = queue_orphanet_changes(db, results)
        created_count = len(pending)
        db.commit()
    except Exception:
        db.rollback()
        raise

    counts = Counter(result["status"] for result in results)
    print(f"Compared {len(normalized_data)} incoming Orphanet diseases.")
    print(f"Comparison results: {dict(counts)}")
    print(f"Created {created_count} new Orphanet pending requests.")

    return results

if __name__ == "__main__":
    with SessionLocal() as db:
        run_orphanet_update(db)




# from db_SQLAlchemy import SessionLocal
# from update.approval import approve_external_change


# def test_external_approvals():

#     db = SessionLocal()

#     try:

#         for change_id in [14, 15, 27]:

#             print("\n==============================")
#             print(f"Approving change {change_id}")
#             print("==============================")

#             change = approve_external_change(
#                 db,
#                 change_id
#             )

#             print("change_id:", change.change_id)
#             print("panel_id:", change.panel_id)
#             print("status:", change.status)
#             print("reviewed_at:", change.reviewed_at)

#     finally:
#         db.close()


# #if __name__ == "__main__":
# #    test_external_approvals()


# from db_SQLAlchemy import SessionLocal
# from update.approval import reject_external_change


# def test_external_rejections():

#     db = SessionLocal()

#     try:

#         for change_id in [36, 26, 1]:

#             print("\n==============================")
#             print(f"Rejecting change {change_id}")
#             print("==============================")

#             change = reject_external_change(
#                 db,
#                 change_id
#             )

#             print("change_id:", change.change_id)
#             print("panel_id:", change.panel_id)
#             print("status:", change.status)
#             print("reviewed_at:", change.reviewed_at)

#     finally:
#         db.close()


# #if __name__ == "__main__":
#  #  test_external_rejections()