"""Render the 1200x630 Open Graph / Twitter social card for the Project Setti
post, from the same notebooks/setti_map.json the in-post altair island uses (so
the share preview matches the blog). Poster layout: title block left, hex map
right. UTM coords are north-up already, so matplotlib needs no y-flip.

    /home/dylan/src/setti-venv/bin/python notebooks/build_og_card.py
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.colors import Normalize

m = json.load(open("setti_map.json"))
W, H = m["width_m"], m["height_m"]

fig = plt.figure(figsize=(12, 6.3), dpi=100)
fig.patch.set_facecolor("white")

# --- map panel (right) ---
ax = fig.add_axes([0.42, 0.05, 0.56, 0.90])
ax.set_aspect("equal"); ax.axis("off")
ax.set_xlim(0, W); ax.set_ylim(0, H)

# waterlines
segs = [np.array(line) for f in m["waterlines"]["features"]
        for line in f["geometry"]["coordinates"]]
ax.add_collection(LineCollection(segs, colors="#33506e", linewidths=0.5, alpha=0.5, zorder=1))

# island
for f in m["island"]["features"]:
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        ext = np.array(poly[0])
        ax.fill(ext[:, 0], ext[:, 1], facecolor="#eaf0e8", edgecolor="#33503f", lw=1.0, zorder=2)

# hex heatmap
verts = [f["geometry"]["coordinates"][0] for f in m["hexes"]["features"]]
counts = np.array([f["properties"]["count"] for f in m["hexes"]["features"]])
ax.add_collection(PolyCollection(
    verts, array=counts, cmap="Blues", norm=Normalize(0, m["max_count"]),
    edgecolors="white", linewidths=0.12, zorder=3))

# --- title block (left) ---
fig.text(0.045, 0.74, "Project Setti", fontsize=48, fontweight="bold",
         family="serif", color="#0b2e22")
fig.text(0.047, 0.635, "sperm-whale sightings  ·  Dominica", fontsize=21,
         family="serif", color="#33506e")
fig.text(0.047, 0.565, "2021 – 2026", fontsize=21, family="serif", color="#33506e")
fig.text(0.047, 0.40,
         "Over 2,000 surface sightings off the\nleeward coast, logged by my dad and\n"
         "binned into 1 km “waterline” hexes.",
         fontsize=15.5, family="sans-serif", color="#42525c", va="top", linespacing=1.5)

# small colorbar under the blurb
cax = fig.add_axes([0.047, 0.20, 0.20, 0.022])
cb = fig.colorbar(plt.cm.ScalarMappable(norm=Normalize(0, m["max_count"]), cmap="Blues"),
                  cax=cax, orientation="horizontal")
cb.set_ticks([0, m["max_count"]]); cb.ax.set_xticklabels(["0", str(m["max_count"])])
cb.ax.tick_params(labelsize=10, colors="#42525c", width=0.5, length=2)
cb.outline.set_edgecolor("#33506e"); cb.outline.set_linewidth(0.5)
cb.set_label("sightings / cell", fontsize=11, color="#42525c", labelpad=2)

fig.savefig("../docs/assets/setti_og.png", dpi=100, facecolor="white")
print("wrote docs/assets/setti_og.png  (1200x630)")
