// Mirror Material's color scheme onto the attribute the marimo islands runtime
// reads. Material toggles `body[data-md-color-scheme="slate|default"]`; the
// islands `useTheme` looks at `body.dataset.theme === "dark"`. Without this
// bridge, hydrated islands (editors, UI widgets) ignore the light/dark toggle.
(function () {
  function sync() {
    var scheme = document.body.getAttribute("data-md-color-scheme");
    document.body.dataset.theme = scheme === "slate" ? "dark" : "light";
  }

  sync();

  // Material swaps the scheme attribute in place on palette toggle (and keeps
  // the same <body> across instant navigation), so observe it.
  new MutationObserver(sync).observe(document.body, {
    attributes: true,
    attributeFilter: ["data-md-color-scheme"],
  });
})();
