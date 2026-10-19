<template>
    <div class="set-editor-block float-layer">
        <div class="float-layer-title">配置編輯器</div>
        <div class="set-name ff14-input">顯示名稱 <input type="text" name="set-name" v-model="editor_set.name" /></div>
        <table class="component-table wikitable">
            <tr
                ><th style="width: 9em">系列</th
                ><th style="width: 5em" v-for="(name, i) in Object.values(SubmarinePartName)" :key="name + i">{{
                    name
                }}</th></tr
            >
            <tr
                v-for="(component, i) in submarineStore.components"
                :key="'component' + i"
                :class="{ locked: isLockedComponent(i) }"
            >
                <th :title="lockedComponentTitle(i)">{{ component.name }}</th>
                <td
                    v-for="j in 4"
                    :key="j"
                    class="hover-block"
                    :class="{ selected: i === editor_set.set[j - 1] }"
                    :title="lockedComponentTitle(i)"
                    @click="setComponent(j - 1, i)"
                    >{{ component.code }}</td
                >
            </tr>
        </table>
        <table class="status-table wikitable">
            <tr>
                <th style="width: 4.5em">位置</th>
                <th style="width: 4.5em">系列</th>
                <th style="width: 5em" v-for="(name, i) in SubmarineAttr" :key="i">{{ name }}</th>
            </tr>
            <tr v-for="partIndex in SubmarinePart" :key="partIndex" :class="{ r0: editor_set.set[partIndex] === -1 }">
                <template v-if="SubmarinePartName[partIndex]">
                    <th>{{ SubmarinePartName[partIndex] }}</th>
                    <template v-if="editor_set.set[partIndex] > -1">
                        <td>{{ getComponent(editor_set.set[partIndex]).code }}</td>
                        <td v-for="(attrName, j) in SubmarineAttr" :key="j">{{
                            getComponent(editor_set.set[partIndex]).getValue(partIndex, attrName)
                        }}</td>
                    </template>
                    <template v-else>
                        <td>無</td>
                        <td v-for="j in 6" :key="j">0</td>
                    </template>
                </template>
            </tr>
            <tr
                ><th :colspan="2" class="rank-bonus-head ff14-input"
                    ><input
                        type="number"
                        name="sub-rank"
                        min="1"
                        :max="submarineStore.maxRank"
                        :value="submarineStore.currentRank"
                        :title="`潛艇等級(1~${submarineStore.maxRank}),獎勵屬性隨等級變化`"
                        @change="onRankInput"
                    />級獎勵屬性</th
                ><td v-for="(bonus_v, i) in submarineStore.currentRankBonus" :key="i">{{ bonus_v }}</td></tr
            >
            <tr :class="{ r0: !editorSetStatus.v }"
                ><th :colspan="2">總計</th>
                <td>{{ editorSetStatus.st[0] }}</td>
                <td :class="{ ['r' + editorSetStatus.ms]: routeInfo.time > 0 }">{{ editorSetStatus.st[1] }}</td>
                <td :class="{ ['r' + editorSetStatus.mr]: routeInfo.time > 0 }">{{ editorSetStatus.st[2] }}</td>
                <td>{{ editorSetStatus.st[3] }}</td>
                <td
                    :class="{
                        r0: routeInfo.time > 0 && routeInfo.distance > editorSetStatus.st[4],
                        r2: routeInfo.time > 0 && routeInfo.distance <= editorSetStatus.st[4],
                    }"
                    >{{ editorSetStatus.st[4] }}</td
                >
                <td :class="{ ['r' + editorSetStatus.mf]: routeInfo.time > 0 }">{{ editorSetStatus.st[5] }}</td>
            </tr>
        </table>
        <table class="explore-preview-table wikitable" v-if="routeInfo.time > 0">
            <tr>
                <th style="width: 9em">探索路線</th>
                <td style="width: 10em; text-align: left">
                    <ul class="hor-waypoints-list no-hover">
                        <li v-for="wp_code in routeInfo.routeCode" :key="wp_code"
                            ><div class="wp selected">{{ wp_code }}</div></li
                        >
                    </ul>
                </td>
            </tr>
            <tr
                ><th>探索距離</th
                ><td
                    style="text-align: left"
                    :class="{
                        r0: routeInfo.time > 0 && routeInfo.distance > editorSetStatus.st[4],
                        r2: routeInfo.time > 0 && routeInfo.distance <= editorSetStatus.st[4],
                    }"
                    >{{ routeInfo.distance }} / {{ editorSetStatus.st[4] }}</td
                ></tr
            >
            <tr
                ><th>探索時間</th
                ><td style="text-align: left">{{ doGetRouteTimeCostText(editorSetStatus.st[3]) }}</td></tr
            >
            <tr
                ><th>回歸時間</th
                ><td style="text-align: left">{{ doGetRouteRealTimeText(editorSetStatus.st[3]) }}</td></tr
            >
            <tr
                ><th>探索情況</th
                ><td style="text-align: left"
                    ><span v-for="(code, i) in routeInfo.routeCode" :key="code" :class="'r' + editorSetStatus.s[i]">{{
                        code
                    }}</span>
                    / 需要:<span class="r2">{{ routeInfo.max_surveillance }}</span></td
                ></tr
            >
            <tr
                ><th>收集情況</th
                ><td style="text-align: left"
                    ><span v-for="(code, i) in routeInfo.routeCode" :key="code" :class="'r' + editorSetStatus.r[i]">{{
                        code
                    }}</span>
                    / 需要:<span class="r2">{{ routeInfo.max_retrieval }}</span></td
                ></tr
            >
            <tr
                ><th>額外探索</th
                ><td style="text-align: left"
                    ><span v-for="(code, i) in routeInfo.routeCode" :key="code" :class="'r' + editorSetStatus.f[i]">{{
                        code
                    }}</span>
                    / 需要:<span class="r2">{{ routeInfo.max_favor }}</span></td
                ></tr
            >
        </table>
        <div class="ff14-btn-group">
            <div class="ff14-btn" :class="{ disable: !editorSetStatus.v }" @click="btnSaveSet">保存</div>
            <div class="ff14-btn" @click="btnClose">取消</div>
            <div class="ff14-btn" v-if="submarineStore.editor_index > -1" @click="btnDeleteSet">刪除</div>
        </div>
    </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive } from 'vue';
import { SubmarineAttr, SubmarinePart, SubmarinePartName } from '../constant/enum';
import { calcSetStatus } from '../module/calcSetStatus';
import { getRouteRealTimeText, getRouteTimeCostText } from '../module/routeTimeText';
import { SetInfo, useSubmarineStore } from '../stores/submarine';

const submarineStore = useSubmarineStore();

const editor_set = reactive<SetInfo>({
    set: [-1, -1, -1, -1],
    name: '',
}); // 編輯中的組合

onMounted(() => {
    if (submarineStore.editor_index == -1) {
        editor_set.set = [-1, -1, -1, -1];
        editor_set.name = '';
    } else {
        editor_set.set = submarineStore.sets[submarineStore.editor_index].set;
        editor_set.name = submarineStore.sets[submarineStore.editor_index].name;
    }
});

const routeInfo = computed(() => submarineStore.routeInfo);

const editorSetStatus = computed(() => {
    return calcSetStatus(editor_set);
});

function doGetRouteTimeCostText(speed: number) {
    return getRouteTimeCostText(submarineStore.routeInfo.time, speed);
}

function doGetRouteRealTimeText(speed: number) {
    return getRouteRealTimeText(submarineStore.startRealTime, submarineStore.routeInfo.time, speed);
}

function getComponent(id: number) {
    return submarineStore.components[id];
}

function isLockedComponent(index: number) {
    return submarineStore.components[index].rankReq > submarineStore.currentRank;
}

function lockedComponentTitle(index: number) {
    const component = submarineStore.components[index];
    return component.rankReq > submarineStore.currentRank
        ? `需要潛艇等級 ${component.rankReq}(目前 ${submarineStore.currentRank})`
        : '';
}

function btnClose(event: MouseEvent) {
    if (event.button > 0) {
        return;
    }
    submarineStore.setLayer(0);
    event.preventDefault();
}

function onRankInput(event: Event) {
    const target = event.target as HTMLInputElement;
    submarineStore.setRank(Number(target.value));
    target.value = String(submarineStore.currentRank);
}

function setComponent(slot: number, componentIndex: number) {
    if (editor_set.set[slot] == componentIndex) {
        editor_set.set[slot] = -1;
    } else {
        editor_set.set[slot] = componentIndex;
    }
}

function btnSaveSet() {
    if (editorSetStatus.value.v) {
        submarineStore.addSet({
            setStatus: editorSetStatus.value,
            index: submarineStore.editor_index,
        });
        submarineStore.setLayer(0);
    }
}

function btnDeleteSet() {
    submarineStore.deleteSet(submarineStore.editor_index);
    submarineStore.setLayer(0);
}
</script>

<style lang="less">
.set-editor-block,
.set-finder-block {
    background: #000;
    color: #fff;
}

.set-editor-block > * + * {
    margin-top: 1em !important;
}

.set-name input {
    margin-left: 1em;
}

// 等級不到的零件系列只標灰提示,不擋選取
.component-table tr.locked {
    th,
    td {
        color: #6b6b6b;
    }
}

.rank-bonus-head input {
    margin-right: 0.3em;
    width: 3.5em;
    text-align: center;
}
</style>
