"""Oracle Autonomous DB access for the Friends app (python-oracledb, thin mode).

Thin mode is pure Python — no Oracle Instant Client needed, so it runs on
Streamlit Community Cloud as-is. Connection settings come from st.secrets.
"""
import base64
import io
import os
import tempfile
import zipfile

import oracledb
import streamlit as st


@st.cache_resource(show_spinner=False)
def _pool():
    """Create a connection pool once per session, configured from secrets."""
    cfg = st.secrets["oracle"]
    kwargs = dict(
        user=cfg["user"],
        password=cfg["password"],
        dsn=cfg["dsn"],              # e.g. "prashant26ai_medium"
        min=1, max=4, increment=1,
    )
    # mTLS wallet path: a base64-encoded wallet .zip stored in secrets.
    wallet_b64 = cfg.get("wallet_b64")
    if wallet_b64:
        wdir = os.path.join(tempfile.gettempdir(), "adb_wallet")
        os.makedirs(wdir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(wallet_b64))) as zf:
            zf.extractall(wdir)
        kwargs.update(
            config_dir=wdir,
            wallet_location=wdir,
            wallet_password=cfg.get("wallet_password", ""),
        )
    return oracledb.create_pool(**kwargs)


def _conn():
    return _pool().acquire()


# ----------------------------------------------------------------- reads
def list_friends():
    sql_f = """
        SELECT id, name, phone, TO_CHAR(dob,'YYYY-MM-DD'),
               email, location, TO_CHAR(anniversary,'YYYY-MM-DD'),
               photo_url, lat, lng
        FROM friends ORDER BY name
    """
    sql_k = "SELECT friend_id, name, TO_CHAR(dob,'YYYY-MM-DD') FROM kids ORDER BY id"
    with _conn() as con:
        cur = con.cursor()
        rows = cur.execute(sql_f).fetchall()
        kids_by = {}
        for fid, kname, kdob in cur.execute(sql_k).fetchall():
            kids_by.setdefault(fid, []).append({"name": kname, "dob": kdob or ""})
    friends = []
    for r in rows:
        friends.append({
            "id": r[0], "name": r[1], "phone": r[2] or "", "dob": r[3] or "",
            "email": r[4] or "", "location": r[5] or "", "anniversary": r[6] or "",
            "photo": r[7] or "", "lat": r[8], "lng": r[9],
            "kids": kids_by.get(r[0], []),
        })
    return friends


# ----------------------------------------------------------------- writes
def add_friend(d):
    with _conn() as con:
        cur = con.cursor()
        new_id = cur.var(oracledb.NUMBER)
        cur.execute("""
            INSERT INTO friends (name, phone, dob, email, location,
                                 anniversary, photo_url, lat, lng)
            VALUES (:name, :phone, TO_DATE(:dob,'YYYY-MM-DD'), :email, :location,
                    TO_DATE(:anniv,'YYYY-MM-DD'), :photo, :lat, :lng)
            RETURNING id INTO :new_id
        """, name=d["name"], phone=d["phone"], dob=d["dob"] or None,
             email=d["email"], location=d["location"], anniv=d["anniversary"] or None,
             photo=d["photo"], lat=d["lat"], lng=d["lng"], new_id=new_id)
        fid = int(new_id.getvalue()[0])
        _replace_kids(cur, fid, d.get("kids", []))
        con.commit()
        return fid


def update_friend(fid, d):
    with _conn() as con:
        cur = con.cursor()
        cur.execute("""
            UPDATE friends SET name=:name, phone=:phone,
                   dob=TO_DATE(:dob,'YYYY-MM-DD'), email=:email, location=:location,
                   anniversary=TO_DATE(:anniv,'YYYY-MM-DD'), photo_url=:photo,
                   lat=:lat, lng=:lng, updated_at=SYSTIMESTAMP
            WHERE id=:fid
        """, name=d["name"], phone=d["phone"], dob=d["dob"] or None,
             email=d["email"], location=d["location"], anniv=d["anniversary"] or None,
             photo=d["photo"], lat=d["lat"], lng=d["lng"], fid=fid)
        _replace_kids(cur, fid, d.get("kids", []))
        con.commit()


def delete_friend(fid):
    with _conn() as con:
        cur = con.cursor()
        cur.execute("DELETE FROM friends WHERE id=:fid", fid=fid)  # kids cascade
        con.commit()


def _replace_kids(cur, fid, kids):
    cur.execute("DELETE FROM kids WHERE friend_id=:fid", fid=fid)
    for k in kids:
        if (k.get("name") or "").strip():
            cur.execute(
                "INSERT INTO kids (friend_id, name, dob) "
                "VALUES (:fid, :name, TO_DATE(:dob,'YYYY-MM-DD'))",
                fid=fid, name=k["name"].strip(), dob=(k.get("dob") or None))
