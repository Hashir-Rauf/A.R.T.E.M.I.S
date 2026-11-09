// Keeps the page itself available offline. It never caches or stores anything from ARTEMIS.
const NAME = "artemis-remote-shell-1";
self.addEventListener("install", (e) => e.waitUntil(caches.open(NAME).then((c) => c.addAll(["./", "manifest.json", "icon.svg"]))));
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
