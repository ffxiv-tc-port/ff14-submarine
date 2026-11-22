# 公會潛水艇小工具(台服版)

FFXIV 公會潛水艇航線與配裝工具的台服(繁體中文)移植版:規劃探索航線、搭配零件、計算屬性與航程時間。

原作:[yueecui/ff14-submarine](https://github.com/yueecui/ff14-submarine)(MIT 授權,部署於灰機 wiki 的[部队潜水艇小工具](https://ff14.huijiwiki.com/wiki/%E9%83%A8%E9%98%9F%E6%BD%9C%E6%B0%B4%E8%89%87%E5%B0%8F%E5%B7%A5%E5%85%B7)頁)。

## 與原作的差異

- **資料以台服遊戲檔為準重新產生**:航點、零件(含完整數值)、逐級屬性獎勵、物品繁中名,全部出自台服 EXD;探索/收集/恩惠門檻與掉落表取自社群量測資料並經 SubmarineTracker 資料交叉驗證;航點間距離由座標重算。目前使用的台服資料版本寫在工具的「關於」頁。
- **可調潛水艇等級**:等級影響船體屬性獎勵;等級不到的航點與零件系列會標灰並擋選取。預設滿級。
- **圖示與海圖鏡像進 repo**:物品圖示、海圖與介面素材放在 `public/` 與 `src/assets/`,不再熱連灰機 CDN。
- 介面繁體中文化,術語對齊台服官方譯名(海域名、零件名、屬性名)。
- 修正兩個原作 bug:沿途目的地的收集需求兩格都顯示「良好」門檻;搜尋器「已加入」判定永遠不成立。
- **掉落機率與目標道具**:「獲得物品」在每個航點旁標出機率(沒選配裝=高監視每趟主掉落機率;選了配裝=該配裝每趟期望數量),
  可切換全部道具/分類,可把道具標成目標(航點清單、海圖、最短路線情報會標出目標的期望);機率來自全球社群紀錄,
  並以台服 SubmarineTracker 紀錄驗證(結果見 `scripts/validate_tc_loot.py`)。

## 開發

```sh
yarn                 # 安裝相依
yarn dev             # 開發伺服器(圖片走 proxy)
yarn build           # 型別檢查+建置到 dist/
```

## 資料重新產生

```sh
python scripts/gen_data.py
```

讀取台服 EXD dump(路徑與資料版本寫死在腳本開頭)、CN 社群資料快照(`scripts/data/huiji_live_data.json`)
與 SubmarineTracker 門檻表,驗證全過才會改寫 `public/data.js`;任何一致性檢查失敗都會中止不輸出。
物品圖示用 `scripts/fetch_assets.py` 下載到 `public/icons/`。

掉落機率:社群試算表快照在 `scripts/data/gs_items.csv`、`gs_sectors.csv`;台服觀測次數在 `scripts/data/tc_loot_stats.json`,
由 `python scripts/gen_tc_loot_stats.py [--db <submarine-sqlite.db>]` 從 SubmarineTracker 資料庫產生
(唯讀開啟,只輸出彙總次數、時間只到月,不含公會/角色/潛水艇等識別資料)。`python scripts/validate_tc_loot.py`
印出台服紀錄對社群機率的交叉驗證表。

台服跳版本後的更新順序:重新 dump EXD → 把腳本與「關於」頁(`src/components/FloatLayerAbout.vue`)裡寫死的版本改成新版 →
需要時更新 CN 快照(抓灰機工具頁的 `wgHuijiVars.DATA`)→ 重跑產生器。

## 部署

`deploy-pages` workflow 在推上 `main` 時建置並發佈到 GitHub Pages(資產走相對路徑,可放在子路徑下)。
本機預覽可 `yarn build` 後以任一靜態伺服器提供 `dist/`。`index.html` 設了 `no-referrer`,是給仍放在灰機 CDN 上的少數背景圖用的。
