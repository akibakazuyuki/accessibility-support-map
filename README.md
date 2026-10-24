# アクセシビリティ・サポートマップ

車椅子・ベビーカー・杖などで外出する人のための地図です。段差・道幅・坂・エレベーター・トイレの情報をもとに、その人の移動条件で「行けるか」を根拠つきで示すことを目指しています。まずは東京都北区の赤羽駅周辺で試験提供します。

- 公開URL：https://akibakazuyuki.github.io/accessibility-support-map/
- スマホのホーム画面に追加すると、アプリのように使えます（PWA）。

## 構成

- `index.html`：画面と処理のすべて（MapLibre GL JS ＋ OpenFreeMap。予備に国土地理院ベクトルタイル）
- `data/areas.json`：対応エリアの一覧（範囲・データのファイル・現在地が範囲外のときの出発地）。経路はここに載ったどのエリアでも同じ仕組みで動く
- `data/akabane.json`：赤羽駅周辺の歩道（段差・幅・坂など）と施設のデータ。`scripts/build_area.py` が GitHub Actions で毎週作り直す
- `manifest.webmanifest`・`sw.js`・`icons/`：ホーム画面への追加とオフライン起動

## データの出典

- 歩道の段差・幅・坂など：[国土交通省 歩行空間ネットワークデータ（赤羽駅周辺）](https://ckan.hokonavi.go.jp/dataset/nwd_akabane_station)（公共データ利用規約 第1.0版）
- トイレ・エレベーター・入口：OpenStreetMap（Overpass API）
- 地図：[OpenFreeMap](https://openfreemap.org/)（© OpenMapTiles、© OpenStreetMap contributors）。予備に[国土地理院ベクトルタイル](https://github.com/gsi-cyberjapan/optimal_bvmap)
- 場所の検索：国土地理院 地名・住所検索、OpenStreetMap（Nominatim・Photon）。© OpenStreetMap contributors（ODbL）
