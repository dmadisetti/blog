/* Per-post behaviour for "Please do not touch" — loaded only on this page via
   the post's front-matter `extra_javascript` (see overrides/main.html). The
   .modal is always opaque; clicking (or Enter/Space) only wobbles it — the
   hidden .dont-touch text is never revealed in-page. */
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
