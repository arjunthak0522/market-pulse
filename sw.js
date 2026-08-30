const CACHE='market-pulse-v9';
const ASSETS=['./','./index.html','./styles.css?v=9','./enhancements.css?v=9','./premium.css?v=9','./clarity.css?v=9','./daily.css?v=9','./app.js?v=9','./premium.js?v=9','./daily.js?v=9','./manifest.webmanifest?v=9','./data/market_context.json','./data/history.json'];
self.addEventListener('install',e=>{self.skipWaiting();e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)))});
self.addEventListener('activate',e=>{e.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))),self.clients.claim()]))});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;const isNav=e.request.mode==='navigate';e.respondWith(fetch(e.request,{cache:'no-store'}).then(r=>{const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return r}).catch(()=>isNav?caches.match('./index.html'):caches.match(e.request)))})
