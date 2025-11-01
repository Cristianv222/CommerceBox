const CACHE_NAME = 'commercebox-v1';

self.addEventListener('install', (event) => {
  console.log('Service Worker instalado');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker activado');
  return self.clients.claim();
});

// NO cachear nada - solo pasar las peticiones a la red
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});