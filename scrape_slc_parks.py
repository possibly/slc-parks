#!/usr/bin/env python3
"""Scrape Every Park SLC uMap data into parks.csv.

The source is the public uMap embedded by City Cast Salt Lake's Every Park SLC page.
This discovers the current uMap datalayers, finds the parks point layer, and writes a
stable CSV next to this script so git history can track changes over time.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

MAP_ID = "1354188"
MAP_URL = (
    "https://umap.openstreetmap.fr/en/map/every-park-slc_1354188"
    "?scaleControl=false&miniMap=false&scrollWheelZoom=false&zoomControl=true"
    "&editMode=disabled&moreControl=true&searchControl=null"
    "&tilelayersControl=null&embedControl=null&datalayersControl=true"
    "&onLoadPanel=none&captionBar=false&captionMenus=true"
)
DATALAYER_URL_TEMPLATE = "https://umap.openstreetmap.fr/en/datalayer/{map_id}/{layer_id}/"
USER_AGENT = "parkslc-csv-scraper/1.0"
OUTPUT_CSV = Path(__file__).with_name("parks.csv")

PARK_LAYER_HINTS = {"Park Name", "City Cast Rating", "Park Management", "Bathrooms"}
CSV_FIELD_ORDER = [
    "Park Name",
    "City",
    "Zip Code",
    "City Cast Rating",
    "Park Management",
    "Location",
    "Bathrooms",
    "Pool",
    "Pond",
    "Grills",
    "Pavillion",
    "Gardens",
    "Baseball Diamond",
    "Softball Diamond",
    "Toddler Friendly Play Area",
    "Kid Play Area",
    "Off Leash Dog Area",
    "Water Fountain",
    "Splash Pad",
    "Skate Park",
    "Basketball Court",
    "Disc Golf",
    "Beach Volleyball Court",
    "Volleyball Court",
    "Soccer Field",
    "River or Stream",
    "Tennis Courts",
    "Pickleball Courts",
    "Fitness Area",
    "Accessible Path",
    "latitude",
    "longitude",
    "Additional Notes",
]


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc


def fetch_json(url: str) -> Any:
    return json.loads(fetch_text(url))


def load_map_settings() -> dict[str, Any]:
    page = fetch_text(MAP_URL)
    match = re.search(r'<script id="map-settings"[^>]*data-settings="([^"]+)"', page)
    if not match:
        raise RuntimeError("Could not find uMap map-settings data in map HTML")
    return json.loads(html.unescape(match.group(1)))


def feature_sort_key(feature: dict[str, Any]) -> tuple[str, str, str]:
    props = feature.get("properties") or {}
    name = str(props.get("Park Name") or props.get("NAME") or props.get("name") or "")
    city = str(props.get("City") or "")
    coordinates = json.dumps(feature.get("geometry", {}).get("coordinates"), sort_keys=True)
    return (name.casefold(), city.casefold(), coordinates)


def looks_like_parks_layer(collection: dict[str, Any]) -> bool:
    if collection.get("type") != "FeatureCollection":
        return False
    for feature in collection.get("features", []):
        properties = set((feature.get("properties") or {}).keys())
        if PARK_LAYER_HINTS.issubset(properties):
            return True
    return False


def point_coordinates(feature: dict[str, Any]) -> tuple[Any, Any]:
    geometry = feature.get("geometry") or {}
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates") or []
        if len(coords) >= 2:
            return coords[1], coords[0]
    return "", ""


def csv_fields(features: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = {"latitude", "longitude"}
    for feature in features:
        seen.update((feature.get("properties") or {}).keys())
    ordered = [field for field in CSV_FIELD_ORDER if field in seen]
    ordered.extend(sorted(seen - set(ordered)))
    return ordered


def write_parks_csv(collection: dict[str, Any], path: Path) -> int:
    features = sorted(collection.get("features", []), key=feature_sort_key)
    fields = csv_fields(features)
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        for feature in features:
            row = dict(feature.get("properties") or {})
            row["latitude"], row["longitude"] = point_coordinates(feature)
            writer.writerow({field: row.get(field, "") for field in fields})
    return len(features)


def find_parks_layer() -> dict[str, Any]:
    settings = load_map_settings()
    properties = settings.get("properties") or {}
    datalayers = sorted(properties.get("datalayers", []), key=lambda layer: layer.get("rank", 0))
    if not datalayers:
        raise RuntimeError("No datalayers found in uMap settings")

    candidates: list[dict[str, Any]] = []
    for layer in datalayers:
        layer_id = layer["id"]
        url = DATALAYER_URL_TEMPLATE.format(map_id=MAP_ID, layer_id=layer_id)
        collection = fetch_json(url)
        if looks_like_parks_layer(collection):
            candidates.append(collection)

    if not candidates:
        raise RuntimeError("Could not identify the parks point layer")

    # uMap currently exposes two matching parks layers. Use the largest matching
    # layer, then the first in map rank order, to avoid writing boundary/metadata layers.
    return max(candidates, key=lambda collection: len(collection.get("features", [])))


def main() -> int:
    parks = find_parks_layer()
    count = write_parks_csv(parks, OUTPUT_CSV)
    print(f"Wrote {OUTPUT_CSV} ({count} parks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
