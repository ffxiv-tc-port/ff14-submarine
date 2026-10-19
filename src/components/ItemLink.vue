<template>
    <span class="item-link huiji-tt size-20" :data-name="item.ID" data-type="item" style="display: inline-block">
        <a :href="item_href" target="_blank" rel="noreferrer">
            <span class="item-icon size-20" style="display: inline-block">
                <span class="item-icon--img"><img :src="item_icon" width="20" height="20" /></span>
            </span>
            <span :class="['item-baseinfo', 'item-name', rarity_class(item['品質'])]">{{ item['中文名'] }}</span>
        </a>
    </span>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import { getFF14IconUrl } from '../module/util/getImageUrl';
import type { ItemInfo } from '../types/ff14data';

const props = defineProps<{
    item: ItemInfo;
}>();

const rarity_map: Record<number, string> = {
    1: 'rarity-common',
    2: 'rarity-uncommon',
    3: 'rarity-rare',
    4: 'rarity-epic',
    7: 'rarity-magic',
};

const item_icon = computed(() => getFF14IconUrl(props.item['圖標ID']));

// 灰機 wiki 的頁名是簡中,用維基名連結;顯示仍是台服繁中名
const item_href = computed(() => {
    const wikiName = props.item['維基名'] ? props.item['維基名'] : props.item['中文名'];
    return 'https://ff14.huijiwiki.com/wiki/物品:' + wikiName;
});

function rarity_class(rarity: number) {
    return rarity > 1 ? rarity_map[rarity] : '';
}
</script>
