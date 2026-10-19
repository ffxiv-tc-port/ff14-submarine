<template>
    <div class="about-block float-layer">
        <div class="float-layer-title">關於</div>
        <p>原作:{{ author }},以 MIT 授權發布。</p>
        <p>台服版:資料以台服 7.20 遊戲檔為準重新產生,介面繁體中文化,並加入可調潛艇等級。</p>
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
