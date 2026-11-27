from sqlalchemy import Column, Text
from pydantic import BaseModel,Field
from datetime import date
from typing import List
from uuid import UUID


#file bch najem nvalidati l info li dakhalha l user


class LabPanelGeneCreate(BaseModel):
    gene_symbol: str
    confidence_level: str | None = None
    phenotypes: List[str] = []
    moi: str | None = None
    lab_entry_id: UUID | None = None


class LabPanelSTRCreate(BaseModel):
    entity_name: str
    gene_symbol: str
    confidence_level: str | None = None
    phenotypes: List[str] = []
    repeated_sequence: str | None = None
    lab_entry_id: UUID | None = None


class LabPanelCreate(BaseModel):
    panel_name: str
    disease_group: str | None = None
    disease_subgroup: str | None = None
    relevant_diseases: str | None = None
    last_updated: date | None = None

    genes: List[LabPanelGeneCreate] = []
    strs: List[LabPanelSTRCreate] = []


class CopyGeneSelection(BaseModel):
    panel_gene_id: int
    confidence_level: str | None = None
    phenotypes: list[str] = Field(default_factory=list)


class CopySTRSelection(BaseModel):
    panel_str_id: int
    confidence_level: str | None = None
    phenotypes: list[str] = Field(default_factory=list)
    repeated_sequence: str | None = None


class LabPanelCopyCreate(BaseModel):
    source_record_panel_ids: list[int] = Field(min_length=1)

    # True when copying a ClinGen disease group.
    track_clingen_group: bool = False

    panel_name: str = Field(min_length=1)
    disease_group: str | None = None
    disease_subgroup: str | None = None
    relevant_diseases: str | None = None

    genes: list[CopyGeneSelection] = Field(default_factory=list)
    strs: list[CopySTRSelection] = Field(default_factory=list)


class LabSourceUpdateSelection(BaseModel):
    laboratory_version_id: int
    review_token: str = Field(min_length=1)

    # Keys produced by your current frontend checkboxes.
    selected_keys: list[str] = Field(min_length=1)


class LabSourceReviewCreate(BaseModel):
    review_token: str = Field(min_length=1)