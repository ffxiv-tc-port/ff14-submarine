# -*- coding: utf-8 -*-
"""台服(TC)版 data.js 產生器。

資料來源三路:
  1. 台服 EXD dump(權威):航點/海圖/零件/逐級獎勵/物品繁中名
     D:/ffxiv-tc-port/exd-tc/7.20/{SubmarineExploration,SubmarineMap,SubmarinePart,SubmarineRank,Item}.csv
  2. CN huijiwiki 線上資料快照(scripts/data/huiji_live_data.json):
     EXD 沒有的社群量測資料——探索/收集/恩惠門檻、掉落表、解鎖鏈、物品分類
  3. SubmarineTracker(艦隊內)Sectors.cs:門檻交叉驗證用

實證過的公式(對 CN 全量回歸命中):
  range    = floor(3D距離 × 0.035)   …… 航行距離消耗
  distance = floor(3D距離 × 39.9)    …… 航行時間秒數(app 內名為 distance)
  surveyDistance = SurveyDurationmin × 60(CN 值是舊版本 ×7/6,以台服為準)

toDestination 鍵結構:CN 原始資料 map1 用 row_id+1(Lua 陣列)、map2+ 用 row_id;
本產生器統一輸出「dict 鍵 = row_id、含起點列」——map1 因含鍵 '0' 不會被
convertLuaTable 誤轉成 0-indexed 陣列,map2+ 鍵不連續本來就安全。
"""
import csv
import json
import math
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

EXD = 'D:/ffxiv-tc-port/exd-tc/7.20/'
ST_SECTORS = 'D:/ffxiv-tc-port/SubmarineTracker/SubmarineTracker/Data/Sectors.cs'
ROOT = Path(__file__).resolve().parent.parent
CN_SNAPSHOT = ROOT / 'scripts' / 'data' / 'huiji_live_data.json'
OUT = ROOT / 'public' / 'data.js'

IDEOGRAPHIC_SPACE = chr(0x3000)

REWARD_CATEGORY_TC = {
    '0': '消耗品/其他',
    '1': '收藏品',
    '2': '時裝',
    '3': '家具',
    '4': '特殊素材',
    '5': '工房素材',
}

PART_SUFFIXES = ['級船體', '級船尾', '級船首', '級艦橋']


def lua_arr(x):
    """CN 資料裡的 Lua 1-indexed dict → list;真 list 原樣回傳。"""
    if isinstance(x, dict):
        return [x[k] for k in sorted(x, key=int)]
    return x


def read_csv(name):
    with open(EXD + name, encoding='utf-8') as f:
        rows = list(csv.reader(f))
    return rows[0], rows[1:]  # (欄名列, 資料列)——exd-tc 沒有型別列,rows[1] 就是 row 0


def main():
    fail = []

    # ---------- 台服 EXD ----------
    _, map_rows = read_csv('SubmarineMap.csv')
    tc_maps = {int(r[0]): r[1] for r in map_rows if r[1].strip()}
    assert len(tc_maps) == 6, f'台服海圖應為 6 張,得到 {tc_maps}'

    _, exp_rows = read_csv('SubmarineExploration.csv')
    tc_pts = {}
    for r in exp_rows:
        rid = int(r[0])
        rec = dict(
            dest=r[1], exp=int(r[3]), surv_min=int(r[4]),
            x=int(r[5]), y=int(r[6]), z=int(r[7]), map=int(r[8]), stars=int(r[9]),
            rank=int(r[10]), tank=int(r[11]), survey_dist=int(r[12]),
            start=(r[13] == 'True'))
        if rec['start'] or rec['dest'].strip():
            tc_pts[rid] = rec
    starts = [rid for rid, p in tc_pts.items() if p['start']]
    sectors = [rid for rid, p in tc_pts.items() if not p['start']]
    print(f'台服航點:起點 {len(starts)} 個、航點 {len(sectors)} 個')
    assert len(starts) == 6, starts
    assert len(sectors) == 123, len(sectors)

    _, rank_rows = read_csv('SubmarineRank.csv')
    # 欄位: #,ExpToNext,Capacity,SurveillanceBonus,RetrievalBonus,SpeedBonus,RangeBonus,FavorBonus
    rank_bonus = {}
    for r in rank_rows:
        rid = int(r[0])
        surv, retr, spd, rng, fav = (int(x) for x in r[3:8])
        if rid > 0 and any((surv, retr, spd, rng, fav)) or rid == 1:
            rank_bonus[rid] = [0, surv, retr, spd, rng, fav]
    max_rank = max(rank_bonus)
    # rank 1 起沒有獎勵的低等級列也要補齊(值全 0)
    for rid in range(1, max_rank + 1):
        rank_bonus.setdefault(rid, [0, 0, 0, 0, 0, 0])
    print(f'台服等級上限 = {max_rank},滿級獎勵 = {rank_bonus[max_rank]}')
    assert max_rank == 130, max_rank

    _, part_rows = read_csv('SubmarinePart.csv')
    # 欄位: #,Class,Surveillance,Retrieval,Speed,Range,Favor,Slot,Rank,Components,RepairMaterials
    tc_parts = {}
    for r in part_rows:
        rid = int(r[0])
        if rid == 0:
            continue
        tc_parts[rid] = dict(
            cls=int(r[1]), surv=int(r[2]), retr=int(r[3]), spd=int(r[4]),
            rng=int(r[5]), fav=int(r[6]), slot=int(r[7]), rank=int(r[8]),
            weight=int(r[9]),  # Components 欄實測=重量(值域 {5,9,12,14,17,20} 與社群資料逐一吻合)
            repair=int(r[10]))
    assert len(tc_parts) == 40, len(tc_parts)

    # ---------- CN 快照 ----------
    cn = json.load(open(CN_SNAPSHOT, encoding='utf-8'))
    cn_pts = {int(p['id']): p for p in lua_arr(cn['point_data'])}
    cn_items = cn['item_db']
    cn_seas = lua_arr(cn['sea_name_map'])
    cn_components = lua_arr(cn['components'])

    # ---------- 全球社群掉落總表(完整逐航點,含普通素材;CN 維基只收精選品) ----------
    # 快照自 SubmarineTracker 引用的社群試算表 Items/Sectors (detailed) 分頁
    gs_tier = {'T1': 'low', 'T2': 'mid', 'T3': 'high'}
    en2id = json.load(open(ROOT / 'scripts' / 'data' / 'item_en_to_id.json', encoding='utf-8'))
    mapletter_to_sector = {}
    with open(ROOT / 'scripts' / 'data' / 'gs_sectors.csv', encoding='utf-8') as f:
        for r in list(csv.reader(f))[1:]:
            if len(r) > 2 and r[0].strip():
                mapletter_to_sector[(r[2].strip(), r[1].strip())] = r[0].strip()
    sheet_loot = {}
    with open(ROOT / 'scripts' / 'data' / 'gs_items.csv', encoding='utf-8') as f:
        for r in list(csv.reader(f))[1:]:
            if len(r) > 3 and r[0].strip() and r[2].strip():
                iid = en2id[r[2].strip().lower()]
                sheet_loot.setdefault(r[0].strip(), {'low': [], 'mid': [], 'high': []})[gs_tier[r[3].strip()]].append(iid)
    en_maps = [s['en'] for s in cn_seas]  # index = map-1
    print(f'社群總表:{len(sheet_loot)} 航點的完整掉落、{len(en2id)} 個物品名對照')

    def sheet_loot_for(rid):
        p = tc_pts[rid]
        if p['start']:
            return None
        letter = p['dest'].split(IDEOGRAPHIC_SPACE, 1)[0]
        sname = mapletter_to_sector.get((en_maps[p['map'] - 1], letter))
        return sheet_loot.get(sname) if sname else None

    # ---------- SubmarineTracker 門檻(交叉驗證) ----------
    st_bp = {}
    for m in re.finditer(r'\{\s*(\d+),\s*new Breakpoint\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)', open(ST_SECTORS, encoding='utf-8').read()):
        rid, t2, t3, norm, optim, favor = (int(g) for g in m.groups())
        st_bp[rid] = dict(mid=t2, high=t3, norm=norm, optim=optim, favor=favor)
    print(f'SubmarineTracker 門檻筆數 = {len(st_bp)}')
    assert len(st_bp) >= 123, len(st_bp)

    # ---------- 物品名(台服 Item.csv,大檔逐列掃) ----------
    need_ids = set()
    for rid in sectors:
        cn_p = cn_pts.get(rid)
        if cn_p:
            for k in ('low', 'mid', 'high'):
                need_ids.update(int(i) for i in lua_arr((cn_p.get('drop') or {}).get(k) or []))
        sl = sheet_loot_for(rid)
        if sl:
            for lst in sl.values():
                need_ids.update(lst)
    for c in cn_components:
        need_ids.update(int(i) for i in lua_arr(c['items']))
    tc_item = {}
    with open(EXD + 'Item.csv', encoding='utf-8') as f:
        rd = csv.reader(f)
        ihdr = next(rd)
        name_i, icon_i, rarity_i = ihdr.index('Name'), ihdr.index('Icon'), ihdr.index('Rarity')
        for r in rd:
            try:
                rid = int(r[0])
            except ValueError:
                continue
            if rid in need_ids and r[name_i].strip():
                tc_item[rid] = dict(name=r[name_i], icon=int(r[icon_i]), rarity=int(r[rarity_i]))
    missing_items = sorted(need_ids - set(tc_item))
    if missing_items:
        print(f'⚠️ {len(missing_items)} 個物品台服查無(掉落表中剔除):{missing_items}')

    # ---------- 零件對映驗證:CN 機體數據 vs 台服 SubmarinePart ----------
    part_item_info = {}  # item_id -> {位置, 重量, 各屬性, 等级}
    matched_parts = set()
    for c in cn_components:
        for item_id in (int(i) for i in lua_arr(c['items'])):
            md = cn_items[str(item_id)].get('机体数据')
            assert md, f'CN 零件 {item_id} 無机体数据'
            hits = [pid for pid, tp in tc_parts.items()
                    if tp['slot'] == md['位置'] and tp['surv'] == md['探索性能']
                    and tp['retr'] == md['收集性能'] and tp['spd'] == md['巡航速度']
                    and tp['rng'] == md['航行距离'] and tp['fav'] == md['恩惠']
                    and tp['weight'] == md['重量']]
            if len(hits) != 1:
                fail.append(f'零件 {item_id} 與台服 SubmarinePart 對映異常: {hits}')
                continue
            pid = hits[0]
            matched_parts.add(pid)
            tp = tc_parts[pid]
            part_item_info[item_id] = {
                '位置': tp['slot'], '重量': tp['weight'],
                '探索性能': tp['surv'], '收集性能': tp['retr'], '巡航速度': tp['spd'],
                '航行距離': tp['rng'], '恩惠': tp['fav'],
                '修理': tp['repair'], '等級': tp['rank'],
            }
    assert len(matched_parts) == 40, f'40 件零件只對上 {len(matched_parts)}'
    print('零件 40/40 與台服 SubmarinePart 全數值吻合')

    # ---------- 組零件 components(名稱取台服物品名的共同字首) ----------
    out_components = []
    for c in cn_components:
        items = [int(i) for i in lua_arr(c['items'])]
        names = [tc_item[i]['name'] for i in items]
        prefixes = set()
        for n in names:
            for suf in PART_SUFFIXES:
                if n.endswith(suf):
                    prefixes.add(n[: -len(suf)])
                    break
            else:
                fail.append(f'零件名 {n} 不符合任何字尾')
        assert len(prefixes) == 1, f'零件組 {c["c"]} 字首不一致: {prefixes} ({names})'
        out_components.append(dict(c=c['c'], n=prefixes.pop(), items=items))
    print('components:', [(c['c'], c['n']) for c in out_components])

    # ---------- 海圖名 ----------
    out_seas = []
    for i in range(1, 7):
        cn_sea = cn_seas[i - 1]
        out_seas.append(dict(cn=tc_maps[i], en=cn_sea['en'], jp=cn_sea['jp']))
    print('海圖:', [s['cn'] for s in out_seas])

    # ---------- 航點 ----------
    by_map = {}
    for rid, p in tc_pts.items():
        by_map.setdefault(p['map'], []).append(rid)

    def dist3(a, b):
        pa, pb = tc_pts[a], tc_pts[b]
        return math.sqrt((pa['x'] - pb['x']) ** 2 + (pa['y'] - pb['y']) ** 2 + (pa['z'] - pb['z']) ** 2)

    # 距離公式回歸閘門:對 CN 已有的同地圖配對全量比對
    reg_total = reg_bad = 0
    for rid, cn_p in cn_pts.items():
        if rid not in tc_pts or tc_pts[rid]['map'] not in by_map:
            continue
        td = cn_p.get('toDestination') or {}
        m = tc_pts[rid]['map']
        shift = 1 if m == 1 else 0  # CN map1 鍵=row_id+1
        for k, v in td.items():
            dest = int(k) - shift
            if dest == rid or dest not in tc_pts or tc_pts[dest]['map'] != m:
                continue
            d3 = dist3(rid, dest)
            reg_total += 1
            if math.floor(d3 * 0.035) != v['range'] or math.floor(d3 * 39.9) != v['distance']:
                reg_bad += 1
                if reg_bad <= 5:
                    fail.append(f'距離回歸失配 {rid}->{dest}: 算({math.floor(d3*0.035)},{math.floor(d3*39.9)}) CN({v["range"]},{v["distance"]})')
    print(f'距離公式回歸:{reg_total} 對,失配 {reg_bad}')
    assert reg_total > 2000 and reg_bad == 0, (reg_total, reg_bad)

    # 門檻:CN 為主、SubmarineTracker 交叉驗證
    bp_mismatch = 0
    sheet_covered = 0  # 有社群總表掉落的航點數
    cn_extra_total = 0  # CN 精選品不在總表的筆數(交叉檢查指標)
    out_points = []
    for rid in sorted(tc_pts):
        p = tc_pts[rid]
        cn_p = cn_pts.get(rid, {})
        if p['start']:
            code, name = '', ''
        else:
            parts = p['dest'].split(IDEOGRAPHIC_SPACE, 1)
            assert len(parts) == 2, f'row {rid} Destination 無全形空白: {p["dest"]!r}'
            code, name = parts[0], parts[1]
            cn_code = cn_p.get('code')
            if cn_code and cn_code != code:
                fail.append(f'row {rid} 代號不一致: TC={code} CN={cn_code}')

        # statReq:CN 快照
        cn_sr = cn_p.get('statReq') or {}
        sr = dict(
            favor=(cn_sr.get('favor') or 0),
            retrieval=dict(norm=(cn_sr.get('retrieval') or {}).get('norm', 0),
                           optim=(cn_sr.get('retrieval') or {}).get('optim', 0)),
            surveillance=dict(mid=(cn_sr.get('surveillance') or {}).get('mid', 0),
                              high=(cn_sr.get('surveillance') or {}).get('high', 0)))
        if not p['start']:
            assert sr['favor'] > 0, f'row {rid} 缺 CN 門檻資料'
            bp = st_bp.get(rid)
            if bp and (bp['mid'] != sr['surveillance']['mid'] or bp['high'] != sr['surveillance']['high']
                       or bp['norm'] != sr['retrieval']['norm'] or bp['optim'] != sr['retrieval']['optim']
                       or bp['favor'] != sr['favor']):
                bp_mismatch += 1
                print(f'⚠️ row {rid} 門檻 CN vs SubmarineTracker 不一致: CN={sr} ST={bp}')

        # 掉落:社群總表為主(tier 歸屬以它的量測為準),CN 精選品若總表沒有補在最前
        sl = sheet_loot_for(rid)
        drop = {}
        if sl:
            sheet_covered += 1
            sheet_all = {i for lst in sl.values() for i in lst}
            for k in ('low', 'mid', 'high'):
                cn_list = [int(x) for x in lua_arr((cn_p.get('drop') or {}).get(k) or [])]
                cn_extra_total += sum(1 for i in cn_list if i not in sheet_all)
                merged = [i for i in cn_list if i not in sheet_all] + sl[k]
                seen = set()
                drop[k] = [i for i in merged if i in tc_item and not (i in seen or seen.add(i))]
        else:
            if not p['start']:
                fail.append(f'row {rid} 在社群總表查無掉落(map={p["map"]} code={code})')
            for k in ('low', 'mid', 'high'):
                drop[k] = [i for i in (int(x) for x in lua_arr((cn_p.get('drop') or {}).get(k) or [])) if i in tc_item]

        td_out = {}
        for dest in by_map[p['map']]:
            d3 = dist3(rid, dest)
            td_out[str(dest)] = dict(range=math.floor(d3 * 0.035), distance=math.floor(d3 * 39.9))

        unlocks = cn_p.get('unlocks') or {}
        unlocks_out = {}
        if isinstance(unlocks, dict):
            if unlocks.get('map'):
                unlocks_out['map'] = unlocks['map']
            if unlocks.get('sectors'):
                unlocks_out['sectors'] = [int(x) for x in lua_arr(unlocks['sectors'])]

        out_points.append(dict(
            id=rid, map=p['map'], code=code, name=name, start=p['start'],
            stars=p['stars'], rankReq=p['rank'], tankReq=p['tank'],
            expReward=p['exp'],
            surveyDistance=p['surv_min'] * 60,   # 勘查時間(秒),台服權威
            surveyRange=p['survey_dist'],        # 勘查距離,台服權威
            x=p['x'], y=p['y'],
            statReq=sr, drop=drop, toDestination=td_out, unlocks=unlocks_out))
    print(f'航點輸出 {len(out_points)} 筆;門檻與 SubmarineTracker 不一致 {bp_mismatch} 筆')
    print(f'掉落:社群總表覆蓋 {sheet_covered}/{len(sectors)} 航點;CN 精選品不在總表的 {cn_extra_total} 筆(已補列)')
    assert sheet_covered == len(sectors), (sheet_covered, len(sectors))

    # map1 的 toDestination 含鍵 '0',convertLuaTable 不會誤轉(鍵 0 存在即非 1-indexed 連續)
    m1 = next(pt for pt in out_points if pt['map'] == 1)
    assert '0' in m1['toDestination'], 'map1 toDestination 必須含起點鍵 0'

    # ---------- item_db ----------
    out_items = {}
    for iid, info in sorted(tc_item.items()):
        cn_it = cn_items.get(str(iid), {})
        rec = {'ID': iid, '中文名': info['name'], '品質': info['rarity'], '圖標ID': info['icon']}
        if cn_it.get('中文名'):
            rec['維基名'] = cn_it['中文名']  # 灰機 wiki 頁名用簡中,連結靠這個
        if 'category' in cn_it:
            rec['category'] = cn_it['category']
        if cn_it.get('valuable'):
            rec['valuable'] = True
        if iid in part_item_info:
            rec['機體數據'] = part_item_info[iid]
        out_items[str(iid)] = rec
    print(f'item_db {len(out_items)} 筆(零件 {len(part_item_info)})')

    # ---------- 總組裝 ----------
    data = dict(
        components=out_components,
        data_sources=[
            dict(title='台服遊戲資料 7.20(航點/零件/等級獎勵/物品名)', desc='SubmarineExploration/SubmarinePart/SubmarineRank/Item', author='SQUARE ENIX', url=''),
            dict(title='部队潜水艇小工具(門檻/掉落/解鎖資料)', desc='原作工具與社群量測資料', author='Yuee', url='https://ff14.huijiwiki.com/wiki/%E9%83%A8%E9%98%9F%E6%BD%9C%E6%B0%B4%E8%89%87%E5%B0%8F%E5%B7%A5%E5%85%B7'),
            dict(title='SubmarineTracker 社群數據表(門檻交叉驗證)', desc='', author='Infiziert90', url='https://docs.google.com/spreadsheets/d/1eiuGRrQTjJ5n4ogybKOBxJRT7EiJLlX93fge-Z8MmD4'),
        ],
        item_db=out_items,
        max_filter_count=cn.get('max_filter_count', 300),
        max_rank=max_rank,
        max_rank_bonus=rank_bonus[max_rank],
        # 真陣列(index=等級,0 位是零值)——dict 鍵 '1'..'130' 連續會被 convertLuaTable 誤轉成 0-indexed
        rank_bonus_table=[[0, 0, 0, 0, 0, 0]] + [rank_bonus[r] for r in range(1, max_rank + 1)],
        sea_name_map=out_seas,
        point_data=out_points,
        reward_category_map=REWARD_CATEGORY_TC,
        tool_version=101,
    )

    if fail:
        print('\n🔴 驗證失敗,不輸出:')
        for f_ in fail:
            print('  -', f_)
        sys.exit(1)

    js = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    js_escaped = js.replace(chr(92), chr(92) * 2).replace(chr(39), chr(92) + chr(39))
    content = "window.DATA = JSON.parse(" + chr(10) + chr(39) + js_escaped + chr(39) + ");" + chr(10)
    OUT.write_bytes(content.encode('utf-8'))

    # 控制字元掃描(CLAUDE.md 規約)
    raw = OUT.read_bytes()
    ctrl = [b for b in raw if b < 32 and b not in (9, 10, 13)]
    assert not ctrl, f'輸出含控制字元: {ctrl[:10]}'
    # 回讀驗證:剝殼後可 JSON 解析且列數一致
    txt = raw.decode('utf-8')
    inner = txt[txt.index(chr(39)) + 1: txt.rindex(chr(39))]
    back = json.loads(inner.replace(chr(92) + chr(39), chr(39)).replace(chr(92) * 2, chr(92)))
    assert len(back['point_data']) == len(out_points)
    print(f'\n✅ 已輸出 {OUT}({len(raw)} bytes)')


if __name__ == '__main__':
    main()
