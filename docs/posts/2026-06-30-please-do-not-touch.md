---
# Verbatim author text below (typos preserved per request); editorial notes in HTML comments.
tier: filler
date: 2026-06-30
slug: please-do-not-touch  # matches the readme.dm/please-do-not-touch self-link in the body
tags:
  - reflections
  - essay
status: draft
---

<!--
  Working notes / context gathered while researching this piece:
  - Museum: Bechtler Museum of Modern Art, Charlotte NC.
  - The David McGee show was the current exhibition on view.
  - The piece "that caught my eye" is from "Collection, Reframed: Jiha Moon"
    (Jun 13 - Nov 9, 2026), themes of representations of women / presence & absence.
  - Most likely artist: Hannele Ollakka (Finnish textile artist who works in
    gauzy, transparent fabrics + dyeing/serigraphy => "mixed media on silk gauze").
    High confidence on artist; exact title/date awaiting the museum's reply.
    The blurry label's nationality read as "Finnish" (not "French"); the Korean
    association was the curator-artist Jiha Moon.
-->

# Please do not touch

I was recently in Charlotte and had the pleasure of visiting the Bechtler Modern Art Museum.
I thought the works by David McGee were absolutely spectacular, but as I was leaving the museum a piece caught my eye again.

<style>
/* The curtain: the installation photo "flooded" so only the veil shows, with
   the gallery label + placard sitting on the wall to its left. */
.md-typeset figure.curtain {
  position: relative;
  background: none;
  padding: 0;
  margin: 2.75rem 0;
  text-align: center;
  overflow: visible;
}
.md-typeset figure.curtain > p { margin: 0; }

/* Mask the photo's four edges to nothing so the gallery wall dissolves and only
   the hanging gauze reads. drop-shadow (not box-shadow) follows the masked alpha. */
.md-typeset figure.curtain .curtain__img {
  display: inline-block;
  width: auto;
  max-width: 100%;
  max-height: 34rem;
  border: none;
  border-radius: 2px;
  background: none;
  -webkit-mask-image: radial-gradient(120% 78% at 50% 46%, #000 52%, transparent 90%);
          mask-image: radial-gradient(120% 78% at 50% 46%, #000 52%, transparent 90%);
  filter: drop-shadow(0 16px 34px color-mix(in srgb, var(--md-default-fg-color) 40%, transparent));
  transition: transform 0.25s ease;
  will-change: transform;
}
.md-typeset figure.curtain .curtain__img:hover,
.md-typeset figure.curtain .curtain__img:active {
  animation: curtain-sway 0.9s ease;
}
@keyframes curtain-sway {
  0%, 100% { transform: rotate(0) translateX(0); }
  20% { transform: rotate(-0.7deg) translateX(-3px); }
  45% { transform: rotate(0.6deg) translateX(3px); }
  70% { transform: rotate(-0.35deg) translateX(-1px); }
  88% { transform: rotate(0.2deg) translateX(1px); }
}

/* Gallery label card — on the (now empty) wall to the lower-left, where it hangs
   beside the piece in the photo. */
.md-typeset figure.curtain .curtain__label {
  position: absolute;
  left: 0;
  bottom: 16%;
  width: min(15rem, 42%);
  padding: 0.7rem 0.85rem;
  text-align: left;
  font-size: 0.62rem;
  line-height: 1.55;
  background: var(--md-default-bg-color);
  border: 1px solid var(--md-default-fg-color--lightest);
  color: var(--md-default-fg-color);
}
.md-typeset figure.curtain .curtain__label p { margin: 0; }
.curtain__meta { color: var(--md-default-fg-color--light); font-weight: 400; }

/* The "Please do not touch" placard, just below the label. */
.md-typeset figure.curtain .curtain__sign {
  position: absolute;
  left: 0;
  bottom: 6%;
  width: max-content;
  max-width: 42%;
  margin: 0;
  padding: 0.35rem 0.7rem;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-align: center;
  border: 1px solid var(--md-default-fg-color--lighter);
  background: var(--md-default-bg-color);
}

/* Narrow screens: drop the absolute cards into normal flow below the image. */
@media screen and (max-width: 48rem) {
  .md-typeset figure.curtain .curtain__label,
  .md-typeset figure.curtain .curtain__sign {
    position: static;
    width: auto;
    max-width: 24rem;
    margin: 0.8rem auto 0;
  }
}

/* The paywall spoof: real text in the DOM, blurred + capped by an opaque overlay.
   Extractable (dev-tools / a chatbot) but never readable in-page. */
.md-typeset .paywall {
  position: relative;
  margin: 1.75rem 0;
  border: 1px solid var(--md-default-fg-color--lightest);
  border-radius: 4px;
  overflow: hidden;
}
.md-typeset .paywall .dont-touch {
  padding: 1.25rem 1.4rem;
  filter: blur(5px);
  opacity: 0.85;
  user-select: none;
  -webkit-user-select: none;
  -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 30%, transparent 92%);
          mask-image: linear-gradient(180deg, #000 0%, #000 30%, transparent 92%);
}
.md-typeset .paywall .dont-touch p:last-child { margin-bottom: 0; }

/* Overlay: a teaser bleeds through the top, fully opaque over the lower half
   where the CTA sits. Always covering. */
.md-typeset .paywall .modal {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 1.4rem;
  background: linear-gradient(
    180deg,
    transparent 0%,
    color-mix(in srgb, var(--md-default-bg-color) 65%, transparent) 28%,
    var(--md-default-bg-color) 58%
  );
  cursor: not-allowed;
  font-weight: 700;
  font-size: 0.8rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--md-default-fg-color--light);
  user-select: none;
  -webkit-user-select: none;
}
.md-typeset .paywall .modal:focus-visible {
  outline: 2px solid var(--md-accent-fg-color);
  outline-offset: -3px;
}

/* Click/tap "activates" a denied wobble. It never reveals anything. */
.md-typeset .paywall.denied .modal { animation: deny-shake 0.5s ease; }
@keyframes deny-shake {
  0%, 100% { transform: translateX(0); }
  15% { transform: translateX(-6px); }
  30% { transform: translateX(6px); }
  45% { transform: translateX(-4px); }
  60% { transform: translateX(4px); }
  78% { transform: translateX(-2px); }
}

@media (prefers-reduced-motion: reduce) {
  .md-typeset figure.curtain .curtain__img:hover,
  .md-typeset figure.curtain .curtain__img:active,
  .md-typeset .paywall.denied .modal { animation: none; }
  .md-typeset figure.curtain .curtain__img { transition: none; }
}
</style>

<figure class="curtain" markdown="1">

![A hanging veil of silk gauze; the worn outline of a figure (or two?) dissolving behind it](../assets/curtain.jpg){ .curtain__img }

<div class="curtain__label" markdown="1">
**Hannele Ollakka** <span class="curtain__meta">(Finnish, b. 19—)</span><br>
*Untitled*, 20—<br>
Mixed media on silk gauze<br>
Bechtler Museum of Modern Art
<!-- Label transcribed from the installation photo (assets/curtain.jpg). Artist,
     medium and institution are legible; the title, birth year and date range are
     too blurred on the photo to read — fill from the museum's reply. The wall
     text's descriptive paragraph belongs here too (the author wants the real
     description in-text, for crawlers and readers). Gist, pending the reply:
     Ollakka's ethereal paintings on silk gauze plumb memory and the boundary
     between presence and absence; the figures of a child and a woman emerge
     through translucent fabric — a haunting physical presence that resists fixed
     form, a gesture of ambiguity about the fragile nature of memory. -->
</div>

<p class="curtain__sign">Please do not touch</p>

</figure>


From the distance of this piece there's a vague outline of a portrait a human, or is it two?
There's something definitely beyond the veil, but the image is too muddy to discern.
It's provocative.

My immediate intrusive thought was "to pull back the curtain".
Living in a connected world, most immediately pressing curiosities can be rectified with a Google or chatbot question.
The pervasive thought was made even stronger by the fact I had immediate agency over the situation.
Obviously, I did not touch the curtain (tragedy of the commons and the friendly **Please do not touch sign**), but I did nearly flatten myself against the wall trying to look at its secrets.
I didn't see any.[^menace]

As I walked away wistful from my museum visit, I came up with a parallel for that feeling of an information tease.
While information is normally widely disseminated on the internet for free (both real and false), a monthly subscription of x.99$/mo
will grant you access to certain articles and news-sites[^onion]- a tiny preview visible for a split second before some obnoxious modal covers the site screaming for payment.

I was always confused by these sites.
Most of the time, _the content was already on the page_.
It just takes a few clicks in most browser developer tools to remove the modal and unstick the page manually.
Even for the less tech savvy- just enabling "reader" mode on Firefox would normally expose the site.
I wondered if it was news outlets playing a game of chicken with search engines like Google.
Give access of the content easily and readily away for search engines to improve your rankings, but superficially restrict the content to users.
And the answer is yes! Google [sanctions the arrangement](https://developers.google.com/search/docs/appearance/flexible-sampling)- feed the crawler the whole article, wall it off from readers- so long as you tag it so it doesn't count as [cloaking](https://developers.google.com/search/docs/essentials/spam-policies#cloaking).
Probably led to the rampant theft of IP for training LLMs too!

Inspired by Ollakka, but much more frivolous- here's a curtain for you.

<!-- Add a spoof "content hidden modal" with the following content -->
<!-- Like paywalls, let's give a little blurb that's a translucent remainder that blocks the view -->
<div class="paywall" markdown="1">

<div class="dont-touch" markdown="1">
When I was a teenager I drilled a hole in a marbled wide ruled composition notebook and put a padlock on it.
It may not be immediately obvious, but this is an incredibly silly thing to do.
Think back to your note-taking days. The classic composition notebooks are laughably ply-able; reams of paper held together with a thin string threading the spine and "takeout" quality cardboard for covers.
My main intent (being a teenager), was that drilling holes into things was cool.[^drill]
My secondary intent was a _signalling_ of privacy.
Mom/ dad/ whoever, you may be able to read the contents of my journal by just slightly bending the pages open- but the pad lock on front should make it obvious this is not for you.
I'm not a great journal-er[], I am not certain I even wrote much, but I absolutely thought it was cool.
</div>

<!-- Always opaque; only "activates" (a denied wobble) on click — see the inline <script> at the foot of this post -->
<div class="modal" role="button" tabindex="0">Please do not touch</div>

</div>

Open up your browser developer tools, or paste this link ([`https://readme.dm/please-do-not-touch`](https://readme.dm/please-do-not-touch)) to your favourite chat bot, and they can do the extraction for you- but _Please do not touch_.

[^menace]: One of the fondest first dates I ever went on was at a modern art museum. My date at the time wanted to touch everything, they were likely just messing with me, but I was appalled. Part of that might have been trauma from accidentally setting off proximity sensors in the Hermitage. Now I sort of get it? At another museum I did sit on a once display piece thinking it was just fun furniture before being promptly corrected by staff. I promise I'm not normally a menace.

[^onion]: modest confession, the onion briefly trialed being subscription only in 2016- at the time it was one of my daily visited sites and I angrily wrote to them. Everyone has to eat- I guess I was just mad that the Baja Blast commercials they were running at the time wasn't enough to cover the bills

[^drill]: I used to wear my extracted wisdom teeth on a leather necklace, with holes made by this same drill. I also drilled some holes into dead hard-drives to build my own Tesla turbine. There's that adage about hammers and nails, but a drill doesn't force a nail analog- you can put holes in most things.

<!-- Inlined so the behaviour ships with THIS post only, not site-wide. The
     .modal is always opaque; clicking (or Enter/Space) only wobbles it — the
     hidden .dont-touch text is never revealed in-page. -->
<script>
(function () {
  function wire() {
    document.querySelectorAll(".paywall .modal").forEach(function (modal) {
      if (modal.dataset.denyWired) return;
      modal.dataset.denyWired = "1";
      var paywall = modal.closest(".paywall");
      if (!paywall) return;
      function deny() {
        paywall.classList.remove("denied");
        void paywall.offsetWidth; // reflow so the animation re-fires
        paywall.classList.add("denied");
      }
      modal.addEventListener("click", deny);
      modal.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); deny(); }
      });
      paywall.addEventListener("animationend", function () {
        paywall.classList.remove("denied");
      });
    });
  }
  wire();
  // Re-bind on Material instant navigation, subscribing only once.
  if (typeof document$ !== "undefined" && !window.__pdntWired) {
    window.__pdntWired = true;
    document$.subscribe(wire);
  }
})();
</script>
