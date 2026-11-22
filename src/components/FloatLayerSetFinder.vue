<template>
    <div class="set-finder-block float-layer">
        <div class="float-layer-title">配置搜尋器</div>
        <div class="finder-rank-hint">以潛艇等級 {{ submarineStore.currentRank }} 計算(等級不到的零件系列不列入)</div>
        <div class="finder-option ff14-input">
            <table>
                <tr v-for="(_, i) in set_filter" :key="i">
                    <th>{{ Object.values(SubmarineAttr)[i] }}</th>
                    <td><input type="text" v-model.number="set_filter[i]" /></td>
                </tr>
            </table>
        </div>
        <div class="ff14-btn-group" style="margin-top: 1em">
            <div class="ff14-btn" @click="close">關閉</div>
        </div>
        <template v-if="validSets.length > 0">
            <p
                >共有 {{ validSets.length }} 筆符合的記錄。<template
                    v-if="validSets.length > submarineStore.maxFilterCount"
                    >最多顯示 {{ submarineStore.maxFilterCount }} 筆記錄,請縮小查詢範圍。</template
                ></p
            >
            <table class="sets-table wikitable" v-if="validSets.length <= submarineStore.maxFilterCount">
                <tr>
                    <th style="width: 12em">配置</th>
                    <th
                        v-for="(name, _, i) in SubmarineAttr"
                        :key="i"
                        style="width: 5em"
                        class="hover-block"
                        @click="sortByAttr(i)"
                        :class="sortTitleColor(i)"
                        >{{ name }}</th
                    >
                    <th
                        style="width: 5em"
                        class="hover-block"
                        :class="sortTitleColor(TARGET_SORT)"
                        :title="targetHeadTitle"
                        @click="sortByAttr(TARGET_SORT)"
                        >目標每趟</th
                    >
                    <th style="width: 5em">操作</th>
                </tr>
                <tr v-for="(set, i) in validSets" :key="i" class="hover-block" @click="checkAndAddSet(set)">
                    <td
                        ><div class="set-code"
                            ><span>{{ set.c[0] }}</span
                            ><span>{{ set.c[1] }}</span
                            ><span>{{ set.c[2] }}</span
                            ><span>{{ set.c[3] }}</span></div
                        ></td
                    >
                    <td v-for="(st_v, i) in set.st" :key="i">{{ st_v }}</td>
                    <td class="target-cell" :class="{ muted: !targetActive }">{{ targetLabel(set) }}</td>
                    <td class="selected" v-if="checkSet(set)">已加入</td>
                    <td class="add-set" v-else>加入</td>
                </tr>
            </table>
        </template>
        <p v-else>沒有找到符合條件的記錄,請修改查詢範圍。</p>
    </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, ref, watchEffect } from 'vue';
import { SubmarineAttr } from '../constant/enum';
import { contextFor, estimateItem, formatQuantity } from '../module/loot';
import { useSubmarineStore } from '../stores/submarine';
import type { SetStatus } from '../types/submarineSet';

const set_filter = ref([0, 0, 0, 0, 0, 0]); // 搜尋用過濾器
const filter_sort = reactive([-1, -1]); // 第一個參數是用哪個屬性排序,第二個參數是正序還是逆序
const TARGET_SORT = 6; // 排序鍵:目前路線的目標每趟期望(不是屬性欄)

const submarineStore = useSubmarineStore();

onMounted(() => {
    submarineStore.initAllSets();
    set_filter.value = [
        0,
        submarineStore.routeInfo.max_surveillance,
        submarineStore.routeInfo.max_retrieval,
        submarineStore.speed,
        submarineStore.routeInfo.distance,
        submarineStore.routeInfo.max_favor,
    ];
});

function close() {
    submarineStore.setLayer(0);
}

/** 有目標且有路線時才有意義;否則整欄顯示「—」、排序維持原順序 */
const targetActive = computed(
    () => submarineStore.targets.length > 0 && submarineStore.routeInfo.routeOrder.length > 0,
);
const targetHeadTitle =
    '目前路線(最短路線情報)上 ☆ 目標道具的每趟期望數量合計,依每組配裝的屬性判監視/回收/恩惠等級。' +
    '\n點一下依此排序(預設不排序)。沒有目標或還沒選航點時顯示「—」;「≥」=有航點缺該回收等級的數量紀錄,是下限。';

/** 每個航點只有 3×3×2 種等級組合,先按等級快取,1 萬組配裝排序時只查表 */
const targetCache = computed(() => {
    const cache = new Map<string, { value: number; partial: boolean }>();
    return { cache, route: submarineStore.routeInfo.routeOrder.slice(), targets: submarineStore.targets.slice() };
});

function targetValue(set: SetStatus) {
    const { cache, route, targets } = targetCache.value;
    let value = 0;
    let partial = false;
    for (const wp_id of route) {
        const p = submarineStore.currentWarpoints[wp_id];
        const ctx = contextFor(set.st, p);
        const key = `${wp_id}:${ctx.surv}:${ctx.ret}:${ctx.favor ? 1 : 0}`;
        let hit = cache.get(key);
        if (!hit) {
            hit = { value: 0, partial: false };
            for (const itemId of targets) {
                const est = estimateItem(p, itemId, ctx);
                hit.value += est.expected;
                hit.partial = hit.partial || est.lowerBound || est.quantityUnknown;
            }
            cache.set(key, hit);
        }
        value += hit.value;
        partial = partial || hit.partial;
    }
    return { value, partial };
}

function targetLabel(set: SetStatus) {
    if (!targetActive.value) {
        return '—';
    }
    const v = targetValue(set);
    return (v.partial ? '≥' : '') + formatQuantity(v.value);
}

const validSets = ref<SetStatus[]>([]);

watchEffect(() => {
    const valid_sets = submarineStore.all_sets.filter((set) => {
        if (!set.v) {
            return false;
        }
        for (let i = 0; i < set_filter.value.length; i++) {
            if (set_filter.value[i] > 0 && set.st[i] < set_filter.value[i]) {
                return false;
            }
        }
        return true;
    });
    if (filter_sort[0] === TARGET_SORT) {
        if (targetActive.value) {
            const values = new Map<SetStatus, number>();
            for (const set of valid_sets) {
                values.set(set, targetValue(set).value);
            }
            valid_sets.sort((a, b) => (values.get(b)! - values.get(a)!) * filter_sort[1]);
        }
    } else if (filter_sort[0] > -1) {
        valid_sets.sort(function (a, b) {
            if (filter_sort[1] === 1) {
                return b.st[filter_sort[0]] - a.st[filter_sort[0]];
            } else {
                return a.st[filter_sort[0]] - b.st[filter_sort[0]];
            }
        });
    }
    validSets.value = valid_sets;
});

function checkSet(c_set: SetStatus) {
    // 檢查配置是否已經存在(上游原版取 set[0] 是 bug,永遠比不到)
    for (let i = 0; i < submarineStore.sets.length; i++) {
        const set = submarineStore.sets[i];
        if (
            c_set.set[0] == set.set[0] &&
            c_set.set[1] == set.set[1] &&
            c_set.set[2] == set.set[2] &&
            c_set.set[3] == set.set[3]
        ) {
            return true;
        }
    }
    return false;
}

function checkAndAddSet(set: SetStatus) {
    if (!checkSet(set)) {
        submarineStore.addSet({
            setStatus: set,
            index: -1,
        });
    }
}

function sortByAttr(attr_index: number) {
    if (filter_sort.length < 2) {
        filter_sort[0] = -1;
        filter_sort[1] = -1;
    }
    if (filter_sort[0] !== attr_index) {
        filter_sort[0] = attr_index;
        filter_sort[1] = 1;
    } else {
        filter_sort.splice(1, 1, filter_sort[1] * -1);
    }
}

function sortTitleColor(attr_index: number) {
    if (filter_sort[0] === attr_index) {
        if (filter_sort[1] === 1) {
            return 'r2';
        } else {
            return 'r0';
        }
    } else {
        return '';
    }
}
</script>

<style lang="less">
.finder-rank-hint {
    margin: 0.5em 0;
    color: #8a8a8a;
    font-size: 12px;
}

.finder-option table {
    border-collapse: separate;
    border-spacing: 0 5px;
    th {
        width: 6em;
    }
}

.finder-option input {
    width: 3em;
}

.set-code > span {
    position: relative;
    display: inline-block;
    margin: 0 1px;
    width: 2.5em;
    color: #efefef;
    text-align: center;
}

.set-code > span + span {
    border-left: 1px solid #7b7b7b;
}

.add-set {
    color: #77d1ff;
}

.target-cell {
    color: #fc3;

    &.muted {
        color: #8a8a8a;
    }
}
</style>
