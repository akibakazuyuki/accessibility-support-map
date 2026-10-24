#!/usr/bin/env python3
"""国交省の歩行空間ネットワークデータがある地区ごとに「通れるか」の材料を集めて書き出す。
赤羽は data/akabane.json、ほかの地区は data/areas/<id>.json、一覧は data/areas.json。

- 歩道の段差・幅・坂・階段など：国土交通省「歩行空間ネットワークデータ（赤羽駅周辺）」
  （ほこナビDP、公共データ利用規約 第1.0版）。コードの意味は歩行空間ネットワークデータ整備仕様（2024年7月）による
- トイレ・エレベーター・入口・車椅子対応の施設：OpenStreetMap（ODbL）を Overpass API で取得

使い方: python3 scripts/build_area.py [link.geojson node.geojson overpass.json]
引数を省くと、ほこナビDPの一覧（CKAN API）から全地区をネットで取得する（GitHub Actions 用）。
手元の試験ではファイルを渡す（赤羽として書き出す）。
"""
import json, os, re, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

AREA = "akabane"
CKAN = "https://ckan.hokonavi.go.jp"
NWD_PAGE = CKAN + "/dataset/nwd_akabane_station"
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
  nwr["name"]["amenity"]({b});
  nwr["name"]["shop"]({b});
  nwr["name"]["tourism"]({b});
  nwr["name"]["leisure"]({b});
  nwr["name"]["healthcare"]({b});
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
            "entrance", "amenity", "shop", "tourism", "healthcare", "operator", "description",
            # 場所のシート用：障害者用駐車場・エレベーター・屋内・ベビーカー・住所
            "capacity:disabled", "elevator", "indoor", "location", "stroller", "cuisine",
            "addr:full", "addr:province", "addr:city", "addr:quarter", "addr:neighbourhood", "addr:block_number", "addr:housenumber"]


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
            if not t.get("name") or "wheelchair" not in t:
                continue
        out.append({"k": kind, "osm": e["type"][0] + str(e["id"]), "ll": [r6(lon), r6(lat)],
                    "t": {k: t[k] for k in TAG_KEYS if k in t}})
    out.sort(key=lambda p: p["osm"])
    return out


CAT_KEYS = ["amenity", "shop", "tourism", "leisure", "healthcare", "cuisine"]


def build_places(osm):
    """検索用：名前のある施設を [名前, 種類, 経度, 緯度, 車椅子] で並べる"""
    out, seen = [], set()
    for e in osm.get("elements", []):
        t = e.get("tags") or {}
        name = t.get("name")
        lat = e.get("lat", (e.get("center") or {}).get("lat"))
        lon = e.get("lon", (e.get("center") or {}).get("lon"))
        if not name or lat is None or lon is None:
            continue
        cat = "|".join(k + "=" + t[k] for k in CAT_KEYS if k in t)
        if not cat:
            continue
        key = (name, round(lat, 4), round(lon, 4))
        if key in seen:
            continue
        seen.add(key)
        out.append([name, cat, r6(lon), r6(lat), t.get("wheelchair", "")])
    out.sort(key=lambda p: (p[0], p[2]))
    return out


def list_areas():
    """ほこナビDPから歩行空間ネットワークデータの一覧（GeoJSON の link と node があるもの）"""
    q = urllib.parse.urlencode({"q": "歩行空間ネットワークデータ", "rows": 200})
    res = json.loads(get(CKAN + "/api/3/action/package_search?" + q))["result"]["results"]
    out = []
    for d in res:
        link = node = None
        for r in d.get("resources", []):
            u = r.get("url") or ""
            if u.endswith("link.geojson"):
                link = u
            elif u.endswith("node.geojson"):
                node = u
        if not (link and node):
            print("skip (GeoJSON なし)", d["name"], file=sys.stderr)
            continue
        name = re.sub(r"^歩行空間ネットワークデータ\s*[（(]|[）)]\s*$", "", d["title"]).strip()
        aid = AREA if d["name"] == "nwd_akabane_station" else re.sub(r"[^a-z0-9-]", "-", d["name"].lower())
        out.append({"id": aid, "name": name, "link": link, "node": node, "page": CKAN + "/dataset/" + d["name"]})
    return out


def path_of(aid):
    return f"data/{AREA}.json" if aid == AREA else f"data/areas/{aid}.json"


def code_stats(links):
    """仕様の版ちがい（コードが1つずれる）に気づけるよう、段差・坂・幅の値の分布を出す"""
    st = {}
    for k in ("lv", "sl", "w"):
        c = {}
        for L in links:
            c[L[k]] = c.get(L[k], 0) + 1
        st[k] = dict(sorted(c.items()))
    return st


def build_one(a, link_gj, node_gj, osm=None):
    links, nodes, dates = build_links(link_gj, node_gj)
    if not links:
        raise ValueError("歩行空間データが空です")
    bbox = bbox_of(links)
    if osm is None:
        osm = overpass(bbox)
    pois = build_pois(osm)
    places = build_places(osm)
    out = {
        "area": a["id"], "name": a["name"], "bbox": bbox,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sources": [
            {"id": "nwd", "name": "国土交通省 歩行空間ネットワークデータ（" + a["name"] + "）", "url": a["page"],
             "license": "公共データ利用規約（第1.0版）", "surveyed": [dates[0], dates[-1]] if dates else None},
            {"id": "osm", "name": "OpenStreetMap", "url": "https://www.openstreetmap.org/copyright",
             "license": "ODbL 1.0（© OpenStreetMap contributors）"},
        ],
        "nodes": nodes, "links": links, "pois": pois, "places": places,
    }
    with open(path_of(a["id"]), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{a['id']}: links={len(links)} nodes={len(nodes)} pois={len(pois)} places={len(places)} "
          f"surveyed={dates[:1]}..{dates[-1:]} codes={code_stats(links)}")
    return {"id": a["id"], "name": a["name"], "file": path_of(a["id"]), "bbox": bbox}


def main():
    os.makedirs("data/areas", exist_ok=True)
    if len(sys.argv) == 4:
        link_gj, node_gj, osm = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4])
        build_one({"id": AREA, "name": "赤羽駅周辺", "page": NWD_PAGE}, link_gj, node_gj, osm)
        return
    index = []
    for a in list_areas():
        try:
            index.append(build_one(a, json.loads(get(a["link"])), json.loads(get(a["node"]))))
        except (Exception, SystemExit) as e:
            # 1地区が失敗しても他は続ける。前回の分のファイルがあれば一覧に残す
            print("失敗", a["id"], e, file=sys.stderr)
            if os.path.exists(path_of(a["id"])):
                with open(path_of(a["id"]), encoding="utf-8") as f:
                    index.append({"id": a["id"], "name": a["name"], "file": path_of(a["id"]), "bbox": json.load(f)["bbox"]})
        time.sleep(15)  # Overpass に負担をかけない
    if not index:
        raise SystemExit("1地区も作れませんでした")
    index.sort(key=lambda x: (x["id"] != AREA, x["id"]))
    with open("data/areas.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"areas={len(index)}")


if __name__ == "__main__":
    main()
