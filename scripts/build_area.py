#!/usr/bin/env python3
"""赤羽駅周辺の「通れるか」の材料を集めて data/akabane.json に書き出す。

- 歩道の段差・幅・坂・階段など：国土交通省「歩行空間ネットワークデータ（赤羽駅周辺）」
  （ほこナビDP、公共データ利用規約 第1.0版）。コードの意味は歩行空間ネットワークデータ整備仕様による
- トイレ・エレベーター・入口・車椅子対応の施設：OpenStreetMap（ODbL）を Overpass API で取得

使い方: python3 scripts/build_area.py [link.geojson node.geojson overpass.json]
引数を省くとネットから取得する（GitHub Actions 用）。手元の試験ではファイルを渡す。
"""
import json, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

AREA = "akabane"
NWD = "https://ckan.hokonavi.go.jp/dataset/2a0005b1-cdf2-43b7-81f8-2ce05a987da2/resource/"
LINK_URL = NWD + "55b154d0-ced2-494e-94cb-ff02c623ee79/download/link.geojson"
NODE_URL = NWD + "042e7998-34cc-48ed-b23d-b5953898bed2/download/node.geojson"
NWD_PAGE = "https://ckan.hokonavi.go.jp/dataset/nwd_akabane_station"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = {"User-Agent": "accessibility-support-map (https://github.com/akibakazuyuki/accessibility-support-map)"}

# リンクの項目のうち画面と判定で使うもの（短い名前に詰め替える）
LINK_KEYS = {"rt_struct": "st", "route_type": "rt", "direction": "dir", "width": "w", "vtcl_slope": "sl",
             "lev_diff": "lv", "tfc_signal": "sg", "brail_tile": "bt", "elevator": "ev", "roof": "rf",
             "condition": "cd", "handrail": "hr", "facility": "fc", "door_type": "dr", "tfc_restr": "rs"}


def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:
            print("retry", url, e, file=sys.stderr)
            time.sleep(10 * (i + 1))
    raise SystemExit("取得できませんでした: " + url)


def num(v, default=99):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def r6(x):
    return round(float(x), 6)


def build_links(link_gj, node_gj):
    nodes = {}
    for f in node_gj.get("features", []):
        p = f.get("properties") or {}
        c = (f.get("geometry") or {}).get("coordinates")
        nid = p.get("node_id")
        if nid is None or not c:
            continue
        fl = p.get("floor")
        try:
            fl = float(fl)
        except (TypeError, ValueError):
            fl = 0
        nodes[str(nid)] = [r6(c[0]), r6(c[1]), fl, num(p.get("in_out"), 1)]
    links, dates = [], set()
    for f in link_gj.get("features", []):
        p = f.get("properties") or {}
        g = f.get("geometry") or {}
        cs = g.get("coordinates") or []
        if g.get("type") == "MultiLineString":
            cs = [pt for part in cs for pt in part]
        if len(cs) < 2:
            continue
        L = {"id": str(p.get("link_id")), "a": str(p.get("start_id")), "b": str(p.get("end_id")),
             "d": round(float(p.get("distance") or 0), 1),
             "c": [[r6(x), r6(y)] for x, y, *_ in cs]}
        for k, short in LINK_KEYS.items():
            L[short] = num(p.get(k))
        md = str(p.get("maint_date") or "")[:10]
        if md:
            L["md"] = md
            dates.add(md)
        links.append(L)
    return links, nodes, sorted(dates)


def bbox_of(links, margin=0.003):
    xs = [c[0] for L in links for c in L["c"]]
    ys = [c[1] for L in links for c in L["c"]]
    return [round(v, 5) for v in (min(ys) - margin, min(xs) - margin, max(ys) + margin, max(xs) + margin)]  # 南,西,北,東


def overpass(bbox):
    b = ",".join(str(round(v, 5)) for v in bbox)
    q = f"""[out:json][timeout:120];
(
  nwr["amenity"="toilets"]({b});
  nwr["toilets:wheelchair"]({b});
  nwr["highway"="elevator"]({b});
  node["entrance"]({b});
  nwr["wheelchair"]({b});
);
out center tags;"""
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for url in OVERPASS:
        try:
            return json.loads(get(url, data))
        except SystemExit as e:
            last = e
    raise last


TAG_KEYS = ["name", "wheelchair", "toilets:wheelchair", "wheelchair:description", "door", "automatic_door",
            "width", "step_count", "ramp", "level", "opening_hours", "changing_table", "access", "fee",
            "entrance", "amenity", "shop", "tourism", "healthcare", "operator", "description"]


def build_pois(osm):
    out = []
    for e in osm.get("elements", []):
        t = e.get("tags") or {}
        lat = e.get("lat", (e.get("center") or {}).get("lat"))
        lon = e.get("lon", (e.get("center") or {}).get("lon"))
        if lat is None or lon is None:
            continue
        if t.get("amenity") == "toilets":
            kind = "toilet"
        elif t.get("highway") == "elevator":
            kind = "elevator"
        elif "entrance" in t:
            kind = "entrance"
        else:
            kind = "place"
            if not t.get("name"):
                continue
        out.append({"k": kind, "osm": e["type"][0] + str(e["id"]), "ll": [r6(lon), r6(lat)],
                    "t": {k: t[k] for k in TAG_KEYS if k in t}})
    out.sort(key=lambda p: p["osm"])
    return out


def main():
    if len(sys.argv) == 4:
        link_gj, node_gj, osm = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4])
    else:
        link_gj = json.loads(get(LINK_URL))
        node_gj = json.loads(get(NODE_URL))
        osm = None
    links, nodes, dates = build_links(link_gj, node_gj)
    if not links:
        raise SystemExit("歩行空間データが空です")
    bbox = bbox_of(links)
    if osm is None:
        osm = overpass(bbox)
    pois = build_pois(osm)
    out = {
        "area": AREA, "name": "赤羽駅周辺", "bbox": bbox,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sources": [
            {"id": "nwd", "name": "国土交通省 歩行空間ネットワークデータ（赤羽駅周辺）", "url": NWD_PAGE,
             "license": "公共データ利用規約（第1.0版）", "surveyed": [dates[0], dates[-1]] if dates else None},
            {"id": "osm", "name": "OpenStreetMap", "url": "https://www.openstreetmap.org/copyright",
             "license": "ODbL 1.0（© OpenStreetMap contributors）"},
        ],
        "nodes": nodes, "links": links, "pois": pois,
    }
    with open(f"data/{AREA}.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"links={len(links)} nodes={len(nodes)} pois={len(pois)} surveyed={dates[:1]}..{dates[-1:]}")


if __name__ == "__main__":
    main()
