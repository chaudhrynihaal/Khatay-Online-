/*
 * service-worker.js
 * ------------------
 * Makes Khatay installable and lets the app shell (nav, CSS, JS) plus
 * whatever pages a device has already visited keep working without a
 * connection.
 *
 * Deliberately does NOT queue or replay offline writes. This app records
 * money - sales, purchases, payments, stock. A queued POST that gets
 * replayed later can double-book a sale or push stock qty out of sync
 * with what actually happened at the counter, and reconciling that after
 * the fact is worse than just telling the cashier up front "you're
 * offline, this won't save." So every non-GET request is left completely
 * untouched here (no event.respondWith at all) and goes straight to the
 * network exactly as if this service worker didn't exist; offline, it
 * simply fails the way it always would have.
 */

const CACHE_VERSION = "khatay-shell-v1";

const PRECACHE_URLS = [
  "/theme.css",
  "/static/js/searchable-select.js",
  "/static/js/barcode-scanner.js",
  "/static/offline.html",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE_URLS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;

  // Only ever intercept safe, idempotent reads. Anything that writes
  // data (POST/PUT/PATCH/DELETE - every sale, purchase, payment, edit,
  // and delete in this app) is left alone entirely, see file header.
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Full-page navigations: try the network first (so a logged-in user
  // always sees live data when online), fall back to a cached copy of
  // that same page, then to the generic offline page as a last resort.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
          return res;
        })
        .catch(() =>
          caches.match(req).then((cached) => cached || caches.match("/static/offline.html"))
        )
    );
    return;
  }

  // Static assets and the theme stylesheet: serve from cache instantly
  // if we have it, but always refresh the cache in the background so a
  // future offline visit has the latest version.
  event.respondWith(
    caches.match(req).then((cached) => {
      const network = fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
          return res;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
