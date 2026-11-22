import type { SubmarinePart } from '../constant/enum';

/** 由 scripts/gen_data.py 產生、寫入 public/data.js 的資料 */
export interface SubmarineData {
    components: SubmarineComponentRaw[]; // 船體零件
    data_sources: DataSourceInfo[]; // 資料源
    item_db: Record<number, ItemInfo>; // 物品資料
    max_filter_count: number; // 搜尋器最大顯示筆數
    max_rank: number; // 潛艇最大等級
    max_rank_bonus: number[]; // 最大等級獎勵屬性
    rank_bonus_table: number[][]; // 逐級獎勵屬性(index=等級,0 位為零值)
    sea_name_map: SeaInfo[]; // 海域名稱
    point_data: PointInfo[]; // 航點資料
    reward_category_map: Record<number, string>;
    tc_loot?: TcLootSummary; // 台服紀錄彙總的涵蓋範圍
    tool_version: number;
}

export interface TcLootSummary {
    records: number; // 航點紀錄筆數
    sectors: number; // 涵蓋航點數
    period_from: string; // YYYY-MM
    period_to: string;
}

export interface SubmarineComponentRaw {
    c: string; // 縮寫
    n: string; // 名稱
    items: number[]; // 物品
}

export interface DataSourceInfo {
    title: string; // 標題
    desc: string; // 描述
    author: string; // 作者
    url: string; // 連結
}

export interface ItemInfo {
    ID: number;
    中文名: string;
    品質: number;
    圖標ID: number;
    維基名?: string; // 灰機 wiki 頁名(簡中),物品連結用
    category?: number;
    valuable?: boolean;
    機體數據?: PartInfo;
}

export interface PartInfo {
    位置: SubmarinePart;
    重量: number;
    探索性能: number;
    收集性能: number;
    巡航速度: number;
    航行距離: number;
    恩惠: number;
    修理: number; // 修理材料數
    等級: number; // 裝備需求等級
}

export interface SeaInfoRaw {
    cn: string; // 中文名
    en: string; // 英文名
    jp: string; // 日文名
}

export type SeaInfo = SeaInfoRaw & {
    info: PointInfo;
};

export interface PointInfo {
    code: string; // 航點代號
    drop: {
        low: number[];
        mid: number[];
        high: number[];
    };
    expReward: number;
    id: number;
    map: number;
    name: string;
    rankReq: number;
    stars: number;
    start: boolean;
    statReq: {
        favor: number;
        retrieval: {
            norm: number;
            optim: number;
        };
        surveillance: {
            mid: number;
            high: number;
        };
    };
    surveyDistance: number;
    surveyRange: number;
    tankReq: number;
    toDestination: Record<
        number,
        {
            range: number;
            distance: number;
        }
    >;
    unlocks: {
        map?: number;
        sectors?: number[];
    };
    x: number;
    y: number;
    loot?: PointLoot; // 社群掉落機率(起點沒有)
    tc?: PointTcObs; // 台服觀測次數(沒跑過的航點沒有)
}

/** tier 鍵沿用 drop:low=T1、mid=T2、high=T3;機率都是 0~1 */
export type TierKey = 'low' | 'mid' | 'high';

export interface PointLoot {
    hp: number[]; // 高監視主掉落的 tier 機率 [T1, T2, T3]
    hd: number[]; // 高監視第二件(恩惠)的 tier 機率
    mp: number[]; // 中監視主掉落 [T1, T2]
    md: number[]; // 中監視第二件
    fp: number; // 恩惠達標時出第二件的機率
    gn: number; // 社群高監視紀錄筆數
    low: Record<number, ItemLootStat>;
    mid: Record<number, ItemLootStat>;
    high: Record<number, ItemLootStat>;
}

export interface ItemLootStat {
    s: number; // tier 內佔比(高監視紀錄)
    o: number; // tier 內佔比(全部紀錄,低監視以這個為準)
    q: number[]; // 平均數量 [差, 普通, 最佳] 回收;0=沒有紀錄
    n: number; // 社群紀錄筆數
}

export interface PointTcObs {
    v: number; // 造訪次數
    sv: number[]; // 主掉落監視等級次數 [低, 中, 高]
    h: number[]; // 高監視主掉落 tier 次數 [T1, T2, T3]
    f: number[]; // 恩惠 [有第二件, 屬性夠沒觸發, 屬性不足]
    low: Record<number, number[]>; // 道具在各監視等級的掉落次數 [低, 中, 高](主+第二件)
    mid: Record<number, number[]>;
    high: Record<number, number[]>;
}
