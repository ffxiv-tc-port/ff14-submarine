<template>
    <div class="waypoint-block">
        <div class="explore-list">
            <table class="wikitable">
                <tr><th>探索地點</th></tr>
                <template v-for="p in currentWarpoints" :key="p.id">
                    <tr
                        ><td class="waypoint" :class="{ selected: isSelect(p.id) }"
                            ><div @click="toggleWP(p.id)"
                                ><i class="fa fa-check" aria-hidden="true" v-if="isSelect(p.id)"></i>
                                {{ p.code + ' ' + p.name }}
                                <span
                                    v-if="targetValues[p.id]"
                                    class="target-value"
                                    :class="{ possible: !targetValues[p.id].known }"
                                    :title="targetValues[p.id].title"
                                    >{{ targetValues[p.id].label }}</span
                                ></div
                            ></td
                        ></tr
                    >
                </template>
            </table>
        </div>
        <div class="explore-map">
            <table class="wikitable">
                <tr
                    ><th :colspan="2">{{ map_name }}</th></tr
                >
            </table>
            <div class="sea-map" :class="'map' + submarineStore.map">
                <div
                    class="base wp"
                    :style="{
                        left: submarineStore.startPoint!.x / 3 + 'px',
                        top: submarineStore.startPoint!.y / 3 + 'px',
                    }"
                ></div>
                <div
                    v-for="p in currentWarpoints"
                    class="wp"
                    :class="{ selected: isSelect(p.id), 'has-target': hasTargetValue(p.id) }"
                    :key="p.id"
                    @click="toggleWP(p.id)"
                    :title="targetValues[p.id] ? targetValues[p.id].title : p.code + ' ' + p.name"
                    :style="{ left: p.x / 3 + 'px', top: p.y / 3 + 'px' }"
                    >{{ p.code }}</div
                >
            </div>
            <div class="ff14-btn-group" style="margin-top: 1em; text-align: center; width: 100%">
                <div class="ff14-btn" @click.prevent.stop="resetSelected()">重置</div>
                <div class="ff14-btn" @click.prevent.stop="changeMap()">切換地圖</div>
            </div>
        </div>
        <div class="explore-drop">
            <div class="drop-controls">
                <select :value="submarineStore.rewardFilter" @change="onFilterChange" title="獲得物品清單要列哪些道具">
                    <option value="valuable">精選品</option>
                    <option value="all">全部道具</option>
                    <option value="target">只看目標</option>
                    <option value="common">一般素材(非精選品)</option>
                    <option v-for="(cname, key) in submarineStore.rewards" :key="key" :value="'cat:' + key"
                        >精選品:{{ cname }}</option
                    >
                </select>
                <select :value="submarineStore.lootBasis" @change="onBasisChange" :title="basisTitle">
                    <option :value="-1">不指定配裝</option>
                    <option v-for="(s, i) in submarineStore.sets" :key="i" :value="i">配裝:{{ s.name }}</option>
                </select>
            </div>
            <table class="drop-map wikitable">
                <tr
                    ><th :colspan="2" :title="headerTitle"
                        >獲得物品<span class="drop-unit">{{ unitText }}</span></th
                    ></tr
                >
                <tr v-if="rewardRows.length === 0"
                    ><td :colspan="2" class="drop-empty">{{
                        submarineStore.rewardFilter === 'target'
                            ? '還沒有目標:點道具前的 ☆ 把它標成目標'
                            : '這張地圖沒有符合條件的道具'
                    }}</td></tr
                >
                <tr v-for="row in rewardRows" :key="row.item.ID">
                    <td class="drop-item-name" :style="{ width: item_name_length + 4 + 'em' }"
                        ><i
                            class="fa target-star"
                            :class="row.target ? 'fa-star' : 'fa-star-o'"
                            :title="row.target ? '取消目標' : '標成目標:航點清單、海圖與路線情報會標出它的期望'"
                            @click.stop="toggleTarget(row.item.ID)"
                        ></i
                        ><ItemLink :item="row.item"></ItemLink
                    ></td>
                    <td>
                        <ul class="hor-waypoints-list">
                            <li
                                v-for="cell in row.cells"
                                :key="cell.wp"
                                :class="{ possible: !cell.known }"
                                :title="cell.title"
                                @click="toggleWP(cell.wp)"
                            >
                                <div class="wp" :class="{ selected: isSelect(cell.wp) }">{{ cell.code }}</div
                                ><span class="drop-value" :class="'r' + tierIndex[cell.tier]">{{ cell.label }}</span>
                            </li>
                        </ul>
                    </td>
                </tr>
            </table>
        </div>
    </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import {
    contextFor,
    describeEstimate,
    dominantTier,
    estimateItem,
    estimateLabel,
    estimateValue,
    formatPercent,
    formatQuantity,
    itemTiers,
} from '../module/loot';
import type { LootContext } from '../module/loot';
import { generateDropMap, getCurrentRewards } from '../module/Waypoint';
import { useSubmarineStore } from '../stores/submarine';
import type { PointInfo, TierKey } from '../types/ff14data';
import ItemLink from './ItemLink.vue';

const submarineStore = useSubmarineStore();

const map_name = computed(() =>
    submarineStore.maps[submarineStore.map] ? submarineStore.maps[submarineStore.map].cn : '未知地圖',
);
const currentWarpoints = computed(() => submarineStore.currentWarpoints);

const rewards = computed(() =>
    getCurrentRewards(
        submarineStore.itemDB,
        submarineStore.currentWarpoints,
        submarineStore.rewardFilter,
        submarineStore.targets,
    ),
);
const item_drop_map = computed(() => generateDropMap(submarineStore.currentWarpoints));

const tierIndex: Record<TierKey, number> = { low: 0, mid: 1, high: 2 };
const lootSet = computed(() => submarineStore.lootSet);
const setName = computed(() => (lootSet.value ? lootSet.value.n : ''));

function ctxFor(p: PointInfo): LootContext | null {
    return lootSet.value ? contextFor(lootSet.value.st, p) : null;
}

const unitText = computed(() => (lootSet.value ? '(每趟期望數量)' : '(高監視每趟主掉落機率)'));
const headerTitle = computed(
    () =>
        (lootSet.value
            ? `數字=配裝「${setName.value}」在各航點的每趟期望數量(含恩惠第二件、依回收等級的平均數量)。`
            : '數字=高監視時每趟主掉落拿到這個道具的機率(不含恩惠第二件)。選了配裝會改成每趟期望數量。') +
        '\n顏色:T1 紅、T2 黃、T3 綠(多個 tier 時取機率最大者)。淡色=只在原作清單,社群與台服紀錄都沒有出現過。' +
        '\n滑鼠移到航點上可看 tier 機率、tier 內佔比、平均數量、社群與台服紀錄筆數。',
);
const basisTitle = computed(() =>
    submarineStore.lootBasis >= 0 && !lootSet.value
        ? '這個配裝零件不完整,暫時以高監視機率標示'
        : '用哪個配裝估算:決定各航點的監視/回收等級與恩惠是否達標',
);

interface DropCell {
    wp: number;
    code: string;
    label: string;
    value: number;
    tier: TierKey;
    known: boolean;
    title: string;
}

const rewardRows = computed(() =>
    rewards.value.map((item) => {
        const cells = [] as DropCell[];
        for (const wp_id of item_drop_map.value[item.ID] || []) {
            const p = currentWarpoints.value[wp_id];
            const ctx = ctxFor(p);
            const est = estimateItem(p, item.ID, ctx);
            cells.push({
                wp: wp_id,
                code: p.code,
                label: estimateLabel(est, ctx),
                value: est.known ? estimateValue(est, ctx) : -1,
                tier: dominantTier(p, item.ID, est.tiers),
                known: est.known,
                title: describeEstimate(p, item, ctx, setName.value),
            });
        }
        cells.sort((a, b) => b.value - a.value);
        return { item, cells, target: submarineStore.targets.includes(item.ID) };
    }),
);

/** 每個航點對「目標道具」的合計:沒配裝=任一目標成為主掉落的機率,有配裝=期望數量合計 */
const targetValues = computed(() => {
    const out = {} as Record<number, { value: number; label: string; known: boolean; title: string }>;
    if (submarineStore.targets.length === 0) {
        return out;
    }
    for (const id in currentWarpoints.value) {
        const p = currentWarpoints.value[id];
        const ctx = ctxFor(p);
        let value = 0;
        let known = false;
        let partial = false;
        const lines = [] as string[];
        for (const itemId of submarineStore.targets) {
            const item = submarineStore.itemDB[itemId];
            if (!item || itemTiers(p, itemId).length === 0) {
                continue;
            }
            const est = estimateItem(p, itemId, ctx);
            known = known || est.known;
            partial = partial || est.lowerBound || est.quantityUnknown;
            value += est.known ? estimateValue(est, ctx) : 0;
            lines.push(`${item['中文名']}:${estimateLabel(est, ctx)}`);
        }
        if (lines.length === 0) {
            continue;
        }
        const label = !known ? '—' : ctx ? (partial ? '≥' : '') + formatQuantity(value) : formatPercent(value);
        const head = ctx ? `目標每趟期望數量(配裝「${setName.value}」)` : '目標成為高監視主掉落的機率';
        out[p.id] = { value, label, known, title: `${p.code} ${p.name}\n${head}:${label}\n${lines.join('\n')}` };
    }
    return out;
});

function hasTargetValue(point_id: number) {
    const v = targetValues.value[point_id];
    return v !== undefined && v.value > 0;
}

const item_name_length = computed(() => {
    let item_name_length = 0;
    for (const reward of rewards.value) {
        if (reward['中文名'].length > item_name_length) {
            item_name_length = reward['中文名'].length;
        }
    }
    return item_name_length;
});

function isSelect(point_id: number) {
    return submarineStore.selected.includes(point_id);
}
function toggleWP(point_id: number) {
    submarineStore.toggleWaypoint(point_id);
}
function resetSelected() {
    submarineStore.resetSelected();
}
function changeMap() {
    submarineStore.changeMap();
}
function toggleTarget(itemId: number) {
    submarineStore.toggleTarget(itemId);
}
function onFilterChange(e: Event) {
    submarineStore.setRewardFilter((e.target as HTMLSelectElement).value);
}
function onBasisChange(e: Event) {
    submarineStore.setLootBasis(Number((e.target as HTMLSelectElement).value));
}
</script>

<style lang="less">
.waypoint-block {
    overflow: hidden;
    margin: 0 auto;
    width: Calc(12em + 26em + 2em + 350px);

    > div {
        float: left;
    }
}

// 航點列表
.explore-list {
    width: 12em;
}

.waypoint {
    padding: 0 !important;

    > div {
        position: relative;
        padding: 0.2em 0.4em 0.2em 1.5em;
        &:hover {
            background-color: #311919;
            cursor: pointer;
        }

        > i.fa {
            position: absolute;
            top: 0.4em;
            left: 0.3em;
        }
    }
}

// 海圖(圖檔已鏡像進 src/assets/maps,由 vite 打包)
.explore-map {
    margin: 0 1em;
}

.sea-map {
    position: relative;
    width: 350px;
    height: 350px;
    background-position: 3px 1px;

    &::before {
        position: absolute;
        width: 100%;
        height: 100%;
        background-position: 3px 1px;
        content: ' ';
    }

    &.map1 {
        background: url('../assets/maps/map1.png');
        &::before {
            background: url('../assets/maps/map1_route.png');
        }
    }
    &.map2 {
        background: url('../assets/maps/map2.png');
        &::before {
            background: url('../assets/maps/map2_route.png');
        }
    }
    &.map3 {
        background: url('../assets/maps/map3.png');
        &::before {
            background: url('../assets/maps/map3_route.png');
        }
    }
    &.map4 {
        background: url('../assets/maps/map4.png');
        &::before {
            background: url('../assets/maps/map4_route.png');
        }
    }
    &.map5 {
        background: url('../assets/maps/map5.png');
        &::before {
            background: url('../assets/maps/map5_route.png');
        }
    }
    &.map6 {
        background: url('../assets/maps/map6.png');
        &::before {
            background: url('../assets/maps/map6_route.png');
        }
    }
}

.sea-map {
    .wp {
        position: absolute;
        width: 23px;
        height: 23px;
        border-color: #000;
        background: #079fe3;
        box-shadow: none;
        color: #000;

        &.base {
            background: #2553b7;
            cursor: auto;
        }

        &.selected {
            background: #0f0;
            color: #000 !important;
        }

        &.has-target {
            border-color: #fc3;
            box-shadow: 0 0 0 2px #fc3;
        }

        &:not(.base):hover {
            background: #fc3;
        }
    }
}

.explore-drop {
    overflow-y: auto;
    width: 26em;
    max-height: 550px;

    .drop-map {
        tr:hover td {
            background-color: #311919;
        }

        .drop-item-name {
            padding: 0.3em 0.4em !important;
        }

        .drop-value {
            margin: 0 4px 0 2px;
            font-size: 11px;
        }

        li.possible {
            opacity: 0.45;
        }
    }

    .drop-unit {
        margin-left: 0.4em;
        color: #8a8a8a;
        font-weight: normal;
        font-size: 12px;
    }

    .drop-empty {
        color: #8a8a8a;
    }

    .target-star {
        margin-right: 0.3em;
        color: #8a8a8a;
        cursor: pointer;

        &.fa-star {
            color: #fc3;
        }
    }
}

.drop-controls {
    display: flex;
    gap: 0.3em;
    margin-bottom: 0.3em;

    select {
        flex: 1;
        min-width: 0;
        border: 1px solid #555;
        background: #191313;
        color: #efefef;
        font-size: 12px;
    }
}

.waypoint .target-value {
    float: right;
    color: #fc3;
    font-size: 11px;

    &.possible {
        opacity: 0.45;
    }
}
</style>
