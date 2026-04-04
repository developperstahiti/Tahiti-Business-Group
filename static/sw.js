// Service Worker — Tahiti Business Group PWA
const CACHE_NAME = 'tbg-v3';
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

// Activate — supprime TOUS les anciens caches (y compris tbg-v1, tbg-v2, etc.)
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

// Fetch — intervention minimale, ne jamais mettre en cache CSS/JS/media
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Ne PAS intercepter les requêtes cross-origin (images S3, API externes, etc.)
    if (url.origin !== self.location.origin) return;

    // Ne JAMAIS intercepter les fichiers statiques CSS/JS/fonts/images
    // pour éviter de servir une version périmée depuis le cache
    const staticExts = ['.css', '.js', '.woff', '.woff2', '.ttf', '.otf',
                        '.png', '.jpg', '.jpeg', '.webp', '.svg', '.ico',
                        '.gif', '.avif'];
    if (staticExts.some(ext => url.pathname.endsWith(ext))) return;

    // Ne PAS intercepter les requêtes /static/ (WhiteNoise les gère avec ses propres headers)
    if (url.pathname.startsWith('/static/')) return;

    // Pages HTML : network-first, fallback offline
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match('/offline.html'))
        );
        return;
    }

    // Tout le reste (API, media) : laisser le navigateur gérer normalement
});
