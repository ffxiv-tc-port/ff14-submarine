// 计算属性

import type { ItemInfo, PointInfo } from '../types/ff14data';

// 当前地图有价值的物品列表
// filter:valuable(預設,精選品)/ all / target / common(非精選品)/ cat:<分類>;目標道具排最前
export function getCurrentRewards(
    itemDB: Record<number, ItemInfo>,
    currentWarpoints: Record<number, PointInfo>,
    filter = 'valuable',
    targets: number[] = [],
) {
    const reward_id_list = [] as number[];
    for (const p_id in currentWarpoints) {
        const p_info = currentWarpoints[p_id];
        const drop_list = [...p_info.drop.low, ...p_info.drop.mid, ...p_info.drop.high];
        for (const item_id of drop_list) {
            if (!reward_id_list.includes(item_id)) {
                reward_id_list.push(item_id);
            }
        }
    }
    const reward_list = [] as ItemInfo[];
    reward_id_list.forEach((item_id) => {
        const item_info = itemDB[item_id];
        if (rewardMatches(item_info, filter, targets)) {
            reward_list.push(item_info);
        }
    });
    reward_list.sort((a, b) => {
        const ta = targets.includes(a.ID);
        if (ta !== targets.includes(b.ID)) {
            return ta ? -1 : 1;
        }
        if (!a.valuable !== !b.valuable) {
            return a.valuable ? -1 : 1;
        }
        if (a.category && b.category && a.category != b.category) {
            return a.category - b.category;
        } else {
            return b.ID - a.ID;
        }
    });
    return reward_list;
}

function rewardMatches(item: ItemInfo, filter: string, targets: number[]) {
    if (filter === 'all') {
        return true;
    }
    if (filter === 'target') {
        return targets.includes(item.ID);
    }
    if (filter === 'common') {
        return !item.valuable;
    }
    if (filter.startsWith('cat:')) {
        return item.valuable === true && String(item.category) === filter.slice(4);
    }
    return item.valuable === true;
}

// 根据地图航点生成掉落物品的反查表(同一道具可在一個航點的兩個 tier,航點只記一次)
export function generateDropMap(currentWarpoints: Record<number, PointInfo>) {
    const drop_map = {} as Record<number, number[]>;
    for (const p_index in currentWarpoints) {
        const p_info = currentWarpoints[p_index];
        for (const item_id of [...p_info.drop.low, ...p_info.drop.mid, ...p_info.drop.high]) {
            if (!drop_map[item_id]) {
                drop_map[item_id] = [];
            }
            if (!drop_map[item_id].includes(p_info.id)) {
                drop_map[item_id].push(p_info.id);
            }
        }
    }
    return drop_map;
}
