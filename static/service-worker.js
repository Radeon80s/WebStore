// service-worker.js

const CACHE_NAME = 'sweetbites-cache-v1';
const OFFLINE_URL = '/offline.html';

const ASSETS_TO_CACHE = [
  '/',
  '/index.html',
  '/offline.html',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/lucide@latest/dist/umd/lucide.min.js',
  'https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.prod.js',
  'https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Playfair+Display:wght@400;500;600;700&display=swap'
];

// Install event - cache assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching files');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache');
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - handle offline access
self.addEventListener('fetch', event => {
  // Skip cross-origin requests
  if (event.request.url.startsWith(self.location.origin) || 
      event.request.url.includes('cdn.jsdelivr.net') ||
      event.request.url.includes('fonts.googleapis.com')) {
    
    // Special handling for API requests
    if (event.request.url.includes('/api/')) {
      // Network first strategy for API calls
      event.respondWith(
        fetch(event.request)
          .catch(error => {
            console.log('Service Worker: Network request failed, serving cached response');
            return caches.match(event.request)
              .then(cachedResponse => {
                if (cachedResponse) {
                  return cachedResponse;
                }
                if (event.request.headers.get('accept').includes('application/json')) {
                  return new Response(JSON.stringify({ 
                    error: 'You are offline. Please check your connection.'
                  }), {
                    headers: { 'Content-Type': 'application/json' }
                  });
                }
                // For any other type, go to offline page
                return caches.match(OFFLINE_URL);
              });
          })
      );
    } else {
      // Cache first strategy for static assets
      event.respondWith(
        caches.match(event.request)
          .then(cachedResponse => {
            // Return cached response if available
            if (cachedResponse) {
              return cachedResponse;
            }

            // Otherwise try to fetch from network
            return fetch(event.request)
              .then(response => {
                // Don't cache if response was not ok
                if (!response.ok) {
                  return response;
                }
                
                // Clone the response before using it
                const responseToCache = response.clone();
                
                // Save new responses in cache
                caches.open(CACHE_NAME)
                  .then(cache => {
                    cache.put(event.request, responseToCache);
                  });
                  
                return response;
              })
              .catch(error => {
                // If no internet connection, serve the offline page
                return caches.match(OFFLINE_URL);
              });
          })
      );
    }
  }
});

// Sync event for background data
self.addEventListener('sync', event => {
  if (event.tag === 'sync-cart') {
    event.waitUntil(syncCart());
  } else if (event.tag === 'sync-orders') {
    event.waitUntil(syncOrders());
  }
});

// Background sync functions
async function syncCart() {
  const db = await openDatabase();
  const pendingCartChanges = await db.getAll('pendingCartChanges');
  
  if (pendingCartChanges.length > 0) {
    // Process pending cart changes when back online
    // This would normally send to a real API
    console.log('Syncing pending cart changes:', pendingCartChanges);
    
    // After successful sync, clear pending changes
    const tx = db.transaction('pendingCartChanges', 'readwrite');
    await tx.objectStore('pendingCartChanges').clear();
  }
}

async function syncOrders() {
  const db = await openDatabase();
  const pendingOrders = await db.getAll('pendingOrders');
  
  if (pendingOrders.length > 0) {
    // Process pending orders when back online
    console.log('Syncing pending orders:', pendingOrders);
    
    // After successful sync, clear pending orders
    const tx = db.transaction('pendingOrders', 'readwrite');
    await tx.objectStore('pendingOrders').clear();
  }
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('SweetBitesOfflineDB', 1);
    
    request.onupgradeneeded = event => {
      const db = event.target.result;
      db.createObjectStore('pendingCartChanges', { keyPath: 'id', autoIncrement: true });
      db.createObjectStore('pendingOrders', { keyPath: 'id', autoIncrement: true });
    };
    
    request.onsuccess = event => resolve(event.target.result);
    request.onerror = event => reject(event.target.error);
  });
}
