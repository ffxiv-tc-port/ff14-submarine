# -*- coding: utf-8 -*-
"""SubmarineTracker 本機紀錄 → 台服掉落彙總(scripts/data/tc_loot_stats.json)。

用法:
  python scripts/gen_tc_loot_stats.py [--db <submarine-sqlite.db>] [--out <json>]
  --db 預設 %APPDATA%/FFXIVSimpleLauncher/Dalamud/Config/pluginConfigs/SubmarineTracker/submarine-sqlite.db

契約:
  - 資料庫只以 mode=ro 開啟、用 backup API 複製進記憶體後立刻關閉(插件持有中也安全:不寫、不 checkpoint)。
  - 輸出只有彙總次數;不含公會、世界、角色、潛水艇的任何識別資料,時間只到月。
  - 監視/回收/恩惠 proc 代碼對照 SubmarineTracker Data/Loot.cs 的 ProcToText。
"""
import argparse
import collections
import datetime
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / 'scripts' / 'data' / 'tc_loot_stats.json'

# 監視 proc → (監視等級, tier);等級 0=低 1=中 2=高
SURV_PROC = {4: (2, 'T3'), 5: (2, 'T2'), 6: (2, 'T1'), 7: (1, 'T2'), 8: (1, 'T1'), 9: (0, 'T1')}
RET_PROC = {16: 0, 15: 1, 14: 2}  # 回收等級 0=差 1=普通 2=最佳
FAV_PROC = {18: 0, 19: 1, 20: 2}  # 0=有第二件 1=屬性夠但沒觸發 2=屬性不足
LEVEL_KEY = ('low', 'mid', 'high')
TIERS_AT = {0: ('T1',), 1: ('T1', 'T2'), 2: ('T1', 'T2', 'T3')}


def default_db():
    appdata = os.environ.get('APPDATA')
    if not appdata:
        sys.exit('找不到 %APPDATA%,請用 --db 指定資料庫')
    return Path(appdata) / 'FFXIVSimpleLauncher' / 'Dalamud' / 'Config' / 'pluginConfigs' / 'SubmarineTracker' / 'submarine-sqlite.db'


def load_snapshot(db_path):
    """唯讀開啟 → 整份複製進記憶體 → 關閉來源。"""
    uri = Path(db_path).resolve().as_uri() + '?mode=ro'
    src = sqlite3.connect(uri, uri=True, timeout=5)
    mem = sqlite3.connect(':memory:')
    try:
        src.backup(mem)
    finally:
        src.close()
    return mem


def month(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime('%Y-%m')


def new_sector():
    return {
        'visits': 0,
        'surv': [0, 0, 0],
        'tier': {k: collections.Counter() for k in LEVEL_KEY},
        'tier_add': {k: collections.Counter() for k in LEVEL_KEY},
        'ret': [0, 0, 0],
        'fav': [0, 0, 0],
        'items': {'T1': {}, 'T2': {}, 'T3': {}},  # 同一道具可能同時在兩個 tier 的掉落池
        # 各等級/各 proc 實際出現過的屬性值 [最小, 最大]:驗門檻用
        'stat': {'surv': [[] for _ in range(3)], 'ret': [[] for _ in range(3)], 'fav': [[] for _ in range(3)]},
    }


def widen(rng, v):
    if rng:
        rng[0], rng[1] = min(rng[0], v), max(rng[1], v)
    else:
        rng.extend((v, v))


def new_item():
    return {'n': [0, 0], 'surv': [0, 0, 0], 'hq': 0,
            'q': [[0, 0, 0, 0] for _ in range(3)]}  # 每回收等級 [次數, 總量, 最小, 最大]


def add_drop(sec, item_id, count, hq, surv_proc, ret_proc, role):
    level, tier = SURV_PROC[surv_proc]
    it = sec['items'][tier].setdefault(str(item_id), new_item())
    it['n'][role] += 1
    it['surv'][level] += 1
    it['hq'] += 1 if hq else 0
    q = it['q'][RET_PROC[ret_proc]]
    q[2] = count if q[0] == 0 else min(q[2], count)
    q[3] = max(q[3], count)
    q[0] += 1
    q[1] += count


def dumps_one_sector_per_line(data):
    """一個航點一行:diff 看得出哪個航點變了,檔案又不會膨脹十倍。"""
    compact = dict(ensure_ascii=False, separators=(',', ':'))
    head = {k: v for k, v in data.items() if k != 'sectors'}
    lines = ['{']
    for k, v in head.items():
        lines.append(f' {json.dumps(k)}: {json.dumps(v, **compact)},')
    lines.append(' "sectors": {')
    sids = list(data['sectors'])
    for i, sid in enumerate(sids):
        tail = ',' if i < len(sids) - 1 else ''
        lines.append(f'  {json.dumps(sid)}: {json.dumps(data["sectors"][sid], **compact)}{tail}')
    lines.append(' }')
    lines.append('}')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=None)
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    args = ap.parse_args()

    db = load_snapshot(args.db or default_db())
    rows = db.execute(
        'select Sector, Surv, Ret, Fav, PrimarySurvProc, AdditionalSurvProc, PrimaryRetProc, AdditionalRetProc, FavProc,'
        ' PrimaryItem, PrimaryCount, PrimaryHQ, AdditionalItem, AdditionalCount, AdditionalHQ, Date'
        ' from loot where Valid = 1').fetchall()
    db.close()

    sectors = {}
    months = set()
    skipped = collections.Counter()
    for (sector, surv, ret, fav, ps, as_, pr, ar, fp, pi, pc, phq, ai, ac, ahq, date) in rows:
        if ps not in SURV_PROC or pr not in RET_PROC or fp not in FAV_PROC or not pi:
            skipped['unknown_proc'] += 1
            continue
        sec = sectors.setdefault(str(sector), new_sector())
        months.add(month(date))
        level, tier = SURV_PROC[ps]
        sec['visits'] += 1
        sec['surv'][level] += 1
        sec['tier'][LEVEL_KEY[level]][tier] += 1
        sec['ret'][RET_PROC[pr]] += 1
        sec['fav'][FAV_PROC[fp]] += 1
        widen(sec['stat']['surv'][level], surv)
        widen(sec['stat']['ret'][RET_PROC[pr]], ret)
        widen(sec['stat']['fav'][FAV_PROC[fp]], fav)
        add_drop(sec, pi, pc, phq, ps, pr, 0)
        if ai:
            if as_ not in SURV_PROC or ar not in RET_PROC:
                skipped['unknown_additional_proc'] += 1
                continue
            alevel, atier = SURV_PROC[as_]
            sec['tier_add'][LEVEL_KEY[alevel]][atier] += 1
            add_drop(sec, ai, ac, ahq, as_, ar, 1)

    out_sectors = {}
    for sid in sorted(sectors, key=int):
        sec = sectors[sid]
        items = {t: {iid: sec['items'][t][iid] for iid in sorted(sec['items'][t], key=int)} for t in ('T1', 'T2', 'T3')}
        out_sectors[sid] = {
            'visits': sec['visits'],
            'surv': sec['surv'],
            'tier': {k: [sec['tier'][k][t] for t in TIERS_AT[i]] for i, k in enumerate(LEVEL_KEY)},
            'tier_add': {k: [sec['tier_add'][k][t] for t in TIERS_AT[i]] for i, k in enumerate(LEVEL_KEY)},
            'ret': sec['ret'],
            'fav': sec['fav'],
            'stat': sec['stat'],
            'items': items,
        }

    total = sum(s['visits'] for s in out_sectors.values())
    data = {
        'source': 'SubmarineTracker 本機紀錄彙總(僅次數,無識別資料)',
        'fields': {
            'surv': '主掉落的監視等級次數 [低, 中, 高]',
            'tier': '主掉落各監視等級的 tier 次數(low=[T1], mid=[T1,T2], high=[T1,T2,T3])',
            'tier_add': '第二件(恩惠)同上',
            'ret': '回收等級次數 [差, 普通, 最佳]',
            'fav': '恩惠 [有第二件, 屬性夠但沒觸發, 屬性不足]',
            'items': '依 tier 分組:items.T1[道具 id] = {n, surv, hq, q}',
            'items.n': '[主掉落次數, 第二件次數]',
            'items.surv': '該道具在各監視等級掉落的次數(主+第二件)',
            'items.q': '各回收等級 [次數, 總數量, 最小, 最大](主+第二件)',
            'stat': '各監視等級/回收等級/恩惠結果出現過的屬性值 [最小, 最大]',
        },
        'period': {'from': min(months), 'to': max(months)} if months else {},
        'records': total,
        'sectors': out_sectors,
    }
    if skipped:
        print('略過:', dict(skipped))

    out = Path(args.out)
    body = dumps_one_sector_per_line(data)
    tmp = out.with_suffix('.tmp')
    tmp.write_bytes(body.encode('utf-8'))
    json.loads(tmp.read_bytes().decode('utf-8'))
    os.replace(tmp, out)
    print(f'紀錄 {total} 筆、{len(out_sectors)} 個航點、期間 {data["period"].get("from")}~{data["period"].get("to")} → {out.name}')
    print('TC_LOOT_STATS_DONE')


if __name__ == '__main__':
    main()
