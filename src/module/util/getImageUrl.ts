/**
 * 物品圖示已全部鏡像到 public/icons/(由 scripts/fetch_assets.py 下載),
 * 一律走本地相對路徑——灰機 CDN 的防盜連按節點搖擺,熱連賭不贏。
 */
export function getFF14IconUrl(icon_id: number) {
    return './icons/' + icon_id.toString().padStart(6, '0') + '.png';
}
