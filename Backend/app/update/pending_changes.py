import json

from sqlalchemy.orm import Session
from model import Panel,PanelChange


def normalize_proposal(value):
    if isinstance(value, dict):
        return {
            key: normalize_proposal(item)
            for key, item in value.items()
            if key != "processed_date"
        }

    if isinstance(value, list):
        items = [normalize_proposal(item) for item in value]

        return sorted(
            items,
            key=lambda item: json.dumps(item, sort_keys=True)
        )

    return value


def keep_existing_proposal(pending, proposed_data):
    previous = pending.proposed_data

    # Compare the action, proposed content, and original DB snapshot.
    fields = ["action", "data", "current_data"]

    identical = all(
        normalize_proposal(previous.get(field))
        == normalize_proposal(proposed_data.get(field))
        for field in fields
    )

    if identical:
        return True

    pending.status = "superseded"
    return False

def create_removed_panel_pending_change(db: Session, comparison_result):

    if comparison_result.get("status") != "removed":
        return None

    panel_id = comparison_result.get("panel_id")

    if panel_id is None:
        raise ValueError("No panel_id found for removed panel")

    panel = (
        db.query(Panel)
        .filter(Panel.panel_id == panel_id)
        .first()
    )

    if panel is None:
        raise ValueError(f"Panel {panel_id} not found in database")


    proposed_data = {
        "action": "remove",
        "data": {
            "panel_id": panel.panel_id,
            "source_panel_id": panel.source_panel_id,
            "child_panel_ids": panel.child_panel_ids,
            "panel_name": panel.panel_name,
            "source_id": panel.source_id,
            "source": comparison_result.get("source"),
            "ontario_id": panel.ontario_id,
            "lab_name": panel.lab_name,
            "reason": "Panel no longer present in latest source data"
        },
        "current_data": comparison_result.get("current_data"),
        "changes": {
            "metadata": comparison_result.get(
                "metadata_changes", {}
            ),
            "genes": comparison_result.get(
                "gene_changes", {}
            ),
            "strs": comparison_result.get(
                "str_changes", {}
            )
        }
    }

    # Avoid duplicate pending removals
    existing_pending = (
        db.query(PanelChange)
        .filter(
            PanelChange.panel_id == panel_id,
            PanelChange.status == "pending",
             PanelChange.change_version_id.is_(None)
        )
        .all()
    )

    # Supersede conflicting updates first.
    for change in existing_pending:
        if change.proposed_data.get("action") == "update":
            change.status = "superseded"


    # Keep an identical removal or supersede an outdated one.
    for change in existing_pending:
        if change.proposed_data.get("action") == "remove":
            if keep_existing_proposal(change, proposed_data):
                return change

            
    # for change in existing_pending:
    #     if change.proposed_data.get("action") == "remove":
    #         return change

    # proposed_data = {
    #     "action": "remove",
    #     "data": {
    #         "panel_id": panel.panel_id,
    #         "panel_name": panel.panel_name,
    #         "source_id": panel.source_id,
    #         "source": comparison_result.get("source"),
    #         "ontario_id": panel.ontario_id,
    #         "lab_name": panel.lab_name,
    #         "reason": "Panel no longer present in latest source data"
    #     },
    #     "current_data": comparison_result.get("current_data"),
    #     "changes": {
    #         "metadata": comparison_result.get(
    #             "metadata_changes", {}
    #         ),
    #         "genes": comparison_result.get(
    #             "gene_changes", {}
    #         ),
    #         "strs": comparison_result.get(
    #             "str_changes", {}
    #         )
    #     }
    # }

    new_change = PanelChange(
        panel_id=panel.panel_id,
        change_version_id=None,
        proposed_data=proposed_data,
        status="pending"
    )

    db.add(new_change)
    db.flush()


    return new_change










def create_external_pending_change(
    db: Session,
    comparison_result
):
    status = comparison_result.get("status")

    if status == "removed":
        return create_removed_panel_pending_change(
            db,
            comparison_result
        )

    if status not in ["new", "changed"]:
        return None

    new_data = comparison_result.get("new_data")

    if new_data is None:
        raise ValueError(
            "No new_data found in comparison result"
        )

    panel_id = comparison_result.get("panel_id")

    if status == "new":
        action = "create"
    else:
        action = "update"



    proposed_data = {
            "action": action,
            "data": new_data,
            "current_data": comparison_result.get("current_data"),
            "changes": {
                "metadata": comparison_result.get(
                    "metadata_changes", {}
                ),
                "genes": comparison_result.get(
                    "gene_changes", {}
                ),
                "strs": comparison_result.get(
                    "str_changes", {}
                )
            }
        }

  
    # DUPLICATE PENDING CHECK

    pending_changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.status == "pending",
             PanelChange.change_version_id.is_(None)
        )
        .all()
    )



    # An update now replaces any pending removal for this panel.
    if action == "update":
        for pending in pending_changes:
            if (
                pending.panel_id == panel_id
                and pending.proposed_data.get("action") == "remove"
            ):
                pending.status = "superseded"

    for pending in pending_changes:

        pending_action = pending.proposed_data.get("action")
        pending_data = pending.proposed_data.get(
            "data",
            {}
        )

        # Existing panel update
        if action == "update":

            if (
                pending.panel_id == panel_id
                and pending_action == "update"
            ):

                if keep_existing_proposal(pending, proposed_data):
                    return pending
             

        # New panel
        elif action == "create":

            if pending_action != "create":
                continue

            source_name = new_data.get("source")

            if pending_data.get("source") != source_name:
                continue

            # GenCC → unique by sgc_id
            if source_name == "GenCC":

                new_genes = new_data.get(
                    "genes",
                    []
                )

                pending_genes = pending_data.get(
                    "genes",
                    []
                )

                new_sgc_id = (
                    new_genes[0].get("sgc_id")
                    if new_genes
                    else None
                )

                pending_sgc_id = (
                    pending_genes[0].get("sgc_id")
                    if pending_genes
                    else None
                )

                if (
                    new_sgc_id
                    and new_sgc_id == pending_sgc_id
                ):

                  if keep_existing_proposal(pending, proposed_data):
                    return pending

            # ClinGen → unique by assertion_url
            elif source_name == "ClinGen":

                new_genes = new_data.get(
                    "genes",
                    []
                )

                pending_genes = pending_data.get(
                    "genes",
                    []
                )

                new_assertion_url = (
                    new_genes[0].get(
                        "assertion_url"
                    )
                    if new_genes
                    else None
                )

                pending_assertion_url = (
                    pending_genes[0].get(
                        "assertion_url"
                    )
                    if pending_genes
                    else None
                )

                if (
                    new_assertion_url
                    and new_assertion_url
                    == pending_assertion_url
                ):
    
                 if keep_existing_proposal(pending, proposed_data):
                    return pending

            elif source_name == "Ontario Health":

                ontario_id = new_data.get("ontario_id")

                if not ontario_id:
                    raise ValueError(
                        "Cannot create an Ontario pending change "
                        "without ontario_id"
                    )

                if (
                    pending_data.get("source") == source_name
                    and pending_data.get("ontario_id") == ontario_id
                ):

                 if keep_existing_proposal(pending, proposed_data):
                    return pending


            elif source_name in ("PanelApp UK", "PanelApp AUS"):

                source_panel_id = new_data.get("source_panel_id")

                if source_panel_id is None:
                    raise ValueError(
                        "Missing source_panel_id for PanelApp proposal"
                    )

                if (
                    pending_data.get("source_panel_id")
                    == source_panel_id
                ):
                    if keep_existing_proposal(pending, proposed_data):
                        return pending



            # Other sources blueprint
            else:

                if (
                    pending_data.get("source")
                    == source_name
                    and pending_data.get("panel_name")
                    == new_data.get("panel_name")
                ):

                   if keep_existing_proposal(pending, proposed_data):
                    return pending
    # ---------------------------------
    # CREATE NEW PENDING CHANGE
    # ---------------------------------

    # proposed_data = {
    #        "action": action,
    #        "data": new_data,
    #        "current_data": comparison_result.get("current_data"),
    #        "changes": {
    #            "metadata": comparison_result.get(
    #                "metadata_changes", {}
    #            ),
    #            "genes": comparison_result.get(
    #                "gene_changes", {}
    #            ),
    #            "strs": comparison_result.get(
    #                "str_changes", {}
    #            )
    #        }
    #    }

    new_change = PanelChange(
        panel_id=panel_id,
        change_version_id=None,
        proposed_data=proposed_data,
        status="pending"
    )

    db.add(new_change)
    db.flush()


    return new_change






def withdraw_unneeded_pending_changes(db: Session, comparison_result):

    if comparison_result.get("status") != "unchanged":
        return []

    panel_id = comparison_result.get("panel_id")

    if panel_id is None:
        return []

    panel = (
        db.query(Panel)
        .filter(Panel.panel_id == panel_id)
        .first()
    )

    # This function handles active external panels only.
    if panel is None or panel.source_id == 7 or not panel.is_active:
        return []

    pending_changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.panel_id == panel_id,
            PanelChange.status == "pending",
            PanelChange.change_version_id.is_(None)
        )
        .all()
    )

    withdrawn_ids = []

    for change in pending_changes:
        action = change.proposed_data.get("action")

        if action in ["update", "remove"]:
            change.status = "withdrawn"
            withdrawn_ids.append(change.change_id)

    db.flush()

    return withdrawn_ids





def create_orphanet_pending_change(
    db: Session,
    comparison_result: dict,
    pending_by_code: dict,
):
    """Queue one Orphanet comparison result in the current transaction."""
    code = comparison_result["orpha_code"]
    status = comparison_result["status"]
    existing = pending_by_code.get(code, [])

    if status == "unchanged":
        for change in existing:
            change.status = "withdrawn"
        pending_by_code.pop(code, None)
        return None

    action = {
        "new": "create",
        "changed": "update",
        "removed": "remove",
    }[status]

    proposed_data = {
        "target": "orphanet_disease",
        "orpha_code": code,
        "action": action,
        "data": comparison_result["new_data"],
        "current_data": comparison_result["current_data"],
        "changes": {
            "metadata": comparison_result["metadata_changes"],
            "epidemiology": comparison_result["epidemiology_changes"],
        },
    }

    matching_change = None
    for change in existing:
        if keep_existing_proposal(change, proposed_data):
            if matching_change is None:
                matching_change = change
            else:
                change.status = "superseded"

    if matching_change is not None:
        pending_by_code[code] = [matching_change]
        return None

    change = PanelChange(
        panel_id=None,
        change_version_id=None,
        proposed_data=proposed_data,
        status="pending",
    )
    db.add(change)
    pending_by_code[code] = [change]
    return change


def queue_orphanet_changes(db: Session, comparison_results):
    """Reconcile the Orphanet queue after a complete comparison."""
    pending_changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.panel_id.is_(None),
            PanelChange.change_version_id.is_(None),
            PanelChange.status == "pending",
        )
        .order_by(PanelChange.change_id)
        .with_for_update()
        .all()
    )

    pending_by_code = {}
    for change in pending_changes:
        proposal = change.proposed_data or {}
        if proposal.get("target") == "orphanet_disease":
            pending_by_code.setdefault(proposal["orpha_code"], []).append(change)

    compared_codes = set()
    created = []

    for result in comparison_results:
        compared_codes.add(result["orpha_code"])
        change = create_orphanet_pending_change(db, result, pending_by_code)
        if change is not None:
            created.append(change)

    # A full comparison can omit a code whose pending create is obsolete,
    # or an inactive disease that is still absent from the source.
    for code in pending_by_code.keys() - compared_codes:
        for change in pending_by_code[code]:
            change.status = "withdrawn"

    db.flush()
    return created