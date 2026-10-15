const CACHE_NAME = "formlog-shell-v1";
const scopeUrl = self.registration.scope;
const indexUrl = new URL("./index.html", scopeUrl).href;
const shellUrls = [
  new URL("./", scopeUrl).href,
  indexUrl,
  new URL("./manifest.webmanifest", scopeUrl).href,
  new URL("./icon.svg", scopeUrl).href,
  new URL("./icon-192.png", scopeUrl).href,
  new URL("./icon-512.png", scopeUrl).href,
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    const response = await fetch(indexUrl, { cache: "reload" });
    const html = await response.clone().text();
    await cache.put(indexUrl, response);
    const assets = [...html.matchAll(/(?:src|href)="([^"]+)"/g)]
      .map((match) => match[1])
      .filter((path) => path.startsWith("./assets/") || path.startsWith("/assets/"))
      .map((path) => new URL(path, scopeUrl).href);
    await cache.addAll([...shellUrls, ...assets]);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter((name) => name.startsWith("formlog-shell-") && name !== CACHE_NAME).map((name) => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        const cache = await caches.open(CACHE_NAME);
        await cache.put(indexUrl, response.clone());
        return response;
      } catch {
        return (await caches.match(indexUrl)) || Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }
    return response;
  })());
});
