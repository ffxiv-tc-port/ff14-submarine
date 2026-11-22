// 掉落模型(scripts/validate_tc_loot.py 以台服紀錄驗過):依監視等級抽 tier → 依 tier 內佔比抽道具 → 數量取回收等級平均;
// 恩惠達標時以 fp 再抽一件(tier 機率用 hd/md)。低監視只出 T1、中監視 T1/T2、高監視 T1~T3。
// tier 內佔比高監視用 s、低/中監視用 o:低監視的佔比與高監視顯著不同,o 主要由低監視紀錄構成。

import type { ItemInfo, PointInfo, PointLoot, TierKey } from '../types/ff14data';

export const TIER_KEYS: TierKey[] = ['low', 'mid', 'high'];
export const TIER_LABEL: Record<TierKey, string> = { low: 'T1', mid: 'T2', high: 'T3' };
const TIER_INDEX: Record<TierKey, number> = { low: 0, mid: 1, high: 2 };
const SURV_LABEL = ['低監視', '中監視', '高監視'];
const RET_LABEL = ['差', '普通', '最佳'];

/** 配裝在某航點達到的等級;surv/ret:0 低(差)、1 中(普通)、2 高(最佳) */
export interface LootContext {
    surv: number;
    ret: number;
    favor: boolean;
}

/** 與 calcSetStatus 同一套門檻判定;stat 是配裝屬性 [重量, 探索, 收集, 速度, 距離, 恩惠] */
export function contextFor(stat: number[], p: PointInfo): LootContext {
    const sr = p.statReq;
    return {
        surv: stat[1] < sr.surveillance.mid ? 0 : stat[1] < sr.surveillance.high ? 1 : 2,
        ret: stat[2] < sr.retrieval.norm ? 0 : stat[2] < sr.retrieval.optim ? 1 : 2,
        favor: stat[5] >= sr.favor,
    };
}

function tierChance(loot: PointLoot, tier: TierKey, surv: number, second: boolean): number {
    const t = TIER_INDEX[tier];
    if (surv === 0) {
        return t === 0 ? 1 : 0;
    }
    if (surv === 1) {
        return t < 2 ? (second ? loot.md : loot.mp)[t] : 0;
    }
    return (second ? loot.hd : loot.hp)[t];
}

/** 該回收等級沒有數量紀錄時,退到較低等級的平均當下限 */
function quantityAt(q: number[], ret: number): { value: number; lowerBound: boolean } {
    for (let r = ret; r >= 0; r--) {
        if (q[r] > 0) {
            return { value: q[r], lowerBound: r !== ret };
        }
    }
    return { value: 0, lowerBound: false };
}

export interface ItemEstimate {
    tiers: TierKey[]; // 道具在此航點出現的 tier
    known: boolean; // 至少一個 tier 有社群機率;false=只在 CN 清單(可能有)
    primaryHigh: number; // 高監視每趟主掉落機率
    expected: number; // 配裝下每趟期望數量(ctx 為 null 時=0)
    atLeastOne: number; // 配裝下每趟至少拿到一次的機率
    lowerBound: boolean; // 期望數量有用到「較低回收等級的平均」
    quantityUnknown: boolean; // 某個可能掉落的 tier 完全沒有數量紀錄
}

export function itemTiers(p: PointInfo, itemId: number): TierKey[] {
    return TIER_KEYS.filter((t) => p.drop[t].includes(itemId));
}

/** tiers 省略=道具在此航點的所有 tier;只看單一 tier 時傳 [tier] */
export function estimateItem(
    p: PointInfo,
    itemId: number,
    ctx: LootContext | null,
    tiers: TierKey[] = itemTiers(p, itemId),
): ItemEstimate {
    const est: ItemEstimate = {
        tiers,
        known: false,
        primaryHigh: 0,
        expected: 0,
        atLeastOne: 0,
        lowerBound: false,
        quantityUnknown: false,
    };
    const loot = p.loot;
    if (!loot) {
        return est;
    }
    // 主掉落與第二件各是一次抽籤,同道具在兩個 tier 的機率要相加,不是 1-Π(1-p)
    let pPrimaryAll = 0;
    let pSecondAll = 0;
    for (const tier of tiers) {
        const st = loot[tier][itemId];
        if (!st) {
            continue;
        }
        est.known = true;
        est.primaryHigh += tierChance(loot, tier, 2, false) * st.s;
        if (!ctx) {
            continue;
        }
        const share = ctx.surv === 2 ? st.s : st.o;
        const pPrimary = tierChance(loot, tier, ctx.surv, false) * share;
        const pSecond = ctx.favor ? loot.fp * tierChance(loot, tier, ctx.surv, true) * share : 0;
        if (pPrimary + pSecond <= 0) {
            continue;
        }
        pPrimaryAll += pPrimary;
        pSecondAll += pSecond;
        const q = quantityAt(st.q, ctx.ret);
        if (q.value <= 0) {
            est.quantityUnknown = true;
            continue;
        }
        est.lowerBound = est.lowerBound || q.lowerBound;
        est.expected += (pPrimary + pSecond) * q.value;
    }
    est.atLeastOne = ctx ? 1 - (1 - pPrimaryAll) * (1 - pSecondAll) : 0;
    return est;
}

/** 排序與標示用的單一數值:沒配裝=高監視主掉落機率,有配裝=每趟期望數量 */
export function estimateValue(est: ItemEstimate, ctx: LootContext | null): number {
    return ctx ? est.expected : est.primaryHigh;
}

export function formatPercent(x: number): string {
    if (x <= 0) {
        return '0%';
    }
    return x >= 0.1 ? Math.round(x * 100) + '%' : (x * 100).toFixed(1) + '%';
}

/** 滑鼠提示用:一律一位小數,小於 1% 用兩位 */
export function formatPercentFine(x: number): string {
    return x > 0 && x < 0.01 ? (x * 100).toFixed(2) + '%' : (x * 100).toFixed(1) + '%';
}

export function formatQuantity(x: number): string {
    if (x <= 0) {
        return '0';
    }
    return x >= 10 ? x.toFixed(1) : x.toFixed(2);
}

/** 列上顯示的短字串;「不知道」一律看得見(—/?),不畫成 0 */
export function estimateLabel(est: ItemEstimate, ctx: LootContext | null): string {
    if (!est.known) {
        return '—';
    }
    if (!ctx) {
        return formatPercent(est.primaryHigh);
    }
    if (est.quantityUnknown && est.expected <= 0) {
        return '?';
    }
    return (est.lowerBound || est.quantityUnknown ? '≥' : '') + formatQuantity(est.expected);
}

/** 最主要的 tier(主掉落機率最大者),上色用 */
export function dominantTier(p: PointInfo, itemId: number, tiers: TierKey[]): TierKey {
    let best = tiers[0];
    let bestP = -1;
    for (const tier of tiers) {
        const st = p.loot ? p.loot[tier][itemId] : undefined;
        const v = st && p.loot ? tierChance(p.loot, tier, 2, false) * st.s : 0;
        if (v > bestP) {
            best = tier;
            bestP = v;
        }
    }
    return best;
}

/** 滑鼠提示全文:為什麼是這個數字 */
export function describeEstimate(
    p: PointInfo,
    item: ItemInfo,
    ctx: LootContext | null,
    setName: string,
    tiers: TierKey[] = itemTiers(p, item.ID),
): string {
    const lines = [`${p.code} ${p.name}・${item['中文名']}`];
    const loot = p.loot;
    for (const tier of tiers) {
        const st = loot ? loot[tier][item.ID] : undefined;
        const need = tier === 'low' ? '各監視等級都會出' : tier === 'mid' ? '中監視以上' : '僅高監視';
        if (!loot || !st) {
            lines.push(`${TIER_LABEL[tier]}(${need}):社群紀錄沒有這項掉落,只在原作清單中`);
            continue;
        }
        const t = TIER_INDEX[tier];
        lines.push(
            `${TIER_LABEL[tier]}(${need}):高監視 tier 機率 ${formatPercentFine(loot.hp[t])}` +
                `(第二件 ${formatPercentFine(loot.hd[t])})× tier 內佔比 ${formatPercentFine(st.s)}` +
                ` = 每趟主掉落 ${formatPercentFine(loot.hp[t] * st.s)}`,
        );
        if (tier !== 'high') {
            const mid = t < 2 ? `中監視 tier 機率 ${formatPercentFine(loot.mp[t])}(第二件 ${formatPercentFine(loot.md[t])})、` : '';
            lines.push(`  ${mid}低/中監視 tier 內佔比 ${formatPercentFine(st.o)}`);
        }
        lines.push(
            `  平均數量 ${RET_LABEL.map((r, i) => r + ' ' + (st.q[i] > 0 ? st.q[i] : '無紀錄')).join('/')}` +
                `;社群紀錄 ${st.n.toLocaleString()} 筆`,
        );
    }
    if (loot) {
        lines.push(`恩惠達標時出第二件:${formatPercentFine(loot.fp)};本航點社群高監視紀錄 ${loot.gn.toLocaleString()} 筆`);
    }
    if (p.tc) {
        let k = 0;
        for (const tier of tiers) {
            const c = p.tc[tier][item.ID];
            if (c) {
                k += c[0] + c[1] + c[2];
            }
        }
        lines.push(
            `台服紀錄:造訪 ${p.tc.v} 次(低/中/高監視 ${p.tc.sv.join('/')}),拿到 ${k} 次(含第二件)`,
        );
    } else {
        lines.push('台服紀錄:沒有');
    }
    if (ctx) {
        const est = estimateItem(p, item.ID, ctx, tiers);
        const cond = `${SURV_LABEL[ctx.surv]}・${RET_LABEL[ctx.ret]}回收・恩惠${ctx.favor ? '達標' : '未達標'}`;
        let res: string;
        if (!est.known) {
            res = '沒有機率資料';
        } else if (est.atLeastOne <= 0) {
            res = `不會掉(${SURV_LABEL[ctx.surv]}不出${tiers.map((t) => TIER_LABEL[t]).join('/')})`;
        } else if (est.quantityUnknown && est.expected <= 0) {
            res = `每趟至少一個 ${formatPercentFine(est.atLeastOne)};數量沒有紀錄`;
        } else {
            const note = est.lowerBound || est.quantityUnknown ? '(此回收等級缺數量紀錄,以較低等級估算,是下限)' : '';
            res = `每趟期望 ${formatQuantity(est.expected)} 個、至少一個 ${formatPercentFine(est.atLeastOne)}${note}`;
        }
        lines.push(`配裝「${setName}」:${cond} → ${res}`);
    }
    return lines.join('\n');
}
