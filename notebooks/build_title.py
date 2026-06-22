"""Render the Project Setti title cartouche (white panel + wave-line ripples
echoing the glyph outlines + serif text) as a transparent PNG, reusing the exact
matplotlib treatment from notebooks/setti.py. It's a fixed corner overlay for the
altair island (not geographically placed), so a baked image is the faithful way
to keep the rippled-text look that Vega can't draw.

    /home/dylan/src/setti-venv/bin/python notebooks/build_title.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
import shapely.geometry as sg
from shapely.ops import unary_union

INK = "#0b2e22"     # Rainforest coast ink (dark green), matches the island
WLC = "#3a566e"     # waterline slate
GAP = 16
TSTEP, TNR = 6.0, 3

def mk_tp(s, size, y, weight="normal"):
    return TextPath((0, y), s, size=size, prop=FontProperties(family=["serif"], weight=weight))

def tp_geom(tp):
    rings = [sg.Polygon(p) for p in tp.to_polygons(closed_only=True) if len(p) >= 4]
    rings = [r for r in rings if r.is_valid and r.area > 1e-9]
    g = None
    for r in sorted(rings, key=lambda x: -x.area):
        g = r if g is None else g.symmetric_difference(r)
    return g

tps = [mk_tp("Project Setti", 30, 0, "bold"),
       mk_tp("sperm whale sightings", 15, -(GAP + 8)),
       mk_tp("Dominica · 2021 – 2026", 15, -(2 * GAP + 8))]
tg = unary_union([tp_geom(t) for t in tps])

fig, ax = plt.subplots(figsize=(6, 3))
ax.set_aspect("equal"); ax.axis("off")
outer = tg.buffer(TNR * TSTEP)
for p in (outer.geoms if hasattr(outer, "geoms") else [outer]):
    ax.fill(*p.exterior.xy, color="white", zorder=1)            # white panel
for k in range(1, TNR + 1):                                     # wave-line ripples (exterior-only)
    bp = tg.buffer(k * TSTEP)
    for p in (bp.geoms if hasattr(bp, "geoms") else [bp]):
        ax.plot(*p.exterior.xy, color=WLC, lw=1.0, alpha=0.85, zorder=2)
for t in tps:                                                   # crisp serif glyphs
    ax.add_patch(PathPatch(t, facecolor=INK, edgecolor="none", zorder=3))
b = outer.bounds
ax.set_xlim(b[0] - 2, b[2] + 2); ax.set_ylim(b[1] - 2, b[3] + 2)

os.makedirs("../docs/assets", exist_ok=True)
out = "../docs/assets/setti_title.png"
fig.savefig(out, transparent=True, bbox_inches="tight", pad_inches=0.04, dpi=200)
plt.close(fig)
print(f"wrote {out}  panel aspect (w/h) = {(b[2]-b[0])/(b[3]-b[1]):.3f}")
