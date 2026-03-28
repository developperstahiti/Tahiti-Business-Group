// Service Worker — Tahiti Business Group PWA
const CACHE_NAME = 'tbg-v1';
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/manifest.json',
    '/offline.html',
];

// Install — cache les assets statiques
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

// Fetch — cache-first pour les assets, network-first pour les pages
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Assets statiques : cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(cached =>
                cached || fetch(event.request).then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
            )
        );
        return;
    }

    // Pages HTML : network-first, fallback offline
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match('/offline.html'))
        );
        return;
    }

    // Autres requetes : network only
    event.respondWith(fetch(event.request));
});
