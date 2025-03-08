self.addEventListener('install', e => {
  e.waitUntil(
    caches.open('sb-images').then(cache => cache.addAll([]))
  )
})
self.addEventListener('fetch', e => {
  if (e.request.destination === 'image') {
    e.respondWith(
      caches.match(e.request).then(r => {
        if (r) return r
        return fetch(e.request).then(resp => {
          const clone = resp.clone()
          caches.open('sb-images').then(c => c.put(e.request, clone))
          return resp
        })
      })
    )
  }
})
