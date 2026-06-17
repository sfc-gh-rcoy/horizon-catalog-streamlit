"""
Horizon Catalog configuration.

These defaults match the objects created by setup/install_horizon_catalog.sql.
Override via environment variables when deploying to a different database/schema.
"""

import os

CATALOG_DATABASE = os.environ.get("HORIZON_CATALOG_DATABASE", "HORIZON_DB")
CATALOG_SCHEMA = os.environ.get("HORIZON_CATALOG_SCHEMA", "HORIZON_CATALOG")
CATALOG_TABLE = os.environ.get(
    "HORIZON_CATALOG_TABLE",
    f"{CATALOG_DATABASE}.{CATALOG_SCHEMA}.horizon_catalog_descriptions",
)

GENERATE_DESCRIPTIONS_PROC = (
    f"{CATALOG_DATABASE}.{CATALOG_SCHEMA}.HORIZON_CATALOG_GENERATE_DESCRIPTIONS"
)
CATALOG_MANAGER_PROC = f"{CATALOG_DATABASE}.{CATALOG_SCHEMA}.HORIZON_CATALOG_MANAGER"
