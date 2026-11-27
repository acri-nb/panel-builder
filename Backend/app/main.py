from copy import deepcopy
from datetime import datetime ,date
import hashlib
import json
from time import perf_counter
from typing import Counter
from fastapi import FastAPI, Depends ,HTTPException,BackgroundTasks
from sqlalchemy.orm import Query, Session,selectinload
from db_SQLAlchemy import SessionLocal
from model import OrphanetDisease, Panel, Gene, PanelChange, PanelGene, Source, STR, PanelSTR, Version, PanelVersion, PanelVersionGene, PanelVersionStr
from schema import LabPanelCreate,LabPanelCopyCreate, LabSourceReviewCreate, LabSourceUpdateSelection
from update.approval import (
    approve_external_change,
    reject_external_change
)
from fastapi import Query as ApiQuery
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import UUID, String, case, cast, func
from sqlalchemy import and_, or_, select
from collections import Counter, defaultdict
from threading import Lock
from uuid import uuid4
from update.test_on_source import (
        run_panelapp_aus_update,
        run_panelapp_uk_update,
        run_blueprint_update,
        run_ontario_update,
        run_clingen_update,
        run_gencc_update,
    )
from datetime import date
from fastapi.encoders import jsonable_encoder
from update.comparison import compare_metadata, get_current_panel_data

from uuid import UUID as PythonUUID, uuid4







app = FastAPI()


EXTERNAL_UPDATE_SOURCES = [
    "PanelApp AUS",
    "PanelApp UK",
    "Blueprint Genetics",
    "Ontario Health",
    "ClinGen",
    "GenCC",
    "Orphanet"

]
external_update_runs = {}
active_external_update_run_id = None
external_update_runs_lock = Lock()



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()





@app.get("/panels")
def get_panels(
    limit: int = 50,
    offset: int = 0,
    source_id: int | None = None,
    name: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Panel).filter(
        Panel.is_active == True
    )

    if source_id is not None:
        query = query.filter(
            Panel.source_id == source_id
        )





    if name and name.strip():
        latest_version_id = (
            select(PanelVersion.panel_version_id)
            .where(PanelVersion.panel_id == Panel.panel_id)
            .order_by(PanelVersion.version_number.desc())
            .limit(1)
            .correlate(Panel)
            .scalar_subquery()
        )

        matching_lab_name = (
            select(PanelVersion.panel_version_id)
            .where(
                PanelVersion.panel_version_id == latest_version_id,
                PanelVersion.panel_name.ilike(f"%{name.strip()}%")
            )
            .correlate(Panel)
            .exists()
        )

        query = query.filter(
            or_(
                and_(
                    Panel.source_id == 7,
                    matching_lab_name
                ),
                and_(
                    Panel.source_id != 7,
                    Panel.panel_name.ilike(f"%{name.strip()}%")
                )
            )
        )






    total = query.count()

    panels = (
        query
        .order_by(Panel.panel_id)
        .limit(limit)
        .offset(offset)
        .all()
    )

    results = []

    for panel in panels:
        panel_name = panel.panel_name
        relevant_diseases = panel.relevant_diseases

        # Use the latest laboratory version's name.
        if panel.source_id == 7:
            latest_version = (
                db.query(PanelVersion)
                .filter(
                    PanelVersion.panel_id == panel.panel_id
                )
                .order_by(
                    PanelVersion.version_number.desc()
                )
                .first()
            )

            if latest_version:
                panel_name = latest_version.panel_name
                relevant_diseases = latest_version.relevant_diseases

        results.append({
            "panel_id": panel.panel_id,
            "source_panel_id": panel.source_panel_id,
            "child_panel_ids": panel.child_panel_ids,
            "panel_name": panel_name,
            "relevant_diseases": relevant_diseases,
            "source_id": panel.source_id,
            "is_active": panel.is_active,
            "is_copied": (
                panel.source_id == 7
                and bool(
                     panel.copied_from_panel_ids
                     or panel.copied_from_panel_id is not None
                     or panel.copied_from_group
        )
    )

        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": results
    }



# here's how enter a panel name : http://127.0.0.1:8000/panels/search?name=Angelman
# here's how enter a gene name : http://127.0.0.1:8000/panels/search?gene=UBE3A
#here's how u enter disease name : http://127.0.0.1:8000/panels/search?disease=Angelman

# here's how u enter them combined : http://127.0.0.1:8000/panels/search?name=Angelman&gene=UBE3A
#easy search panel : Epidermolysis , gene PKP1 disease:Abnormal blistering of the skin/ HP:0008066 
#HPO entry that has 3 panels : HP:0001943




def get_origin_panel_names(db: Session):
    rows = (
        db.query(
            Panel.source_id,
            Panel.source_panel_id,
            Panel.panel_name
        )
        .join(Source, Panel.source_id == Source.source_id)
        .filter(
            Source.source_name.in_(["PanelApp UK", "PanelApp AUS"]),
            Panel.source_panel_id.isnot(None)
        )
        .all()
    )

    return {
        (source_id, source_panel_id): panel_name
        for source_id, source_panel_id, panel_name in rows
    }





@app.get("/panels/search")
def search_panels(
    name: str | None = None,
    gene: str | None = None,
    disease: str | None = None,
    limit: int | None = ApiQuery(default=None, ge=1, le=100),
    offset: int = ApiQuery(default=0, ge=0),
    db: Session = Depends(get_db)
):
    # Find the latest laboratory version for each panel.
    latest_version_id = (
        select(PanelVersion.panel_version_id)
        .where(PanelVersion.panel_id == Panel.panel_id)
        .order_by(PanelVersion.version_number.desc())
        .limit(1)
        .correlate(Panel)
        .scalar_subquery()
    )

    query = (
        db.query(Panel, PanelVersion)
        .outerjoin(
            PanelVersion,
            and_(
                Panel.source_id == 7,
                PanelVersion.panel_version_id == latest_version_id
            )
        )
        .filter(Panel.is_active == True)
    )

    # Search laboratory version names or external panel names.
    if name:
        query = query.filter(
            or_(
                and_(
                    Panel.source_id == 7,
                    PanelVersion.panel_name.ilike(f"%{name}%")
                ),
                and_(
                    Panel.source_id != 7,
                    Panel.panel_name.ilike(f"%{name}%")
                )
            )
        )

    # Search metadata from the correct tables.
    if disease:
        query = query.filter(
            or_(
                and_(
                    Panel.source_id == 7,
                    or_(
                        PanelVersion.disease_group.ilike(f"%{disease}%"),
                        PanelVersion.disease_subgroup.ilike(f"%{disease}%"),
                        PanelVersion.relevant_diseases.ilike(f"%{disease}%")
                    )
                ),
                and_(
                    Panel.source_id != 7,
                    or_(
                        Panel.disease_group.ilike(f"%{disease}%"),
                        Panel.disease_subgroup.ilike(f"%{disease}%"),
                        Panel.relevant_diseases.ilike(f"%{disease}%")
                    )
                )
            )
        )

    if gene:
        # External panels containing the searched gene.
        external_matches = (
            select(PanelGene.panel_id)
            .join(Gene, Gene.gene_id == PanelGene.gene_id)
            .where(Gene.gene_symbol.ilike(f"%{gene}%"))
        )

        # Laboratory versions containing the searched gene.
        laboratory_matches = (
            select(PanelVersionGene.panel_version_id)
            .join(Gene, Gene.gene_id == PanelVersionGene.gene_id)
            .where(Gene.gene_symbol.ilike(f"%{gene}%"))
        )

        query = query.filter(
            or_(
                and_(
                    Panel.source_id == 7,
                    PanelVersion.panel_version_id.in_(laboratory_matches)
                ),
                and_(
                    Panel.source_id != 7,
                    Panel.panel_id.in_(external_matches)
                )
            )
        )


    total_groups = None

    if limit is not None:
        grouped_source_ids = [
            source_id
            for (source_id,) in (
                db.query(Source.source_id)
                .filter(Source.source_name.in_(["ClinGen", "GenCC"]))
                .all()
            )
            ]

        # ClinGen/GenCC: one source + disease name is one displayed result.
        # Other sources: each panel ID is one displayed result.
        group_key = case(
        (
        Panel.source_id.in_(grouped_source_ids),
        func.concat(
            "disease:",
            cast(Panel.source_id, String),
            ":",
            func.lower(func.trim(Panel.panel_name))
        )
        ),
           else_=func.concat("panel:", cast(Panel.panel_id, String))
        )

        matched = (
        query.with_entities(
        Panel.panel_id.label("panel_id"),
        group_key.label("group_key")
        )
        .subquery()
        )

        total_groups = (
        db.query(func.count(func.distinct(matched.c.group_key)))
        .scalar()
        )

        page_groups = (
        db.query(matched.c.group_key)
        .group_by(matched.c.group_key)
        .order_by(func.min(matched.c.panel_id))
        .offset(offset)
        .limit(limit)
        .all()
        )

        page_keys = [group_key for (group_key,) in page_groups]

        panel_ids = (   
        db.query(matched.c.panel_id)
        .filter(matched.c.group_key.in_(page_keys))
        )

        query = query.filter(Panel.panel_id.in_(panel_ids))



    started = perf_counter()
   
    panels = query.order_by(Panel.panel_id).all()
    
    print(
      f"Panel query: {perf_counter() - started:.2f}s "
      f"({len(panels)} panel records)"
    )

    details_started = perf_counter()




#attempt to fetch data to lighten the api response time 

    # Collect the source and version IDs needed by external panels.
    external_source_ids = {
        panel.source_id
        for panel, latest_version in panels
        if panel.source_id != 7 and panel.source_id is not None
    }

    external_version_ids = {
        panel.version_id
        for panel, latest_version in panels
        if panel.source_id != 7 and panel.version_id is not None
    }

    # Fetch all needed sources in one query.
    sources_by_id = {}

    if external_source_ids:
        sources_by_id = {
            source.source_id: source
            for source in (
                db.query(Source)
                .filter(Source.source_id.in_(external_source_ids))
                .all()
            )
        }

    # Fetch all needed external versions in one query.
    versions_by_id = {}

    if external_version_ids:
        versions_by_id = {
            version.version_id: version
            for version in (
                db.query(Version)
                .filter(Version.version_id.in_(external_version_ids))
                .all()
            )
        }








    results = []
    
    origin_panel_names = get_origin_panel_names(db)

    external_panel_ids = [
        panel.panel_id
        for panel, latest_version in panels
        if panel.source_id != 7
    ]

    external_genes_by_panel = {}

    if external_panel_ids:
        external_gene_rows = (
            db.query(PanelGene, Gene)
            .join(Gene, Gene.gene_id == PanelGene.gene_id)
            .filter(PanelGene.panel_id.in_(external_panel_ids))
            .all()
        )

        for link, gene_record in external_gene_rows:
            external_genes_by_panel.setdefault(
                link.panel_id, []
            ).append((link, gene_record))

    for panel, latest_version in panels:

        if panel.source_id == 7:
            # An incomplete laboratory panel cannot provide version data.
            if latest_version is None:
                continue

            metadata = latest_version
            source_name = "Laboratory"
            version_number = latest_version.version_number
            last_updated = latest_version.last_updated

            gene_rows = (
                db.query(PanelVersionGene, Gene)
                .join(
                    Gene,
                    Gene.gene_id == PanelVersionGene.gene_id
                )
                .filter(
                    PanelVersionGene.panel_version_id
                    == latest_version.panel_version_id
                )
                .all()
            )

            genes = [
                {
                    "gene_symbol": gene_record.gene_symbol,
                    "confidence_level": link.confidence_level,
                    "phenotypes": link.phenotypes,
                    "moi": None,
                    "submitter": None
                }
                for link, gene_record in gene_rows
            ]

            str_rows = (
                db.query(PanelVersionStr, STR, Gene)
                .join(
                    STR,
                    STR.str_id == PanelVersionStr.str_id
                )
                .outerjoin(Gene, Gene.gene_id == STR.gene_id)
                .filter(
                    PanelVersionStr.panel_version_id
                    == latest_version.panel_version_id
                )
                .all()
            )

            strs = [
                {
                    "str_id": str_record.str_id,
                    "entity_name": str_record.entity_name,
                    "gene_id": str_record.gene_id,
                    "gene_symbol": (
                        gene_record.gene_symbol if gene_record else None
                    ),
                    "confidence_level": link.confidence_level,
                    "phenotypes": link.phenotypes,
                    "repeated_sequence": str_record.repeated_sequence
                }
                for link, str_record, gene_record in str_rows
            ]

        else:
            metadata = panel

            # source = (
            #     db.query(Source)
            #     .filter(Source.source_id == panel.source_id)
            #     .first()
            # )

            # version = (
            #     db.query(Version)
            #     .filter(Version.version_id == panel.version_id)
            #     .first()
            # )
            source = sources_by_id.get(panel.source_id)
            version = versions_by_id.get(panel.version_id)

            source_name = source.source_name if source else None
            version_number = version.version_number if version else None
            last_updated = version.last_updated if version else None

            # gene_rows = (
            #     db.query(PanelGene, Gene)
            #     .join(Gene, Gene.gene_id == PanelGene.gene_id)
            #     .filter(PanelGene.panel_id == panel.panel_id)
            #     .all()
            # )
            
            gene_rows = external_genes_by_panel.get(
                panel.panel_id, []
            )

            genes = [
                {
                    "gene_symbol": gene_record.gene_symbol,
                    "confidence_level": link.confidence_level,
                    "origin_panel_id": link.origin_panel_id,
                    "origin_panel_name": origin_panel_names.get(
                        (panel.source_id, link.origin_panel_id)
                    ),
                    "phenotypes": link.phenotypes,
                    "moi": link.moi,
                    "submitter": link.submitter
                }
                for link, gene_record in gene_rows
            ]

            str_rows = (
                db.query(STR,PanelSTR, Gene)
                .join(PanelSTR, PanelSTR.str_id == STR.str_id)
                .outerjoin(Gene, Gene.gene_id == STR.gene_id)
                .filter(PanelSTR.panel_id == panel.panel_id)
                .all()
            )

            strs = [
                {
                    "str_id": str_record.str_id,
                    "entity_name": str_record.entity_name,
                    "gene_id": str_record.gene_id,
                    "gene_symbol": (
                        gene_record.gene_symbol if gene_record else None
                    ),
                    "origin_panel_id": str_link.origin_panel_id,
                    "origin_panel_name": origin_panel_names.get(
                        (panel.source_id, str_link.origin_panel_id)
                    ),
                    "confidence_level": str_record.confidence_level,
                    "phenotypes": str_record.phenotypes,
                    "repeated_sequence": str_record.repeated_sequence
                }
                for str_record, str_link, gene_record in str_rows
            ]

        results.append({
            "panel_id": panel.panel_id,
            "source_panel_id": panel.source_panel_id,
            "child_panel_ids": panel.child_panel_ids,
            "panel_name": metadata.panel_name,
            "lab_name": panel.lab_name,
            "disease_group": metadata.disease_group,
            "disease_subgroup": metadata.disease_subgroup,
            "relevant_diseases": metadata.relevant_diseases,
            "source": source_name,
            "version": version_number,
            "last_updated": last_updated,
            "genes": genes,
            "strs": strs
        })

    print(
                f"Related data and response building: "
                f"{perf_counter() - details_started:.2f}s"
            )



    if limit is not None:
        return {
            "total": total_groups,
            "limit": limit,
            "offset": offset,
            "data": results
        }

    return results





@app.get("/orphanet/diseases")
def search_orphanet_diseases(
    q: str = ApiQuery(..., min_length=1, max_length=200),
    limit: int = ApiQuery(default=25, ge=1, le=100),
    offset: int = ApiQuery(default=0, ge=0),
    db: Session = Depends(get_db),
):
    term = q.strip()
    if not term:
        raise HTTPException(
            status_code=422,
            detail="Enter a disease name.",
        )

    # Treat SQL wildcard characters in the search term as literal text.
    escaped_term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    query = db.query(OrphanetDisease).filter(
        OrphanetDisease.disease_name.ilike(f"%{escaped_term}%", escape="\\"),
        OrphanetDisease.is_active.is_(True),
    )

    total = query.count()
    diseases = (
        query.options(selectinload(OrphanetDisease.epidemiology))
        .order_by(OrphanetDisease.disease_name, OrphanetDisease.orpha_code)
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        {
            "orpha_code": disease.orpha_code,
            "disease_name": disease.disease_name,
            "source": disease.source,
            "orphanet_url": disease.orphanet_url,
            "disorder_group": disease.disorder_group,
            "age_at_onset": disease.age_at_onset,
            "inheritance": disease.inheritance,
            "epidemiology": [
                {
                    "epidemiology_id": record.epidemiology_id,
                    "prevalence_type": record.prevalence_type,
                    "prevalence_qualification": record.prevalence_qualification,
                    "prevalence_geography": record.prevalence_geography,
                    "prevalence_class": record.prevalence_class,
                    "reported_value": record.reported_value,
                    "reference": record.reference,
                    "validation_status": record.validation_status,
                }
                for record in sorted(
                    disease.epidemiology,
                    key=lambda record: record.epidemiology_id,
                )
            ],
        }
        for disease in diseases
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

















@app.get("/panels/{panel_id}")
def get_panel(
    panel_id: int,
    db: Session = Depends(get_db)
):
    panel = db.query(Panel).filter(
        Panel.panel_id == panel_id,
        Panel.is_active == True
    ).first()

    if panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    # Laboratory panel
    if panel.source_id == 7:

        latest_version = (
            db.query(PanelVersion)
            .filter(
                PanelVersion.panel_id == panel.panel_id
            )
            .order_by(
                PanelVersion.version_number.desc()
            )
            .first()
        )

        if latest_version is None:
            raise HTTPException(
                status_code=404,
                detail="Panel version not found"
            )

        original_ids = panel.copied_from_panel_ids or []

        # Support older copies using the single-reference field.
        if not original_ids and panel.copied_from_panel_id is not None:
            original_ids = [panel.copied_from_panel_id]

        originals = (
            db.query(Panel, Source.source_name)
            .join(Source, Panel.source_id == Source.source_id)
            .filter(Panel.panel_id.in_(original_ids))
            .order_by(Panel.panel_id)
            .all()
        )

        copied_from = [
            {
                "panel_id": original.panel_id,
                "panel_name": original.panel_name,
                "source": original_source,
                "is_active": original.is_active
            }
            for original, original_source in originals
        ]

        return {
            "panel_id": panel.panel_id,
            "panel_name": latest_version.panel_name,
            "disease_group": latest_version.disease_group,
            "disease_subgroup": latest_version.disease_subgroup,
            "relevant_diseases": latest_version.relevant_diseases,
            "source": "Laboratory",
            "version": latest_version.version_number,
            "last_updated": latest_version.last_updated,
            "copied_from": copied_from,
            "copied_from_group": panel.copied_from_group
        }

    # External panel
    result = (
        db.query(
            Panel,
            Source.source_name,
            Version.version_number,
            Version.last_updated
        )
        .join(
            Source,
            Panel.source_id == Source.source_id
        )
        .join(
            Version,
            Panel.version_id == Version.version_id
        )
        .filter(
            Panel.panel_id == panel_id
        )
        .first()
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    panel, source_name, version_number, last_updated = result

    return {
        "panel_id": panel.panel_id,
        "panel_name": panel.panel_name,
        "lab_name": panel.lab_name,
        "disease_group": panel.disease_group,
        "disease_subgroup": panel.disease_subgroup,
        "relevant_diseases": panel.relevant_diseases,
        "source": source_name,
        "version": version_number,
        "last_updated": last_updated
    
    }






@app.get("/panels/{panel_id}/genes")
def get_panel_genes(
    panel_id: int,
    db: Session = Depends(get_db)
):
    
    panel = db.query(Panel).filter(
        Panel.panel_id == panel_id,
        Panel.is_active == True
    ).first()

    if panel is None:
       raise HTTPException(
          status_code=404,
          detail="Panel not found"
    )

        # Laboratory panel
    if panel.source_id == 7:

        latest_version = (
            db.query(PanelVersion)
            .filter(
                PanelVersion.panel_id == panel.panel_id
            )
            .order_by(
                PanelVersion.version_number.desc()
            )
            .first()
        )

        if latest_version is None:
            raise HTTPException(
                status_code=404,
                detail="Panel version not found"
            )

        version_genes = (
            db.query(
                Gene.gene_symbol,
                PanelVersionGene.confidence_level,
                PanelVersionGene.phenotypes,
                PanelVersionGene.moi,
                PanelVersionGene.lab_entry_id
            )
            .join(
                PanelVersionGene,
                Gene.gene_id == PanelVersionGene.gene_id
            )
            .filter(
                PanelVersionGene.panel_version_id == latest_version.panel_version_id
            )
            .all()
        )



        return [
            {
                "gene_symbol": gene_symbol,
                "confidence_level": confidence_level,
                "phenotypes": phenotypes,
                "moi": moi,
                "lab_entry_id": lab_entry_id,
                "source": "Laboratory"
            }
            for gene_symbol, confidence_level ,phenotypes ,moi,lab_entry_id in version_genes
        ]


    genes = (
        db.query(
            Gene.gene_symbol,
            PanelGene.panel_gene_id,
            PanelGene.confidence_level,
            PanelGene.phenotypes,
            Source.source_name,
            PanelGene.moi,
            PanelGene.submitter,
            PanelGene.sgc_id,
            PanelGene.origin_panel_id
        )
        .join(
            PanelGene,
            Gene.gene_id == PanelGene.gene_id
        )
        .join(
            Panel,
            PanelGene.panel_id == Panel.panel_id
        )
        .join(
            Source,
            Panel.source_id == Source.source_id
        )
        .filter(Panel.panel_id == panel_id)
        .all()
    )


    origin_panel_names = get_origin_panel_names(db)
    return [
        {
            "gene_symbol": gene_symbol,
            "panel_gene_id": panel_gene_id,
            "confidence_level": confidence_level,
            "phenotypes": phenotypes,
            "source": source_name,
            "submitter": submitter,
            "moi": moi,
            "sgc_id": sgc_id,
            "origin_panel_id": origin_panel_id,
            "origin_panel_name": origin_panel_names.get(
                (panel.source_id, origin_panel_id)
            )
            
        }
        for gene_symbol,panel_gene_id, confidence_level, phenotypes,source_name , moi ,submitter,sgc_id,origin_panel_id in genes
    ]






@app.get("/panels/{panel_id}/strs")
def get_panel_strs(
    panel_id: int,
    db: Session = Depends(get_db)
):
    panel = db.query(Panel).filter(
        Panel.panel_id == panel_id,
        Panel.is_active == True
           ).first()
           
    if panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
               )

    if panel.source_id == 7:
        latest_version = (
                db.query(PanelVersion)
                .filter(
                    PanelVersion.panel_id == panel.panel_id
                )
                .order_by(
                    PanelVersion.version_number.desc()
                )
                .first()
            )
        if latest_version is None:
            raise HTTPException(
                status_code=404,
                detail="Panel version not found"
                            )
        
       

        version_strs = (
            db.query(STR,PanelVersionStr, Gene)
            .join(
                PanelVersionStr,
                STR.str_id == PanelVersionStr.str_id
            )
            .outerjoin(
                Gene,
                STR.gene_id == Gene.gene_id
            )
            .filter(
                PanelVersionStr.panel_version_id 
                == latest_version.panel_version_id
            )
            .all()
        )

        return [
            {
                "str_id": str_record.str_id,
                "lab_entry_id": version_link.lab_entry_id,
                "entity_name": str_record.entity_name,
                "gene_id": str_record.gene_id,
                "gene_symbol": (
                    gene.gene_symbol if gene else None
                ),
                "confidence_level": version_link.confidence_level,
                "phenotypes": version_link.phenotypes,
                "repeated_sequence": str_record.repeated_sequence
            }
            for str_record, version_link, gene in version_strs
        ]

  

    
# External panel


    str_rows = (
        db.query(STR, PanelSTR, Gene)
        .join(
            PanelSTR,
            STR.str_id == PanelSTR.str_id
        )
        .outerjoin(
            Gene,
            STR.gene_id == Gene.gene_id
        )
        .filter(PanelSTR.panel_id == panel_id)
        .all()
    )
    
    origin_panel_names = get_origin_panel_names(db)
    return [
        {
            "str_id": str_record.str_id,
            "entity_name": str_record.entity_name,
            "gene_id": str_record.gene_id,
            "gene_symbol": gene.gene_symbol if gene else None,
            "panel_str_id": link.panel_str_id,
            "origin_panel_id": link.origin_panel_id,
            "origin_panel_name": origin_panel_names.get(
                (panel.source_id, link.origin_panel_id)
            ),
            "confidence_level": str_record.confidence_level,
            "phenotypes": str_record.phenotypes,
            "repeated_sequence": str_record.repeated_sequence
        }
        for str_record, link, gene in str_rows
    ]








@app.get("/grouped-disease")
def get_grouped_disease(
    source: str,
    name: str,
    db: Session = Depends(get_db)
):

    # Only GenCC and ClinGen use this grouped view
    if source not in ["GenCC", "ClinGen"]:
        raise HTTPException(
            status_code=400,
            detail="Grouped disease view is only available for GenCC and ClinGen"
        )

    normalized_name = name.strip().lower()

    # Find every active panel with the same disease name and source
    panels = (
        db.query(Panel)
        .join(
            Source,
            Panel.source_id == Source.source_id
        )
        .filter(
            Source.source_name == source,
            Panel.is_active == True,
            func.lower(func.trim(Panel.panel_name)) == normalized_name
        )
        .all()
    )

    if not panels:
        raise HTTPException(
            status_code=404,
            detail="Grouped disease not found"
        )

    records = []

    for panel in panels:

        # -----------------------------
        # Version information
        # -----------------------------

        version = (
            db.query(Version)
            .filter(
                Version.version_id == panel.version_id
            )
            .first()
        )

        # -----------------------------
        # Genes
        # -----------------------------

        genes = (
            db.query(
                Gene.gene_symbol,
                PanelGene.confidence_level,
                PanelGene.phenotypes,
                PanelGene.moi,
                PanelGene.submitter,
                PanelGene.sgc_id
            )
            .join(
                PanelGene,
                Gene.gene_id == PanelGene.gene_id
            )
            .filter(
                PanelGene.panel_id == panel.panel_id
            )
            .all()
        )

        gene_data = [
            {
                "gene_symbol": gene_symbol,
                "confidence_level": confidence_level,
                "phenotypes": phenotypes,
                "moi": moi,
                "submitter": submitter,
                "sgc_id": sgc_id
            }
            for (
                gene_symbol,
                confidence_level,
                phenotypes,
                moi,
                submitter,
                sgc_id
            ) in genes
        ]

        # -----------------------------
        # STRs
        # -----------------------------

        strs = (
            db.query(
                STR.entity_name,
                Gene.gene_symbol,
                STR.confidence_level,
                STR.phenotypes,
                STR.repeated_sequence
            )
            .join(
                PanelSTR,
                STR.str_id == PanelSTR.str_id
            )
            .outerjoin(
                Gene,
                STR.gene_id == Gene.gene_id
            )
            .filter(
                PanelSTR.panel_id == panel.panel_id
            )
            .all()
        )

        str_data = [
            {
                "entity_name": entity_name,
                "gene_symbol": gene_symbol,
                "confidence_level": confidence_level,
                "phenotypes": phenotypes,
                "repeated_sequence": repeated_sequence
            }
            for (
                entity_name,
                gene_symbol,
                confidence_level,
                phenotypes,
                repeated_sequence
            ) in strs
        ]

        # -----------------------------
        # One original database record
        # -----------------------------

        records.append({
            "panel_id": panel.panel_id,
            "panel_name": panel.panel_name,
            "disease_group": panel.disease_group,
            "disease_subgroup": panel.disease_subgroup,
            "relevant_diseases": panel.relevant_diseases,

            "version": (
                version.version_number
                if version else None
            ),

            "last_updated": (
                version.last_updated
                if version else None
            ),

            "genes": gene_data,
            "strs": str_data
        })

    return {
        "panel_name": panels[0].panel_name,
        "source": source,
        "record_count": len(records),
        "records": records
    }





@app.post("/lab-panels/copy", status_code=201)
def copy_external_panel(
    data: LabPanelCopyCreate,
    db: Session = Depends(get_db)
):
    try:
        # 1. Validate the selected originals.
        original_ids = sorted(set(data.source_record_panel_ids))

        originals = (
            db.query(Panel)
            .filter(
                Panel.panel_id.in_(original_ids),
                Panel.is_active.is_(True)
            )
            .order_by(Panel.panel_id)
            .with_for_update()
            .all()
        )

        if len(originals) != len(original_ids):
            raise HTTPException(
                status_code=400,
                detail="An original panel is missing or inactive"
            )

        source_ids = {panel.source_id for panel in originals}

        if len(source_ids) != 1:
            raise HTTPException(
                status_code=400,
                detail="Copy panels from one source at a time"
            )

        source_id = next(iter(source_ids))

        source = (
            db.query(Source)
            .filter(Source.source_id == source_id)
            .first()
        )

        supported_sources = {
            "PanelApp UK",
            "PanelApp AUS",
            "Blueprint Genetics",
            "Ontario Health",
            "ClinGen"
        }

        if source is None or source.source_name not in supported_sources:
            raise HTTPException(
                status_code=400,
                detail="Unsupported source for copying"
            )

        # 2. Preserve the original ClinGen group identity.
        copied_from_group = None

        if data.track_clingen_group:
            names = {
                panel.panel_name.strip().casefold()
                for panel in originals
            }

            if source.source_name != "ClinGen" or len(names) != 1:
                raise HTTPException(
                    status_code=400,
                    detail="A ClinGen group must share one disease name"
                )

            copied_from_group = {
                "source": "ClinGen",
                "panel_name": originals[0].panel_name
            }

        elif len(originals) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple originals require ClinGen group tracking"
            )

        panel_name = data.panel_name.strip()

        if not panel_name:
            raise HTTPException(
                status_code=400,
                detail="Panel name cannot be empty"
            )

        if not data.genes and not data.strs:
            raise HTTPException(
                status_code=400,
                detail="Select at least one gene or STR"
            )

        # 3. Validate selected association IDs.
        gene_ids = [item.panel_gene_id for item in data.genes]
        str_ids = [item.panel_str_id for item in data.strs]

        if (
            len(gene_ids) != len(set(gene_ids))
            or len(str_ids) != len(set(str_ids))
        ):
            raise HTTPException(
                status_code=400,
                detail="The same association was selected more than once"
            )

        gene_links = (
            db.query(PanelGene)
            .filter(
                PanelGene.panel_id.in_(original_ids),
                PanelGene.panel_gene_id.in_(gene_ids)
            )
            .all()
        )

        str_rows = (
            db.query(PanelSTR, STR)
            .join(STR, PanelSTR.str_id == STR.str_id)
            .filter(
                PanelSTR.panel_id.in_(original_ids),
                PanelSTR.panel_str_id.in_(str_ids)
            )
            .all()
        )

        if len(gene_links) != len(gene_ids):
            raise HTTPException(
                status_code=400,
                detail="A selected gene no longer belongs to the originals"
            )

        if len(str_rows) != len(str_ids):
            raise HTTPException(
                status_code=400,
                detail="A selected STR no longer belongs to the originals"
            )

        genes_by_id = {
            link.panel_gene_id: link
            for link in gene_links
        }


#this retrieves the original gene symbols together 
        originals_by_id = {
            original.panel_id: original
            for original in originals
        }


        referenced_gene_ids = {
           link.gene_id for link in gene_links
    }

        referenced_gene_ids.update(
           original_str.gene_id
            for _, original_str in str_rows
            if original_str.gene_id is not None
     )

        gene_symbols_by_id = dict(
            db.query(Gene.gene_id, Gene.gene_symbol)
            .filter(
                Gene.gene_id.in_(
                    {link.gene_id for link in gene_links}
                )
            )
            .all()
        )


        strs_by_id = {
          link.panel_str_id: (link, original_str)
          for link, original_str in str_rows
        }


        # strs_by_id = {
        #     link.panel_str_id: original_str
        #     for link, original_str in str_rows
        # }


        # 4. Capture full source snapshots, including unselected entries.
        baselines = {}

        for original in originals:
            snapshot = get_current_panel_data(db, original)
            snapshot["source_panel_id"] = original.source_panel_id
            snapshot["child_panel_ids"] = original.child_panel_ids
            baselines[str(original.panel_id)] = snapshot

        # 5. Create the laboratory panel using edited metadata.
        laboratory_panel = Panel(
            panel_name=panel_name,
            disease_group=data.disease_group,
            disease_subgroup=data.disease_subgroup,
            relevant_diseases=data.relevant_diseases,
            source_id=7,
            is_active=True,
            copied_from_panel_ids=original_ids,
            copied_from_group=copied_from_group,
            source_baseline=jsonable_encoder(baselines),
            source_reviewed_at=None
        )

        db.add(laboratory_panel)
        db.flush()

        version_1 = PanelVersion(
            panel_id=laboratory_panel.panel_id,
            version_number=1,
            panel_name=panel_name,
            disease_group=data.disease_group,
            disease_subgroup=data.disease_subgroup,
            relevant_diseases=data.relevant_diseases,
            last_updated=date.today()
        )

        db.add(version_1)
        db.flush()






        # # 6. Save only selected genes, using their edited values.
        # for selected in data.genes:
        #     original_link = genes_by_id[selected.panel_gene_id]

        #     db.add(
        #         PanelVersionGene(
        #             panel_version_id=version_1.panel_version_id,
        #             gene_id=original_link.gene_id,
        #             confidence_level=selected.confidence_level,
        #             phenotypes=selected.phenotypes,
        #             moi=original_link.moi,
        #         )
        #     )





        # 6. Save selected genes with their source tracking.
        for selected in data.genes:
            original_link = genes_by_id[selected.panel_gene_id]
            original_panel = originals_by_id[original_link.panel_id]

            source_reference = {
                "original_panel_id": original_link.panel_id,
                "source": source.source_name,
                "source_panel_id": original_panel.source_panel_id,
                "ontario_id": original_panel.ontario_id,
                "gene_symbol": gene_symbols_by_id[original_link.gene_id],
                "origin_panel_id": original_link.origin_panel_id,
                "assertion_url": original_link.assertion_url,
                "sgc_id": original_link.sgc_id,
            }

            db.add(
                PanelVersionGene(
                    panel_version_id=version_1.panel_version_id,
                    gene_id=original_link.gene_id,
                    confidence_level=selected.confidence_level,
                    phenotypes=selected.phenotypes,
                    moi=original_link.moi,
                    lab_entry_id=uuid4(),
                    source_reference=source_reference,
                )
            )


        # # 7. Save only selected STRs as independent records.
        # for selected in data.strs:
        #     original_str = strs_by_id[selected.panel_str_id]

        #     copied_str = STR(
        #         entity_name=original_str.entity_name,
        #         gene_id=original_str.gene_id,
        #         confidence_level=selected.confidence_level,
        #         phenotypes=selected.phenotypes,
        #         repeated_sequence=selected.repeated_sequence
        #     )

        #     db.add(copied_str)
        #     db.flush()

        #     db.add(
        #         PanelVersionStr(
        #             panel_version_id=version_1.panel_version_id,
        #             str_id=copied_str.str_id,
        #             confidence_level=selected.confidence_level,
        #             phenotypes=selected.phenotypes
        #         )
        #     )

        #  7. Save selected STRs with their source tracking.
        for selected in data.strs:
            original_link, original_str = strs_by_id[
                selected.panel_str_id
            ]

            original_panel = originals_by_id[original_link.panel_id]

            source_reference = {
                "original_panel_id": original_link.panel_id,
                "source": source.source_name,
                "source_panel_id": original_panel.source_panel_id,
                "ontario_id": original_panel.ontario_id,
                "entity_name": original_str.entity_name,
                "gene_symbol": gene_symbols_by_id.get(
                    original_str.gene_id
                ),
                "origin_panel_id": original_link.origin_panel_id,
            }

            copied_str = STR(
                entity_name=original_str.entity_name,
                gene_id=original_str.gene_id,
                confidence_level=selected.confidence_level,
                phenotypes=selected.phenotypes,
                repeated_sequence=selected.repeated_sequence
            )

            db.add(copied_str)
            db.flush()

            db.add(
                PanelVersionStr(
                    panel_version_id=version_1.panel_version_id,
                    str_id=copied_str.str_id,
                    confidence_level=selected.confidence_level,
                    phenotypes=selected.phenotypes,
                    lab_entry_id=uuid4(),
                    source_reference=source_reference
                )
            )








        # Prepare the response before committing.
        result = {
            "panel_id": laboratory_panel.panel_id,
            "panel_name": laboratory_panel.panel_name,
            "source": "Laboratory",
            "version": 1,
            "copied_from_panel_ids": original_ids,
            "gene_count": len(data.genes),
            "str_count": len(data.strs)
        }

        db.commit()
        return result

    except Exception:
        db.rollback()
        raise











@app.post("/panels/{panel_id}/changes")
def create_panel_change(
    panel_id: int,
    panel: LabPanelCreate,
    db: Session = Depends(get_db)
):
    # 1. Find the panel
    existing_panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id,
            Panel.is_active == True
        )
        .first()
    )

    if existing_panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    # 2. Make sure it is a laboratory panel
    if existing_panel.source_id != 7:
        raise HTTPException(
            status_code=400,
            detail="Changes can only be submitted for laboratory panels"
        )

    # 3. Find the latest approved version
    latest_version = (
        db.query(PanelVersion)
        .filter(
            PanelVersion.panel_id == panel_id
        )
        .order_by(
            PanelVersion.version_number.desc()
        )
        .first()
    )

    if latest_version is None:
        raise HTTPException(
            status_code=404,
            detail="No panel version found"
        )

    # 4. Convert the proposed panel to a dictionary
    proposed_data = panel.model_dump(mode="json")
    proposed_data.pop("_source_update_context", None)
    proposed_data["last_updated"] = date.today().isoformat()

    # 5. Create the change request
    new_change = PanelChange(
        panel_id=panel_id,
        change_version_id=latest_version.panel_version_id,
        proposed_data=proposed_data,
        status="pending"
    )

    # 6. Save the change request
    db.add(new_change)
    db.commit()
    db.refresh(new_change)

    # 7. Return the change request
    return {
        "change_id": new_change.change_id,
        "panel_id": new_change.panel_id,
        "change_version_id": new_change.change_version_id,
        "status": new_change.status,
        "proposed_data": new_change.proposed_data,
        "created_at": new_change.created_at
    }







#get only for lab panels
@app.get("/panels/{panel_id}/changes")
def get_panel_changes(
    panel_id: int,
    db: Session = Depends(get_db)
):
    # 1. Check that the panel exists
    panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id
        )
        .first()
    )

    if panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    if panel.source_id != 7:
        raise HTTPException(
            status_code=400,
            detail="This endpoint only lists laboratory changes"
        )

    # 2. Get all change requests for this panel
    changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.panel_id == panel_id,
            #lab panels onlYYYYYY
            PanelChange.change_version_id.isnot(None)
        )
        .order_by(
            PanelChange.created_at.desc()
        )
        .all()
    )

    # if not changes:
    #     raise HTTPException(
    #         status_code=404,
    #         detail="No changes found for this panel"
    #     )

    # 3. Return the change requests
    return [
        {
            "change_id": change.change_id,
            "panel_id": change.panel_id,
            "change_version_id": change.change_version_id,
            "status": change.status,
            "proposed_data": change.proposed_data,
            "created_at": change.created_at,
            "reviewed_at": change.reviewed_at
        }
        for change in changes
    ]









#approve lab panels changes ONLYY
@app.post("/changes/{change_id}/approve")
def approve_panel_change(
    change_id: int,
    db: Session = Depends(get_db)
):
   try:
        # 1. Find the change request
        change = (
            db.query(PanelChange)
            .filter(
                PanelChange.change_id == change_id
            )
            .with_for_update()
            .populate_existing()
            .first()
        )

        if change is None:
            raise HTTPException(
                status_code=404,
                detail="Change request not found"
            )

        # 2. Make sure this is a LABORATORY change
        if change.change_version_id is None:
            raise HTTPException(
                status_code=400,
                detail="This endpoint only approves laboratory panel changes"
            )
    

        # 2. Make sure the change is still pending
        if change.status != "pending":
            raise HTTPException(
                status_code=400,
                detail="This change has already been reviewed"
            )

        # 3. Find the current panel version
        current_version = (
            db.query(PanelVersion)
            .filter(
                PanelVersion.panel_version_id == change.change_version_id
            )
            .first()
        )

        if current_version is None:
            raise HTTPException(
                status_code=404,
                detail="Panel version not found"
            )

        # 4. Calculate the new version number
        panel = (
            db.query(Panel)
            .filter(Panel.panel_id == change.panel_id)
            .with_for_update()
            .first()
        )

        if panel is None or panel.source_id != 7 or not panel.is_active:
            raise HTTPException(
                status_code=400,
                detail="The target must be an active laboratory panel"
            )

        latest_version = (
            db.query(PanelVersion)
            .filter(PanelVersion.panel_id == panel.panel_id)
            .order_by(PanelVersion.version_number.desc())
            .first()
        )

        if (
            latest_version is None
            or latest_version.panel_version_id != change.change_version_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "This request is based on an older panel version. "
                    "Reject it and submit changes from the latest version."
                )
            )

        new_version_number = latest_version.version_number + 1

        # 5. Get the proposed panel data
        proposed_data = change.proposed_data
        
        source_context = proposed_data.get("_source_update_context")
        validated_additions = (
        source_context.get("validated_additions", {})
        if source_context else {}
        )

        # 6. Create the new panel version
        new_version = PanelVersion(
            panel_id=change.panel_id,
            version_number=new_version_number,
            panel_name=proposed_data["panel_name"],
            disease_group=proposed_data.get("disease_group"),
            disease_subgroup=proposed_data.get("disease_subgroup"),
            relevant_diseases=proposed_data.get("relevant_diseases"),
            last_updated=proposed_data["last_updated"]
        )

        db.add(new_version)
        db.flush()

        # # 7. Add the genes to the new version
        # for gene_data in proposed_data.get("genes", []):

        #     gene = (
        #         db.query(Gene)
        #         .filter(
        #             Gene.gene_symbol == gene_data["gene_symbol"]
        #         )
        #         .first()
        #     )

        #     if gene is None:
        #         gene = Gene(
        #             gene_symbol=gene_data["gene_symbol"]
        #         )

        #         db.add(gene)
        #         db.flush()

        #     version_gene = PanelVersionGene(
        #         panel_version_id=new_version.panel_version_id,
        #         gene_id=gene.gene_id,
        #         confidence_level=gene_data.get("confidence_level"),
        #         phenotypes=gene_data.get("phenotypes", [])
        #     )

        #     db.add(version_gene)





        # Existing entries from the version this request was based on.
        existing_gene_rows = (
            db.query(PanelVersionGene, Gene.gene_symbol)
            .join(Gene, Gene.gene_id == PanelVersionGene.gene_id)
            .filter(
                PanelVersionGene.panel_version_id
                == current_version.panel_version_id
            )
            .all()
        )

        existing_by_entry_id = {
            str(link.lab_entry_id): (link, symbol)
            for link, symbol in existing_gene_rows
            if link.lab_entry_id is not None
        }

        seen_entry_ids = set()

        for gene_data in proposed_data.get("genes", []):
            gene_symbol = gene_data["gene_symbol"].strip()
            submitted_id = gene_data.get("lab_entry_id")

            entry_id = uuid4()
            source_reference = None

            if submitted_id is not None:
                entry_key = str(submitted_id)

                if entry_key in seen_entry_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="The same laboratory gene entry was submitted twice"
                    )

                seen_entry_ids.add(entry_key)
                existing = existing_by_entry_id.get(entry_key)

                # if existing is None:
                #     raise HTTPException(
                #         status_code=400,
                #         detail="Gene tracking ID does not belong to the base version"
                #     )

                # previous_link, previous_symbol = existing

                # # Preserve lineage only when this is still the same gene.
                # # A replacement gene receives a new ID without source tracking.
                # if gene_symbol == previous_symbol:
                #     entry_id = previous_link.lab_entry_id
                #     source_reference = previous_link.source_reference




                if existing is not None:
                    previous_link, previous_symbol = existing

                    if gene_symbol == previous_symbol:
                        entry_id = previous_link.lab_entry_id
                        source_reference = previous_link.source_reference

                else:
                    addition = validated_additions.get(entry_key)

                    if (
                        addition is None
                        or addition["gene_symbol"] != gene_symbol
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Gene tracking ID does not belong to the base version"
                        )

                    entry_id = PythonUUID(entry_key)
                    source_reference = addition["source_reference"]
















            gene = (
                db.query(Gene)
                .filter(Gene.gene_symbol == gene_symbol)
                .first()
            )

            if gene is None:
                gene = Gene(gene_symbol=gene_symbol)
                db.add(gene)
                db.flush()

            db.add(
                PanelVersionGene(
                    panel_version_id=new_version.panel_version_id,
                    gene_id=gene.gene_id,
                    confidence_level=gene_data.get("confidence_level"),
                    phenotypes=gene_data.get("phenotypes", []),
                    moi=gene_data.get("moi"),
                    lab_entry_id=entry_id,
                    source_reference=source_reference
                )
            )



        # base_str_rows = (
        #     db.query(PanelVersionStr)
        #     .filter(
        #         PanelVersionStr.panel_version_id
        #         == current_version.panel_version_id
        #     )
        #     .all()
        # ) if source_context else []

        # base_str_ids = {link.str_id for link in base_str_rows}


        base_str_rows = (
            db.query(PanelVersionStr, STR)
            .join(STR, STR.str_id == PanelVersionStr.str_id)
            .filter(
                PanelVersionStr.panel_version_id
                == current_version.panel_version_id
            )
            .all()
        )
        
        base_strs_by_version_row = {
            link.panel_version_str_id: (link, record)
            for link, record in base_str_rows
        }

        seen_source_str_rows = set()
        seen_source_str_entry_ids = set()

        base_strs_by_id = {}

        for previous_link, previous_str in base_str_rows:
            base_strs_by_id.setdefault(
                previous_str.str_id, []
            ).append((previous_link, previous_str))

        base_strs_by_entry_id = {
            str(previous_link.lab_entry_id): (
                previous_link,
                previous_str
            )
            for previous_link, previous_str in base_str_rows
            if previous_link.lab_entry_id is not None
        }

        seen_str_entry_ids = set()
        preserved_str_counts = {}



    # 8. Add STRs while preserving their tracking.
        for str_data in proposed_data.get("strs", []):
            if source_context and source_context.get("str_updates_format") == 1:
                    base_row_id = str_data.get("base_version_str_id")
                    submitted_id = str_data.get("lab_entry_id")
                    entry_key = str(submitted_id) if submitted_id else None

                    if entry_key is not None:
                        if entry_key in seen_source_str_entry_ids:
                            raise HTTPException(
                                status_code=400,
                                detail="Duplicate laboratory STR tracking ID"
                            )

                        seen_source_str_entry_ids.add(entry_key)

                    previous_link = None
                    previous_str = None

                    if base_row_id is not None:
                        if base_row_id in seen_source_str_rows:
                            raise HTTPException(
                                status_code=400,
                                detail="Duplicate base laboratory STR entry"
                            )

                        seen_source_str_rows.add(base_row_id)
                        previous = base_strs_by_version_row.get(base_row_id)

                        if previous is None:
                            raise HTTPException(
                                status_code=400,
                                detail="STR does not belong to the base version"
                            )

                        previous_link, previous_str = previous

                        expected_id = (
                            str(previous_link.lab_entry_id)
                            if previous_link.lab_entry_id else None
                        )

                        if (
                            entry_key != expected_id
                            or str_data.get("str_id") != previous_str.str_id
                        ):
                            raise HTTPException(
                                status_code=400,
                                detail="STR tracking does not match the base entry"
                            )

                        gene_id = previous_str.gene_id
                        entity_name = previous_str.entity_name
                        entry_id = previous_link.lab_entry_id or uuid4()
                        source_reference = previous_link.source_reference

                    else:
                        addition = source_context.get(
                            "validated_str_additions", {}
                        ).get(entry_key)

                        if (
                            addition is None
                            or addition["entity_name"] != str_data.get("entity_name")
                            or addition.get("gene_symbol")
                            != str_data.get("gene_symbol")
                        ):
                            raise HTTPException(
                                status_code=400,
                                detail="Unverified source STR addition"
                            )

                        entity_name = addition["entity_name"]
                        symbol = addition.get("gene_symbol")
                        gene_id = None

                        if symbol:
                            gene = (
                                db.query(Gene)
                                .filter(Gene.gene_symbol == symbol)
                                .first()
                            )

                            if gene is None:
                                gene = Gene(gene_symbol=symbol)
                                db.add(gene)
                                db.flush()

                            gene_id = gene.gene_id

                        entry_id = PythonUUID(entry_key)
                        source_reference = addition["source_reference"]

                    sequence = str_data.get("repeated_sequence")

                    if (
                        previous_str is not None
                        and sequence == previous_str.repeated_sequence
                    ):
                        str_record = previous_str
                    else:
                        str_record = STR(
                            entity_name=entity_name,
                            gene_id=gene_id,
                            repeated_sequence=sequence,
                            confidence_level=str_data.get("confidence_level"),
                            phenotypes=str_data.get("phenotypes")
                        )

                        db.add(str_record)
                        db.flush()

                    db.add(
                        PanelVersionStr(
                            panel_version_id=new_version.panel_version_id,
                            str_id=str_record.str_id,
                            confidence_level=str_data.get("confidence_level"),
                            phenotypes=str_data.get("phenotypes"),
                            lab_entry_id=entry_id,
                            source_reference=source_reference
                        )
                    )
                    continue

            # Gene-only source requests preserve existing STRs unchanged.
            if source_context:
                str_id = str_data.get("str_id")
                matching_rows = base_strs_by_id.get(str_id, [])
                used_count = preserved_str_counts.get(str_id, 0)

                if used_count >= len(matching_rows):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "STR does not belong to the base version "
                            "or was submitted too many times"
                        )
                    )

                previous_link, previous_str = matching_rows[used_count]
                preserved_str_counts[str_id] = used_count + 1

                db.add(
                    PanelVersionStr(
                        panel_version_id=new_version.panel_version_id,
                        str_id=previous_str.str_id,
                        confidence_level=previous_link.confidence_level,
                        phenotypes=previous_link.phenotypes,
                        lab_entry_id=(
                            previous_link.lab_entry_id or uuid4()
                        ),
                        source_reference=previous_link.source_reference
                    )
                )
                continue

            # Ordinary laboratory editing.
            entity_name = str_data["entity_name"].strip()
            gene_symbol = str_data["gene_symbol"].strip()

            submitted_id = str_data.get("lab_entry_id")

            entry_id = uuid4()
            source_reference = None

            previous_link = None
            previous_str = None

            if submitted_id is not None:
                entry_key = str(submitted_id)

                if entry_key in seen_str_entry_ids:
                    raise HTTPException(
                        status_code=400,
                        detail="The same laboratory STR entry was submitted twice"
                    )

                seen_str_entry_ids.add(entry_key)
                previous = base_strs_by_entry_id.get(entry_key)

                if previous is None:
                    raise HTTPException(
                        status_code=400,
                        detail="STR tracking ID does not belong to the base version"
                    )

                previous_link, previous_str = previous

            gene = (
                db.query(Gene)
                .filter(Gene.gene_symbol == gene_symbol)
                .first()
            )

            if gene is None:
                gene = Gene(gene_symbol=gene_symbol)
                db.add(gene)
                db.flush()

            # Retain lineage when editing the same entity and gene.
            if (
                previous_str is not None
                and entity_name == previous_str.entity_name
                and gene.gene_id == previous_str.gene_id
            ):
                entry_id = previous_link.lab_entry_id
                source_reference = previous_link.source_reference

            # Reuse this entry's STR record only if its structural
            # values are unchanged. Never mutate an older version's STR.
            if (
                previous_str is not None
                and entity_name == previous_str.entity_name
                and gene.gene_id == previous_str.gene_id
                and str_data.get("repeated_sequence")
                == previous_str.repeated_sequence
            ):
                str_record = previous_str

            else:
                str_record = STR(
                    entity_name=entity_name,
                    gene_id=gene.gene_id,
                    confidence_level=str_data.get("confidence_level"),
                    phenotypes=str_data.get("phenotypes", []),
                    repeated_sequence=str_data.get("repeated_sequence")
                )

                db.add(str_record)
                db.flush()

            db.add(
                PanelVersionStr(
                    panel_version_id=new_version.panel_version_id,
                    str_id=str_record.str_id,
                    confidence_level=str_data.get("confidence_level"),
                    phenotypes=str_data.get("phenotypes", []),
                    lab_entry_id=entry_id,
                    source_reference=source_reference
                )
            )



        # # 8. Add the STRs to the new version
        # for str_data in proposed_data.get("strs", []):
        #     if source_context:
        #         if str_data["str_id"] not in base_str_ids:
        #             raise HTTPException(
        #                 status_code=400,
        #                 detail="STR does not belong to the base laboratory version"
        #             )

        #         db.add(
        #             PanelVersionStr(
        #                 panel_version_id=new_version.panel_version_id,
        #                 str_id=str_data["str_id"],
        #                 confidence_level=str_data.get("confidence_level"),
        #                 phenotypes=str_data.get("phenotypes")
        #             )
        #         )
        #         continue

        #     gene = (
        #         db.query(Gene)
        #         .filter(
        #             Gene.gene_symbol == str_data["gene_symbol"]
        #         )
        #         .first()
        #     )

        #     if gene is None:
        #         gene = Gene(
        #             gene_symbol=str_data["gene_symbol"]
        #         )

        #         db.add(gene)
        #         db.flush()

        #     str_record = (
        #         db.query(STR)
        #         .filter(
        #             STR.entity_name == str_data["entity_name"],
        #             STR.gene_id == gene.gene_id
        #         )
        #         .first()
        #     )

        #     if str_record is None:
        #         str_record = STR(
        #             entity_name=str_data["entity_name"],
        #             gene_id=gene.gene_id,
        #             confidence_level=str_data.get("confidence_level"),
        #             phenotypes=str_data.get("phenotypes", []),
        #             repeated_sequence=str_data.get("repeated_sequence")
        #         )

        #         db.add(str_record)
        #         db.flush()

        #     version_str = PanelVersionStr(
        #         panel_version_id=new_version.panel_version_id,
        #         str_id=str_record.str_id,
        #         confidence_level=str_data.get("confidence_level"),
        #         phenotypes=str_data.get("phenotypes", [])
        #     )

        #     db.add(version_str)

        # 9. Mark the change as approved
        change.status = "approved"
        change.reviewed_at = datetime.now()

        # 10. Save everything
        db.commit()

        # 11. Refresh the new version
        db.refresh(new_version)

        return {
            "message": "Panel change approved",
            "change_id": change.change_id,
            "panel_id": change.panel_id,
            "new_version_id": new_version.panel_version_id,
            "version_number": new_version.version_number,
            "status": change.status
        }
   except Exception:
    db.rollback()
    raise











@app.post("/changes/{change_id}/reject")
def reject_panel_change(
    change_id: int,
    db: Session = Depends(get_db)
):
    change = (
        db.query(PanelChange)
        .filter(PanelChange.change_id == change_id)
        .first()
    )

    if change is None:
        raise HTTPException(
            status_code=404,
            detail="Change request not found"
        )

    panel = (
        db.query(Panel)
        .filter(Panel.panel_id == change.panel_id)
        .first()
    )

    if (
        change.change_version_id is None
        or panel is None
        or panel.source_id != 7
    ):
        raise HTTPException(
            status_code=400,
            detail="This endpoint only rejects laboratory changes"
        )

    if change.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="This change has already been reviewed"
        )

    change.status = "rejected"
    change.reviewed_at = datetime.now()

    db.commit()

    return {
        "message": "Panel change rejected",
        "change_id": change.change_id,
        "panel_id": change.panel_id,
        "status": change.status
    }






@app.get("/panels/{panel_id}/versions")
def get_panel_versions(
    panel_id: int,
    db: Session = Depends(get_db)
):
    # 1. Check that the panel exists
    panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id
        )
        .first()
    )

    if panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    # 2. Get all versions of the panel
    versions = (
        db.query(PanelVersion)
        .filter(
            PanelVersion.panel_id == panel_id
        )
        .order_by(
            PanelVersion.version_number.asc()
        )
        .all()
    )

    if not versions:
        raise HTTPException(
            status_code=404,
            detail="No versions found for this panel"
        )

    # 3. Return the version history
    return [
        {
            "panel_version_id": version.panel_version_id,
            "version_number": version.version_number,
            "panel_name": version.panel_name,
            "disease_group": version.disease_group,
            "disease_subgroup": version.disease_subgroup,
            "relevant_diseases": version.relevant_diseases,
            "last_updated": version.last_updated
        }
        for version in versions
    ]













@app.get("/panels/{panel_id}/versions/{version_number}")
def get_panel_version(
    panel_id: int,
    version_number: int,
    db: Session = Depends(get_db)
):
    # 1. Find the requested version
    version = (
        db.query(PanelVersion)
        .filter(
            PanelVersion.panel_id == panel_id,
            PanelVersion.version_number == version_number
        )
        .first()
    )

    if version is None:
        raise HTTPException(
            status_code=404,
            detail="Panel version not found"
        )

    # 2. Get the genes for this version
    version_genes = (
        db.query(PanelVersionGene, Gene)
        .join(
            Gene,
            PanelVersionGene.gene_id == Gene.gene_id
        )
        .filter(
            PanelVersionGene.panel_version_id == version.panel_version_id
        )
        .all()
    )

    # 3. Get the STRs for this version
    version_strs = (
        db.query(PanelVersionStr, STR)
        .join(
            STR,
            PanelVersionStr.str_id == STR.str_id
        )
        .filter(
            PanelVersionStr.panel_version_id == version.panel_version_id
        )
        .all()
    )

    # 4. Format the genes
    genes = [
        {
            "gene_symbol": gene.gene_symbol,
            "confidence_level": version_gene.confidence_level,
            "phenotypes": version_gene.phenotypes
        }
        for version_gene, gene in version_genes
    ]

    # 5. Format the STRs
    strs = [
        {
            "entity_name": str_record.entity_name,
            "gene_symbol": (
                db.query(Gene.gene_symbol)
                .filter(
                    Gene.gene_id == str_record.gene_id
                )
                .scalar()
            ),
            "confidence_level": version_str.confidence_level,
            "phenotypes": version_str.phenotypes,
            "repeated_sequence": str_record.repeated_sequence
        }
        for version_str, str_record in version_strs
    ]

    # 6. Return the complete historical version
    return {
        "panel_id": panel_id,
        "panel_version_id": version.panel_version_id,
        "version": version.version_number,
        "panel_name": version.panel_name,
        "disease_group": version.disease_group,
        "disease_subgroup": version.disease_subgroup,
        "relevant_diseases": version.relevant_diseases,
        "last_updated": version.last_updated,
        "genes": genes,
        "strs": strs
    }









@app.get("/genes")

def get_all_genes(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    genes = (
        db.query(Gene)
        .limit(limit)
        .offset(offset)
        .all()

    )

    return genes








@app.post("/lab-panels")
def create_panel(
    panel: LabPanelCreate,
    db: Session = Depends(get_db)
):
    try:
        # 1. Create the laboratory panel.
        new_panel = Panel(
            panel_name=panel.panel_name,
            disease_group=panel.disease_group,
            disease_subgroup=panel.disease_subgroup,
            relevant_diseases=panel.relevant_diseases,
            source_id=7,
            is_active=True
        )

        db.add(new_panel)
        db.flush()

        # 2. Create version 1.
        version_1 = PanelVersion(
            panel_id=new_panel.panel_id,
            version_number=1,
            panel_name=panel.panel_name,
            disease_group=panel.disease_group,
            disease_subgroup=panel.disease_subgroup,
            relevant_diseases=panel.relevant_diseases,
            last_updated=date.today()
        )

        db.add(version_1)
        db.flush()

        # 3. Add genes to version 1.
        for gene_data in panel.genes:
            gene = db.query(Gene).filter(
                Gene.gene_symbol == gene_data.gene_symbol
            ).first()

            if gene is None:
                gene = Gene(gene_symbol=gene_data.gene_symbol)
                db.add(gene)
                db.flush()

            db.add(
                PanelVersionGene(
                    panel_version_id=version_1.panel_version_id,
                    gene_id=gene.gene_id,
                    confidence_level=gene_data.confidence_level,
                    phenotypes=gene_data.phenotypes
                )
            )

        # 4. Add STRs to version 1.
        for str_data in panel.strs:
            gene = db.query(Gene).filter(
                Gene.gene_symbol == str_data.gene_symbol
            ).first()

            if gene is None:
                gene = Gene(gene_symbol=str_data.gene_symbol)
                db.add(gene)
                db.flush()

            str_record = db.query(STR).filter(
                STR.entity_name == str_data.entity_name,
                STR.gene_id == gene.gene_id,
                STR.repeated_sequence == str_data.repeated_sequence
            ).first()

            if str_record is None:
                str_record = STR(
                    entity_name=str_data.entity_name,
                    gene_id=gene.gene_id,
                    confidence_level=str_data.confidence_level,
                    phenotypes=str_data.phenotypes,
                    repeated_sequence=str_data.repeated_sequence
                )

                db.add(str_record)
                db.flush()

            db.add(
                PanelVersionStr(
                    panel_version_id=version_1.panel_version_id,
                    str_id=str_record.str_id,
                    confidence_level=str_data.confidence_level,
                    phenotypes=str_data.phenotypes
                )
            )

        # 5. Save everything together.
        db.commit()
        db.refresh(new_panel)

        return new_panel

    except Exception:
        db.rollback()
        raise

















@app.delete("/panels/{panel_id}")
def delete_panel(
    panel_id: int,
    db: Session = Depends(get_db)
):
    panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id
        )
        .first()
    )

    if panel is None:
        raise HTTPException(
            status_code=404,
            detail="Panel not found"
        )

    # Only laboratory panels can be deleted
    if panel.source_id != 7:
        raise HTTPException(
            status_code=400,
            detail="Only laboratory panels can be deleted"
        )

    # Soft delete
    panel.is_active = False

    db.commit()

    return {
        "message": "Laboratory panel deleted successfully",
        "panel_id": panel.panel_id
    }








#get changes for the external sources(chnages are the consequence of running the update on the 6 sources,this will show the output of the create pending change dunction in the comparison layer)
@app.get("/external-changes")
def get_external_changes(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.change_version_id.is_(None),
            PanelChange.status == "pending"
        )
        .order_by(PanelChange.change_id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []

    for change in changes:
        proposed_data = change.proposed_data or {}
        data = proposed_data.get("data") or {}


        source_name = data.get("source")

        if not source_name and change.panel_id is not None:
          source_name = (
             db.query(Source.source_name)
            .join(Panel, Panel.source_id == Source.source_id)
            .filter(Panel.panel_id == change.panel_id)
            .scalar()
          )

        results.append({
            "change_id": change.change_id,
            "panel_id": change.panel_id,
            "action": proposed_data.get("action"),
            "status": change.status,
            "created_at": change.created_at,
            "panel_name": data.get("panel_name"),
            "source": source_name,
            "target": proposed_data.get("target"),
            "orpha_code": proposed_data.get("orpha_code"),
            "disease_name": data.get("disease_name"),
        })

    return results



#changes that are made when running update not us changing the external sources
@app.get("/external-changes/{change_id}")
def get_external_change(
    change_id: int,
    db: Session = Depends(get_db)
):
    change = (
        db.query(PanelChange)
        .filter(
            PanelChange.change_id == change_id,
            PanelChange.change_version_id.is_(None)
        )
        .first()
    )

    if not change:
        raise HTTPException(
            status_code=404,
            detail="External change not found"
        )


    proposed_data = change.proposed_data or {}
    data = proposed_data.get("data") or {}
    
    return {
        "change_id": change.change_id,
        "panel_id": change.panel_id,
        "status": change.status,
        "created_at": change.created_at,
        "reviewed_at": change.reviewed_at,
        "action": proposed_data.get("action"),
        "data": proposed_data.get("data"),
        "current_data": proposed_data.get("current_data"),
        "changes": proposed_data.get("changes"),
        "proposed_data": change.proposed_data,
        "target": proposed_data.get("target"),
        "orpha_code": proposed_data.get("orpha_code"),
        "disease_name": data.get("disease_name"),
    }



#approving the chnages of the newest update in the external sourcesssssssss
@app.post("/external-changes/{change_id}/approve")
def approve_external_change_endpoint(
    change_id: int,
    db: Session = Depends(get_db)
):
    try:
        result = approve_external_change(
            db=db,
            change_id=change_id
        )

        return {
            "message": "External change approved successfully",
            "change_id": change_id,
            "result": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )




@app.post("/external-changes/{change_id}/reject")
def reject_external_change_endpoint(
    change_id: int,
    db: Session = Depends(get_db)
):
    try:
        result = reject_external_change(
            db=db,
            change_id=change_id
        )

        return {
            "message": "External change rejected successfully",
            "change_id": change_id,
            "result": result
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )





@app.post("/external-changes/source/{source_name}/{decision}")
def review_all_external_changes_for_source(
    source_name: str,
    decision: str,
    db: Session = Depends(get_db),
):
    """Approve or reject all pending external changes for one source."""
    if source_name not in EXTERNAL_UPDATE_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported external source: {source_name}",
        )

    if decision not in ["approve", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approve' or 'reject'.",
        )

    pending_changes = (
        db.query(PanelChange)
        .filter(
            PanelChange.change_version_id.is_(None),
            PanelChange.status == "pending",
        )
        .order_by(PanelChange.change_id.asc())
        .all()
    )
    
    source_change_ids = []
    
    for change in pending_changes:
        proposed_data = change.proposed_data or {}
        data = proposed_data.get("data") or {}
        pending_source = data.get("source")

        # Existing external proposals usually save the source in proposed_data.
        # Fall back to the panel's source for older proposals without that field.
        if not pending_source and change.panel_id is not None:
            pending_source = (
                db.query(Source.source_name)
                .join(Panel, Panel.source_id == Source.source_id)
                .filter(Panel.panel_id == change.panel_id)
                .scalar()
            )

        if pending_source == source_name:
            source_change_ids.append(change.change_id)

    review_function = (
        approve_external_change
        if decision == "approve"
        else reject_external_change
    )
    final_status = "approved" if decision == "approve" else "rejected"
    results = []

    for change_id in source_change_ids:
        try:
            review_function(db=db, change_id=change_id)
            results.append({
                "change_id": change_id,
                "status": final_status,
                "error": None,
            })
        except Exception as error:
            db.rollback()
            results.append({
                "change_id": change_id,
                "status": "failed",
                "error": str(error),
            })

    success_count = sum(
        result["status"] == final_status
        for result in results
    )

    return {
        "source": source_name,
        "decision": decision,
        "total": len(results),
        "success_count": success_count,
        "failed_count": len(results) - success_count,
        "results": results,
    }















# adding the endpoint to run all the updates of the sources at the same time 

def _run_external_updates_in_background(run_id):
    """Run each external source sequentially and save progress for polling."""
    global active_external_update_run_id


    runners = {}
    try:
        from update.test_on_source import (
            run_panelapp_aus_update,
            run_panelapp_uk_update,
            run_blueprint_update,
            run_ontario_update,
            run_clingen_update,
            run_gencc_update,
            run_orphanet_update,
        )

       
        def run_orphanet():
            with SessionLocal() as db:
                return run_orphanet_update(db)
            
        runners = {
            "PanelApp AUS": run_panelapp_aus_update,
            "PanelApp UK": run_panelapp_uk_update,
            "Blueprint Genetics": run_blueprint_update,
            "Ontario Health": run_ontario_update,
            "ClinGen": run_clingen_update,
            "GenCC": run_gencc_update,
            "Orphanet":run_orphanet,
        }


    except Exception as error:
        
        with external_update_runs_lock:
            run = external_update_runs[run_id]
            for source_result in run["sources"]:
                source_result["status"] = "failed"
                source_result["error"] = f"Could not load update runners: {error}"
            run["status"] = "failed"
            run["current_source"] = None
            run["completed_sources"] = len(run["sources"])
            active_external_update_run_id = None
        return

    # for source_name in EXTERNAL_UPDATE_SOURCES:
    with external_update_runs_lock:
        selected_sources = [
            item["source"]
            for item in external_update_runs[run_id]["sources"]
        ]

    for source_name in selected_sources:
        with external_update_runs_lock:
            run = external_update_runs[run_id]

            if run["cancel_requested"]:
                for pending_source in run["sources"]:
                    if pending_source["status"] == "waiting":
                        pending_source["status"] = "cancelled"
                        run["completed_sources"] += 1
                run["status"] = "cancelled"
                run["current_source"] = None
                active_external_update_run_id = None
                return

            run["status"] = "running"
            run["current_source"] = source_name
            source_result = next(
                item for item in run["sources"]
                if item["source"] == source_name
            )
            source_result["status"] = "running"

        try:
            comparison_results = runners[source_name]() or []
            counts = Counter(
                result.get("status", "unknown")
                for result in comparison_results
                if isinstance(result, dict)
            )
            result_update = {
                "status": "completed",
                "compared": sum(counts.values()),
                "new": counts.get("new", 0),
                "changed": counts.get("changed", 0),
                "unchanged": counts.get("unchanged", 0),
                "removed": counts.get("removed", 0),
                "error": None,
            }
        except Exception as error:
            result_update = {
                "status": "failed",
                "compared": 0,
                "new": 0,
                "changed": 0,
                "unchanged": 0,
                "removed": 0,
                "error": str(error),
            }


        with external_update_runs_lock:
            source_result.update(result_update)
            run["completed_sources"] += 1
            run["current_source"] = None

    with external_update_runs_lock:
        run = external_update_runs[run_id]
        failed_count = sum(
            item["status"] == "failed"
            for item in run["sources"]
        )
        run["status"] = (
            "cancelled" if run["cancel_requested"]
            else "failed" if failed_count == len(run["sources"])
            else "partial" if failed_count
            else "completed"
        )
        run["current_source"] = None
        active_external_update_run_id = None







@app.post("/external-updates/run-all", status_code=202)
def run_all_external_updates(background_tasks: BackgroundTasks):
    """Start the six source updates and return a run ID for progress checks."""
    global active_external_update_run_id

    with external_update_runs_lock:
        if active_external_update_run_id is not None:
            active_run = external_update_runs.get(
                active_external_update_run_id
            )
            if active_run and active_run["status"] in ["queued", "running","cancelling"]:
                raise HTTPException(
                    status_code=409,
                    detail={ 
                    "message":"An external update run is already in progress.",
                    "run_id": active_external_update_run_id,
                     },
                )

        run_id = str(uuid4())
        external_update_runs[run_id] = {
            "run_id": run_id,
            "status": "queued",
            "cancel_requested": False,
            "current_source": None,
            "completed_sources": 0,
            "total_sources": len(EXTERNAL_UPDATE_SOURCES),
            "sources": [
                {
                    "source": source_name,
                    "status": "waiting",
                    "compared": 0,
                    "new": 0,
                    "changed": 0,
                    "unchanged": 0,
                    "removed": 0,
                    "error": None,
                }
                for source_name in EXTERNAL_UPDATE_SOURCES
            ],
        }
        active_external_update_run_id = run_id

    background_tasks.add_task(
        _run_external_updates_in_background,
        run_id,
    )

    return external_update_runs[run_id]











@app.post("/external-updates/runs/{run_id}/cancel")
def cancel_external_update_run(run_id: str):
    with external_update_runs_lock:
        run = external_update_runs.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail="External update run not found.",
            )

        if run["status"] not in ["queued", "running"]:
            raise HTTPException(
                status_code=409,
                detail=f"This update run is already {run['status']}.",
            )

        waiting_sources = [
            source_result
            for source_result in run["sources"]
            if source_result["status"] == "waiting"
        ]
        if not waiting_sources:
            raise HTTPException(
                status_code=409,
                detail="The final source is already running and will finish before the run stops.",
            )

        run["cancel_requested"] = True
        run["status"] = "cancelling"
        return dict(run)





@app.get("/external-updates/active-run")
def get_active_external_update_run():
    with external_update_runs_lock:
        if active_external_update_run_id is None:
            return None

        run = external_update_runs.get(active_external_update_run_id)
        if run is None or run["status"] not in [
            "queued", "running", "cancelling"
        ]:
            return None

        return dict(run)


@app.post("/external-updates/run/{source_name}", status_code=202)
def run_external_source_update(
    source_name: str,
    background_tasks: BackgroundTasks
):
    global active_external_update_run_id

    # Accept source names regardless of capitalization.
    matched_source = next(
        (
            source
            for source in EXTERNAL_UPDATE_SOURCES
            if source.casefold() == source_name.strip().casefold()
        ),
        None
    )

    if matched_source is None:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Unsupported external source.",
                "supported_sources": list(EXTERNAL_UPDATE_SOURCES)
            }
        )

    with external_update_runs_lock:
        if active_external_update_run_id is not None:
            active_run = external_update_runs.get(
                active_external_update_run_id
            )

            if active_run and active_run["status"] in [
                "queued", "running", "cancelling"
            ]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "An external update run is already in progress.",
                        "run_id": active_external_update_run_id
                    }
                )

        run_id = str(uuid4())

        run = {
            "run_id": run_id,
            "status": "queued",
            "cancel_requested": False,
            "current_source": None,
            "completed_sources": 0,
            "total_sources": 1,
            "sources": [
                {
                    "source": matched_source,
                    "status": "waiting",
                    "compared": 0,
                    "new": 0,
                    "changed": 0,
                    "unchanged": 0,
                    "removed": 0,
                    "error": None
                }
            ]
        }

        external_update_runs[run_id] = run
        active_external_update_run_id = run_id

        # Independent response snapshot.
        response = {
            **run,
            "sources": [dict(item) for item in run["sources"]]
        }

    background_tasks.add_task(
        _run_external_updates_in_background,
        run_id
    )

    return response



@app.get("/external-updates/runs/{run_id}")
def get_external_update_run(run_id: str):
    with external_update_runs_lock:
        run = external_update_runs.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail="External update run not found.",
            )
        return dict(run)







def compare_snapshot_entries(old_entries, new_entries, source, kind):
    def identity(entry):
        if kind == "genes":
            if source == "ClinGen":
                return entry.get("assertion_url") or entry.get("gene_symbol")

            name = entry.get("gene_symbol")
        else:
            name = entry.get("entity_name")

        if source in ("PanelApp UK", "PanelApp AUS"):
            return (name, entry.get("origin_panel_id"))

        return name

    fields = (
        [
            "gene_symbol",
            "confidence_level",
            "phenotypes",
            "moi",
            "submitter",
            "assertion_url",
            "sgc_id",
            "origin_panel_id"
        ]
        if kind == "genes"
        else [
            "entity_name",
            "gene_symbol",
            "confidence_level",
            "phenotypes",
            "repeated_sequence",
            "origin_panel_id"
        ]
    )

    def signature(entry):
        values = {field: entry.get(field) for field in fields}

        # Ignore phenotype order and repeated phenotype labels.
        values["phenotypes"] = sorted(
            set(entry.get("phenotypes") or [])
        )

        return json.dumps(values, sort_keys=True)

    old_groups = defaultdict(list)
    new_groups = defaultdict(list)

    for entry in old_entries:
        old_groups[identity(entry)].append(entry)

    for entry in new_entries:
        new_groups[identity(entry)].append(entry)

    changes = {"added": [], "removed": [], "modified": []}

    for key in sorted(old_groups.keys() | new_groups.keys(), key=repr):
        old_items = old_groups.get(key, [])
        new_items = new_groups.get(key, [])

        if not old_items:
            changes["added"].extend(new_items)
        elif not new_items:
            changes["removed"].extend(old_items)
        elif (
            Counter(signature(item) for item in old_items)
            != Counter(signature(item) for item in new_items)
        ):
            changes["modified"].append({
                "identity": key,
                "old": old_items,
                "new": new_items
            })

    return changes





def source_gene_identity(entry, source):
    if source == "ClinGen":
        return entry.get("assertion_url") or entry.get("gene_symbol")

    if source in ("PanelApp UK", "PanelApp AUS"):
        return (
            entry.get("gene_symbol"),
            entry.get("origin_panel_id")
        )

    return entry.get("gene_symbol")


def normalized_gene_value(field, value):
    if field == "phenotypes":
        return sorted(set(value or []))

    return value




def source_str_identity(entry, source):
    name = entry.get("entity_name")

    if source in ("PanelApp UK", "PanelApp AUS"):
        return (name, entry.get("origin_panel_id"))

    return name


def normalized_str_value(field, value):
    if field == "phenotypes":
        return sorted(set(value or []))

    return value


def build_lab_gene_proposals(
    db,
    latest_version,
    baselines,
    current_snapshots,
    source_results
):
    rows = (
        db.query(PanelVersionGene, Gene)
        .join(Gene, Gene.gene_id == PanelVersionGene.gene_id)
        .filter(
            PanelVersionGene.panel_version_id
            == latest_version.panel_version_id
        )
        .all()
    )

    proposals = []
    warnings = []
    additions = []

    # Group source entries without collapsing repeated records.
    def group_genes(snapshot):
        groups = defaultdict(list)

        if snapshot:
            source = snapshot.get("source")

            for entry in snapshot.get("genes") or []:
                groups[source_gene_identity(entry, source)].append(entry)

        return groups

    old_groups = {
        panel_id: group_genes(snapshot)
        for panel_id, snapshot in baselines.items()
    }

    new_groups = {
        panel_id: group_genes(snapshot)
        for panel_id, snapshot in current_snapshots.items()
    }

    lab_symbols = {gene.gene_symbol for _, gene in rows}




    lab_name_counts = Counter(gene.gene_symbol for _, gene in rows)
    
    removed_by_name = defaultdict(list)
    for result in source_results:
        for entry in result["gene_changes"]["removed"]:
            symbol = entry.get("gene_symbol")
            if symbol:
                removed_by_name[symbol].append((result, entry))

    active_source_names = {
        entry.get("gene_symbol")
        for snapshot in current_snapshots.values()
        if snapshot.get("is_active", True)
        for entry in (snapshot.get("genes") or [])
    }


    for link, gene in rows:
        reference = link.source_reference

        # Manually added and older untracked entries have no source mapping.
        # if not reference:
        #     if link.lab_entry_id is None:
        #         warnings.append({
        #             "gene_symbol": gene.gene_symbol,
        #             "reason": "Entry has no tracking information"
        #         })
        #     continue
      
      
        if not reference:
            symbol = gene.gene_symbol
            matches = removed_by_name.get(symbol, [])

            if (
                lab_name_counts[symbol] == 1
                and len(matches) == 1
                and symbol not in active_source_names
            ):
                result, removed_entry = matches[0]

                proposals.append({
                    "action": "remove",
                    "match_by_name": True,
                    "base_version_gene_id": link.panel_version_gene_id,
                    "lab_entry_id": (
                        str(link.lab_entry_id) if link.lab_entry_id else None
                    ),
                    "gene_symbol": symbol,
                    "original_panel_id": result["original_panel_id"],
                    "source_reference": None,
                    "baseline": removed_entry,
                    "current_source": None,
                    "current_lab": {
                        "gene_symbol": symbol,
                        "confidence_level": link.confidence_level,
                        "phenotypes": link.phenotypes,
                        "moi": link.moi,
                    },
                })
            elif link.lab_entry_id is None or matches:
                warnings.append({
                    "gene_symbol": symbol,
                    "reason": (
                        "Source removal could not be matched uniquely"
                        if matches else "Entry has no tracking information"
                    ),
                })

            continue









        if link.lab_entry_id is None:
            warnings.append({
                "gene_symbol": gene.gene_symbol,
                "reason": "Source reference exists but lab_entry_id is missing"
            })
            continue

        panel_key = str(reference.get("original_panel_id"))
        old_snapshot = baselines.get(panel_key)
        new_snapshot = current_snapshots.get(panel_key)

        base = {
            "lab_entry_id": str(link.lab_entry_id),
            "gene_symbol": gene.gene_symbol,
            "original_panel_id": reference.get("original_panel_id"),
            "source_reference": reference
        }

        if old_snapshot is None:
            warnings.append({
                **base,
                "reason": "No baseline exists for this tracked entry"
            })
            continue

        source = reference.get("source")

        if (
            source != old_snapshot.get("source")
            or (
                new_snapshot is not None
                and source != new_snapshot.get("source")
            )
        ):
            warnings.append({
                **base,
                "reason": "Source identity mismatch"
            })
            continue

        identity = source_gene_identity(reference, source)
        old_items = old_groups.get(panel_key, {}).get(identity, [])

        new_active = bool(
            new_snapshot and new_snapshot.get("is_active", True)
        )

        new_items = (
            new_groups.get(panel_key, {}).get(identity, [])
            if new_active
            else []
        )

        # Never guess which repeated source record belongs to this lab entry.
        if len(old_items) != 1 or len(new_items) > 1:
            warnings.append({
                **base,
                "reason": "Source entry matching requires manual review",
                "baseline_matches": old_items,
                "current_matches": new_items
            })
            continue

        old_entry = old_items[0]

        lab_entry = {
            "gene_symbol": gene.gene_symbol,
            "confidence_level": link.confidence_level,
            "phenotypes": link.phenotypes,
            "moi": link.moi
        }

        if not new_items:
            # Report a removal only if it was active in the baseline.
            if old_snapshot.get("is_active", True):
                proposals.append({
                    **base,
                    "action": "remove",
                    "baseline": old_entry,
                    "current_source": None,
                    "current_lab": lab_entry
                })
            continue

        new_entry = new_items[0]
        field_changes = {}

        for field in ("confidence_level", "phenotypes", "moi"):
            old_value = normalized_gene_value(
                field, old_entry.get(field)
            )
            new_value = normalized_gene_value(
                field, new_entry.get(field)
            )
            lab_value = normalized_gene_value(
                field, lab_entry.get(field)
            )

            if old_value == new_value:
                continue

            if lab_value == new_value:
                status = "already_current"
            elif lab_value == old_value:
                status = "update_available"
            else:
                status = "conflict"

            field_changes[field] = {
                "old_source": old_entry.get(field),
                "new_source": new_entry.get(field),
                "current_lab": lab_entry.get(field),
                "status": status
            }

        if field_changes:
            proposals.append({
                **base,
                "action": "update",
                "fields": field_changes
            })

    # Genuinely new source identities, including new ClinGen group members.
    for panel_key, snapshot in current_snapshots.items():
        if not snapshot.get("is_active", True):
            continue

        previous = old_groups.get(panel_key, {})

        for identity, entries in new_groups.get(panel_key, {}).items():
            if identity in previous:
                continue

            additions.append({
                "original_panel_id": int(panel_key),
                "source": snapshot.get("source"),
                "entries": entries,
                "requires_manual_matching": len(entries) > 1,
                "matching_lab_symbols": sorted({
                    entry.get("gene_symbol")
                    for entry in entries
                    if entry.get("gene_symbol") in lab_symbols
                })
            })

    return {
        "proposals": proposals,
        "new_source_entries": additions,
        "warnings": warnings
    }





def build_lab_str_proposals(
    db,
    latest_version,
    baselines,
    current_snapshots
):
    rows = (
        db.query(PanelVersionStr, STR, Gene)
        .join(STR, STR.str_id == PanelVersionStr.str_id)
        .outerjoin(Gene, Gene.gene_id == STR.gene_id)
        .filter(
            PanelVersionStr.panel_version_id
            == latest_version.panel_version_id
        )
        .all()
    )

    proposals = []
    warnings = []
    additions = []

    def group_strs(snapshot):
        groups = defaultdict(list)

        if snapshot:
            source = snapshot.get("source")

            for entry in snapshot.get("strs") or []:
                groups[
                    source_str_identity(entry, source)
                ].append(entry)

        return groups

    old_groups = {
        panel_id: group_strs(snapshot)
        for panel_id, snapshot in baselines.items()
    }

    new_groups = {
        panel_id: group_strs(snapshot)
        for panel_id, snapshot in current_snapshots.items()
    }

    lab_names = {
        str_record.entity_name
        for _, str_record, _ in rows
    }

    # Used to avoid offering an already tracked source entry again.
    tracked_source_keys = set()

    for link, str_record, gene in rows:
        reference = link.source_reference

        if not reference:
            if link.lab_entry_id is None:
                warnings.append({
                    "entity_name": str_record.entity_name,
                    "reason": "Entry has no tracking information"
                })
            continue

        if link.lab_entry_id is None:
            warnings.append({
                "entity_name": str_record.entity_name,
                "reason": (
                    "Source reference exists but lab_entry_id is missing"
                )
            })
            continue

        panel_key = str(reference.get("original_panel_id"))
        source = reference.get("source")
        identity = source_str_identity(reference, source)

        tracked_source_keys.add((panel_key, source, identity))

        base = {
            "lab_entry_id": str(link.lab_entry_id),
            "entity_name": str_record.entity_name,
            "original_panel_id": reference.get("original_panel_id"),
            "source_reference": reference
        }

        old_snapshot = baselines.get(panel_key)
        new_snapshot = current_snapshots.get(panel_key)

        if old_snapshot is None:
            warnings.append({
                **base,
                "reason": "No baseline exists for this tracked STR"
            })
            continue

        if (
            source != old_snapshot.get("source")
            or (
                new_snapshot is not None
                and source != new_snapshot.get("source")
            )
        ):
            warnings.append({
                **base,
                "reason": "Source identity mismatch"
            })
            continue

        old_items = old_groups.get(panel_key, {}).get(identity, [])

        new_active = bool(
            new_snapshot and new_snapshot.get("is_active", True)
        )

        new_items = (
            new_groups.get(panel_key, {}).get(identity, [])
            if new_active else []
        )

        if len(old_items) != 1 or len(new_items) > 1:
            warnings.append({
                **base,
                "reason": "Source STR matching requires manual review",
                "baseline_matches": old_items,
                "current_matches": new_items
            })
            continue

        old_entry = old_items[0]

        lab_entry = {
            "entity_name": str_record.entity_name,
            "gene_symbol": gene.gene_symbol if gene else None,
            "confidence_level": link.confidence_level,
            "phenotypes": link.phenotypes,
            "repeated_sequence": str_record.repeated_sequence
        }

        if not new_items:
            if old_snapshot.get("is_active", True):
                proposals.append({
                    **base,
                    "action": "remove",
                    "baseline": old_entry,
                    "current_source": None,
                    "current_lab": lab_entry
                })
            continue

        new_entry = new_items[0]
        field_changes = {}

        # Gene reassignment needs separate identity review.
        if old_entry.get("gene_symbol") != new_entry.get("gene_symbol"):
            warnings.append({
                **base,
                "reason": "Associated source gene changed; review manually",
                "baseline": old_entry,
                "current_source": new_entry,
                "current_lab": lab_entry
            })

        for field in (
            "confidence_level",
            "phenotypes",
            "repeated_sequence"
        ):
            old_value = normalized_str_value(
                field, old_entry.get(field)
            )
            new_value = normalized_str_value(
                field, new_entry.get(field)
            )
            lab_value = normalized_str_value(
                field, lab_entry.get(field)
            )

            if old_value == new_value:
                continue

            if lab_value == new_value:
                status = "already_current"
            elif lab_value == old_value:
                status = "update_available"
            else:
                status = "conflict"

            field_changes[field] = {
                "old_source": old_entry.get(field),
                "new_source": new_entry.get(field),
                "current_lab": lab_entry.get(field),
                "status": status
            }

        if field_changes:
            proposals.append({
                **base,
                "action": "update",
                "fields": field_changes
            })

    for panel_key, snapshot in current_snapshots.items():
        if not snapshot.get("is_active", True):
            continue

        source = snapshot.get("source")
        previous = old_groups.get(panel_key, {})

        for identity, entries in new_groups.get(panel_key, {}).items():
            if identity in previous:
                continue

            if (panel_key, source, identity) in tracked_source_keys:
                continue

            additions.append({
                "original_panel_id": int(panel_key),
                "source": source,
                "entries": entries,
                "requires_manual_matching": len(entries) > 1,
                "matching_lab_entities": sorted({
                    entry.get("entity_name")
                    for entry in entries
                    if entry.get("entity_name") in lab_names
                })
            })

    return {
        "proposals": proposals,
        "new_source_entries": additions,
        "warnings": warnings
    }














def source_report_token(report):
    def canonical(value):
        if isinstance(value, dict):
            return {
                key: canonical(item)
                for key, item in sorted(value.items())
            }

        if isinstance(value, list):
            items = [canonical(item) for item in value]

            return sorted(
                items,
                key=lambda item: json.dumps(item, sort_keys=True)
            )

        return value

    encoded = jsonable_encoder(report)

    return hashlib.sha256(
        json.dumps(
            canonical(encoded),
            sort_keys=True,
            separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()














@app.get("/lab-panels/{panel_id}/source-updates")
def check_lab_panel_source_updates(
    panel_id: int,
    db: Session = Depends(get_db)
):
    laboratory_panel = (
        db.query(Panel)
        .filter(
            Panel.panel_id == panel_id,
            Panel.source_id == 7,
            Panel.is_active.is_(True)
        )
        .first()
    )

    if laboratory_panel is None:
        raise HTTPException(
            status_code=404,
            detail="Laboratory panel not found"
        )

    baselines = laboratory_panel.source_baseline

    if not isinstance(baselines, dict) or not baselines:
        raise HTTPException(
            status_code=400,
            detail="This panel has no source tracking snapshots"
        )

    # Expect snapshots keyed by original internal panel ID.
    try:
        baseline_ids = {int(key) for key in baselines}
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Old snapshot format: migrate this copy before checking"
        )

    if any(not isinstance(value, dict) for value in baselines.values()):
        raise HTTPException(
            status_code=400,
            detail="Invalid source snapshot"
        )

    original_ids = set(laboratory_panel.copied_from_panel_ids or [])
    tracked_ids = original_ids | baseline_ids

    # Include inactive originals so their removal can be detected.
    originals = (
        db.query(Panel)
        .filter(Panel.panel_id.in_(tracked_ids))
        .all()
    )

    current_panels = {
        original.panel_id: original
        for original in originals
    }

    # Discover new active members of a copied ClinGen disease group.
    group = laboratory_panel.copied_from_group

    if group:
        if group.get("source") != "ClinGen" or not group.get("panel_name"):
            raise HTTPException(
                status_code=400,
                detail="Invalid copied group identity"
            )

        group_members = (
            db.query(Panel)
            .join(Source, Panel.source_id == Source.source_id)
            .filter(
                Source.source_name == "ClinGen",
                Panel.is_active.is_(True),
                func.lower(func.trim(Panel.panel_name))
                == group["panel_name"].strip().lower()
            )
            .all()
        )

        for member in group_members:
            current_panels[member.panel_id] = member

    current_snapshots = {
        str(original_id): get_current_panel_data(db, original)
        for original_id, original in current_panels.items()
    }

    results = []

    for original_id in sorted(tracked_ids | set(current_panels)):
        key = str(original_id)
        old = baselines.get(key)
        new = current_snapshots.get(key)

        old_active = bool(old and old.get("is_active", True))
        new_active = bool(new and new.get("is_active", True))

        metadata_changes = {}
        gene_changes = {"added": [], "removed": [], "modified": []}
        str_changes = {"added": [], "removed": [], "modified": []}

        if old is None:
            if new is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Missing snapshot and original for panel {original_id}"
                )

            status = "added" if new_active else "unchanged"

            if new_active:
                gene_changes["added"] = new.get("genes") or []
                str_changes["added"] = new.get("strs") or []

        elif old_active and not new_active:
            status = "removed"
            gene_changes["removed"] = old.get("genes") or []
            str_changes["removed"] = old.get("strs") or []

        elif not old_active and new_active:
            status = "reactivated"
            gene_changes["added"] = new.get("genes") or []
            str_changes["added"] = new.get("strs") or []

        elif not old_active and not new_active:
            status = "unchanged"

        else:
            if old.get("source") != new.get("source"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Source identity mismatch for panel {original_id}"
                )

            metadata_changes = compare_metadata(new, old)

            # Compare supplied child lists without considering order.
            if sorted(old.get("child_panel_ids") or []) != sorted(
                new.get("child_panel_ids") or []
            ):
                metadata_changes["child_panel_ids"] = {
                    "old": old.get("child_panel_ids"),
                    "new": new.get("child_panel_ids")
                }

            source = new.get("source")

            gene_changes = compare_snapshot_entries(
                old.get("genes") or [],
                new.get("genes") or [],
                source,
                "genes"
            )

            str_changes = compare_snapshot_entries(
                old.get("strs") or [],
                new.get("strs") or [],
                source,
                "strs"
            )

            has_changes = (
                bool(metadata_changes)
                or any(gene_changes.values())
                or any(str_changes.values())
            )

            status = "changed" if has_changes else "unchanged"

        results.append({
            "original_panel_id": original_id,
            "panel_name": (new or old).get("panel_name"),
            "source": (new or old).get("source"),
            "status": status,
            "metadata_changes": metadata_changes,
            "gene_changes": gene_changes,
            "str_changes": str_changes,
            "baseline": old,
            "current_source": new
        })

    latest_version = (
        db.query(PanelVersion)
        .filter(PanelVersion.panel_id == laboratory_panel.panel_id)
        .order_by(PanelVersion.version_number.desc())
        .first()
    )

    if latest_version is None:
        raise HTTPException(
            status_code=404,
            detail="Laboratory panel version not found"
        )

    lab_gene_updates = build_lab_gene_proposals(
        db=db,
        latest_version=latest_version,
        baselines=baselines,
        current_snapshots=current_snapshots,
        source_results=results,

    )

    lab_str_updates = build_lab_str_proposals(
    db=db,
    latest_version=latest_version,
    baselines=baselines,
    current_snapshots=current_snapshots,
  
)

    report = jsonable_encoder({
        "panel_id": laboratory_panel.panel_id,
        "laboratory_version_id": latest_version.panel_version_id,
        "laboratory_version_number": latest_version.version_number,
       "lab_gene_updates": lab_gene_updates,
       "lab_str_updates": lab_str_updates,
        "has_updates": any(
            result["status"] != "unchanged"
            for result in results
        ),
        "source_reviewed_at": laboratory_panel.source_reviewed_at,
        "results": results,
        "current_source_snapshots": current_snapshots
    })


    report["addition_order_token"] = hashlib.sha256(
    json.dumps(
        report["lab_gene_updates"]["new_source_entries"],
        sort_keys=True,
        separators=(",", ":")
       ).encode("utf-8")
    ).hexdigest()

    report["str_addition_order_token"] = hashlib.sha256(
    json.dumps(
        report["lab_str_updates"]["new_source_entries"],
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")
    ).hexdigest()



   
    report["review_token"] = source_report_token(report)
   
    return report




def prepare_selected_str_updates(
    db,
    latest_version,
    report,
    selected_keys
):
    rows = (
        db.query(PanelVersionStr, STR, Gene)
        .join(STR, STR.str_id == PanelVersionStr.str_id)
        .outerjoin(Gene, Gene.gene_id == STR.gene_id)
        .filter(
            PanelVersionStr.panel_version_id
            == latest_version.panel_version_id
        )
        .all()
    )

    proposed = [
        {
            "base_version_str_id": link.panel_version_str_id,
            "str_id": record.str_id,
            "lab_entry_id": (
                str(link.lab_entry_id)
                if link.lab_entry_id else None
            ),
            "entity_name": record.entity_name,
            "gene_symbol": gene.gene_symbol if gene else None,
            "confidence_level": link.confidence_level,
            "phenotypes": link.phenotypes,
            "repeated_sequence": record.repeated_sequence
        }
        for link, record, gene in rows
    ]

    by_entry = {
        item["lab_entry_id"]: item
        for item in proposed
        if item["lab_entry_id"] is not None
    }

    available = {}
    updates = report["lab_str_updates"]

    for proposal in updates["proposals"]:
        entry_id = proposal["lab_entry_id"]

        if proposal["action"] == "remove":
            available[f"str:remove:{entry_id}"] = (
                "remove", entry_id, None
            )

        elif proposal["action"] == "update":
            for field, values in proposal["fields"].items():
                if (
                    field in (
                        "confidence_level",
                        "phenotypes",
                        "repeated_sequence"
                    )
                    and values["status"] in (
                        "update_available", "conflict"
                    )
                ):
                    available[f"str:update:{entry_id}:{field}"] = (
                        "update", entry_id, (field, values)
                    )

    for group_index, group in enumerate(
        updates["new_source_entries"]
    ):
        if group["requires_manual_matching"]:
            continue

        for entry_index, entry in enumerate(group["entries"]):
            available[f"str:add:{group_index}:{entry_index}"] = (
                "add", group, entry
            )

    if selected_keys - available.keys():
        raise HTTPException(
            status_code=400,
            detail="A selected STR change is no longer available"
        )

    removed_ids = set()
    validated_additions = {}

    for key in sorted(selected_keys):
        action, target, value = available[key]

        if action in ("remove", "update"):
            if target not in by_entry:
                raise HTTPException(
                    status_code=409,
                    detail="A selected laboratory STR entry is missing"
                )

            if action == "remove":
                removed_ids.add(target)
            else:
                field, values = value
                by_entry[target][field] = deepcopy(
                    values["new_source"]
                )

        else:
            group = target
            entry = value
            original_id = group["original_panel_id"]
            snapshot = report["current_source_snapshots"][
                str(original_id)
            ]

            new_id = str(uuid4())

            proposed.append({
                "base_version_str_id": None,
                "str_id": None,
                "lab_entry_id": new_id,
                "entity_name": entry["entity_name"],
                "gene_symbol": entry.get("gene_symbol"),
                "confidence_level": entry.get("confidence_level"),
                "phenotypes": entry.get("phenotypes") or [],
                "repeated_sequence": entry.get("repeated_sequence")
            })

            validated_additions[new_id] = {
                "entity_name": entry["entity_name"],
                "gene_symbol": entry.get("gene_symbol"),
                "source_reference": {
                    "original_panel_id": original_id,
                    "source": group["source"],
                    "source_panel_id": snapshot.get("source_panel_id"),
                    "ontario_id": snapshot.get("ontario_id"),
                    "entity_name": entry["entity_name"],
                    "gene_symbol": entry.get("gene_symbol"),
                    "origin_panel_id": entry.get("origin_panel_id")
                }
            }

    proposed = [
        item for item in proposed
        if item["lab_entry_id"] not in removed_ids
    ]

    return proposed, validated_additions


















@app.post(
    "/lab-panels/{panel_id}/source-updates/changes",
    status_code=201
)
def submit_lab_source_updates(
    panel_id: int,
    data: LabSourceUpdateSelection,
    db: Session = Depends(get_db)
):
    try:
        laboratory_panel = (
            db.query(Panel)
            .filter(
                Panel.panel_id == panel_id,
                Panel.source_id == 7,
                Panel.is_active.is_(True)
            )
            .with_for_update()
            .first()
        )

        if laboratory_panel is None:
            raise HTTPException(
                status_code=404,
                detail="Laboratory panel not found"
            )

        latest_version = (
            db.query(PanelVersion)
            .filter(PanelVersion.panel_id == panel_id)
            .order_by(PanelVersion.version_number.desc())
            .first()
        )

        if (
            latest_version is None
            or latest_version.panel_version_id
            != data.laboratory_version_id
        ):
            raise HTTPException(
                status_code=409,
                detail="The laboratory version changed. Reload the review."
            )

        # Coordinate with external approvals, which also lock these panels.
        original_ids = {
            int(key)
            for key in (laboratory_panel.source_baseline or {})
        }
        original_ids.update(
            laboratory_panel.copied_from_panel_ids or []
        )

        (
            db.query(Panel)
            .filter(Panel.panel_id.in_(original_ids))
            .order_by(Panel.panel_id)
            .with_for_update()
            .all()
        )

        report = check_lab_panel_source_updates(
            panel_id=panel_id,
            db=db
        )

        if report["review_token"] != data.review_token:
            raise HTTPException(
                status_code=409,
                detail="The source comparison changed. Reload the review."
            )

        selected = set(data.selected_keys)

        if len(selected) != len(data.selected_keys):
            raise HTTPException(
                status_code=400,
                detail="Duplicate selections"
            )


        selected_str_keys = {
            key for key in selected
            if key.startswith("str:")
        }

        selected_gene_keys = selected - selected_str_keys

        gene_rows = (
            db.query(PanelVersionGene, Gene)
            .join(Gene, Gene.gene_id == PanelVersionGene.gene_id)
            .filter(
                PanelVersionGene.panel_version_id
                == latest_version.panel_version_id
            )
            .all()
        )

        proposed_genes = [
            {
                "gene_symbol": gene.gene_symbol,
                "confidence_level": link.confidence_level,
                "phenotypes": link.phenotypes or [],
                "moi": link.moi,
                "lab_entry_id": (
                    str(link.lab_entry_id)
                    if link.lab_entry_id else None
                ),
                "base_version_gene_id": link.panel_version_gene_id,
            }
            for link, gene in gene_rows
        ]

        genes_by_entry = {
            item["lab_entry_id"]: item
            for item in proposed_genes
            if item["lab_entry_id"] is not None
        }

        available = {}

        for proposal in report["lab_gene_updates"]["proposals"]:
            entry_id = proposal["lab_entry_id"]

            # if proposal["action"] == "remove":
            #     available[f"remove:{entry_id}"] = (
            #         "remove", entry_id, None
            #     )
            if proposal["action"] == "remove":
                if proposal.get("match_by_name"):
                    row_id = proposal["base_version_gene_id"]
                    available[f"remove-by-name:{row_id}"] = (
                        "remove_by_name", row_id, None
                    )
                else:
                    available[f"remove:{entry_id}"] = (
                        "remove", entry_id, None
                    )

            elif proposal["action"] == "update":
                for field, values in proposal["fields"].items():
                    if values["status"] in (
                        "update_available", "conflict"
                    ):
                        available[f"update:{entry_id}:{field}"] = (
                            "update", entry_id, (field, values)
                        )

        for group_index, group in enumerate(
            report["lab_gene_updates"]["new_source_entries"]
        ):
            if group["requires_manual_matching"]:
                continue

            for entry_index, entry in enumerate(group["entries"]):
                available[f"add:{group_index}:{entry_index}"] = (
                    "add", group, entry
                )

        unknown = selected_gene_keys - available.keys()

        if unknown:
            raise HTTPException(
                status_code=400,
                detail="One or more selected changes are no longer available"
            )

        removed_ids = set()
        validated_additions = {}
        removed_gene_row_ids = set()


        for key in sorted(selected_gene_keys):
            action, target, value = available[key]


            if action == "remove_by_name":
                removed_gene_row_ids.add(target)
                continue

            if action == "remove":
                if target not in genes_by_entry:
                    raise HTTPException(
                        status_code=409,
                        detail="A selected laboratory entry is missing"
                    )

                removed_ids.add(target)

            elif action == "update":
                if target not in genes_by_entry:
                    raise HTTPException(
                        status_code=409,
                        detail="A selected laboratory entry is missing"
                    )

                field, values = value
                genes_by_entry[target][field] = deepcopy(
                    values["new_source"]
                )

            else:
                group = target
                entry = value
                original_id = group["original_panel_id"]

                snapshot = report["current_source_snapshots"][
                    str(original_id)
                ]

                new_id = str(uuid4())

                proposed_genes.append({
                    "gene_symbol": entry["gene_symbol"],
                    "confidence_level": entry.get("confidence_level"),
                    "phenotypes": entry.get("phenotypes") or [],
                    "moi": entry.get("moi"),
                    "lab_entry_id": new_id,
                    "base_version_gene_id": None
                })

                # Generated from verified source data, never client input.
                validated_additions[new_id] = {
                    "gene_symbol": entry["gene_symbol"],
                    "source_reference": {
                        "original_panel_id": original_id,
                        "source": group["source"],
                        "source_panel_id": snapshot.get("source_panel_id"),
                        "ontario_id": snapshot.get("ontario_id"),
                        "gene_symbol": entry["gene_symbol"],
                        "origin_panel_id": entry.get("origin_panel_id"),
                        "assertion_url": entry.get("assertion_url"),
                        "sgc_id": entry.get("sgc_id")
                    }
                }

        proposed_genes = [
            item for item in proposed_genes
            if item["lab_entry_id"] not in removed_ids
            and item["base_version_gene_id"] not in removed_gene_row_ids
        ]

        for item in proposed_genes:
             item.pop("base_version_gene_id", None)

        # str_rows = (
        #     db.query(PanelVersionStr)
        #     .filter(
        #         PanelVersionStr.panel_version_id
        #         == latest_version.panel_version_id
        #     )
        #     .all()
        # )

        # proposed_strs = [
        #     {
        #         "str_id": link.str_id,
        #         "confidence_level": link.confidence_level,
        #         "phenotypes": link.phenotypes
        #     }
        #     for link in str_rows
        # ]


    # Preserve existing laboratory STR associations exactly.
        proposed_strs, validated_str_additions = (
            prepare_selected_str_updates(
                db=db,
                latest_version=latest_version,
                report=report,
                selected_keys=selected_str_keys
            )
        )

        proposed_data = {
            "panel_name": latest_version.panel_name,
            "disease_group": latest_version.disease_group,
            "disease_subgroup": latest_version.disease_subgroup,
            "relevant_diseases": latest_version.relevant_diseases,
            "last_updated": date.today().isoformat(),
            "genes": proposed_genes,
            "strs": proposed_strs,
            "_source_update_context": {
                "validated_additions": validated_additions,
                "str_updates_format": 1,
                "validated_str_additions": validated_str_additions,
                "selected_keys": sorted(selected),
                "review_token": data.review_token
            }
        }

        change = PanelChange(
            panel_id=panel_id,
            change_version_id=latest_version.panel_version_id,
            proposed_data=jsonable_encoder(proposed_data),
            status="pending"
        )

        db.add(change)
        db.flush()

        response = {
            "change_id": change.change_id,
            "panel_id": panel_id,
            "status": "pending"
        }

        db.commit()
        return response

    except Exception:
        db.rollback()
        raise



@app.post("/lab-panels/{panel_id}/source-updates/review")
def mark_lab_source_updates_reviewed(
    panel_id: int,
    data: LabSourceReviewCreate,
    db: Session = Depends(get_db)
):
    try:
        panel = (
            db.query(Panel)
            .filter(
                Panel.panel_id == panel_id,
                Panel.source_id == 7,
                Panel.is_active.is_(True)
            )
            .with_for_update()
            .populate_existing()
            .first()
        )

        if panel is None:
            raise HTTPException(
                status_code=404,
                detail="Laboratory panel not found"
            )

        # Wait until laboratory requests have been reviewed.
        pending_change = (
            db.query(PanelChange.change_id)
            .filter(
                PanelChange.panel_id == panel_id,
                PanelChange.change_version_id.isnot(None),
                PanelChange.status == "pending"
            )
            .first()
        )

        if pending_change is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Approve or reject pending laboratory changes "
                    "before marking source updates as reviewed."
                )
            )

        baselines = panel.source_baseline

        if not isinstance(baselines, dict) or not baselines:
            raise HTTPException(
                status_code=400,
                detail="This panel has no source tracking snapshots"
            )

        tracked_ids = {
            int(key) for key in baselines
        } | set(panel.copied_from_panel_ids or [])

        # Include currently active ClinGen group members.
        group = panel.copied_from_group

        if group and group.get("source") == "ClinGen":
            members = (
                db.query(Panel.panel_id)
                .join(Source, Source.source_id == Panel.source_id)
                .filter(
                    Source.source_name == "ClinGen",
                    Panel.is_active.is_(True),
                    func.lower(func.trim(Panel.panel_name))
                    == group["panel_name"].strip().lower()
                )
                .all()
            )

            tracked_ids.update(
                member_id for (member_id,) in members
            )

        # External approval also locks original panel rows.
        (
            db.query(Panel)
            .filter(Panel.panel_id.in_(tracked_ids))
            .order_by(Panel.panel_id)
            .with_for_update()
            .populate_existing()
            .all()
        )

        report = check_lab_panel_source_updates(
            panel_id=panel_id,
            db=db
        )

        if report["review_token"] != data.review_token:
            raise HTTPException(
                status_code=409,
                detail=(
                    "The comparison changed. Reload the page "
                    "and review it again."
                )
            )

        reviewed_snapshots = deepcopy(
            report["current_source_snapshots"]
        )

        # Retain a removal marker for physically missing originals.
        # Otherwise later checks could flag their removal repeatedly.
        for key, old_snapshot in baselines.items():
            if key not in reviewed_snapshots:
                removed_snapshot = deepcopy(old_snapshot)
                removed_snapshot["is_active"] = False
                reviewed_snapshots[key] = removed_snapshot

        panel.source_baseline = jsonable_encoder(reviewed_snapshots)
        panel.source_reviewed_at = datetime.now()

        # Remember newly discovered ClinGen members too.
        panel.copied_from_panel_ids = sorted(
            {int(key) for key in reviewed_snapshots}
        )

        db.flush()

        updated_report = check_lab_panel_source_updates(
            panel_id=panel_id,
            db=db
        )

        result = jsonable_encoder({
            "message": "Source updates marked as reviewed",
            "report": updated_report
        })

        db.commit()
        return result

    except Exception:
        db.rollback()
        raise