from sqlalchemy.orm import Session,selectinload
from model import Panel, Source, Version, Gene, PanelGene,STR,PanelSTR, PanelChange,OrphanetDisease
from collections import Counter
from decimal import Decimal






def find_existing_panel(
    db: Session,
    panel_name: str,
    source_name: str,
    gene: dict | None = None,
    ontario_id: str | None = None,
    source_panel_id: int | None = None
):
    # First, restrict the search to the same source.
    query = (
        db.query(Panel)
        .join(Source, Panel.source_id == Source.source_id)
        .filter(Source.source_name == source_name)
    )

    if source_name == "GenCC":

        if not gene or not gene.get("sgc_id"):
            raise ValueError("Missing GenCC sgc_id")

        query = (
            query
            .join(PanelGene, Panel.panel_id == PanelGene.panel_id)
            .filter(PanelGene.sgc_id == gene["sgc_id"])
        )

    elif source_name == "ClinGen":

        if not gene or not gene.get("assertion_url"):
            raise ValueError("Missing ClinGen assertion_url")

        query = (
            query
            .join(PanelGene, Panel.panel_id == PanelGene.panel_id)
            .filter(
                PanelGene.assertion_url == gene["assertion_url"]
            )
        )

    elif source_name == "Ontario Health":

        if not ontario_id:
            raise ValueError("Missing Ontario ID")

        query = query.filter(
            Panel.ontario_id == ontario_id
        )

    elif source_name in ("PanelApp UK", "PanelApp AUS"):

        if source_panel_id is None:
            raise ValueError(
                f"Missing source_panel_id for {source_name}: {panel_name}"
            )

        query = query.filter(
            Panel.source_panel_id == source_panel_id
        )

    else:
        # Blueprint Genetics
        if not panel_name:
            raise ValueError("Missing panel name")

        query = query.filter(
            Panel.panel_name == panel_name
        )

    return query.one_or_none()









def _panel_identity(panel):
    source = panel.get("source")

    if source in ("PanelApp UK", "PanelApp AUS"):
        return panel.get("source_panel_id")

    if source == "Ontario Health":
        return panel.get("ontario_id")

    if source == "GenCC":
        genes = panel.get("genes", [])
        if genes:
            return genes[0].get("sgc_id")
        return None

    if source == "ClinGen":
        genes = panel.get("genes", [])
        if genes:
            return genes[0].get("assertion_url")
        return None

    return panel.get("panel_name")





def find_removed_panels(db: Session, normalized_data):
    if not normalized_data:
        return []

    source_name = normalized_data[0].get("source")

    # identities currently present in source
    incoming_identities = {
        _panel_identity(panel)
        for panel in normalized_data
        if _panel_identity(panel)
    }

    removed = []

    db_panels = (
        db.query(Panel)
        .join(Source, Panel.source_id == Source.source_id)
        .filter(
            Source.source_name == source_name,
            Panel.is_active.is_(True)
        )
        .all()
    )

    for panel in db_panels:

        current_data = get_current_panel_data(
            db,
            panel
        )

        db_identity = _panel_identity(
            current_data
        )

        if db_identity and db_identity not in incoming_identities:

            removed.append({
                "status": "removed",
                "panel_id": panel.panel_id,
                "panel_name": panel.panel_name,
                "source": source_name,
                "metadata_changes": {},
                "gene_changes": {
                    "added": [],
                    "removed": current_data.get("genes", []),
                    "modified": []
                },
                "str_changes": {
                    "added": [],
                    "removed": current_data.get("strs", []),
                    "modified": []
                },
                "current_data": current_data,
                "new_data": None
            })

    return removed








EXTERNAL_SOURCES = {
    "PanelApp UK",
    "PanelApp AUS",
    "Ontario Health",
    "Blueprint Genetics",
    "ClinGen",
    "GenCC"
}


def validate_source_data(normalized_data):

    if not normalized_data:
        raise ValueError(
            "The source dataset is empty. "
            "Check acquisition before running comparison."
        )

    source_name = normalized_data[0].get("source")

    if source_name not in EXTERNAL_SOURCES:
        raise ValueError(
            f"Unsupported external source: {source_name}"
        )

    identities = set()

    for panel in normalized_data:

        if panel.get("source") != source_name:
            raise ValueError(
                "Compare one source at a time."
            )

        identity = _panel_identity(panel)

        if identity is None or not str(identity).strip():
            raise ValueError(
                f"Missing identity for {source_name}: "
                f"{panel.get('panel_name')}"
            )

        if identity in identities:
            raise ValueError(
                f"Duplicate identity in {source_name}: {identity}"
            )

        identities.add(identity)








def compare_source_data(db: Session, normalized_data):

    validate_source_data(normalized_data)

    comparison_results = []

    # 1. Detect new / changed / unchanged
    for panel in normalized_data:
        result = compare_panel(
            db,
            panel
        )

        comparison_results.append(
            result
        )

    # 2. Detect DB panels/assertions that disappeared
    removed_results = find_removed_panels(
        db,
        normalized_data
    )

    comparison_results.extend(
        removed_results
    )

    return comparison_results






def _normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str) and value.strip() == "{}":
     return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = value
    else:
        raise ValueError(
            f"Expected text or a list of text, got: {type(value).__name__}"
        )

    normalized = set()

    for item in values:

        if item is None:
            continue

        if not isinstance(item, str):
            raise ValueError(
                f"Expected a text list item, got: {type(item).__name__}"
            )

        item = item.strip()

        if item:
            normalized.add(item)

    return sorted(normalized)





def _normalize_text(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip().casefold()

    return value


def compare_metadata(new_panel, current_data):
    changes = {}
    fields = [
        "panel_name",
        "disease_group",
        "disease_subgroup",
        "relevant_diseases",
        "version",
        "last_updated"
    ]


    if new_panel.get("source") == "Ontario Health":
        fields.extend([
            "lab_name"
        ])



    for field in fields:
        new_value = new_panel.get(field)
        current_value = current_data.get(field)



        if field == "version":
            new_compare = (
                str(new_value).strip()
                if new_value is not None
                else None
            )
            current_compare = (
                str(current_value).strip()
                if current_value is not None
                else None
            )

        elif field == "relevant_diseases":
        # Keep your existing relevant_diseases handling here.

            if new_panel.get("source") == "Ontario Health":

                # Match the comma-separated TEXT format used by
                # your Ontario loader.
                if isinstance(new_value, list):
                    new_value = ", ".join(new_value)

                if isinstance(current_value, list):
                    current_value = ", ".join(current_value)

                new_compare = _normalize_text(new_value or "")
                current_compare = _normalize_text(
                    current_value or ""
                )

            else:
              new_compare = _normalize_list(new_value)
              current_compare = _normalize_list(current_value)

              if isinstance(new_value, list) and isinstance(current_value, str):
                 joined_new = ", ".join(str(item).strip() for item in new_value
                )

                 if _normalize_text(joined_new) == _normalize_text(current_value):
                    current_compare = new_compare

        else:
            new_compare = _normalize_text(new_value)
            current_compare = _normalize_text(current_value)

        if new_compare != current_compare:
            changes[field] = {
                "old": current_value,
                "new": new_value                
            }

    return changes






def compare_panel(db: Session, panel):
    panel_name = panel.get("panel_name")
    source_name = panel.get("source")

    gene = None

   

    if source_name in ["GenCC", "ClinGen"]:
        genes = panel.get("genes", [])

        if genes:
            gene = genes[0]

    existing_panel = find_existing_panel(
        db,
        panel_name,
        source_name,
        gene,
        ontario_id=panel.get("ontario_id"),
        source_panel_id=panel.get("source_panel_id")
    )

    if not existing_panel:
        return {
            "status": "new",
            "panel_id": None,
            "panel_name": panel_name,
            "source": source_name,
            "metadata_changes": {},
            "gene_changes": {
                "added": panel.get("genes", []),
                "removed": [],
                "modified": []
            },
            "str_changes": {
                "added": panel.get("strs", []),
                "removed": [],
                "modified": []
            },
            "current_data": None,
            "new_data": panel
        }

    current_data = get_current_panel_data(
        db,
        existing_panel
    )

    metadata_changes = compare_metadata(
        panel,
        current_data
    )

    if not existing_panel.is_active:

        metadata_changes["is_active"] = {
            "old": False,
            "new": True
        }

    gene_changes = compare_genes(
        panel,
        current_data
    )

    str_changes = compare_strs(
        panel,
        current_data
    )

    has_changes = bool(
        metadata_changes
        or gene_changes["added"]
        or gene_changes["removed"]
        or gene_changes["modified"]
        or str_changes["added"]
        or str_changes["removed"]
        or str_changes["modified"]
    )

#********************************************************************************************

    return {
        "status": "changed" if has_changes else "unchanged",
        "panel_id": existing_panel.panel_id,
        "panel_name": panel_name,
        "source": source_name,
        "metadata_changes": metadata_changes,
        "gene_changes": gene_changes,
        "str_changes": str_changes,
        "current_data": current_data,
        "new_data": panel
    }





def _gene_identity(gene, source):
    """Return the stable identity of a gene/assertion within a panel."""
    if source == "GenCC":
        return gene.get("sgc_id")

    if source == "ClinGen":
        return gene.get("assertion_url")

    if source in ("PanelApp UK", "PanelApp AUS"):
        gene_symbol = gene.get("gene_symbol")

        if not gene_symbol:
            return None

        return (
            gene_symbol,
            gene.get("origin_panel_id")
        )

    return gene.get("gene_symbol") 




def compare_genes(new_panel, current_data):
    new_genes = new_panel.get("genes", [])
    current_genes = current_data.get("genes", [])
    source = new_panel.get("source")

    new_gene_dict = {
        _gene_identity(gene, source): gene
        for gene in new_genes
        if _gene_identity(gene, source)
    }

    current_gene_dict = {
        _gene_identity(gene, source): gene
        for gene in current_genes
        if _gene_identity(gene, source)
    }

    new_keys = set(new_gene_dict.keys())
    current_keys = set(current_gene_dict.keys())

    added = [
        new_gene_dict[key]
        for key in sorted(new_keys - current_keys, key=repr)
    ]

    removed = [
        current_gene_dict[key]
        for key in sorted(current_keys - new_keys, key=repr)
    ]

    modified = []

    # These fields describe the assertion/gene data itself.
    mutable_fields = [
        "gene_symbol",
        "confidence_level",
        "phenotypes",
        "moi",
        "submitter"
    ]

    for key in sorted(new_keys & current_keys, key=repr):
        new_gene = new_gene_dict[key]
        current_gene = current_gene_dict[key]
        changes = {}

        for field in mutable_fields:
            new_value = new_gene.get(field)
            current_value = current_gene.get(field)

            if field == "phenotypes":
                different = (
                    _normalize_list(new_value)
                    != _normalize_list(current_value)
                )
            else:
                different = new_value != current_value

            if different:
                changes[field] = {
                    "old": current_value,
                    "new": new_value
                }

        if changes:
            modified.append({
                "identity": key,
                "origin_panel_id": new_gene.get("origin_panel_id"),
                "gene_symbol": new_gene.get("gene_symbol"),
                "assertion_url": new_gene.get("assertion_url"),
                "sgc_id": new_gene.get("sgc_id"),
                "changes": changes
            })

    return {
        "added": added,
        "removed": removed,
        "modified": modified
    }


def _str_identity(str_data, source):
    entity_name = str_data.get("entity_name")

    if not entity_name:
        return None

    if source in ("PanelApp UK", "PanelApp AUS"):
        return (
            entity_name,
            str_data.get("origin_panel_id")
        )

    return entity_name


def compare_strs(new_panel, current_data):
    new_strs = new_panel.get("strs", [])
    current_strs = current_data.get("strs", [])

    source = new_panel.get("source")

    new_str_dict = {
        _str_identity(str_data, source): str_data
        for str_data in new_strs
        if _str_identity(str_data, source)
    }

    current_str_dict = {
        _str_identity(str_data, source): str_data
        for str_data in current_strs
        if _str_identity(str_data, source)
    }

        # new_str_dict = {
        #     str_data.get("entity_name"): str_data
        #     for str_data in new_strs
        #     if str_data.get("entity_name")
        # }

        # current_str_dict = {
        #     str_data.get("entity_name"): str_data
        #     for str_data in current_strs
        #     if str_data.get("entity_name")
        # }

    new_names = set(new_str_dict.keys())
    current_names = set(current_str_dict.keys())

    added = [
        new_str_dict[name]
        for name in sorted(new_names - current_names,key=repr)
    ]

    removed = [
        current_str_dict[name]
        for name in sorted(current_names - new_names,key=repr)
    ]

    modified = []

    for name in sorted(new_names & current_names,key=repr):
        new_str = new_str_dict[name]
        current_str = current_str_dict[name]
        changes = {}

        for field in [
            "gene_symbol",
            "confidence_level",
            "phenotypes",
            "repeated_sequence"
        ]:
            new_value = new_str.get(field)
            current_value = current_str.get(field)

            if field == "phenotypes":
                different = (
                    _normalize_list(new_value)
                    != _normalize_list(current_value)
                )
            else:
                different = new_value != current_value

            if different:
                changes[field] = {
                    "old": current_value,
                    "new": new_value
                }

        if changes:
            modified.append({
                "entity_name": new_str.get("entity_name"),
                "origin_panel_id": new_str.get("origin_panel_id"),
                "changes": changes
            })
            # modified.append({
            #     "entity_name": name,
            #     "changes": changes,
            #     "origin_panel_id": new_str.get("origin_panel_id"),
            # })

    return {
        "added": added,
        "removed": removed,
        "modified": modified
    }




def get_current_panel_data(db: Session, panel):
    source = (
        db.query(Source)
        .filter(Source.source_id == panel.source_id)
        .first()
    )

    version = None
    if panel.version_id:
        version = (
            db.query(Version)
            .filter(Version.version_id == panel.version_id)
            .first()
        )

    panel_genes = (
        db.query(PanelGene, Gene)
        .join(Gene, PanelGene.gene_id == Gene.gene_id)
        .filter(PanelGene.panel_id == panel.panel_id)
        .all()
    )

    genes = []
    for panel_gene, gene in panel_genes:
        genes.append({
            "gene_symbol": gene.gene_symbol,
            "confidence_level": panel_gene.confidence_level,
            "phenotypes": panel_gene.phenotypes,
            "moi": panel_gene.moi,
            "submitter": panel_gene.submitter,
            "sgc_id": panel_gene.sgc_id,
            "origin_panel_id": panel_gene.origin_panel_id,
            # getattr keeps comparison.py safe until the model column is added.
            "assertion_url": getattr(panel_gene, "assertion_url", None)
        })

    panel_strs = (
        db.query(PanelSTR, STR)
        .join(STR, PanelSTR.str_id == STR.str_id)
        .filter(PanelSTR.panel_id == panel.panel_id)
        .all()
    )

    strs = []
    for panel_str, str_entity in panel_strs:
        gene = (
            db.query(Gene)
            .filter(Gene.gene_id == str_entity.gene_id)
            .first()
        )

        strs.append({
            "entity_name": str_entity.entity_name,
            "gene_symbol": gene.gene_symbol if gene else None,
            "origin_panel_id": panel_str.origin_panel_id,
            "confidence_level": str_entity.confidence_level,
            "phenotypes": str_entity.phenotypes,
            "repeated_sequence": str_entity.repeated_sequence
        })

    return {
        "panel_id": panel.panel_id,
        "source_panel_id": panel.source_panel_id,
        "child_panel_ids": panel.child_panel_ids,        
        "is_active": panel.is_active,
        "panel_name": panel.panel_name,
        "disease_group": panel.disease_group,
        "disease_subgroup": panel.disease_subgroup,
        "relevant_diseases": panel.relevant_diseases,
        "ontario_id": panel.ontario_id,
        "lab_name": panel.lab_name,
        "source": source.source_name if source else None,
        "version": version.version_number if version else None,
        "last_updated": (
            version.last_updated.strftime("%Y-%m-%d")
            if version and version.last_updated else None
        ),
        "genes": genes,
        "strs": strs
    }







#orphanet data comparison


ORPHANET_METADATA_FIELDS = (
    "disease_name",
    "orphanet_url",
    "disorder_group",
    "age_at_onset",
    "inheritance",
    "is_active",
)

ORPHANET_EPIDEMIOLOGY_FIELDS = {
    "prevalence_type": "PrevalenceType",
    "prevalence_qualification": "PrevalenceQualification",
    "prevalence_geography": "PrevalenceGeographic",
    "prevalence_class": "PrevalenceClass",
    "reported_value": "ValMoy",
    "reference": "Source",
    "validation_status": "PrevalenceValidationStatus",
}


def _orphanet_reported_value(value, qualification):
    if (qualification or "").strip().casefold() == "class only":
        return None

    if value is None or str(value).strip() == "":
        return None

    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError(f"Invalid Orphanet reported value: {value!r}")

    # Use a JSON-compatible decimal string without losing precision.
    if number == 0:
        return "0"

    text = format(number, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _orphanet_epidemiology_row(record, *, from_api):
    if from_api:
        row = {
            field: record.get(api_field)
            for field, api_field in ORPHANET_EPIDEMIOLOGY_FIELDS.items()
        }
    else:
        row = {
            field: getattr(record, field)
            for field in ORPHANET_EPIDEMIOLOGY_FIELDS
        }

    row["reported_value"] = _orphanet_reported_value(
        row["reported_value"],
        row["prevalence_qualification"],
    )
    return row





def get_current_orphanet_data(disease):
    return {
        "orpha_code": disease.orpha_code,
        "source": disease.source,
        "disease_name": disease.disease_name,
        "orphanet_url": disease.orphanet_url,
        "disorder_group": disease.disorder_group,
        "age_at_onset": sorted(disease.age_at_onset or []),
        "inheritance": sorted(disease.inheritance or []),
        "is_active": disease.is_active,
        "epidemiology": [
            _orphanet_epidemiology_row(record, from_api=False)
            for record in disease.epidemiology
        ],
    }


def _orphanet_epidemiology_diff(current_rows, incoming_rows):
    fields = tuple(ORPHANET_EPIDEMIOLOGY_FIELDS)
    current = Counter(tuple(row[field] for field in fields) for row in current_rows)
    incoming = Counter(tuple(row[field] for field in fields) for row in incoming_rows)

    return {
        "added": [
            dict(zip(fields, values))
            for values in (incoming - current).elements()
        ],
        "removed": [
            dict(zip(fields, values))
            for values in (current - incoming).elements()
        ],
    }


def compare_orphanet_data(db: Session, normalized_data, *, detect_removals=True,scope_codes=None,):
    """Compare a complete normalized Orphadata epidemiology snapshot."""
    if not isinstance(normalized_data, list) or not normalized_data:
        raise ValueError("Expected a non-empty Orphanet snapshot.")

    incoming_by_code = {}

    for disease in normalized_data:
        code = disease["orpha_code"]
        if type(code) is not int or code <= 0 or code in incoming_by_code:
            raise ValueError(f"Invalid or duplicate ORPHAcode: {code!r}")
        if disease["source"] != "Orphanet":
            raise ValueError(f"Unexpected source for ORPHA:{code}")

        incoming_by_code[code] = {
            "orpha_code": code,
            "source": disease["source"],
            "disease_name": disease["disease_name"],
            "orphanet_url": disease.get("orphanet_url"),
            "disorder_group": disease.get("disorder_group"),
            "age_at_onset": sorted(disease.get("age_at_onset") or []),
            "inheritance": sorted(disease.get("inheritance") or []),
            "is_active": True,
            "epidemiology": [
                _orphanet_epidemiology_row(record, from_api=True)
                for record in disease["epidemiology"]
            ],
        }

    # diseases = (
    #     db.query(OrphanetDisease)
    #     .options(selectinload(OrphanetDisease.epidemiology))
    #     .all()
    # )
    query = db.query(OrphanetDisease)

    if scope_codes is not None:
        query = query.filter(OrphanetDisease.orpha_code.in_(scope_codes))

    diseases = query.options(selectinload(OrphanetDisease.epidemiology)).all()
    
    
    
    current_by_code = {
 
 
    disease.orpha_code: get_current_orphanet_data(disease)
    for disease in diseases
    
    
    }

    results = []

    for code in sorted(incoming_by_code.keys() | current_by_code.keys()):
        current = current_by_code.get(code)
        incoming = incoming_by_code.get(code)
        metadata_changes = {}
        epidemiology_changes = {"added": [], "removed": []}

        if incoming is None:
          if not detect_removals or not current["is_active"]:
            continue

          status = "removed"
          incoming = {**current, "is_active": False}
          metadata_changes["is_active"] = {"old": True, "new": False}

       

        elif current is None:
            status = "new"
            epidemiology_changes["added"] = incoming["epidemiology"]

        else:
            metadata_changes = {
                field: {"old": current[field], "new": incoming[field]}
                for field in ORPHANET_METADATA_FIELDS
                if current[field] != incoming[field]
            }
            epidemiology_changes = _orphanet_epidemiology_diff(
                current["epidemiology"],
                incoming["epidemiology"],
            )
            status = (
                "changed"
                if metadata_changes or any(epidemiology_changes.values())
                else "unchanged"
            )

        results.append({
            "status": status,
            "orpha_code": code,
            "source": incoming["source"],
            "disease_name": incoming["disease_name"],
            "metadata_changes": metadata_changes,
            "epidemiology_changes": epidemiology_changes,
            "current_data": current,
            "new_data": incoming,
        })

    return results






