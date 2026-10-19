# -*- coding: utf-8 -*-
"""把所有熱連的灰機 CDN 資產鏡像進 repo,讓部署不再依賴對方的防盜連政策。

實測(2026-08-18):huiji-public.huijistatic.com 對外站 referer 回 403,
且同一批檔案在不同 CDN 節點上 403/200 不一致——no-referrer 賭不贏,只能自host。
下載時帶 referer=https://ff14.huijiwiki.com/ + 瀏覽器 UA(實測全 200)。

鏡像三塊:
  1. 物品圖示:public/data.js 的所有 圖標ID → public/icons/{六位數}.png
     (執行期由 getImageUrl.ts 以 ./icons/ 相對路徑取用)
  2. 海圖背景:12 張(6 海域 × 地圖/路線)→ src/assets/maps/map{n}.png / map{n}_route.png
     (由 WaypointList.vue 的 CSS 引用,vite 打包)
  3. huijiwiki.css 引用的外部資產(圖/字型)→ public/vendor/,並改寫 CSS 為 ./vendor/ 相對路徑
     (只改寫 https:// 與 // 開頭的絕對 URL;站內相對路徑是 wiki 專屬功能,本來就 404,不動)

冪等:重跑會跳過已存在且非空的檔;CSS 改寫前先驗「還有沒有絕對 URL」。
每個下載都驗 Content 前 4 bytes 不是 HTML(擋住錯誤頁被當圖存下來)。
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / 'public' / 'icons'
VENDOR_DIR = ROOT / 'public' / 'vendor'
MAP_DIR = ROOT / 'src' / 'assets' / 'maps'
CSS_PATH = ROOT / 'public' / 'huijiwiki.css'

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'
REFERER = 'https://ff14.huijiwiki.com/'
CDN = 'https://huiji-public.huijistatic.com'

# 海圖檔名(CN wiki 命名),鍵=地圖編號
MAP_FILES = {
    1: '溺没海',
    2: '灰海',
    3: '翠浪海',
    4: '妖歌海',
    5: '紫礁海',
    6: '南苍茫洋',
}


def cdn_upload_url(filename):
    filename = filename[0].upper() + filename[1:] if filename and filename[0].isascii() else filename
    h = hashlib.md5(filename.encode('utf-8')).hexdigest()
    return f'{CDN}/ff14/uploads/{h[0]}/{h[:2]}/{urllib.parse.quote(filename)}'


def fetch(url, dest: Path, retries=3):
    if dest.exists() and dest.stat().st_size > 0:
        return 'skip'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Referer': REFERER})
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if not data:
                raise RuntimeError('空回應')
            head = data[:64].lstrip()[:16].lower()
            if head.startswith(b'<!doctype') or head.startswith(b'<html'):
                raise RuntimeError('回應是 HTML 不是資產')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return 'ok'
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1 + attempt)
    raise RuntimeError(f'{url} -> {last}')


def mirror_icons():
    raw = CSS_PATH.parent.joinpath('data.js').read_text(encoding='utf-8')
    inner = raw[raw.index(chr(39)) + 1: raw.rindex(chr(39))]
    data = json.loads(inner.replace(chr(92) + chr(39), chr(39)).replace(chr(92) * 2, chr(92)))
    icon_ids = sorted({v['圖標ID'] for v in data['item_db'].values()})
    ok = skip = 0
    for icon_id in icon_ids:
        fn = str(icon_id).zfill(6) + '.png'
        r = fetch(cdn_upload_url(fn), ICON_DIR / fn)
        ok, skip = ok + (r == 'ok'), skip + (r == 'skip')
    print(f'圖示 {len(icon_ids)} 個:新下載 {ok}、已存在 {skip}')


def mirror_maps():
    ok = skip = 0
    for n, sea in MAP_FILES.items():
        for suffix, out in (('地图', f'map{n}.png'), ('路线', f'map{n}_route.png')):
            r = fetch(cdn_upload_url(f'{sea}{suffix}.png'), MAP_DIR / out)
            ok, skip = ok + (r == 'ok'), skip + (r == 'skip')
    print(f'海圖 12 張:新下載 {ok}、已存在 {skip}')


def mirror_css_assets():
    css = CSS_PATH.read_text(encoding='utf-8')
    # 絕對 URL(https:// 或 //),含引號或裸寫兩種形式
    pattern = re.compile(r"url\(\s*['\"]?((?:https?:)?//[^)'\"]+)['\"]?\s*\)")
    urls = sorted({m.group(1) for m in pattern.finditer(css)})
    seen_names = {}
    ok = skip = 0
    failed = []
    for u in urls:
        full = ('https:' + u) if u.startswith('//') else u
        base = full.split('#')[0].split('?')[0]  # query 只是 cache buster,一併剝掉
        name = urllib.parse.unquote(base.rsplit('/', 1)[-1])
        if not name:
            continue
        if name in seen_names and seen_names[name] != base:
            raise RuntimeError(f'vendor 檔名衝突: {name} ({seen_names[name]} vs {base})')
        seen_names[name] = base
        try:
            r = fetch(base, VENDOR_DIR / name)
        except RuntimeError as e:
            failed.append(str(e))
            continue  # 下載不到就保留原 URL,不改寫這筆
        ok, skip = ok + (r == 'ok'), skip + (r == 'skip')
        css = css.replace(u, f'./vendor/{urllib.parse.quote(name)}')
    CSS_PATH.write_text(css, encoding='utf-8')
    print(f'huijiwiki.css 外部資產 {len(urls)} 筆:新下載 {ok}、已存在 {skip}、失敗保留原樣 {len(failed)}')
    for f_ in failed:
        print('  ⚠️', f_)


if __name__ == '__main__':
    mirror_icons()
    mirror_maps()
    mirror_css_assets()
    print('✅ 鏡像完成')
