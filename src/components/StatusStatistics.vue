<template>
    <div class="statistics-block">
        <table class="statistics-table wikitable">
            <tr><th :colspan="7">最短路線情報</th></tr>
            <template v-if="submarineStore.selected.length > 0">
                <tr>
                    <th>目的地順序</th>
                    <td :colspan="4">
                        <ul class="hor-waypoints-list">
                            <li
                                v-for="wp_id in submarineStore.routeInfo.routeOrder"
                                :key="wp_id"
                                @click="toggleWP(wp_id)"
                            >
                                <div class="wp selected">{{ submarineStore.currentWarpoints[wp_id].code }}</div>
                            </li>
                            <li v-if="submarineStore.selected.length < 5">
                                <div class="wp btn-red" @click="layerAddWP"
                                    ><i class="fa fa-plus" aria-hidden="true"></i
                                ></div>
                            </li>
                        </ul>
                    </td>
                    <th>最大探索需求</th>
                    <td class="r2">{{ submarineStore.routeInfo.max_surveillance }}</td>
                </tr>
                <tr>
                    <th>航行距離</th>
                    <td :colspan="2">{{ submarineStore.routeInfo.distance }}</td>
                    <th>預覽速度</th>
                    <td
                        >{{ submarineStore.speed }}
                        <i class="fa fa-pencil-square btn-red" aria-hidden="true" @click="layerSetSpeed"></i
                    ></td>
                    <th>最大收集需求</th>
                    <td class="r2">{{ submarineStore.routeInfo.max_retrieval }}</td>
                </tr>
                <tr>
                    <th>航行時間預覽</th>
                    <td :colspan="2">{{ routeTimeCostText }}</td>
                    <th>回歸時間</th>
                    <td>{{ routeRealTimeText }}</td>
                    <th>最大恩惠需求</th>
                    <td class="r2">{{ submarineStore.routeInfo.max_favor }}</td>
                </tr>
                <tr>
                    <th :title="targetHeadTitle">目標物品</th>
                    <td :colspan="6" class="route-targets">
                        <template v-if="targetSummary.length > 0">
                            <span v-for="t in targetSummary" :key="t.item.ID" class="route-target" :title="t.title"
                                ><ItemLink :item="t.item" /><span class="route-target-value" :class="{ possible: !t.known }">{{
                                    t.label
                                }}</span></span
                            >
                        </template>
                        <span v-else class="muted">在「獲得物品」點道具前的 ☆ 標成目標,這裡會列出目前路線每趟的期望</span>
                    </td>
                </tr>
                <tr>
                    <th :colspan="7">沿途目的地情報</th>
                </tr>
                <tr>
                    <th style="width: 16%">目的地</th>
                    <th style="width: 9%">探索需求</th>
                    <th style="width: 9%">收集需求</th>
                    <th style="width: 9%">恩惠需求</th>
                    <th style="width: 19%">探索物品<span class="r0">(低)</span></th>
                    <th style="width: 19%">探索物品<span class="r1">(中)</span></th>
                    <th style="width: 19%">探索物品<span class="r2">(高)</span></th>
                </tr>
                <tr v-for="w in submarineStore.routeInfo.routeOrder" v-bind:key="w">
                    <td>{{
                        submarineStore.currentWarpoints[w].code + ' ' + submarineStore.currentWarpoints[w].name
                    }}</td>
                    <td style="text-align: center"
                        ><span class="r1">{{ submarineStore.currentWarpoints[w].statReq.surveillance.mid }}</span
                        >&nbsp;/&nbsp;<span class="r2">{{
                            submarineStore.currentWarpoints[w].statReq.surveillance.high
                        }}</span></td
                    >
                    <td style="text-align: center"
                        ><span class="r1">{{ submarineStore.currentWarpoints[w].statReq.retrieval.norm }}</span
                        >&nbsp;/&nbsp;<span class="r2">{{
                            submarineStore.currentWarpoints[w].statReq.retrieval.optim
                        }}</span></td
                    >
                    <td style="text-align: center"
                        ><span class="r2">{{ submarineStore.currentWarpoints[w].statReq.favor }}</span></td
                    >
                    <td v-for="tier in TIER_KEYS" :key="tier"
                        ><div
                            v-for="cell in tierCells(w, tier)"
                            :key="tier + cell.id"
                            class="route-drop"
                            :class="{ possible: !cell.known }"
                            :title="cell.title"
                            ><ItemLink :item="submarineStore.itemDB[cell.id]" /><span class="route-drop-value">{{
                                cell.label
                            }}</span></div
                        ></td
                    >
                </tr>
            </template>
            <tr v-else><td :colspan="7">請選擇希望探索的目的地</td></tr>
        </table>
    </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import {
    TIER_KEYS,
    contextFor,
    describeEstimate,
    estimateItem,
    estimateLabel,
    estimateValue,
    formatQuantity,
    itemTiers,
} from '../module/loot';
import type { LootContext } from '../module/loot';
import { getRouteRealTimeText, getRouteTimeCostText } from '../module/routeTimeText';
import { useSubmarineStore } from '../stores/submarine';
import type { ItemInfo, PointInfo, TierKey } from '../types/ff14data';
import ItemLink from './ItemLink.vue';

const submarineStore = useSubmarineStore();

const routeTimeCostText = computed(() => getRouteTimeCostText(submarineStore.routeInfo.time, submarineStore.speed));

const routeRealTimeText = computed(() =>
    getRouteRealTimeText(submarineStore.startRealTime, submarineStore.routeInfo.time, submarineStore.speed),
);

const lootSet = computed(() => submarineStore.lootSet);
const setName = computed(() => (lootSet.value ? lootSet.value.n : ''));

function ctxFor(p: PointInfo): LootContext | null {
    return lootSet.value ? contextFor(lootSet.value.st, p) : null;
}

/** 沿途目的地情報的單一 tier 欄:每個道具在該 tier 的機率或期望數量 */
function tierCells(point_id: number, tier: TierKey) {
    const p = submarineStore.currentWarpoints[point_id];
    const ctx = ctxFor(p);
    return p.drop[tier].map((id) => {
        const est = estimateItem(p, id, ctx, [tier]);
        return {
            id,
            known: est.known,
            label: estimateLabel(est, ctx),
            title: describeEstimate(p, submarineStore.itemDB[id], ctx, setName.value, [tier]),
        };
    });
}

const targetHeadTitle = computed(() =>
    lootSet.value
        ? `配裝「${setName.value}」跑目前路線,每趟可得目標道具的期望數量(各航點相加,含恩惠第二件)`
        : '目前路線上,目標道具在高監視時成為主掉落的期望次數(各航點機率相加);選了配裝會改成期望數量',
);

interface TargetSummary {
    item: ItemInfo;
    label: string;
    known: boolean;
    title: string;
}

const targetSummary = computed(() => {
    const out = [] as TargetSummary[];
    for (const itemId of submarineStore.targets) {
        const item = submarineStore.itemDB[itemId];
        if (!item) {
            continue;
        }
        let total = 0;
        let onRoute = false;
        let known = false;
        let partial = false;
        const lines = [] as string[];
        for (const wp_id of submarineStore.routeInfo.routeOrder) {
            const p = submarineStore.currentWarpoints[wp_id];
            if (itemTiers(p, itemId).length === 0) {
                continue;
            }
            onRoute = true;
            const ctx = ctxFor(p);
            const est = estimateItem(p, itemId, ctx);
            known = known || est.known;
            partial = partial || est.lowerBound || est.quantityUnknown;
            total += est.known ? estimateValue(est, ctx) : 0;
            lines.push(`${p.code} ${p.name}:${estimateLabel(est, ctx)}`);
        }
        if (!onRoute) {
            out.push({ item, label: '路線上不會掉', known: false, title: '目前路線的航點掉落表都沒有這個道具' });
            continue;
        }
        const label = !known
            ? '—'
            : lootSet.value
            ? `${partial ? '≥' : ''}${formatQuantity(total)} 個`
            : `${formatQuantity(total)} 次`;
        out.push({ item, label, known, title: `${targetHeadTitle.value}\n${lines.join('\n')}` });
    }
    return out;
});

function layerAddWP() {
    submarineStore.setLayer(4);
}

function layerSetSpeed() {
    submarineStore.setLayer(3);
}

function toggleWP(point_id: number) {
    submarineStore.toggleWaypoint(point_id);
}
</script>

<style lang="less">
.statistics-block {
    margin-top: 1.5em;

    .route-drop-value,
    .route-target-value {
        margin-left: 0.3em;
        color: #8a8a8a;
        font-size: 11px;
    }

    .route-target-value {
        color: #fc3;
    }

    .route-target + .route-target {
        margin-left: 1em;
    }

    .possible {
        opacity: 0.45;
    }

    .muted {
        color: #8a8a8a;
    }
}
</style>
