// Drive the footer statusline's position readout: `15%:16/103 ☰ ℅:1`.
//
// Two sources, in priority order:
//   * the vim cursor — VimNavigation dispatches `vim:cursor` with a fraction
//     through the buffer plus a column; we map the fraction onto the source
//     file's line count (rendered into `data-vim-lines` by hooks/statusline.py),
//     so the denominator is the real file, not the browser's line wrapping.
//   * scroll position — until the reader touches a key there is no cursor, so
//     the readout follows how far down the page they've read. This is also the
//     only source on phones, where vim navigation never initializes.
//
// The first real cursor move also sets `body.vim-active`, which is what reveals
// the landing page's subtitle (site.css).
(function () {
  var el = null;
  var lines = 1;
  var engaged = false;

  function render(progress, col) {
    if (!el) return;
    var p = Math.max(0, Math.min(1, progress || 0));
    var line = Math.min(lines, 1 + Math.round(p * (lines - 1)));
    el.textContent =
      Math.round(p * 100) + "%:" + line + "/" + lines + " ☰ ℅:" + (col || 1);
  }

  function scrollProgress() {
    var doc = document.documentElement;
    var span = doc.scrollHeight - window.innerHeight;
    return span > 0 ? window.scrollY / span : 0;
  }

  function onScroll() {
    if (engaged) return; // the cursor owns the readout once it has moved
    render(scrollProgress(), 1);
  }

  window.addEventListener("vim:cursor", function (e) {
    var d = e.detail || {};
    if (!d.engaged) return; // mount-time position: leave scroll in charge
    if (!engaged) {
      engaged = true;
      document.body.classList.add("vim-active");
    }
    render(d.progress, d.col);
  });

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll, { passive: true });

  function attach() {
    el = document.querySelector("[data-vim-pos]");
    lines = Math.max(1, parseInt((el && el.dataset.vimLines) || "1", 10));
    // Material's instant navigation swaps the footer with the rest of the
    // container, so every page starts over: new buffer, no cursor in it yet.
    engaged = false;
    onScroll();
  }

  if (typeof document$ !== "undefined") {
    document$.subscribe(attach);
  } else {
    document.addEventListener("DOMContentLoaded", attach);
    attach();
  }
})();
