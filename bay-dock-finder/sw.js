/* Dock Finder service worker.
   Goal: the app shell opens instantly and still opens with no signal.
   Live data is never cached — a stale dock count is worse than no answer. */

var CACHE = 'dockfinder-v2';
var SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
];

/* Anything that answers "what is true right now" must always hit the network. */
var LIVE = /gbfs\.lyft\.com|routing\.openstreetmap\.de|photon\.komoot\.io|nominatim\.openstreetmap\.org/;

self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(function (c) {
      // addAll is all-or-nothing; cache what we can and don't fail the install.
      return Promise.all(SHELL.map(function (u) {
        return c.add(new Request(u, { cache: 'reload' })).catch(function () {});
      }));
    })
  );
});

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
                             .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  if (LIVE.test(req.url)) return;                 // live data: straight to network
  if (req.url.indexOf('basemaps.cartocdn.com') > -1) return;  // tiles: let HTTP cache handle it

  // Shell: network first so a deploy lands immediately, cache as the fallback.
  e.respondWith(
    fetch(req).then(function (res) {
      if (res && res.ok){
        var copy = res.clone();
        caches.open(CACHE).then(function (c) { c.put(req, copy); });
      }
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        return hit || caches.match('./index.html');
      });
    })
  );
});
