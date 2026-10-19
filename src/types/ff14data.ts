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
    tool_version: number;
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
}
