// Service Worker — Tahiti Business Group PWA
const CACHE_NAME = 'tbg-v2';
const STATIC_ASSETS = [
    '/offline.html',
];

// Install — cache la page offline uniquement
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

// Activate — supprime les anciens caches
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// Fetch — intervention minimale
self.addEventListener('fetch', event => {
    // Ne PAS intercepter les requêtes cross-origin (images S3, API externes, etc.)
    if (new URL(event.request.url).origin !== self.location.origin) return;

    // Pages HTML : network-first, fallback offline
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match('/offline.html'))
        );
        return;
    }

    // Tout le reste (static, media, API) : laisser le navigateur gérer normalement
});
