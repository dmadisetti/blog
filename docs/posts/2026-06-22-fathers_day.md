---
date: 2026-06-22
tags:
  - data-viz
  - whales
  - altair
  - Dominica
  - Chatou Marine
categories:
  - reflection
authors:
  - dylan
slug: project-setti
description: "Over 2,000 sperm-whale sightings off of Dominica (2021–2026) from my dad's logbook, made into an interactive map and a Father's Day Retro."
image: assets/setti_og.png
license: CC-BY-ND-4.0
marimo_mode: static
---

# Project Setti

I am not a great gift giver.

However, I do believe that a good gift is one that is personal both to the giver and the receiver.
Izzy (pops) is incredibly passionate about his work with [sperm whales](http://www.thespermwhaleproject.org/) and it's something he's been able to share with me.
We even went briefly viral (viral before we could make money off it as Izzy likes to say), in 2011.

<figure markdown="span">
!["He's ready for his close-up" is a pretty cheesy tagline](https://nypost.com/wp-content/uploads/sites/2/2013/08/sperm_whale-300x300.jpg?quality=75&strip=all)
<figcaption markdown="span">
Picture of myself taken by Izzy ([@madisetti.a](https://www.instagram.com/madisetti.a/)) as seen on [The New York Post in 2011](https://nypost.com/2011/04/08/hes-ready-for-his-close-up/).
If I recall correctly there was also a Skype interview with some news outlet.
</figcaption>
</figure>

Dominica has the world's first ["sperm whale reserve"](https://news.nationalgeographic.org/dominica-establishes-worlds-first-sperm-whale-reserve-a-boost-for-climate-biodiversity-and-the-local-economy/), and a large resident population.
Last year I asked dad for his whale sighting data, figuring I could do some basic analysis and visualization, as something personalized and something I'm uniquely equipped to do.

In restarting this blog, I wanted to start off with something I felt was worth sharing and highlight a bit of my world (in this case our shared worlds).
I've named this post `Project Setti`.
[Project CETI](https://www.projectceti.org/) is an organization driven to explore <u>C</u>etacean intelligence, which is in turn a play of [Project SETI](https://www.seti.org/) which is an organization driven to explore <u>ET</u> intelligence.
Project Setti is hopefully a demonstration of [Madi<u>setti</u>][That's us if it wasn't evident] intelligence, but the results are not conclusive.

Izzy has agreed to allow this surface-level data to be available, but outside of this visualization, we ask that you reach out to us before usage.
Specific to this blog post, I've rendered a little interactive map of the data, which you can explore below.

```python {.marimo}
import json
import altair as alt

_m = json.load(open("notebooks/setti_map.json"))
_aspect = _m["height_m"] / _m["width_m"]

# Year picker (pure Vega binding — interactive without a Python kernel).
_yr = alt.param(
    name="yr",
    value="all",
    bind=alt.binding_select(options=["all"] + [str(y) for y in _m["years"]], name="year  "),
)

_island = alt.Chart(alt.Data(values=_m["island"]["features"])).mark_geoshape(
    fill="#eaf0e8", stroke="#33503f", strokeWidth=1.0
)
_waves = alt.Chart(alt.Data(values=_m["waterlines"]["features"])).mark_geoshape(
    filled=False, stroke="#33506e", strokeWidth=0.6, opacity=0.55
)
_labels = (
    alt.Chart(alt.Data(values=_m["labels"]))
    .mark_text(color="#33506e", fontSize=8.5, baseline="middle")
    .encode(longitude="x:Q", latitude="y:Q", text="text:N")
)
_hex = (
    alt.Chart(alt.Data(values=_m["hexes"]["features"]))
    .transform_calculate(n="yr === 'all' ? datum.properties.count : datum.properties['y' + yr]")
    .transform_filter("datum.n > 0")
    .mark_geoshape(stroke="white", strokeWidth=0.15)
    .encode(
        color=alt.Color(
            "n:Q",
            scale=alt.Scale(scheme="blues", domain=[0, _m["max_count"]]),
            legend=alt.Legend(
                title="sightings / cell",
                direction="horizontal",
                orient="top-right",
                gradientLength=120,
                gradientThickness=9,
                titleFontSize=10,
                labelFontSize=9,
            ),
        ),
        tooltip=[alt.Tooltip("n:Q", title="sightings")],
    )
)

# Title cartouche (white panel + wave-line ripples + serif text), baked by
# notebooks/build_title.py and overlaid at a fixed pixel position in the map's
# lower-left. The rippled-text look is glyph-path geometry Vega can't draw, so
# it's a small transparent PNG floated over the open water.
_TITLE_ASPECT = 2.476
_titleimg = (
    alt.Chart(alt.Data(values=[{}]))
    .mark_image(url="../assets/setti_title.png", width=250,
                height=round(250 / _TITLE_ASPECT), align="left", baseline="bottom")
    .encode(x=alt.value(12), y=alt.value(round(560 * _aspect) - 12))
)

_chart = (
    alt.layer(_island, _waves, _hex, _labels, _titleimg)
    .add_params(_yr)
    .project(type="identity", reflectY=True)
    .properties(width=560, height=round(560 * _aspect))
    .configure(
        background="white",
        view=alt.ViewConfig(stroke=None),
        legend=alt.LegendConfig(titleColor="#1f3a52", labelColor="#3a4a55"),
    )
)
_chart
```

I put the exploratory notebook on [`molab`](https://molab.marimo.io/notebooks/nb_e1CgUrJdGLJUJWwQnpjQpp) if you would like to jump deeper into the specific data and visualization choices I made to render this map.
I was heavily inspired by a [waterlines visualization post on Observable](https://observablehq.com/@oliviafvane/ii-drawing-waterlines-on-maps?collection=@oliviafvane/watermarks) which not only looks amazing, but seemed like a good way to mark distance from the shore.

There's a large corpus of research and toolkits I'd love to run his data on in my spare time.
For instance, his recorded whale songs.
We're still working on our workflows and ideas we can glean from the data itself, leave a comment if you have any ideas or would like to collaborate on this project.

If you enjoyed this post, consider subscribing to the substack (below), and following [@madisetti.a](https://www.instagram.com/madisetti.a/) on instagram (Happy Father's Day!)
