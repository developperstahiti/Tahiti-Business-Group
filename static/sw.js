// Service Worker — Tahiti Business Group PWA
const CACHE_NAME = 'tbg-v1';
const PRECACHE = [
  '/',
  '/static/css/style.css',
  '/static/img/favicon-192.png',
  '/static/img/favicon-512.png',
];

// Install : pré-cache les ressources essentielles
self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

// Activate : nettoie les anciens caches
self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch : network-first, fallback sur le cache
self.addEventListener('fetch', (e) => {
  // Ne pas cacher les requêtes POST ou les API
  if (e.request.method !== 'GET') return;

  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        // Mettre en cache les réponses réussies
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
