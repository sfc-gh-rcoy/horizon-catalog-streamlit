# Horizon Catalog Description Management

Transform your Snowflake data catalog with AI-powered descriptions, smart automation, and a native Streamlit interface.

[![Snowflake](https://img.shields.io/badge/Snowflake-Native_Streamlit-blue.svg)](https://snowflake.com)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![AI](https://img.shields.io/badge/AI-Cortex_Powered-orange.svg)](https://docs.snowflake.com/en/user-guide/snowflake-cortex)

## Features

- **AI description generation** — Cortex-powered stored procedures with existence checking and cost controls
- **Audit trail** — Versioned descriptions with change history
- **Multi-mode operations** — Generate, apply, sync, or preview before committing
- **Native Snowflake Streamlit** — Uses `get_active_session()`; no external connection strings
- **Coverage dashboard** — Track table and column documentation progress

## Quick start

### Prerequisites

- Snowflake account with Streamlit enabled
- Cortex AI access (`SNOWFLAKE.CORTEX_USER` database role)
- `ACCOUNTADMIN` or `SYSADMIN` for initial setup

### Installation

1. **Clone this repository**

   ```bash
   git clone https://github.com/sfc-gh-rcoy/horizon-catalog-streamlit.git
   cd horizon-catalog-streamlit
   ```

2. **Run the setup script in Snowflake**

   ```sql
   -- Execute setup/install_horizon_catalog.sql
   ```

3. **Deploy the Streamlit app**

   Upload `streamlit_app.py`, `environment.yml`, `lib/`, and `pages/` to Snowflake Streamlit. See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions.

## App pages

| Page | Description |
|------|-------------|
| Overview | Coverage metrics and recent activity |
| Tables Browser | Search and browse tables/views |
| AI Generator | Single-table AI description generation |
| Catalog Manager | Batch operations (GENERATE_ONLY, APPLY_ONLY, FULL_SYNC, CHECK_ONLY) |
| Description History | Version history and audit trail |
| Edit Descriptions | Manual table and column editing |

## Architecture

### Database objects

```
HORIZON_DB
└── HORIZON_CATALOG
    ├── horizon_catalog_descriptions
    ├── horizon_catalog_current_descriptions (view)
    ├── HORIZON_CATALOG_GENERATE_DESCRIPTIONS (procedure)
    └── HORIZON_CATALOG_MANAGER (procedure)
```

### Application layout

```
horizon-catalog-streamlit/
├── streamlit_app.py          # Entry point
├── pages/                    # Multi-page UI
├── lib/                      # Connection, operations, UI helpers
└── setup/                    # SQL installation script
```

## Configuration

Database object names default to those created by the install script. Override via environment variables if needed:

- `HORIZON_CATALOG_DATABASE` (default: `HORIZON_DB`)
- `HORIZON_CATALOG_SCHEMA` (default: `HORIZON_CATALOG`)
- `HORIZON_CATALOG_TABLE` (default: fully qualified catalog table name)

No Snowflake account credentials should be stored in this repository. Authentication is handled by the Snowflake Streamlit runtime.

## Best practices

1. Start with `CHECK_ONLY` mode to preview changes.
2. Use `GENERATE_ONLY` to populate the catalog, review, then `APPLY_ONLY`.
3. Set `include_sample_data=FALSE` when sample data is not needed to reduce Cortex cost.
4. Test on a small schema before running batch operations.

## Contributing

Pull requests are welcome. Please open an issue first for large changes.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
