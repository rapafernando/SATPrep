/* ScorePath: service worker, "add to home screen" prompt, and math rendering. */
(function () {
  "use strict";

  // 1. Register the service worker (lets phones treat the site as an installable app).
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  // 2. Math: render $...$ with KaTeX when it is on the page.
  window.addEventListener("load", function () {
    if (typeof window.renderMathInElement !== "function") return;
    document.querySelectorAll(".math").forEach(function (el) {
      window.renderMathInElement(el, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,
      });
    });
  });

  // 3. Install prompt.
  var banner = document.getElementById("install-banner");
  var hint = document.getElementById("install-hint");
  var installBtn = document.getElementById("install-btn");
  var dismissBtn = document.getElementById("install-dismiss");
  var pageBtn = document.getElementById("install-page-btn");
  var deferred = null;
  var KEY = "install-dismissed-at";
  var TWO_WEEKS = 14 * 24 * 3600 * 1000;

  function isStandalone() {
    return (
      (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
      window.navigator.standalone === true
    );
  }
  function isIos() {
    return (
      /iphone|ipad|ipod/i.test(navigator.userAgent) ||
      (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1)
    );
  }
  function recentlyDismissed() {
    try {
      var at = Number(localStorage.getItem(KEY) || 0);
      return at && Date.now() - at < TWO_WEEKS;
    } catch (e) {
      return false;
    }
  }
  function show() {
    if (banner && !isStandalone() && !recentlyDismissed()) banner.hidden = false;
  }
  function runInstall() {
    if (!deferred) return;
    deferred.prompt();
    deferred.userChoice.finally(function () {
      deferred = null;
      if (banner) banner.hidden = true;
      if (pageBtn) pageBtn.hidden = true;
    });
  }

  window.addEventListener("beforeinstallprompt", function (event) {
    event.preventDefault();
    deferred = event;
    if (installBtn) installBtn.hidden = false;
    if (pageBtn) pageBtn.hidden = false;
    if (hint) hint.textContent = "Open it like an app, full screen, with its own icon.";
    show();
  });
  window.addEventListener("appinstalled", function () {
    if (banner) banner.hidden = true;
  });

  if (isIos() && !isStandalone() && hint) {
    hint.textContent = "Tap the Share button, then “Add to Home Screen”.";
    show();
  }
  if (installBtn) installBtn.addEventListener("click", runInstall);
  if (pageBtn) pageBtn.addEventListener("click", runInstall);
  if (dismissBtn) {
    dismissBtn.addEventListener("click", function () {
      try {
        localStorage.setItem(KEY, String(Date.now()));
      } catch (e) {}
      if (banner) banner.hidden = true;
    });
  }
})();
