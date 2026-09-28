const CACHE = "mikamike-ui-v3-installable-micro";
const ASSETS = ["./","./index.html","./parent.html","./styles.css","./app.js","./native-bridge.js","./manifest.webmanifest","./icons/mikamike-192.svg","./icons/mikamike-512.svg"];
self.addEventListener("install",(event)=>{event.waitUntil(caches.open(CACHE).then((cache)=>cache.addAll(ASSETS)));self.skipWaiting();});
self.addEventListener("activate",(event)=>{event.waitUntil(caches.keys().then((keys)=>Promise.all(keys.filter((key)=>key!==CACHE).map((key)=>caches.delete(key)))));self.clients.claim();});
self.addEventListener("fetch",(event)=>{
  const request=event.request;if(request.method!=="GET")return;
  const url=new URL(request.url);if(url.pathname.startsWith("/api/"))return;
  event.respondWith(fetch(request).then((response)=>{if(response.ok){const clone=response.clone();caches.open(CACHE).then((cache)=>cache.put(request,clone));}return response;})
  .catch(()=>caches.match(request).then((cached)=>cached||caches.match("./index.html"))));
});
