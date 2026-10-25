// スマホ幅（390×844）で、はじめの画面・車いすで絞り込み・レイヤー・お店カード・経路・案内中を撮る
import { chromium } from "playwright";
import { mkdirSync } from "fs";
mkdirSync("preview", { recursive: true });
const b = await chromium.launch({ args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, serviceWorkers: "block", locale: "ja-JP", geolocation: { latitude: 35.7772, longitude: 139.7199, accuracy: 40 }, permissions: ["geolocation"] });
await ctx.addInitScript(() => localStorage.setItem("profile", JSON.stringify({ key: "assisted", label: "手動車いす（介助あり）", step: 3, slope: 3, width: 2, stairs: false, esc: false, kmh: 3, wheel: true })));
const p = await ctx.newPage();
p.on("pageerror", e => console.log("pageerror", String(e)));
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
// 全国：国交省データのない高松で駅を探してお店カード（OpenStreetMap をその場で読む）、カフェの検索、新宿（国交省データの地区）への切り替え
if (await p.$("#closeCard:not([hidden])")) { await p.click("#closeCard"); await p.waitForTimeout(500); }
await p.evaluate(() => map.jumpTo({ center: [134.0465, 34.3505], zoom: 16 })); await p.waitForTimeout(3000);
await p.fill("#q", "カフェ"); await p.press("#q", "Enter"); await p.waitForTimeout(12000);
await p.screenshot({ path: "preview/9_takamatsu_search.png" });
if (await p.$("#sugg li:nth-child(1) button")) { await p.click("#sugg li:nth-child(1) button"); await p.waitForTimeout(8000); }
await p.screenshot({ path: "preview/10_takamatsu_card.png" });
if (await p.$("#closeCard:not([hidden])")) { await p.click("#closeCard"); await p.waitForTimeout(500); }
await p.evaluate(() => map.jumpTo({ center: [139.7005, 35.6905], zoom: 16 })); await p.waitForTimeout(8000);
await p.screenshot({ path: "preview/11_shinjuku.png" });
await b.close();
