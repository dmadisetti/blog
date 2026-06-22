"""Rasterize the 'hello' post's posting-history heatmap into a 1200x630 OG card.
Mirrors the altair cell in docs/posts/2026-06-16-hello.md, but recolored for a
white card (the in-post version is tuned for the dark theme) and with a hook
title. Run from the blog root (it live-counts docs/posts for the readme.dm row):

    .venv/bin/python notebooks/build_hello_og.py
"""
import glob, pathlib, re
import altair as alt
import pandas as pd
from PIL import Image

blog = {
    "2013-07": 4, "2013-09": 3, "2013-10": 1, "2013-11": 3,
    "2015-03": 1, "2015-06": 3, "2015-07": 1,
    "2016-03": 1, "2016-04": 1, "2016-05": 1, "2016-12": 1,
    "2019-03": 12, "2019-04": 3, "2019-06": 2, "2019-07": 3, "2019-11": 2,
    "2020-01": 1, "2021-03": 1, "2022-01": 1, "2022-03": 1,
}
observable = {
    "2021-03": 3, "2021-09": 1, "2022-02": 2, "2022-11": 2, "2022-12": 1,
    "2023-02": 2,
}

def readme_dm_by_month():
    counts: dict = {}
    for p in glob.glob("docs/posts/*.md"):
        m = re.search(r"^date:\s*(\d{4}-\d{2})", pathlib.Path(p).read_text(encoding="utf-8"), re.M)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts or {"2026-06": 1}

monthly: dict = {}
for source in (blog, observable, readme_dm_by_month()):
    for ym, n in source.items():
        monthly[ym] = monthly.get(ym, 0) + n
LAUNCH = (2026, 2)

quarters = ["Q1", "Q2", "Q3", "Q4"]
agg: dict = {}
for ym, n in monthly.items():
    y, mo = (int(x) for x in ym.split("-"))
    agg[(y, (mo - 1) // 3 + 1)] = agg.get((y, (mo - 1) // 3 + 1), 0) + n
df = pd.DataFrame([
    {"year": yr, "quarter": quarters[q - 1], "posts": agg.get((yr, q), 0)}
    for yr in range(2013, 2027) for q in range(1, 5)
])

ax_year = alt.X("year:O", title=None,
                axis=alt.Axis(labelAngle=0, ticks=False, domain=False, labelOverlap=False))
ax_q = alt.Y("quarter:O", sort=quarters, title=None, axis=alt.Axis(ticks=False, domain=False))
grid = alt.Chart(df).mark_rect(cornerRadius=2).encode(
    x=ax_year, y=ax_q,
    color=alt.Color("posts:Q", legend=None, scale=alt.Scale(
        type="threshold", domain=[1, 3, 6],
        range=["rgba(127,127,127,0.14)", "#9be9a8", "#40c463", "#216e39"])))
launch = pd.DataFrame([{"year": LAUNCH[0], "quarter": quarters[LAUNCH[1] - 1]}])
ring = alt.Chart(launch).mark_rect(fill=None, stroke="#c47a9c", strokeWidth=2,
                                   cornerRadius=2).encode(x=ax_year, y=ax_q)
tag = alt.Chart(launch).mark_text(text="readme.dm —→", align="right", dx=-10, fontSize=11,
                                  fontStyle="italic", color="#c47a9c").encode(x=ax_year, y=ax_q)

chart = (
    (grid + ring + tag)
    .properties(width=640, height=180, background="white",
        title=alt.TitleParams("Hello again",
            subtitle="personal blog posts from my teens to now  ·  readme.dm",
            anchor="start", fontSize=23, subtitleFontSize=13.5,
            color="#1f3a52", subtitleColor="#5a6b76"))
    .configure_view(strokeWidth=0)
    .configure_axis(labelColor="#5a6b76", labelFontSize=12.5))

chart.save("/tmp/hello_chart.png", scale_factor=3.0)  # vl-convert backend

ch = Image.open("/tmp/hello_chart.png").convert("RGBA")
ch.thumbnail((1080, 540))
canvas = Image.new("RGB", (1200, 630), "white")
canvas.paste(ch, ((1200 - ch.width) // 2, (630 - ch.height) // 2), ch)
canvas.save("docs/assets/hello_og.png")
print(f"wrote docs/assets/hello_og.png  (chart {ch.size} centered on 1200x630)")
