from datetime import date, datetime
from sqlalchemy.orm import Session
from decimal import Decimal

from model import (
    Panel,
    Source,
    Version,
    Gene,
    PanelGene,
    STR,
    PanelSTR,
    PanelChange,
    OrphanetDisease,
    OrphanetEpidemiology
)

from update.comparison import (
    get_current_panel_data,
    find_existing_panel,
    ORPHANET_EPIDEMIOLOGY_FIELDS,
    ORPHANET_METADATA_FIELDS,
    get_current_orphanet_data
)
from update.pending_changes import normalize_proposal












def parse_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).date()
        except ValueError:
            return None

    return None



def get_or_create_external_version(
    db: Session,
    source_id: int,
    version_number,
    last_updated
):
    last_updated = parse_date(last_updated)

    version = (
        db.query(Version)
        .filter(
            Version.source_id == source_id,
            Version.version_number == (
                str(version_number)
                if version_number is not None
                else None
            ),
            Version.last_updated == last_updated
        )
        .first()
    )

    if version:
        return version

    version = Version(
        source_id=source_id,
        version_number=(
            str(version_number)
            if version_number is not None
            else None
        ),
        last_updated=last_updated
    )

    db.add(version)
    db.flush()

    return version






def apply_external_create(
    db: Session,
    data: dict,
    change: PanelChange
):

    # SOURCE

    source_name = data.get("source")

    if not source_name:
        raise ValueError("No source found in new panel data")

    source = (
        db.query(Source)
        .filter(Source.source_name == source_name)
        .first()
    )

    if source is None:
        raise ValueError(
            f"Source '{source_name}' not found"
        )

    if source_name == "Ontario Health":

        ontario_id = data.get("ontario_id")

        if not ontario_id:
            raise ValueError(
                "Cannot create an Ontario panel without ontario_id"
            )

        existing = (
            db.query(Panel)
            .filter(
                Panel.source_id == source.source_id,
                Panel.ontario_id == ontario_id
            )
            .first()
        )

        if existing is not None:
            raise ValueError(
                f"Ontario ID {ontario_id} already exists "
                f"as panel {existing.panel_id}"
            )

    # VERSION

    version = get_or_create_external_version(
        db=db,
        source_id=source.source_id,
        version_number=data.get("version"),
        last_updated=data.get("last_updated")
    )

    # PANEL

    panel = Panel(
        panel_name=data.get("panel_name"),
        source_panel_id=data.get("source_panel_id"),
        child_panel_ids=data.get("child_panel_ids"),
        disease_group=data.get("disease_group"),
        disease_subgroup=data.get("disease_subgroup"),
        relevant_diseases=data.get("relevant_diseases"),
        source_id=source.source_id,
        version_id=version.version_id,
        is_active=True
    )

    if source_name == "Ontario Health":
        panel.ontario_id = data["ontario_id"]
        panel.lab_name = data.get("lab_name")

        relevant = data.get("relevant_diseases")

        panel.relevant_diseases = (
            ", ".join(relevant)
            if isinstance(relevant, list)
            else relevant
        )

    db.add(panel)

    # Need panel_id before creating relationships
    db.flush()

    
    # GENES

    for gene_data in data.get("genes", []):

        gene_symbol = gene_data.get("gene_symbol")

        if not gene_symbol:
            continue

        gene = (
            db.query(Gene)
            .filter(
                Gene.gene_symbol == gene_symbol
            )
            .first()
        )

        if gene is None:
            gene = Gene(
                gene_symbol=gene_symbol
            )

            db.add(gene)
            db.flush()

        panel_gene = PanelGene(
            panel_id=panel.panel_id,
            gene_id=gene.gene_id,
            confidence_level=gene_data.get(
                "confidence_level"
            ),
            origin_panel_id=gene_data.get("origin_panel_id"),
            phenotypes=gene_data.get("phenotypes"),
            moi=gene_data.get("moi"),
            submitter=gene_data.get("submitter"),
            sgc_id=gene_data.get("sgc_id"),
            assertion_url=gene_data.get(
                "assertion_url"
            )
        )

        db.add(panel_gene)

    # STRs

    for str_data in data.get("strs", []):

        gene = None

        gene_symbol = str_data.get("gene_symbol")

        if gene_symbol:
            gene = (
                db.query(Gene)
                .filter(
                    Gene.gene_symbol == gene_symbol
                )
                .first()
            )

            if gene is None:
                gene = Gene(
                    gene_symbol=gene_symbol
                )

                db.add(gene)
                db.flush()

        new_str = STR(
            entity_name=str_data.get("entity_name"),
            gene_id=(
                gene.gene_id
                if gene else None
            ),
            confidence_level=str_data.get(
                "confidence_level"
            ),
            phenotypes=str_data.get("phenotypes"),
            repeated_sequence=str_data.get(
                "repeated_sequence"
            )
        )

        db.add(new_str)
        db.flush()

        panel_str = PanelSTR(
            panel_id=panel.panel_id,
            str_id=new_str.str_id,
            origin_panel_id=str_data.get("origin_panel_id")
        )

        db.add(panel_str)

    
    # LINK CHANGE TO NEW PANEL

    change.panel_id = panel.panel_id

    return panel






def apply_external_update(
    db: Session,
    panel_id: int,
    data: dict
):

    # PANEL
    panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id
        )
        .first()
    )

    if panel is None:
        raise ValueError(
            f"Panel {panel_id} not found"
        )

    # SOURCE
    source_name = data.get("source")

    if not source_name:
        raise ValueError(
            "No source found in update data"
        )

    source = (
        db.query(Source)
        .filter(
            Source.source_name == source_name
        )
        .first()
    )

    if source is None:
        raise ValueError(
            f"Source '{source_name}' not found"
        )


    if source_name in ("PanelApp UK", "PanelApp AUS"):
        source_panel_id = data.get("source_panel_id")

        if source_panel_id is None:
            raise ValueError("Missing PanelApp source_panel_id")

        if (
            panel.source_id != source.source_id
            or panel.source_panel_id != source_panel_id
        ):
            raise ValueError(
                "PanelApp update identity does not match "
                "the target database panel"
            )
    if source_name == "Ontario Health":

        ontario_id = data.get("ontario_id")

        if not ontario_id:
            raise ValueError(
                "Cannot update an Ontario panel without ontario_id"
            )

        if (
            panel.source_id != source.source_id
            or panel.ontario_id != ontario_id
        ):
            raise ValueError(
                "Ontario update identity does not match "
                "the target database panel"
            )
    # VERSION

    version = get_or_create_external_version(
        db=db,
        source_id=source.source_id,
        version_number=data.get("version"),
        last_updated=data.get("last_updated")
    )

    # UPDATE PANEL METADATA

    panel.panel_name = data.get("panel_name")
    panel.disease_group = data.get("disease_group")
    panel.disease_subgroup = data.get(
        "disease_subgroup"
    )
    panel.relevant_diseases = data.get(
        "relevant_diseases"
    )

    if source_name in ("PanelApp UK", "PanelApp AUS"):
        panel.child_panel_ids = data.get("child_panel_ids")

    if source_name == "Ontario Health":

        panel.lab_name = data.get("lab_name")

        relevant = data.get("relevant_diseases")

        panel.relevant_diseases = (
            ", ".join(relevant)
            if isinstance(relevant, list)
            else relevant
        )

    panel.source_id = source.source_id
    panel.version_id = version.version_id

    panel.is_active = True

    # REMOVE OLD GENE LINKS

    (
        db.query(PanelGene)
        .filter(
            PanelGene.panel_id == panel.panel_id
        )
        .delete(
            synchronize_session=False
        )
    )

    # INSERT CURRENT GENES

    for gene_data in data.get("genes", []):

        gene_symbol = gene_data.get("gene_symbol")

        if not gene_symbol:
            continue

        gene = (
            db.query(Gene)
            .filter(
                Gene.gene_symbol == gene_symbol
            )
            .first()
        )

        if gene is None:
            gene = Gene(
                gene_symbol=gene_symbol
            )

            db.add(gene)
            db.flush()

        panel_gene = PanelGene(
            panel_id=panel.panel_id,
            gene_id=gene.gene_id,
            confidence_level=gene_data.get(
                "confidence_level"
            ),
            origin_panel_id=gene_data.get("origin_panel_id"),
            phenotypes=gene_data.get("phenotypes"),
            moi=gene_data.get("moi"),
            submitter=gene_data.get("submitter"),
            sgc_id=gene_data.get("sgc_id"),
            assertion_url=gene_data.get(
                "assertion_url"
            )
        )

        db.add(panel_gene)

    # REMOVE OLD STR LINKS

    (
        db.query(PanelSTR)
        .filter(
            PanelSTR.panel_id == panel.panel_id
        )
        .delete(
            synchronize_session=False
        )
    )

    # INSERT CURRENT STRs

    for str_data in data.get("strs", []):

        gene = None

        gene_symbol = str_data.get("gene_symbol")

        if gene_symbol:

            gene = (
                db.query(Gene)
                .filter(
                    Gene.gene_symbol == gene_symbol
                )
                .first()
            )

            if gene is None:
                gene = Gene(
                    gene_symbol=gene_symbol
                )

                db.add(gene)
                db.flush()

        new_str = STR(
            entity_name=str_data.get("entity_name"),
            gene_id=(
                gene.gene_id
                if gene else None
            ),
            confidence_level=str_data.get(
                "confidence_level"
            ),
            phenotypes=str_data.get("phenotypes"),
            repeated_sequence=str_data.get(
                "repeated_sequence"
            )
        )

        db.add(new_str)
        db.flush()

        panel_str = PanelSTR(
            panel_id=panel.panel_id,
            str_id=new_str.str_id,
            origin_panel_id=str_data.get("origin_panel_id")
        )

        db.add(panel_str)

    return panel




def apply_external_remove(
    db: Session,
    panel_id: int
):

    panel = (
        db.query(Panel)
        .filter(Panel.panel_id == panel_id)
        .first()
    )

    if panel is None:
        raise ValueError(
            f"Panel {panel_id} not found"
        )

    panel.is_active = False






def reject_external_change(
    db: Session,
    change_id: int
):

    change = (
        db.query(PanelChange)
        .filter(PanelChange.change_id == change_id)
        .first()
    )

    if change is None:
        raise ValueError(
            "Change request not found"
        )

    if change.change_version_id is not None:
        raise ValueError(
            "This function only handles external changes"
        )

    if change.status != "pending":
        raise ValueError(
            f"Change request is already {change.status}"
        )

    change.status = "rejected"
    change.reviewed_at = datetime.now()

    db.commit()
    db.refresh(change)

    return change





































def apply_orphanet_change(db: Session, proposal: dict):
    action = proposal["action"]
    data = proposal["data"]
    code = proposal["orpha_code"]

    if (
        type(code) is not int
        or code <= 0
        or data.get("orpha_code") != code
        or data.get("source") != "Orphanet"
    ):
        raise ValueError("Invalid Orphanet proposal target.")

    disease = (
        db.query(OrphanetDisease)
        .filter(OrphanetDisease.orpha_code == code)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )

    if action == "create":
        if disease is not None:
            raise ValueError(f"ORPHA:{code} already exists. Run comparison again.")

        disease = OrphanetDisease(orpha_code=code, source="Orphanet")
        db.add(disease)
        current = None
    else:
        if disease is None:
            raise ValueError(f"ORPHA:{code} no longer exists. Run comparison again.")

        current = get_current_orphanet_data(disease)
        if normalize_proposal(current) != normalize_proposal(
            proposal.get("current_data")
        ):
            raise ValueError(
                f"ORPHA:{code} changed after this proposal was created. "
                "Run comparison again."
            )

        if action == "remove":
            disease.is_active = False
            return

    for field in ORPHANET_METADATA_FIELDS:
        setattr(disease, field, data[field])

    incoming_records = data["epidemiology"]

    # Preserve existing row IDs when only disease metadata changed.
    if current is not None and normalize_proposal(
        current["epidemiology"]
    ) == normalize_proposal(incoming_records):
        return

    db.flush()

    if current is not None:
        db.query(OrphanetEpidemiology).filter(
            OrphanetEpidemiology.orpha_code == code
        ).delete(synchronize_session="fetch")

    for record in incoming_records:
        values = {
            field: record[field] for field in ORPHANET_EPIDEMIOLOGY_FIELDS
        }
        if values["reported_value"] is not None:
            values["reported_value"] = Decimal(values["reported_value"])

        db.add(OrphanetEpidemiology(orpha_code=code, **values))








def approve_external_change(db: Session, change_id: int):

    try:
        # Lock the request while reviewing and applying it.
        change = (
            db.query(PanelChange)
            .filter(PanelChange.change_id == change_id)
            .with_for_update()
            .populate_existing()
            .first()
        )

        if change is None:
            raise ValueError("Change request not found")

        if change.change_version_id is not None:
            raise ValueError(
                "This function only handles external changes"
            )

        if change.status != "pending":
            raise ValueError(
                f"Change request is already {change.status}"
            )

        proposed_data = change.proposed_data
        action = proposed_data.get("action")
        data = proposed_data.get("data")  

        if action not in ["create", "update", "remove"]:
            raise ValueError("Invalid external change action")

        if not isinstance(data, dict):
            raise ValueError("Missing or invalid proposed data")

        if proposed_data.get("target") == "orphanet_disease":
            apply_orphanet_change(db, proposed_data)

            change.status = "approved"
            change.reviewed_at = datetime.now()
            db.commit()
            db.refresh(change)
            return change

        

        # Check existing panels before updates or removals.
        if action in ["update", "remove"]:

            panel = (
                db.query(Panel)
                .filter(Panel.panel_id == change.panel_id)
                .with_for_update()
                .populate_existing()
                .first()
            )

            if panel is None:
                raise ValueError("The target panel no longer exists")

            if panel.source_id == 7:
                raise ValueError(
                    "External approval cannot modify laboratory panels"
                )

            saved_data = proposed_data.get("current_data")

            if (
                not isinstance(saved_data, dict)
                or "is_active" not in saved_data
            ):
                raise ValueError(
                    "This proposal has an incomplete database snapshot. "
                    "Run comparison again before approval."
                )

            current_data = get_current_panel_data(db, panel)

            if (
                normalize_proposal(current_data)
                != normalize_proposal(saved_data)
            ):
                raise ValueError(
                    "The database panel changed after this proposal "
                    "was generated. Run comparison again before approval."
                )

        # CREATE
        if action == "create":

            source_name = data.get("source")

            external_sources = {
                "PanelApp UK",
                "PanelApp AUS",
                "Blueprint Genetics",
                "Ontario Health",
                "ClinGen",
                "GenCC"
            }

            if source_name not in external_sources:
                raise ValueError("Invalid external source")

            genes = data.get("genes") or []
            gene = genes[0] if genes else None

            existing_panel = find_existing_panel(
                db,
                panel_name=data.get("panel_name"),
                source_name=source_name,
                gene=gene,
                ontario_id=data.get("ontario_id"),
                source_panel_id=data.get("source_panel_id")
            )

            if existing_panel is not None:
                raise ValueError(
                    "A panel with this source identity already exists. "
                    "Run comparison again before approval."
                )

            apply_external_create(
                db=db,
                data=data,
                change=change
            )

        # UPDATE
        elif action == "update":

            if data.get("source") != current_data.get("source"):
                raise ValueError(
                    "The proposed source does not match the target panel"
                )

            apply_external_update(
                db=db,
                panel_id=change.panel_id,
                data=data
            )

        # REMOVE
        else:
            apply_external_remove(
                db=db,
                panel_id=change.panel_id
            )

        change.status = "approved"
        change.reviewed_at = datetime.now()

        db.commit()
        db.refresh(change)

        return change

    except Exception:
        db.rollback()
        raise


































def approve_external_changetodelete(db: Session, change_id: int):

    change = (
        db.query(PanelChange)
        .filter(PanelChange.change_id == change_id)
        .first()
    )

    if change is None:
        raise ValueError("Change request not found")

     # Make sure this is an external change
    if change.change_version_id is not None:
        raise ValueError(
            "This function only handles external changes"
        )

    if change.status != "pending":
        raise ValueError(
            f"Change request is already {change.status}"
        )

    proposed_data = change.proposed_data

    action = proposed_data.get("action")
    data = proposed_data.get("data")

    if action is None:
        raise ValueError("No action found in proposed_data")

    if data is None:
        raise ValueError("No data found in proposed_data")

    try:
        
        # CREATE

        if action == "create":

            apply_external_create(
                db=db,
                data=data,
                change=change
            )

        # UPDATE
        
        elif action == "update":

            apply_external_update(
                db=db,
                panel_id=change.panel_id,
                data=data
            )

        
        # REMOVE
        elif action == "remove":

            apply_external_remove(
                db=db,
                panel_id=change.panel_id
            )

        else:
            raise ValueError(
                f"Unknown external change action: {action}"
            )

        # Mark change as approved
        change.status = "approved"
        change.reviewed_at = datetime.now()

        db.commit()
        db.refresh(change)

        return change

    except Exception:
        db.rollback()
        raise