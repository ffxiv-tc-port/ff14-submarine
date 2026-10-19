import type { SubmarinePart } from '../constant/enum';
import { getItemData } from '../module/getSubmarineData';
import type { PartInfo, SubmarineComponentRaw } from '../types/ff14data';

export class SubmarineComponent {
    raw: SubmarineComponentRaw;
    parts: Record<SubmarinePart, PartInfo>;

    constructor(raw: SubmarineComponentRaw) {
        this.raw = raw;
        this.parts = this.getInitParts();
    }

    get name() {
        return this.raw.n;
    }

    get code() {
        return this.raw.c;
    }

    /** 本系列零件的裝備需求等級(四件同級,取最大值保險) */
    get rankReq() {
        let rank = 0;
        for (const part of Object.values(this.parts)) {
            if (part.等級 > rank) {
                rank = part.等級;
            }
        }
        return rank;
    }

    private getInitParts() {
        const itemData = getItemData();
        const parts = {} as Record<SubmarinePart, PartInfo>;
        this.raw.items.forEach((itemId) => {
            const item = itemData[itemId];
            if (item === undefined || item.機體數據 === undefined) {
                throw new Error(`item ${itemId} not found`);
            }
            parts[item.機體數據.位置] = item.機體數據;
        });
        return parts;
    }

    getValue(part: SubmarinePart, valueType: '重量' | '探索性能' | '收集性能' | '巡航速度' | '航行距離' | '恩惠') {
        return this.parts[part][valueType];
    }

    getPartAllValue(part: SubmarinePart) {
        return this.parts[part];
    }

    getWeight(part: SubmarinePart) {
        return this.parts[part].重量;
    }

    getExplore(part: SubmarinePart) {
        return this.parts[part].探索性能;
    }

    getCollect(part: SubmarinePart) {
        return this.parts[part].收集性能;
    }

    getSpeed(part: SubmarinePart) {
        return this.parts[part].巡航速度;
    }

    getDistance(part: SubmarinePart) {
        return this.parts[part].航行距離;
    }

    getFavor(part: SubmarinePart) {
        return this.parts[part].恩惠;
    }
}
