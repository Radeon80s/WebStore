// SweetBites Service Worker

const CACHE_NAME = 'sweetbites-cache-v1';
const OFFLINE_PAGE = '/offline.html';

// Assets to cache immediately when the service worker installs
const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  OFFLINE_PAGE,
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/lucide@latest/dist/umd/lucide.min.js',
  'https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.prod.js',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap',

];

// Install event - caches the specified assets when the service worker is installed
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Caching pre-defined assets');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => {
        // Skip waiting forces the waiting service worker to become the active service worker
        return self.skipWaiting();
      })
  );
});

// Activate event - cleanup old caches when a new service worker activates
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(cacheNames => {
        return Promise.all(
          cacheNames.filter(cacheName => {
            return cacheName !== CACHE_NAME;
          }).map(cacheName => {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          })
        );
      })
      .then(() => {
        // Claim control over all clients within scope immediately
        // Rather than waiting for reload
        return self.clients.claim();
      })
  );
});

// Fetch event - serve from cache first, then network with cache update for non-API routes
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (!event.request.url.startsWith(self.location.origin) && 
      !event.request.url.startsWith('https://cdn.')) {
    return;
  }

  // Handle API requests differently
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // If API call fails, return a custom JSON response
          return new Response(
            JSON.stringify({ 
              error: 'You are currently offline.',
              offline: true
            }),
            { 
              headers: { 'Content-Type': 'application/json' } 
            }
          );
        })
    );
    return;
  }

  // Handle HTML navigation requests 
  if (event.request.mode === 'navigate' || 
      (event.request.method === 'GET' && 
       event.request.headers.get('accept').includes('text/html'))) {
    
    event.respondWith(
      fetch(event.request)
        .catch(() => {
          // If navigation fails due to being offline, serve the offline page
          return caches.match(OFFLINE_PAGE);
        })
    );
    return;
  }

  // For all other requests (CSS, JS, images, etc)
  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Return cached version if available
        if (cachedResponse) {
          // Fetch an updated version in the background to cache for next time
          fetch(event.request)
            .then(response => {
              // Only cache valid responses
              if (response && response.status === 200) {
                caches.open(CACHE_NAME)
                  .then(cache => cache.put(event.request, response));
              }
            })
            .catch(() => {/* Silently fail background fetch */});
          
          return cachedResponse;
        }

        // No cached version, try network
        return fetch(event.request)
          .then(response => {
            if (!response || response.status !== 200) {
              return response;
            }

            // Clone the response as it can only be consumed once
            const responseToCache = response.clone();
            
            // Cache for next time
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });

            return response;
          })
          .catch(error => {
            // For image requests, you might want to return a placeholder
            if (event.request.url.match(/\.(jpg|jpeg|png|gif|svg)$/)) {
              return caches.match('/images/products/placeholder.jpg');
            }
            
            throw error;
          });
      })
  );
});

// Handle messages from the main thread
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
