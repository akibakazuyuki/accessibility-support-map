// スマホ幅（390×844）で、はじめの画面・車いすで絞り込み・レイヤー・お店カード・経路・案内中を撮る
import { chromium } from "playwright";
import { mkdirSync } from "fs";
mkdirSync("preview", { recursive: true });
const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
// 開いたとき：位置情報なし → 日本全体、大阪で位置情報あり → 大阪へ動く
for (const [name, opt] of [["0_open_nolocation", {}], ["0b_open_osaka", { geolocation: { latitude: 34.7025, longitude: 135.4959, accuracy: 40 }, permissions: ["geolocation"] }]]) {
  const c0 = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, serviceWorkers: "block", locale: "ja-JP", ...opt });
  const p0 = await c0.newPage(); p0.on("pageerror", e => console.log("pageerror", String(e)));
  await p0.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" }); await p0.waitForTimeout(9000);
  console.log(name, await p0.evaluate(() => JSON.stringify({ ih: innerHeight, iw: innerWidth, map: document.getElementById("map").getBoundingClientRect().height, cv: document.querySelector("#map canvas")?.clientHeight, view: localStorage.getItem("view") })));
  await p0.screenshot({ path: `preview/${name}.png` }); await c0.close();
}
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, serviceWorkers: "block", locale: "ja-JP", geolocation: { latitude: 35.7772, longitude: 139.7199, accuracy: 40 }, permissions: ["geolocation"] });
await ctx.addInitScript(() => localStorage.setItem("profile", JSON.stringify({ key: "assisted", label: "手動車いす（介助あり）", step: 3, slope: 3, width: 2, stairs: false, esc: false, kmh: 3, wheel: true })));
const p = await ctx.newPage();
p.on("pageerror", e => console.log("pageerror", String(e)));
p.on("requestfailed", r => console.log("requestfailed", r.url().slice(0, 80), r.failure()?.errorText));
p.on("response", r => { if (/overpass/.test(r.url())) console.log("overpass", r.status(), r.url().slice(0, 60)); });
await p.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" });
await p.waitForTimeout(5000);
await p.click("#btnLocate"); await p.waitForTimeout(3500);
await p.screenshot({ path: "preview/1_start.png" });
await p.click('.chip[data-f="wheel"]'); await p.waitForTimeout(2500);
await p.screenshot({ path: "preview/2_food.png" });
await p.click("#btnLayers"); await p.waitForTimeout(800);
await p.screenshot({ path: "preview/4_layers.png" });
await p.keyboard.press("Escape"); await p.waitForTimeout(400);
await p.click("#btnList"); await p.waitForTimeout(800);
await p.screenshot({ path: "preview/6_list.png" });
await p.click("#sugg li:nth-child(1) button"); await p.waitForTimeout(5000);
await p.screenshot({ path: "preview/3_card.png" });
await p.click("#grab"); await p.waitForTimeout(1200);
await p.screenshot({ path: "preview/5_full.png" });
await p.click("#grab"); await p.waitForTimeout(800);
if (await p.$("#btnGo")) { await p.click("#btnGo"); await p.waitForTimeout(4000); }
await p.screenshot({ path: "preview/7_go.png" });
if (await p.$("#navGo")) { await p.click("#navGo"); await p.waitForTimeout(3500); }
await p.screenshot({ path: "preview/8_nav.png" });
// 全国：国交省データのない金沢で駅のカード（OpenStreetMap をその場で読む）とカフェの検索、新宿（国交省データの地区）のカード
await p.goto("http://127.0.0.1:8080/", { waitUntil: "networkidle" }); await p.waitForTimeout(5000);
async function find(q, shot, wait) {
  await p.evaluate(() => { const c = document.getElementById("closeCard"); if (c && !c.hidden) c.click(); }); await p.waitForTimeout(500);
  await p.fill("#q", q); await p.press("#q", "Enter"); await p.waitForTimeout(wait);
  await p.screenshot({ path: `preview/${shot}_list.png` });
  const first = p.locator("#sugg li:nth-child(1) button");
  if (await first.isVisible()) { await first.click(); await p.waitForTimeout(9000); await p.screenshot({ path: `preview/${shot}_card.png` }); }
  else console.log("no results for", q, await p.textContent("#msg"));
}
await find("大阪", "8b_osaka", 9000);
await find("金沢 カフェ", "8c_kanazawa_cafe", 12000);
await find("金沢駅", "9_kanazawa", 8000);
await find("カフェ", "10_kanazawa_cafe", 28000);
await find("新宿駅", "11_shinjuku", 14000);
// 金沢に戻って、全国のピン（トイレ・車椅子OK）が出るか
await find("兼六園", "12_kenrokuen", 8000);
await p.evaluate(() => { const c = document.getElementById("closeCard"); if (c && !c.hidden) c.click(); }); await p.waitForTimeout(6000);
await p.screenshot({ path: "preview/12_kenrokuen_pins.png" });
// 金沢駅にいるとして、兼六園までの階段を避けた道（国交省データのない地域の経路）
await ctx.setGeolocation({ latitude: 36.5781, longitude: 136.6480, accuracy: 30 });
await p.click("#btnLocate"); await p.waitForTimeout(4000);
await find("兼六園", "13_route", 8000);
await p.waitForTimeout(6000); await p.screenshot({ path: "preview/13_route_card2.png" });
if (await p.locator("#btnGo").isVisible()) { await p.click("#btnGo"); await p.waitForTimeout(4000); await p.screenshot({ path: "preview/13_route_go.png" }); }
else console.log("no route button");
await b.close();
