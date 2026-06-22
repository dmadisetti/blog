# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "geopandas==1.1.3",
#     "matplotlib==3.11.0",
#     "numpy==2.4.6",
#     "osmnx==2.1.0 ; sys_platform != 'emscripten'",
#     "pandas==3.0.3",
#     "scipy==1.17.1",
#     "shapely==2.1.2",
# ]
# ///

import marimo

__generated_with = "0.23.9"
app = marimo.App(
    width="medium",
    auto_download=["html"],
)


@app.cell
def _():
    import marimo as mo
    import io, json, os, urllib.request
    import numpy as np
    import geopandas as gpd
    import shapely.geometry as sg
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    UTM20N = 32620  # Dominica sits in UTM zone 20N — metres, good for 1 km offsets
    UA = "whale-waterlines/0.1 (dylan.madisetti@gmail.com)"
    return UA, UTM20N, gpd, io, json, mo, np, os, plt, sg, urllib


@app.cell
def _(UA, UTM20N, gpd, json, os, sg, urllib):
    # Dominica's true coastline (GADM level-0 — follows the shore, not territorial waters).
    # Cached to disk so reruns are instant.
    _CACHE = "data/dominica_gadm.geojson"

    def _load_coast():
        if os.path.exists(_CACHE):
            return gpd.read_file(_CACHE).geometry.iloc[0]
        url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_DMA_0.json"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        raw = json.load(urllib.request.urlopen(req, timeout=60))["features"][0]["geometry"]
        geom = sg.shape(raw)
        gpd.GeoSeries([geom], crs=4326).to_file(_CACHE, driver="GeoJSON")
        return geom

    land_ll = _load_coast()      # lon/lat (EPSG:4326)
    land_m = gpd.GeoSeries([land_ll], crs=4326).to_crs(UTM20N).iloc[0]   # metres
    return land_ll, land_m


@app.cell(hide_code=True)
def _(WAVE_KM, hex_extent, land_m):
    # Waterlines: outward buffers of the coast, WAVE_KM apart — enough rings to cover the view.
    import math as _m
    SPACING_KM = WAVE_KM
    N_LINES = max(2, _m.ceil((float(hex_extent.value) + 16.0) / WAVE_KM))
    water_rings = [land_m.buffer(SPACING_KM * 1000 * i).boundary
                   for i in range(1, N_LINES + 1)]
    return (water_rings,)


@app.cell(hide_code=True)
def _(UTM20N, gpd, land_ll, os):
    import osmnx as ox

    # Full-island OSM export — roads, rivers, towns — cached to disk (slow first run ~15 s).
    _OSM = "data/island"

    def _clean(g, cols):
        g = g[g.geometry.notna() & ~g.geometry.is_empty].copy()
        for c in cols:
            if c not in g.columns:
                g[c] = None
            g[c] = g[c].apply(lambda v: ",".join(map(str, v)) if isinstance(v, list) else v)
        return gpd.GeoDataFrame(g[cols + ["geometry"]], crs=g.crs)

    def _layer(name, cols, fetch):
        p = f"{_OSM}_{name}.gpkg"
        if os.path.exists(p):
            return gpd.read_file(p)
        g = _clean(fetch(), cols)
        g.to_file(p, driver="GPKG")
        return g

    roads_ll  = _layer("roads",  ["highway"],
                       lambda: ox.graph_to_gdfs(ox.graph_from_polygon(land_ll, network_type="drive", retain_all=True), nodes=False))
    rivers_ll = _layer("rivers", ["waterway"],
                       lambda: ox.features_from_polygon(land_ll, tags={"waterway": ["river", "stream"]}))
    places_ll = _layer("places", ["name", "place"],
                       lambda: ox.features_from_polygon(land_ll, tags={"place": ["city", "town", "village", "hamlet"]}))

    roads_m  = roads_ll.to_crs(UTM20N)
    rivers_m = rivers_ll.to_crs(UTM20N)
    # towns as labelled points (use representative point so polygons/relations work too)
    places_m = places_ll.to_crs(UTM20N).copy()
    places_m["geometry"] = places_m.representative_point()
    len(roads_m), len(rivers_m), len(places_m)
    return rivers_ll, roads_ll


@app.cell(hide_code=True)
def _(np, os, urllib):
    import gzip

    # SRTM 30 m elevation (AWS public mirror), cached to disk. Tile N15W062 covers
    # lat [15, 16] (row 0 = north) and lon [-62, -61] — Dominica sits inside it.
    _DEM = "data/dominica_dem.npy"

    def _load_dem():
        if os.path.exists(_DEM):
            return np.load(_DEM)
        url = "https://elevation-tiles-prod.s3.amazonaws.com/skadi/N15/N15W062.hgt.gz"
        hgt = gzip.decompress(urllib.request.urlopen(url, timeout=60).read())
        d = np.frombuffer(hgt, dtype=">i2").reshape(3601, 3601).astype("float32")
        np.save(_DEM, d)
        return d

    dem_full = _load_dem()
    dem_lat = np.linspace(16.0, 15.0, 3601)    # row index -> latitude
    dem_lon = np.linspace(-62.0, -61.0, 3601)  # col index -> longitude
    # crop to Dominica's bbox (+margin) so the auto-cached blob is ~1 MB, not 52 MB
    _rm = (dem_lat <= 15.70) & (dem_lat >= 15.13)
    _cm = (dem_lon >= -61.55) & (dem_lon <= -61.18)
    dem_full = dem_full[np.ix_(_rm, _cm)]
    dem_lat = dem_lat[_rm]
    dem_lon = dem_lon[_cm]
    int(np.nanmax(np.where(dem_full > 0, dem_full, np.nan)))
    return dem_full, dem_lat, dem_lon


@app.cell(hide_code=True)
def _(mo):
    # Land-focused palettes (prettymaps-inspired). Water stays white so the upcoming
    # whale heatmap has a clean canvas. Each palette styles relief / rivers / roads / ink.
    PALETTES = {
        "Tropic":     dict(relief=["#1b7340","#3fa15c","#7cc47f","#b6d99a","#e7dcae"],
                           contour="#0d4023", river="#1f7fa6", road="#9c6b3f",
                           coast="#0d3b2e", waterline="#d3dde2"),
        "Rainforest": dict(relief=["#0d3b2e","#1d6b4a","#3f9b6e","#86c79a","#cfe3b0"],
                           contour="#0b2e22", river="#1b6f8c", road="#7a5230",
                           coast="#0b2e22", waterline="#d3dde2"),
        "Volcanic":   dict(relief=["#22303f","#3d5a6c","#6e7b6b","#a98b5e","#e3b878"],
                           contour="#1e2a36", river="#5fb0cf", road="#e6cfa0",
                           coast="#16202a", waterline="#dbe2e6"),
        "Coral":      dict(relief=["#fbeec2","#f4d59a","#eaa46a","#d9744b","#a84b3a"],
                           contour="#7a3b2e", river="#13988f", road="#e2603f",
                           coast="#7a3b2e", waterline="#cfe0e0"),
        "Sand":       dict(relief=["#ede2c2","#dccb9f","#c7b07d","#ad8a55","#8c6a3f"],
                           contour="#2f4858", river="#4a7f97", road="#6f513a",
                           coast="#2f4858", waterline="#c9d2d6"),
        "Mono":       dict(relief=["#1a1a1a","#4d4d4d","#808080","#b3b3b3","#f2f2f2"],
                           contour="#2b2b2b", river="#555555", road="#777777",
                           coast="#111111", waterline="#d3dde2"),
        "Mono inv":   dict(relief=["#f2f2f2","#b3b3b3","#808080","#4d4d4d","#1a1a1a"],
                           contour="#2b2b2b", river="#555555", road="#777777",
                           coast="#111111", waterline="#d3dde2"),
    }
    palette_sel = mo.ui.dropdown(options=list(PALETTES), value="Rainforest", label="🎨 Map palette")
    palette_sel
    return PALETTES, palette_sel


@app.cell(hide_code=True)
def _(mo):
    # Hex heatmap control panel — canonical "Project Setti" state
    WAVE_OPTS = {"1 km": 1.0, "1 mi": 1.609344, "2 km": 2.0, "2 mi": 3.218688,
                 "3 mi": 4.828032, "5 km": 5.0, "5 mi": 8.04672, "10 km": 10.0}
    wave_spacing = mo.ui.dropdown(options=list(WAVE_OPTS), value="1 km", label="〰️ Wave spacing")
    hex_packing = mo.ui.dropdown(options=["A · flat offshore", "B · vertex offshore"],
                                 value="A · flat offshore", label="🔷 Packing")
    morph_mode = mo.ui.dropdown(
        options=["planar (regular grid)", "explicit (per-band)", "cvt (relaxed)", "conformal (grow)"],
        value="explicit (per-band)", label="🌊 Morph mode")
    hex_N = mo.ui.slider(1, 4, step=1, value=1, label="cells per wave-band", show_value=True)
    hex_extent = mo.ui.slider(2, 30, step=1, value=27, label="offshore extent (km)", show_value=True)
    lloyd_iters = mo.ui.slider(0, 12, step=1, value=5, label="CVT relax iters", show_value=True)
    wave_weight = mo.ui.slider(0.2, 2.5, step=0.1, value=0.5, label="wave line weight", show_value=True)
    cont_smooth = mo.ui.slider(0, 14, step=1, value=6, label="contour smoothing", show_value=True)
    hill_alpha = mo.ui.slider(0.0, 1.0, step=0.02, value=0.14, label="hillshade opacity", show_value=True)
    title_gap = mo.ui.slider(-8, 28, step=1, value=16, label="title line spacing", show_value=True)
    hex_show = mo.ui.checkbox(value=True, label="heatmap")
    hex_edges = mo.ui.checkbox(value=False, label="cell edges")
    lay_hill = mo.ui.checkbox(value=True, label="hillshade")
    lay_cont = mo.ui.checkbox(value=False, label="contours")
    lay_riv = mo.ui.checkbox(value=False, label="rivers")
    lay_road = mo.ui.checkbox(value=False, label="roads")
    lay_coast = mo.ui.checkbox(value=True, label="coastline")
    lay_wave = mo.ui.checkbox(value=True, label="waterlines")
    coast_match = mo.ui.checkbox(value=False, label="coast = wave weight")
    contour_palette = mo.ui.checkbox(value=False, label="contours: palette color")
    mo.vstack([
        mo.md("### 🧭 Project Setti — controls"),
        mo.hstack([morph_mode, hex_packing, wave_spacing], justify="start"),
        hex_N, hex_extent, lloyd_iters, wave_weight, cont_smooth, hill_alpha, title_gap,
        mo.md("**layers**"),
        mo.hstack([lay_hill, lay_cont, lay_riv, lay_road, lay_coast, lay_wave], justify="start"),
        mo.hstack([coast_match, contour_palette, hex_show, hex_edges], justify="start"),
    ])
    return (
        WAVE_OPTS,
        coast_match,
        cont_smooth,
        contour_palette,
        hex_N,
        hex_edges,
        hex_extent,
        hex_packing,
        hex_show,
        hill_alpha,
        lay_coast,
        lay_cont,
        lay_hill,
        lay_riv,
        lay_road,
        lay_wave,
        lloyd_iters,
        morph_mode,
        title_gap,
        wave_spacing,
        wave_weight,
    )


@app.cell(hide_code=True)
def _(WAVE_OPTS, wave_spacing):
    # parse the wave-spacing choice into km (drives both the waterlines and the hex radial pitch)
    WAVE_KM = WAVE_OPTS[wave_spacing.value]
    _parts = wave_spacing.value.split()
    WAVE_NUM = float(_parts[0]); WAVE_UNIT = _parts[1]    # e.g. 2, "mi"  → label in chosen unit
    return WAVE_KM, WAVE_NUM, WAVE_UNIT


@app.cell(hide_code=True)
def _(
    UTM20N,
    WAVE_KM,
    gpd,
    hex_N,
    hex_extent,
    hex_packing,
    land_m,
    lloyd_iters,
    morph_mode,
    sg,
):
    import math
    from shapely.ops import voronoi_diagram

    # ----- packing math: radial pitch = 1/N km locks rows onto the waterlines -----
    def hex_side_km(packing, N):
        return 1.0 / (N * math.sqrt(3)) if packing == "A" else 2.0 / (3 * N)

    def _hexagon(cx, cy, s, pointy):
        a0 = 30.0 if pointy else 0.0
        return sg.Polygon([(cx + s * math.cos(math.radians(a0 + 60 * k)),
                            cy + s * math.sin(math.radians(a0 + 60 * k))) for k in range(6)])

    def build_planar(s_m, packing, sea_poly):
        minx, miny, maxx, maxy = sea_poly.bounds
        pointy = (packing == "B")
        centers = []
        if not pointy:
            dx, dy = 1.5 * s_m, math.sqrt(3) * s_m
            for c in range(-1, int((maxx - minx) / dx) + 2):
                cx = minx + c * dx
                for r in range(-1, int((maxy - miny) / dy) + 2):
                    centers.append((cx, miny + r * dy + (c % 2) * (dy / 2)))
        else:
            dy, dx = 1.5 * s_m, math.sqrt(3) * s_m
            for r in range(-1, int((maxy - miny) / dy) + 2):
                cy = miny + r * dy
                for c in range(-1, int((maxx - minx) / dx) + 2):
                    centers.append((minx + c * dx + (r % 2) * (dx / 2), cy))
        _minarea = 0.06 * (3 * math.sqrt(3) / 2) * s_m ** 2
        polys, cxs, cys = [], [], []
        for cx, cy in centers:
            h = _hexagon(cx, cy, s_m, pointy)
            if h.intersects(sea_poly):
                clip = h.intersection(sea_poly)
                if (not clip.is_empty) and clip.area > _minarea:
                    polys.append(clip); cxs.append(cx); cys.append(cy)
        return gpd.GeoDataFrame({"cx": cxs, "cy": cys}, geometry=polys, crs=UTM20N)

    # ----- shared Voronoi tessellator (used by all morph routes) -----
    def voronoi_cells(pts, clip):
        mp = sg.MultiPoint([sg.Point(x, y) for x, y in pts])
        vd = voronoi_diagram(mp, envelope=clip.envelope.buffer(6000))
        out = []
        for g in vd.geoms:
            c = g.intersection(clip)
            if (not c.is_empty) and c.area > 0:
                out.append(c)
        gdf = gpd.GeoDataFrame(geometry=out, crs=UTM20N)
        gdf["cx"] = gdf.geometry.centroid.x
        gdf["cy"] = gdf.geometry.centroid.y
        return gdf

    def _ring_pts(r_km, n, off):
        ring = land_m.buffer(r_km * 1000).exterior
        L = ring.length
        return [(p.x, p.y) for p in (ring.interpolate(((j + off) / n) * L) for j in range(n))]

    # Route 1 — explicit per-band: equilateral lattice on offset rings (1km-commensurate, defects insert)
    def build_explicit(p_r, ext, packing, clip):
        p_v = 2 * p_r / math.sqrt(3)
        K = max(1, int(round(ext / p_r)))
        pts = []
        for k in range(K):
            r = (k + 0.5) * p_r
            L = land_m.buffer(r * 1000).exterior.length
            n = max(3, int(round(L / (p_v * 1000))))
            pts += _ring_pts(r, n, (k % 2) * 0.5)
        return voronoi_cells(pts, clip)

    # Route 2 — CVT / Lloyd relaxation: seed from planar, relax to centroidal (natural, emergent defects)
    def build_cvt(s_m, packing, clip, iters):
        base = build_planar(s_m, packing, clip)
        pts = list(zip(base["cx"].tolist(), base["cy"].tolist()))
        for _ in range(max(0, iters)):
            g = voronoi_cells(pts, clip)
            pts = list(zip(g["cx"].tolist(), g["cy"].tolist()))
        return voronoi_cells(pts, clip)

    # Route 3 — conformal-ish: fixed spoke count, cells grow with circumference offshore
    def build_conformal(p_r0, ext, packing, clip):
        p_v = 2 * p_r0 / math.sqrt(3)
        L0 = land_m.buffer(0.5 * p_r0 * 1000).exterior.length
        n0 = max(6, int(round(L0 / (p_v * 1000))))
        pts = []; r = 0.0; k = 0
        while r < ext and k < 60:
            Lr = land_m.buffer(max(r, 0.25) * 1000).exterior.length
            pr_km = (math.sqrt(3) / 2) * (Lr / n0) / 1000.0
            pts += _ring_pts(r + pr_km / 2, n0, (k % 2) * 0.5)
            r += pr_km; k += 1
        return voronoi_cells(pts, clip)

    # ----- dispatch -----
    _pack = "A" if hex_packing.value.startswith("A") else "B"
    _N = int(hex_N.value)
    _ext = float(hex_extent.value)
    hex_s_m = hex_side_km(_pack, _N) * WAVE_KM * 1000.0
    sea_poly_m = land_m.buffer(_ext * 1000.0).difference(land_m)
    _mode = morph_mode.value
    if _mode.startswith("planar"):
        hex_cells = build_planar(hex_s_m, _pack, sea_poly_m)
    elif _mode.startswith("explicit"):
        hex_cells = build_explicit(WAVE_KM / _N, _ext, _pack, sea_poly_m)
    elif _mode.startswith("cvt"):
        hex_cells = build_cvt(hex_s_m, _pack, sea_poly_m, int(lloyd_iters.value))
    else:
        hex_cells = build_conformal(WAVE_KM / _N, _ext, _pack, sea_poly_m)
    f"{_mode} · packing {_pack} · {len(hex_cells)} cells"
    return (hex_cells,)


@app.cell(hide_code=True)
def _(UTM20N, gpd):
    import pandas as pd

    # Dad's sperm-whale sightings — GPS + count only (parsed locally from the Chatou permit xlsx)
    _sdf = pd.read_csv("data/sightings.csv")
    sightings_ll = gpd.GeoDataFrame(_sdf, geometry=gpd.points_from_xy(_sdf.lon, _sdf.lat), crs=4326)
    sightings_m = sightings_ll.to_crs(UTM20N)
    f"{len(sightings_m)} sightings, {int(_sdf['year'].min())}–{int(_sdf['year'].max())}"
    return (sightings_m,)


@app.cell(hide_code=True)
def _(gpd, hex_cells, np, sightings_m):
    # Real density: bin sightings into the current cells (count of sightings per cell)
    _cells = hex_cells.reset_index(drop=True).copy()
    _cells["cid"] = range(len(_cells))
    _sj = gpd.sjoin(sightings_m, _cells[["cid", "geometry"]], predicate="within", how="inner")
    _n = _sj.groupby("cid").size()
    _dens = np.zeros(len(_cells))
    _dens[_n.index.values] = _n.values
    hexd = _cells.assign(density=_dens).to_crs(4326)
    f"binned {int(_dens.sum())}/{len(sightings_m)} sightings into {int((_dens>0).sum())}/{len(_cells)} cells (max {int(_dens.max())})"
    return (hexd,)


@app.cell(hide_code=True)
def _(
    PALETTES,
    UTM20N,
    WAVE_KM,
    WAVE_NUM,
    WAVE_UNIT,
    coast_match,
    cont_smooth,
    contour_palette,
    dem_full,
    dem_lat,
    dem_lon,
    gpd,
    hex_edges,
    hex_show,
    hexd,
    hill_alpha,
    io,
    land_ll,
    land_m,
    lay_coast,
    lay_cont,
    lay_hill,
    lay_riv,
    lay_road,
    lay_wave,
    mo,
    np,
    palette_sel,
    plt,
    rivers_ll,
    roads_ll,
    sg,
    title_gap,
    water_rings,
    wave_weight,
):
    from matplotlib.colors import LightSource, LinearSegmentedColormap, Normalize
    from matplotlib.path import Path as _MPath
    from matplotlib.patches import PathPatch as _PPatch
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    from shapely.ops import unary_union
    import base64 as _b64
    import matplotlib.patheffects as pe
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    # Data-driven frame: enlarge Dominica + push east; cap east at the coast.
    _b = land_ll.bounds
    _hot = hexd[hexd["density"] > 0]
    _hb = _hot.total_bounds if len(_hot) else _b
    _mE, _mO = 0.010, 0.018
    _lon0 = min(_b[0], _hb[0]) - _mO
    _lon1 = _b[2] + _mE
    _lat0 = min(_b[1], _hb[1]) - _mE
    _lat1 = max(_b[3], _hb[3]) + _mE

    _PAL = PALETTES[palette_sel.value]
    PAPER = "#ffffff"
    INK = _PAL["coast"]; RIVER = _PAL["river"]; ROAD = _PAL["road"]
    _CONTOUR = _PAL["contour"]; _WLC = "#3a566e"
    _HEATCM = LinearSegmentedColormap.from_list("heat", [plt.cm.Blues(0.16), plt.cm.Blues(0.55), plt.cm.Blues(1.0)])
    _terr = LinearSegmentedColormap.from_list("setti", _PAL["relief"])

    _aspect = 1.0 / np.cos(np.deg2rad((_lat0 + _lat1) / 2))
    _wd, _ht = (_lon1 - _lon0), (_lat1 - _lat0) * _aspect
    fig, ax = plt.subplots(figsize=(8.2 * _wd / _ht, 8.2))
    fig.patch.set_facecolor(PAPER); ax.set_facecolor(PAPER)

    def _land_patch():
        _polys = [land_ll] if land_ll.geom_type == "Polygon" else list(land_ll.geoms)
        _v, _c = [], []
        for _p in _polys:
            for _ring in [_p.exterior, *_p.interiors]:
                _pts = list(_ring.coords)
                _v.extend(_pts); _c.extend([_MPath.MOVETO] + [_MPath.LINETO] * (len(_pts) - 1))
        _pp = _PPatch(_MPath(_v, _c), transform=ax.transData, facecolor="none", edgecolor="none")
        ax.add_patch(_pp); return _pp

    # relief layers (DEM cropped only when needed)
    if lay_hill.value or lay_cont.value:
        _rm = (dem_lat <= _lat1) & (dem_lat >= _lat0)
        _cm = (dem_lon >= _lon0) & (dem_lon <= _lon1)
        _la = dem_lat[_rm][::2]; _lo = dem_lon[_cm][::2]
        _dem = np.where(dem_full[np.ix_(_rm, _cm)][::2, ::2] > 0, dem_full[np.ix_(_rm, _cm)][::2, ::2], np.nan)
        _clip = _land_patch()
    if lay_hill.value:
        _ls = LightSource(azdeg=315, altdeg=45)
        _rgba = _ls.shade(np.nan_to_num(_dem, nan=0.0), cmap=_terr, blend_mode="soft",
                          vert_exag=2.2, dx=60, dy=60, vmin=0, vmax=1450)
        _rgba[..., 3] = np.where(np.isnan(_dem), 0.0, float(hill_alpha.value))
        _im = ax.imshow(_rgba, extent=[_lo.min(), _lo.max(), _la.min(), _la.max()],
                        origin="upper", interpolation="bilinear", zorder=2)
        _im.set_clip_path(_clip)
    if lay_cont.value:
        from scipy.ndimage import gaussian_filter
        _demf = gaussian_filter(np.nan_to_num(_dem, nan=0.0), sigma=float(cont_smooth.value))
        _demf = np.where(np.isnan(_dem), np.nan, _demf)        # smooth real elevation → flowing rings
        _ckw = dict(cmap=_terr, norm=Normalize(vmin=0, vmax=1450)) if contour_palette.value else dict(colors=_WLC)
        _cs = ax.contour(_lo, _la, _demf, levels=np.arange(150, 1450, 200),
                         linewidths=wave_weight.value * 0.85, alpha=0.7, zorder=3, **_ckw)
        _cs.set_clip_path(_clip)

    if lay_riv.value:
        rivers_ll.clip(land_ll).plot(ax=ax, color=RIVER, linewidth=0.5, alpha=0.85, zorder=4)
    if lay_road.value:
        _wmap = {"primary":1.4,"primary_link":1.0,"secondary":1.0,"secondary_link":0.75,
                 "tertiary":0.68,"tertiary_link":0.5,"unclassified":0.42}
        _roads = roads_ll.assign(_lw=roads_ll["highway"].map(lambda h: _wmap.get(str(h).split(",")[0], 0.3)))
        for _lw, _grp in _roads.groupby("_lw"):
            _grp.plot(ax=ax, color=ROAD, linewidth=_lw, alpha=0.8, zorder=5)

    # heatmap — the data (the star)
    if hex_show.value and len(hexd):
        _v = hexd["density"].values.astype(float)
        _mx = _v.max() if _v.max() > 0 else 1.0
        _fc = _HEATCM(_v / _mx); _fc[:, 3] = np.where(_v > 0, 0.9, 0.0)
        _ec = "#9aa6ad" if hex_edges.value else "none"
        hexd.plot(ax=ax, color=_fc, edgecolor=_ec, linewidth=0.12, zorder=4.5)

    if lay_coast.value:
        _clw = wave_weight.value if coast_match.value else 1.3
        _clc = _WLC if coast_match.value else INK
        gpd.GeoSeries([land_ll]).boundary.plot(ax=ax, color=_clc, linewidth=_clw,
                                               alpha=0.85 if coast_match.value else 1.0, zorder=6)

    # waterlines + distance labels (toggleable, weighted)
    if lay_wave.value:
        _wl = gpd.GeoSeries(water_rings, crs=UTM20N).to_crs(4326)
        for _ring in _wl:
            gpd.GeoSeries([_ring]).plot(ax=ax, color=_WLC, linewidth=wave_weight.value, alpha=0.5, zorder=6)
        _halo = [pe.withStroke(linewidth=2.2, foreground="white")]
        _lstep = max(1, int(round(2.0 / WAVE_KM)))
        # staggering direction: island's general axis (min-rotated-rect long edge), oriented south
        _mrr = np.array(land_m.minimum_rotated_rectangle.exterior.coords)
        _edg = _mrr[1:] - _mrr[:-1]
        _e = _edg[int(np.argmax((_edg ** 2).sum(1)))]
        _ux, _uy = _e / np.hypot(_e[0], _e[1])
        if _uy > 0:
            _ux, _uy = -_ux, -_uy
        _oc = land_m.centroid
        _o = sg.Point(_oc.x - 0.7071 * 6500, _oc.y - 0.7071 * 6500)
        _ray = sg.LineString([(_o.x, _o.y), (_o.x + _ux * 150000, _o.y + _uy * 150000)])
        for i, ring_m in enumerate(water_rings):
            if (i + 1) % _lstep:
                continue
            _it = ring_m.intersection(_ray)
            if _it.is_empty:
                continue
            _pts = [c for g in (_it.geoms if hasattr(_it, "geoms") else [_it]) for c in g.coords]
            _wp = max(_pts, key=lambda c: (c[0]-_o.x)**2 + (c[1]-_o.y)**2)
            _pll = gpd.GeoSeries([sg.Point(_wp)], crs=UTM20N).to_crs(4326).iloc[0]
            if _lon0 <= _pll.x <= _lon1 and _lat0 <= _pll.y <= _lat1:
                ax.annotate(f"{(i+1)*WAVE_NUM:g} {WAVE_UNIT}", (_pll.x, _pll.y), fontsize=6.0,
                            color="#1f3a52", ha="center", va="center", zorder=7, path_effects=_halo)

    ax.set_xlim(_lon0, _lon1); ax.set_ylim(_lat0, _lat1)
    ax.set_aspect(_aspect); ax.axis("off")
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # ---- title (lower-left): rings from the outline, text rendered crisply by matplotlib ----
    def _mk_tp(s, size, y, weight="normal"):
        return TextPath((0, y), s, size=size, prop=FontProperties(family=["serif"], weight=weight))
    def _tp_geom(tp):
        rings = [sg.Polygon(p) for p in tp.to_polygons(closed_only=True) if len(p) >= 4]
        rings = [r for r in rings if r.is_valid and r.area > 1e-9]
        g = None
        for r in sorted(rings, key=lambda x: -x.area):
            g = r if g is None else g.symmetric_difference(r)
        return g
    _tps = [_mk_tp("Project Setti", 30, 0, "bold"),
            _mk_tp("sperm whale sightings", 15, -(title_gap.value + 8)),
            _mk_tp("Dominica · 2021 – 2026", 15, -(2 * title_gap.value + 8))]
    _tg = unary_union([_tp_geom(_t) for _t in _tps])
    _TSTEP, _TNR = 6.0, 3
    _tax = inset_axes(ax, width="52%", height="22%", loc="lower left", borderpad=0.8)
    _tax.set_aspect("equal"); _tax.axis("off")
    _outer = _tg.buffer(_TNR * _TSTEP)
    for _p in (_outer.geoms if hasattr(_outer, "geoms") else [_outer]):
        _tax.fill(*_p.exterior.xy, color=PAPER, zorder=1)
    for _k in range(1, _TNR + 1):                # exterior-only rings → no inter-line artifacts
        _bp = _tg.buffer(_k * _TSTEP)
        for _p in (_bp.geoms if hasattr(_bp, "geoms") else [_bp]):
            _tax.plot(*_p.exterior.xy, color=_WLC, lw=wave_weight.value, alpha=0.85, zorder=2)
    for _t in _tps:                              # matplotlib rasterizes the real glyph paths
        _tax.add_patch(_PPatch(_t, facecolor=INK, edgecolor="none", zorder=3))
    _tb = _outer.bounds
    _tax.set_xlim(_tb[0]-2, _tb[2]+2); _tax.set_ylim(_tb[1]-2, _tb[3]+2)

    # ---- density legend (upper-right, horizontal) ----
    if hex_show.value and len(hexd) and hexd["density"].max() > 0:
        _vmax = float(hexd["density"].max())
        _cax = inset_axes(ax, width="24%", height="2.4%", loc="upper right", borderpad=1.4)
        _sm = plt.cm.ScalarMappable(cmap=_HEATCM, norm=Normalize(vmin=0, vmax=_vmax))
        _cb = fig.colorbar(_sm, cax=_cax, orientation="horizontal")
        _cb.outline.set_edgecolor("#3a566e"); _cb.outline.set_linewidth(0.5)
        _cb.set_ticks([0, _vmax]); _cb.ax.set_xticklabels(["0", str(int(_vmax))])
        _cb.ax.tick_params(labelsize=6, colors="#1f3a52", width=0.4, length=2)
        _cb.set_label("sightings / cell", fontsize=7, color="#1f3a52", labelpad=2)

    _png = io.BytesIO()
    fig.savefig(_png, format="png", dpi=220, facecolor=PAPER)
    plt.close(fig)
    mo.image(_png.getvalue(), width=520)
    return


if __name__ == "__main__":
    app.run()
