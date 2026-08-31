"""Project-wide paths and constants. Single source of truth for directory layout."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_INTERIM = PROJECT_ROOT / "data" / "interim"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_EXTERNAL = PROJECT_ROOT / "data" / "external"

OUTPUTS_FIGURES = PROJECT_ROOT / "outputs" / "figures"
OUTPUTS_TABLES = PROJECT_ROOT / "outputs" / "tables"
OUTPUTS_MODELS = PROJECT_ROOT / "outputs" / "models"
OUTPUTS_REPORTS = PROJECT_ROOT / "outputs" / "reports"

DOCS_DIR = PROJECT_ROOT / "docs"

# ICD-10 underlying-cause codes for diabetes mellitus, per docs/data_feasibility_audit.md #2
DIABETES_ICD10_CODES = ["E10", "E11", "E12", "E13", "E14"]

# CDC WONDER database identifiers, per docs/DATA_SOURCES.md #1-2.
# NOTE: the short numeric/alnum "database code" WONDER's XML API expects (e.g. the
# value that belongs in each request's <input><parameter name="database"> or
# equivalent Description tag) must be read off an XML export generated from an
# actual interactive query at https://wonder.cdc.gov, or from the current API
# documentation page (wonder.cdc.gov/wonder/help/wonder-api.html), which lists
# the code per database. It is not hardcoded here to avoid fabricating a value
# that CDC could have changed. See src/ingestion/cdc_wonder.py for where it is
# required and how to obtain it.
WONDER_UCD_1999_2020_URL = "https://wonder.cdc.gov/ucd-icd10.html"
WONDER_UCD_2018_2024_SR_URL = "https://wonder.cdc.gov/ucd-icd10-expanded.html"

# County change-point eligibility thresholds, per docs/research_protocol.md #6
MIN_NONSUPPRESSED_YEARS = 15
MIN_YEARS_EACH_SIDE_OF_BREAK = 5
MIN_COUNTY_POPULATION = 50_000

# Study windows, per docs/research_protocol.md #5
PRIMARY_WINDOW = (1999, 2020)
EXTENSION_WINDOW = (2018, 2024)
HETEROGENEITY_WINDOW = (2010, 2020)
