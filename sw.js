// 画面の部品だけを端末に保存して、電波が弱い場所でもアプリを開けるようにする。
// 地図タイルと検索結果は毎回ネットから取る（国土地理院・OSMの利用条件に合わせ、まとめて保存しない）
var CACHE = "asm-v10";
var SHELL = ["./", "index.html", "terms.html", "privacy.html", "manifest.webmanifest", "icons/icon.svg", "icons/icon-192.png"];  // data/ はアプリ本体と同じく「新しい版を優先」で保存される
var LIBS = ["https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.js",
  "https://cdn.jsdelivr.net/npm/maplibre-gl@4.7.1/dist/maplibre-gl.css",
  "https://cdn.jsdelivr.net/npm/pmtiles@3.2.1/dist/pmtiles.js"];

self.addEventListener("install", function(e){
  // ライブラリが取れなくてもアプリ本体の保存は済ませる
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.addAll(SHELL).then(function(){ return c.addAll(LIBS).catch(function(){}); }); })
    .then(function(){ return self.skipWaiting(); }));
});
self.addEventListener("activate", function(e){
  e.waitUntil(caches.keys().then(function(ks){
    return Promise.all(ks.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener("fetch", function(e){
  var req = e.request, url = new URL(req.url);
  if (req.method !== "GET") return;
  // アプリ本体：新しい版を優先し、つながらなければ保存した版
  if (req.mode === "navigate" || (url.origin === location.origin)) {
    // 端末やブラウザに残った古い版を使わず、毎回サーバーに新しい版があるか確かめる
    // （画面を開くリクエストはそのまま作り直せないので URL から作る）
    var fresh = req.mode === "navigate" ? new Request(req.url, {cache: "no-cache"}) : new Request(req, {cache: "no-cache"});
    e.respondWith(fetch(fresh).then(function(r){
      var copy = r.clone(); caches.open(CACHE).then(function(c){ c.put(req, copy); }); return r;
    }).catch(function(){ return caches.match(req).then(function(r){ return r || caches.match("index.html"); }); }));
    return;
  }
  // 版を固定したライブラリ：保存した版を使う
  if (url.host === "cdn.jsdelivr.net") {
    e.respondWith(caches.match(req).then(function(r){ return r || fetch(req); }));
  }
});
