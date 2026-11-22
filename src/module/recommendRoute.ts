// 依目標推薦路線:從一張地圖挑 1~maxPoints 個航點,讓目標道具的期望數量(每趟或每小時)最大。
// 契約:每個組合的航行時間/距離 = findBestRoute 會選的順序(時間最短,同時間取距離短),不含回程;
// 航點的期望數量只看航點本身與配裝等級,與順序無關,所以組合的期望 = 各航點相加。

import type { PointInfo } from '../types/ff14data';
import { estimateItem } from './loot';
import type { LootContext } from './loot';
import { routeMinutes } from './routeTimeText';

export type RecommendObjective = 'trip' | 'hour';

export interface TargetValue {
    value: number; // 目標道具每趟期望數量合計
    partial: boolean; // 有用到較低回收等級的平均或缺數量紀錄(是下限)
    drops: boolean; // 掉落表上至少有一個目標
}

export function targetValueAt(p: PointInfo, targets: number[], ctx: LootContext): TargetValue {
    const out: TargetValue = { value: 0, partial: false, drops: false };
    for (const itemId of targets) {
        const est = estimateItem(p, itemId, ctx);
        if (est.tiers.length === 0) {
            continue;
        }
        out.drops = true;
        out.value += est.expected;
        out.partial = out.partial || est.lowerBound || est.quantityUnknown;
    }
    return out;
}

export interface RecommendInput {
    start: PointInfo;
    points: Record<number, PointInfo>;
    candidates: number[]; // 只放期望 > 0 的航點;零產出的航點對兩種目標都只會拉長時間
    values: Record<number, number>;
    speed: number;
    maxRange: number; // 沒有配裝時傳 Infinity
    objective: RecommendObjective;
    maxPoints: number;
    topK: number;
    prune?: boolean; // 預設 true;false 只用來量最壞情況與對照
}

export interface RecommendRoute {
    ids: number[]; // 組合(依候選順序,不是航行順序)
    perTrip: number;
    perHour: number;
    score: number;
    time: number; // 與 routeInfo.time 同單位
    distance: number;
}

export interface RecommendOutput {
    routes: RecommendRoute[];
    evaluated: number; // 評估過的組合數
    overRange: number; // 因超過航續距離被剔除的組合數
    pruned: number; // 被上界剪掉的子樹數
    ms: number;
}

/**
 * 組合依序擴張(i1<i2<...),位置遮罩上的 Held-Karp 增量更新:深度 p 只重算含位置 p 的遮罩,其餘沿用祖先。
 * 剪枝:候選依期望由大到小排,子樹上界 = 目前合計 + 後面最大的幾個;每小時目標再除以目前時間
 * (每個航點勘查時間 ≥ 1 時,加航點不會讓最短時間變短,floor 誤差每段最多 1)。
 */
export function recommendRoutes(input: RecommendInput): RecommendOutput {
    const t0 = performance.now();
    const ids = input.candidates.slice().sort((a, b) => input.values[b] - input.values[a] || a - b);
    const n = ids.length;
    const K = Math.min(input.maxPoints, n);
    const startT = new Float64Array(n);
    const startD = new Float64Array(n);
    const surT = new Float64Array(n);
    const surD = new Float64Array(n);
    const edgeT = new Float64Array(n * n);
    const edgeD = new Float64Array(n * n);
    const val = new Float64Array(n);
    for (let i = 0; i < n; i++) {
        const p = input.points[ids[i]];
        startT[i] = input.start.toDestination[ids[i]].distance;
        startD[i] = input.start.toDestination[ids[i]].range;
        surT[i] = p.surveyDistance;
        surD[i] = p.surveyRange;
        val[i] = input.values[ids[i]];
        for (let j = 0; j < n; j++) {
            if (i !== j) {
                edgeT[i * n + j] = p.toDestination[ids[j]].distance;
                edgeD[i * n + j] = p.toDestination[ids[j]].range;
            }
        }
    }

    const prefix = new Float64Array(n + 1);
    let monotoneTime = true;
    for (let i = 0; i < n; i++) {
        prefix[i + 1] = prefix[i] + val[i];
        monotoneTime = monotoneTime && surT[i] >= 1;
    }
    const canPrune = input.prune !== false && (input.objective === 'trip' || monotoneTime);

    const W = 1 << Math.max(K, 1);
    const dpT = new Float64Array(W * K);
    const dpD = new Float64Array(W * K);
    const stack = new Int32Array(K);
    const top: RecommendRoute[] = [];
    let evaluated = 0;
    let overRange = 0;
    let pruned = 0;

    const better = (a: RecommendRoute, b: RecommendRoute) =>
        a.score !== b.score ? a.score > b.score : a.time !== b.time ? a.time < b.time : a.ids.length < b.ids.length;

    function offer(depth: number, total: number, t: number, d: number) {
        evaluated++;
        if (d > input.maxRange) {
            overRange++;
            return;
        }
        const perHour = total / (routeMinutes(t, input.speed) / 60);
        const score = input.objective === 'trip' ? total : perHour;
        if (top.length >= input.topK) {
            const worst = top[top.length - 1];
            if (score < worst.score || (score === worst.score && t >= worst.time)) {
                return;
            }
        }
        const r: RecommendRoute = {
            ids: Array.from(stack.subarray(0, depth + 1), (i) => ids[i]),
            perTrip: total,
            perHour,
            score,
            time: t,
            distance: d,
        };
        let pos = top.length;
        while (pos > 0 && better(r, top[pos - 1])) {
            pos--;
        }
        top.splice(pos, 0, r);
        if (top.length > input.topK) {
            top.pop();
        }
    }

    function dfs(depth: number, from: number, sum: number) {
        const bit = 1 << depth;
        for (let x = from; x < n; x++) {
            stack[depth] = x;
            // 遞增走訪低位子遮罩:m 去掉非 p 的一位後仍含 p 且數值更小,已先算好
            for (let sub = 0; sub < bit; sub++) {
                const m = sub | bit;
                for (let j = 0; j <= depth; j++) {
                    if (!(m & (1 << j))) {
                        continue;
                    }
                    const xj = stack[j];
                    const idx = m * K + j;
                    if (m === 1 << j) {
                        dpT[idx] = startT[xj] + surT[xj];
                        dpD[idx] = startD[xj] + surD[xj];
                        continue;
                    }
                    const pm = m ^ (1 << j);
                    let bt = Infinity;
                    let bd = Infinity;
                    for (let i = 0; i <= depth; i++) {
                        if (!(pm & (1 << i))) {
                            continue;
                        }
                        const e = stack[i] * n + xj;
                        const tt = dpT[pm * K + i] + edgeT[e];
                        const dd = dpD[pm * K + i] + edgeD[e];
                        if (tt < bt || (tt === bt && dd < bd)) {
                            bt = tt;
                            bd = dd;
                        }
                    }
                    dpT[idx] = bt + surT[xj];
                    dpD[idx] = bd + surD[xj];
                }
            }
            const full = (bit << 1) - 1;
            let bt = Infinity;
            let bd = Infinity;
            for (let j = 0; j <= depth; j++) {
                const tt = dpT[full * K + j];
                const dd = dpD[full * K + j];
                if (tt < bt || (tt === bt && dd < bd)) {
                    bt = tt;
                    bd = dd;
                }
            }
            const total = sum + val[x];
            offer(depth, total, bt, bd);
            if (depth + 1 >= K) {
                continue;
            }
            if (canPrune && top.length >= input.topK) {
                const best = total + prefix[Math.min(n, x + K - depth)] - prefix[x + 1];
                const bound = input.objective === 'trip' ? best : best / (routeMinutes(bt, input.speed) / 60);
                if (bound * (1 + 1e-9) < top[top.length - 1].score) {
                    pruned++;
                    continue;
                }
            }
            dfs(depth + 1, x + 1, total);
        }
    }

    if (n > 0) {
        dfs(0, 0, 0);
    }
    return { routes: top, evaluated, overRange, pruned, ms: performance.now() - t0 };
}

/** 最壞情況的組合數 Σ C(n,k), k=1..maxPoints */
export function subsetCount(n: number, maxPoints: number): number {
    let total = 0;
    let c = 1;
    for (let k = 1; k <= Math.min(maxPoints, n); k++) {
        c = (c * (n - k + 1)) / k;
        total += c;
    }
    return total;
}
