import { acceptHMRUpdate, defineStore } from 'pinia';
import { store } from '.';
import { DEFAULT_MAP, LOCAL_STOREAGE_KEY } from '../constant/name';
import { calcSetBaseStatus } from '../module/calcSetStatus';
import { getSubmarineData } from '../module/getSubmarineData';
import { SubmarineComponent } from '../objects/component';
import type { DataSourceInfo, ItemInfo, PointInfo, SeaInfo } from '../types/ff14data';
import type { routeInfo } from '../types/routeInfo';
import type { SetStatus } from '../types/submarineSet';

export interface SetInfo {
    set: number[];
    name: string;
}

export const useSubmarineStore = defineStore({
    id: 'submarine',
    state: () => ({
        // 從 data.js 取得的內容
        version: 0,
        dataSources: [] as DataSourceInfo[],
        maxFilterCount: 300, // 搜尋時最大過濾器數量,會讀取設定,不要太大影響效能

        components: [] as SubmarineComponent[], // 船體零件
        maps: {} as Record<number, SeaInfo>, // 海圖名稱和基本資訊
        waypointData: {} as Record<number, Record<number, PointInfo>>, // 航點資料
        itemDB: {} as Record<number, ItemInfo>, // 用到的物品資料
        rewards: {} as Record<number, string>, // 獎勵類型名稱

        maxRank: 0, // 船最大等級
        maxRankBonus: [] as number[], // 船最大等級時的屬性獎勵
        rankBonusTable: [] as number[][], // 逐級屬性獎勵(index=等級)

        // 會保存到 localStorage 的暫存資料
        map: DEFAULT_MAP, // 目前地圖
        selected: [] as number[], // 目前選中的航點
        speed: 100, // 目前預覽時使用的速度
        rank: 0, // 潛艇等級(0=未設定,視為滿級)
        sets: [] as SetInfo[], // 儲存的船體組合,每筆是 4 個零件編號和一個名字

        // 其他暫存資料
        layer: 0, // 浮層顯示
        routeInfo: {
            routeOrder: [], // 航線順序 r
            routeCode: [], // 航線代號 rc
            time: 0, // 航線時間 t
            distance: 0, // 航線距離 d
            max_surveillance: 0, // 最大需要的探索 ms
            max_retrieval: 0, // 最大需要的收集 mr
            max_favor: 0, // 最大需要的恩惠 mf
        } as routeInfo,
        startRealTime: Date.now(), // 用於計算出發時間的現實時間基數,每 5 秒刷新一次

        // 編輯器用暫存變數
        editor_index: -1, // 目前編輯的序號,-1 為新增
        // 搜尋器用變數
        all_sets: [] as SetStatus[], // 全配置,初次使用時再初始化
    }),
    getters: {
        currentWarpoints: (state) => {
            return state.waypointData[state.map];
        },
        startPoint: (state) => {
            if (state.maps[state.map]) {
                return state.maps[state.map].info;
            }
            return null;
        },
        /** 目前生效的潛艇等級(未設定或超界時=滿級) */
        currentRank: (state) => {
            if (state.rank >= 1 && state.rank <= state.maxRank) {
                return state.rank;
            }
            return state.maxRank;
        },
        /** 目前等級的屬性獎勵 */
        currentRankBonus(state): number[] {
            const bonus = state.rankBonusTable[this.currentRank];
            return bonus ? bonus : state.maxRankBonus;
        },
    },
    actions: {
        // 讀取/保存設定
        // 更新 localStorage 資料
        saveLocalData() {
            const ls_data = {
                map: this.map,
                selected: this.selected,
                speed: this.speed,
                rank: this.rank,
                sets: this.sets,
                ver: this.version,
            };
            localStorage.setItem(LOCAL_STOREAGE_KEY, JSON.stringify(ls_data));
        },

        // 取得 localStorage 資料
        loadLocalData() {
            const ls_str = localStorage.getItem(LOCAL_STOREAGE_KEY);
            let ls_data = ls_str ? JSON.parse(ls_str) : {};
            if (!ls_data.ver) ls_data = {};
            this.map = ls_data.map ? ls_data.map : DEFAULT_MAP;
            this.selected = ls_data.selected ? ls_data.selected : [];
            this.speed = ls_data.speed ? ls_data.speed : 100;
            this.rank = ls_data.rank ? ls_data.rank : 0;
            this.sets = ls_data.sets ? ls_data.sets : [];
        },
        // 從網頁提供的原資料中初始化
        initAllData() {
            const allData = getSubmarineData();
            // 基礎資訊
            this.version = allData.tool_version;
            this.dataSources = allData.data_sources;
            this.maxFilterCount = allData.max_filter_count;

            // 遊戲資料
            this.components = allData.components.map((component) => {
                return new SubmarineComponent(component);
            });
            this.maps = (() => {
                const startPoints = allData.point_data.filter((point) => point.start);
                const maps = {} as Record<number, SeaInfo>;
                startPoints.forEach((point) => {
                    if (allData.sea_name_map[point.map - 1] === undefined) {
                        console.error(`地圖${point.map}不存在`);
                        return;
                    }
                    maps[point.map] = {
                        ...allData.sea_name_map[point.map - 1],
                        info: point,
                    };
                });
                return maps;
            })();
            this.rewards = allData.reward_category_map;
            this.maxRank = allData.max_rank;
            this.maxRankBonus = allData.max_rank_bonus;
            this.rankBonusTable = allData.rank_bonus_table ? allData.rank_bonus_table : [];
            this.waypointData = (() => {
                const wpData = allData.point_data.filter((point) => !point.start);
                const wp = {} as Record<number, Record<number, PointInfo>>;
                wpData.forEach((point) => {
                    if (wp[point.map] === undefined) {
                        wp[point.map] = {};
                    }
                    wp[point.map][point.id] = point;
                });
                return wp;
            })();
            this.itemDB = allData.item_db;
        },
        toggleWaypoint(point_id: number) {
            const index = this.selected.indexOf(point_id);
            if (index > -1) {
                this.selected.splice(index, 1);
            } else {
                if (this.selected.length < 5) {
                    this.selected.push(point_id);
                }
            }
        },
        updateStartRealTime(timestamp: number) {
            this.startRealTime = timestamp;
        },
        resetSelected() {
            this.selected = [];
        },
        changeMap() {
            this.map += 1;
            if (this.map > Object.keys(this.maps).length) {
                this.map = 1;
            }
            this.selected = [];
        },
        setLayer(layerId: number) {
            this.layer = layerId;
        },
        setRouteInfo(routeInfo: routeInfo) {
            this.routeInfo = routeInfo;
        },
        setSpeed(speed: number) {
            this.speed = speed;
        },
        /** 設定潛艇等級,並讓搜尋器快取失效(基礎屬性隨等級變) */
        setRank(rank: number) {
            let r = Math.floor(rank);
            if (isNaN(r) || r < 1) {
                r = 1;
            }
            if (r > this.maxRank) {
                r = this.maxRank;
            }
            if (r !== this.currentRank) {
                this.all_sets = [];
            }
            this.rank = r;
        },
        setEditorIndex(index: number) {
            this.editor_index = index;
        },
        // 初始化所有零件組合,首次打開搜尋視窗時初始化(等級不到的零件系列不列入)
        initAllSets() {
            if (this.all_sets.length == 0) {
                const usable = [] as number[];
                for (let i = 0; i < this.components.length; i++) {
                    if (this.components[i].rankReq <= this.currentRank) {
                        usable.push(i);
                    }
                }
                for (const c1 of usable) {
                    for (const c2 of usable) {
                        for (const c3 of usable) {
                            for (const c4 of usable) {
                                this.all_sets.push(
                                    calcSetBaseStatus({
                                        set: [c1, c2, c3, c4],
                                        name: '',
                                    }),
                                );
                            }
                        }
                    }
                }
            }
        },
        // 新增套裝
        addSet(payload: { setStatus: SetStatus; index: number }) {
            const { setStatus, index } = payload;
            if (setStatus.v) {
                if (!setStatus.n || setStatus.n == '') {
                    setStatus.n = '未命名';
                }
                if (index === -1) {
                    this.sets.push({
                        set: setStatus.set,
                        name: setStatus.n,
                    });
                } else {
                    this.sets.splice(index, 1, {
                        set: setStatus.set,
                        name: setStatus.n,
                    });
                }
            }
        },
        // 刪除套裝
        deleteSet(index: number) {
            if (this.sets.length >= index) {
                this.sets.splice(index, 1);
            }
        },
    },
});

if (import.meta.hot) {
    import.meta.hot.accept(acceptHMRUpdate(useSubmarineStore, import.meta.hot));
}

// 用於在 vue setup 外部取得該倉庫
export function useSubmarineStoreWithoutSetup() {
    return useSubmarineStore(store);
}
