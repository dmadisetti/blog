---
date: 2026-07-21
tags:
  - mathematics
  - data-viz
  - interactive
  - from-the-archive
categories:
  - Mathematics
  - Data
  - Interactive
authors:
  - dylan
slug: friendship-paradox
---

# Friendship Paradox: My Friends Have More Friends Than I Do

!!! note "From the archive (2016) — rebuilding the interactives"
    Originally posted on my old Ghost blog. Re-publishing as part of the relaunch.
    The original interactive D3 widgets are being rebuilt as live **marimo** cells
    — placeholders are marked 🔁 below.

Your friends probably have more friends than you do. It's the mind blowing premise you can read about [here](http://opinionator.blogs.nytimes.com/2012/09/17/friends-you-can-count-on/), [here](http://www.macroeconomics.tu-berlin.de/fileadmin/fg124/networks/Lectures/Summer2012/Material/American_Journal_of_Sociology_1991_Feld.pdf) and [here](https://en.wikipedia.org/wiki/Friendship_paradox). In addition, here's a little youtube video explaining the gist of how this is possible.

# An error occurred.

Unable to execute JavaScript.

The paradox might apply to most people, but how can I tell if it applies to someone in particular? Does it apply to me? With the miracle of the internet- it's actually pretty easy to tell. I reckon the [Facebook](htttps://www.facebook.com) friends page is a pretty good sense of how many 'friends I have'. So with a [little scipting](https://gist.github.com/dmadisetti/cfaccde928da6b6e1b4c69944dc45985) and a little data massaging in [python](https://github.com/dmadisetti/blogdata/blob/master/friends/Friends.ipynb), I was able to piece together that most of my friends do in fact have more friends than I do. But it's close; only around 51% of my friends have more friends than I do. Here's the plot showing where I fall on the friend count distribution of my friends:

> 🔁 *[figure / interactive — rebuild as a marimo cell]*

and graphically, here's how many friends my friends have by size of the nodes. I'm the little red node in the middle:

> 🔁 *[figure / interactive — rebuild as a marimo cell]*

I ran the script for mom and she ended up being 68th percentile for friend count in her friend group. It's a weird feeling being less cool than your mom. Let me know what you think in the comments below.
