<template>
    <div class="recommend-block float-layer">
        <div class="float-layer-title">依目標推薦路線</div>
        <div class="recommend-hint" :title="helpTitle"
            >{{ mapName }}・潛艇等級 {{ submarineStore.currentRank }}・從這張地圖挑最多 5 個航點,讓 ☆ 目標道具的期望數量最大
            <i class="fa fa-question-circle" aria-hidden="true"></i
        ></div>
        <template v-if="targetItems.length === 0">
            <p class="muted">還沒有目標:先在「獲得物品」點道具前的 ☆ 把它標成目標。</p>
        </template>
        <template v-else>
            <div class="recommend-targets"
                >目標:<span v-for="item in targetItems" :key="item.ID" class="recommend-target"
                    ><ItemLink :item="item" /></span
            ></div>
            <div class="recommend-controls">
                <select :value="submarineStore.recommendObjective" @change="onObjectiveChange" :title="objectiveTitle">
                    <option value="trip">最大化:每趟期望數量</option>
                    <option value="hour">最大化:每小時期望數量</option>
                </select>
                <select :value="submarineStore.lootBasis" @change="onBasisChange" :title="basisTitle">
                    <option :value="-1">不指定配裝(假設高監視・最佳回收・恩惠達標)</option>
                    <option v-for="(s, i) in submarineStore.sets" :key="i" :value="i">配裝:{{ s.name }}</option>
                </select>
            </div>
            <div class="recommend-conditions muted">{{ conditionText }}</div>

            <table class="wikitable recommend-points">
                <tr
                    ><th :title="excludeTitle"
                        >航點(點一下排除/恢復;未解鎖的請自己排除)<span
                            v-if="excludedHere > 0"
                            class="recommend-reset"
                            @click="clearExcluded"
                            >全部恢復({{ excludedHere }})</span
                        ></th
                    ></tr
                >
                <tr
                    ><td>
                        <ul class="hor-waypoints-list recommend-chips">
                            <li
                                v-for="row in pointRows"
                                :key="row.id"
                                :class="row.state"
                                :title="row.title"
                                @click="toggleExcluded(row)"
                                ><div class="wp">{{ row.code }}</div
                                ><span class="recommend-chip-value">{{ row.label }}</span></li
                            >
                        </ul>
                    </td></tr
                >
            </table>

            <table class="wikitable recommend-results" v-if="result.routes.length > 0">
                <tr>
                    <th style="width: 3em">#</th>
                    <th style="width: 14em">航點(依航行順序)</th>
                    <th style="width: 7em" :class="{ r2: objective === 'trip' }">目標每趟</th>
                    <th style="width: 7em" :class="{ r2: objective === 'hour' }">目標每小時</th>
                    <th style="width: 9em">航行時間</th>
                    <th style="width: 5em">距離</th>
                </tr>
                <tr
                    v-for="(r, i) in routeRows"
                    :key="r.key"
                    class="hover-block"
                    :title="r.title"
                    @click="apply(r.order)"
                >
                    <td>{{ i + 1 }}</td>
                    <td
                        ><ul class="hor-waypoints-list no-hover"
                            ><li v-for="id in r.order" :key="id"
                                ><div class="wp" :class="{ selected: isSelected(id) }">{{
                                    submarineStore.currentWarpoints[id].code
                                }}</div></li
                            ></ul
                        ></td
                    >
                    <td>{{ r.perTripLabel }}</td>
                    <td>{{ r.perHourLabel }}</td>
                    <td>{{ r.timeText }}</td>
                    <td>{{ r.distance }}</td>
                </tr>
            </table>
            <p v-else class="muted">{{ emptyText }}</p>
            <div class="recommend-stats muted" :title="statsTitle">{{ statsText }}</div>
        </template>
        <div class="ff14-btn-group" style="margin-top: 1em">
            <div class="ff14-btn" @click="close">關閉</div>
        </div>
    </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import { findBestRoute } from '../module/findBestRoute';
import { contextFor, formatQuantity } from '../module/loot';
import type { LootContext } from '../module/loot';
import { recommendRoutes, subsetCount, targetValueAt } from '../module/recommendRoute';
import type { RecommendObjective, TargetValue } from '../module/recommendRoute';
import { getRouteTimeCostText } from '../module/routeTimeText';
import { useSubmarineStore } from '../stores/submarine';
import type { ItemInfo, PointInfo } from '../types/ff14data';
import ItemLink from './ItemLink.vue';

const MAX_POINTS = 5;
const TOP_K = 5;
const ASSUMED_CTX: LootContext = { surv: 2, ret: 2, favor: true };

const submarineStore = useSubmarineStore();

const mapName = computed(() =>
    submarineStore.maps[submarineStore.map] ? submarineStore.maps[submarineStore.map].cn : '未知地圖',
);
const objective = computed(() => submarineStore.recommendObjective);
const lootSet = computed(() => submarineStore.lootSet);
const speed = computed(() => (lootSet.value ? lootSet.value.st[3] : submarineStore.speed));
const maxRange = computed(() => (lootSet.value ? lootSet.value.st[4] : Infinity));

const targetItems = computed(() =>
    submarineStore.targets.map((id) => submarineStore.itemDB[id]).filter((x): x is ItemInfo => !!x),
);

function ctxFor(p: PointInfo): LootContext {
    return lootSet.value ? contextFor(lootSet.value.st, p) : ASSUMED_CTX;
}

const helpTitle =
    '從目前地圖挑 1~5 個航點,讓目標道具的期望數量合計最大;每個組合的航行順序與時間和「最短路線情報」相同(時間最短)。' +
    '\n限制:航點等級不超過目前潛艇等級;選了配裝時路線距離不超過配裝的航行距離,並依配裝屬性判監視/回收/恩惠等級。' +
    '\n工具不知道你解鎖了哪些航點:未解鎖的請在下方點一下排除(會記住)。' +
    '\n只有目標期望大於 0 的航點會被考慮(零產出的航點只會拉長時間)。點結果列套用成目前選取。';
const objectiveTitle =
    '每趟:一趟能拿到的目標數量最多。\n每小時:目標數量 ÷ 整趟航行時間(含基礎 12 小時),適合要跑很多趟時比較效率。';
const excludeTitle =
    '工具不知道你解鎖了哪些航點,未解鎖的請自己排除。\n灰色刪除線=已排除;暗灰=潛艇等級不足(自動排除);數字=目標每趟期望,「—」=不掉目標。';
const basisTitle = computed(() =>
    submarineStore.lootBasis >= 0 && !lootSet.value
        ? '這個配裝零件不完整,暫時以「高監視・最佳回收・恩惠達標」估算、不檢查航行距離'
        : '用哪個配裝估算:決定監視/回收等級、恩惠是否達標、航行距離上限與速度(和「獲得物品」的選擇同步)',
);
const conditionText = computed(() =>
    lootSet.value
        ? `配裝「${lootSet.value.n}」:速度 ${lootSet.value.st[3]}、航行距離上限 ${lootSet.value.st[4]}`
        : `未指定配裝:以預覽速度 ${submarineStore.speed} 計時、不檢查航行距離`,
);

interface PointRow {
    id: number;
    code: string;
    label: string;
    state: string;
    title: string;
    tv: TargetValue;
    usable: boolean;
}

const pointRows = computed(() => {
    const rows = [] as PointRow[];
    for (const key in submarineStore.currentWarpoints) {
        const p = submarineStore.currentWarpoints[key];
        const tv = targetValueAt(p, submarineStore.targets, ctxFor(p));
        const locked = p.rankReq > submarineStore.currentRank;
        const excluded = submarineStore.excluded.includes(p.id);
        const label = !tv.drops ? '—' : tv.value <= 0 && tv.partial ? '?' : (tv.partial ? '≥' : '') + formatQuantity(tv.value);
        let state = '';
        let why = '';
        if (locked) {
            state = 'locked';
            why = `需要潛艇等級 ${p.rankReq}(目前 ${submarineStore.currentRank}),自動排除`;
        } else if (excluded) {
            state = 'excluded';
            why = '已排除,點一下恢復';
        } else if (tv.value <= 0) {
            state = 'zero';
            why = tv.drops ? '這個配裝等級下目標期望為 0(或沒有數量紀錄),不列入' : '掉落表沒有目標道具,不列入';
        } else {
            why = '列入候選,點一下排除';
        }
        rows.push({
            id: p.id,
            code: p.code,
            label,
            state,
            tv,
            usable: !locked && !excluded && tv.value > 0,
            title: `${p.code} ${p.name}(等級 ${p.rankReq})\n目標每趟期望:${label}\n${why}`,
        });
    }
    return rows;
});

const excludedHere = computed(
    () => pointRows.value.filter((r) => submarineStore.excluded.includes(r.id)).length,
);

const result = computed(() => {
    const candidates = pointRows.value.filter((r) => r.usable).map((r) => r.id);
    const values = {} as Record<number, number>;
    for (const r of pointRows.value) {
        values[r.id] = r.tv.value;
    }
    if (!submarineStore.startPoint || targetItems.value.length === 0) {
        return { routes: [], evaluated: 0, overRange: 0, pruned: 0, ms: 0, candidates: 0 };
    }
    const out = recommendRoutes({
        start: submarineStore.startPoint,
        points: submarineStore.currentWarpoints,
        candidates,
        values,
        speed: speed.value,
        maxRange: maxRange.value,
        objective: objective.value,
        maxPoints: MAX_POINTS,
        topK: TOP_K,
    });
    return { ...out, candidates: candidates.length };
});

const partialIds = computed(() => pointRows.value.filter((r) => r.tv.partial).map((r) => r.id));

const routeRows = computed(() =>
    result.value.routes.map((r) => {
        // 顯示與套用都以 findBestRoute 為準,和套用後的「最短路線情報」一致
        const best = findBestRoute(r.ids, submarineStore.startPoint!, submarineStore.currentWarpoints);
        const partial = r.ids.some((id) => partialIds.value.includes(id));
        const ge = partial ? '≥' : '';
        const lines = best.routeOrder.map((id) => {
            const row = pointRows.value.find((x) => x.id === id)!;
            return `${row.code} ${submarineStore.currentWarpoints[id].name}:${row.label}`;
        });
        return {
            key: r.ids.join('-'),
            order: best.routeOrder,
            perTripLabel: ge + formatQuantity(r.perTrip) + ' 個',
            perHourLabel: ge + formatRate(r.perHour) + ' 個',
            timeText: getRouteTimeCostText(best.time, speed.value),
            distance: best.distance,
            title: `點一下套用成目前選取(會取代已選航點)\n${lines.join('\n')}` +
                (partial ? '\n「≥」:有航點缺這個回收等級的數量紀錄,以較低等級估算' : ''),
        };
    }),
);

const emptyText = computed(() => {
    if (result.value.candidates === 0) {
        return '沒有可用的航點能拿到目標道具:可能都被排除、潛艇等級不足,或這張地圖不掉這些目標(可換張地圖)。';
    }
    if (result.value.overRange === result.value.evaluated) {
        return `所有組合都超過配裝的航行距離 ${maxRange.value}。`;
    }
    return '沒有結果。';
});

const statsText = computed(() => {
    const r = result.value;
    const range = r.overRange > 0 ? `,${r.overRange.toLocaleString()} 組超過航行距離` : '';
    const pruned = r.pruned > 0 ? `,剪掉 ${r.pruned.toLocaleString()} 個不可能更好的分支` : '';
    return `候選 ${r.candidates} 個航點、評估 ${r.evaluated.toLocaleString()} 組${range}${pruned}、耗時 ${r.ms.toFixed(1)} ms`;
});
const statsTitle = computed(
    () =>
        `組合數 = Σ C(候選數, k),k=1~5;這張地圖 ${pointRows.value.length} 個航點全列入時最多 ` +
        `${subsetCount(pointRows.value.length, MAX_POINTS).toLocaleString()} 組。`,
);

/** 每小時的數字通常小於 1,兩位小數分不出名次 */
function formatRate(x: number) {
    return x >= 1 ? formatQuantity(x) : x.toFixed(3);
}

function isSelected(id: number) {
    return submarineStore.selected.includes(id);
}
function toggleExcluded(row: PointRow) {
    if (row.state !== 'locked') {
        submarineStore.toggleExcluded(row.id);
    }
}
function clearExcluded() {
    submarineStore.clearExcluded(pointRows.value.map((r) => r.id));
}
function apply(order: number[]) {
    submarineStore.setSelected(order);
    submarineStore.setLayer(0);
}
function onObjectiveChange(e: Event) {
    submarineStore.setRecommendObjective((e.target as HTMLSelectElement).value as RecommendObjective);
}
function onBasisChange(e: Event) {
    submarineStore.setLootBasis(Number((e.target as HTMLSelectElement).value));
}
function close() {
    submarineStore.setLayer(0);
}
</script>

<style lang="less">
.recommend-block {
    .muted {
        color: #8a8a8a;
    }

    .recommend-hint {
        margin: 0.5em 0;
        color: #8a8a8a;
        font-size: 12px;
        cursor: help;
    }

    .recommend-target + .recommend-target {
        margin-left: 0.8em;
    }

    .recommend-controls {
        display: flex;
        gap: 0.3em;
        margin: 0.5em 0 0.3em;

        select {
            flex: 1;
            min-width: 0;
            border: 1px solid #555;
            background: #191313;
            color: #efefef;
            font-size: 12px;
        }
    }

    .recommend-conditions,
    .recommend-stats {
        margin-bottom: 0.5em;
        font-size: 12px;
    }

    table.recommend-points,
    table.recommend-results {
        width: 100% !important;
        margin-bottom: 0.5em;
    }

    .recommend-reset {
        float: right;
        color: #77d1ff;
        font-weight: normal;
        font-size: 12px;
        cursor: pointer;
    }

    .recommend-chips {
        > li {
            margin-right: 0.4em !important;
            cursor: pointer;
        }

        .recommend-chip-value {
            margin-left: 2px;
            color: #fc3;
            font-size: 11px;
        }

        li.zero {
            opacity: 0.45;

            .recommend-chip-value {
                color: #8a8a8a;
            }
        }

        li.excluded {
            text-decoration: line-through;
            opacity: 0.45;
        }

        li.locked {
            opacity: 0.25;
            cursor: not-allowed;
        }
    }
}
</style>
