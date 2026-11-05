{% load static %}/* {{ APP_NAME }} service worker. Caches only public files (styles, scripts, icons, offline page).
   Signed-in pages and your practice data are never stored on the phone by this file. */
const CACHE = "{{ APP_NAME|slugify }}-v{{ APP_VERSION }}";
const PRECACHE = [
  "{% url 'offline' %}",
  "{% static 'css/tokens.css' %}",
  "{% static 'css/fonts.css' %}",
  "{% static 'css/app.css' %}",
  "{% static 'js/app.js' %}",
  "{% static 'icons/icon-192.png' %}",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Pages: always go to the network; show the offline page if the phone has no connection.
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("{% url 'offline' %}")));
    return;
  }

  // Static files: use the saved copy if there is one, otherwise fetch and save it.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then(
        (hit) =>
          hit ||
          fetch(request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(CACHE).then((cache) => cache.put(request, copy));
            }
            return response;
          })
      )
    );
  }
});
