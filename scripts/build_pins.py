#!/usr/bin/env python3
"""全国のトイレ・エレベーター・車椅子OKの施設・障害者用駐車場を、0.1度四方の区画ごとに data/pins/ に書き出す。

国交省データの地区の外で、地図のピンと「近くの車椅子トイレ」などに使う。形は地区のファイルの pois・places と同じ。
材料は Geofabrik の日本の OpenStreetMap（ODbL）を osmium で絞って GeoJSON 行にしたもの（.github/workflows/pins.yml）。

使い方: python3 scripts/build_pins.py pins.geojsonseq
"""
import json, math, os, shutil, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_area import TAG_KEYS, r6  # noqa: E402

OUT = "data/pins"
GRID = 10  # 1度を何区画に分けるか（0.1度≒11km）


def center(g):
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point":
        return c
    pts = {"LineString": lambda: c, "Polygon": lambda: c[0], "MultiPolygon": lambda: c[0][0],
           "MultiLineString": lambda: c[0]}.get(t, lambda: None)()
    if not pts:
        return None
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def main(path):
    tiles = {}
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e")
            if not line:
                continue
            ft = json.loads(line)
            t = dict(ft.get("properties") or {})
            osm = str(t.pop("@type", "n"))[0] + str(t.pop("@id", ""))
            c = center(ft.get("geometry") or {})
            if not c:
                continue
            lon, lat = r6(c[0]), r6(c[1])
            key = f"{math.floor(lat * GRID)}_{math.floor(lon * GRID)}"
            tile = tiles.setdefault(key, {"pois": [], "places": []})
            if t.get("amenity") == "toilets":
                kind = "toilet"
            elif t.get("highway") == "elevator":
                kind = "elevator"
            else:
                kind = "place"
            if t.get("amenity") == "parking" and t.get("capacity:disabled") not in (None, "no", "0"):
                tile["places"].append([t.get("name") or "障害者用駐車場", "amenity=parking", lon, lat, t.get("wheelchair", "")])
                continue
            if kind == "place" and (not t.get("name") or "wheelchair" not in t):
                continue
            tile["pois"].append({"k": kind, "osm": osm, "ll": [lon, lat], "t": {k: t[k] for k in TAG_KEYS if k in t}})
            n += 1
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for key, tile in tiles.items():
        if not tile["pois"] and not tile["places"]:
            continue
        tile["pois"].sort(key=lambda p: p["osm"])
        tile["places"].sort()
        with open(f"{OUT}/{key}.json", "w", encoding="utf-8") as f:
            json.dump(tile, f, ensure_ascii=False, separators=(",", ":"))
    with open(f"{OUT}/index.json", "w", encoding="utf-8") as f:
        json.dump({"grid": GRID, "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                   "tiles": sorted(k for k, v in tiles.items() if v["pois"] or v["places"])}, f, separators=(",", ":"))
    print(f"pins={n} tiles={len(tiles)}")


if __name__ == "__main__":
    main(sys.argv[1])
