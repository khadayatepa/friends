"""Friends World Map — Streamlit + Oracle Autonomous Database.

Map with photo markers, live "Happy Birthday" flashing, birthday-within-N-hours
highlight, and full add/edit/delete backed by Oracle ADB.
"""
import datetime as dt

import streamlit as st
import streamlit.components.v1 as components

import db
from geocode import geocode
from mapview import build_map_html

st.set_page_config(page_title="Friends World Map", page_icon="🎂", layout="wide")

WINDOW_HOURS = int(st.secrets.get("app", {}).get("highlight_window_hours", 2))
MIN_DATE = dt.date(1900, 1, 1)
TODAY = dt.date.today()


# ------------------------------------------------ optional private gate
def check_password():
    pw = st.secrets.get("app", {}).get("password")
    if not pw:
        return True  # no password configured -> open
    if st.session_state.get("authed"):
        return True
    st.title("🔒 Friends World Map")
    entered = st.text_input("Password", type="password")
    if entered:
        if entered == pw:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Wrong password")
    return False


if not check_password():
    st.stop()


# ------------------------------------------------ helpers
def to_iso(d):
    return d.isoformat() if isinstance(d, dt.date) else ""


def parse_iso(s):
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        return None


def md_of(s):
    d = parse_iso(s)
    return (d.month, d.day) if d else None


def event_state(friend, now):
    """Return 'today' / 'soon' / None for a friend's nearest event."""
    win = dt.timedelta(hours=WINDOW_HOURS)
    state = None
    sources = [friend["dob"], friend["anniversary"]] + [k["dob"] for k in friend["kids"]]
    for s in sources:
        md = md_of(s)
        if not md:
            continue
        m, d = md
        if now.month == m and now.day == d:
            return "today"
        try:
            nxt = dt.datetime(now.year, m, d)
        except ValueError:
            continue
        if nxt < now:
            try:
                nxt = dt.datetime(now.year + 1, m, d)
            except ValueError:
                continue
        if dt.timedelta(0) <= (nxt - now) <= win:
            state = "soon"
    return state


def kids_editor(initial, key):
    rows = initial or [{"name": "", "dob": ""}]
    edited = st.data_editor(
        rows, num_rows="dynamic", key=key,
        column_config={
            "name": st.column_config.TextColumn("Kid name"),
            "dob": st.column_config.TextColumn("DOB (YYYY-MM-DD)"),
        },
        hide_index=True, use_container_width=True,
    )
    return [{"name": r.get("name", ""), "dob": r.get("dob", "")}
            for r in edited if (r.get("name") or "").strip()]


def resolve_coords(location, prev_loc="", prev_lat=None, prev_lng=None):
    """Geocode only when location is new or changed."""
    location = (location or "").strip()
    if not location:
        return None, None
    if location == (prev_loc or "").strip() and prev_lat is not None:
        return prev_lat, prev_lng
    return geocode(location)


# ------------------------------------------------ load data
try:
    friends = db.list_friends()
except Exception as e:
    st.error(f"Could not connect to Oracle ADB: {e}")
    st.info("Check your `.streamlit/secrets.toml` (user / password / dsn) and that "
            "the schema + tables exist (run the SQL scripts).")
    st.stop()

now = dt.datetime.now()
for f in friends:
    f["_state"] = event_state(f, now)

# ------------------------------------------------ header / today banner
st.title("🎂 Friends World Map")
today_people = [f for f in friends if f["_state"] == "today"]
if today_people:
    st.success("🎉 " + "  •  ".join(f"Happy day, {f['name']}!" for f in today_people) + " 🎉")

# ------------------------------------------------ layout
left, right = st.columns([3, 1])

with right:
    st.subheader("🔍 Search")
    q = st.text_input("Find a friend", label_visibility="collapsed", placeholder="name or city…")
    shown = [f for f in friends
             if not q or q.lower() in (f["name"] + " " + f["location"]).lower()]

    st.caption(f"{len(friends)} friends • {sum(1 for f in friends if f['lat'] is not None)} on map")

    st.markdown(f"**⏰ Birthday within {WINDOW_HOURS}h**")
    soon = [f for f in friends if f["_state"] == "soon"]
    st.write("\n".join(f"- {f['name']}" for f in soon) or "_nobody in the window_")

    st.markdown("**🎉 Today**")
    st.write("\n".join(f"- {f['name']}" for f in today_people) or "_nobody today_")

with left:
    components.html(build_map_html(shown, WINDOW_HOURS, height=560), height=600)

# ------------------------------------------------ manage (add / edit / delete)
st.divider()
st.subheader("✏️ Manage friends")
tab_add, tab_edit = st.tabs(["➕ Add", "✏️ Edit / Delete"])

with tab_add:
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name *")
        location = c2.text_input("Location (city)")
        c3, c4 = st.columns(2)
        dob = c3.date_input("Date of birth", value=None, min_value=MIN_DATE, max_value=TODAY)
        anniv = c4.date_input("Anniversary", value=None, min_value=MIN_DATE, max_value=TODAY)
        c5, c6 = st.columns(2)
        phone = c5.text_input("Phone")
        email = c6.text_input("Email")
        photo = st.text_input("Photo URL")
        st.caption("Kids (optional)")
        kids = kids_editor([], key="kids_add")
        submitted = st.form_submit_button("Add friend", type="primary")
        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                lat, lng = resolve_coords(location)
                db.add_friend({
                    "name": name.strip(), "phone": phone, "dob": to_iso(dob),
                    "email": email, "location": location, "anniversary": to_iso(anniv),
                    "photo": photo, "lat": lat, "lng": lng, "kids": kids,
                })
                st.success(f"Added {name}." + ("" if lat else " (location not found — no map pin)"))
                st.rerun()

with tab_edit:
    if not friends:
        st.info("No friends yet.")
    else:
        names = {f"{f['name']} (#{f['id']})": f for f in friends}
        pick = st.selectbox("Choose a friend", list(names.keys()))
        f = names[pick]
        with st.form("edit_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name *", f["name"])
            location = c2.text_input("Location (city)", f["location"])
            c3, c4 = st.columns(2)
            dob = c3.date_input("Date of birth", value=parse_iso(f["dob"]),
                                min_value=MIN_DATE, max_value=TODAY)
            anniv = c4.date_input("Anniversary", value=parse_iso(f["anniversary"]),
                                  min_value=MIN_DATE, max_value=TODAY)
            c5, c6 = st.columns(2)
            phone = c5.text_input("Phone", f["phone"])
            email = c6.text_input("Email", f["email"])
            photo = st.text_input("Photo URL", f["photo"])
            st.caption("Kids")
            kids = kids_editor(f["kids"], key=f"kids_edit_{f['id']}")
            colu, cold = st.columns(2)
            do_update = colu.form_submit_button("💾 Save changes", type="primary")
            do_delete = cold.form_submit_button("🗑️ Delete")
        if do_update:
            lat, lng = resolve_coords(location, f["location"], f["lat"], f["lng"])
            db.update_friend(f["id"], {
                "name": name.strip(), "phone": phone, "dob": to_iso(dob),
                "email": email, "location": location, "anniversary": to_iso(anniv),
                "photo": photo, "lat": lat, "lng": lng, "kids": kids,
            })
            st.success("Saved.")
            st.rerun()
        if do_delete:
            db.delete_friend(f["id"])
            st.warning(f"Deleted {f['name']}.")
            st.rerun()
