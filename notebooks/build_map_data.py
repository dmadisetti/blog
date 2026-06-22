"""Bake the Project Setti hex-bin map into a compact GeoJSON bundle for the
in-post altair island (which runs in the blog venv: altair/pandas/numpy only,
no geopandas). Mirrors the canonical settings of notebooks/setti.py:
explicit per-band morph, packing A, N=1 cell/km, 27 km offshore, 1 km waves.

Geometry is emitted in UTM-20N metres shifted to a local origin so altair can
draw it with project(type="identity", reflectY=True) — equal-area, north-up,
matching the matplotlib render. Run with the geopandas venv:

    /home/dylan/src/setti-venv/bin/python notebooks/build_map_data.py
"""
import json, math
import numpy as np, pandas as pd, geopandas as gpd
import shapely.geometry as sg
from shapely.ops import voronoi_diagram, unary_union

UTM = 32620
WAVE_KM, N, EXT = 1.0, 1, 20.0           # canonical locked state (cropped to 20 km offshore)
DATA = "data"

# --- coastline ---
land_ll = gpd.read_file(f"{DATA}/dominica_gadm.geojson").geometry.iloc[0]
land_m = gpd.GeoSeries([land_ll], crs=4326).to_crs(UTM).iloc[0]
sea = land_m.buffer(EXT * 1000).difference(land_m)

# --- hexes: explicit per-band Voronoi (verbatim from setti.py) ---
def voronoi_cells(pts, clip):
    mp = sg.MultiPoint([sg.Point(x, y) for x, y in pts])
    vd = voronoi_diagram(mp, envelope=clip.envelope.buffer(6000))
    out = [g.intersection(clip) for g in vd.geoms]
    out = [c for c in out if (not c.is_empty) and c.area > 0]
    gdf = gpd.GeoDataFrame(geometry=out, crs=UTM)
    gdf["cx"] = gdf.geometry.centroid.x
    gdf["cy"] = gdf.geometry.centroid.y
    return gdf

def ring_pts(r_km, n, off):
    ring = land_m.buffer(r_km * 1000).exterior
    L = ring.length
    return [(p.x, p.y) for p in (ring.interpolate(((j + off) / n) * L) for j in range(n))]

def build_explicit(p_r, ext, clip):
    p_v = 2 * p_r / math.sqrt(3)
    K = max(1, int(round(ext / p_r)))
    pts = []
    for k in range(K):
        r = (k + 0.5) * p_r
        L = land_m.buffer(r * 1000).exterior.length
        n = max(3, int(round(L / (p_v * 1000))))
        pts += ring_pts(r, n, (k % 2) * 0.5)
    return voronoi_cells(pts, clip)

hexes = build_explicit(WAVE_KM / N, EXT, sea).reset_index(drop=True)
hexes["cid"] = range(len(hexes))

# --- bin sightings: total + per year ---
sdf = pd.read_csv(f"{DATA}/sightings.csv")
# drop east/Atlantic outliers (the whales are off the leeward WEST coast; a few
# rows sit ~26 km east at round junk coords like -61.0004 and distort the frame)
sdf = sdf[sdf.lon < -61.24].reset_index(drop=True)
pts = gpd.GeoDataFrame(sdf, geometry=gpd.points_from_xy(sdf.lon, sdf.lat), crs=4326).to_crs(UTM)
years = sorted(int(y) for y in sdf.year.unique())
sj = gpd.sjoin(pts, hexes[["cid", "geometry"]], predicate="within", how="inner")
hexes["count"] = hexes["cid"].map(sj.groupby("cid").size()).fillna(0).astype(int)
for y in years:
    c = sj[sj.year == y].groupby("cid").size()
    hexes[f"y{y}"] = hexes["cid"].map(c).fillna(0).astype(int)
lit = hexes[hexes["count"] > 0].copy()
print(f"{len(lit)} lit cells / {len(hexes)} | {int(hexes['count'].sum())} sightings | years {years}")

# --- view frame = tight bbox of (island ∪ lit hexes) + small margin, so the
# rings clip at the chart edges instead of being cut mid-air ---
_view = unary_union([land_m] + list(lit.geometry))
_vb = _view.bounds
PAD = 2500
frame = sg.box(_vb[0] - PAD, _vb[1] - PAD, _vb[2] + PAD, _vb[3] + PAD)

# enough 1 km rings to reach the farthest frame corner (fill the frame)
_corners = [(frame.bounds[i], frame.bounds[j]) for i in (0, 2) for j in (1, 3)]
_maxk = int(math.ceil(max(land_m.distance(sg.Point(c)) for c in _corners) / 1000)) + 1
rings = []
for k in range(1, _maxk + 1):
    g = land_m.buffer(k * 1000).exterior.intersection(frame)
    if not g.is_empty:
        rings.append((k, g))

# distance labels along a coast-parallel ray (every 2 km), like the matplotlib map
_oc = land_m.centroid
_o = sg.Point(_oc.x - 0.7071 * 6500, _oc.y - 0.7071 * 6500)
_mrr = np.array(land_m.minimum_rotated_rectangle.exterior.coords)
_edg = _mrr[1:] - _mrr[:-1]
_ev = _edg[int(np.argmax((_edg ** 2).sum(1)))]
_ux, _uy = _ev / np.hypot(_ev[0], _ev[1])
if _uy > 0:
    _ux, _uy = -_ux, -_uy
_ray = sg.LineString([(_o.x, _o.y), (_o.x + _ux * 200000, _o.y + _uy * 200000)])
label_pts = []
for k in range(2, _maxk + 1, 2):
    it = land_m.buffer(k * 1000).exterior.intersection(_ray)
    if it.is_empty:
        continue
    pc = [c for gg in (it.geoms if hasattr(it, "geoms") else [it]) for c in gg.coords]
    wp = max(pc, key=lambda c: (c[0] - _o.x) ** 2 + (c[1] - _o.y) ** 2)
    if frame.contains(sg.Point(wp)):
        label_pts.append((k, wp))

# --- serialise in shifted UTM metres (round to whole m) ---
ox, oy = frame.bounds[0], frame.bounds[1]
def shift(x, y): return [round(x - ox, 1), round(y - oy, 1)]
def ring_xy(geom):
    parts = geom.geoms if geom.geom_type.startswith("Multi") else [geom]
    return [[shift(x, y) for x, y in getattr(p, "exterior", p).coords] for p in parts]

def feat(geom, props):
    g = geom.geoms if geom.geom_type.startswith("Multi") else [geom]
    polys = [[ [shift(x, y) for x, y in p.exterior.coords] ] for p in g]
    gj = ({"type": "Polygon", "coordinates": polys[0]} if len(polys) == 1
          else {"type": "MultiPolygon", "coordinates": polys})
    return {"type": "Feature", "geometry": gj, "properties": props}

island_clip = land_m.intersection(frame)
bundle = {
    "origin_m": [round(ox), round(oy)],
    "width_m": round(frame.bounds[2] - ox), "height_m": round(frame.bounds[3] - oy),
    "years": years, "max_count": int(lit["count"].max()),
    "island": {"type": "FeatureCollection", "features": [feat(island_clip, {})]},
    "hexes": {"type": "FeatureCollection", "features": [
        feat(row.geometry, {"count": int(row["count"]),
                            **{f"y{y}": int(row[f"y{y}"]) for y in years}})
        for _, row in lit.iterrows()]},
    "labels": [{"x": shift(*wp)[0], "y": shift(*wp)[1], "text": f"{k} km"}
               for k, wp in label_pts],
    "waterlines": {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"km": k},
         "geometry": {"type": "MultiLineString",
                      "coordinates": [[shift(x, y) for x, y in
                                       (p.coords)] for p in
                                      (g.geoms if g.geom_type.startswith("Multi") else [g])]}}
        for k, g in rings]},
}
out = "setti_map.json"
json.dump(bundle, open(out, "w"), separators=(",", ":"))
import os
print(f"wrote notebooks/{out}  {os.path.getsize(out)/1024:.0f} KB  "
      f"(hexes={len(lit)}, rings={len(rings)})")
