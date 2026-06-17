# Deployment Guide

## Quick Deployment to Snowflake

### Step 1: Install database objects

1. Open a Snowflake SQL worksheet.
2. Run the installation script from this repository:

```sql
-- Upload install_horizon_catalog.sql to a stage, then:
!source @~/horizon-catalog-streamlit/setup/install_horizon_catalog.sql
```

Or paste and execute the contents of `setup/install_horizon_catalog.sql` directly.

This creates:

- `HORIZON_DB` database (customize in the SQL script if needed)
- `HORIZON_CATALOG` schema
- Catalog tables, views, and stored procedures

Estimated time: 2–5 minutes.

### Step 2: Deploy the Streamlit app

**Option A: Snowflake UI**

1. Go to **Streamlit** in the Snowflake UI.
2. Click **+ Streamlit App**.
3. Name the app (for example, `Horizon_Catalog`).
4. Upload the project files:
   - `streamlit_app.py`
   - `environment.yml`
   - `lib/` (all files)
   - `pages/` (all files)
5. Set the main file to `streamlit_app.py`.
6. Click **Create**.

**Option B: SnowCLI**

```bash
snow streamlit deploy \
  --name horizon_catalog_app \
  --file streamlit_app.py \
  --database HORIZON_DB \
  --schema HORIZON_CATALOG
```

### Step 3: Grant permissions

```sql
GRANT USAGE ON STREAMLIT HORIZON_DB.HORIZON_CATALOG.HORIZON_CATALOG_APP TO ROLE PUBLIC;

GRANT USAGE ON PROCEDURE HORIZON_DB.HORIZON_CATALOG.HORIZON_CATALOG_GENERATE_DESCRIPTIONS TO ROLE PUBLIC;
GRANT USAGE ON PROCEDURE HORIZON_DB.HORIZON_CATALOG.HORIZON_CATALOG_MANAGER TO ROLE PUBLIC;

GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE PUBLIC;
```

Adjust role names for your environment.

### Step 4: Launch

Open the Streamlit app in Snowflake and select the database/schema you want to document.

---

## File structure

```
horizon-catalog-streamlit/
├── streamlit_app.py
├── pages/
│   ├── 1_Overview.py
│   ├── 2_Tables_Browser.py
│   ├── 3_AI_Generator.py
│   ├── 4_Catalog_Manager.py
│   ├── 5_Description_History.py
│   └── 6_Edit_Descriptions.py
├── lib/
│   ├── app_bootstrap.py
│   ├── config.py
│   ├── snowpark_connection.py
│   ├── catalog_operations.py
│   └── ui_components.py
├── setup/
│   └── install_horizon_catalog.sql
├── environment.yml
├── requirements.txt
└── README.md
```

---

## Configuration

The app uses Snowflake's built-in Snowpark session (`get_active_session()`). No account credentials belong in the code.

If you install catalog objects under different names, set these environment variables before deploying:

| Variable | Default |
|----------|---------|
| `HORIZON_CATALOG_DATABASE` | `HORIZON_DB` |
| `HORIZON_CATALOG_SCHEMA` | `HORIZON_CATALOG` |
| `HORIZON_CATALOG_TABLE` | `{database}.{schema}.horizon_catalog_descriptions` |

---

## Troubleshooting

### App won't start

- Confirm all files are uploaded (`lib/`, `pages/`, `streamlit_app.py`).
- Confirm `streamlit_app.py` is set as the main file.
- Run the app inside Snowflake Streamlit, not locally without a Snowpark session.

### Can't call procedures

- Confirm `setup/install_horizon_catalog.sql` completed successfully.
- Confirm the user has `USAGE` on the procedures.
- Confirm the user has the `CORTEX_USER` database role.

### Database context errors

- Confirm the user can access the target database and schema.
- Use the sidebar selectors on the home page to switch context.
