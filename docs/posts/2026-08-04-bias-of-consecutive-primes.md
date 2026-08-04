---
date: 2026-08-04
tags:
  - mathematics
  - interactive
  - from-the-archive
categories:
  - Mathematics
  - Visualization
  - Interactive
authors:
  - dylan
slug: bias-of-consecutive-primes
---

# Visualizing the Bias of Consecutive Primes

!!! note "From the archive (2016) — rebuilding the interactives"
    Originally posted on my old Ghost blog. Re-publishing as part of the relaunch.
    The original interactive D3 widgets are being rebuilt as live **marimo** cells
    — placeholders are marked 🔁 below.

So a fairly cool paper is [currently in preprint](http://arxiv.org/pdf/1603.03720v2.pdf) by some Stanford Mathematicians Kannan Soundararajan and Robert Lemke Oliver- regarding the unexpected distribution of consecutive primes.

**Spoiler alert:** *the last digits of consecutive prime pairings aren't randomly distributed*.

Wait what. What does that even mean? It means if (for example in base 10) I have a prime \$p_n\$ that ends in the digit 1, there's a high chance the next prime \$p\_{n+1}\$ will end in 9. Isn't that weird? It's pretty weird. We expect most things dealing with primes to be inherently random.

The paper puts together a heuristic explaining this distribution, but I'm not exceptionally interested in that- I'm interested in visualizing the bias. If you would like to read more about the discovery and back story, [you can do so here](https://www.quantamagazine.org/20160313-mathematicians-discover-prime-conspiracy/). By setting the last digit of \$p_n\$ against the last digit of \$p\_{n+1}\$ we can plot this phenomenon. By using a darker color for the frequency of that grid position when examining primes, we get a nice visualization. In addition, we can change the system of counting or 'base' to produce even nicer patterns. So without further ado here's an interactive of consecutive prime distribution:

Neat huh? Really nifty patterns. I ran the Sieve of Eratosthenes over integers up to 100,000,000 yielding 5,761,455 primes. [Here's that terrible, terrible code](https://gist.github.com/dmadisetti/2b6d62a9bab41ce529d1). I decided to take this further and checkout the distribution of 3 consecutive primes. Any longer sequences become dramatically more difficult to visualize. Here is said interactive distribution (click and drag and whatnot):

On mobile or have a limited screen? Checkout the raw visualization for these guys: [here for dim=2](https://blog.postmodern.technology/static/ragged/2d.html) and [here for dim=3](https://blog.postmodern.technology/static/ragged/3d.html)

I'd be interested to explore these distributions over non-traditional bases. For instance, consider a system \$n\_{base 10} = d_4\cdot 21 + d_3\cdot 10 + d_2\cdot 3 + d_1\cdot 2 + d_0\$ for each digit d of a number \$n\_{base\\ strange}\$, or something crazy like that. I'll update if I have time to explore this.
