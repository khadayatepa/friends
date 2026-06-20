"""Turn a city/place name into lat/lng via OpenStreetMap Nominatim.
Called only when a friend is added or their location changes, then the
coordinates are stored in the DB (so we never geocode on page load)."""
import requests


def geocode(place):
    place = (place or "").strip()
    if not place:
        return None, None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "FriendsWorldMap/1.0"},
            timeout=15,
        )
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None, None
