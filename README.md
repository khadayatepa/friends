# Friends World Map — Streamlit + Oracle Autonomous DB

A private, hosted version of the Friends map. The app runs on **Streamlit
Community Cloud**; all friend data lives in **your own Oracle Autonomous
Database** (so edits persist and the personal data stays in your DB, not on
Streamlit's ephemeral disk).

```
Browser → Streamlit Cloud (app)  ──oracledb (thin)──►  Oracle ADB (your data)
```

Features: world map with photo markers, live **"Happy Birthday" flashing** on the
day, **birthday-within-N-hours** highlight, search, and full **add / edit /
delete** written straight to Oracle.

---

## Step 1 — Create the schema in your ADB

Connect **as ADMIN** (OCI Console → your ADB → **Database Actions → SQL**) and run:

1. **`sql/01_create_user.sql`** — creates the low-privilege `FRIENDS_APP` user.
   ⚠️ Change the password in that file first; remember it for Step 3.
2. Then sign in **as `FRIENDS_APP`** and run **`sql/02_schema.sql`** — creates the
   `FRIENDS` and `KIDS` tables (with a couple of sample rows).

## Step 2 — Enable TLS and copy the connect string (no wallet)

You're using a **wallet-less TLS** connection, so:

1. OCI Console → your ADB → **Network** → set **Mutual TLS (mTLS) authentication**
   to **Not required** (this allows plain TLS).
2. **Database Connection → Connection Strings → TLS** → copy the
   **`prashant26ai_medium`** descriptor — the long `(description=...)` string.

> ⚠️ Without a wallet you must use that **full descriptor** as `dsn`, not the short
> alias `prashant26ai_medium` (the alias only lives inside a wallet's
> `tnsnames.ora`). No wallet files or `wallet_*` secrets are needed.

## Step 3 — Configure secrets

Copy `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` and fill in:

```toml
[oracle]
user = "FRIENDS_APP"
password = "the password from step 1"
dsn = """(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1521)(host=adb.<region>.oraclecloud.com))(connect_data=(service_name=<id>_prashant26ai_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))"""

[app]
password = ""              # optional gate; set to require a password
highlight_window_hours = 2
```

## Step 4 — Run locally (test before deploying)

```powershell
cd streamlit_oracle
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Opens at http://localhost:8501. Add/edit/delete a friend → confirm it appears in
the DB (Database Actions → SQL → `SELECT * FROM friends;`).

## Step 5 — Deploy to Streamlit Community Cloud

1. Push **this `streamlit_oracle/` folder** to a GitHub repo.
   - ✅ `.gitignore` already excludes `secrets.toml` and the wallet — never commit them.
2. Go to **share.streamlit.io → Create app**, pick the repo/branch, set the main
   file to `streamlit_app.py`.
3. In **Advanced settings → Secrets**, paste the *same* contents as your local
   `secrets.toml`.
4. Deploy.

## Step 6 — Make it private 🔒

- In the app's Streamlit Cloud settings, set it to **Private** and invite only
  your own Google account(s) as viewers, **and/or** set `[app] password` in
  secrets for a built-in password gate.
- The database is always protected by credentials + TLS regardless.

---

### Notes
- **Geocoding** (city → lat/lng) runs only when you add a friend or change their
  location; coordinates are stored in the DB, so page loads don't re-geocode.
- **Photos** must be public, browser-openable image URLs.
- `python-oracledb` runs in **thin mode** — no Oracle Instant Client needed,
  which is why it works on Streamlit Cloud unchanged.
- Files: `streamlit_app.py` (UI) · `db.py` (Oracle CRUD) · `mapview.py` (embedded
  Leaflet map) · `geocode.py` · `sql/` (schema) · `tools/encode_wallet.py`.
