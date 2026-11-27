from sqlalchemy import ARRAY, BigInteger, Boolean, Column, Date, DateTime, Identity, Integer, Numeric, Text, String, ForeignKey, func, text
from db_SQLAlchemy import Base
from sqlalchemy.dialects.postgresql import JSONB,UUID
from datetime import date
from sqlalchemy.orm import relationship

# file bch ynajem python yefhem l database mteei

class Panel(Base):
    __tablename__ = "panels"

    panel_id = Column(Integer, primary_key=True)
    panel_name = Column(Text)
    disease_group = Column(Text)
    disease_subgroup = Column(Text)
    relevant_diseases = Column(Text)
    source_id = Column(Integer)
    version_id = Column(Integer)
    is_active = Column(Boolean, nullable=False, default=True)
    lab_name = Column(Text, nullable=True)
    ontario_id = Column(Text, nullable=True)
    source_panel_id = Column(Integer, nullable=True)
    child_panel_ids = Column(ARRAY(Integer), nullable=True)
    copied_from_panel_id = Column(Integer,ForeignKey("panels.panel_id", ondelete="RESTRICT"),nullable=True)
    source_baseline = Column(JSONB, nullable=True)
    copied_from_panel_ids = Column(ARRAY(Integer),nullable=True)
    copied_from_group = Column(JSONB,nullable=True)
    source_reviewed_at = Column(DateTime,nullable=True)



class Gene(Base):
    __tablename__ = "genes"

    gene_id = Column(Integer, primary_key=True)
    gene_symbol = Column(Text)


class PanelGene(Base):
    __tablename__ = "panel_gene"

    panel_gene_id = Column(Integer, primary_key=True)
    panel_id = Column(Integer)
    gene_id = Column(Integer)
    confidence_level = Column(Text)
    phenotypes = Column(ARRAY(String))
    moi = Column(Text)
    submitter = Column(Text)
    sgc_id = Column(Text)
    assertion_url = Column(Text)
    origin_panel_id = Column(Integer, nullable=True)


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(Integer, primary_key=True)
    source_name = Column(String)


class STR(Base):
    __tablename__ = "strs"

    str_id = Column(Integer, primary_key=True)
    entity_name = Column(String)
    gene_id = Column(Integer)
    confidence_level = Column(String)
    phenotypes = Column(ARRAY(String))
    repeated_sequence = Column(String)


class PanelSTR(Base):
    __tablename__ = "panel_str"

    panel_str_id = Column(Integer, primary_key=True)
    panel_id = Column(Integer)
    str_id = Column(Integer)
    origin_panel_id = Column(Integer, nullable=True)


class Version(Base):
    __tablename__ = "versions"

    version_id = Column(Integer, primary_key=True)
    source_id = Column(Integer)
    version_number = Column(String)
    last_updated = Column(Date)




class PanelVersion(Base):
    __tablename__ = "panel_versions"

    panel_version_id = Column(Integer, primary_key=True)
    panel_id = Column(Integer, ForeignKey("panels.panel_id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    panel_name = Column(String, nullable=False)
    disease_group = Column(String)
    disease_subgroup = Column(String)
    relevant_diseases = Column(String)
    last_updated = Column(Date, nullable=False)



class PanelVersionGene(Base):
    __tablename__ = "panel_version_gene"

    panel_version_gene_id = Column(Integer, primary_key=True)
    panel_version_id = Column(
        Integer,
        ForeignKey("panel_versions.panel_version_id"),
        nullable=False
    )
    gene_id = Column(
        Integer,
        ForeignKey("genes.gene_id"),
        nullable=False
    )
    confidence_level = Column(String)
    phenotypes = Column(ARRAY(String))
    moi = Column(Text, nullable=True)
    lab_entry_id = Column(UUID(as_uuid=True), nullable=True)
    source_reference = Column(JSONB, nullable=True)





class PanelVersionStr(Base):
    __tablename__ = "panel_version_str"

    panel_version_str_id = Column(Integer, primary_key=True)
    panel_version_id = Column(
        Integer,
        ForeignKey("panel_versions.panel_version_id"),
        nullable=False
    )
    str_id = Column(
        Integer,
        ForeignKey("strs.str_id"),
        nullable=False
    )
    confidence_level = Column(String)
    phenotypes = Column(ARRAY(String))
    lab_entry_id = Column(UUID(as_uuid=True), nullable=True)
    source_reference = Column(JSONB, nullable=True)



class PanelChange(Base):
    __tablename__ = "panel_changes"

    change_id = Column(Integer, primary_key=True)

    panel_id = Column(
        Integer,
        ForeignKey("panels.panel_id"),
        nullable=True
    )

    change_version_id = Column(
        Integer,
        ForeignKey("panel_versions.panel_version_id"),
        nullable=True
    )

    proposed_data = Column(JSONB, nullable=False)


    status = Column(
        Text,
        nullable=False,
        default="pending"
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    reviewed_at = Column(DateTime)



    #ophanet integration
class OrphanetDisease(Base):
    __tablename__ = "orphanet_diseases"

    orpha_code = Column(Integer, primary_key=True, autoincrement=False)
    disease_name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    source = Column(Text, nullable=False)
    orphanet_url = Column(Text)
    disorder_group = Column(Text)
    age_at_onset = Column(
        ARRAY(Text),
        nullable=False,
        server_default=text("ARRAY[]::TEXT[]"),
    )
    inheritance = Column(
        ARRAY(Text),
        nullable=False,
        server_default=text("ARRAY[]::TEXT[]"),
    )

    epidemiology = relationship(
        "OrphanetEpidemiology",
        back_populates="disease",
    )


class OrphanetEpidemiology(Base):
    __tablename__ = "orphanet_epidemiology"

    epidemiology_id = Column(BigInteger, Identity(), primary_key=True)
    orpha_code = Column(
        Integer,
        ForeignKey("orphanet_diseases.orpha_code"),
        nullable=False,
        index=True,
    )
    prevalence_type = Column(Text)
    prevalence_qualification = Column(Text)
    prevalence_geography = Column(Text)
    prevalence_class = Column(Text)
    reported_value = Column(Numeric)
    reference = Column(Text)
    validation_status = Column(Text)

    disease = relationship(
        "OrphanetDisease",
        back_populates="epidemiology",
    )