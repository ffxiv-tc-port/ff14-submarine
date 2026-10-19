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
                                {{ p.code + ' ' + p.name }}</div
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
                    :class="{ selected: isSelect(p.id) }"
                    :key="p.id"
                    @click="toggleWP(p.id)"
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
            <table class="drop-map wikitable">
                <tr><th :colspan="2">獲得物品</th></tr>
                <tr v-for="item in rewards" :key="item.ID">
                    <td class="drop-item-name" :style="{ width: item_name_length + 3 + 'em' }"
                        ><ItemLink :item="item"></ItemLink
                    ></td>
                    <td>
                        <ul class="hor-waypoints-list">
                            <li v-for="wp_id in item_drop_map[item.ID]" :key="wp_id" @click="toggleWP(wp_id)">
                                <div class="wp" :class="{ selected: isSelect(wp_id) }">{{
                                    currentWarpoints[wp_id].code
                                }}</div>
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
import { generateDropMap, getCurrentRewards } from '../module/Waypoint';
import { useSubmarineStore } from '../stores/submarine';
import ItemLink from './ItemLink.vue';

const submarineStore = useSubmarineStore();

const map_name = computed(() =>
    submarineStore.maps[submarineStore.map] ? submarineStore.maps[submarineStore.map].cn : '未知地圖',
);
const currentWarpoints = computed(() => submarineStore.currentWarpoints);

const rewards = computed(() => getCurrentRewards(submarineStore.itemDB, submarineStore.currentWarpoints));
const item_drop_map = computed(() => generateDropMap(submarineStore.currentWarpoints));
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
    }
}
</style>
