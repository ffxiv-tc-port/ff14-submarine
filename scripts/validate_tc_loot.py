# -*- coding: utf-8 -*-
"""台服紀錄彙總(tc_loot_stats.json)對全球社群試算表(gs_items.csv / gs_sectors.csv)的交叉驗證。

用法:python scripts/validate_tc_loot.py [--min-n 30] [--markdown]
只讀 repo 內的檔案(彙總、社群快照、public/data.js);輸出驗證表到 stdout,收工行 VALIDATE_TC_LOOT_DONE。
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'scripts' / 'data'


def load_data_js():
    s = (ROOT / 'public' / 'data.js').read_bytes().decode('utf-8')
    inner = s[s.index(chr(39)) + 1: s.rindex(chr(39))]
    return json.loads(inner.replace(chr(92) + chr(39), chr(39)).replace(chr(92) * 2, chr(92)))


def pct(x):
    x = (x or '').strip()
    return float(x.rstrip('%')) / 100 if x.endswith('%') else None


def gammaincc(a, x):
    """正規化上不完全 gamma Q(a, x)(級數/連分數,Numerical Recipes 6.2)。"""
    if x <= 0:
        return 1.0
    gln = math.lgamma(a)
    if x < a + 1:
        ap, s, d = a, 1.0 / a, 1.0 / a
        for _ in range(500):
            ap += 1
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-14:
                break
        return 1.0 - s * math.exp(-x + a * math.log(x) - gln)
    b = x + 1 - a
    c, d = 1.0 / 1e-300, 1.0 / b
    h = d
    for i in range(1, 500):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = 1e-300 if abs(d) < 1e-300 else d
        c = b + an / c
        c = 1e-300 if abs(c) < 1e-300 else c
        d = 1.0 / d
        h *= d * c
        if abs(d * c - 1) < 1e-14:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def chi2_sf(x2, df):
    return gammaincc(df / 2, x2 / 2) if df > 0 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-n', type=int, default=30)
    args = ap.parse_args()

    d = load_data_js()
    pts = {p['id']: p for p in d['point_data']}
    name = {int(k): v['中文名'] for k, v in d['item_db'].items()}
    en_maps = [x['en'] for x in d['sea_name_map']]
    en2id = json.loads((DATA / 'item_en_to_id.json').read_text(encoding='utf-8'))
    tc = json.loads((DATA / 'tc_loot_stats.json').read_text(encoding='utf-8'))

    rows = list(csv.reader(open(DATA / 'gs_sectors.csv', encoding='utf-8')))
    hdr = {k: i for i, k in enumerate(rows[0])}
    gsec = {(r[2].strip(), r[1].strip()): r for r in rows[1:] if len(r) > 2 and r[0].strip()}
    gitems = {}
    irows = list(csv.reader(open(DATA / 'gs_items.csv', encoding='utf-8')))
    ih = {k: i for i, k in enumerate(irows[0])}
    for r in irows[1:]:
        if len(r) > 8 and r[0].strip() and r[2].strip():
            key = (r[0].strip(), r[1].strip())
            gitems.setdefault(key, {})[(en2id[r[2].strip().lower()], r[3].strip())] = r  # 同道具可在兩個 tier

    def label(sid):
        p = pts[int(sid)]
        return f"[{sid}] {d['sea_name_map'][p['map'] - 1]['cn']} {p['code']} {p['name']}"

    def gs_row(sid):
        p = pts[int(sid)]
        return gsec[(en_maps[p['map'] - 1], p['code'])]

    def gs_items_of(sid):
        r = gs_row(sid)
        return gitems.get((r[0].strip(), r[1].strip()), {})

    print(f"台服紀錄:{tc['records']} 筆、{len(tc['sectors'])} 航點、{tc['period']['from']}~{tc['period']['to']}")

    # ---- 1. 門檻:各等級實際出現的屬性值是否落在 data.js 門檻內 ----
    print('\n## 門檻一致性(台服實際屬性值 vs data.js statReq)')
    bad = 0
    for sid, s in tc['sectors'].items():
        sr = pts[int(sid)]['statReq']
        lo = [None, sr['surveillance']['mid'], sr['surveillance']['high']]
        for lvl, rng in enumerate(s['stat']['surv']):
            if rng and ((lvl > 0 and rng[0] < lo[lvl]) or (lvl < 2 and rng[1] >= lo[lvl + 1])):
                bad += 1
                print(f'  監視 {label(sid)} 等級{lvl} 屬性 {rng} 門檻 {lo[1:]}')
        rl = [None, sr['retrieval']['norm'], sr['retrieval']['optim']]
        for lvl, rng in enumerate(s['stat']['ret']):
            if rng and ((lvl > 0 and rng[0] < rl[lvl]) or (lvl < 2 and rng[1] >= rl[lvl + 1])):
                bad += 1
                print(f'  回收 {label(sid)} 等級{lvl} 屬性 {rng} 門檻 {rl[1:]}')
        fv = s['stat']['fav']
        for k in (0, 1):
            if fv[k] and fv[k][0] < sr['favor']:
                bad += 1
                print(f"  恩惠 {label(sid)} {'觸發' if k == 0 else '屬性夠沒觸發'} 屬性 {fv[k]} < 門檻 {sr['favor']}"
                      f"(社群 BP {gs_row(sid)[hdr['Favor BP']]})")
        if fv[2] and fv[2][1] >= sr['favor']:
            bad += 1
            print(f"  恩惠 {label(sid)} 屬性不足卻有 {fv[2]} >= 門檻 {sr['favor']}")
    print(f'  不一致 {bad} 處')

    # ---- 2. 高監視 tier 比例 ----
    print('\n## 高監視 tier 比例(主掉落;社群 FD = 主掉落)')
    print('| 航點 | n | 台服 T1/T2/T3 | 社群 T1/T2/T3 | 最大偏差(標準誤) |')
    print('|---|---|---|---|---|')
    for sid, s in sorted(tc['sectors'].items(), key=lambda kv: -sum(kv[1]['tier']['high'])):
        n = sum(s['tier']['high'])
        if n < args.min_n:
            continue
        r = gs_row(sid)
        g = [pct(r[hdr[f'T{t} FD high surv proc']]) for t in (1, 2, 3)]
        o = [c / n for c in s['tier']['high']]
        z = max(((o[i] - g[i]) / math.sqrt(g[i] * (1 - g[i]) / n) for i in range(3)), key=abs)
        print(f"| {label(sid)} | {n} | {'/'.join(f'{x:.1%}' for x in o)} | {'/'.join(f'{x:.1%}' for x in g)} | {z:+.1f} |")

    print('\n## 第二件(恩惠)高監視 tier 比例(社群 DD)')
    print('| 航點 | n | 台服 T1/T2/T3 | 社群 T1/T2/T3 | 最大偏差(標準誤) |')
    print('|---|---|---|---|---|')
    for sid, s in sorted(tc['sectors'].items(), key=lambda kv: -sum(kv[1]['tier_add']['high'])):
        n = sum(s['tier_add']['high'])
        if n < args.min_n:
            continue
        r = gs_row(sid)
        g = [pct(r[hdr[f'T{t} DD high surv proc']]) for t in (1, 2, 3)]
        o = [c / n for c in s['tier_add']['high']]
        z = max(((o[i] - g[i]) / math.sqrt(g[i] * (1 - g[i]) / n) for i in range(3)), key=abs)
        print(f"| {label(sid)} | {n} | {'/'.join(f'{x:.1%}' for x in o)} | {'/'.join(f'{x:.1%}' for x in g)} | {z:+.1f} |")

    # ---- 3. 恩惠觸發率(屬性達標時) ----
    print('\n## 恩惠觸發率(屬性達標的趟次)')
    print('| 航點 | 達標 n | 台服 | 社群 | 偏差(標準誤) |')
    print('|---|---|---|---|---|')
    tot_yes = tot_elig = 0
    for sid, s in sorted(tc['sectors'].items(), key=lambda kv: -(kv[1]['fav'][0] + kv[1]['fav'][1])):
        n = s['fav'][0] + s['fav'][1]
        tot_yes += s['fav'][0]
        tot_elig += n
        if n < args.min_n:
            continue
        g = pct(gs_row(sid)[hdr['Favor proc chance']])
        o = s['fav'][0] / n
        z = (o - g) / math.sqrt(g * (1 - g) / n)
        print(f'| {label(sid)} | {n} | {o:.1%} | {g:.1%} | {z:+.1f} |')
    print(f'  全部達標趟次:{tot_yes}/{tot_elig} = {tot_yes / max(tot_elig, 1):.1%}')

    # ---- 4. tier 內道具佔比卡方 ----
    print(f'\n## tier 內道具佔比(主+第二件、全監視等級合併;n>={args.min_n})')
    tests = []
    unexpected = []
    tier_mismatch = []
    for sid, s in tc['sectors'].items():
        gi = gs_items_of(sid)
        by_tier = {}
        for t, tier_items in s['items'].items():
            for iid, it in tier_items.items():
                iid_i = int(iid)
                k = sum(it['n'])
                if (iid_i, t) not in gi:
                    (tier_mismatch if any(i == iid_i for i, _ in gi) else unexpected).append((sid, iid_i, t, k))
                    continue
                by_tier.setdefault(t, {})[iid_i] = k
        for t, cnt in by_tier.items():
            n = sum(cnt.values())
            exp = {i: pct(r[ih['Overall drop chance (within tier)']]) for (i, rt), r in gi.items() if rt == t}
            if n < args.min_n or len(exp) < 2:
                continue
            x2 = 0.0
            worst = None
            for i, sh in exp.items():
                e = n * sh
                o = cnt.get(i, 0)
                x2 += (o - e) ** 2 / e
                dev = (o - e) / math.sqrt(e)
                if worst is None or abs(dev) > abs(worst[1]):
                    worst = (i, dev, o, e)
            tests.append((chi2_sf(x2, len(exp) - 1), sid, t, n, x2, len(exp) - 1, worst))
    tests.sort()
    m = len(tests)
    print(f'  檢定 {m} 組;p<0.05 {sum(1 for t in tests if t[0] < 0.05)} 組、p<0.01 {sum(1 for t in tests if t[0] < 0.01)} 組'
          f'(全為真時期望約 {m * 0.05:.1f} / {m * 0.01:.1f} 組)')
    for rank, (p, sid, t, n, x2, df, w) in enumerate(tests):
        holm = min(1.0, p * (m - rank))
        if p < 0.01:
            print(f'  {label(sid)} {t} n={n} X2={x2:.1f} df={df} p={p:.4f} Holm={holm:.3f}'
                  f' 最偏:{name.get(w[0], w[0])} 觀測 {w[2]} 期望 {w[3]:.1f}')
    print(f'  社群表沒有的道具:{len(unexpected)} 筆 {unexpected[:10]}')
    print(f'  社群表有此道具、但不在這個 tier:{len(tier_mismatch)} 筆 {tier_mismatch[:10]}')

    # ---- 5. 平均數量(最佳回收) ----
    print('\n## 平均數量(最佳回收,台服 n>=20 的道具)')
    print('| 航點 | 道具 | 台服 n | 台服平均 | 社群平均 | 台服範圍 | 社群範圍 |')
    print('|---|---|---|---|---|---|---|')
    qdev = []
    for sid, s in sorted(tc['sectors'].items(), key=lambda kv: -kv[1]['visits']):
        gi = gs_items_of(sid)
        for t, iid, it in ((t, iid, it) for t, ti in s['items'].items() for iid, it in ti.items()):
            q = it['q'][2]
            r = gi.get((int(iid), t))
            if q[0] < 20 or not r:
                continue
            ga = float(r[ih['Optimal avg']])
            ta = q[1] / q[0]
            outside = q[2] < int(r[ih['Optimal min']]) or q[3] > int(r[ih['Optimal max']])
            qdev.append((abs(ta - ga) / ga, outside))
            if outside or abs(ta - ga) / ga > 0.1:
                print(f"| {label(sid)} | {name.get(int(iid))} {t} | {q[0]} | {ta:.2f} | {ga:.2f} | {q[2]}~{q[3]} | "
                      f"{r[ih['Optimal min']]}~{r[ih['Optimal max']]} |")
    if qdev:
        print(f'  比較 {len(qdev)} 組;平均相對差 {sum(x for x, _ in qdev) / len(qdev):.1%};'
              f'範圍超出社群 min~max {sum(1 for _, o in qdev if o)} 組;相差 >10% {sum(1 for x, _ in qdev if x > 0.1)} 組')
    # ---- 6. tier 內佔比該用哪一欄:各監視等級分開,對「高監視佔比」與「整體佔比」各算合併卡方 ----
    print('\n## tier 內佔比的監視等級相依性(台服各監視等級觀測 vs 社群兩種佔比)')
    print('| 監視等級 | 組數 | 自由度 | X2(高監視佔比) | p | X2(整體佔比) | p |')
    print('|---|---|---|---|---|---|---|')
    for lvl, lname in ((0, '低'), (1, '中'), (2, '高')):
        x2 = {'s': 0.0, 'o': 0.0}
        groups = dof = 0
        for sid, s in tc['sectors'].items():
            gi = gs_items_of(sid)
            for t, tier_items in s['items'].items():
                cnt = {int(i): it['surv'][lvl] for i, it in tier_items.items()}
                n = sum(cnt.values())
                exp = {i: r for (i, rt), r in gi.items() if rt == t}
                if n < 20 or len(exp) < 2:
                    continue
                groups += 1
                dof += len(exp) - 1
                for key, col in (('s', 'High surv drop chance (within tier)'), ('o', 'Overall drop chance (within tier)')):
                    for i, r in exp.items():
                        e = n * pct(r[ih[col]])
                        if e > 0:
                            x2[key] += (cnt.get(i, 0) - e) ** 2 / e
        if groups:
            print(f"| {lname} | {groups} | {dof} | {x2['s']:.1f} | {chi2_sf(x2['s'], dof):.3g} | {x2['o']:.1f} | {chi2_sf(x2['o'], dof):.3g} |")
    print('VALIDATE_TC_LOOT_DONE')


if __name__ == '__main__':
    main()
