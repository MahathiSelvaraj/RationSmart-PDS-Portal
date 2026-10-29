/**
 * RationSmart - Progressive Web App Service Worker (Native / Lightweight)
 * Scope: /
 * Cache Name: rationsmart-pwa-v1
 * Features: Static asset pre-caching, navigation offline fallback, stale-while-revalidate for assets,
 *           and safe bypass of sensitive/authenticated non-GET actions.
 */

const CACHE_NAME = 'rationsmart-pwa-v1';

// Essential App Shell & Static Resources to Pre-cache
const PRECACHE_ASSETS = [
    '/',
    '/static/manifest.json',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/pwa.js',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js'
];

// Install Event: Pre-cache static assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            // Use addAll with resilient per-item catch to prevent one failed CDN font from breaking install
            return Promise.all(
                PRECACHE_ASSETS.map((url) => {
                    return cache.add(url).catch((err) => {
                        console.warn('[SW] Pre-cache item failed (non-fatal):', url, err);
                    });
                })
            );
        }).then(() => {
            return self.skipWaiting();
        })
    );
});

// Activate Event: Clear obsolete caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((name) => {
                    if (name !== CACHE_NAME) {
                        return caches.delete(name);
                    }
                })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch Event: Intelligent routing & caching strategy
self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // 1. Never intercept or cache non-GET requests (POST, PUT, DELETE)
    // All offline POST data is handled by client-side IndexedDB in pwa.js
    if (request.method !== 'GET') {
        return;
    }

    // 2. Never cache authentication routes, secrets, or admin panels
    if (
        url.pathname.startsWith('/login') ||
        url.pathname.startsWith('/logout') ||
        url.pathname.startsWith('/admin') ||
        url.pathname.includes('password')
    ) {
        return;
    }

    // 3. Navigation requests (HTML Pages): Network-First with Cache Fallback
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then((networkResponse) => {
                    // Cache successful navigation responses for authorized dealer routes
                    if (networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return networkResponse;
                })
                .catch(async () => {
                    // When offline, attempt exact URL match from cache
                    const cachedResponse = await caches.match(request);
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    // If dealer POS or offline-sales requested, fallback to cached dealer shell
                    if (url.pathname.includes('dealer') || url.pathname.includes('offline-sales')) {
                        const posCached = await caches.match('/dealer/pos');
                        if (posCached) return posCached;
                        const offlineSalesCached = await caches.match('/offline-sales');
                        if (offlineSalesCached) return offlineSalesCached;
                    }
                    // Fallback to home/root shell
                    return caches.match('/');
                })
        );
        return;
    }

    // 4. Static Assets (CSS, JS, Images, Fonts): Cache-First with Stale-While-Revalidate
    if (
        url.pathname.startsWith('/static/') ||
        url.hostname.includes('cdn.jsdelivr.net') ||
        url.pathname.endsWith('.css') ||
        url.pathname.endsWith('.js') ||
        url.pathname.endsWith('.png') ||
        url.pathname.endsWith('.svg') ||
        url.pathname.endsWith('.woff2')
    ) {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                const fetchPromise = fetch(request).then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseClone = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseClone);
                        });
                    }
                    return networkResponse;
                }).catch(() => {
                    // Offline and not in cache: let cachedResponse handle it
                });

                return cachedResponse || fetchPromise;
            })
        );
        return;
    }

    // Default: Network fetch
    event.respondWith(
        fetch(request).catch(() => caches.match(request))
    );
});

// Background Sync Event (where supported by browser)
self.addEventListener('sync', (event) => {
    if (event.tag === 'pwa-sync-sales') {
        event.waitUntil(
            self.clients.matchAll().then((clients) => {
                clients.forEach((client) => {
                    client.postMessage({ type: 'PWA_TRIGGER_BACKGROUND_SYNC' });
                });
            })
        );
    }
});
