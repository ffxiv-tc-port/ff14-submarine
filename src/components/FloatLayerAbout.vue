<template>
    <div class="about-block float-layer">
        <div class="float-layer-title">關於</div>
        <p>原作:{{ author }},以 MIT 授權發布。</p>
        <p>台服版:資料以台服 7.30 遊戲檔為準重新產生,介面繁體中文化,並加入可調潛艇等級、掉落機率與目標道具。</p>
        <div class="float-layer-title">掉落機率</div>
        <p class="about-loot"
            >機率與數量取自全球社群紀錄(SubmarineTracker 社群數據表):每趟依監視等級先抽 tier(低監視只出 T1、中監視
            T1/T2、高監視 T1~T3),再依 tier 內佔比抽道具,數量取所在回收等級的平均;恩惠達標時有機率多拿第二件。</p
        >
        <p class="about-loot" v-if="submarineStore.tcLoot"
            >台服紀錄:{{ submarineStore.tcLoot.records.toLocaleString() }} 筆航點紀錄({{
                submarineStore.tcLoot.period_from
            }}~{{ submarineStore.tcLoot.period_to }},{{ submarineStore.tcLoot.sectors }} 個航點)。拿來驗證社群機率,
            沒有發現台服獨有的掉落;各航點的台服觀測次數列在滑鼠提示裡。</p
        >
        <p class="about-loot" v-else>台服紀錄:這份資料沒有附台服紀錄彙總。</p>
        <div class="float-layer-title">探索/收集/恩惠門檻</div>
        <p class="about-loot"
            >取社群數據表的實測門檻(BP)。原作與 SubmarineTracker 的門檻是同一份、取整到 5 的倍數,在翠浪海、賽蓮海、紫礁海與南蒼茫洋共
            29 個航點比實測高 1~4 點;改用實測值後,每個航點的台服紀錄(各監視/回收等級與恩惠結果出現過的屬性值)都和門檻沒有矛盾。</p
        >
        <div class="float-layer-title">資料來源</div>
        <p>本工具使用了以下來源的資料</p>
        <table class="wikitable" style="text-align: left">
            <tr><th>來源</th><th>作者</th><th>使用部分</th></tr>
            <tr v-for="(ds, i) in submarineStore.dataSources" :key="i">
                <td
                    ><a v-if="ds.url" :href="ds.url" target="_blank">{{ ds.title }}</a
                    ><template v-else>{{ ds.title }}</template></td
                >
                <td>{{ ds.author }}</td>
                <td>{{ ds.desc }}</td>
            </tr>
        </table>
        <div class="ff14-btn-group" style="margin-top: 1em">
            <div class="ff14-btn" @click="close">關閉</div>
        </div>
    </div>
</template>

<script lang="ts" setup>
import * as pkg from '../../package.json';
import { useSubmarineStore } from '../stores/submarine';

const submarineStore = useSubmarineStore();

const author = `${pkg.author.name}(${pkg.author.character}@${pkg.author.server})`;

function close() {
    submarineStore.setLayer(0);
}
</script>
